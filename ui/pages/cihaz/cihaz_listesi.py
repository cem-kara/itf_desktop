# -*- coding: utf-8 -*-
"""
Cihaz Listesi — Personel Listesi mimarisi ile uyumlu (tema + delegate + lazy-loading).
"""
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel,
    Signal, QRect, QPoint, QSize, QTimer
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QHeaderView,
    QTableView, QComboBox, QLineEdit, QStyledItemDelegate, QStyle
)
from PySide6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QFont
)

from core.logger import logger
from core.di import get_cihaz_service as _get_cihaz_service
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer


# ── Bakım / Kalibrasyon uyarı hesaplamaları ───────────────────────────────────
import calendar as _cal
from datetime import date as _date, datetime as _dt

def _parse_date(val) -> _date | None:
    """ISO tarih string'ini date nesnesine çevirir."""
    if not val:
        return None
    try:
        s = str(val).strip()[:10]
        return _dt.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _bakim_uyari(row: dict) -> str | None:
    """
    Planlanan bakım tarihi geçmiş ya da 30 gün içinde ise uyarı döner.
    Returns: "gecikmiş" | "yaklaşan" | None
    """
    try:
        from core.di import get_cihaz_service as _cs
        pass
    except Exception:
        return None
    # BakimDurum veya PlanlananTarih alanı varsa kullan
    bakim_tarihi = _parse_date(row.get("PlanlananTarih") or row.get("SonBakimTarihi"))
    if not bakim_tarihi:
        return None
    bugun = _date.today()
    delta = (bakim_tarihi - bugun).days
    if delta < 0:
        return "gecikmiş"
    if delta <= 30:
        return "yaklaşan"
    return None

def _kalibrasyon_uyari(row: dict) -> str | None:
    """
    Kalibrasyon bitiş tarihi geçmiş ya da 30 gün içinde ise uyarı döner.
    Returns: "süresi dolmuş" | "yaklaşan" | None
    """
    bitis = _parse_date(row.get("KalibrasyonBitis") or row.get("KalBitis"))
    if not bitis:
        return None
    bugun = _date.today()
    delta = (bitis - bugun).days
    if delta < 0:
        return "süresi dolmuş"
    if delta <= 30:
        return "yaklaşan"
    return None

# ── Durum renk yardımcıları ───────────────────────────────────────────────────
_STATUS_COLORS = {
    "Aktif":      (46,  201, 142, 38),
    "Arızalı":    (232, 85,  85,  38),
    "Bakımda":    (232, 160, 48,  38),
    "Devre Dışı": (232, 85,  85,  25),
}
_STATUS_TEXT = {
    "Aktif":      "#2ec98e",
    "Arızalı":    "#e85555",
    "Bakımda":    "#e8a030",
    "Devre Dışı": "#8fa3b8",
}

def _get_status_color(durum: str) -> tuple:
    return _STATUS_COLORS.get(durum, (143, 163, 184, 38))

def _get_status_text_color(durum: str) -> str:
    return _STATUS_TEXT.get(durum, "#8fa3b8")


# ─── Sütun tanımları ──────────────────────────────────────────
COLUMNS = [
    ("_cihaz",       "Cihaz",          250),
    ("_marka_model", "Marka / Model",  130),
    ("_seri",        "Seri / NDK",     140),
    ("Birim",        "Birim",          160),
    ("DemirbasNo",   "Demirbas No",    120),
    ("Durum",        "Durum",           90),
]
    # ("_actions",     "",               200),
COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}


# ═══════════════════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════════════════

class CihazTableModel(BaseTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(COLUMNS, data, parent)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        key = self._keys[index.column()]

        if role == self.RAW_ROW_ROLE:
            return row

        if role == Qt.ItemDataRole.DisplayRole:
            if key == "_cihaz":
                return f"{row.get('Cihazid', '')} {row.get('CihazTipi', '')}".strip()
            if key == "_marka_model":
                return f"{row.get('Marka', '')} {row.get('Model', '')}".strip()
            if key == "_seri":
                return f"{row.get('SeriNo', '')} {row.get('NDKSeriNo', '')}".strip()
            return str(row.get(key, ""))

        return None

    def set_data(self, data: list):
        super().set_data(data)


# ═══════════════════════════════════════════════════════════
#  DELEGATE
# ═══════════════════════════════════════════════════════════

class CihazDelegate(QStyledItemDelegate):
    """Özel hücre çizimi: iki satır metin + durum pill + aksiyon butonları."""

    BTN_W, BTN_H, BTN_GAP = 54, 26, 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1
        self._btn_rects: dict[tuple, QRect] = {}

    def set_hover_row(self, row: int):
        self._hover_row = row

    def sizeHint(self, option, index):
        return QSize(COLUMNS[index.column()][2], 46)

        def paint(self, painter: QPainter, option, index):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            row = index.row()
            col = index.column()
            key = COLUMNS[col][0]
            rect = option.rect
            is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
            is_hover = (row == self._hover_row)

            if is_sel:
                c = QColor("#0ea5e9")
                c.setAlpha(60)
                painter.fillRect(rect, c)
            elif is_hover:
                c = QColor("#eef0f5")
                c.setAlpha(10)
                painter.fillRect(rect, c)

            raw = index.model().data(index, BaseTableModel.RAW_ROW_ROLE)
            if raw is None:
                painter.restore()
                return

            if key == "_cihaz":
                self._draw_two(painter, rect,
                               str(raw.get("Cihazid", "")),
                               str(raw.get("CihazTipi", "") or "—"),
                               mono_top=True)
            elif key == "_marka_model":
                self._draw_two(painter, rect,
                               str(raw.get("Marka", "") or "—"),
                               str(raw.get("Model", "") or "—"))
            elif key == "_seri":
                self._draw_two(painter, rect,
                               str(raw.get("SeriNo", "") or "—"),
                               str(raw.get("NDKSeriNo", "") or "—"),
                               mono_top=True)
            elif key == "Birim":
                self._draw_two(painter, rect,
                               str(raw.get("AnaBilimDali", "") or "—"),
                               str(raw.get("Birim", "") or "—"))
            elif key == "DemirbasNo":
                self._draw_mono(painter, rect, str(raw.get("DemirbasNo", "") or "—"))
            elif key == "Durum":
                self._draw_status_pill(painter, rect, str(raw.get("Durum", "") or "—"))
                # Bakım uyarısı rozeti
                bakim_u = _bakim_uyari(raw)
                kal_u   = _kalibrasyon_uyari(raw)
                if bakim_u or kal_u:
                    self._draw_uyari_rozet(painter, rect, bakim_u, kal_u)


    # ── Çizim yardımcıları ───────────────────────────────

    def _draw_two(self, p, rect, top, bottom, mono_top=False):
        pad = 8
        r1 = QRect(rect.x() + pad, rect.y() + 4, rect.width() - pad * 2, 17)
        r2 = QRect(rect.x() + pad, rect.y() + 21, rect.width() - pad * 2, 14)
        p.setFont(QFont("Courier New", 10) if mono_top else QFont("Segoe UI", 11, QFont.Weight.Medium))
        p.setPen(QColor("#eef0f5"))
        p.drawText(r1, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   p.fontMetrics().elidedText(top, Qt.TextElideMode.ElideRight, r1.width()))
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor("#8fa3b8"))
        p.drawText(r2, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   p.fontMetrics().elidedText(bottom, Qt.TextElideMode.ElideRight, r2.width()))

    def _draw_mono(self, p, rect, text):
        pad = 8
        r = QRect(rect.x() + pad, rect.y(), rect.width() - pad * 2, rect.height())
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor("#eef0f5"))
        p.drawText(r, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   p.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, r.width()))

    def _draw_status_pill(self, p, rect, text):
        text = text or "—"
        r = QRect(rect.x() + 8, rect.y() + 9, rect.width() - 16, 22)
        bg = _get_status_color(text)
        fg = _get_status_text_color(text)
        br, bgc, bb, ba = bg
        p.setBrush(QBrush(QColor(br, bgc, bb, ba)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 11, 11)
        p.setPen(QColor(fg))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_uyari_rozet(self, p, rect, bakim_u: str | None, kal_u: str | None):
        """
        Durum hücresinin sağ üst köşesine küçük uyarı rozeti çizer.
        Kırmızı = gecikmiş/süresi dolmuş, Turuncu = yaklaşan.
        """
        # Renk önceliği: gecikmiş > yaklaşan
        renk_str = None
        tooltip_parts = []
        if bakim_u == "gecikmiş":
            renk_str = "#ef4444"
            tooltip_parts.append("Bakım gecikmiş")
        elif kal_u == "süresi dolmuş":
            renk_str = "#ef4444"
            tooltip_parts.append("Kalibrasyon süresi dolmuş")
        elif bakim_u == "yaklaşan":
            renk_str = "#f59e0b"
            tooltip_parts.append("Bakım yaklaşıyor")
        elif kal_u == "yaklaşan":
            renk_str = "#f59e0b"
            tooltip_parts.append("Kalibrasyon bitiyor")

        if not renk_str:
            return

        # Küçük daire rozet — sağ üst köşe
        dot_x = rect.right() - 10
        dot_y = rect.top() + 6
        dot_r = 5
        p.setBrush(QBrush(QColor(renk_str)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(dot_x - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2)

    
# ═══════════════════════════════════════════════════════════
#  SAYFA
# ═══════════════════════════════════════════════════════════

class CihazListesiPage(QWidget):

    detay_requested = Signal(dict)
    edit_requested = Signal(dict)
    periodic_maintenance_requested = Signal(dict)
    add_requested = Signal()

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self.style().unpolish(self)
        self.style().polish(self)
        self._db = db
        self._action_guard = action_guard
        self._all_data = []
        self._active_filter = "Tümü"
        self._filter_btns = {}
        self._hover_row = -1

        # Arama debounce timer
        self._search_timer = QTimer()
        self._search_timer.setInterval(300)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._execute_search)
        self._last_search_text = ""

        # Lazy-loading state
        self._page_size = 100
        self._current_page = 1
        self._total_count = 0
        self._is_loading = False

        self._setup_ui()
        self._connect_signals()

    # ─── UI Kurulum ──────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self._build_toolbar())
        main.addWidget(self._build_subtoolbar())
        main.addWidget(self._build_table(), 1)
        main.addWidget(self._build_footer())

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setProperty("bg-role", "panel")
        frame.setProperty("border-role", "border")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        title = QLabel("Cihaz Listesi")
        title.setProperty("color-role", "primary")
        title.setProperty("bg-role", "panel")
        title.style().unpolish(title)
        title.style().polish(title)
        lay.addWidget(title)

        lay.addWidget(self._sep())

        for lbl in ("Aktif", "Bakımda", "Arızalı", "Tümü"):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.setMinimumWidth(90)

            bg = _get_status_color(lbl)
            text_color = _get_status_text_color(lbl)
            r, g, b, a = bg
            btn_style = f"""
                QPushButton {{
                    background: rgba({r}, {g}, {b}, {a});
                    color: {text_color};
                    border: 1px solid rgba({r}, {g}, {b}, {min(a + 80, 255)});
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: rgba({r}, {g}, {b}, {min(a + 30, 255)});
                    border: 1px solid rgba({r}, {g}, {b}, {min(a + 100, 255)});
                }}
                QPushButton:checked {{
                    background: rgba({r}, {g}, {b}, {min(a + 60, 255)});
                    border: 1px solid {text_color};
                    font-weight: 600;
                }}
            """
            btn.setStyleSheet(btn_style)
            if lbl == self._active_filter:
                btn.setChecked(True)
            self._filter_btns[lbl] = btn
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cihaz, marka, model, seri ara…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(220)
        # setStyleSheet kaldırıldı: search — global QSS kuralı geçerli
        lay.addWidget(self.search_input)

        lay.addStretch()

        self.btn_yenile = QPushButton()
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.style().unpolish(self.btn_yenile)
        self.btn_yenile.style().polish(self.btn_yenile)
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color="secondary", size=16)
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton(" Yeni Cihaz")
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.style().unpolish(self.btn_yeni)
        self.btn_yeni.style().polish(self.btn_yeni)
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color="primary", size=16)
        self.btn_yeni.setIconSize(QSize(16, 16))
        
        # IP-06: Aksiyon bazlı yetki kontrolü
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni, "cihaz.write")
        
        lay.addWidget(self.btn_yeni)

        return frame

    def _build_subtoolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "page")
        frame.setProperty("border-role", "border")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        lbl = QLabel("FİLTRE:")
        lbl.setProperty("color-role", "disabled")
        lbl.setProperty("bg-role", "panel")
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        lay.addWidget(lbl)

        lbl_abd = QLabel("Birim:")
        lbl_abd.setProperty("color-role", "disabled")
        lbl_abd.setProperty("bg-role", "panel")
        lbl_abd.style().unpolish(lbl_abd)
        lbl_abd.style().polish(lbl_abd)
        lay.addWidget(lbl_abd)

        self.cmb_abd = QComboBox()
        self.cmb_abd.addItem("Tümü")
        self.cmb_abd.setFixedWidth(160)
        # setStyleSheet kaldırıldı: combo — global QSS kuralı geçerli
        lay.addWidget(self.cmb_abd)

        lbl_kaynak = QLabel("Kaynak:")
        lbl_kaynak.setProperty("color-role", "disabled")
        lbl_kaynak.setProperty("bg-role", "panel")
        lbl_kaynak.style().unpolish(lbl_kaynak)
        lbl_kaynak.style().polish(lbl_kaynak)
        lay.addWidget(lbl_kaynak)

        self.cmb_kaynak = QComboBox()
        self.cmb_kaynak.addItem("Tümü")
        self.cmb_kaynak.setFixedWidth(160)
        # setStyleSheet kaldırıldı: combo — global QSS kuralı geçerli
        lay.addWidget(self.cmb_kaynak)

        lay.addStretch()

        return frame

    def _build_table(self) -> QTableView:
        self._model = CihazTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        # setStyleSheet kaldırıldı: table — global QSS kuralı geçerli
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setDefaultSectionSize(46)

        self._delegate = CihazDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        self._model.setup_columns(
            self.table,
            stretch_keys=["_marka_model", "Birim"]
)
        return self.table

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setProperty("bg-role", "panel")
        frame.setProperty("border-role", "border")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)

        self.lbl_info = QLabel("0 kayıt")
        self.lbl_info.setProperty("style-role", "footer")
        self.lbl_info.style().unpolish(self.lbl_info)
        self.lbl_info.style().polish(self.lbl_info)
        lay.addWidget(self.lbl_info)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setProperty("style-role", "footer")
        self.lbl_detail.style().unpolish(self.lbl_detail)
        self.lbl_detail.style().polish(self.lbl_detail)
        lay.addWidget(self.lbl_detail)

        lay.addStretch()

        self.progress = QProgressBar()
        self.progress.setFixedSize(140, 4)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        # setStyleSheet kaldırıldı: progress — global QSS kuralı geçerli
        lay.addWidget(self.progress)

        self.btn_load_more = QPushButton("Daha Fazla Yükle")
        self.btn_load_more.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_load_more.setFixedHeight(28)
        self.btn_load_more.setProperty("style-role", "action")
        self.btn_load_more.style().unpolish(self.btn_load_more)
        self.btn_load_more.style().polish(self.btn_load_more)
        self.btn_load_more.setVisible(False)
        lay.addWidget(self.btn_load_more)

        return frame

    # ─── Sinyaller ───────────────────────────────────────

    def _connect_signals(self):
        for text, btn in self._filter_btns.items():
            btn.clicked.connect(lambda _, t=text: self._on_filter_click(t))
        self.search_input.textChanged.connect(self._on_search)
        self.cmb_abd.currentTextChanged.connect(lambda _: self._apply_filters())
        self.cmb_kaynak.currentTextChanged.connect(lambda _: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni.clicked.connect(self.add_requested.emit)
        self.btn_load_more.clicked.connect(self._load_more_data)
        self.table.doubleClicked.connect(self._on_double_click)


    # ─── Veri Yükleme ────────────────────────────────────

    def load_data(self):
        if not self._db:
            logger.warning("Cihaz listesi: DB yok")
            return
        try:
            self._current_page = 1
            self._total_count = 0
            self._all_data = []

            svc = _get_cihaz_service(self._db)
            page_data, total = svc.get_cihaz_paginated(
                page=self._current_page,
                page_size=self._page_size
            ).veri or ([], 0 )
            # Bakım ve kalibrasyon tarihlerini zenginleştir (uyarı rozetleri için)
            try:
                tum_bakimlar  = svc.get_tum_bakimlar().veri or []
                tum_kal       = svc.get_kalibrasyon_listesi(cihaz_id=None).veri if hasattr(svc, 'get_kalibrasyon_listesi') else []
                # Son planlanan bakım tarihi
                bakim_map: dict[str, str] = {}
                for b in tum_bakimlar:
                    cid = str(b.get("Cihazid", "")).strip()
                    if b.get("PlanlananTarih") and b.get("Durum", "") != "Yapıldı":
                        if cid not in bakim_map or b["PlanlananTarih"] < bakim_map[cid]:
                            bakim_map[cid] = str(b["PlanlananTarih"])
                # Son kalibrasyon bitiş tarihi
                kal_map: dict[str, str] = {}
                for k in tum_kal:
                    cid = str(k.get("Cihazid", "")).strip()
                    if k.get("BitisTarihi"):
                        if cid not in kal_map or k["BitisTarihi"] > kal_map[cid]:
                            kal_map[cid] = str(k["BitisTarihi"])
                # Satırlara ekle
                for row in page_data:
                    cid = str(row.get("Cihazid", "")).strip()
                    if cid in bakim_map:
                        row["PlanlananTarih"] = bakim_map[cid]
                    if cid in kal_map:
                        row["KalibrasyonBitis"] = kal_map[cid]
            except Exception as e:
                logger.debug(f"Bakım/kalibrasyon zenginleştirme: {e}")
            self._all_data = page_data
            self._total_count = total

            self._model.set_data(self._all_data)
            self._populate_combos(svc)
            self._apply_filters()
            self._update_load_more_button()
        except Exception as e:
            logger.error(f"Cihaz yükleme: {e}")

    def _load_more_data(self):
        if self._is_loading or not self._db:
            return
        try:
            self._is_loading = True
            self.btn_load_more.setEnabled(False)
            self.progress.setVisible(True)

            svc = _get_cihaz_service(self._db)
            self._current_page += 1
            page_data, _ = svc.get_cihaz_paginated(
                page=self._current_page,
                page_size=self._page_size
            ).veri or []

            if not page_data:
                self._current_page -= 1
            else:
                self._all_data.extend(page_data)
                self._model.append_rows(page_data)   # beginInsertRows → verimli
                self._apply_filters()

            self._update_load_more_button()
        except Exception as e:
            logger.error(f"Daha fazla cihaz yükleme: {e}")
        finally:
            self._is_loading = False
            self.btn_load_more.setEnabled(True)
            self.progress.setVisible(False)

    # ─── Filtreleme ──────────────────────────────────────

    def _on_filter_click(self, text: str):
        self._active_filter = text
        for t, btn in self._filter_btns.items():
            btn.setChecked(t == text)
        self._apply_filters()

    def _on_search(self, text: str):
        self._last_search_text = text
        self._search_timer.stop()
        self._search_timer.start()

    def _execute_search(self):
        self._proxy.setFilterFixedString(self._last_search_text)
        self._update_count()

    def _apply_filters(self):
        filtered = self._all_data

        if self._active_filter != "Tümü":
            filtered = [r for r in filtered
                        if str(r.get("Durum", "")).strip() == self._active_filter]

        abd = self.cmb_abd.currentText()
        if abd and abd != "Tümü":
            filtered = [r for r in filtered
                        if str(r.get("AnaBilimDali", "")).strip() == abd]

        kaynak = self.cmb_kaynak.currentText()
        if kaynak and kaynak != "Tümü":
            filtered = [r for r in filtered
                        if str(r.get("Kaynak", "")).strip() == kaynak]

        self._model.set_data(filtered)
        self._update_count()

    def _populate_combos(self, svc):
        sabitler = []
        try:
            sabitler = svc.get_sabitler().veri or []
        except Exception as e:
            logger.debug(f"Sabitler okunamadi: {e}")

        abd_list = sorted({
            str(r.get("MenuEleman", "")).strip()
            for r in sabitler
            if r.get("Kod") == "AnaBilimDali" and str(r.get("MenuEleman", "")).strip()
        })
        kaynak_list = sorted({
            str(r.get("MenuEleman", "")).strip()
            for r in sabitler
            if r.get("Kod") == "Kaynak" and str(r.get("MenuEleman", "")).strip()
        })

        if not abd_list:
            abd_list = sorted({
                str(r.get("AnaBilimDali", "")).strip()
                for r in self._all_data
                if str(r.get("AnaBilimDali", "")).strip()
            })
        if not kaynak_list:
            kaynak_list = sorted({
                str(r.get("Kaynak", "")).strip()
                for r in self._all_data
                if str(r.get("Kaynak", "")).strip()
            })

        self.cmb_abd.blockSignals(True)
        self.cmb_abd.clear()
        self.cmb_abd.addItem("Tümü")
        self.cmb_abd.addItems(abd_list)
        self.cmb_abd.blockSignals(False)

        self.cmb_kaynak.blockSignals(True)
        self.cmb_kaynak.clear()
        self.cmb_kaynak.addItem("Tümü")
        self.cmb_kaynak.addItems(kaynak_list)
        self.cmb_kaynak.blockSignals(False)

    def _update_count(self):
        total = self._model.rowCount()
        self.lbl_info.setText(f"{total} kayıt")

    def _update_load_more_button(self):
        loaded = len(self._all_data)
        has_more = loaded < self._total_count
        self.btn_load_more.setVisible(has_more)
        if has_more:
            self.btn_load_more.setText(f"Daha Fazla Yükle ({loaded}/{self._total_count})")



    def _on_double_click(self, idx):
        if not idx.isValid():
            return
        src = self._proxy.mapToSource(idx)
        row_data = self._model.get_row(src.row())
        if row_data:
            self.detay_requested.emit(row_data)

    # ─── UI yardımcıları ─────────────────────────────────

    @staticmethod
    def _sep():
        f = QFrame()
        f.setFixedSize(1, 22)
        f.setProperty("bg-role", "separator")
        f.style().unpolish(f)
        f.style().polish(f)
        return f
