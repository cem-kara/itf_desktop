# -*- coding: utf-8 -*-
"""
RKE Form Widget'ı
──────────────────
Sol panel: ekipman ekleme / güncelleme formu + muayene geçmişi tablosu.

Sinyaller (dışarıya):
    kaydet_istendi(str mod, dict veri)  – "INSERT" veya "UPDATE"
    temizle_istendi()
    kapat_istendi()
"""
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QTableView, QHeaderView,
    QTextEdit, QAbstractItemView,
)
from PySide6.QtGui import QColor, QCursor, QIntValidator

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.yonetim.rke_table_models import GecmisTableModel
from ui.pages.rke.yonetim.rke_workers import GecmisYukleyiciThread

S = ThemeManager.get_all_component_styles()


class RKEFormWidget(QWidget):
    """
    Sol panel.

    Sinyal         Açıklama
    ─────────────  ─────────────────────────────────────────
    kaydet_istendi(mod, veri)   Kaydet butonuna basıldığında
    temizle_istendi()           Temizle/Yeni butonuna basıldığında
    kapat_istendi()             Vazgeç butonuna basıldığında
    """
    kaydet_istendi  = Signal(str, dict)   # mod, veri
    temizle_istendi = Signal()
    kapat_istendi   = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secili      = None    # dict | None  (mevcut seçili satır)
        self._rke_listesi = []      # kod hesaplaması için dışarıdan set edilir
        self._kisaltma    = {}      # dışarıdan set edilir
        self.ui           = {}      # widget_key → QWidget
        self._combo_db    = {}      # ui_key → sabit_kod

        self._setup_ui()
        self._connect_signals()

    # ═══════════════════════════════════════════
    #  DIŞ ARABIRIM
    # ═══════════════════════════════════════════

    def set_context(self, rke_listesi: list, kisaltma: dict):
        """Ana sayfa tarafından her veri yüklemesinden sonra çağrılır."""
        self._rke_listesi = rke_listesi
        self._kisaltma    = kisaltma

    def fill_combos(self, sabitler: dict):
        """Form combo kutularını sabitler dict'iyle doldurur."""
        for ui_key, db_kod in self._combo_db.items():
            w = self.ui.get(ui_key)
            if w and db_kod in sabitler:
                w.blockSignals(True)
                curr = w.currentText()
                w.clear()
                w.addItem("")
                w.addItems(sorted(sabitler[db_kod]))
                idx = w.findText(curr)
                w.setCurrentIndex(idx if idx >= 0 else 0)
                w.blockSignals(False)

    def load_row(self, row_data: dict):
        """Tabloda bir satır seçildiğinde formu bu veriyle açar (güncelleme modu)."""
        self._secili = row_data
        self.setVisible(True)
        self._grp_durum.setVisible(True)
        self._grp_gecmis.setVisible(True)
        self.ui["KoruyucuCinsi"].setEnabled(False)
        self._fill_form(row_data)
        self._gecmis_yukle(row_data.get("EkipmanNo", ""))
        self.btn_kaydet.setText("GUNCELLE")
        self.btn_temizle.setVisible(False)

    def open_new(self):
        """Yeni kayıt modunda formu açar."""
        self.setVisible(True)
        self._grp_durum.setVisible(False)
        self._grp_gecmis.setVisible(False)
        self.ui["KoruyucuCinsi"].setEnabled(True)
        self._clear()

    def set_busy(self, busy: bool):
        """Kaydetme sırasında progress bar ve buton durumunu yönetir."""
        self._pbar.setVisible(busy)
        self._pbar.setRange(0, 0 if busy else 1)
        self.btn_kaydet.setEnabled(not busy)

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scroll ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 8, 0)
        inner.setSpacing(12)

        # 1. Kimlik
        grp_kimlik = QGroupBox("Kimlik Bilgileri")
        grp_kimlik.setStyleSheet(S.get("group", ""))
        v_kimlik = QVBoxLayout(grp_kimlik)
        v_kimlik.setSpacing(10)

        row1 = QHBoxLayout()
        self.ui["EkipmanNo"]        = self._make_input("Ekipman No (Otomatik)", row1, read_only=True)
        self.ui["KoruyucuNumarasi"] = self._make_input("Koruyucu No (Tam Kod)", row1, read_only=True)
        v_kimlik.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["VarsaDemirbasNo"] = self._make_input("Demirbaş No", row2)
        v_kimlik.addLayout(row2)

        inner.addWidget(grp_kimlik)

        # 2. Özellikler
        grp_ozel = QGroupBox("Ekipman Özellikleri")
        grp_ozel.setStyleSheet(S.get("group", ""))
        v_ozel = QVBoxLayout(grp_ozel)
        v_ozel.setSpacing(10)

        self.ui["AnaBilimDali"] = self._make_combo("Ana Bilim Dalı *", v_ozel, required=True)
        self._combo_db["AnaBilimDali"] = "AnaBilimDali"

        row3 = QHBoxLayout()
        self.ui["Birim"]         = self._make_combo("Birim", row3)
        self.ui["KoruyucuCinsi"] = self._make_combo("Koruyucu Cinsi", row3)
        self._combo_db["Birim"]         = "Birim"
        self._combo_db["KoruyucuCinsi"] = "Koruyucu_Cinsi"
        v_ozel.addLayout(row3)

        row4 = QHBoxLayout()
        self.ui["Bedeni"]         = self._make_combo("Beden", row4)
        self.ui["KursunEsdegeri"] = self._make_combo("Kurşun Eşdeğeri", row4, editable=True)
        self._combo_db["Bedeni"] = "Bedeni"
        v_ozel.addLayout(row4)

        for val in ["0.25 mmPb", "0.35 mmPb", "0.50 mmPb", "1.0 mmPb"]:
            self.ui["KursunEsdegeri"].addItem(val)

        row5 = QHBoxLayout()
        self.ui["HizmetYili"] = self._make_input("Üretim Yılı", row5)
        self.ui["KayitTarih"] = self._make_date("Envanter Giriş", row5)
        v_ozel.addLayout(row5)

        self.ui["HizmetYili"].setValidator(QIntValidator(1900, 2100))
        self.ui["HizmetYili"].setPlaceholderText("Örn: 2024")

        lbl_acik = QLabel("Açıklama:")
        lbl_acik.setStyleSheet(S.get("label", ""))
        self.ui["Aciklama"] = QTextEdit()
        self.ui["Aciklama"].setMaximumHeight(60)
        self.ui["Aciklama"].setStyleSheet(S.get("input", ""))
        v_ozel.addWidget(lbl_acik)
        v_ozel.addWidget(self.ui["Aciklama"])

        inner.addWidget(grp_ozel)

        # 3. Durum
        self._grp_durum = QGroupBox("Durum Bilgileri")
        self._grp_durum.setStyleSheet(S.get("group", ""))
        v_durum = QVBoxLayout(self._grp_durum)
        v_durum.setSpacing(10)

        row6 = QHBoxLayout()
        self.ui["Durum"] = self._make_combo("Durum", row6)
        for d in ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Hurda", "Tamirde", "Kayıp"]:
            self.ui["Durum"].addItem(d)
        self.ui["KontrolTarihi"] = self._make_date("Son Kontrol Tarihi", row6)
        v_durum.addLayout(row6)

        inner.addWidget(self._grp_durum)

        # 4. Muayene Geçmişi
        self._grp_gecmis = QGroupBox("Muayene Geçmişi")
        self._grp_gecmis.setStyleSheet(S.get("group", ""))
        v_gecmis = QVBoxLayout(self._grp_gecmis)

        self._gecmis_model = GecmisTableModel()
        self._gecmis_view  = QTableView()
        self._gecmis_view.setModel(self._gecmis_model)
        self._gecmis_view.setStyleSheet(S.get("table", ""))
        self._gecmis_view.verticalHeader().setVisible(False)
        self._gecmis_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._gecmis_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._gecmis_view.setFixedHeight(140)
        self._gecmis_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v_gecmis.addWidget(self._gecmis_view)

        inner.addWidget(self._grp_gecmis)
        inner.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Progress bar
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        root.addWidget(self._pbar)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(8)

        self.btn_temizle = QPushButton("TEMİZLE / YENİ")
        self.btn_temizle.setStyleSheet(S.get("cancel_btn", ""))
        self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_temizle, "x", color=DarkTheme.TEXT_PRIMARY, size=14)

        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        self._btn_vazgec = QPushButton("VAZGEÇ")
        self._btn_vazgec.setStyleSheet(S.get("close_btn", S.get("cancel_btn", "")))
        self._btn_vazgec.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_vazgec, "x", color=DarkTheme.TEXT_PRIMARY, size=14)

        h_btn.addWidget(self.btn_temizle)
        h_btn.addWidget(self.btn_kaydet)
        h_btn.addWidget(self._btn_vazgec)
        root.addLayout(h_btn)

    # ═══════════════════════════════════════════
    #  YARDIMCI WIDGET FABRİKALARI
    # ═══════════════════════════════════════════

    def _make_input(self, label: str, parent_layout, read_only=False, placeholder="") -> QLineEdit:
        container, lay = self._labeled_container()
        lay.addWidget(self._styled_label(label))
        inp = QLineEdit()
        inp.setStyleSheet(S.get("input", ""))
        if read_only:
            inp.setReadOnly(True)
        if placeholder:
            inp.setPlaceholderText(placeholder)
        lay.addWidget(inp)
        parent_layout.addWidget(container, 1)
        return inp

    def _make_combo(self, label: str, parent_layout, required=False, editable=False) -> QComboBox:
        container, lay = self._labeled_container()
        lay.addWidget(self._styled_label(label, required=required))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.setEditable(editable)
        lay.addWidget(cmb)
        # VBoxLayout: stretch yok; HBoxLayout: stretch=1
        if isinstance(parent_layout, QVBoxLayout):
            parent_layout.addWidget(container)
        else:
            parent_layout.addWidget(container, 1)
        return cmb

    def _make_date(self, label: str, parent_layout) -> QDateEdit:
        container, lay = self._labeled_container()
        lay.addWidget(self._styled_label(label))
        de = QDateEdit()
        de.setStyleSheet(S.get("date", ""))
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setDisplayFormat("yyyy-MM-dd")
        ThemeManager.setup_calendar_popup(de)
        lay.addWidget(de)
        parent_layout.addWidget(container, 1)
        return de

    def _labeled_container(self):
        """Şeffaf arka planlı label+widget sarmalayıcı döndürür."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        return container, lay

    def _styled_label(self, text: str, required=False) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(S.get("required_label" if required else "label", ""))
        return lbl

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self.btn_kaydet.clicked.connect(self._on_save)
        self.btn_temizle.clicked.connect(self._on_temizle)
        self._btn_vazgec.clicked.connect(self.kapat_istendi)

        self.ui["AnaBilimDali"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["Birim"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["KoruyucuCinsi"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["KayitTarih"].dateChanged.connect(self._tarih_hesapla)

    def _on_temizle(self):
        self._clear()
        self.temizle_istendi.emit()

    # ═══════════════════════════════════════════
    #  KAYDET
    # ═══════════════════════════════════════════

    def _on_save(self):
        if not self.ui["EkipmanNo"].text().strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Ekipman No zorunludur (Ana Bilim Dalı ve Cinsi seçin).")
            return

        veri = {}
        for key, w in self.ui.items():
            if isinstance(w, QLineEdit):
                veri[key] = w.text().strip()
            elif isinstance(w, QComboBox):
                veri[key] = w.currentText().strip()
            elif isinstance(w, QDateEdit):
                veri[key] = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, QTextEdit):
                veri[key] = w.toPlainText().strip()

        mod = "UPDATE" if self._secili else "INSERT"
        if mod == "UPDATE":
            veri["EkipmanNo"] = self._secili.get("EkipmanNo")
        else:
            veri["KontrolTarihi"] = veri.get("KayitTarih", "")
            veri["Durum"]         = "Kullanıma Uygun"

        self.kaydet_istendi.emit(mod, veri)

    # ═══════════════════════════════════════════
    #  TEMİZLE
    # ═══════════════════════════════════════════

    def _clear(self):
        self._secili = None
        for w in self.ui.values():
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
            elif isinstance(w, QDateEdit):
                w.setDate(QDate.currentDate())
            elif isinstance(w, QTextEdit):
                w.clear()

        self.ui["HizmetYili"].setText(str(QDate.currentDate().year()))
        self.ui["Durum"].setCurrentText("Kullanıma Uygun")
        self.ui["KontrolTarihi"].setDate(self.ui["KayitTarih"].date())
        self.ui["KoruyucuCinsi"].setEnabled(True)
        self._gecmis_model.set_data([])

        self.btn_kaydet.setText("KAYDET")
        self.btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self.btn_temizle.setVisible(True)

    # ═══════════════════════════════════════════
    #  FORM DOLDURMAK
    # ═══════════════════════════════════════════

    def _fill_form(self, data: dict):
        for key, w in self.ui.items():
            val = str(data.get(key, ""))
            if isinstance(w, QLineEdit):
                w.setText(val)
            elif isinstance(w, QComboBox):
                i = w.findText(val)
                if i >= 0:
                    w.setCurrentIndex(i)
                elif w.isEditable():
                    w.setEditText(val)
            elif isinstance(w, QDateEdit) and val:
                d = QDate.fromString(val, "yyyy-MM-dd")
                if d.isValid():
                    w.setDate(d)
            elif isinstance(w, QTextEdit):
                w.setPlainText(val)

    # ═══════════════════════════════════════════
    #  MUAYENe GEÇMİŞİ
    # ═══════════════════════════════════════════

    def _gecmis_yukle(self, ekipman_no: str):
        if not ekipman_no:
            return
        if hasattr(self, "_gecmis_loader") and self._gecmis_loader.isRunning():
            return
        self._gecmis_loader = GecmisYukleyiciThread(ekipman_no)
        self._gecmis_loader.gecmis_hazir.connect(self._gecmis_model.set_data)
        self._gecmis_loader.start()

    # ═══════════════════════════════════════════
    #  KOD HESAPLAMA
    # ═══════════════════════════════════════════

    def _hesapla_kod(self):
        abd   = self.ui["AnaBilimDali"].currentText()
        birim = self.ui["Birim"].currentText()
        cins  = self.ui["KoruyucuCinsi"].currentText()

        def kisaltma(grup, deger):
            if not deger:
                return "UNK"
            return self._kisaltma.get(grup, {}).get(deger, deger[:3].upper())

        k_abd  = kisaltma("AnaBilimDali",   abd)
        k_bir  = kisaltma("Birim",          birim)
        k_cins = kisaltma("Koruyucu_Cinsi", cins)

        sayac_genel = sum(
            1 for k in self._rke_listesi
            if str(k.get("KoruyucuCinsi", "")).strip() == cins
        )
        sayac_yerel = sum(
            1 for k in self._rke_listesi
            if str(k.get("KoruyucuCinsi",  "")).strip() == cins
            and str(k.get("AnaBilimDali",  "")).strip() == abd
            and str(k.get("Birim",         "")).strip() == birim
        )

        if not self._secili:
            self.ui["EkipmanNo"].setText(f"RKE-{k_cins}-{str(sayac_genel + 1).zfill(3)}")

        if abd and birim and cins:
            self.ui["KoruyucuNumarasi"].setText(
                f"{k_abd}-{k_bir}-{k_cins}-{str(sayac_yerel + 1).zfill(3)}"
            )

    def _tarih_hesapla(self):
        if not self._secili:
            self.ui["KontrolTarihi"].setDate(self.ui["KayitTarih"].date())
