# -*- coding: utf-8 -*-
"""
ArizaPanel — Cihaz 360° Merkez için Arıza Sekmesi
────────────────────────────────────────────────────
• Seçili cihaza ait arızaları tablo olarak gösterir
• Üst kısımda durum özet bandı (Açık / İşlemde / Kapalı)
• Sağdaki hızlı form: ArizaEklePanel inline (popup yok)
• Çift tıklama → ArizaIslemPenceresi
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

ONCELIK_RENK = {
    "Düşük":         "#6b7280",
    "Normal":        "#60a5fa",
    "Yüksek":        "#fb923c",
    "Acil (Kritik)": "#f87171",
}
DURUM_RENK = {
    "Açık":              "#f87171",
    "İşlemde":           "#fb923c",
    "Parça Bekliyor":    "#facc15",
    "Dış Serviste":      "#a78bfa",
    "Kapalı (Çözüldü)":  "#4ade80",
    "Kapalı (İptal)":    "#9ca3af",
}

SUTUNLAR = [
    ("Arizaid",         "Arıza ID",   110),
    ("Cihazid",         "Cihaz",      110),
    ("BaslangicTarihi", "Tarih",       90),
    ("Bildiren",        "Bildiren",   120),
    ("Baslik",          "Konu",       200),
    ("ArizaTipi",       "Tip",        120),
    ("Oncelik",         "Öncelik",     90),
    ("Durum",           "Durum",       90),
]


class ArizaPanel(QWidget):
    """Cihaza özel arıza listesi + hızlı ekleme formu."""

    ariza_eklendi = Signal()

    def __init__(self, cihaz_id: str, db=None, parent=None):
        super().__init__(parent)
        self._cihaz_id = cihaz_id
        self._db       = db
        self._all_data = []
        self._cihaz_map   = {}   # cihaz_id → "Marka Model"
        self._setup_ui()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle{{background:{C.BORDER_PRIMARY};}}")

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 12, 16, 12)
        ll.setSpacing(8)
        ll.addWidget(self._build_ozet_band())
        ll.addWidget(self._build_table(), 1)
        splitter.addWidget(left)

        self.form_panel = self._build_form_panel()
        splitter.addWidget(self.form_panel)
        splitter.setSizes([680, 340])
        root.addWidget(splitter, 1)

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_SECONDARY}; border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        self.lbl_cihaz = QLabel(f"Cihaz: {self._cihaz_id}")
        self.lbl_cihaz.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(self.lbl_cihaz)
        lay.addStretch()

        self.btn_yenile = QPushButton("⟳")
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.clicked.connect(self.load_data)
        lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("+ Yeni Arıza")
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.clicked.connect(self._toggle_form)
        lay.addWidget(self.btn_yeni)
        return frame

    def _build_ozet_band(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_TERTIARY}; border-radius:6px; border:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(20)

        self._ozet_labels = {}
        for key, label, color in [
            ("acik",    "Açık",              "#f87171"),
            ("islemde", "İşlemde",           "#fb923c"),
            ("kapali",  "Kapalı",            "#4ade80"),
        ]:
            lbl = QLabel(f"{label}: 0")
            lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:600; background:transparent;")
            self._ozet_labels[key] = lbl
            lay.addWidget(lbl)

        lay.addStretch()
        self.lbl_toplam = QLabel("Toplam: 0")
        self.lbl_toplam.setStyleSheet(STYLES["footer_label"])
        lay.addWidget(self.lbl_toplam)
        return frame

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(SUTUNLAR))
        tbl.setHorizontalHeaderLabels([s[1] for s in SUTUNLAR])
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setStyleSheet(STYLES["table"])

        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        for i, (_, __, w) in enumerate(SUTUNLAR):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents if w < 150 else QHeaderView.Stretch)

        tbl.doubleClicked.connect(self._on_double_click)
        self.table = tbl
        return tbl

    def _build_form_panel(self) -> QWidget:
        from ui.pages.cihaz.ariza_ekle import ArizaEklePanel
        panel = QWidget()
        panel.setStyleSheet(f"background:{C.BG_SECONDARY}; border-left:1px solid {C.BORDER_PRIMARY};")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(380)

        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)

        # Başlık şeridi
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel("HIZLI ARIZA BİLDİRİMİ")
        lbl.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:11px; font-weight:600; background:transparent;")
        hl.addWidget(lbl); hl.addStretch()
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(20, 20)
        btn_kapat.setStyleSheet("background:transparent; border:none; color:#888;")
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.clicked.connect(lambda: panel.setVisible(False))
        hl.addWidget(btn_kapat)
        pl.addWidget(hdr)

        self.ariza_form = ArizaEklePanel(db=self._db, parent=panel)
        self.ariza_form.formu_sifirla(self._cihaz_id)
        self.ariza_form.kapanma_istegi.connect(lambda: panel.setVisible(False))
        self.ariza_form.kayit_basarili_sinyali.connect(self._on_ariza_saved)
        pl.addWidget(self.ariza_form, 1)

        panel.setVisible(False)
        return panel

    # ═══════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════

    def verileri_yenile(self):
        """İşlem penceresi kapandığında verileri yenilemek için çağrılır."""
        self.load_data()

    def set_cihaz(self, cihaz_id: str):
        """Filtre cihazını değiştir ve yenile. Boş string = tüm cihazlar."""
        self._cihaz_id = cihaz_id.strip()
        self.lbl_cihaz.setText(f"Cihaz: {self._cihaz_id}" if self._cihaz_id else "Tüm Cihazlar")
        if hasattr(self, "ariza_form"):
            self.ariza_form.formu_sifirla(self._cihaz_id)
        self.load_data()

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_registry
            reg = get_registry(self._db)
            tum = reg.get("Cihaz_Ariza").get_all()
            cihaz_list = reg.get("Cihazlar").get_all()
            self._cihaz_map = {
                str(r.get("Cihazid","")): f"{r.get('Marka','')} {r.get('Model','')}".strip()
                for r in cihaz_list
            }
            if self._cihaz_id:
                self._all_data = [r for r in tum
                                  if str(r.get("Cihazid","")).strip() == self._cihaz_id]
            else:
                self._all_data = list(tum)
            self._all_data.sort(key=lambda x: x.get("BaslangicTarihi",""), reverse=True)
            self._populate()
        except Exception as e:
            logger.error(f"ArizaPanel veri yükleme: {e}")

    def _populate(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._all_data))

        acik = islemde = kapali = 0
        for r, row in enumerate(self._all_data):
            for c, (key, _, __) in enumerate(SUTUNLAR):
                if key == "Cihazid":
                    cid = str(row.get("Cihazid",""))
                    cihaz_map = getattr(self, "_cihaz_map", {})
                    ad = cihaz_map.get(cid, "")
                    val = f"{ad} ({cid})" if ad else cid
                else:
                    val = str(row.get(key, "") or "")
                item = QTableWidgetItem(val)

                if key == "Oncelik":
                    item.setForeground(QColor(ONCELIK_RENK.get(val, C.TEXT_SECONDARY)))
                elif key == "Durum":
                    item.setForeground(QColor(DURUM_RENK.get(val, C.TEXT_SECONDARY)))
                    if val == "Açık": acik += 1
                    elif val == "İşlemde": islemde += 1
                    elif val.startswith("Kapalı"): kapali += 1

                item.setData(Qt.UserRole, row)
                self.table.setItem(r, c, item)

        self._ozet_labels["acik"].setText(f"Açık: {acik}")
        self._ozet_labels["islemde"].setText(f"İşlemde: {islemde}")
        self._ozet_labels["kapali"].setText(f"Kapalı: {kapali}")
        self.lbl_toplam.setText(f"Toplam: {len(self._all_data)}")

    # ═══════════════════════════════════════════
    #  AKSİYONLAR
    # ═══════════════════════════════════════════

    def _toggle_form(self):
        if self.form_panel.isVisible():
            self.form_panel.setVisible(False)
        else:
            self.ariza_form.formu_sifirla(self._cihaz_id)
            self.form_panel.setVisible(True)

    def _on_ariza_saved(self):
        self.form_panel.setVisible(False)
        self.load_data()
        self.ariza_eklendi.emit()

    def _on_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return
        try:
            from ui.pages.cihaz.ariza_islem import ArizaIslemPenceresi
            ariza_id = data.get("Arizaid")
            # QWidget'i modal bir pencere gibi göstermek için.
            # self'e atayarak pencerenin GC tarafından toplanmasını engelliyoruz.
            self.islem_penceresi = ArizaIslemPenceresi(ariza_id=ariza_id, ana_pencere=self)
            self.islem_penceresi.setWindowModality(Qt.ApplicationModal)
            self.islem_penceresi.show()
        except Exception as e:
            logger.error(f"ArizaIslem açılamadı: {e}")
            QMessageBox.critical(self, "Hata", f"Arıza detay açılamadı:\n{e}")
