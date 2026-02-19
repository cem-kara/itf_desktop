# -*- coding: utf-8 -*-
"""
Cihaz Listesi — v2 (Yeniden Tasarım)
──────────────────────────────────────
• 2 katlı toolbar: üstte durum pill (Aktif|Arızalı|Bakımda|Tümü) + arama
• Alt toolbar: tip / birim / kaynak combo + excel
• QAbstractTableModel + QSortFilterProxyModel (performanslı)
• Custom delegate: cihaz tipi ikonu, Marka+Model, Tip+Birim,
  kalibrasyon son tarih bar, durum pill, hover aksiyonları
• ArizaEklePanel inline sağ panel (popup yok, orijinal panel korundu)
• Tüm renkler DarkTheme / STYLES üzerinden — hardcoded renk yok
"""
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel,
    Signal, QRect, QPoint, QSize,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QHeaderView,
    QTableView, QComboBox, QLineEdit, QMenu, QMessageBox,
    QStyledItemDelegate, QStyle,
)
from PySide6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QFont, QFontMetrics,
)
from datetime import date

from core.logger import logger
from core.date_utils import parse_date
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

# ─── Sütun tanımları ──────────────────────────────────────────
COLUMNS = [
    ("_icon",        "",                  36),
    ("_marka_model", "Cihaz",            190),
    ("_tip_birim",   "Tip · Birim",      170),
    ("SeriNo",       "Seri No",          130),
    ("_kalibrasyon", "Kalibrasyon",      110),
    ("Durum",        "Durum",             80),
    ("_actions",     "",                  84),
]
COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}

# Cihaz tipi → unicode sembol (sade, font bağımsız)
TIP_SIMGE = {
    "Röntgen": "R", "MR": "M", "CT": "C", "USG": "U",
    "EKG": "E", "Monitör": "V", "Enjektör": "J",
    "Bilgisayar": "B", "Yazıcı": "Y",
}

# Cihaz durumu renk tablosu (fg_hex, r, g, b, alpha)
CIHAZ_DURUM_RENK = {
    "Aktif":         ("#4ade80", 34,  197, 94,  45),
    "Arızalı":       ("#f87171", 239, 68,  68,  45),
    "Bakımda":       ("#facc15", 234, 179, 8,   45),
    "Pasif":         ("#8b8fa3", 100, 100, 120, 40),
    "Kalibrasyonda": ("#a78bfa", 167, 139, 250, 45),
}


def _kalibrasyon_info(row: dict) -> tuple:
    """(pct 0-1, metin, color_hex). pct=-1 => veri yok."""
    s = str(row.get("KalibrasyonSonTarih", "") or "")
    if not s:
        return -1.0, "Tarih yok", C.TEXT_DISABLED
    son = parse_date(s)
    if not son:
        return -1.0, "Tarih yok", C.TEXT_DISABLED
    delta = (son - date.today()).days
    pct   = max(0.0, min(1.0, 1.0 - (365 - max(0, delta)) / 365))
    if delta < 0:
        return pct, f"{abs(delta)} gün geçti", C.STATUS_ERROR
    if delta <= 30:
        return pct, f"{delta} gün kaldı",    C.STATUS_WARNING
    return pct, f"{delta} gün kaldı",        C.STATUS_SUCCESS


# ═══════════════════════════════════════════════════════════
#  MODEL
# ═══════════════════════════════════════════════════════════

class CihazTableModel(QAbstractTableModel):

    RAW_ROW_ROLE  = Qt.UserRole + 1
    KAL_INFO_ROLE = Qt.UserRole + 2   # (pct, text, color_hex)

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data: list[dict] = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        if role == Qt.SizeHintRole and orientation == Qt.Horizontal:
            return QSize(COLUMNS[section][2], 28)
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = self._keys[index.column()]

        if role == self.RAW_ROW_ROLE:
            return row
        if role == self.KAL_INFO_ROLE and col == "_kalibrasyon":
            return _kalibrasyon_info(row)
        if role == Qt.DisplayRole:
            if col in ("_icon", "_marka_model", "_tip_birim",
                       "_kalibrasyon", "_actions"):
                return ""
            if col == "SeriNo": return str(row.get("SeriNo", "") or "—")
            if col == "Durum":  return str(row.get("Durum", ""))
            return str(row.get(col, ""))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if col in ("Durum", "_icon") else Qt.AlignVCenter | Qt.AlignLeft
        return None

    def get_row(self, idx: int):
        return self._data[idx] if 0 <= idx < len(self._data) else None

    def set_data(self, data: list):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


# ═══════════════════════════════════════════════════════════
#  DELEGATE
# ═══════════════════════════════════════════════════════════

class CihazDelegate(QStyledItemDelegate):

    BTN_W, BTN_H, BTN_GAP = 36, 22, 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1
        self._btn_rects: dict[tuple, QRect] = {}

    def set_hover_row(self, row: int):
        self._hover_row = row

    def sizeHint(self, option, index):
        return QSize(COLUMNS[index.column()][2], 40)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        row      = index.row()
        col      = index.column()
        key      = COLUMNS[col][0]
        rect     = option.rect
        is_sel   = bool(option.state & QStyle.State_Selected)
        is_hover = (row == self._hover_row)

        if is_sel:
            painter.fillRect(rect, QColor(29, 117, 254, 60))
        elif is_hover:
            painter.fillRect(rect, QColor(255, 255, 255, 10))

        raw = index.model().data(index, CihazTableModel.RAW_ROW_ROLE)
        if raw is None:
            painter.restore()
            return

        if   key == "_icon":        self._draw_icon(painter, rect, raw)
        elif key == "_marka_model": self._draw_marka_model(painter, rect, raw)
        elif key == "_tip_birim":   self._draw_two(painter, rect,
                                        str(raw.get("CihazTipi","") or "—"),
                                        str(raw.get("Birim","") or ""))
        elif key == "SeriNo":       self._draw_mono(painter, rect, str(raw.get("SeriNo","") or "—"))
        elif key == "_kalibrasyon":
            info = index.model().data(index, CihazTableModel.KAL_INFO_ROLE)
            if info:
                self._draw_kal_bar(painter, rect, *info)
        elif key == "Durum":        self._draw_status_pill(painter, rect, str(raw.get("Durum","")))
        elif key == "_actions":
            if is_hover or is_sel:
                self._draw_action_btns(painter, rect, row)
            else:
                for k in list(self._btn_rects):
                    if k[0] == row:
                        del self._btn_rects[k]

        painter.restore()

    # ── Çizim yardımcıları ────────────────────────────────

    def _draw_icon(self, p, rect, row):
        tip   = str(row.get("CihazTipi", "") or "")
        harf  = TIP_SIMGE.get(tip, tip[:1].upper() if tip else "?")
        cx, cy, r = rect.center().x(), rect.center().y(), 13
        hue = (sum(ord(c) for c in tip) * 47) % 360 if tip else 200
        p.setBrush(QBrush(QColor.fromHsl(hue, 80, 48)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.setFont(QFont("", 8, QFont.Bold))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(rect, Qt.AlignCenter, harf)

    def _draw_marka_model(self, p, rect, row):
        mm  = f"{row.get('Marka','') or ''} {row.get('Model','') or ''}".strip() or "—"
        cid = str(row.get("Cihazid","") or "")
        self._draw_two(p, rect, mm, cid)

    def _draw_two(self, p, rect, top, bottom):
        pad = 8
        r1  = QRect(rect.x()+pad, rect.y()+4,  rect.width()-pad*2, 17)
        r2  = QRect(rect.x()+pad, rect.y()+21, rect.width()-pad*2, 14)
        p.setFont(QFont("", 9, QFont.Medium))
        p.setPen(QColor(C.TEXT_SECONDARY))
        p.drawText(r1, Qt.AlignVCenter|Qt.AlignLeft,
                   p.fontMetrics().elidedText(top,    Qt.ElideRight, r1.width()))
        p.setFont(QFont("", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        p.drawText(r2, Qt.AlignVCenter|Qt.AlignLeft,
                   p.fontMetrics().elidedText(bottom, Qt.ElideRight, r2.width()))

    def _draw_mono(self, p, rect, text):
        p.setFont(QFont("Courier New", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        r = QRect(rect.x()+8, rect.y(), rect.width()-16, rect.height())
        p.drawText(r, Qt.AlignVCenter|Qt.AlignLeft, text)

    def _draw_kal_bar(self, p, rect, pct: float, text: str, color_hex: str):
        pad = 8
        bw  = rect.width() - pad*2
        bx  = rect.x() + pad
        ty  = rect.y() + 5
        by  = rect.y() + rect.height() - 10

        p.setFont(QFont("Courier New", 8))
        p.setPen(QColor(color_hex))
        p.drawText(QRect(bx, ty, bw, 14), Qt.AlignVCenter|Qt.AlignLeft, text)

        if pct >= 0:
            p.setBrush(QBrush(QColor(C.BG_TERTIARY)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(bx, by, bw, 4, 2, 2)
            p.setBrush(QBrush(QColor(color_hex)))
            p.drawRoundedRect(bx, by, max(3, int(bw*pct)), 4, 2, 2)

    def _draw_status_pill(self, p, rect, durum: str):
        info = CIHAZ_DURUM_RENK.get(durum, ("#8b8fa3", 100, 100, 120, 40))
        fg, rv, gv, bv, av = info
        font = QFont("", 8, QFont.Medium)
        p.setFont(font)
        fm   = QFontMetrics(font)
        pw, ph = fm.horizontalAdvance(durum) + 20, fm.height() + 8
        px   = rect.center().x() - pw//2
        py   = rect.center().y() - ph//2
        p.setBrush(QBrush(QColor(rv, gv, bv, av)))
        p.setPen(QPen(QColor(rv, gv, bv, min(av+80, 255)), 1))
        p.drawRoundedRect(px, py, pw, ph, 4, 4)
        p.setPen(QColor(fg))
        p.drawText(QRect(px, py, pw, ph), Qt.AlignCenter, durum)

    def _draw_action_btns(self, p, rect, row):
        x = rect.x() + 4
        y = rect.center().y() - self.BTN_H//2
        for i, lbl in enumerate(["Detay", "Arıza"]):
            bx = x + i*(self.BTN_W + self.BTN_GAP)
            br = QRect(bx, y, self.BTN_W, self.BTN_H)
            self._btn_rects[(row, i)] = br
            p.setBrush(QBrush(QColor(255, 255, 255, 15)))
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.drawRoundedRect(br, 4, 4)
            p.setFont(QFont("", 8))
            p.setPen(QColor(C.TEXT_SECONDARY))
            p.drawText(br, Qt.AlignCenter, lbl)

    def get_action_at(self, row: int, pos: QPoint):
        for (r, i), rect in self._btn_rects.items():
            if r == row and rect.contains(pos):
                return ["detay", "ariza"][i]
        return None


# ═══════════════════════════════════════════════════════════
#  CIHAZ LİSTESİ SAYFASI
# ═══════════════════════════════════════════════════════════

class CihazListesiPage(QWidget):

    detay_requested                = Signal(dict)
    add_requested                  = Signal()
    periodic_maintenance_requested = Signal(dict)
    edit_requested                 = Signal(dict)   # geriye dönük uyumluluk

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        self._db            = db
        self._all_data      = []
        self._active_filter = "Aktif"
        self._filter_btns   = {}
        self._setup_ui()
        self._connect_signals()
        self.detay_requested.connect(self.edit_requested.emit)

    # ── UI ───────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Yatay gövde: sol (liste) + sağ (arıza panel, gizli)
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        ll.addWidget(self._build_toolbar())
        ll.addWidget(self._build_subtoolbar())
        ll.addWidget(self._build_table(), 1)
        ll.addWidget(self._build_footer())
        body_lay.addWidget(left, 1)

        self._build_ariza_panel(body_lay)
        root.addWidget(body, 1)

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(48)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        title = QLabel("Cihaz Yönetimi")
        title.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        lay.addWidget(title)
        lay.addWidget(self._sep())

        for lbl in ("Aktif", "Arızalı", "Bakımda", "Tümü"):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.setStyleSheet(STYLES["filter_btn_all" if lbl == "Tümü" else "filter_btn"])
            btn.setChecked(lbl == self._active_filter)
            self._filter_btns[lbl] = btn
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Marka, model, seri no…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet(STYLES["search"])
        lay.addWidget(self.search_input)

        lay.addStretch()

        self.btn_yenile = QPushButton("⟳")
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("+ Yeni Cihaz")
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.setFixedHeight(28)
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        lay.addWidget(self.btn_yeni)
        return frame

    def _build_subtoolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_PRIMARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        lay.addWidget(QLabel("FİLTRE:", styleSheet=f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;"))

        self.cmb_tip = QComboBox()
        self.cmb_tip.addItem("Tüm Tipler")
        self.cmb_tip.setFixedSize(150, 26)
        self.cmb_tip.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_tip)

        self.cmb_birim = QComboBox()
        self.cmb_birim.addItem("Tüm Birimler")
        self.cmb_birim.setFixedSize(160, 26)
        self.cmb_birim.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_birim)

        self.cmb_kaynak = QComboBox()
        self.cmb_kaynak.addItem("Tüm Kaynaklar")
        self.cmb_kaynak.setFixedSize(140, 26)
        self.cmb_kaynak.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_kaynak)

        lay.addStretch()

        self.btn_excel = QPushButton("↓ Excel")
        self.btn_excel.setFixedHeight(26)
        self.btn_excel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_excel.setStyleSheet(STYLES["excel_btn"])
        lay.addWidget(self.btn_excel)
        return frame

    def _build_table(self) -> QTableView:
        self._model = CihazTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setStyleSheet(STYLES["table"])
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().setDefaultSectionSize(40)

        self._delegate = CihazDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        hdr = self.table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            hdr.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        hdr.setSectionResizeMode(COL_IDX["_marka_model"], QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_IDX["_tip_birim"],   QHeaderView.Stretch)
        return self.table

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(34)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-top: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)
        self.lbl_info   = QLabel("0 cihaz")
        self.lbl_detail = QLabel("")
        for l in (self.lbl_info, self.lbl_detail):
            l.setStyleSheet(STYLES["footer_label"])
            lay.addWidget(l)
        lay.addStretch()
        return frame

    def _build_ariza_panel(self, parent_layout):
        from ui.pages.cihaz.ariza_ekle import ArizaEklePanel
        self.ariza_panel = ArizaEklePanel(db=self._db, parent=self)
        self.ariza_panel.setVisible(False)
        self.ariza_panel.setFixedWidth(340)
        self.ariza_panel.setStyleSheet(
            f"background-color:{C.BG_SECONDARY}; border-left:1px solid {C.BORDER_PRIMARY};"
        )
        self.ariza_panel.kapanma_istegi.connect(self._close_ariza_panel)
        self.ariza_panel.kayit_basarili_sinyali.connect(self._on_ariza_saved)
        parent_layout.addWidget(self.ariza_panel)

    # ── Sinyaller ────────────────────────────────────────

    def _connect_signals(self):
        for text, btn in self._filter_btns.items():
            btn.clicked.connect(lambda _, t=text: self._on_filter_click(t))
        self.search_input.textChanged.connect(self._on_search)
        self.cmb_tip.currentTextChanged.connect(lambda _: self._apply_filters())
        self.cmb_birim.currentTextChanged.connect(lambda _: self._apply_filters())
        self.cmb_kaynak.currentTextChanged.connect(lambda _: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni.clicked.connect(self.add_requested.emit)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.mouseMoveEvent  = self._tbl_mouse_move
        self.table.mousePressEvent = self._tbl_mouse_press

    # ── Veri ─────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_registry
            self._all_data = get_registry(self._db).get("Cihazlar").get_all()
            self._populate_combos()
            self._apply_filters()
        except Exception as e:
            logger.error(f"Cihaz listesi yükleme: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenemedi:\n{e}")

    def _populate_combos(self):
        for cmb, key, default in [
            (self.cmb_tip,    "CihazTipi", "Tüm Tipler"),
            (self.cmb_birim,  "Birim",     "Tüm Birimler"),
            (self.cmb_kaynak, "Kaynak",    "Tüm Kaynaklar"),
        ]:
            items = sorted({str(r.get(key,"")).strip() for r in self._all_data if r.get(key,"").strip()})
            cur   = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear(); cmb.addItem(default); cmb.addItems(items)
            idx = cmb.findText(cur)
            cmb.setCurrentIndex(idx if idx >= 0 else 0)
            cmb.blockSignals(False)

    # ── Filtreleme ───────────────────────────────────────

    def _on_filter_click(self, text: str):
        self._active_filter = text
        for t, btn in self._filter_btns.items():
            btn.setChecked(t == text)
        self._apply_filters()

    def _on_search(self, text: str):
        self._proxy.setFilterFixedString(text)
        self._update_count()

    def _apply_filters(self):
        filtered = self._all_data
        if self._active_filter != "Tümü":
            filtered = [r for r in filtered
                        if str(r.get("Durum","")).strip() == self._active_filter]
        for cmb, key, default in [
            (self.cmb_tip,    "CihazTipi", "Tüm Tipler"),
            (self.cmb_birim,  "Birim",     "Tüm Birimler"),
            (self.cmb_kaynak, "Kaynak",    "Tüm Kaynaklar"),
        ]:
            val = cmb.currentText()
            if val and val != default:
                filtered = [r for r in filtered if str(r.get(key,"")).strip() == val]
        self._model.set_data(filtered)
        self._update_count()

    def _update_count(self):
        total   = len(self._all_data)
        visible = self._proxy.rowCount()
        counts  = {k: sum(1 for r in self._all_data if str(r.get("Durum","")).strip() == k)
                   for k in ("Aktif","Arızalı","Bakımda")}
        self.lbl_info.setText(f"Gösterilen {visible} / {total}")
        self.lbl_detail.setText(
            "  ·  ".join(f"{k} {v}" for k, v in counts.items())
        )
        for t, btn in self._filter_btns.items():
            c = counts.get(t, "")
            btn.setText(f"{t}  {c}" if c != "" else t)

    # ── Mouse ─────────────────────────────────────────────

    def _tbl_mouse_move(self, event):
        idx = self.table.indexAt(event.pos())
        src = self._proxy.mapToSource(idx).row() if idx.isValid() else -1
        self._delegate.set_hover_row(src)
        self.table.viewport().update()
        QTableView.mouseMoveEvent(self.table, event)

    def _tbl_mouse_press(self, event):
        idx = self.table.indexAt(event.pos())
        if idx.isValid():
            src      = self._proxy.mapToSource(idx)
            row_data = self._model.get_row(src.row())
            if row_data and COLUMNS[idx.column()][0] == "_actions":
                action = self._delegate.get_action_at(src.row(), event.pos())
                if action == "detay":
                    self.detay_requested.emit(row_data); return
                elif action == "ariza":
                    self._open_ariza_panel(row_data); return
        QTableView.mousePressEvent(self.table, event)

    def _on_double_click(self, index):
        src = self._proxy.mapToSource(index)
        row = self._model.get_row(src.row())
        if row:
            self.detay_requested.emit(row)

    def get_selected(self):
        idxs = self.table.selectionModel().selectedRows()
        if idxs:
            return self._model.get_row(self._proxy.mapToSource(idxs[0]).row())
        return None

    # ── Arıza Panel ───────────────────────────────────────

    def _open_ariza_panel(self, row_data: dict):
        self.ariza_panel.formu_sifirla(str(row_data.get("Cihazid", "")))
        self.ariza_panel.setVisible(True)

    def _close_ariza_panel(self):
        self.ariza_panel.setVisible(False)

    def _on_ariza_saved(self):
        self.ariza_panel.setVisible(False)
        self.load_data()

    # ── Sağ tık ───────────────────────────────────────────

    def _show_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid(): return
        row = self._model.get_row(self._proxy.mapToSource(idx).row())
        if not row: return
        menu = QMenu(self)
        menu.setStyleSheet(STYLES["context_menu"])
        menu.addAction("Detay / Düzenle").triggered.connect(
            lambda: self.detay_requested.emit(row))
        menu.addSeparator()
        menu.addAction("Arıza Bildir").triggered.connect(
            lambda: self._open_ariza_panel(row))
        menu.addAction("Periyodik Bakım Ekle").triggered.connect(
            lambda: self.periodic_maintenance_requested.emit(row))
        menu.addSeparator()
        durum = str(row.get("Durum","")).strip()
        for d in ("Aktif", "Arızalı", "Bakımda", "Pasif"):
            if d != durum:
                menu.addAction(f"{d} Yap").triggered.connect(
                    lambda _, dd=d: self._change_durum(row, dd))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _change_durum(self, row_data: dict, yeni: str):
        cid = row_data.get("Cihazid", "")
        if QMessageBox.question(
            self, "Durum Değiştir",
            f'Cihaz "{cid}" durumu "{yeni}" olarak değiştirilsin mi?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            from core.di import get_registry
            get_registry(self._db).get("Cihazlar").update(cid, {"Durum": yeni})
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem başarısız:\n{e}")

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame(); s.setFixedSize(1, 20)
        s.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        return s
