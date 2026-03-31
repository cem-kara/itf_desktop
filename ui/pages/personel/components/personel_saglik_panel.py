# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QStyledItemDelegate
from ui.styles.icons import Icons

# =============================================================================
# Delegate: IconCellDelegate — [icon:check], [icon:x], [icon:tilde] stringlerini svg ikon olarak çizer
# =============================================================================
class IconCellDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        value = index.data()
        if isinstance(value, str) and value.startswith('[icon:'):
            icon_key = value[6:-1]
            color = None
            if icon_key == 'check':
                color = '#22c55e'
            elif icon_key == 'x':
                color = '#ef4444'
            elif icon_key == 'tilde':
                color = '#f59e0b'
            else:
                color = '#6b7280'
            pixmap = Icons.pixmap(icon_key, size=16, color=color)
            rect = option.rect
            x = rect.x() + (rect.width() - 16) // 2
            y = rect.y() + (rect.height() - 16) // 2
            painter.save()
            painter.drawPixmap(x, y, pixmap)
            painter.restore()
        else:
            super().paint(painter, option, index)

"""
PersonelSaglikPanel — Personel detay sayfasındaki sağlık takip sekmesi.

Mantık saglik_takip.py ile senkron:
    - _compute_durum  : Gecerli / Riskli (60 gün) / Gecikmis / Planlandi / IlkMuayene
    - Tablo           : Dermat/Dah/Göz/Görünt sütunları  ✓ / ✗ / ~
    - Muayene kartları: StyledPanel + renkli başlık (saglik_takip tarzı)
    - IlkMuayene      : Hiç kaydı olmayan personel → yeni form açılır
    - Rapor açma      : Drive link önce, sonra DATA_DIR offline yol
"""

import os
import platform
import subprocess
import uuid
from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, QDate, QModelIndex, Signal, QUrl
from PySide6.QtGui  import QColor, QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSizePolicy, QTableView, QVBoxLayout, QWidget,
)

from core.date_utils import parse_date, to_db_date, to_ui_date
from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconColors, IconRenderer

# ─────────────────────────────────────────────────────────────────────────────
#  Sabitler
# ─────────────────────────────────────────────────────────────────────────────
_RISKLI_GUN    = 60
STATUS_OPTIONS = ["Uygun", "Şartlı Uygun", "Uygun Değil"]

_EXAM_KEYS   = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
_EXAM_LABELS = {
    "Dermatoloji": "Dermatoloji",
    "Dahiliye":    "Dahiliye",
    "Goz":         "Göz",
    "Goruntuleme": "Görüntüleme",
}

TABLE_COLUMNS = [
    ("MuayeneTarihi",        "Muayene",         110),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol",  110),
    ("Dermat",               "Derm.",             65),
    ("Dahiliye_",            "Dah.",              65),
    ("Goz_",                 "Göz",               65),
    ("Goruntuleme_",         "Görünt.",            65),
    ("Sonuc",                "Sonuç",            100),
    ("Durum",                "Durum",             95),
    ("Notlar",               "Not",             -1),   # stretch
    ("Rapor",                "Rapor",             80),
]

_DURUM_CFG: dict[str, tuple[str, str, str]] = {
    "Gecerli":    ("#4ade80", "#4ade8022", "Geçerli"),
    "Riskli":     ("#f59e0b", "#f59e0b22", "Riskli"),
    "Gecikmis":   ("#f87171", "#f8717122", "Gecikmiş"),
    "Planlandi":  ("#94a3b8", "#94a3b822", "Planlandı"),
    "IlkMuayene": ("#38bdf8", "#38bdf822", "İlk Muayene"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Yardımcı
# ─────────────────────────────────────────────────────────────────────────────
def _compute_durum(mevcut: str, sonraki_str: str) -> str:
    sonraki = parse_date(str(sonraki_str or ""))
    if sonraki is None:
        return mevcut if mevcut else "Planlandi"
    bugun = date.today()
    if sonraki < bugun:
        return "Gecikmis"
    if sonraki <= bugun + timedelta(days=_RISKLI_GUN):
        return "Riskli"
    return "Gecerli"


# ─────────────────────────────────────────────────────────────────────────────
#  Tablo modeli
# ─────────────────────────────────────────────────────────────────────────────
class _SaglikModel(BaseTableModel):
    DATE_KEYS    = frozenset({"MuayeneTarihi", "SonrakiKontrolTarihi"})
    ALIGN_CENTER = frozenset({
        "MuayeneTarihi", "SonrakiKontrolTarihi",
        "Dermat", "Dahiliye_", "Goz_", "Goruntuleme_",
        "Sonuc", "Durum", "Rapor",
    })
    _EXAM_MAP = {
        "Dermat":        "DermatolojiDurum",
        "Dahiliye_":     "DahiliyeDurum",
        "Goz_":          "GozDurum",
        "Goruntuleme_":  "GoruntulemeDurum",
    }

    def __init__(self, data=None, parent=None):
        super().__init__(TABLE_COLUMNS, data, parent)

    def _display(self, key, row):
        if key in self._EXAM_MAP:
            val = str(row.get(self._EXAM_MAP[key], "") or "").strip().lower()
            if not val:
                return "–"
            if val == "uygun":
                return "[icon:check]"
            if val == "uygun değil":
                return "[icon:x]"
            return "[icon:tilde]"
        if key == "Rapor":
            if str(row.get("Durum","")) == "IlkMuayene": return "—"
            return "Aç" if row.get("_RaporDoc") else (
                "⚠ Eksik" if row.get("MuayeneTarihi") else "—"
            )
        if key == "Durum":
            cfg = _DURUM_CFG.get(str(row.get("Durum","")))
            return cfg[2] if cfg else str(row.get("Durum",""))
        val = super()._display(key, row)
        return "" if str(val).strip().lower() in ("none","") else val

    def _fg(self, key, row):
        if key in self._EXAM_MAP:
            val = str(row.get(self._EXAM_MAP[key], "") or "").strip().lower()
            if val == "uygun":       return QColor("#4ade80")
            if val == "uygun değil": return QColor("#f87171")
            if val:                  return QColor("#f59e0b")
            return QColor("#4b5563")
        if key == "Rapor" and not row.get("_RaporDoc") and row.get("MuayeneTarihi"):
            return QColor("#f59e0b")
        if key == "Durum":
            cfg = _DURUM_CFG.get(str(row.get("Durum","")))
            return QColor(cfg[0]) if cfg else None
        return None

    def _bg(self, key, row):
        if key == "Durum":
            cfg = _DURUM_CFG.get(str(row.get("Durum","")))
            return QColor(cfg[1]) if cfg else None
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  Panel
# ─────────────────────────────────────────────────────────────────────────────
class PersonelSaglikPanel(QWidget):
    open_documents = Signal(str)   # KayitNo → dokümanlar sekmesine git

    def __init__(self, db, personel_id: str, parent=None):
        super().__init__(parent)
        self.db           = db
        self.personel_id  = personel_id
        self._records:    list[dict] = []
        self._rapor_map:  dict       = {}
        self._last_kayit: str        = ""
        self._editing_no: Optional[str] = None
        self._selected_rapor_path: str  = ""
        self._exam_widgets: dict        = {}
        self._setup_ui()
        self.load_data()

    # ── UI ───────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.addWidget(self._build_stat_bar())
        self._form_panel = self._build_form_panel()
        self._form_panel.setVisible(False)
        root.addWidget(self._form_panel)
        root.addWidget(self._build_history_panel(), 1)

    # ── Durum özet barı ───────────────────────────────────────────────────────
    def _build_stat_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        bar.setFixedHeight(80)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 16, 10)
        lay.setSpacing(0)

        stats = QHBoxLayout()
        stats.setSpacing(28)
        self._lbl_son     = self._make_stat(stats, "Son Muayene")
        self._lbl_sonraki = self._make_stat(stats, "Sonraki Kontrol")
        self._lbl_sonuc   = self._make_stat(stats, "Sonuç")
        lay.addLayout(stats)
        lay.addStretch()

        self._badge = QLabel("—")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedSize(108, 28)
        self._badge.setStyleSheet(
            "border-radius:5px; font-size:11px; font-weight:700;"
            "background:#1e293b; color:#94a3b8; border:none;"
        )
        lay.addWidget(self._badge)
        lay.addSpacing(12)

        self._btn_yeni = QPushButton(" Muayene Ekle")
        self._btn_yeni.setProperty("style-role", "action")
        self._btn_yeni.setFixedHeight(28)
        self._btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yeni, "plus", color=IconColors.PRIMARY, size=13)
        self._btn_yeni.clicked.connect(self._open_form_new)
        lay.addWidget(self._btn_yeni)
        return bar

    def _make_stat(self, lay: QHBoxLayout, label: str) -> QLabel:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(1)
        lt = QLabel(label)
        lt.setProperty("style-role", "form")
        lt.setStyleSheet("font-size:10px;")
        vl.addWidget(lt)
        lv = QLabel("—")
        lv.setProperty("color-role", "primary")
        lv.setStyleSheet("font-size:13px; font-weight:600;")
        vl.addWidget(lv)
        lay.addWidget(w)
        return lv

    # ── Form paneli ───────────────────────────────────────────────────────────
    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(10)

        # Başlık
        top = QHBoxLayout()
        self._lbl_form_title = QLabel("Yeni Muayene Kaydı")
        self._lbl_form_title.setProperty("style-role", "section-title")
        top.addWidget(self._lbl_form_title)
        top.addStretch()
        btn_kapat = QPushButton()
        btn_kapat.setProperty("style-role", "danger")
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kapat, "x", color=IconColors.DANGER, size=14)
        btn_kapat.clicked.connect(self._close_form)
        top.addWidget(btn_kapat)
        lay.addLayout(top)

        # 4 muayene kutusu
        exam_row = QHBoxLayout()
        exam_row.setSpacing(10)
        for key in _EXAM_KEYS:
            exam_row.addWidget(self._create_exam_box(key, _EXAM_LABELS[key]))
        lay.addLayout(exam_row)

        # Rapor seç
        rapor_row = QHBoxLayout()
        rapor_row.setSpacing(8)
        self._btn_rapor = QPushButton(" Rapor Seç")
        self._btn_rapor.setProperty("style-role", "secondary")
        self._btn_rapor.setFixedWidth(110)
        self._btn_rapor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_rapor, "upload", color=IconColors.PRIMARY, size=13)
        self._btn_rapor.clicked.connect(self._on_rapor_sec)
        rapor_row.addWidget(self._btn_rapor)
        self._inp_rapor = QLineEdit()
        self._inp_rapor.setReadOnly(True)
        self._inp_rapor.setPlaceholderText("Rapor dosyası seçilmedi...")
        rapor_row.addWidget(self._inp_rapor, 1)
        lay.addLayout(rapor_row)

        # Notlar
        not_row = QHBoxLayout()
        lbl_not = QLabel("Notlar")
        lbl_not.setProperty("style-role", "form")
        lbl_not.setFixedWidth(48)
        not_row.addWidget(lbl_not)
        self._inp_not = QLineEdit()
        self._inp_not.setPlaceholderText("Açıklama veya not...")
        not_row.addWidget(self._inp_not, 1)
        lay.addLayout(not_row)

        # Kaydet / İptal
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_kaydet = QPushButton("Kaydet")
        self._btn_kaydet.setProperty("style-role", "action")
        self._btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_kaydet.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        IconRenderer.set_button_icon(self._btn_kaydet, "save", color=IconColors.PRIMARY, size=14)
        self._btn_kaydet.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_kaydet)
        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_iptal.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        IconRenderer.set_button_icon(btn_iptal, "x", color=IconColors.MUTED, size=14)
        btn_iptal.clicked.connect(self._close_form)
        btn_row.addWidget(btn_iptal)
        lay.addLayout(btn_row)
        return panel

    def _create_exam_box(self, key: str, label: str) -> QFrame:
        """saglik_takip._create_exam_box ile aynı yapı."""
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        vlay = QVBoxLayout(box)
        vlay.setContentsMargins(10, 8, 10, 10)
        vlay.setSpacing(4)

        title = QLabel(label)
        title.setProperty("style-role", "section-title")
        vlay.addWidget(title)

        lbl_tarih = QLabel("Muayene Tarihi")
        lbl_tarih.setProperty("style-role", "form")
        vlay.addWidget(lbl_tarih)

        de = QDateEdit(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        de.setCalendarPopup(True)
        vlay.addWidget(de)

        lbl_durum = QLabel("Durum")
        lbl_durum.setProperty("style-role", "form")
        vlay.addWidget(lbl_durum)

        cmb = QComboBox()
        cmb.addItems([""] + STATUS_OPTIONS)
        vlay.addWidget(cmb)

        self._exam_widgets[key] = {"tarih": de, "durum": cmb}
        return box

    # ── Geçmiş paneli ─────────────────────────────────────────────────────────
    def _build_history_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)

        # Başlık + buton
        hdr = QHBoxLayout()
        lbl = QLabel("Muayene Geçmişi")
        lbl.setProperty("style-role", "section-title")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self._btn_rapor_yukle = QPushButton(" Seçiliye Rapor Yükle")
        self._btn_rapor_yukle.setProperty("style-role", "secondary")
        self._btn_rapor_yukle.setFixedHeight(30)
        self._btn_rapor_yukle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(
            self._btn_rapor_yukle, "upload", color=IconColors.PRIMARY, size=13
        )
        self._btn_rapor_yukle.clicked.connect(self._rapor_yukle_selected)
        hdr.addWidget(self._btn_rapor_yukle)
        lay.addLayout(hdr)

        # Uyarı bandı
        self._lbl_uyari = QLabel("")
        self._lbl_uyari.setStyleSheet(
            "color:#f59e0b; background:#f59e0b15; border:1px solid #f59e0b44;"
            "border-radius:5px; padding:5px 10px; font-size:12px;"
        )
        self._lbl_uyari.setVisible(False)
        lay.addWidget(self._lbl_uyari)

        # Tablo
        self._model = _SaglikModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setProperty("color-role", "primary")
        self._table.doubleClicked.connect(self._on_double_click)

        hdr_h = self._table.horizontalHeader()
        for i, (col_key, _, w) in enumerate(TABLE_COLUMNS):
            if w == -1:
                hdr_h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr_h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self._table.setColumnWidth(i, w)
            # Muayene sütunları için ikon delegate ata
            if col_key in ("Dermat", "Dahiliye_", "Goz_", "Goruntuleme_"):
                self._table.setItemDelegateForColumn(i, IconCellDelegate(self._table))

        lay.addWidget(self._table)
        return panel

    # ── Veri yükleme ──────────────────────────────────────────────────────────
    def load_data(self):
        if not self.db or not self.personel_id:
            return
        try:
            from core.di import get_saglik_service as _sf
            svc          = _sf(self.db)
            takip_repo   = svc._r.get("Personel_Saglik_Takip")
            dokuman_repo = svc._r.get("Dokumanlar")

            all_rows = takip_repo.get_all() or []
            self._records = [
                r for r in all_rows
                if str(r.get("Personelid","")).strip() == self.personel_id
            ]
            self._records.sort(key=lambda x: str(x.get("MuayeneTarihi","")), reverse=True)

            # Rapor eşle
            self._rapor_map = {}
            knolar = {str(r.get("KayitNo","")).strip() for r in self._records}
            docs = dokuman_repo.get_where({
                "EntityType": "personel",
                "EntityId":   self.personel_id,
            }) or []
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi","")).strip() != "Personel_Saglik_Takip":
                    continue
                rel = str(doc.get("IliskiliBelgeID","")).strip()
                if rel in knolar and rel not in self._rapor_map:
                    self._rapor_map[rel] = doc
            for r in self._records:
                r["_RaporDoc"] = self._rapor_map.get(str(r.get("KayitNo","")).strip())

            # Durum yeniden hesapla
            for r in self._records:
                r["Durum"] = _compute_durum(
                    str(r.get("Durum","")).strip(),
                    str(r.get("SonrakiKontrolTarihi","")).strip(),
                )

            self._refresh_ui()
        except Exception as e:
            logger.error(f"PersonelSaglikPanel yükleme ({self.personel_id}): {e}")
            self._clear_ui()

    def _refresh_ui(self):
        self._model.set_data(self._records)

        if not self._records:
            self._clear_ui()
            self._set_badge("IlkMuayene")
            return

        latest = self._records[0]
        self._lbl_son.setText(to_ui_date(latest.get("MuayeneTarihi"), "—"))
        self._lbl_sonraki.setText(to_ui_date(latest.get("SonrakiKontrolTarihi"), "—"))
        self._lbl_sonuc.setText(str(latest.get("Sonuc") or "—"))

        snr = parse_date(str(latest.get("SonrakiKontrolTarihi","") or ""))
        if snr and snr < date.today():
            self._lbl_sonraki.setProperty("color-role", "primary")
        elif snr and snr <= date.today() + timedelta(days=_RISKLI_GUN):
            self._lbl_sonraki.setProperty("color-role", "primary")
        else:
            self._lbl_sonraki.setStyleSheet("font-size:13px; font-weight:600;")

        self._set_badge(latest.get("Durum",""))

        eksik = sum(1 for r in self._records if not r.get("_RaporDoc") and r.get("MuayeneTarihi"))
        if eksik:
            self._lbl_uyari.setText(f"⚠  Rapor yüklenmemiş {eksik} muayene kaydı var.")
            self._lbl_uyari.setVisible(True)
        else:
            self._lbl_uyari.setVisible(False)

    def _clear_ui(self):
        self._lbl_son.setText("—")
        self._lbl_sonraki.setText("—")
        self._lbl_sonuc.setText("—")
        self._lbl_uyari.setVisible(False)
        self._model.set_data([])

    def _set_badge(self, durum: str):
        cfg = _DURUM_CFG.get(durum)
        if cfg:
            fg, bg, txt = cfg
            self._badge.setStyleSheet(
                f"border-radius:5px; font-size:11px; font-weight:700;"
                f"background:{bg}; color:{fg}; border:1px solid {fg}55;"
            )
            self._badge.setText(txt)
        else:
            self._badge.setStyleSheet(
                "border-radius:5px; font-size:11px; font-weight:700;"
                "background:#1e293b; color:#94a3b8; border:none;"
            )
            self._badge.setText("—")

    # ── Form aç / kapat ───────────────────────────────────────────────────────
    def _open_form_new(self):
        self._editing_no = None
        self._lbl_form_title.setText("Yeni Muayene Kaydı")
        self._reset_form()
        self._form_panel.setVisible(True)

    def _open_form_edit(self, record: dict):
        self._editing_no = str(record.get("KayitNo","")).strip()
        self._lbl_form_title.setText("Kaydı Düzenle")
        self._inp_not.setText(str(record.get("Notlar","") or ""))
        self._inp_rapor.clear()
        self._selected_rapor_path = ""
        for key, t_col, d_col in [
            ("Dermatoloji",  "DermatolojiMuayeneTarihi",  "DermatolojiDurum"),
            ("Dahiliye",     "DahiliyeMuayeneTarihi",      "DahiliyeDurum"),
            ("Goz",          "GozMuayeneTarihi",           "GozDurum"),
            ("Goruntuleme",  "GoruntulemeMuayeneTarihi",   "GoruntulemeDurum"),
        ]:
            w = self._exam_widgets[key]
            d = parse_date(str(record.get(t_col,"") or ""))
            w["durum"].setCurrentText(str(record.get(d_col,"") or ""))
            w["tarih"].setDate(QDate(d.year, d.month, d.day) if d else QDate.currentDate())
        self._form_panel.setVisible(True)

    def _close_form(self):
        self._form_panel.setVisible(False)
        self._editing_no = None

    def _reset_form(self):
        self._inp_not.clear()
        self._inp_rapor.clear()
        self._selected_rapor_path = ""
        for w in self._exam_widgets.values():
            w["tarih"].setDate(QDate.currentDate())
            w["durum"].setCurrentIndex(0)

    # ── Rapor seç ─────────────────────────────────────────────────────────────
    def _on_rapor_sec(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "",
            "PDF ve Resim (*.pdf *.jpg *.jpeg *.png);;Tüm Dosyalar (*)"
        )
        if path:
            self._selected_rapor_path = path
            self._inp_rapor.setText(os.path.basename(path))

    # ── Kaydet ───────────────────────────────────────────────────────────────
    def _exam_date_if_set(self, key: str) -> str:
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return to_db_date(w["tarih"].date().toString("yyyy-MM-dd"))

    def _compute_summary(self):
        exam_data = []
        for key in _EXAM_KEYS:
            w = self._exam_widgets[key]
            exam_data.append((self._exam_date_if_set(key), str(w["durum"].currentText()).strip()))

        dates   = [parse_date(t) for t, _ in exam_data]
        dates_no_none = [d for d in dates if d is not None]
        latest  = max(dates_no_none).isoformat() if dates_no_none else ""
        sonraki = ""
        if latest:
            d = parse_date(latest)
            if d is not None:
                try:
                    sonraki = d.replace(year=d.year + 1).isoformat()
                except Exception:
                    sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        statuses = [s for _, s in exam_data if s]
        if "Uygun Değil" in statuses:
            sonuc, durum = "Uygun Değil", "Riskli"
        elif "Şartlı Uygun" in statuses:
            sonuc, durum = "Şartlı Uygun", "Riskli"
        elif "Uygun" in statuses:
            sonuc = "Uygun"
            durum = _compute_durum("Gecerli", sonraki)
        else:
            sonuc, durum = "", "Planlandi"

        return latest, sonraki, sonuc, durum

    def _on_save(self):
        if not self.db or not self.personel_id:
            return

        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        if not sonuc:
            QMessageBox.warning(self, "Eksik Bilgi", "En az bir muayene sonucu girilmelidir.")
            return

        aciklama = self._inp_not.text().strip()
        kritik   = any(
            str(self._exam_widgets[k]["durum"].currentText()).strip()
            in {"Şartlı Uygun", "Uygun Değil"}
            for k in _EXAM_KEYS
        )
        if kritik and not aciklama:
            QMessageBox.warning(
                self, "Eksik Bilgi",
                "Şartlı Uygun / Uygun Değil seçiminde açıklama zorunludur."
            )
            return

        try:
            from core.di import get_saglik_service as _sf
            svc           = _sf(self.db)
            takip_repo    = svc._r.get("Personel_Saglik_Takip")
            personel_repo = svc._r.get("Personel")
            pdata         = personel_repo.get_by_id(self.personel_id) or {}

            # IlkMuayene kaydı varsa onu güncelle
            if not self._editing_no:
                ilk = next(
                    (r for r in self._records if str(r.get("Durum","")) == "IlkMuayene"),
                    None
                )
                if ilk:
                    self._editing_no = str(ilk.get("KayitNo","")).strip() or None

            kayit_no = self._editing_no or uuid.uuid4().hex[:12].upper()

            payload = {
                "KayitNo":                  kayit_no,
                "Personelid":               self.personel_id,
                "AdSoyad":                  pdata.get("AdSoyad", ""),
                "Birim":                    pdata.get("GorevYeri", ""),
                "Yil":                      date.today().year,
                "MuayeneTarihi":            muayene_db,
                "SonrakiKontrolTarihi":     sonraki_db,
                "Sonuc":                    sonuc,
                "Durum":                    durum,
                "Notlar":                   aciklama,
                "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
                "DermatolojiDurum":         str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
                "DahiliyeMuayeneTarihi":    self._exam_date_if_set("Dahiliye"),
                "DahiliyeDurum":            str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
                "GozMuayeneTarihi":         self._exam_date_if_set("Goz"),
                "GozDurum":                 str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
                "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
                "GoruntulemeDurum":         str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
                "RaporDosya":               self._selected_rapor_path,
            }

            mevcut = takip_repo.get_by_id(kayit_no)
            if mevcut:
                takip_repo.update(kayit_no, payload)
            else:
                takip_repo.insert(payload)
            self._last_kayit = kayit_no

            # Personel tablosu özet — sadece en yeni muayeneyse güncelle
            mevcut_p = personel_repo.get_by_id(self.personel_id) or {}
            mevcut_t = parse_date(str(mevcut_p.get("MuayeneTarihi","") or ""))
            yeni_t   = parse_date(muayene_db)
            if yeni_t and (not mevcut_t or yeni_t >= mevcut_t):
                personel_repo.update(self.personel_id, {
                    "MuayeneTarihi": muayene_db,
                    "Sonuc": sonuc.lower() if sonuc == "Uygun" else sonuc,
                })

            QMessageBox.information(self, "Başarılı", "Muayene kaydı kaydedildi.")
            self._close_form()
            self.load_data()

        except Exception as e:
            logger.error(f"Muayene kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata oluştu:\n{e}")

    # ── Çift tıklama ─────────────────────────────────────────────────────────
    def _on_double_click(self, index: QModelIndex):
        if not index.isValid():
            return
        row = self._model.get_row(index.row()) if hasattr(self._model, "get_row") else None
        if not row:
            return

        rapor_col = next((i for i, (k,_,__) in enumerate(TABLE_COLUMNS) if k == "Rapor"), -1)
        if index.column() == rapor_col:
            self._open_rapor(row)
            return

        if str(row.get("Durum","")) == "IlkMuayene":
            self._open_form_new()
        else:
            self._open_form_edit(row)

    def _open_rapor(self, row: dict):
        doc = row.get("_RaporDoc")
        if not doc:
            QMessageBox.information(self, "Bilgi", "Bu kayıt için rapor yüklenmemiş.")
            return
        drive = str(doc.get("DrivePath","") or "").strip()
        local = str(doc.get("LocalPath","") or "").strip()
        try:
            if drive:
                QDesktopServices.openUrl(QUrl(drive))
                return
            if not local:
                QMessageBox.warning(self, "Dosya Bulunamadı", "Rapor dosya yolu bulunamadı.")
                return
            resolved = local
            if not os.path.isfile(resolved):
                try:
                    from core.paths import DATA_DIR
                    pid       = str(row.get("Personelid","")).strip()
                    fname     = os.path.basename(local)
                    candidate = os.path.join(
                        DATA_DIR, "offline_uploads", "personel", pid, fname
                    )
                    if os.path.isfile(candidate):
                        resolved = candidate
                except Exception:
                    pass
            if not os.path.isfile(resolved):
                QMessageBox.warning(
                    self, "Dosya Bulunamadı",
                    f"Rapor dosyasına erişilemedi:\n{local}"
                )
                return
            if platform.system() == "Windows":
                os.startfile(str(resolved))
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(resolved)])
            else:
                subprocess.run(["xdg-open", str(resolved)])
        except Exception as e:
            logger.error(f"Rapor açma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Rapor açılamadı:\n{e}")

    # ── Dokümanlar sekmesine yönlendir ────────────────────────────────────────
    def _rapor_yukle_selected(self):
        sel = (
            self._table.selectionModel().selectedRows()
            if self._table.selectionModel() else []
        )
        if not sel:
            QMessageBox.information(self, "Bilgi", "Önce tablodan bir muayene kaydı seçin.")
            return
        row = self._model.get_row(sel[0].row()) if hasattr(self._model, "get_row") else {}
        kno = str((row or {}).get("KayitNo","")).strip()
        if not kno:
            QMessageBox.warning(self, "Hata", "Seçili kaydın KayitNo bilgisi bulunamadı.")
            return
        self.open_documents.emit(kno)

    def set_embedded_mode(self, _): pass
