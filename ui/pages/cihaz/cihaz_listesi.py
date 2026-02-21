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
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles, STYLES
from ui.styles.icons import IconRenderer

C = DarkTheme

# ─── Sütun tanımları ──────────────────────────────────────────
COLUMNS = [
    ("_cihaz",       "Cihaz",          140),
    ("_marka_model", "Marka / Model",  180),
    ("_seri",        "Seri / NDK",     140),
    ("Birim",        "Birim",          120),
    ("Sorumlusu",    "Sorumlu",        120),
    ("Durum",        "Durum",           90),
    ("BakimDurum",   "Bakım",           90),
    ("_actions",     "",               190),
]
COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}


# ═══════════════════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════════════════

class CihazTableModel(QAbstractTableModel):

    RAW_ROW_ROLE = Qt.UserRole + 1

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data: list[dict] = data or []
        self._keys = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        key = self._keys[index.column()]

        if role == self.RAW_ROW_ROLE:
            return row

        if role == Qt.DisplayRole:
            if key == "_cihaz":
                return f"{row.get('Cihazid', '')} {row.get('CihazTipi', '')}".strip()
            if key == "_marka_model":
                return f"{row.get('Marka', '')} {row.get('Model', '')}".strip()
            if key == "_seri":
                return f"{row.get('SeriNo', '')} {row.get('NDKSeriNo', '')}".strip()
            return str(row.get(key, ""))

        return None

    def set_data(self, data: list):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def get_row(self, row: int) -> dict | None:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None


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
        return QSize(COLUMNS[index.column()][2], 40)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        row = index.row()
        col = index.column()
        key = COLUMNS[col][0]
        rect = option.rect
        is_sel = bool(option.state & QStyle.State_Selected)
        is_hover = (row == self._hover_row)

        if is_sel:
            c = QColor(C.BTN_PRIMARY_BG)
            c.setAlpha(60)
            painter.fillRect(rect, c)
        elif is_hover:
            c = QColor(C.TEXT_PRIMARY)
            c.setAlpha(10)
            painter.fillRect(rect, c)

        raw = index.model().data(index, CihazTableModel.RAW_ROW_ROLE)
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
            self._draw_mono(painter, rect, str(raw.get("Birim", "") or "—"))
        elif key == "Sorumlusu":
            self._draw_mono(painter, rect, str(raw.get("Sorumlusu", "") or "—"))
        elif key == "Durum":
            self._draw_status_pill(painter, rect, str(raw.get("Durum", "") or "—"))
        elif key == "BakimDurum":
            self._draw_status_pill(painter, rect, str(raw.get("BakimDurum", "") or "—"))
        elif key == "_actions":
            if is_hover or is_sel:
                self._draw_action_btns(painter, rect, row)
            else:
                for k in list(self._btn_rects):
                    if k[0] == row:
                        del self._btn_rects[k]

        painter.restore()

    # ── Çizim yardımcıları ───────────────────────────────

    def _draw_two(self, p, rect, top, bottom, mono_top=False):
        pad = 8
        r1 = QRect(rect.x() + pad, rect.y() + 4, rect.width() - pad * 2, 17)
        r2 = QRect(rect.x() + pad, rect.y() + 21, rect.width() - pad * 2, 14)
        p.setFont(QFont("Courier New", 8) if mono_top else QFont("", 9, QFont.Medium))
        p.setPen(QColor(C.TEXT_SECONDARY))
        p.drawText(r1, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(top, Qt.ElideRight, r1.width()))
        p.setFont(QFont("", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        p.drawText(r2, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(bottom, Qt.ElideRight, r2.width()))

    def _draw_mono(self, p, rect, text):
        pad = 8
        r = QRect(rect.x() + pad, rect.y(), rect.width() - pad * 2, rect.height())
        p.setFont(QFont("", 9))
        p.setPen(QColor(C.TEXT_PRIMARY))
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(text, Qt.ElideRight, r.width()))

    def _draw_status_pill(self, p, rect, text):
        text = text or "—"
        r = QRect(rect.x() + 8, rect.y() + 9, rect.width() - 16, 22)
        bg = ComponentStyles.get_status_color(text)
        fg = ComponentStyles.get_status_text_color(text)
        br, bgc, bb, ba = bg
        p.setBrush(QBrush(QColor(br, bgc, bb, ba)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 11, 11)
        p.setPen(QColor(fg))
        p.setFont(QFont("", 8, QFont.Medium))
        p.drawText(r, Qt.AlignCenter, text)

    def _draw_action_btns(self, p, rect, row):
        labels = [
            ("detay", "Detay", C.BTN_PRIMARY_BG, C.BTN_PRIMARY_TEXT),
            ("edit", "Duzenle", C.BTN_SECONDARY_BG, C.TEXT_PRIMARY),
            ("bakim", "Bakim", C.BTN_SUCCESS_BG, C.BTN_SUCCESS_TEXT),
        ]
        x = rect.x() + 8
        y = rect.center().y() - int(self.BTN_H / 2)
        for key, label, bg, fg in labels:
            btn_rect = QRect(x, y, self.BTN_W, self.BTN_H)
            p.setBrush(QBrush(QColor(bg)))
            p.setPen(QPen(QColor(C.BORDER_STRONG)))
            p.drawRoundedRect(btn_rect, 6, 6)
            p.setPen(QColor(fg))
            p.setFont(QFont("", 8, QFont.Medium))
            p.drawText(btn_rect, Qt.AlignCenter, label)
            self._btn_rects[(row, key)] = btn_rect
            x += self.BTN_W + self.BTN_GAP

    def get_action_at(self, row: int, pos: QPoint) -> str | None:
        for (r, key), rect in self._btn_rects.items():
            if r == row and rect.contains(pos):
                return key
        return None


# ═══════════════════════════════════════════════════════════
#  SAYFA
# ═══════════════════════════════════════════════════════════

class CihazListesiPage(QWidget):

    detay_requested = Signal(dict)
    edit_requested = Signal(dict)
    periodic_maintenance_requested = Signal(dict)
    add_requested = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        self._db = db
        self._all_data = []
        self._active_filter = "Tümü"
        self._filter_btns = {}

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

        title = QLabel("Cihaz Listesi")
        title.setStyleSheet(f"font-size:13px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;")
        lay.addWidget(title)

        lay.addWidget(self._sep())

        for lbl in ("Aktif", "Bakımda", "Arızalı", "Tümü"):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.setMinimumWidth(90)

            bg = ComponentStyles.get_status_color(lbl)
            text_color = ComponentStyles.get_status_text_color(lbl)
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
        self.search_input.setStyleSheet(STYLES["search"])
        lay.addWidget(self.search_input)

        lay.addStretch()

        self.btn_yenile = QPushButton()
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=C.TEXT_SECONDARY, size=16)
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton(" Yeni Cihaz")
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=C.BTN_PRIMARY_TEXT, size=16)
        self.btn_yeni.setIconSize(QSize(16, 16))
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

        lbl = QLabel("FİLTRE:")
        lbl.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl)

        lbl_abd = QLabel("Birim:")
        lbl_abd.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl_abd)

        self.cmb_abd = QComboBox()
        self.cmb_abd.addItem("Tümü")
        self.cmb_abd.setFixedWidth(160)
        self.cmb_abd.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_abd)

        lbl_kaynak = QLabel("Kaynak:")
        lbl_kaynak.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl_kaynak)

        self.cmb_kaynak = QComboBox()
        self.cmb_kaynak.addItem("Tümü")
        self.cmb_kaynak.setFixedWidth(160)
        self.cmb_kaynak.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_kaynak)

        lay.addStretch()

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
        self.table.verticalHeader().setDefaultSectionSize(40)

        self._delegate = CihazDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        hdr = self.table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            hdr.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        hdr.setSectionResizeMode(COL_IDX["_marka_model"], QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_IDX["Birim"], QHeaderView.Stretch)
        return self.table

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-top: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)

        self.lbl_info = QLabel("0 kayıt")
        self.lbl_info.setStyleSheet(STYLES["footer_label"])
        lay.addWidget(self.lbl_info)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setStyleSheet(STYLES["footer_label"])
        lay.addWidget(self.lbl_detail)

        lay.addStretch()

        self.progress = QProgressBar()
        self.progress.setFixedSize(140, 4)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(STYLES["progress"])
        lay.addWidget(self.progress)

        self.btn_load_more = QPushButton("Daha Fazla Yükle")
        self.btn_load_more.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_load_more.setFixedHeight(28)
        self.btn_load_more.setStyleSheet(STYLES["action_btn"])
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
        self.table.mouseMoveEvent = self._tbl_mouse_move
        self.table.mousePressEvent = self._tbl_mouse_press

    # ─── Veri Yükleme ────────────────────────────────────

    def load_data(self):
        if not self._db:
            logger.warning("Cihaz listesi: DB yok")
            return
        try:
            self._current_page = 1
            self._total_count = 0
            self._all_data = []

            registry = RepositoryRegistry(self._db)
            cihaz_repo = registry.get("Cihazlar")

            page_data, total = cihaz_repo.get_paginated(
                page=self._current_page,
                page_size=self._page_size
            )
            self._all_data = page_data
            self._total_count = total

            self._model.set_data(self._all_data)
            self._populate_combos(registry)
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

            registry = RepositoryRegistry(self._db)
            cihaz_repo = registry.get("Cihazlar")

            self._current_page += 1
            page_data, _ = cihaz_repo.get_paginated(
                page=self._current_page,
                page_size=self._page_size
            )

            if not page_data:
                self._current_page -= 1
            else:
                self._all_data.extend(page_data)
                self._model.set_data(self._all_data)
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

    def _populate_combos(self, registry):
        sabitler = []
        try:
            sabitler = registry.get("Sabitler").get_all()
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

    # ─── Mouse ───────────────────────────────────────────

    def _tbl_mouse_move(self, event):
        idx = self.table.indexAt(event.pos())
        src_row = self._proxy.mapToSource(idx).row() if idx.isValid() else -1
        self._delegate.set_hover_row(src_row)
        self.table.viewport().update()
        QTableView.mouseMoveEvent(self.table, event)

    def _tbl_mouse_press(self, event):
        idx = self.table.indexAt(event.pos())
        if idx.isValid():
            src = self._proxy.mapToSource(idx)
            row_data = self._model.get_row(src.row())
            if row_data and COLUMNS[idx.column()][0] == "_actions":
                cell_rect = self.table.visualRect(idx)
                local_pos = event.pos() - cell_rect.topLeft()
                action = self._delegate.get_action_at(src.row(), local_pos)
                if action == "detay":
                    self.detay_requested.emit(row_data)
                    event.accept()
                    return
                if action == "edit":
                    self.edit_requested.emit(row_data)
                    event.accept()
                    return
                if action == "bakim":
                    self.periodic_maintenance_requested.emit(row_data)
                    event.accept()
                    return
        QTableView.mousePressEvent(self.table, event)

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
        f.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        return f
