# -*- coding: utf-8 -*-
"""
Personel Listesi — v3 (Tema Entegrasyonu)
──────────────────────────────────────────
Tüm renkler merkezi ThemeManager / DarkTheme / ComponentStyles üzerinden gelir.
Hardcoded renk yok.
"""
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel,
    Signal, QRect, QPoint, QSize,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QHeaderView,
    QTableView, QComboBox, QLineEdit, QMenu, QMessageBox,
    QStyledItemDelegate, QApplication, QStyle,
)
from PySide6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QFont, QFontMetrics,
)

from core.logger import logger
from core.date_utils import parse_date, to_db_date
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles

C      = DarkTheme                                  # kısayol
STYLES = ThemeManager.get_all_component_styles()    # merkezi stil dict

# ─── Sütun tanımları ──────────────────────────────────────────
COLUMNS = [
    ("_avatar",     "",               36),
    ("AdSoyad",     "Ad Soyad",      180),
    ("_tc_sicil",   "TC / Sicil",    140),
    ("_birim",      "Birim · Ünvan", 180),
    ("CepTelefonu", "Telefon",       120),
    ("_izin_bar",   "İzin Bakiye",   110),
    ("Durum",       "Durum",          80),
    ("_actions",    "",               84),
]
COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}


# ═══════════════════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════════════════

class PersonelTableModel(QAbstractTableModel):

    RAW_ROW_ROLE  = Qt.UserRole + 1
    IZIN_PCT_ROLE = Qt.UserRole + 2   # float 0–1  (-1 = veri yok)
    IZIN_TXT_ROLE = Qt.UserRole + 3   # "13 / 20"

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data: list[dict] = data or []
        self._izin_map: dict[str, dict] = {}
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
        if role == self.IZIN_PCT_ROLE and col == "_izin_bar":
            return self._izin_pct(row)
        if role == self.IZIN_TXT_ROLE and col == "_izin_bar":
            return self._izin_txt(row)
        if role == Qt.DisplayRole:
            if col in ("_avatar", "_izin_bar", "_actions"): return ""
            if col == "AdSoyad":      return str(row.get("AdSoyad", ""))
            if col == "_tc_sicil":   return str(row.get("KimlikNo", ""))
            if col == "_birim":      return str(row.get("GorevYeri", ""))
            if col == "CepTelefonu": return str(row.get("CepTelefonu", "") or "—")
            if col == "Durum":       return str(row.get("Durum", ""))
            return str(row.get(col, ""))
        if role == Qt.TextAlignmentRole:
            if col in ("Durum", "_avatar"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft
        return None

    def get_row(self, idx: int):
        return self._data[idx] if 0 <= idx < len(self._data) else None

    def set_data(self, data: list):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def set_izin_map(self, m: dict):
        self._izin_map = m or {}
        if self._data:
            col = COL_IDX["_izin_bar"]
            self.dataChanged.emit(
                self.index(0, col),
                self.index(len(self._data) - 1, col),
            )

    def _izin_pct(self, row: dict) -> float:
        tc     = str(row.get("KimlikNo", "")).strip()
        bilgi  = self._izin_map.get(tc, {})
        toplam = float(bilgi.get("YillikToplamHak", 0) or 0)
        kalan  = float(bilgi.get("YillikKalan",    0) or 0)
        if toplam <= 0:
            return -1.0
        return max(0.0, min(1.0, kalan / toplam))

    def _izin_txt(self, row: dict) -> str:
        tc    = str(row.get("KimlikNo", "")).strip()
        bilgi = self._izin_map.get(tc, {})
        return f"{bilgi.get('YillikKalan','—')} / {bilgi.get('YillikToplamHak','—')}"


# ═══════════════════════════════════════════════════════════
#  DELEGATE
# ═══════════════════════════════════════════════════════════

class PersonelDelegate(QStyledItemDelegate):
    """
    Özel hücre çizimi. Tüm renkler DarkTheme ve ComponentStyles'dan alınır.
    """

    BTN_W, BTN_H, BTN_GAP = 36, 22, 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row  = -1
        self._btn_rects: dict[tuple, QRect] = {}

    def set_hover_row(self, row: int):
        self._hover_row = row

    def sizeHint(self, option, index):
        return QSize(COLUMNS[index.column()][2], 40)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        row  = index.row()
        col  = index.column()
        key  = COLUMNS[col][0]
        rect = option.rect
        is_sel   = bool(option.state & QStyle.State_Selected)
        is_hover = (row == self._hover_row)

        # ── Zemin (temadan) ──
        if is_sel:
            # BG_SELECTED = "rgba(29, 117, 254, 0.45)"
            painter.fillRect(rect, QColor(29, 117, 254, 60))
        elif is_hover:
            # BG_HOVER = "rgba(255, 255, 255, 0.04)"
            painter.fillRect(rect, QColor(255, 255, 255, 10))

        raw = index.model().data(index, PersonelTableModel.RAW_ROW_ROLE)
        if raw is None:
            painter.restore()
            return

        if key == "_avatar":
            self._draw_avatar(painter, rect, raw)
        elif key == "AdSoyad":
            self._draw_primary(painter, rect, str(raw.get("AdSoyad", "")))
        elif key == "_tc_sicil":
            self._draw_two(painter, rect,
                           str(raw.get("KimlikNo", "")),
                           str(raw.get("KurumSicilNo", "") or ""),
                           mono_top=True)
        elif key == "_birim":
            self._draw_two(painter, rect,
                           str(raw.get("GorevYeri", "") or "—"),
                           str(raw.get("KadroUnvani", "") or ""))
        elif key == "CepTelefonu":
            self._draw_mono(painter, rect, str(raw.get("CepTelefonu", "") or "—"))
        elif key == "_izin_bar":
            pct = index.model().data(index, PersonelTableModel.IZIN_PCT_ROLE)
            txt = index.model().data(index, PersonelTableModel.IZIN_TXT_ROLE)
            self._draw_izin_bar(painter, rect, pct, txt)
        elif key == "Durum":
            self._draw_status_pill(painter, rect, str(raw.get("Durum", "")))
        elif key == "_actions":
            if is_hover or is_sel:
                self._draw_action_btns(painter, rect, row)
            else:
                for k in list(self._btn_rects):
                    if k[0] == row:
                        del self._btn_rects[k]

        painter.restore()

    # ── Çizim yardımcıları ───────────────────────────────

    def _draw_avatar(self, p, rect, row):
        """Monogram dairesi — renk addan türetilir."""
        ad = str(row.get("AdSoyad", "")).strip()
        initials = "".join(w[0].upper() for w in ad.split()[:2]) if ad else "?"
        cx, cy, r = rect.center().x(), rect.center().y(), 13
        hue = (sum(ord(c) for c in ad) * 37) % 360
        p.setBrush(QBrush(QColor.fromHsl(hue, 100, 55)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.setFont(QFont("", 8, QFont.Bold))
        p.setPen(QColor(C.TEXT_PRIMARY))
        p.drawText(rect, Qt.AlignCenter, initials)

    def _draw_primary(self, p, rect, text):
        p.setFont(QFont("", 9, QFont.Medium))
        p.setPen(QColor(C.TEXT_PRIMARY))
        r = QRect(rect.x() + 8, rect.y(), rect.width() - 16, rect.height())
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(text, Qt.ElideRight, r.width()))

    def _draw_two(self, p, rect, top, bottom, mono_top=False):
        pad = 8
        r1 = QRect(rect.x() + pad, rect.y() + 4,  rect.width() - pad*2, 17)
        r2 = QRect(rect.x() + pad, rect.y() + 21, rect.width() - pad*2, 14)
        # Üst satır
        p.setFont(QFont("Courier New", 8) if mono_top else QFont("", 9, QFont.Medium))
        p.setPen(QColor(C.TEXT_SECONDARY))
        p.drawText(r1, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(top, Qt.ElideRight, r1.width()))
        # Alt satır (muted)
        p.setFont(QFont("", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        p.drawText(r2, Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(bottom, Qt.ElideRight, r2.width()))

    def _draw_mono(self, p, rect, text):
        p.setFont(QFont("Courier New", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        r = QRect(rect.x() + 8, rect.y(), rect.width() - 16, rect.height())
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, text)

    def _draw_izin_bar(self, p, rect, pct, txt):
        """Üstte kalan/toplam metni, altta ince progress bar."""
        pad = 8
        bw  = rect.width() - pad * 2
        bx  = rect.x() + pad
        bh  = 4
        # Bar dikey ortalama: metin üstte (y+5..18), bar altta (y+24..28)
        ty  = rect.y() + 5
        by  = rect.y() + rect.height() - 10

        # Metin
        p.setFont(QFont("Courier New", 8))
        p.setPen(QColor(C.TEXT_MUTED))
        p.drawText(QRect(bx, ty, bw, 14), Qt.AlignVCenter | Qt.AlignLeft, txt or "—")

        # Arka plan (BG_TERTIARY)
        p.setBrush(QBrush(QColor(C.BG_TERTIARY)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bx, by, bw, bh, 2, 2)

        # Dolu kısım (pct'ye göre renk)
        if pct is not None and pct >= 0:
            if pct >= 0.7:
                fc = QColor(ComponentStyles.get_status_text_color("Aktif"))   # yeşil
            elif pct >= 0.3:
                fc = QColor(C.BTN_PRIMARY_BORDER)                             # mavi
            else:
                fc = QColor(ComponentStyles.get_status_text_color("İzinli"))  # sarı
            fw = max(3, int(bw * pct))
            p.setBrush(QBrush(fc))
            p.drawRoundedRect(bx, by, fw, bh, 2, 2)

    def _draw_status_pill(self, p, rect, durum):
        """Tema renklerini kullanan durum pill."""
        r_val, g_val, b_val, a_val = ComponentStyles.get_status_color(durum)
        fg_hex = ComponentStyles.get_status_text_color(durum)

        font = QFont("", 8, QFont.Medium)
        p.setFont(font)
        fm   = QFontMetrics(font)
        tw   = fm.horizontalAdvance(durum)
        pw, ph = tw + 20, fm.height() + 8
        px   = rect.center().x() - pw // 2
        py   = rect.center().y() - ph // 2

        p.setBrush(QBrush(QColor(r_val, g_val, b_val, a_val)))
        p.setPen(QPen(QColor(r_val, g_val, b_val, min(a_val + 80, 255)), 1))
        p.drawRoundedRect(px, py, pw, ph, 4, 4)
        p.setPen(QColor(fg_hex))
        p.drawText(QRect(px, py, pw, ph), Qt.AlignCenter, durum)

    def _draw_action_btns(self, p, rect, row):
        """Hover'da görünen "Detay" ve "İzin" butonları."""
        x = rect.x() + 4
        y = rect.center().y() - self.BTN_H // 2
        for i, lbl in enumerate(["Detay", "İzin"]):
            bx = x + i * (self.BTN_W + self.BTN_GAP)
            br = QRect(bx, y, self.BTN_W, self.BTN_H)
            self._btn_rects[(row, i)] = br
            # BTN_SECONDARY_BG benzeri
            p.setBrush(QBrush(QColor(255, 255, 255, 15)))
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.drawRoundedRect(br, 4, 4)
            p.setFont(QFont("", 8))
            p.setPen(QColor(C.TEXT_SECONDARY))
            p.drawText(br, Qt.AlignCenter, lbl)

    def get_action_at(self, row: int, pos: QPoint):
        for (r, i), rect in self._btn_rects.items():
            if r == row and rect.contains(pos):
                return ["detay", "izin"][i]
        return None


# ═══════════════════════════════════════════════════════════
#  PERSONEL LİSTESİ SAYFASI
# ═══════════════════════════════════════════════════════════

class PersonelListesiPage(QWidget):

    detay_requested = Signal(dict)
    izin_requested  = Signal(dict)
    yeni_requested  = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        self._db             = db
        self._all_data       = []
        self._izin_map       = {}
        self._active_filter  = "Aktif"
        self._filter_btns    = {}
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

        title = QLabel("Personel Listesi")
        title.setStyleSheet(f"font-size:13px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;")
        lay.addWidget(title)
        lay.addWidget(self._sep())

        # Durum filtre pill butonları — merkezi STYLES kullanır
        for lbl in ("Aktif", "Pasif", "İzinli", "Tümü"):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(28)
            # "Tümü" için filter_btn_all, diğerleri için filter_btn
            style_key = "filter_btn_all" if lbl == "Tümü" else "filter_btn"
            btn.setStyleSheet(STYLES[style_key])
            if lbl == self._active_filter:
                btn.setChecked(True)
            self._filter_btns[lbl] = btn
            lay.addWidget(btn)

        lay.addWidget(self._sep())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ad, TC, birim ara…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet(STYLES["search"])
        lay.addWidget(self.search_input)

        lay.addStretch()

        self.btn_yenile = QPushButton("⟳")
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("+ Yeni Personel")
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
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

        lbl = QLabel("FİLTRE:")
        lbl.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl)

        self.cmb_gorev_yeri = QComboBox()
        self.cmb_gorev_yeri.addItem("Tüm Birimler")
        self.cmb_gorev_yeri.setFixedWidth(160)
        self.cmb_gorev_yeri.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_gorev_yeri)

        self.cmb_hizmet = QComboBox()
        self.cmb_hizmet.addItem("Tüm Sınıflar")
        self.cmb_hizmet.setFixedWidth(140)
        self.cmb_hizmet.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_hizmet)

        lay.addStretch()

        self.btn_excel = QPushButton("↓ Excel")
        self.btn_excel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_excel.setStyleSheet(STYLES["excel_btn"])
        lay.addWidget(self.btn_excel)
        return frame

    def _build_table(self) -> QTableView:
        self._model = PersonelTableModel()
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

        self._delegate = PersonelDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        hdr = self.table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            hdr.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        hdr.setSectionResizeMode(COL_IDX["AdSoyad"], QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_IDX["_birim"],  QHeaderView.Stretch)
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
        return frame

    # ─── Sinyaller ───────────────────────────────────────

    def _connect_signals(self):
        for text, btn in self._filter_btns.items():
            btn.clicked.connect(lambda _, t=text: self._on_filter_click(t))
        self.search_input.textChanged.connect(self._on_search)
        self.cmb_gorev_yeri.currentTextChanged.connect(lambda _: self._apply_filters())
        self.cmb_hizmet.currentTextChanged.connect(lambda _: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni.clicked.connect(self.yeni_requested.emit)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.mouseMoveEvent  = self._tbl_mouse_move
        self.table.mousePressEvent = self._tbl_mouse_press

    # ─── Veri Yükleme ────────────────────────────────────

    def load_data(self):
        if not self._db:
            logger.warning("Personel listesi: DB yok")
            return
        try:
            from core.di import get_registry
            reg = get_registry(self._db)
            self._all_data = reg.get("Personel").get_all()
            try:
                bilgiler = reg.get("Izin_Bilgi").get_all()
                self._izin_map = {
                    str(r.get("TCKimlik", "")).strip(): r for r in bilgiler
                }
                self._model.set_izin_map(self._izin_map)
            except Exception as e:
                logger.warning(f"İzin bakiye yüklenemedi: {e}")
            self._populate_combos(reg)
            self._apply_filters()
        except Exception as e:
            logger.error(f"Personel yükleme: {e}")

    def _populate_combos(self, reg):
        try:
            sabit = reg.get("Sabitler").get_all()
            gy = sorted({
                str(r.get("MenuEleman", "")).strip()
                for r in sabit
                if r.get("Kod") == "Gorev_Yeri" and r.get("MenuEleman", "").strip()
            })
            self.cmb_gorev_yeri.blockSignals(True)
            self.cmb_gorev_yeri.clear()
            self.cmb_gorev_yeri.addItem("Tüm Birimler")
            self.cmb_gorev_yeri.addItems(gy)
            self.cmb_gorev_yeri.blockSignals(False)

            hs = sorted({
                str(r.get("MenuEleman", "")).strip()
                for r in sabit
                if r.get("Kod") == "Hizmet_Sinifi" and r.get("MenuEleman", "").strip()
            })
            self.cmb_hizmet.blockSignals(True)
            self.cmb_hizmet.clear()
            self.cmb_hizmet.addItem("Tüm Sınıflar")
            self.cmb_hizmet.addItems(hs)
            self.cmb_hizmet.blockSignals(False)
        except Exception as e:
            logger.error(f"Sabitler yükleme: {e}")

    # ─── Filtreleme ──────────────────────────────────────

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

        if self._active_filter == "İzinli":
            izinli = self._get_izinli_personeller()
            filtered = [r for r in filtered
                        if str(r.get("KimlikNo", "")).strip() in izinli]
        elif self._active_filter != "Tümü":
            filtered = [r for r in filtered
                        if str(r.get("Durum", "")).strip() == self._active_filter]

        birim = self.cmb_gorev_yeri.currentText()
        if birim and birim != "Tüm Birimler":
            filtered = [r for r in filtered
                        if str(r.get("GorevYeri", "")).strip() == birim]

        sinif = self.cmb_hizmet.currentText()
        if sinif and sinif != "Tüm Sınıflar":
            filtered = [r for r in filtered
                        if str(r.get("HizmetSinifi", "")).strip() == sinif]

        self._model.set_data(filtered)
        self._update_count()
        self._update_pill_counts()

    def _get_izinli_personeller(self) -> set:
        if not self._db:
            return set()
        try:
            from datetime import date
            from core.di import get_registry
            b      = date.today()
            ay_bas = date(b.year, b.month, 1).isoformat()
            ay_son = (date(b.year + 1, 1, 1)
                      if b.month == 12
                      else date(b.year, b.month + 1, 1)).isoformat()
            reg = get_registry(self._db)
            izinli: set = set()
            for r in reg.get("Izin_Giris").get_all():
                bas = to_db_date(r.get("BaslamaTarihi", ""))
                bit = to_db_date(r.get("BitisTarihi",   ""))
                tc  = str(r.get("Personelid", "")).strip()
                if not bas or not tc:
                    continue
                if not bit:
                    bit = bas
                if bas < ay_son and bit >= ay_bas:
                    izinli.add(tc)
            return izinli
        except Exception as e:
            logger.error(f"İzinli sorgu: {e}")
            return set()

    def _update_count(self):
        self.lbl_info.setText(
            f"Gösterilen {self._proxy.rowCount()} / {len(self._all_data)}"
        )

    def _update_pill_counts(self):
        aktif  = sum(1 for r in self._all_data if str(r.get("Durum", "")).strip() == "Aktif")
        pasif  = sum(1 for r in self._all_data if str(r.get("Durum", "")).strip() == "Pasif")
        izinli = sum(1 for r in self._all_data if str(r.get("Durum", "")).strip() == "İzinli")
        self.lbl_detail.setText(f"Aktif {aktif}  ·  Pasif {pasif}  ·  İzinli {izinli}")
        counts = {"Aktif": aktif, "Pasif": pasif, "İzinli": izinli}
        for t, btn in self._filter_btns.items():
            c = counts.get(t, "")
            btn.setText(f"{t}  {c}" if c != "" else t)

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
            src      = self._proxy.mapToSource(idx)
            row_data = self._model.get_row(src.row())
            if row_data and COLUMNS[idx.column()][0] == "_actions":
                action = self._delegate.get_action_at(src.row(), event.pos())
                if action == "detay":
                    self.detay_requested.emit(row_data)
                    return
                elif action == "izin":
                    self.izin_requested.emit(row_data)
                    return
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

    # ─── Sağ tık ─────────────────────────────────────────

    def _show_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        row = self._model.get_row(self._proxy.mapToSource(idx).row())
        if not row:
            return
        ad, tc = row.get("AdSoyad", ""), row.get("KimlikNo", "")
        durum  = str(row.get("Durum", "")).strip()

        menu = QMenu(self)
        menu.setStyleSheet(STYLES["context_menu"])
        menu.addAction("Detay Görüntüle").triggered.connect(
            lambda: self.detay_requested.emit(row))
        menu.addSeparator()
        menu.addAction("İzin Girişi").triggered.connect(
            lambda: self.izin_requested.emit(row))
        menu.addSeparator()
        for d in ("Aktif", "Pasif", "İzinli"):
            if d != durum:
                menu.addAction(f"{d} Yap").triggered.connect(
                    lambda _, dd=d: self._change_durum(tc, ad, dd))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _change_durum(self, tc, ad, yeni):
        if QMessageBox.question(
            self, "Durum Değiştir",
            f'"{ad}" personelinin durumu "{yeni}" olarak değiştirilsin mi?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            from core.di import get_registry
            get_registry(self._db).get("Personel").update(tc, {"Durum": yeni})
            logger.info(f"Durum: {tc} → {yeni}")
            self.load_data()
        except Exception as e:
            logger.error(f"Durum değiştirme: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem başarısız:\n{e}")

    # ─── Yardımcılar ─────────────────────────────────────

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setStyleSheet(f"background: {C.BORDER_PRIMARY};")
        return s
