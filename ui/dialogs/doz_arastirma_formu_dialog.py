# -*- coding: utf-8 -*-
"""
ui/dialogs/doz_arastirma_formu_dialog.py
═══════════════════════════════════════════════════════════════
RADAT Doz Araştırma Formu (RD.F43) — Basitleştirilmiş PySide6 Dialog

Kaynak: TAEK/RADAT RD.F43 Rev.01 (10.10.2022)

Kullanım
--------
from ui.dialogs.doz_arastirma_formu_dialog import DozArastirmaFormuDialog

    dialog = DozArastirmaFormuDialog(
        parent=self,
        olcum_kaydi={
            "AdSoyad":      "BİRSEN FIRAT",
            "KimlikNo":     "14522068356",
            "CalistiBirim": "Radyoloji A.B.D.",
            "DozimetreNo":  "992378",
            "DozimetriTipi":"TLD",
            "Yil":          2023,
            "Periyot":      3,
            "PeriyotAdi":   "Temmuz–Eylül",
            "Hp10":         15.20,
        },
    )
    if dialog.exec():
        veri = dialog.get_form_data()
        # veri → dict, veritabanına kaydet
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QCheckBox, QRadioButton,
    QPushButton, QFrame, QGroupBox, QButtonGroup,
    QScrollArea, QWidget, QSpinBox, QDoubleSpinBox,
    QSizePolicy,
)

from core.logger import logger


# ─────────────────────────────────────────────────────────────
#  Küçük yardımcı widget'lar
# ─────────────────────────────────────────────────────────────

def _baslik(metin: str) -> QLabel:
    lbl = QLabel(metin)
    lbl.setProperty("style-role", "section-title")
    lbl.setProperty("color-role", "primary")
    return lbl


def _alt_baslik(metin: str) -> QLabel:
    lbl = QLabel(metin)
    lbl.setProperty("color-role", "muted")
    lbl.setProperty("style-role", "caption")
    return lbl


def _ayrac() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setProperty("color-role", "muted")
    return f


def _evet_hayir_grup(parent_widget) -> tuple[QButtonGroup, QRadioButton, QRadioButton]:
    """(grup, evet_radio, hayir_radio) döndürür."""
    grup = QButtonGroup(parent_widget)
    evet  = QRadioButton("Evet")
    hayir = QRadioButton("Hayır")
    hayir.setChecked(True)
    grup.addButton(evet,  1)
    grup.addButton(hayir, 0)
    evet.setProperty("color-role", "primary")
    hayir.setProperty("color-role", "primary")
    return grup, evet, hayir


def _evet_hayir_satir(soru_no: str, soru: str,
                      parent_widget) -> tuple[QHBoxLayout, QButtonGroup, QTextEdit]:
    """
    Soru | O Evet  O Hayır | [Açıklama alanı]
    Döndürür: (lay, button_group, aciklama_edit)
    """
    lay  = QHBoxLayout()
    lay.setSpacing(12)

    no_lbl = QLabel(soru_no + ".")
    no_lbl.setProperty("color-role", "muted")
    no_lbl.setFixedWidth(20)
    lay.addWidget(no_lbl)

    soru_lbl = QLabel(soru)
    soru_lbl.setWordWrap(True)
    soru_lbl.setProperty("color-role", "primary")
    soru_lbl.setMinimumWidth(260)
    soru_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    lay.addWidget(soru_lbl, 2)

    grup, evet, hayir = _evet_hayir_grup(parent_widget)
    eh_lay = QHBoxLayout()
    eh_lay.setSpacing(8)
    eh_lay.addWidget(evet)
    eh_lay.addWidget(hayir)
    lay.addLayout(eh_lay)

    aciklama = QTextEdit()
    aciklama.setPlaceholderText("Evet ise açıklayınız…")
    aciklama.setFixedHeight(46)
    aciklama.setProperty("style-role", "form")
    aciklama.setEnabled(False)
    aciklama.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    lay.addWidget(aciklama, 2)

    # Evet seçilince açıklama aktif olur
    evet.toggled.connect(aciklama.setEnabled)

    return lay, grup, aciklama


# ─────────────────────────────────────────────────────────────
#  Ana Dialog
# ─────────────────────────────────────────────────────────────

class DozArastirmaFormuDialog(QDialog):
    """
    RADAT Doz Araştırma Formu (RD.F43) basitleştirilmiş versiyonu.

    Parameters
    ----------
    olcum_kaydi : dict
        Dozimetre_Olcum tablosundan gelen kayıt.
        Mevcut alanlar otomatik doldurulur.
    """

    def __init__(self, olcum_kaydi: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._kayit = olcum_kaydi or {}
        self.setWindowTitle("Doz Araştırma Formu  —  RADAT RD.F43")
        self.setMinimumWidth(860)
        self.setMinimumHeight(680)
        self.setModal(True)
        self.setProperty("bg-role", "page")
        self._build_ui()
        self._doldur_otomatik()

    # ─── UI inşa ──────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Başlık bandı ──────────────────────────────────────
        baslik_frame = QFrame()
        baslik_frame.setProperty("bg-role", "panel")
        baslik_frame.setProperty("style-role", "dialog-header")
        baslik_lay = QHBoxLayout(baslik_frame)
        baslik_lay.setContentsMargins(24, 14, 24, 14)

        sol = QVBoxLayout()
        sol.setSpacing(2)
        ana_baslik = QLabel("DOZ ARAŞTIRMA FORMU")
        ana_baslik.setProperty("style-role", "dialog-title")
        ana_baslik.setProperty("color-role", "primary")
        alt = QLabel("TAEK/RADAT  •  RD.F43 Rev.01  •  10.10.2022")
        alt.setProperty("color-role", "muted")
        alt.setProperty("style-role", "caption")
        sol.addWidget(ana_baslik)
        sol.addWidget(alt)
        baslik_lay.addLayout(sol, 1)

        # Form No + Tarih
        sag = QVBoxLayout()
        sag.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_form_no = QLabel("Form No: —")
        self._lbl_form_no.setProperty("color-role", "muted")
        self._lbl_form_no.setProperty("style-role", "mono")
        self._lbl_tarih = QLabel(f"Tarih: {date.today().strftime('%d.%m.%Y')}")
        self._lbl_tarih.setProperty("color-role", "muted")
        sag.addWidget(self._lbl_form_no, alignment=Qt.AlignmentFlag.AlignRight)
        sag.addWidget(self._lbl_tarih,   alignment=Qt.AlignmentFlag.AlignRight)
        baslik_lay.addLayout(sag)
        root.addWidget(baslik_frame)

        # ── Kaydırılabilir içerik alanı ──────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("bg-role", "page")

        icerik = QWidget()
        icerik.setProperty("bg-role", "page")
        icerik_lay = QVBoxLayout(icerik)
        icerik_lay.setContentsMargins(24, 20, 24, 20)
        icerik_lay.setSpacing(20)

        # 3 bölüm
        icerik_lay.addWidget(self._bolum_a())   # Dozimetri Servisi
        icerik_lay.addWidget(_ayrac())
        icerik_lay.addWidget(self._bolum_b())   # Kullanıcı soruları
        icerik_lay.addWidget(_ayrac())
        icerik_lay.addWidget(self._bolum_c())   # RK Sorumlusu soruları
        icerik_lay.addStretch()

        scroll.setWidget(icerik)
        root.addWidget(scroll, 1)

        # ── Alt butonlar ──────────────────────────────────────
        alt_frame = QFrame()
        alt_frame.setProperty("bg-role", "panel")
        alt_frame.setProperty("style-role", "dialog-footer")
        alt_lay = QHBoxLayout(alt_frame)
        alt_lay.setContentsMargins(24, 12, 24, 12)

        self._lbl_zorunlu = QLabel("")
        self._lbl_zorunlu.setProperty("color-role", "warning")
        alt_lay.addWidget(self._lbl_zorunlu, 1)

        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.clicked.connect(self.reject)

        btn_kaydet = QPushButton("💾  Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        btn_kaydet.setDefault(True)
        btn_kaydet.clicked.connect(self._on_kaydet)

        alt_lay.addWidget(btn_iptal)
        alt_lay.addWidget(btn_kaydet)
        root.addWidget(alt_frame)

    # ── Bölüm A — Dozimetri Servisi bilgileri ─────────────────

    def _bolum_a(self) -> QGroupBox:
        gb = QGroupBox("A  —  Dozimetri Servisi Tarafından Doldurulacaktır")
        gb.setProperty("style-role", "group")
        grid = QGridLayout(gb)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        def satir(label_metin, row, col=0, readonly=False) -> QLineEdit:
            grid.addWidget(QLabel(label_metin), row, col)
            e = QLineEdit()
            e.setProperty("style-role", "form")
            if readonly:
                e.setReadOnly(True)
                e.setProperty("color-role", "muted")
            grid.addWidget(e, row, col + 1)
            return e

        # Sol sütun
        self._e_ad_soyad    = satir("Adı Soyadı:",       0, 0)
        self._e_tc_no       = satir("TC Kimlik No:",      1, 0, readonly=True)
        self._e_kurum_adi   = satir("Kuruluş Adı:",       2, 0)
        self._e_kurum_kodu  = satir("Kuruluş Kodu:",      3, 0)
        self._e_uyg_alani   = satir("Uygulama Alanı:",    4, 0)
        self._e_meslek      = satir("Mesleği:",            5, 0)

        # Sağ sütun
        self._e_yil         = satir("Yıl:",                0, 2)
        self._e_periyot     = satir("Periyot:",            1, 2)
        self._e_sure        = satir("Süre:",               2, 2)
        self._e_doz         = satir("Ölçülen Doz (mSv):", 3, 2)
        self._e_dzm_no      = satir("Dozimetre No:",       4, 2)
        self._e_form_no     = satir("Form No:",            5, 2)

        # Dozimetre tipi satırı (tam genişlik)
        grid.addWidget(QLabel("Dozimetre Tipi:"), 6, 0)
        tip_lay = QHBoxLayout()
        self._cb_tld     = QCheckBox("TLD")
        self._cb_osl     = QCheckBox("OSL")
        self._cb_notron  = QCheckBox("Nötron")
        self._cb_elek    = QCheckBox("Elektronik")
        self._cb_diger_tip = QCheckBox("Diğer:")
        self._e_diger_tip  = QLineEdit()
        self._e_diger_tip.setFixedWidth(100)
        self._e_diger_tip.setEnabled(False)
        self._cb_diger_tip.toggled.connect(self._e_diger_tip.setEnabled)

        for w in (self._cb_tld, self._cb_osl, self._cb_notron,
                  self._cb_elek, self._cb_diger_tip, self._e_diger_tip):
            tip_lay.addWidget(w)
        tip_lay.addStretch()
        grid.addLayout(tip_lay, 6, 1, 1, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return gb

    # ── Bölüm B — Kullanıcı Soruları ─────────────────────────

    def _bolum_b(self) -> QGroupBox:
        gb = QGroupBox("B  —  Dozimetre Kullanıcısı Tarafından Doldurulacaktır")
        gb.setProperty("style-role", "group")
        lay = QVBoxLayout(gb)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lay.addWidget(_alt_baslik(
            "Aşağıdaki sorular için dozimetrenin kullanıldığı periyodu dikkate alınız."
        ))

        # Soru 1 — Çalışma günü + süre
        s1_lay = QHBoxLayout()
        no1 = QLabel("1.")
        no1.setProperty("color-role", "muted")
        no1.setFixedWidth(20)
        s1_lay.addWidget(no1)
        s1_lbl = QLabel("Radyasyon kaynağıyla çalışılan iş günü sayısı ve günlük çalışma süresi:")
        s1_lbl.setProperty("color-role", "primary")
        s1_lay.addWidget(s1_lbl, 2)
        self._spin_gun = QSpinBox()
        self._spin_gun.setRange(0, 365)
        self._spin_gun.setSuffix(" gün")
        self._spin_gun.setFixedWidth(90)
        self._spin_saat = QSpinBox()
        self._spin_saat.setRange(0, 24)
        self._spin_saat.setSuffix(" saat/gün")
        self._spin_saat.setFixedWidth(110)
        s1_lay.addWidget(self._spin_gun)
        s1_lay.addWidget(self._spin_saat)
        s1_lay.addStretch()
        lay.addLayout(s1_lay)

        # Soru 2 — Radyasyon kaynağı
        s2_lay = QHBoxLayout()
        no2 = QLabel("2.")
        no2.setProperty("color-role", "muted")
        no2.setFixedWidth(20)
        s2_lay.addWidget(no2)
        s2_lbl = QLabel("Maruz kalınan radyasyonun kaynağı:")
        s2_lbl.setProperty("color-role", "primary")
        s2_lay.addWidget(s2_lbl, 1)
        self._cb_xisini      = QCheckBox("X-ışını cihazı")
        self._cb_kapali_kayn = QCheckBox("Kapalı kaynak")
        self._cb_acik_kayn   = QCheckBox("Açık kaynak")
        self._cb_tesis       = QCheckBox("Tesis")
        self._cb_kaynak_diger = QCheckBox("Diğer:")
        self._e_kaynak_diger  = QLineEdit()
        self._e_kaynak_diger.setFixedWidth(100)
        self._e_kaynak_diger.setEnabled(False)
        self._cb_kaynak_diger.toggled.connect(self._e_kaynak_diger.setEnabled)
        for w in (self._cb_xisini, self._cb_kapali_kayn, self._cb_acik_kayn,
                  self._cb_tesis, self._cb_kaynak_diger, self._e_kaynak_diger):
            s2_lay.addWidget(w)
        s2_lay.addStretch()
        lay.addLayout(s2_lay)

        # Sorular 3–6 — Evet/Hayır
        l3, self._g3, self._a3 = _evet_hayir_satir(
            "3", "Dozimetrenizi sizden başka herhangi biri kullandı mı?", self)
        l4, self._g4, self._a4 = _evet_hayir_satir(
            "4", "Dozimetrenizi kullanmadığınız zamanlarda muhafaza ettiğiniz yer radyasyon alanı içerisinde miydi?", self)
        l5, self._g5, self._a5 = _evet_hayir_satir(
            "5", "Dozimetrenizi radyasyon alanında bıraktığınız veya unuttuğunuz oldu mu?", self)
        l6, self._g6, self._a6 = _evet_hayir_satir(
            "6", "Sağlık nedeniyle tetkik veya tedavi sırasında dozimetrenizi yanlışlıkla yanınızda bulundurdunuz mu?", self)

        for l in (l3, l4, l5, l6):
            lay.addLayout(l)

        # Soru 5 ek — süre ve mesafe
        s5_ek = QHBoxLayout()
        s5_ek.addSpacing(32)
        s5_ek.addWidget(QLabel("Tahmini süre:"))
        self._spin_sure_saat = QSpinBox()
        self._spin_sure_saat.setRange(0, 999)
        self._spin_sure_saat.setSuffix(" saat")
        self._spin_sure_saat.setFixedWidth(90)
        s5_ek.addWidget(self._spin_sure_saat)
        s5_ek.addWidget(QLabel("Kaynağa mesafe:"))
        self._spin_mesafe = QDoubleSpinBox()
        self._spin_mesafe.setRange(0, 999)
        self._spin_mesafe.setSuffix(" m")
        self._spin_mesafe.setFixedWidth(90)
        s5_ek.addWidget(self._spin_mesafe)
        s5_ek.addStretch()
        lay.addLayout(s5_ek)

        # Soru 7 — Korunma donanımları
        s7_lay = QHBoxLayout()
        s7_lay.addWidget(QLabel("7."))
        s7_lay.itemAt(0).widget().setProperty("color-role", "muted")
        s7_lay.addWidget(QLabel("Radyasyondan korunma donanımları:"), 1)
        self._cb_paravan     = QCheckBox("Kurşun paravan")
        self._cb_onluk       = QCheckBox("Kurşun önlük")
        self._cb_gozluk      = QCheckBox("Gözlük")
        self._cb_tiroid      = QCheckBox("Tiroid koruyucu")
        self._cb_eldiven     = QCheckBox("Kurşun eldiven")
        self._cb_don7_diger   = QCheckBox("Diğer:")
        self._e_don7_diger    = QLineEdit()
        self._e_don7_diger.setFixedWidth(100)
        self._e_don7_diger.setEnabled(False)
        self._cb_don7_diger.toggled.connect(self._e_don7_diger.setEnabled)
        for w in (self._cb_paravan, self._cb_onluk, self._cb_gozluk,
                  self._cb_tiroid, self._cb_eldiven,
                  self._cb_don7_diger, self._e_don7_diger):
            s7_lay.addWidget(w)
        s7_lay.addStretch()
        lay.addLayout(s7_lay)

        # Soru 8 — Dozimetre kullanma yeri
        s8_lay = QHBoxLayout()
        s8_lay.addWidget(QLabel("8."))
        s8_lay.itemAt(0).widget().setProperty("color-role", "muted")
        s8_lay.addWidget(QLabel("Dozimetreyi kullandığınız yer:"), 1)
        self._cb_yaka      = QCheckBox("Yaka")
        self._cb_kemer     = QCheckBox("Kemer")
        self._cb_gomlek    = QCheckBox("Gömlek cebi")
        self._cb_onluk_ust = QCheckBox("Önlük üstü")
        self._cb_onluk_alt = QCheckBox("Önlük altı")
        self._cb_el_bilek  = QCheckBox("El/Bilek")
        self._cb_goz_pos   = QCheckBox("Göz")
        for w in (self._cb_yaka, self._cb_kemer, self._cb_gomlek,
                  self._cb_onluk_ust, self._cb_onluk_alt,
                  self._cb_el_bilek, self._cb_goz_pos):
            s8_lay.addWidget(w)
        s8_lay.addStretch()
        lay.addLayout(s8_lay)

        # Soru 9 — Radyoaktif kirlilik
        l9, self._g9, self._a9 = _evet_hayir_satir(
            "9", "Dozimetrenizde radyoaktif kirlilik oldu mu?", self)
        self._a9.setPlaceholderText("Evet ise radyoizotopu belirtiniz (örn: Tc-99, I-131)")
        lay.addLayout(l9)

        # Yorum
        lay.addWidget(_baslik("Yorum / Sonuç:"))
        yorum_lay = QHBoxLayout()
        self._cb_hatali_kul = QCheckBox("Dozimetrenin hatalı kullanımı")
        self._cb_cal_kosul  = QCheckBox("Çalışma koşulu")
        self._cb_kasit      = QCheckBox("Kasıtlı ışınlanma")
        self._cb_yorum_diger = QCheckBox("Diğer:")
        self._e_yorum_diger  = QLineEdit()
        self._e_yorum_diger.setEnabled(False)
        self._cb_yorum_diger.toggled.connect(self._e_yorum_diger.setEnabled)
        self._e_yorum_diger.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for w in (self._cb_hatali_kul, self._cb_cal_kosul,
                  self._cb_kasit, self._cb_yorum_diger, self._e_yorum_diger):
            yorum_lay.addWidget(w)
        yorum_lay.addStretch()
        lay.addLayout(yorum_lay)

        self._e_kullanici_aciklama = QTextEdit()
        self._e_kullanici_aciklama.setPlaceholderText(
            "Kullanıcı notları, ek açıklamalar…")
        self._e_kullanici_aciklama.setFixedHeight(60)
        self._e_kullanici_aciklama.setProperty("style-role", "form")
        lay.addWidget(self._e_kullanici_aciklama)

        return gb

    # ── Bölüm C — Radyasyondan Korunma Sorumlusu ─────────────

    def _bolum_c(self) -> QGroupBox:
        gb = QGroupBox("C  —  Radyasyondan Korunma Sorumlusu Tarafından Doldurulacaktır")
        gb.setProperty("style-role", "group")
        lay = QVBoxLayout(gb)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # Sorular 1–6
        lc1, self._gc1, self._ac1 = _evet_hayir_satir(
            "1", "Tesiste / radyasyon kaynağında / çalışma koşullarında değişiklik oldu mu?", self)
        lc2, self._gc2, _         = _evet_hayir_satir(
            "2", "Kişi radyasyondan korunma konusunda yeterli bilgiye sahip mi?", self)
        lc3, self._gc3, _         = _evet_hayir_satir(
            "3", "Kişiye radyasyondan korunma konusunda hizmet içi eğitim verildi mi?", self)
        lc4, self._gc4, self._ac4 = _evet_hayir_satir(
            "4", "Periyotta olağan dışı bir durum oldu mu?", self)
        lc5, self._gc5, self._ac5 = _evet_hayir_satir(
            "5", "Aynı ortamda çalışan diğer kişilerin dozunda artış oldu mu?", self)
        lc6, self._gc6, self._ac6 = _evet_hayir_satir(
            "6", "Çalışma ortamında radyasyon ölçümlerinde artış izlendi mi?", self)

        for l in (lc1, lc2, lc3, lc4, lc5, lc6):
            lay.addLayout(l)

        # Soru 7 — Hesaplanmış doz
        s7_lay = QHBoxLayout()
        no7 = QLabel("7.")
        no7.setProperty("color-role", "muted")
        no7.setFixedWidth(20)
        s7_lay.addWidget(no7)
        s7_lay.addWidget(QLabel("Hesaplanmış Doz Değeri:"), 1)
        self._spin_hesap_doz = QDoubleSpinBox()
        self._spin_hesap_doz.setRange(0, 9999)
        self._spin_hesap_doz.setDecimals(3)
        self._spin_hesap_doz.setSuffix(" mSv")
        self._spin_hesap_doz.setFixedWidth(130)
        s7_lay.addWidget(self._spin_hesap_doz)
        s7_lay.addWidget(_alt_baslik(
            "(Doz hızı × Süre)"))
        s7_lay.addStretch()
        lay.addLayout(s7_lay)

        # Sorumlu yorumu
        lay.addWidget(_baslik("Sorumlu Yorum / Sonuç:"))
        sor_lay = QHBoxLayout()
        self._cb_sor_hatali  = QCheckBox("Dozimetrenin hatalı kullanımı")
        self._cb_sor_cal_kos = QCheckBox("Çalışma koşulu")
        self._cb_sor_kasit   = QCheckBox("Kasıtlı ışınlanma")
        self._cb_sor_diger    = QCheckBox("Diğer:")
        self._e_sor_diger     = QLineEdit()
        self._e_sor_diger.setEnabled(False)
        self._cb_sor_diger.toggled.connect(self._e_sor_diger.setEnabled)
        self._e_sor_diger.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for w in (self._cb_sor_hatali, self._cb_sor_cal_kos,
                  self._cb_sor_kasit, self._cb_sor_diger, self._e_sor_diger):
            sor_lay.addWidget(w)
        sor_lay.addStretch()
        lay.addLayout(sor_lay)

        self._e_sorumlu_aciklama = QTextEdit()
        self._e_sorumlu_aciklama.setPlaceholderText("Sorumlu notları, alınan önlemler…")
        self._e_sorumlu_aciklama.setFixedHeight(60)
        self._e_sorumlu_aciklama.setProperty("style-role", "form")
        lay.addWidget(self._e_sorumlu_aciklama)

        # İmza satırı
        imza_lay = QGridLayout()
        imza_lay.setHorizontalSpacing(24)
        for col, baslik_txt in enumerate([
            "Dozimetre Kullanıcısı  —  Adı Soyadı / İmza",
            "Radyasyondan Korunma Sorumlusu  —  Adı Soyadı / İmza",
            "Yetkili Kişi  —  Adı Soyadı / İmza",
        ]):
            lbl = QLabel(baslik_txt)
            lbl.setProperty("color-role", "muted")
            lbl.setProperty("style-role", "caption")
            e = QLineEdit()
            e.setProperty("style-role", "form")
            e.setMinimumWidth(180)
            imza_lay.addWidget(lbl, 0, col)
            imza_lay.addWidget(e,   1, col)

        lay.addLayout(imza_lay)

        # Önemli açıklamalar
        lay.addWidget(_alt_baslik(
            "⚠  Bu formun en geç 10 iş günü içerisinde eksiksiz doldurularak "
            "RADAT ve NDK'ya gönderilmesi gerekmektedir."
        ))

        return gb

    # ─── Otomatik doldurma ────────────────────────────────────

    def _doldur_otomatik(self):
        k = self._kayit
        if not k:
            return

        def _set(edit: QLineEdit, val):
            if val is not None:
                edit.setText(str(val))

        _set(self._e_ad_soyad,   k.get("AdSoyad"))
        _set(self._e_tc_no,      k.get("KimlikNo") or k.get("PersonelID"))
        _set(self._e_uyg_alani,  k.get("CalistiBirim"))
        _set(self._e_yil,        k.get("Yil"))
        _set(self._e_periyot,    k.get("Periyot"))
        _set(self._e_dzm_no,     k.get("DozimetreNo"))
        _set(self._e_doz,        k.get("Hp10"))

        # Periyot → süre (yaklaşık)
        _set(self._e_sure, k.get("PeriyotAdi", ""))

        # Dozimetre tipi
        tip = str(k.get("DozimetriTipi") or "").upper()
        if "TLD"       in tip: self._cb_tld.setChecked(True)
        if "OSL"       in tip: self._cb_osl.setChecked(True)
        if "NÖTRON"    in tip: self._cb_notron.setChecked(True)
        if "ELEKTRONİK" in tip or "ELEK" in tip: self._cb_elek.setChecked(True)

        # Form no
        form_no = k.get("RaporNo") or k.get("KayitNo") or "—"
        self._e_form_no.setText(str(form_no))
        self._lbl_form_no.setText(f"Form No: {form_no}")

    # ─── Kaydet ───────────────────────────────────────────────

    def _on_kaydet(self):
        # Zorunlu alan kontrolü
        if not self._e_ad_soyad.text().strip():
            self._lbl_zorunlu.setText("⚠ Adı Soyadı alanı zorunludur.")
            self._e_ad_soyad.setFocus()
            return
        if not self._e_doz.text().strip():
            self._lbl_zorunlu.setText("⚠ Ölçülen Doz (mSv) alanı zorunludur.")
            self._e_doz.setFocus()
            return
        self._lbl_zorunlu.setText("")
        self.accept()

    # ─── Veri okuma ───────────────────────────────────────────

    def get_form_data(self) -> dict:
        """
        Tüm form verilerini dict olarak döndürür.
        dialog.accept() sonrası çağırın.
        """
        def _eh(grup: QButtonGroup) -> str:
            return "Evet" if grup.checkedId() == 1 else "Hayır"

        return {
            # Bölüm A
            "AdSoyad":        self._e_ad_soyad.text().strip(),
            "TCKimlik":        self._e_tc_no.text().strip(),
            "KurulusAdi":      self._e_kurum_adi.text().strip(),
            "KurulusKodu":     self._e_kurum_kodu.text().strip(),
            "UygulamaAlani":   self._e_uyg_alani.text().strip(),
            "Meslek":          self._e_meslek.text().strip(),
            "Yil":             self._e_yil.text().strip(),
            "Periyot":         self._e_periyot.text().strip(),
            "Sures":           self._e_sure.text().strip(),
            "OlculenDoz":      self._e_doz.text().strip(),
            "DozimetreNo":     self._e_dzm_no.text().strip(),
            "FormNo":          self._e_form_no.text().strip(),
            "DozimetriTipi": (
                "TLD"       if self._cb_tld.isChecked()    else
                "OSL"       if self._cb_osl.isChecked()    else
                "Nötron"    if self._cb_notron.isChecked() else
                "Elektronik" if self._cb_elek.isChecked() else
                self._e_diger_tip.text().strip()
            ),
            # Bölüm B — kullanıcı
            "CalismaGunSayisi":   self._spin_gun.value(),
            "GunlukCalismaSaat":  self._spin_saat.value(),
            "KaynakXIsini":       self._cb_xisini.isChecked(),
            "KaynakKapali":       self._cb_kapali_kayn.isChecked(),
            "KaynakAcik":         self._cb_acik_kayn.isChecked(),
            "KaynakTesis":        self._cb_tesis.isChecked(),
            "KaynakDiger":        self._e_kaynak_diger.text().strip(),
            "S3_BaskasıKullandi":  _eh(self._g3),
            "S3_Aciklama":         self._a3.toPlainText().strip(),
            "S4_RadAlaniMuhafaza": _eh(self._g4),
            "S4_Aciklama":         self._a4.toPlainText().strip(),
            "S5_RadAlaniUnutuldu":  _eh(self._g5),
            "S5_SureSaat":         self._spin_sure_saat.value(),
            "S5_MesafeM":          self._spin_mesafe.value(),
            "S5_Aciklama":         self._a5.toPlainText().strip(),
            "S6_TetkikSirasinda":  _eh(self._g6),
            "S6_Aciklama":         self._a6.toPlainText().strip(),
            "KorunmaParavan":      self._cb_paravan.isChecked(),
            "KorunmaOnluk":        self._cb_onluk.isChecked(),
            "KorunmaGozluk":       self._cb_gozluk.isChecked(),
            "KorunmaTiroid":       self._cb_tiroid.isChecked(),
            "KorunmaEldiven":      self._cb_eldiven.isChecked(),
            "DzPositionYaka":      self._cb_yaka.isChecked(),
            "DzPositionKemer":     self._cb_kemer.isChecked(),
            "DzPositionGomlek":    self._cb_gomlek.isChecked(),
            "DzPositionOnlukUst":  self._cb_onluk_ust.isChecked(),
            "DzPositionOnlukAlt":  self._cb_onluk_alt.isChecked(),
            "DzPositionElBilek":   self._cb_el_bilek.isChecked(),
            "S9_RadKirlilik":      _eh(self._g9),
            "S9_Izotop":           self._a9.toPlainText().strip(),
            "Yorum_HataliKullanim": self._cb_hatali_kul.isChecked(),
            "Yorum_CalKosulu":      self._cb_cal_kosul.isChecked(),
            "Yorum_KasitliIsinlama":self._cb_kasit.isChecked(),
            "Yorum_Diger":          self._e_yorum_diger.text().strip(),
            "KullaniciAciklama":    self._e_kullanici_aciklama.toPlainText().strip(),
            # Bölüm C — sorumlu
            "SC1_TesisDegisim":    _eh(self._gc1),
            "SC1_Aciklama":        self._ac1.toPlainText().strip(),
            "SC2_KorunmaBilgi":    _eh(self._gc2),
            "SC3_Egitim":          _eh(self._gc3),
            "SC4_OlaganDisI":      _eh(self._gc4),
            "SC4_Aciklama":        self._ac4.toPlainText().strip(),
            "SC5_DigerArtis":      _eh(self._gc5),
            "SC5_Aciklama":        self._ac5.toPlainText().strip(),
            "SC6_RadArtis":        _eh(self._gc6),
            "SC6_Aciklama":        self._ac6.toPlainText().strip(),
            "HesaplananDoz":       self._spin_hesap_doz.value(),
            "Sor_HataliKullanim":  self._cb_sor_hatali.isChecked(),
            "Sor_CalKosulu":       self._cb_sor_cal_kos.isChecked(),
            "Sor_KasitliIsinlama": self._cb_sor_kasit.isChecked(),
            "Sor_Diger":           self._e_sor_diger.text().strip(),
            "SorumluAciklama":     self._e_sorumlu_aciklama.toPlainText().strip(),
            # Meta
            "FormTarihi":          date.today().isoformat(),
        }
