# -*- coding: utf-8 -*-
"""
Teknik Hizmetler — Birleşik Servis Merkezi
════════════════════════════════════════════
Arıza Listesi · Periyodik Bakım · Kalibrasyon Takip

Yapı:
  ┌─ Header (48px): başlık + sekme nav ──────────────────────────────┐
  │  Arızalar | Periyodik Bakım | Kalibrasyon                        │
  ├─ Filtre çubuğu (40px): Cihaz combo + durum + arama ─────────────┤
  └─ QStackedWidget                                                   │
       ArizaPanel / BakimPanel / KalibrasyonPanel  (lazy-load)       │

Cihaz seçilmeden: tüm kayıtlar listelenir
Cihaz seçilince : sadece o cihaza ait kayıtlar
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QComboBox, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

TABS = [
    ("ARIZA",       "🔧  Arızalar"),
    ("BAKIM",       "🛠  Periyodik Bakım"),
    ("KALIBRASYON", "📐  Kalibrasyon"),
]


class TeknikHizmetlerPage(QWidget):
    """Arıza + Bakım + Kalibrasyon tek ekranda."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db          = db
        self._cihazlar   = []   # [{"Cihazid": ..., "Marka": ..., "Model": ...}]
        self._cihaz_id   = ""   # "" = tüm cihazlar
        self._modules    = {}   # code → widget (lazy)
        self._nav_btns   = {}   # code → QPushButton
        self._active_tab = ""

        self._setup_ui()
        self._load_cihazlar()
        self._switch_tab("ARIZA")

    # ═══════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setStyleSheet(STYLES["page"])
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_filtre_bar())

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

    # ── Header ──────────────────────────────────────────

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {C.BG_SECONDARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Üst şerit
        top = QWidget()
        top.setFixedHeight(48)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 0, 16, 0)
        tl.setSpacing(12)

        lbl = QLabel("Teknik Hizmetler")
        lbl.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        tl.addWidget(lbl)
        tl.addStretch()

        btn_yenile = QPushButton("⟳  Yenile")
        btn_yenile.setFixedHeight(28)
        btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        btn_yenile.clicked.connect(self._yenile)
        tl.addWidget(btn_yenile)
        lay.addWidget(top)

        # Sekme nav (36px)
        nav = QWidget()
        nav.setFixedHeight(36)
        nav.setStyleSheet(f"background:transparent; border-top:1px solid {C.BORDER_SECONDARY};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(16, 0, 16, 0)
        nl.setSpacing(0)
        for code, label in TABS:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self._tab_qss(False))
            btn.clicked.connect(lambda _=False, c=code: self._switch_tab(c))
            self._nav_btns[code] = btn
            nl.addWidget(btn)
        nl.addStretch()
        lay.addWidget(nav)
        return frame

    # ── Filtre Çubuğu ───────────────────────────────────

    def _build_filtre_bar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(44)
        frame.setStyleSheet(
            f"QFrame{{background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        # Cihaz etiketi
        lbl = QLabel("Cihaz:")
        lbl.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(lbl)

        # Cihaz combo
        self.combo_cihaz = QComboBox()
        self.combo_cihaz.setFixedWidth(260)
        self.combo_cihaz.setStyleSheet(STYLES["combo"])
        self.combo_cihaz.setEditable(True)
        self.combo_cihaz.setInsertPolicy(QComboBox.NoInsert)
        self.combo_cihaz.lineEdit().setPlaceholderText("Tüm cihazlar…")
        self.combo_cihaz.currentIndexChanged.connect(self._on_cihaz_changed)
        lay.addWidget(self.combo_cihaz)

        sep = QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        lay.addWidget(sep)

        # Özet sayaçlar (aktif sekmeye göre güncellenir)
        self.lbl_ozet = QLabel("")
        self.lbl_ozet.setStyleSheet(f"color:{C.TEXT_MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(self.lbl_ozet)

        lay.addStretch()

        # Temizle butonu
        self.btn_temizle = QPushButton("✕  Filtreyi Temizle")
        self.btn_temizle.setFixedHeight(26)
        self.btn_temizle.setStyleSheet(STYLES["cancel_btn"])
        self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_temizle.setVisible(False)
        self.btn_temizle.clicked.connect(self._filtre_temizle)
        lay.addWidget(self.btn_temizle)

        return frame

    # ═══════════════════════════════════════════════════
    #  VERİ
    # ═══════════════════════════════════════════════════

    def _load_cihazlar(self):
        """Cihaz listesini DB'den yükle, combo'ya doldur."""
        if not self.db:
            return
        try:
            from core.di import get_registry
            tum = get_registry(self.db).get("Cihazlar").get_all()
            self._cihazlar = sorted(tum, key=lambda r: (
                str(r.get("Marka", "") or ""),
                str(r.get("Model", "") or "")
            ))
        except Exception as e:
            logger.error(f"TeknikHizmetler cihaz yükleme: {e}")
            self._cihazlar = []

        self.combo_cihaz.blockSignals(True)
        self.combo_cihaz.clear()
        self.combo_cihaz.addItem("— Tüm Cihazlar —", userData="")
        for r in self._cihazlar:
            cid   = str(r.get("Cihazid", ""))
            marka = str(r.get("Marka", "") or "")
            model = str(r.get("Model", "") or "")
            tip   = str(r.get("CihazTipi", "") or "")
            label = f"{marka} {model}".strip() or cid
            if tip:
                label += f"  [{tip}]"
            self.combo_cihaz.addItem(label, userData=cid)
        self.combo_cihaz.blockSignals(False)

    def load_data(self):
        """Dışarıdan çağrılabilir — cihaz listesini yenile, aktif paneli yenile."""
        self._load_cihazlar()
        self._yenile()

    # ═══════════════════════════════════════════════════
    #  SEKME
    # ═══════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_qss(c == code))
        self._active_tab = code

        if code not in self._modules:
            self._modules[code] = self._create_panel(code)
            self.stack.addWidget(self._modules[code])

        self.stack.setCurrentWidget(self._modules[code])
        self._update_ozet()

    def _create_panel(self, code: str) -> QWidget:
        try:
            if code == "ARIZA":
                from ui.pages.cihaz.components.ariza_panel import ArizaPanel
                w = ArizaPanel(cihaz_id=self._cihaz_id, db=self.db)
                w.ariza_eklendi.connect(self._update_ozet)
                return w
            elif code == "BAKIM":
                from ui.pages.cihaz.components.bakim_panel import BakimPanel
                w = BakimPanel(cihaz_id=self._cihaz_id, db=self.db)
                w.kayit_eklendi.connect(self._update_ozet)
                return w
            elif code == "KALIBRASYON":
                from ui.pages.cihaz.components.kalibrasyon_panel import KalibrasyonPanel
                w = KalibrasyonPanel(cihaz_id=self._cihaz_id, db=self.db)
                w.kayit_eklendi.connect(self._update_ozet)
                return w
        except Exception as e:
            logger.error(f"TeknikHizmetler panel oluşturma ({code}): {e}")
            err = QLabel(f"Panel yüklenemedi:\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(f"color:{C.STATUS_ERROR};")
            return err
        return QWidget()

    # ═══════════════════════════════════════════════════
    #  FİLTRE
    # ═══════════════════════════════════════════════════

    def _on_cihaz_changed(self, idx: int):
        cid = self.combo_cihaz.itemData(idx) or ""
        self._cihaz_id = cid
        self.btn_temizle.setVisible(bool(cid))
        self._propagate_cihaz()

    def _propagate_cihaz(self):
        """Seçili cihazı tüm yüklenmiş panellere ilet."""
        for code, panel in self._modules.items():
            if hasattr(panel, "set_cihaz"):
                try:
                    panel.set_cihaz(self._cihaz_id)
                except Exception as e:
                    logger.error(f"set_cihaz ({code}): {e}")
        self._update_ozet()

    def _filtre_temizle(self):
        self.combo_cihaz.setCurrentIndex(0)   # "— Tüm Cihazlar —" → _on_cihaz_changed tetiklenir

    def _yenile(self):
        for panel in self._modules.values():
            if hasattr(panel, "load_data"):
                try:
                    panel.load_data()
                except Exception as e:
                    logger.error(f"Panel yenile hatası: {e}")
        self._update_ozet()

    # ═══════════════════════════════════════════════════
    #  ÖZET BANDI
    # ═══════════════════════════════════════════════════

    def _update_ozet(self):
        """Aktif sekmenin kayıt sayısını filtre çubuğunda göster."""
        panel = self._modules.get(self._active_tab)
        if panel is None:
            self.lbl_ozet.setText("")
            return
        try:
            data = getattr(panel, "_all_data", [])
            n = len(data)
            if self._active_tab == "ARIZA":
                acik    = sum(1 for r in data if str(r.get("Durum","")) == "Açık")
                islemde = sum(1 for r in data if str(r.get("Durum","")) == "İşlemde")
                self.lbl_ozet.setText(
                    f"Toplam {n} arıza  ·  "
                    f"<span style='color:{C.STATUS_ERROR}'>Açık {acik}</span>  ·  "
                    f"<span style='color:{C.STATUS_WARNING}'>İşlemde {islemde}</span>"
                )
                self.lbl_ozet.setTextFormat(Qt.RichText)
            elif self._active_tab == "BAKIM":
                import datetime
                bugun = datetime.date.today()
                acil  = sum(1 for r in data
                            if self._gun_kalan(r.get("PlanlananTarih",""), bugun) <= 0)
                yakin = sum(1 for r in data
                            if 0 < self._gun_kalan(r.get("PlanlananTarih",""), bugun) <= 30)
                self.lbl_ozet.setText(
                    f"Toplam {n} plan  ·  "
                    f"<span style='color:{C.STATUS_ERROR}'>Gecikmiş {acil}</span>  ·  "
                    f"<span style='color:{C.STATUS_WARNING}'>30 gün içinde {yakin}</span>"
                )
                self.lbl_ozet.setTextFormat(Qt.RichText)
            elif self._active_tab == "KALIBRASYON":
                import datetime
                bugun = datetime.date.today()
                gecmis = sum(1 for r in data
                             if self._gun_kalan(r.get("GecerlilikBitis",""), bugun) < 0)
                yakin  = sum(1 for r in data
                             if 0 <= self._gun_kalan(r.get("GecerlilikBitis",""), bugun) <= 30)
                self.lbl_ozet.setText(
                    f"Toplam {n} kayıt  ·  "
                    f"<span style='color:{C.STATUS_ERROR}'>Süresi geçmiş {gecmis}</span>  ·  "
                    f"<span style='color:{C.STATUS_WARNING}'>30 gün içinde {yakin}</span>"
                )
                self.lbl_ozet.setTextFormat(Qt.RichText)
        except Exception:
            self.lbl_ozet.setText("")

    @staticmethod
    def _gun_kalan(tarih_str: str, bugun) -> int:
        if not tarih_str:
            return 999
        try:
            from core.date_utils import parse_date
            t = parse_date(tarih_str)
            if t:
                return (t - bugun).days
        except Exception:
            pass
        return 999

    # ═══════════════════════════════════════════════════
    #  DIŞ ARAYÜZ — başka sayfalardan tab + cihaz seçerek aç
    # ═══════════════════════════════════════════════════

    def open_tab(self, tab_code: str, cihaz_id: str = ""):
        """
        Dashboard veya cihaz listesinden doğrudan belirli
        bir sekme + cihaz filtresiyle açmak için çağrılır.

        Örnek:
            page.open_tab("ARIZA", cihaz_id="CIH-001")
            page.open_tab("BAKIM")   # tüm cihazlar
        """
        # Önce cihaz filtrele
        if cihaz_id:
            for i in range(self.combo_cihaz.count()):
                if self.combo_cihaz.itemData(i) == cihaz_id:
                    self.combo_cihaz.setCurrentIndex(i)
                    break
        else:
            self.combo_cihaz.setCurrentIndex(0)

        # Sonra sekmeyi aç
        if tab_code in self._nav_btns:
            self._switch_tab(tab_code)

    # ═══════════════════════════════════════════════════
    #  YARDIMCILAR
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{background:transparent;border:none;"
                f"border-bottom:2px solid {C.INPUT_BORDER_FOCUS};"
                f"color:{C.BTN_PRIMARY_TEXT};font-size:12px;font-weight:600;padding:0 16px;}}"
            )
        return (
            "QPushButton{background:transparent;border:none;"
            "border-bottom:2px solid transparent;"
            f"color:{C.TEXT_MUTED};font-size:12px;padding:0 16px;}}"
            f"QPushButton:hover{{color:{C.TEXT_SECONDARY};}}"
        )
