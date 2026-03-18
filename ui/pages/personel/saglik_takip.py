# -*- coding: utf-8 -*-
import os
import uuid
import platform
import subprocess
from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import Qt, QDate, QUrl, QModelIndex, QEvent, QThread, Signal as _Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableView,
    QDateEdit, QMessageBox, QFileDialog, QSizePolicy,
    QStyledItemDelegate, QApplication,
)
# =============================================================================
# Delegate: Rapor Sütunu Buton
# =============================================================================
class RaporButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            value = index.data()
            if value in ("Raporu Aç", "⚠ Rapor Eksik"):
                row = index.row()
                if self._parent:
                    self._parent.handle_rapor_button_clicked(row, value)
                return True
        return super().editorEvent(event, model, option, index)

from core.logger import logger
from core.date_utils import parse_date, to_db_date, to_ui_date
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer, IconColors, Icons

# =============================================================================
# Delegate: IconCellDelegate — [icon:check] ve [icon:x] stringlerini svg ikon olarak çizer
# =============================================================================
from PySide6.QtGui import QPainter
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

def _compute_durum(durum_db: str, sonraki_tarih_str: str) -> str:
    """
    DB'den gelen Durum değerini günceller:
    - Elle "Gecerli"/"Gecikmis" yazılmışsa önce bunları koru,
      ama SonrakiKontrolTarihi'ne göre tekrar değerlendir.
    - SonrakiKontrolTarihi geçmişse → Gecikmis
    - SonrakiKontrolTarihi 60 gün içindeyse → Riskli
    - SonrakiKontrolTarihi uzaktaysa → Gecerli
    - Tarih yoksa → Planlandi
    """
    from datetime import date, timedelta
    RISKLI_GUN = 60

    sonraki = None
    if sonraki_tarih_str:
        from core.date_utils import parse_date as _pd
        sonraki = _pd(sonraki_tarih_str)

    if sonraki is None:
        return durum_db if durum_db else "Planlandi"

    bugun = date.today()
    if sonraki < bugun:
        return "Gecikmis"
    if sonraki <= bugun + timedelta(days=RISKLI_GUN):
        return "Riskli"
    return "Gecerli"


STATUS_OPTIONS = ["Uygun", "Şartlı Uygun", "Uygun Değil"]

TABLE_COLUMNS = [
    ("AdSoyad",              "Ad Soyad",         175),
    ("Birim",                "Birim",             155),
    ("MuayeneTarihi",        "Muayene",          150),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol",  150),
    ("Dermat",               "Derm.",              60),
    ("Dahiliye",             "Dah.",               60),
    ("Goz",                  "Göz",               60),
    ("Goruntuleme",          "Görünt.",            60),
    ("Sonuc",                "Sonuç",            130),
    ("Durum",                "Durum",            100),
    ("Rapor",                "Rapor",             80),
]


# =============================================================================
# Model
# =============================================================================

class SaglikTakipTableModel(BaseTableModel):
    DATE_KEYS    = frozenset({"MuayeneTarihi", "SonrakiKontrolTarihi"})
    ALIGN_CENTER = frozenset({
        "MuayeneTarihi", "SonrakiKontrolTarihi",
        "Dermat", "Dahiliye", "Goz", "Goruntuleme",
        "Sonuc", "Durum", "Rapor",
    })
    _EXAM_COL_MAP = {
        "Dermat":      "DermatolojiDurum",
        "Dahiliye":    "DahiliyeDurum",
        "Goz":         "GozDurum",
        "Goruntuleme": "GoruntulemeDurum",
    }

    def __init__(self, rows=None, parent=None):
        super().__init__(TABLE_COLUMNS, rows, parent)

    def _display(self, key, row):
        if key in self._EXAM_COL_MAP:
            val = str(row.get(self._EXAM_COL_MAP[key], "") or "").strip()
            if not val:
                return "–"
            if val.lower() in ("uygun", "normal", "ok"):
                return "[icon:check]"
            if val.lower() in ("uygun değil", "anormal"):
                return "[icon:x]"
            # Şartlı Uygun veya bilinmeyen kısaltılmış göster
            return "[icon:tilde]"
        if key == "Rapor":
            # İlk Muayene satırında rapor gösterme — henüz kaydı yok
            if row.get("Durum") == "IlkMuayene":
                return "-"
            rapor_path = row.get("_RaporPath")
            if rapor_path and str(rapor_path).strip():
                return "Raporu Aç"
            muayene = row.get("MuayeneTarihi")
            if muayene and str(muayene).strip():
                return "⚠ Rapor Eksik"
            return "-"
        if key == "Durum" and row.get("Durum") == "IlkMuayene":
            return "İlk Muayene"
        # "None" string'ini temizle
        val = super()._display(key, row)
        return "" if str(val).strip().lower() == "none" else val

    def _fg(self, key, row):
        from PySide6.QtGui import QColor
        if key in self._EXAM_COL_MAP:
            val = str(row.get(self._EXAM_COL_MAP[key], "") or "").strip().lower()
            # Sanal satır (bu yıl kaydı yok) → önceki yılın verisi, daha soluk renk
            is_virtual = not str(row.get("KayitNo", "")).strip()
            alpha = 140 if is_virtual else 255
            if val in ("uygun", "normal", "ok"):
                c = QColor("#22c55e"); c.setAlpha(alpha); return c
            if val in ("uygun değil", "anormal"):
                c = QColor("#ef4444"); c.setAlpha(alpha); return c
            if val:
                c = QColor("#f59e0b"); c.setAlpha(alpha); return c
            return QColor("#6b7280")       # gri — boş
        if key == "Rapor":
            muayene = row.get("MuayeneTarihi") if row else None
            if muayene and str(muayene).strip() and not row.get("_RaporPath"):
                return QColor("#f59e0b")
        if key == "Durum":
            durum = row.get("Durum", "")
            if durum == "IlkMuayene":
                from PySide6.QtGui import QColor
                return QColor("#38bdf8")   # açık mavi
            return self.status_fg(durum)
        return None

    def _bg(self, key, row):
        if key == "Durum":
            durum = row.get("Durum", "")
            if durum == "IlkMuayene":
                from PySide6.QtGui import QColor
                return QColor("#38bdf822")
            return self.status_bg(durum)
        return None



# =============================================================================
# Worker: arka planda veri yükleme
# =============================================================================

class _SaglikLoader(QThread):
    finished = _Signal(dict)
    error    = _Signal(str)

    def __init__(self, db):
        super().__init__()
        self._db_path = getattr(db, 'db_path', None) if db else None

    def run(self):
        try:
            from core.di import get_saglik_service as _svc_factory, get_dokuman_service
            from core.paths import DATA_DIR, DB_PATH
            from database.sqlite_manager import SQLiteManager
            db_path = self._db_path or DB_PATH
            db = SQLiteManager(db_path=db_path)
            _svc          = _svc_factory(db)
            personel_repo = _svc._r.get("Personel")
            takip_repo    = _svc._r.get("Personel_Saglik_Takip")
            dokuman_repo  = _svc._r.get("Dokumanlar")

            all_personel  = personel_repo.get_all()
            personel_rows = [
                p for p in all_personel
                if str(p.get("Durum", "")).strip().lower() != "pasif"
            ]
            takip_rows = takip_repo.get_all()

            rapor_map: dict = {}
            docs = dokuman_repo.get_where({"EntityType": "personel"})
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                    continue
                entity_id = str(doc.get("EntityId", "")).strip()
                rel_id    = str(doc.get("IliskiliBelgeID", "")).strip()
                if entity_id and rel_id:
                    rapor_map[(entity_id, rel_id)] = doc

            for takip in takip_rows:
                personelid = str(takip.get("Personelid", "")).strip()
                kayit_no   = str(takip.get("KayitNo",    "")).strip()
                doc        = rapor_map.get((personelid, kayit_no))

                rapor_path = ""
                if doc:
                    local_path = str(doc.get("LocalPath", "")).strip()
                    drive_path = str(doc.get("DrivePath", "")).strip()
                    belge_adi  = str(doc.get("Belge",     "")).strip()
                    tc_no      = str(doc.get("EntityId",  "")).strip() or personelid

                    if local_path and os.path.isfile(local_path):
                        rapor_path = local_path
                    elif drive_path:
                        rapor_path = drive_path
                    else:
                        rapor_path = local_path

                    canonical_path = ""
                    if belge_adi and tc_no:
                        canonical_path = os.path.join(
                            DATA_DIR, "offline_uploads", "personel", tc_no, belge_adi
                        )
                    if canonical_path and os.path.isfile(canonical_path):
                        rapor_path = canonical_path
                    elif local_path and os.path.isdir(local_path) and belge_adi:
                        joined = os.path.join(local_path, belge_adi)
                        if os.path.isfile(joined):
                            rapor_path = joined

                if not rapor_path:
                    rapor_dosya = str(takip.get("RaporDosya", "")).strip()
                    if rapor_dosya:
                        if not os.path.isabs(rapor_dosya) and not rapor_dosya.startswith(
                            ("http://", "https://")
                        ):
                            basename  = os.path.basename(rapor_dosya)
                            canonical = os.path.join(
                                DATA_DIR, "offline_uploads", "personel", personelid, basename
                            )
                            rapor_path = canonical if os.path.isfile(canonical) else rapor_dosya
                        else:
                            rapor_path = rapor_dosya

                takip["_RaporPath"] = rapor_path

            self.finished.emit({
                "all_personel":  all_personel,
                "personel_rows": personel_rows,
                "takip_rows":    takip_rows,
            })
        except Exception as exc:
            self.error.emit(str(exc))



class _SaglikSaver(QThread):
    """Kaydetme işlemini arka planda yapar."""
    finished = _Signal(str)   # "ok" veya "rapor_ok"
    error    = _Signal(str)

    def __init__(self, db, mode: str, payload: dict):
        super().__init__()
        self._db_path = getattr(db, 'db_path', None) if db else None
        self._mode    = mode     # "full" veya "rapor"
        self._payload = payload

    def run(self):
        try:
            from core.di import get_saglik_service as _svc_factory
            from database.sqlite_manager import SQLiteManager
            from core.paths import DB_PATH
            db_path = self._db_path or DB_PATH
            db = SQLiteManager(db_path=db_path)
            _svc       = _svc_factory(db)
            takip_repo = _svc._r.get("Personel_Saglik_Takip")

            if self._mode == "rapor":
                takip_repo.update(self._payload["KayitNo"], {"RaporDosya": self._payload["RaporDosya"]})
                self.finished.emit("rapor_ok")
                return

            # full kayıt
            personel_repo = _svc._r.get("Personel")
            mevcut = takip_repo.get_by_id(self._payload["KayitNo"])
            if mevcut:
                takip_repo.update(self._payload["KayitNo"], self._payload)
            else:
                takip_repo.insert(self._payload)

            muayene_db = self._payload.get("MuayeneTarihi", "")
            if muayene_db:
                from core.date_utils import parse_date as _pd
                mevcut_p = personel_repo.get_by_id(self._payload["Personelid"]) or {}
                mevcut_t = _pd(mevcut_p.get("MuayeneTarihi"))
                yeni_t   = _pd(muayene_db)
                if yeni_t and (not mevcut_t or yeni_t >= mevcut_t):
                    personel_repo.update(self._payload["Personelid"], {
                        "MuayeneTarihi": muayene_db,
                        "Sonuc":         self._payload.get("Sonuc", ""),
                    })
            self.finished.emit("ok")
        except Exception as exc:
            self.error.emit(str(exc))

# =============================================================================
# Sayfa
# =============================================================================

class SaglikTakipPage(QWidget):
    def _set_icon_delegate(self):
        # Sadece muayene sütunları için uygula
        exam_cols = ["Dermat", "Dahiliye", "Goz", "Goruntuleme"]
        for col in exam_cols:
            idx = None
            for i, c in enumerate(TABLE_COLUMNS):
                if c[0] == col:
                    idx = i
                    break
            if idx is not None:
                self.table.setItemDelegateForColumn(idx, IconCellDelegate(self.table))
    def _fill_hizmet_sinifi_combo(self):
        """Hizmet sınıfı combobox'unu Sabitler tablosundan doldur."""
        try:
            from core.di import get_settings_service
            svc = get_settings_service(self._db) if self._db else None
            sinifler = []
            if svc:
                # Sabitler tablosunda Kod='HizmetSinifi' olanları çek
                sabitler = svc.get_sabitler().veri or [] if hasattr(svc, 'get_sabitler') else []
                sinifler = [s.get("MenuEleman", "").strip() for s in sabitler if s.get("Kod") == "Hizmet_Sinifi" and s.get("MenuEleman")]
            sinifler = sorted(set(sinifler))
            current = self.cmb_hizmet_sinifi.currentText() if hasattr(self, 'cmb_hizmet_sinifi') else None
            self.cmb_hizmet_sinifi.blockSignals(True)
            self.cmb_hizmet_sinifi.clear()
            self.cmb_hizmet_sinifi.addItem("Tümü")
            self.cmb_hizmet_sinifi.addItems(sinifler)
            if current:
                idx = self.cmb_hizmet_sinifi.findText(current)
                if idx >= 0:
                    self.cmb_hizmet_sinifi.setCurrentIndex(idx)
            self.cmb_hizmet_sinifi.blockSignals(False)
        except Exception as e:
            logger.error(f"Hizmet sınıfı combobox doldurma hatası: {e}")

    def _fill_personel_combo(self):
        """Seçili hizmet sınıfına göre personel comboyu doldur."""
        sinif_filtre = self.cmb_hizmet_sinifi.currentText() if hasattr(self, 'cmb_hizmet_sinifi') else None
        aktif = [p for p in self._personel_rows]
        if sinif_filtre and sinif_filtre != "Tümü":
            aktif = [p for p in aktif if str(p.get("HizmetSinifi") or "").strip() == sinif_filtre]
        aktif.sort(key=lambda p: str(p.get("AdSoyad", "")))
        current_data = self.cmb_personel.currentData() if hasattr(self, 'cmb_personel') else None
        self.cmb_personel.blockSignals(True)
        self.cmb_personel.clear()
        for p in aktif:
            ad = p.get("AdSoyad", "")
            tc = p.get("KimlikNo", "")
            birim = p.get("GorevYeri", "") or p.get("Birim", "")
            self.cmb_personel.addItem(f"{ad}  ({birim})", p)
        if current_data:
            idx = self.cmb_personel.findData(current_data)
            if idx >= 0:
                self.cmb_personel.setCurrentIndex(idx)
        self.cmb_personel.blockSignals(False)
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db   = db
        self._all_rows = []
        self._takip_rows = []
        self._personel_rows = []
        self._editing_id = None
        self._rapor_only_mode = False
        self._selected_report_path = ""
        self._exam_keys = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
        self._exam_widgets = {}
        self._exam_status_dot = {}
        self._setup_ui()
        self._connect_signals()
        self._set_icon_delegate()

    # -------------------------------------------------------------------------
    # UI Kurulum
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 10, 12, 10)
        main_lay.setSpacing(10)

        # 1. Başlık satırı
        main_lay.addWidget(self._build_header_bar())

        # 2. Özet istatistik kartları
        self._stat_cards = {}
        main_lay.addWidget(self._build_stat_cards())

        # 3. Filtre çubuğu
        main_lay.addWidget(self._build_filter_bar())

        # 4. Form paneli — gizli başlar
        self.form_panel = self._build_form_panel()
        self.form_panel.setVisible(False)
        main_lay.addWidget(self.form_panel)

        # 5. Tablo
        self._build_table_widget()
        main_lay.addWidget(self.table, 1)

        # 6. Durum/bilgi satırı
        info_row = QHBoxLayout()
        self.lbl_info = QLabel("")
        self.lbl_info.setProperty("style-role", "footer")
        info_row.addWidget(self.lbl_info)
        info_row.addStretch()
        self.lbl_table_count = QLabel("")
        self.lbl_table_count.setProperty("color-role", "muted")
        self.lbl_table_count.setStyleSheet("font-size: 11px;")
        info_row.addWidget(self.lbl_table_count)
        main_lay.addLayout(info_row)

    # -- Başlık çubuğu ---------------------------------------------------------

    def _build_header_bar(self) -> QFrame:
        frame = QFrame()
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        lbl = QLabel("Sağlık Takip")
        lbl.setProperty("style-role", "title")
        lbl.style().unpolish(lbl); lbl.style().polish(lbl)
        lay.addWidget(lbl)
        lay.addStretch()

        self.btn_yeni = QPushButton("Yeni Muayene Kaydı")
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.setFixedHeight(30)
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_yeni)

        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setFixedHeight(30)
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "sync", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_yenile)

        self.btn_export = QPushButton("Excel'e Aktar")
        self.btn_export.setProperty("style-role", "secondary")
        self.btn_export.setFixedHeight(30)
        self.btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_export, "download", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_export)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setProperty("style-role", "danger")
        self.btn_kapat.setFixedHeight(30)
        self.btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=IconColors.DANGER, size=14)
        lay.addWidget(self.btn_kapat)

        return frame

    # -- Özet kart satırı ------------------------------------------------------

    def _build_stat_cards(self) -> QFrame:
        frame = QFrame()
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card_defs = [
            ("toplam",      "Toplam Kayıt",  "—", "accent",  None),
            ("gecerli",     "Geçerli",        "—", "ok",      "#16a34a"),
            ("gecikmis",    "Gecikmiş",       "—", "warn",    "#d97706"),
            ("riskli",      "Riskli",         "—", "err",     "#dc2626"),
            ("planlandi",   "Planlandı",       "—", "muted",   None),
            ("ilkmuayene",  "İlk Muayene",    "—", "info",    "#0369a1"),
        ]
        for key, label, init_val, color_role, badge_bg in card_defs:
            card = QFrame()
            card.setProperty("bg-role", "panel")
            card.setStyleSheet("border-radius: 8px;")
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setFixedHeight(72)

            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 8, 14, 8)
            cl.setSpacing(2)

            lbl_num = QLabel(init_val)
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignLeft)
            lbl_num.setProperty("color-role", color_role)
            lbl_num.setStyleSheet("font-size: 22px; font-weight: 700; background: transparent;")
            lbl_num.style().unpolish(lbl_num); lbl_num.style().polish(lbl_num)
            cl.addWidget(lbl_num)

            lbl_lbl = QLabel(label)
            lbl_lbl.setProperty("color-role", "muted")
            lbl_lbl.setStyleSheet("font-size: 11px; background: transparent;")
            lbl_lbl.style().unpolish(lbl_lbl); lbl_lbl.style().polish(lbl_lbl)
            cl.addWidget(lbl_lbl)

            lay.addWidget(card)
            self._stat_cards[key] = lbl_num

        return frame

    # -- Filtre çubuğu ---------------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("bg-role", "panel")
        frame.setStyleSheet("border-radius: 6px;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        # Yıl
        self.cmb_yil = QComboBox()
        self.cmb_yil.setFixedWidth(150)
        self.cmb_yil.addItem("Tüm Yıllar", 0)
        this_year = date.today().year
        for y in range(this_year + 1, this_year - 4, -1):
            self.cmb_yil.addItem(str(y), y)
        self.cmb_yil.setCurrentIndex(2)  # index 0=Tüm Yıllar, 1=gelecek yıl, 2=bu yıl
        lay.addWidget(self.cmb_yil)

        # Birim
        self.cmb_birim_filter = QComboBox()
        self.cmb_birim_filter.setMinimumWidth(300)
        self.cmb_birim_filter.addItem("Tüm Birimler")
        lay.addWidget(self.cmb_birim_filter)

        # Durum
        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setMinimumWidth(130)
        self.cmb_durum_filter.addItems(
            ["Tüm Durumlar", "Planlandi", "Gecerli", "Gecikmis", "Riskli", "IlkMuayene"]
        )
        lay.addWidget(self.cmb_durum_filter)

        # Arama
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Ad soyad ara...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(200)
        lay.addWidget(self.search, 1)

        return frame

    # -- Form paneli ----------------------------------------------------------

    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        panel.setStyleSheet("border-radius: 8px;")
        form_lay = QVBoxLayout(panel)
        form_lay.setContentsMargins(14, 12, 14, 12)
        form_lay.setSpacing(10)

        # ── Başlık satırı ──
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.lbl_form_title = QLabel("Yeni Muayene Kaydı")
        self.lbl_form_title.setProperty("style-role", "section-title")
        self.lbl_form_title.style().unpolish(self.lbl_form_title)
        self.lbl_form_title.style().polish(self.lbl_form_title)
        top_row.addWidget(self.lbl_form_title)

        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setFixedWidth(1)
        sep_v.setProperty("bg-role", "separator")
        sep_v.style().unpolish(sep_v); sep_v.style().polish(sep_v)
        top_row.addWidget(sep_v)

        # Hizmet Sınıfı
        lbl_hs = QLabel("Hizmet Sınıfı:")
        lbl_hs.setProperty("color-role", "muted")
        lbl_hs.setStyleSheet("font-size: 11px;")
        lbl_hs.style().unpolish(lbl_hs); lbl_hs.style().polish(lbl_hs)
        top_row.addWidget(lbl_hs)
        self.cmb_hizmet_sinifi = QComboBox()
        self.cmb_hizmet_sinifi.setMinimumWidth(150)
        self.cmb_hizmet_sinifi.setToolTip("Hizmet Sınıfına göre filtrele")
        top_row.addWidget(self.cmb_hizmet_sinifi)

        # Personel
        lbl_per = QLabel("Personel:")
        lbl_per.setProperty("color-role", "muted")
        lbl_per.setStyleSheet("font-size: 11px;")
        lbl_per.style().unpolish(lbl_per); lbl_per.style().polish(lbl_per)
        top_row.addWidget(lbl_per)
        self.cmb_personel = QComboBox()
        self.cmb_personel.setMinimumWidth(220)
        self.cmb_personel.setEditable(True)
        if _le := self.cmb_personel.lineEdit():
            _le.setPlaceholderText("İsim yazarak ara...")
        top_row.addWidget(self.cmb_personel, 1)

        self.lbl_personel_ro = QLabel("")
        self.lbl_personel_ro.setProperty("style-role", "section-title")
        self.lbl_personel_ro.setVisible(False)
        top_row.addWidget(self.lbl_personel_ro, 1)

        self.btn_form_kapat = QPushButton()
        self.btn_form_kapat.setProperty("style-role", "close")
        self.btn_form_kapat.setFixedSize(28, 28)
        self.btn_form_kapat.setToolTip("Formu Kapat")
        self.btn_form_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_form_kapat, "x", color=IconColors.DANGER, size=16)
        top_row.addWidget(self.btn_form_kapat)
        form_lay.addLayout(top_row)

        # ── İnce ayırıcı ──
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.Shape.HLine)
        sep_h.setFixedHeight(1)
        sep_h.setProperty("bg-role", "separator")
        sep_h.style().unpolish(sep_h); sep_h.style().polish(sep_h)
        form_lay.addWidget(sep_h)

        # ── 4 muayene kartı ──
        self.exam_section = QWidget()
        self.exam_section.setStyleSheet("background: transparent;")
        exam_lay = QVBoxLayout(self.exam_section)
        exam_lay.setContentsMargins(0, 0, 0, 0)
        exam_lay.setSpacing(4)

        exam_hint = QLabel("Muayene branşlarını doldurun — sonuç otomatik hesaplanır")
        exam_hint.setProperty("color-role", "muted")
        exam_hint.setStyleSheet("font-size: 11px;")
        exam_hint.style().unpolish(exam_hint); exam_hint.style().polish(exam_hint)
        exam_lay.addWidget(exam_hint)

        exam_row = QHBoxLayout()
        exam_row.setSpacing(10)
        exam_labels = {
            "Dermatoloji": ("Dermatoloji", "skin"),
            "Dahiliye":    ("Dahiliye",    "activity"),
            "Goz":         ("Göz",         "eye"),
            "Goruntuleme": ("Görüntüleme", "image"),
        }
        for key in self._exam_keys:
            lbl_txt, icon_key = exam_labels[key]
            exam_row.addWidget(self._create_exam_box(key, lbl_txt, icon_key))

        exam_lay.addLayout(exam_row)
        form_lay.addWidget(self.exam_section)

        # ── Alt satır: Rapor + Notlar + Kaydet/İptal ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        # Rapor seç
        rapor_grp = QFrame()
        rapor_grp.setProperty("bg-role", "elevated")
        rapor_grp.setStyleSheet("border-radius: 6px;")
        rapor_grp_l = QHBoxLayout(rapor_grp)
        rapor_grp_l.setContentsMargins(8, 6, 8, 6)
        rapor_grp_l.setSpacing(8)
        lbl_rapor = QLabel("Rapor:")
        lbl_rapor.setProperty("color-role", "muted")
        lbl_rapor.setStyleSheet("font-size: 11px;")
        lbl_rapor.style().unpolish(lbl_rapor); lbl_rapor.style().polish(lbl_rapor)
        rapor_grp_l.addWidget(lbl_rapor)
        self.inp_rapor = QLineEdit()
        self.inp_rapor.setReadOnly(True)
        self.inp_rapor.setPlaceholderText("Dosya seçilmedi...")
        self.inp_rapor.setMinimumWidth(160)
        rapor_grp_l.addWidget(self.inp_rapor, 1)
        self.btn_rapor = QPushButton("Seç")
        self.btn_rapor.setProperty("style-role", "secondary")
        self.btn_rapor.setFixedHeight(28)
        self.btn_rapor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_rapor, "upload", color=IconColors.PRIMARY, size=12)
        rapor_grp_l.addWidget(self.btn_rapor)
        bottom_row.addWidget(rapor_grp, 2)

        # Notlar
        self._not_grp = QFrame()
        not_grp = self._not_grp
        not_grp.setProperty("bg-role", "elevated")
        not_grp.setStyleSheet("border-radius: 6px;")
        not_grp_l = QHBoxLayout(not_grp)
        not_grp_l.setContentsMargins(8, 6, 8, 6)
        not_grp_l.setSpacing(8)
        lbl_not = QLabel("Not:")
        lbl_not.setProperty("color-role", "muted")
        lbl_not.setStyleSheet("font-size: 11px;")
        lbl_not.style().unpolish(lbl_not); lbl_not.style().polish(lbl_not)
        not_grp_l.addWidget(lbl_not)
        self.inp_not = QLineEdit()
        self.inp_not.setPlaceholderText("Açıklama veya not...")
        not_grp_l.addWidget(self.inp_not, 1)
        bottom_row.addWidget(not_grp, 2)

        # Kaydet / İptal
        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setFixedHeight(34)
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=IconColors.PRIMARY, size=14)
        btn_col.addWidget(self.btn_kaydet)

        self.btn_temizle = QPushButton("İptal")
        self.btn_temizle.setProperty("style-role", "secondary")
        self.btn_temizle.setFixedHeight(34)
        self.btn_temizle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_temizle, "x", color=IconColors.MUTED, size=14)
        btn_col.addWidget(self.btn_temizle)
        bottom_row.addLayout(btn_col)
        form_lay.addLayout(bottom_row)

        return panel

    def _create_exam_box(self, key: str, label: str, icon_key: str = "") -> QFrame:
        # Her branş için renk tonu
        _COLORS = {
            "Dermatoloji": "rgba(99,102,241,0.12)",
            "Dahiliye":    "rgba(16,185,129,0.12)",
            "Goz":         "rgba(59,130,246,0.12)",
            "Goruntuleme": "rgba(245,158,11,0.12)",
        }
        _BORDER = {
            "Dermatoloji": "#6366f1",
            "Dahiliye":    "#10b981",
            "Goz":         "#3b82f6",
            "Goruntuleme": "#f59e0b",
        }
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background: {_COLORS.get(key, 'transparent')}; "
            f"border: 1px solid {_BORDER.get(key, '#444')}44; border-radius: 8px; }}"
        )
        vlay = QVBoxLayout(box)
        vlay.setContentsMargins(10, 10, 10, 12)
        vlay.setSpacing(6)

        # Başlık
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title = QLabel(label)
        title.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {_BORDER.get(key, '#aaa')}; "
            "background: transparent; border: none;"
        )
        title_row.addWidget(title)
        title_row.addStretch()
        # Durum göstergesi (sonradan güncellenecek)
        dot = QLabel("●")
        dot.setStyleSheet("font-size: 10px; color: #555; background: transparent; border: none;")
        dot.setToolTip("Durum seçilmedi")
        title_row.addWidget(dot)
        self._exam_status_dot[key] = dot
        vlay.addLayout(title_row)

        # Tarih
        lbl_tarih = QLabel("Muayene Tarihi")
        lbl_tarih.setStyleSheet(
            "font-size: 10px; color: #888; background: transparent; border: none;"
        )
        vlay.addWidget(lbl_tarih)
        de = QDateEdit(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        de.setCalendarPopup(True)
        de.setFixedHeight(28)
        vlay.addWidget(de)

        # Sonuç
        lbl_durum = QLabel("Sonuç")
        lbl_durum.setStyleSheet(
            "font-size: 10px; color: #888; background: transparent; border: none;"
        )
        vlay.addWidget(lbl_durum)
        cmb = QComboBox()
        cmb.addItems([""] + STATUS_OPTIONS)
        cmb.setFixedHeight(28)
        vlay.addWidget(cmb)

        self._exam_widgets[key] = {"tarih": de, "durum": cmb}

        # Dot'u durum değişince güncelle
        cmb.currentTextChanged.connect(lambda txt, k=key: self._update_exam_dot(k, txt))
        return box

    def _update_exam_dot(self, key: str, durum: str):
        dot = getattr(self, "_exam_status_dot", {}).get(key)
        if not dot:
            return
        color_map = {
            "Uygun":        "#16a34a",
            "Şartlı Uygun": "#d97706",
            "Uygun Değil":  "#dc2626",
        }
        color = color_map.get(durum, "#555")
        tip   = durum if durum else "Seçilmedi"
        dot.setStyleSheet(f"font-size: 10px; color: {color}; background: transparent; border: none;")
        dot.setToolTip(tip)

    # -- Tablo ----------------------------------------------------------------

    def _build_table_widget(self):
        self.table = QTableView()
        self.model = SaglikTakipTableModel([])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setShowGrid(False)
        self.model.setup_columns(self.table)
        self.table.setStyleSheet(
            "QTableView::item:selected { color: #ffffff; }"
            "QTableView { border: none; }"
        )
        # Rapor sütununa buton delegate ata
        rapor_col = [i for i, (k, _, _) in enumerate(TABLE_COLUMNS) if k == "Rapor"]
        if rapor_col:
            self.table.setItemDelegateForColumn(rapor_col[0], RaporButtonDelegate(self))
    def _on_export(self):
        """Tabloda görünen satırları CSV olarak dışa aktar."""
        rows = self.model._data if hasattr(self.model, "_data") else []
        if not rows:
            QMessageBox.information(self, "Dışa Aktarma", "Aktarılacak satır bulunamadı.")
            return

        yil  = self.cmb_yil.currentData() or date.today().year
        birim = self.cmb_birim_filter.currentText()
        dosya_adi = f"saglik_takip_{yil}"
        if birim and birim != "Tüm Birimler":
            dosya_adi += f"_{birim}"
        dosya_adi += ".csv"

        path, _ = QFileDialog.getSaveFileName(
            self, "Excel/CSV olarak kaydet", dosya_adi,
            "CSV Dosyaları (*.csv);;Tüm Dosyalar (*)"
        )
        if not path:
            return

        import csv
        basliklar = [
            "Ad Soyad", "Birim", "Yıl", "Muayene Tarihi", "Sonraki Kontrol",
            "Dermatoloji", "Dahiliye", "Göz", "Görüntüleme",
            "Sonuç", "Durum",
        ]
        alan_map = [
            ("AdSoyad", ""),
            ("Birim", ""),
            ("Yil", ""),
            ("MuayeneTarihi", ""),
            ("SonrakiKontrolTarihi", ""),
            ("DermatolojiDurum", ""),
            ("DahiliyeDurum", ""),
            ("GozDurum", ""),
            ("GoruntulemeDurum", ""),
            ("Sonuc", ""),
            ("Durum", ""),
        ]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(basliklar)
                for row in rows:
                    writer.writerow([
                        str(row.get(alan, "") or "").strip()
                        for alan, _ in alan_map
                    ])
            QMessageBox.information(
                self, "Başarılı",
                f"{len(rows)} satır dışa aktarıldı.\n\n{path}"
            )
            if platform.system() == "Windows":
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi:\n{e}")

    def handle_rapor_button_clicked(self, row_idx: int, value: str):
        row = self.model.get_row(row_idx)
        if not row:
            return
        if value == "Raporu Aç":
            # Raporu aç fonksiyonu (mevcut)
            rapor_path = str(row.get("_RaporPath", "")).strip()
            if not rapor_path:
                QMessageBox.information(self, "Bilgi", "Bu kayıt için rapor dosyası bulunmuyor.")
                return
            try:
                if rapor_path.startswith(("http://", "https://")):
                    QDesktopServices.openUrl(QUrl(rapor_path))
                    logger.info(f"Saglik raporu acildi (online): {rapor_path}")
                    return
                from core.paths import DATA_DIR
                resolved_path = rapor_path
                if not os.path.isfile(resolved_path):
                    personelid = str(row.get("Personelid", "")).strip()
                    kayit_no   = str(row.get("KayitNo",    "")).strip()
                    file_name  = os.path.basename(rapor_path)
                    candidates = []
                    if file_name and personelid:
                        candidates.append(
                            os.path.join(DATA_DIR, "offline_uploads", "personel", personelid, file_name)
                        )
                    if rapor_path and not os.path.isabs(rapor_path):
                        candidates.append(os.path.join(DATA_DIR, rapor_path))
                    for candidate in candidates:
                        if candidate and os.path.isfile(candidate):
                            resolved_path = candidate
                            break
                if not os.path.isfile(resolved_path):
                    QMessageBox.warning(
                        self, "Dosya Bulunamadı",
                        f"Rapor dosyası bulunamadı:\n\n{rapor_path}\n\nDosya silinmiş veya yol değişmiş olabilir."
                    )
                    logger.warning(f"Saglik raporu dosyası bulunamadı: {rapor_path}")
                    return
                if platform.system() == "Windows":
                    os.startfile(str(resolved_path))
                elif platform.system() == "Darwin":
                    subprocess.run(["open", str(resolved_path)])
                else:
                    subprocess.run(["xdg-open", str(resolved_path)])
                logger.info(f"Saglik raporu acildi (local): {resolved_path}")
            except Exception as e:
                logger.error(f"Saglik raporu acma hatasi: {e}")
                QMessageBox.critical(self, "Hata", f"Rapor açılamadı:\n\n{str(e)}\n\nYol: {rapor_path}")
        elif value == "⚠ Rapor Eksik":
            kayit_no = str(row.get("KayitNo", "")).strip()
            takip_row = next(
                (t for t in self._takip_rows if str(t.get("KayitNo", "")).strip() == kayit_no),
                None,
            )
            if takip_row:
                self._show_rapor_panel(takip_row)

    # -------------------------------------------------------------------------
    # Sinyal ba\u011flantıları
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        self.cmb_hizmet_sinifi.currentTextChanged.connect(self._fill_personel_combo)
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_kaydet.clicked.connect(self._save_record)
        self.btn_temizle.clicked.connect(self._clear_form)
        self.btn_yeni.clicked.connect(self._show_form_panel)
        self.btn_form_kapat.clicked.connect(self._hide_form_panel)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_rapor.clicked.connect(self._pick_report)
        self.search.textChanged.connect(self._apply_filters)
        self.cmb_yil.currentIndexChanged.connect(self._on_yil_changed)
        self.cmb_birim_filter.currentTextChanged.connect(self._apply_filters)
        self.cmb_durum_filter.currentTextChanged.connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._on_select_row)
        self.table.doubleClicked.connect(self._on_table_double_click)
        # Stat kart tıklanabilir filtre (durum filtresi)
        for key in self._exam_keys:
            self._exam_widgets[key]["durum"].currentTextChanged.connect(
                lambda _txt, k=key: self._on_exam_status_changed(k)
            )

    # -------------------------------------------------------------------------
    # Form panel g\öster / gizle
    # -------------------------------------------------------------------------

    def _show_form_panel(self):
        """Yeni kayıt — tüm alanlar boş, exam_section görünür."""
        self._editing_id = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        self.cmb_personel.setCurrentIndex(-1)
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        self.lbl_form_title.setText("Yeni Kayıt")
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self._rapor_only_mode = False
        self.cmb_yil.setEnabled(False)   # Form açıkken yıl değiştirme engeli
        self.form_panel.setVisible(True)

    def _fill_form_from_takip(self, takip_row: dict):
        """Form widget'larını verilen takip kaydıyla doldurur (panel göstermez)."""
        rapor_dosya = str(takip_row.get("RaporDosya", ""))
        self.inp_rapor.setText(os.path.basename(rapor_dosya) if rapor_dosya else "")
        self.inp_not.setText(str(takip_row.get("Notlar", "")))

        personelid = str(takip_row.get("Personelid", "")).strip()
        for i in range(self.cmb_personel.count()):
            info = self.cmb_personel.itemData(i)
            if info and str(info.get("KimlikNo", "")) == personelid:
                self.cmb_personel.setCurrentIndex(i)
                break

        mapping = [
            ("Dermatoloji", "DermatolojiMuayeneTarihi", "DermatolojiDurum"),
            ("Dahiliye",    "DahiliyeMuayeneTarihi",    "DahiliyeDurum"),
            ("Goz",         "GozMuayeneTarihi",         "GozDurum"),
            ("Goruntuleme", "GoruntulemeMuayeneTarihi",  "GoruntulemeDurum"),
        ]
        for key, col_t, col_d in mapping:
            w = self._exam_widgets[key]
            w["durum"].setCurrentText(str(takip_row.get(col_d, "")))
            d = parse_date(takip_row.get(col_t, ""))
            w["tarih"].setDate(QDate(d.year, d.month, d.day) if d else QDate.currentDate())

    def _show_edit_panel(self, takip_row: dict):
        """Mevcut kaydı düzenle — tüm alanlar dolu, exam_section görünür."""
        self._editing_id           = str(takip_row.get("KayitNo", ""))
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self._fill_form_from_takip(takip_row)
        self.lbl_form_title.setText("Kaydı Düzenle")
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self._rapor_only_mode = False
        self.cmb_yil.setEnabled(False)
        self.form_panel.setVisible(True)

    def _show_rapor_panel(self, takip_row: dict):
        """Sadece rapor yükle — exam_section gizli, personel salt-okunur."""
        self._editing_id = str(takip_row.get("KayitNo", ""))
        self._selected_report_path = ""
        self.inp_rapor.clear()

        # Personel adını salt-okunur göster
        ad = str(takip_row.get("AdSoyad", "")).strip()
        pid = str(takip_row.get("Personelid", "")).strip()
        self.lbl_personel_ro.setText(f"{ad} ({pid})")
        self.cmb_personel.setVisible(False)
        self.lbl_personel_ro.setVisible(True)

        self.lbl_form_title.setText("Rapor Yükle")
        self.exam_section.setVisible(False)
        self._rapor_only_mode = True
        self.form_panel.setVisible(True)

    def _hide_form_panel(self):
        self.cmb_yil.setEnabled(True)   # Formu kapatınca yıl seçimi tekrar açık
        self.form_panel.setVisible(False)

    # -------------------------------------------------------------------------
    # Veri yükleme
    # -------------------------------------------------------------------------

    def load_data(self):
        if not self._db:
            return
        # Madde 1: önceki thread hâlâ çalışıyorsa yeni istek yok say
        if hasattr(self, "_loader") and self._loader and self._loader.isRunning():
            return
        self.btn_yenile.setEnabled(False)
        self.lbl_info.setText("Yükleniyor...")
        # Madde 4: yükleme sırasında form paneli etkileşime kapalı
        self.form_panel.setEnabled(False)
        self._loader = _SaglikLoader(self._db)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, result: dict):
        self.btn_yenile.setEnabled(True)
        self.form_panel.setEnabled(True)
        all_personel = result["all_personel"]
        self._personel_rows = all_personel
        self._takip_rows    = result["takip_rows"]

        self._fill_hizmet_sinifi_combo()
        self._fill_personel_combo()

        # Seçili yıl için listeyi oluştur
        self._rebuild_all_rows()
        self._fill_filter_combos()
        self._apply_filters()

    def _rebuild_all_rows(self):
        """Seçili yıla göre tüm aktif personelin muayene satırlarını oluşturur."""
        yil = int(self.cmb_yil.currentData() or date.today().year)
        self._current_yil = yil   # _apply_filters ile senkron
        self._all_rows = self._build_yearly_exam_rows(
            self._takip_rows, self._personel_rows, yil
        )

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        self.form_panel.setEnabled(True)
        self.lbl_info.setText("Yükleme hatası")
        logger.error(f"Saglik takip yukleme hatasi: {msg}")

    def _build_yearly_exam_rows(self, takip_rows, all_personel, yil: int) -> list[dict]:
        """
        Verilen yıl için her aktif personelin bir satırını döner.

        Mantık:
        - Bu yıla ait kayıt varsa → onu kullan.
        - Yoksa → önceki yılın (yil-1) Göz/Dahiliye/Dermatoloji muayenelerinin
          en yeni tarihine +1 yıl ekleyerek SonrakiKontrolTarihi hesapla,
          Durum = "Planlandi" ile sanal satır oluştur.
        """
        # Aktif personel seti
        aktif_set = {
            str(p.get("KimlikNo", "")).strip()
            for p in all_personel
            if str(p.get("Durum", "")).strip().lower() != "pasif"
        }
        personel_by_id = {
            str(p.get("KimlikNo", "")).strip(): p for p in all_personel
        }

        # Takip kayıtlarını personelid + yıl bazında indeksle
        # Aynı (pid, yil) için birden fazla kayıt varsa MuayeneTarihi en yeni olanı tut
        takip_index: dict = {}
        for t in takip_rows:
            pid = str(t.get("Personelid", "")).strip()
            ty  = int(t.get("Yil") or 0)
            if not pid:
                continue
            key = (pid, ty)
            mevcut = takip_index.get(key)
            if mevcut is None:
                takip_index[key] = t
            else:
                # En yeni MuayeneTarihi olan kaydı tut
                t_tarih  = parse_date(t.get("MuayeneTarihi", ""))
                mv_tarih = parse_date(mevcut.get("MuayeneTarihi", ""))
                if t_tarih and (mv_tarih is None or t_tarih > mv_tarih):
                    takip_index[key] = t

        rows = []
        for pid in aktif_set:
            p_data = personel_by_id.get(pid, {})
            ad     = str(p_data.get("AdSoyad", "")).strip()
            birim  = str(p_data.get("GorevYeri", "") or p_data.get("Birim", "")).strip()

            # Bu yıl kaydı var mı?
            takip = takip_index.get((pid, yil))

            if takip:
                rows.append({
                    "KayitNo":              str(takip.get("KayitNo", "")).strip(),
                    "Personelid":           pid,
                    "AdSoyad":              str(takip.get("AdSoyad", "") or ad).strip(),
                    "Birim":                str(takip.get("Birim", "") or birim).strip(),
                    "Yil":                  yil,
                    "MuayeneTarihi":        to_db_date(takip.get("MuayeneTarihi", "")),
                    "SonrakiKontrolTarihi": to_db_date(takip.get("SonrakiKontrolTarihi", "")),
                    "DermatolojiDurum":     str(takip.get("DermatolojiDurum", "")).strip(),
                    "DahiliyeDurum":        str(takip.get("DahiliyeDurum", "")).strip(),
                    "GozDurum":             str(takip.get("GozDurum", "")).strip(),
                    "GoruntulemeDurum":     str(takip.get("GoruntulemeDurum", "")).strip(),
                    "Sonuc":                str(takip.get("Sonuc", "")).strip(),
                    "Durum":                _compute_durum(
                                                str(takip.get("Durum", "")).strip(),
                                                to_db_date(takip.get("SonrakiKontrolTarihi", ""))
                                            ),
                    "_RaporPath":           str(takip.get("_RaporPath", "")).strip(),
                })
            else:
                # Önceki yıllarda hiç kaydı var mı? (yeni personel tespiti)
                has_any_record = any(
                    (pid, y) in takip_index for y in range(yil - 5, yil)
                )

                if has_any_record:
                    # Eski personel: bu yıl henüz muayene olmamış
                    # → önceki yılın en yeni exam tarihine göre SonrakiKontrol hesapla
                    sonraki = self._calc_next_exam_from_prev_year(takip_index, pid, yil)
                    durum   = _compute_durum("Planlandi", sonraki)
                    dermat  = self._prev_exam_durum(takip_index, pid, yil, "DermatolojiDurum")
                    dahil   = self._prev_exam_durum(takip_index, pid, yil, "DahiliyeDurum")
                    goz     = self._prev_exam_durum(takip_index, pid, yil, "GozDurum")
                    gorunt  = self._prev_exam_durum(takip_index, pid, yil, "GoruntulemeDurum")
                else:
                    # Yeni personel: hiç geçmiş kaydı yok
                    # → SonrakiKontrol boş, Durum özel işaretli, exam alanları boş
                    sonraki = ""
                    durum   = "IlkMuayene"
                    dermat = dahil = goz = gorunt = ""

                rows.append({
                    "KayitNo":              "",
                    "Personelid":           pid,
                    "AdSoyad":              ad,
                    "Birim":                birim,
                    "Yil":                  yil,
                    "MuayeneTarihi":        "",
                    "SonrakiKontrolTarihi": sonraki,
                    "Sonuc":                "",
                    "Durum":                durum,
                    "DermatolojiDurum":     dermat,
                    "DahiliyeDurum":        dahil,
                    "GozDurum":             goz,
                    "GoruntulemeDurum":     gorunt,
                    "_RaporPath":           "",
                })
        return rows

    def _prev_exam_durum(
        self, takip_index: dict, pid: str, yil: int, field: str
    ) -> str:
        """Önceki yıla ait tek bir exam durum alanını döner (en fazla 3 yıl geriye)."""
        for gecmis_yil in range(yil - 1, yil - 4, -1):
            prev = takip_index.get((pid, gecmis_yil))
            if prev:
                val = str(prev.get(field, "") or "").strip()
                if val:
                    return val
        return ""

    def _calc_next_exam_from_prev_year(
        self, takip_index: dict, pid: str, yil: int
    ) -> str:
        """
        Önceki kayıtlardan (en fazla 3 yıl geriye) Göz/Dahiliye/Dermatoloji
        muayenelerinin en yenisine kayıt_yılı - muayene_yılı + 1 yıl ekler.
        Yeni sisteme geçmiş personelde de tarih hesaplanabilsin diye geriye bakar.
        Hiç kayıt bulunamazsa boş string döner.
        """
        EXAM_FIELDS = ("GozMuayeneTarihi", "DahiliyeMuayeneTarihi", "DermatolojiMuayeneTarihi")
        LOOKBACK    = 3   # kaç yıl geriye bakılacak

        for gecmis_yil in range(yil - 1, yil - 1 - LOOKBACK, -1):
            prev = takip_index.get((pid, gecmis_yil))
            if not prev:
                continue
            candidates = [parse_date(prev.get(f, "")) for f in EXAM_FIELDS]
            valid = [d for d in candidates if d]
            if not valid:
                continue
            # En yeni muayene tarihine (hedef_yil - muayene_yili + 1) yıl ekle
            latest   = max(valid)
            delta    = (yil - latest.year)   # kaç yıl geçmiş + 1 sonraki kontrol
            yeni_yil = latest.year + delta
            try:
                return latest.replace(year=yeni_yil).isoformat()
            except ValueError:
                return latest.replace(month=2, day=28, year=yeni_yil).isoformat()

        return ""

    def _fill_filter_combos(self):
        curr     = self.cmb_birim_filter.currentText()
        birimler = sorted({
            str(r.get("Birim", "")).strip()
            for r in self._all_rows
            if str(r.get("Birim", "")).strip()
        })
        self.cmb_birim_filter.blockSignals(True)
        self.cmb_birim_filter.clear()
        self.cmb_birim_filter.addItem("Tüm Birimler")
        self.cmb_birim_filter.addItems(birimler)
        idx = self.cmb_birim_filter.findText(curr)
        self.cmb_birim_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_birim_filter.blockSignals(False)


    def _update_stat_cards(self, rows: list):
        """Özet kart sayılarını günceller."""
        counts = {"toplam": len(rows), "gecerli": 0, "gecikmis": 0, "riskli": 0, "planlandi": 0, "ilkmuayene": 0}
        for r in rows:
            d = str(r.get("Durum", "")).strip()
            if d == "Gecerli":
                counts["gecerli"] += 1
            elif d == "Gecikmis":
                counts["gecikmis"] += 1
            elif d == "Riskli":
                counts["riskli"] += 1
            elif d == "Planlandi":
                counts["planlandi"] += 1
            elif d == "IlkMuayene":
                counts["ilkmuayene"] += 1
        for key, lbl in self._stat_cards.items():
            try:
                lbl.setText(str(counts.get(key, 0)))
            except RuntimeError:
                pass

    def _on_yil_changed(self):
        """Yıl combo değişince _all_rows yeniden oluşturulur, sonra filtreler uygulanır.
        Birim/durum/arama değişikliklerinde bu metod çağrılmaz — gereksiz rebuild önlenir."""
        yil = self.cmb_yil.currentData()
        if yil and self._personel_rows:
            yil_int = int(yil)
            self._rebuild_all_rows()
            self._fill_filter_combos()
        self._apply_filters()

    def _apply_filters(self):
        """Sadece birim/durum/arama filtrelerini uygular.
        Yıl rebuild burada yapılmaz — _on_yil_changed sorumluluğundadır."""
        query        = self.search.text().strip().lower()
        birim_filter = self.cmb_birim_filter.currentText()
        durum_filter = self.cmb_durum_filter.currentText()

        out = []
        for row in self._all_rows:
            if birim_filter != "Tüm Birimler" and str(row.get("Birim", "")).strip() != birim_filter:
                continue
            if durum_filter != "Tüm Durumlar" and str(row.get("Durum", "")).strip() != durum_filter:
                continue
            ad    = str(row.get("AdSoyad", "")).lower()
            birim = str(row.get("Birim", "")).lower()
            if query and query not in ad and query not in birim:
                continue
            out.append(row)
        out.sort(key=lambda r: (str(r.get("AdSoyad", "")), str(r.get("MuayeneTarihi", ""))))
        self.model.set_data(out)
        cnt = len(out)
        self.lbl_info.setText(f"{cnt} kayıt gösteriliyor")
        self.lbl_table_count.setText(f"Toplam filtrelenen: {cnt}")
        self._update_stat_cards(out)

    # -------------------------------------------------------------------------
    # Muayene yardımcıları
    # -------------------------------------------------------------------------

    def _on_exam_status_changed(self, key):
        pass

    def _safe_date_from_widget(self, widget) -> str:
        if not widget:
            return ""
        return to_db_date(widget.date().toString("yyyy-MM-dd"))

    def _exam_date_if_set(self, key) -> str:
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return self._safe_date_from_widget(w["tarih"])

    def _compute_summary(self):
        exam_data = []
        for key in self._exam_keys:
            w     = self._exam_widgets[key]
            tarih = self._exam_date_if_set(key)
            durum = str(w["durum"].currentText()).strip()
            exam_data.append((key, tarih, durum))

        dates   = [t for _, t, _ in exam_data if parse_date(t)]
        latest  = max(dates) if dates else ""
        sonraki = ""
        if latest:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            try:
                sonraki = d.replace(year=d.year + 1).isoformat()
            except ValueError:
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        # Sadece Göz, Dermatoloji, Dahiliye Sonuc/Durum hesabını etkiler
        _KRITIK = {"Dermatoloji", "Dahiliye", "Goz"}
        kritik  = [d for k, _, d in exam_data if k in _KRITIK and d]
        tum     = [d for _, _, d in exam_data if d]

        if "Uygun Değil" in kritik:
            # Kritiklerden biri Uygun Değil → Sonuç = Uygun Değil, Durum = Riskli
            sonuc = "Uygun Değil"
            durum = "Riskli"
        elif "Şartlı Uygun" in kritik:
            # Kritiklerden biri Şartlı Uygun → Sonuç = Şartlı Uygun, Durum = Riskli
            sonuc = "Şartlı Uygun"
            durum = "Riskli"
        elif "Uygun" in tum:
            sonuc = "Uygun"
            sonraki_tarih = parse_date(sonraki)
            durum = "Gecikmis" if (sonraki_tarih and sonraki_tarih < date.today()) else "Gecerli"
        else:
            sonuc = ""
            durum = "Planlandi"

        return latest, sonraki, sonuc, durum


    # -------------------------------------------------------------------------
    # Rapor
    # -------------------------------------------------------------------------

    def _pick_report(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Rapor Sec", "", "Dosyalar (*.pdf *.jpg *.jpeg *.png)"
        )
        if path:
            self._selected_report_path = path
            self.inp_rapor.setText(os.path.basename(path))

    def _upload_report(self, tc_no, kayit_no) -> str:
        if not self._selected_report_path:
            return self.inp_rapor.text().strip()
        if not os.path.exists(self._selected_report_path):
            QMessageBox.warning(self, "Uyari", "Secilen rapor dosyasi bulunamadi.")
            return ""
        try:
            ext         = os.path.splitext(self._selected_report_path)[1]
            custom_name = f"{tc_no}_{kayit_no}_SaglikRapor{ext}"
            from core.di import get_dokuman_service
            svc         = get_dokuman_service(self._db)
            sonuc       = svc.upload_and_save(
                file_path    = self._selected_report_path,
                entity_type  = "personel",
                entity_id    = str(tc_no),
                belge_turu   = "Periyodik Sa\u011flık Muayene Raporu",
                folder_name  = "Saglik_Raporlari",
                doc_type     = "Personel_Belge",
                custom_name  = custom_name,
                iliskili_id  = str(kayit_no),
                iliskili_tip = "Personel_Saglik_Takip",
            )
            if not sonuc.get("ok"):
                err = str(sonuc.get("error", "Bilinmeyen yükleme hatası"))
                QMessageBox.warning(self, "Yukleme Hatasi", f"Rapor yüklenemedi:\n{err}")
                return ""
            rapor_ref = str(sonuc.get("drive_link") or sonuc.get("local_path") or "").strip()

            return rapor_ref
        except Exception as exc:
            logger.error(f"Saglik rapor yukleme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Rapor yuklenemedi:\n{exc}")
            return ""

    # -------------------------------------------------------------------------
    # Çift tıklama — düzenle
    # -------------------------------------------------------------------------

    def _on_table_double_click(self, index):
        """Rapor sütunu hariç çift tıklama → kayıt varsa düzenle, yoksa yeni form (personel dolu)."""
        if not index.isValid():
            return
        # Rapor sütununu delegate zaten ele alıyor — buraya düşmez, yine de guard
        rapor_col = next(
            (i for i, (k, *_) in enumerate(TABLE_COLUMNS) if k == "Rapor"), -1
        )
        if index.column() == rapor_col:
            return
        row = self.model.get_row(index.row())
        if not row:
            return
        kayit_no  = str(row.get("KayitNo", "")).strip()

        if kayit_no:
            # Mevcut kayıt → düzenle
            takip_row = next(
                (t for t in self._takip_rows if str(t.get("KayitNo", "")).strip() == kayit_no),
                None,
            )
            if takip_row:
                self._show_edit_panel(takip_row)
        else:
            # Sanal satır (Planlandi/Gecikmis, kayıt yok) → yeni form aç + personeli doldur
            self._show_form_panel()
            pid = str(row.get("Personelid", "")).strip()
            for i in range(self.cmb_personel.count()):
                info = self.cmb_personel.itemData(i)
                if info and str(info.get("KimlikNo", "")).strip() == pid:
                    self.cmb_personel.setCurrentIndex(i)
                    break

    # -------------------------------------------------------------------------
    # Kaydet
    # -------------------------------------------------------------------------

    def _save_record(self):
        if self._rapor_only_mode:
            self._save_rapor_only()
        else:
            self._save_full_record()

    def _save_rapor_only(self):
        """Sadece RaporDosya alanını günceller — diğer alanlara dokunmaz."""
        if not self._editing_id:
            QMessageBox.warning(self, "Hata", "Güncellenecek kayıt bulunamadı.")
            return

        # Hangi personele ait olduğunu mevcut kayıttan al
        takip_row = next(
            (t for t in self._takip_rows
             if str(t.get("KayitNo", "")).strip() == self._editing_id),
            None,
        )
        if not takip_row:
            QMessageBox.warning(self, "Hata", "Kayıt bulunamadı.")
            return

        tc_no = str(takip_row.get("Personelid", "")).strip()
        rapor_link = self._upload_report(tc_no, self._editing_id)
        if self._selected_report_path and not rapor_link:
            return  # yükleme hatası zaten uyarıldı

        if not rapor_link:
            QMessageBox.warning(self, "Eksik", "Lütfen bir rapor dosyası seçin.")
            return

        self._start_save(
            mode="rapor",
            payload={"KayitNo": self._editing_id, "RaporDosya": rapor_link},
        )

    def _save_full_record(self):
        """Tüm muayene alanlarını kaydeder."""
        if self.cmb_personel.currentIndex() < 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lutfen personel seciniz.")
            return

        # Durum seçili ama tarih gelecekteyse uyar
        _ETIKETLER = {"Dermatoloji": "Dermatoloji", "Dahiliye": "Dahiliye",
                      "Goz": "Göz", "Goruntuleme": "Görüntüleme"}
        gelecek = [
            _ETIKETLER.get(key, key)
            for key in self._exam_keys
            if str(self._exam_widgets[key]["durum"].currentText()).strip()
            and (lambda t: t is not None and t > date.today())(
                parse_date(self._exam_widgets[key]["tarih"].date().toString("yyyy-MM-dd"))
            )
        ]
        if gelecek:
            mesaj = "Şu muayene(ler) için tarih bugünden ileri:\n\n" + ", ".join(gelecek) + "\n\nYine de kaydetmek istiyor musunuz?"
            cevap = QMessageBox.question(
                self, "Tarih Kontrolü", mesaj,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if cevap != QMessageBox.StandardButton.Yes:
                return

        personel_data                        = self.cmb_personel.currentData()
        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        kayit_no   = self._editing_id or uuid.uuid4().hex[:12].upper()
        rapor_link = self._upload_report(personel_data.get("KimlikNo", ""), kayit_no)
        if self._selected_report_path and not rapor_link:
            return

        payload = {
            "KayitNo":                  kayit_no,
            "Personelid":               personel_data.get("KimlikNo", ""),
            "AdSoyad":                  personel_data.get("AdSoyad", ""),
            "Birim":                    personel_data.get("Birim", ""),
            "Yil":                      int(self.cmb_yil.currentData() or date.today().year),
            "MuayeneTarihi":            muayene_db,
            "SonrakiKontrolTarihi":     sonraki_db,
            "Sonuc":                    sonuc,
            "Durum":                    durum,
            "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
            "DermatolojiDurum":         str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
            "DahiliyeMuayeneTarihi":    self._exam_date_if_set("Dahiliye"),
            "DahiliyeDurum":            str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
            "GozMuayeneTarihi":         self._exam_date_if_set("Goz"),
            "GozDurum":                 str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
            "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
            "GoruntulemeDurum":         str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
            "RaporDosya":               rapor_link,
            "Notlar":                   self.inp_not.text().strip(),
        }

        self._start_save(mode="full", payload=payload)

    def _start_save(self, mode: str, payload: dict):
        """Kaydetme worker'ını başlatır, UI'ı kilitler."""
        self.btn_kaydet.setEnabled(False)
        self.form_panel.setEnabled(False)
        self._saver = _SaglikSaver(self._db, mode, payload)
        self._saver.finished.connect(self._on_save_finished)
        self._saver.error.connect(self._on_save_error)
        self._saver.start()

    def _on_save_finished(self, result: str):
        self.btn_kaydet.setEnabled(True)
        self.form_panel.setEnabled(True)
        if result == "rapor_ok":
            QMessageBox.information(self, "Başarılı", "Rapor kaydedildi.")
        else:
            QMessageBox.information(self, "Başarılı", "Sağlık takip kaydı kaydedildi.")
        self._clear_form()
        self.load_data()

    def _on_save_error(self, msg: str):
        self.btn_kaydet.setEnabled(True)
        self.form_panel.setEnabled(True)
        logger.error(f"Saglik takip kaydetme hatasi: {msg}")
        QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata oluştu:\n{msg}")

    # -------------------------------------------------------------------------
    # Seçim & Temizlik
    # -------------------------------------------------------------------------

    def _on_select_row(self, *_):
        """Sadece durum çubuğunu günceller. _editing_id'ye dokunmaz."""
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        row = self.model.get_row(idx.row())
        if not row:
            return
        ad    = str(row.get("AdSoyad", "")).strip()
        birim = str(row.get("Birim",   "")).strip()
        durum = str(row.get("Durum",   "")).strip()
        self.lbl_info.setText(f"{ad}  |  {birim}  |  {durum}")

    def _clear_form(self):
        self._editing_id           = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        # Panel bileşenlerini varsayılan görünüme döndür
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self._rapor_only_mode = False
        self.form_panel.setVisible(False)

