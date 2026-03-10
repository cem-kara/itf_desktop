# -*- coding: utf-8 -*-
"""
REPYS Tema Demo — Bağımsız form önizleme aracı
═══════════════════════════════════════════════
Çalıştır:  python tema_demo.py
Gereksinim: PySide6, proje dizininde theme_template.qss / theme_light_template.qss
"""
import sys
from pathlib import Path

# Proje kök dizinini Python yoluna ekle
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QProgressBar, QTabWidget,
    QSplitter, QFrame, QListWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabBar,
)

# ── Token ve QSS yükleyici ───────────────────────────────────────────────────

def _load_qss(theme: str) -> str:
    """theme_template.qss / theme_light_template.qss yükle ve token'ları doldur."""
    try:
        from ui.styles.themes import get_tokens
        tokens = get_tokens(theme)
    except ImportError:
        # Proje import'u yoksa token'ları ham olarak oku
        tokens = {}

    qss_file = ROOT / "ui" / (
        "theme_light_template.qss" if theme == "light" else "theme_template.qss"
    )
    if not qss_file.exists():
        return ""

    qss = qss_file.read_text(encoding="utf-8")
    for key, val in tokens.items():
        qss = qss.replace(f"{{{key}}}", val)
    return qss


def _apply_theme(app: QApplication, theme: str) -> None:
    try:
        from ui.styles.themes import get_tokens
        tokens = get_tokens(theme)
    except ImportError:
        tokens = {}

    app.setStyle("Fusion")
    app.setStyleSheet(_load_qss(theme))

    if tokens:
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor(tokens.get("BG_PRIMARY", "#f0f4f8")))
        p.setColor(QPalette.ColorRole.WindowText,      QColor(tokens.get("TEXT_PRIMARY", "#0f172a")))
        p.setColor(QPalette.ColorRole.Base,            QColor(tokens.get("BG_TERTIARY", "#e8f0fe")))
        p.setColor(QPalette.ColorRole.AlternateBase,   QColor(tokens.get("BG_SECONDARY", "#ffffff")))
        p.setColor(QPalette.ColorRole.Text,            QColor(tokens.get("TEXT_PRIMARY", "#0f172a")))
        p.setColor(QPalette.ColorRole.Button,          QColor(tokens.get("BG_SECONDARY", "#ffffff")))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor(tokens.get("TEXT_PRIMARY", "#0f172a")))
        p.setColor(QPalette.ColorRole.Highlight,       QColor(tokens.get("ACCENT", "#0284c7")))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens.get("TEXT_MUTED", "#94a3b8")))
        app.setPalette(p)


# ── Yardımcı: bölüm başlığı ayırıcısı ───────────────────────────────────────

def _section(title: str) -> QLabel:
    lbl = QLabel(f"  {title}")
    lbl.setProperty("style-role", "section-title")
    lbl.setMinimumHeight(34)
    sep = QFrame()
    sep.setProperty("bg-role", "separator")
    return lbl


def _sep() -> QFrame:
    f = QFrame()
    f.setProperty("bg-role", "separator")
    f.setFixedHeight(1)
    return f


# ── Demo penceresi ───────────────────────────────────────────────────────────

class DemoWindow(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._theme = "dark"
        self.setWindowTitle("REPYS — Tema Demo")
        self.resize(1100, 820)
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Üst toolbar
        root.addWidget(self._build_topbar())
        root.addWidget(_sep())

        # İçerik - scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setProperty("style-role", "plain")

        content = QWidget()
        content.setProperty("bg-role", "page")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(24, 20, 24, 32)
        vbox.setSpacing(24)

        vbox.addWidget(self._build_buttons())
        vbox.addWidget(self._build_inputs())
        vbox.addWidget(self._build_labels())
        vbox.addWidget(self._build_selections())
        vbox.addWidget(self._build_table_section())
        vbox.addWidget(self._build_tabs_section())
        vbox.addWidget(self._build_badges())
        vbox.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── Üst çubuk ────────────────────────────────────────────────────────────

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setProperty("bg-role", "panel")
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 8, 20, 8)

        title = QLabel("🎨  REPYS Tema Demo")
        title.setProperty("style-role", "title")
        lay.addWidget(title)
        lay.addStretch()

        lbl = QLabel("Tema:")
        lbl.setProperty("color-role", "muted")
        lay.addWidget(lbl)

        self._btn_dark = QPushButton("Dark")
        self._btn_dark.setProperty("style-role", "tab-active")
        self._btn_dark.setFixedWidth(72)
        self._btn_dark.clicked.connect(lambda: self._switch("dark"))
        lay.addWidget(self._btn_dark)

        self._btn_light = QPushButton("Light")
        self._btn_light.setProperty("style-role", "tab-inactive")
        self._btn_light.setFixedWidth(72)
        self._btn_light.clicked.connect(lambda: self._switch("light"))
        lay.addWidget(self._btn_light)

        return bar

    # ── Butonlar ──────────────────────────────────────────────────────────────

    def _build_buttons(self) -> QGroupBox:
        grp = QGroupBox("Butonlar — style-role")
        grp.setProperty("gb-role", "section")
        lay = QVBoxLayout(grp)
        lay.setSpacing(14)

        roles = [
            ("action",         "Kaydet / Ana İşlem"),
            ("secondary",      "İkincil / İptal"),
            ("success",        "Başarı (outline hover)"),
            ("success-filled", "Başarı (dolu)"),
            ("warning",        "Uyarı / Güncelle"),
            ("danger",         "Tehlike / Sil"),
            ("refresh",        "Yenile"),
            ("upload",         "Dosya Yükle"),
            ("close",          "✕  Kapat"),
            ("tab-active",     "Sekme — Aktif"),
            ("tab-inactive",   "Sekme — Pasif"),
            ("quick-action",   "Hızlı İşlem (sol hizalı)"),
        ]

        for i in range(0, len(roles), 4):
            row = QHBoxLayout()
            row.setSpacing(8)
            for role, label in roles[i:i+4]:
                btn = QPushButton(label)
                btn.setProperty("style-role", role)
                btn.setMinimumHeight(32)
                row.addWidget(btn)
            row.addStretch()
            lay.addLayout(row)

        # Disabled örnekleri
        lay.addWidget(_sep())
        dis_row = QHBoxLayout()
        dis_row.setSpacing(8)
        for role, label in [("action","Disabled Action"), ("secondary","Disabled Secondary"), ("success-filled","Disabled Success")]:
            btn = QPushButton(label)
            btn.setProperty("style-role", role)
            btn.setEnabled(False)
            btn.setMinimumHeight(32)
            dis_row.addWidget(btn)
        dis_row.addStretch()
        lay.addLayout(dis_row)

        return grp

    # ── Girişler ─────────────────────────────────────────────────────────────

    def _build_inputs(self) -> QGroupBox:
        grp = QGroupBox("Form Girişleri — Global QSS")
        grp.setProperty("gb-role", "section")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def lbl(text):
            l = QLabel(text)
            l.setProperty("style-role", "form")
            return l

        # QLineEdit
        inp = QLineEdit()
        inp.setPlaceholderText("Metin girin...")
        form.addRow(lbl("QLineEdit"), inp)

        inp_ro = QLineEdit("Read-only alan")
        inp_ro.setReadOnly(True)
        form.addRow(lbl("Read-only"), inp_ro)

        inp_dis = QLineEdit("Disabled alan")
        inp_dis.setEnabled(False)
        form.addRow(lbl("Disabled"), inp_dis)

        inp_search = QLineEdit()
        inp_search.setPlaceholderText("🔍  Arama...")
        inp_search.setProperty("input-role", "search")
        form.addRow(lbl("Arama"), inp_search)

        # QTextEdit
        txt = QTextEdit()
        txt.setPlaceholderText("Çok satırlı metin...")
        txt.setFixedHeight(70)
        form.addRow(lbl("QTextEdit"), txt)

        # QComboBox
        cmb = QComboBox()
        cmb.addItems(["Seçenek 1", "Seçenek 2", "Seçenek 3", "Seçenek 4"])
        form.addRow(lbl("QComboBox"), cmb)

        cmb_dis = QComboBox()
        cmb_dis.addItems(["Disabled combo"])
        cmb_dis.setEnabled(False)
        form.addRow(lbl("Disabled Combo"), cmb_dis)

        # QDateEdit
        dt = QDateEdit(QDate.currentDate())
        dt.setCalendarPopup(True)
        dt.setDisplayFormat("dd.MM.yyyy")
        form.addRow(lbl("QDateEdit"), dt)

        # QSpinBox
        spn = QSpinBox()
        spn.setRange(0, 999)
        spn.setValue(42)
        form.addRow(lbl("QSpinBox"), spn)

        dspn = QDoubleSpinBox()
        dspn.setRange(0.0, 999.0)
        dspn.setValue(3.14)
        form.addRow(lbl("QDoubleSpinBox"), dspn)

        # QCheckBox / QRadioButton
        chk_row = QHBoxLayout()
        for text, checked in [("Seçenek A", True), ("Seçenek B", False), ("Devre dışı", False)]:
            chk = QCheckBox(text)
            chk.setChecked(checked)
            if text == "Devre dışı":
                chk.setEnabled(False)
            chk_row.addWidget(chk)
        chk_row.addStretch()
        form.addRow(lbl("QCheckBox"), chk_row)

        rad_row = QHBoxLayout()
        for text in ["Seçenek 1", "Seçenek 2", "Seçenek 3"]:
            rad = QRadioButton(text)
            rad_row.addWidget(rad)
        rad_row.addStretch()
        form.addRow(lbl("QRadioButton"), rad_row)

        # QProgressBar
        pb = QProgressBar()
        pb.setValue(65)
        form.addRow(lbl("QProgressBar"), pb)

        return grp

    # ── Etiket rolleri ────────────────────────────────────────────────────────

    def _build_labels(self) -> QGroupBox:
        grp = QGroupBox("Etiket Rolleri — style-role & color-role")
        grp.setProperty("gb-role", "section")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        style_roles = [
            ("title",        "QLabel — title"),
            ("section",      "QLabel — section"),
            ("section-title","QLabel — section-title"),
            ("form",         "QLabel — form (alan etiketi)"),
            ("info",         "QLabel — info"),
            ("footer",       "QLabel — footer"),
            ("header-name",  "QLabel — header-name (kişi adı)"),
            ("required",     "QLabel — required *"),
            ("stat-label",   "QLabel — stat-label"),
            ("stat-value",   "QLabel — stat-value  123"),
            ("stat-red",     "QLabel — stat-red  ↓ 12"),
            ("stat-green",   "QLabel — stat-green  ↑ 45"),
            ("stat-highlight","QLabel — stat-highlight  ⭐"),
            ("value",        "QLabel — value"),
            ("donem",        "QLabel — donem  2025/1"),
        ]

        grid = QGridLayout()
        grid.setSpacing(4)
        for i, (role, text) in enumerate(style_roles):
            lbl = QLabel(text)
            lbl.setProperty("style-role", role)
            grid.addWidget(lbl, i // 2, i % 2)
        lay.addLayout(grid)

        lay.addWidget(_sep())

        color_row = QHBoxLayout()
        color_row.setSpacing(16)
        for role in ["primary","secondary","muted","accent","accent2","ok","warn","err","info"]:
            l = QLabel(role)
            l.setProperty("color-role", role)
            color_row.addWidget(l)
        color_row.addStretch()
        lay.addLayout(color_row)

        return grp

    # ── Seçim kontrolleri ─────────────────────────────────────────────────────

    def _build_selections(self) -> QGroupBox:
        grp = QGroupBox("Liste & Ayırıcılar")
        grp.setProperty("gb-role", "section")
        lay = QHBoxLayout(grp)
        lay.setSpacing(16)

        # QListWidget
        lw = QListWidget()
        for item in ["Kalem Biyopsi Cihazı", "Ultrason (GE)", "MRI 1.5T", "Defibrilatör", "Enjektör Pompası"]:
            lw.addItem(item)
        lw.setMaximumHeight(130)
        lw.setCurrentRow(1)
        lay.addWidget(lw, 1)

        # QSplitter içinde paneller
        spl = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left.setProperty("bg-role", "panel")
        l_lay = QVBoxLayout(left)
        l_lay.addWidget(QLabel("Sol Panel"))
        right = QWidget()
        right.setProperty("bg-role", "elevated")
        r_lay = QVBoxLayout(right)
        r_lay.addWidget(QLabel("Sağ Panel"))
        spl.addWidget(left)
        spl.addWidget(right)
        spl.setMaximumHeight(130)
        lay.addWidget(spl, 2)

        return grp

    # ── Tablo ─────────────────────────────────────────────────────────────────

    def _build_table_section(self) -> QGroupBox:
        grp = QGroupBox("QTableWidget")
        grp.setProperty("gb-role", "section")
        lay = QVBoxLayout(grp)

        tbl = QTableWidget(5, 5)
        tbl.setHorizontalHeaderLabels(["Ad Soyad", "TC Kimlik", "Birim", "Durum", "Tarih"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        data = [
            ("Ayşe Kaya",    "12345678901", "Radyoloji", "Aktif",  "01.01.2020"),
            ("Mehmet Demir", "98765432100", "Dahiliye",  "Aktif",  "15.03.2019"),
            ("Fatma Öztürk", "11223344556", "Acil",      "İzinli", "22.07.2021"),
            ("Ali Yılmaz",   "66778899001", "Kardiyoloji","Pasif", "10.11.2018"),
            ("Zeynep Çelik", "55443322110", "Nöroloji",  "Aktif",  "03.09.2022"),
        ]
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                tbl.setItem(r, c, QTableWidgetItem(val))

        tbl.setMaximumHeight(175)
        tbl.setAlternatingRowColors(True)
        lay.addWidget(tbl)
        return grp

    # ── Sekmeler ──────────────────────────────────────────────────────────────

    def _build_tabs_section(self) -> QGroupBox:
        grp = QGroupBox("QTabWidget")
        grp.setProperty("gb-role", "section")
        lay = QVBoxLayout(grp)

        tabs = QTabWidget()
        for title, content in [
            ("Genel Bilgiler", "Bu sekme genel bilgileri içerir."),
            ("Sağlık Takip",   "Sağlık takip verileri burada görünür."),
            ("Belgeler",       "Belge ve doküman listesi."),
            ("İzin",           "İzin kayıtları ve bakiyesi."),
        ]:
            w = QWidget()
            wl = QVBoxLayout(w)
            lbl = QLabel(content)
            lbl.setProperty("color-role", "secondary")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.addWidget(lbl)
            tabs.addTab(w, title)

        tabs.setMaximumHeight(140)
        lay.addWidget(tabs)
        return grp

    # ── Durum badge'leri ──────────────────────────────────────────────────────

    def _build_badges(self) -> QGroupBox:
        grp = QGroupBox("Durum Badge'leri — header-durum-*")
        grp.setProperty("gb-role", "section")
        lay = QHBoxLayout(grp)
        lay.setSpacing(12)

        for role, text in [
            ("header-durum-aktif",   "● Aktif"),
            ("header-durum-pasif",   "● Pasif / Arızalı"),
            ("header-durum-izinli",  "● İzinli / Bakımda"),
        ]:
            lbl = QLabel(text)
            lbl.setProperty("style-role", role)
            lay.addWidget(lbl)

        lay.addSpacing(32)

        # bg-role örnekleri
        for role, text in [("page","page"), ("panel","panel"), ("elevated","elevated")]:
            w = QLabel(f" bg:{text} ")
            w.setProperty("bg-role", role)
            w.setContentsMargins(8, 4, 8, 4)
            lay.addWidget(w)

        lay.addStretch()
        return grp

    # ── Tema geçişi ───────────────────────────────────────────────────────────

    def _switch(self, theme: str):
        self._theme = theme
        _apply_theme(self._app, theme)
        self._btn_dark.setProperty("style-role",
                                    "tab-active" if theme == "dark" else "tab-inactive")
        self._btn_light.setProperty("style-role",
                                     "tab-active" if theme == "light" else "tab-inactive")
        for btn in [self._btn_dark, self._btn_light]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)


# ── Giriş noktası ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    _apply_theme(app, "dark")
    win = DemoWindow(app)
    win.show()
    sys.exit(app.exec())
