# ui/pages/fhsz/dis_alan_kurulum_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Birim Kurulum Sihirbazı

Kullanıcı yalnızca gerçek operasyonel verileri girer:
  - Hangi birim
  - Hangi yılın verisi
  - Kaç ameliyat/işlem yapıldı
  - Kaçında C-kollu kullanıldı
  - C-kollu ne kadar süre kullanıldı
  - Kaç personel var

Sistem otomatik olarak:
  - C-kollu oranını hesaplar
  - Katsayıyı hesaplar (saat/vaka)
  - Katsayı protokolünü oluşturur
"""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFormLayout, QSpinBox, QDoubleSpinBox,
    QComboBox, QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles.components import STYLES as S
from core.logger import logger


# ─────────────────────────────────────────────────────────────
#  Yardımcı widget: bilgi kartı
# ─────────────────────────────────────────────────────────────

class _InfoKart(QFrame):
    def __init__(self, baslik: str, deger: str = "", aciklama: str = "", vurgu=False):
        super().__init__()
        renk = "#1D75FE" if vurgu else "#457B9D"
        self.setStyleSheet(
            f"QFrame {{ background:#1A2535; border:1px solid {renk}; "
            f"border-radius:8px; padding:0px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        lbl_baslik = QLabel(baslik)
        lbl_baslik.setStyleSheet("font-size:10px; color:#8fa3b8; border:none;")
        lay.addWidget(lbl_baslik)

        self.lbl_deger = QLabel(deger)
        font = QFont()
        font.setPointSize(16 if vurgu else 13)
        font.setBold(vurgu)
        self.lbl_deger.setFont(font)
        self.lbl_deger.setStyleSheet(
            f"color:{'#FFD600' if vurgu else '#E0E0E0'}; border:none;"
        )
        lay.addWidget(self.lbl_deger)

        if aciklama:
            lbl_ac = QLabel(aciklama)
            lbl_ac.setStyleSheet("font-size:10px; color:#666; border:none;")
            lbl_ac.setWordWrap(True)
            lay.addWidget(lbl_ac)

    def set_deger(self, deger: str):
        self.lbl_deger.setText(deger)


# ─────────────────────────────────────────────────────────────
#  Ana sayfa
# ─────────────────────────────────────────────────────────────

class DisAlanKurulumPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._setup_ui()
        self._connect_signals()

    # =========================================================
    #  UI
    # =========================================================

    def _setup_ui(self):
        # Kaydırılabilir alan
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        main = QVBoxLayout(inner)
        main.setContentsMargins(30, 20, 30, 30)
        main.setSpacing(20)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ── Üst bilgi ─────────────────────────────────────────
        baslik = QLabel("Birim Kurulum Sihirbazı")
        baslik.setStyleSheet(
            "font-size:18px; font-weight:bold; color:#1D75FE;"
        )
        main.addWidget(baslik)

        aciklama = QLabel(
            "Biriminizin geçen yılki operasyonel verilerini girin. "
            "Sistem katsayıyı otomatik hesaplar ve önümüzdeki yıl için "
            "tüm ayarları tek tıkla kaydeder."
        )
        aciklama.setStyleSheet("font-size:11px; color:#8fa3b8;")
        aciklama.setWordWrap(True)
        main.addWidget(aciklama)

        # ── Bölüm 1: Birim ve Yıl ─────────────────────────────
        main.addWidget(self._bolum_baslik("1  —  Birim ve Protokol Yılı"))

        form1 = QFormLayout()
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form1.setContentsMargins(0, 0, 0, 0)

        self.cmb_anabilim = QComboBox()
        self.cmb_anabilim.setEditable(True)
        self._sabitler_doldur(self.cmb_anabilim, "AnaBilimDali")
        form1.addRow("Anabilim Dalı:", self.cmb_anabilim)

        self.cmb_birim = QComboBox()
        self.cmb_birim.setEditable(True)
        self._sabitler_doldur(self.cmb_birim, "Birim")
        form1.addRow("Birim:", self.cmb_birim)

        self.spn_veri_yil = QSpinBox()
        self.spn_veri_yil.setRange(2020, date.today().year)
        self.spn_veri_yil.setValue(date.today().year)
        self.spn_veri_yil.setToolTip(
            "Hangi yılın verilerini giriyorsunuz?\n"
            "Genellikle geçen yıl — bu veriden önümüzdeki yıl için katsayı hesaplanır."
        )
        form1.addRow("Protokol geçerlilik yılı:", self.spn_veri_yil)

        main.addLayout(form1)

        # ── Bölüm 2: İşlem verileri ───────────────────────────
        main.addWidget(self._bolum_baslik("2  —  İşlem Verileri"))

        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form2.setContentsMargins(0, 0, 0, 0)

        self.spn_ckollu_gun = QSpinBox()
        self.spn_ckollu_gun.setRange(0, 999)
        self.spn_ckollu_gun.setValue(14)
        self.spn_ckollu_gun.setSuffix("  işlem/gün")
        self.spn_ckollu_gun.setToolTip(
            "Tipik bir iş gününde C-kollu (floroskopi) kullanılan işlem sayısı.\n"
            "Örnek: Günde 22 ameliyattan 14'ünde C-kollu kullanılıyorsa → 14"
        )
        form2.addRow("Günlük C-kollu kullanan işlem:", self.spn_ckollu_gun)

        self.spn_toplam_gun = QSpinBox()
        self.spn_toplam_gun.setRange(1, 999)
        self.spn_toplam_gun.setValue(22)
        self.spn_toplam_gun.setSuffix("  işlem/gün")
        self.spn_toplam_gun.setToolTip(
            "Tipik bir iş gününde toplam kaç işlem yapılıyor.\n"
            "C-kollu oran = C-kollu işlem / Toplam işlem"
        )
        form2.addRow("Günlük toplam işlem:", self.spn_toplam_gun)

        self.spn_sure = QSpinBox()
        self.spn_sure.setRange(1, 480)
        self.spn_sure.setValue(20)
        self.spn_sure.setSuffix("  dakika")
        self.spn_sure.setToolTip(
            "Her C-kollu kullanımında radyasyona maruz kalınan ortalama süre.\n"
            "Ameliyatın tamamı değil — sadece C-kollu açık olan süre.\n"
            "Örnek: 2 saatlik ameliyatta C-kollu 20 dk kullanılıyorsa → 20"
        )
        form2.addRow("C-kollu kullanım süresi (dk):", self.spn_sure)

        main.addLayout(form2)

        # ── Bölüm 3: Canlı hesap ──────────────────────────────
        main.addWidget(self._bolum_baslik("3  —  Sistem Hesabı (Otomatik)"))

        kart_grid = QHBoxLayout()
        kart_grid.setSpacing(10)

        self.kart_oran    = _InfoKart("C-kollu oran", "—", "C-kollu işlem / Toplam işlem")
        self.kart_katsayi = _InfoKart("Katsayı (saat/vaka)", "—",
                                      "C-kollu süre × oran / 60", vurgu=True)

        for k in [self.kart_oran, self.kart_katsayi]:
            kart_grid.addWidget(k)

        main.addLayout(kart_grid)

        # ── Bölüm 4: Özet ve Kaydet ───────────────────────────
        main.addWidget(self._bolum_baslik("4  —  Kaydet"))

        ozet_frame = QFrame()
        ozet_frame.setStyleSheet(
            "QFrame { background:#0D1A2A; border:1px solid #1D75FE; "
            "border-radius:10px; }"
        )
        ozet_lay = QVBoxLayout(ozet_frame)
        ozet_lay.setContentsMargins(16, 14, 16, 14)
        ozet_lay.setSpacing(6)

        self.lbl_ozet = QLabel("Verileri girdikten sonra özet burada görünecek.")
        self.lbl_ozet.setStyleSheet("font-size:11px; color:#8fa3b8;")
        self.lbl_ozet.setWordWrap(True)
        ozet_lay.addWidget(self.lbl_ozet)

        self.lbl_uyari = QLabel("")
        self.lbl_uyari.setStyleSheet("font-size:11px; color:#FFB300;")
        self.lbl_uyari.setWordWrap(True)
        self.lbl_uyari.setVisible(False)
        ozet_lay.addWidget(self.lbl_uyari)

        main.addWidget(ozet_frame)

        # Kaydet butonu
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        self.btn_hesapla = QPushButton("Hesapla ve Önizle")
        self.btn_hesapla.setStyleSheet(S.get("secondary_btn", S["save_btn"]))
        self.btn_hesapla.setFixedHeight(40)
        self.btn_hesapla.setFixedWidth(160)

        self.btn_kaydet = QPushButton("✓  Kaydet ve Uygula")
        self.btn_kaydet.setStyleSheet(
            "QPushButton { background:#1D75FE; color:#fff; border-radius:8px; "
            "font-size:13px; font-weight:bold; padding:0 24px; }"
            "QPushButton:hover { background:#1558C0; }"
            "QPushButton:disabled { background:#2A3A4A; color:#556; }"
        )
        self.btn_kaydet.setFixedHeight(40)
        self.btn_kaydet.setEnabled(False)

        btn_lay.addWidget(self.btn_hesapla)
        btn_lay.addWidget(self.btn_kaydet)
        main.addLayout(btn_lay)

        main.addStretch()

    # =========================================================
    #  Bölüm başlık yardımcısı
    # =========================================================

    def _bolum_baslik(self, metin: str) -> QLabel:
        lbl = QLabel(metin)
        lbl.setStyleSheet(
            "font-size:12px; font-weight:bold; color:#457B9D; "
            "padding:6px 0 2px 0; border-bottom:1px solid #1A2535;"
        )
        return lbl

    # =========================================================
    #  Sabitler doldurucu
    # =========================================================

    def _sabitler_doldur(self, cmb: QComboBox, kod: str):
        cmb.addItem("")
        if not self._db:
            return
        try:
            from core.di import get_registry
            rows = get_registry(self._db).get("Sabitler").get_all() or []
            for r in sorted(rows, key=lambda x: x.get("MenuEleman", "")):
                if str(r.get("Kod", "")).strip() == kod:
                    val = str(r.get("MenuEleman", "")).strip()
                    if val:
                        cmb.addItem(val)
        except Exception as e:
            logger.error(f"DisAlanKurulumPage._sabitler_doldur({kod}): {e}")

    # =========================================================
    #  Sinyaller
    # =========================================================

    def _connect_signals(self):
        for w in [self.spn_ckollu_gun, self.spn_toplam_gun, self.spn_sure]:
            w.valueChanged.connect(self._canli_hesapla)

        self.btn_hesapla.clicked.connect(self._onizle)
        self.btn_kaydet.clicked.connect(self._kaydet)

    # =========================================================
    #  Canlı hesaplama (kartları günceller)
    # =========================================================

    def _canli_hesapla(self):
        gun_ckollu = self.spn_ckollu_gun.value()
        gun_toplam = self.spn_toplam_gun.value()
        sure       = self.spn_sure.value()

        if gun_toplam == 0:
            return

        oran    = gun_ckollu / gun_toplam
        katsayi = (sure * oran) / 60.0

        self.kart_oran.set_deger(f"{oran:.3f}  ({gun_ckollu}/{gun_toplam})")
        self.kart_katsayi.set_deger(f"{katsayi:.4f}")
        self.btn_kaydet.setEnabled(False)

    # =========================================================
    #  Önizle
    # =========================================================

    def _onizle(self):
        ana   = self.cmb_anabilim.currentText().strip()
        birim = self.cmb_birim.currentText().strip()
        yil   = self.spn_veri_yil.value()

        if not ana:
            QMessageBox.warning(self, "Eksik", "Anabilim Dalı boş olamaz.")
            return
        if not birim:
            QMessageBox.warning(self, "Eksik", "Birim boş olamaz.")
            return

        gun_ckollu = self.spn_ckollu_gun.value()
        gun_toplam = self.spn_toplam_gun.value()
        sure       = self.spn_sure.value()

        if gun_toplam == 0:
            QMessageBox.warning(self, "Hata", "Günlük toplam işlem 0 olamaz.")
            return

        oran    = gun_ckollu / gun_toplam
        katsayi = (sure * oran) / 60.0

        # Mevcut protokol kontrolü
        uyari_metni = ""
        if self._db:
            try:
                from core.di import get_dis_alan_katsayi_service
                mevcut = get_dis_alan_katsayi_service(self._db).get_aktif_katsayi(ana, birim)
                if mevcut:
                    uyari_metni = (
                        f"⚠  Bu birim için zaten aktif bir protokol var "
                        f"(Katsayı: {mevcut.get('Katsayi')}, "
                        f"Başlangıç: {mevcut.get('GecerlilikBaslangic')}). "
                        f"Önce Katsayı Protokolleri ekranından mevcut protokolü "
                        f"pasife alın, sonra burada kaydedin."
                    )
            except Exception:
                pass

        ozet = (
            f"<b>Birim:</b> {ana} / {birim}<br>"
            f"<b>Protokol geçerlilik yılı:</b> {yil}<br><br>"
            f"<b>Oluşturulacak Katsayı Protokolü</b><br>"
            f"  • Katsayı: <b>{katsayi:.4f}</b> saat/vaka<br>"
            f"  • Geçerlilik: {yil}-01-01<br>"
            f"  • Formül: {sure} dk × {oran:.3f} C-kollu oran / 60"
        )

        self.lbl_ozet.setText(ozet)
        self.lbl_uyari.setText(uyari_metni)
        self.lbl_uyari.setVisible(bool(uyari_metni))
        self.btn_kaydet.setEnabled(True)

        self._onizle_veri = {
            "ana": ana, "birim": birim, "yil": yil,
            "oran": oran, "katsayi": katsayi, "sure": sure,
            "gun_ckollu": gun_ckollu, "gun_toplam": gun_toplam,
        }

    # =========================================================
    #  Kaydet
    # =========================================================

    def _kaydet(self):
        if not hasattr(self, "_onizle_veri"):
            QMessageBox.warning(self, "Önce önizleyin",
                                "Lütfen önce 'Hesapla ve Önizle' butonuna tıklayın.")
            return
        if not self._db:
            QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        v = self._onizle_veri

        try:
            from core.di import get_dis_alan_katsayi_service
            kat_svc = get_dis_alan_katsayi_service(self._db)
            protokol = {
                "AnaBilimDali":        v["ana"],
                "Birim":               v["birim"],
                "GecerlilikBaslangic": f"{v['yil']}-01-01",
                "Katsayi":             round(v["katsayi"], 4),
                "OrtSureDk":           v["sure"],
                "AlanTipAciklama":     f"{v['birim']} — Kurulum sihirbazı",
                "AciklamaFormul":      (
                    f"{v['sure']} dk × {v['oran']:.3f} C-kollu / 60 = {v['katsayi']:.4f}"
                ),
                "ProtokolRef":         (
                    f"Sihirbaz | {v['gun_ckollu']}/{v['gun_toplam']} C-kollu/gün, "
                    f"{v['sure']} dk"
                ),
                "Aktif":               1,
                "KaydedenKullanici":   "Kurulum Sihirbazı",
            }
            ok = kat_svc.protokol_ekle(protokol)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            return

        if ok:
            QMessageBox.information(
                self, "Kurulum Tamamlandı",
                f"{v['ana']} / {v['birim']} için katsayı protokolü oluşturuldu.\n\n"
                f"Katsayı : {v['katsayi']:.4f} saat/vaka\n"
                f"Geçerlilik : {v['yil']}-01-01 tarihinden itibaren\n\n"
                f"Artık bu birimden Excel import yapabilirsiniz."
            )
            self.btn_kaydet.setEnabled(False)
            del self._onizle_veri
        else:
            QMessageBox.warning(
                self, "Eklenemedi",
                f"{v['yil']}-01-01 başlangıç tarihli bir protokol zaten mevcut.\n"
                "Önce Katsayı Protokolleri ekranından mevcut protokolü pasife alın."
            )
