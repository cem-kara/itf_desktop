# ui/pages/fhsz/dis_alan_import_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Excel Import Ekranı

Akış:
  1. Kullanıcı dosya seçer ve dönemi belirler
  2. "Dosyayı Oku" → önizleme tablosu dolup hatalı satırlar kırmızı gösterilir
  3. Kullanıcı hatalı satırları işaretler (onayla / atla)
  4. "Seçilileri Kaydet" → sadece işaretlenenler DB'ye gider
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QCheckBox, QAbstractItemView,
    QTabWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QDate
from PySide6.QtGui import QColor, QBrush

from typing import Optional
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor, uyari_goster
from core.di import get_dis_alan_import_service, get_dis_alan_katsayi_service, get_dis_alan_service
from ui.styles.icons import IconRenderer

# Renk sabitleri (koyu tema uyumlu)
RENK_TAMAM   = QColor("#1B5E20")   # Koyu yeşil zemin
RENK_UYARI   = QColor("#4A3200")   # Koyu amber zemin
RENK_HATA    = QColor("#4A0000")   # Koyu kırmızı zemin
YAZ_TAMAM    = QColor("#A5D6A7")
YAZ_UYARI    = QColor("#FFE082")
YAZ_HATA     = QColor("#EF9A9A")

SUTUNLAR = [
    ("",              40,  "onay"),          # Onay checkbox
    ("Satır",         48,  "satir_no"),
    ("Durum",         72,  "durum"),
    ("TC Kimlik",    130,  "TCKimlik"),
    ("Ad Soyad",     200,  "AdSoyad"),
    ("Alan",         210,  "IslemTipi"),
    ("Vaka",          60,  "VakaSayisi"),
    ("Katsayı",       72,  "Katsayi"),
    ("Saat",          72,  "HesaplananSaat"),
    ("Hata / Uyarı", 360,  "mesaj"),
]


class _OkuyucuWorker(QObject):
    """Excel okumayı arka planda yapar — UI donmaz."""
    bitti  = Signal(object)   # ImportSonucu
    hata   = Signal(str)

    def __init__(self, svc, dosya, ay, yil, katsayi_cache: Optional[dict] = None):
        super().__init__()
        self._svc           = svc
        self._dosya         = dosya
        self._ay            = ay
        self._yil           = yil
        self._katsayi_cache = katsayi_cache or {}

    def calistir(self):
        try:
            sonuc_yonetici = self._svc.excel_oku(
                self._dosya, self._ay, self._yil,
                katsayi_cache=self._katsayi_cache,
            )
            if sonuc_yonetici.basarili:
                self.bitti.emit(sonuc_yonetici.data)
            else:
                self.hata.emit(sonuc_yonetici.mesaj)
        except Exception as e:
            self.hata.emit(str(e))


class DisAlanImportPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db     = db
        self._sonuc  = None   # Son okunan ImportSonucu
        self._thread = None
        self._import_svc  = get_dis_alan_import_service(db) if db else None
        self._katsayi_svc = get_dis_alan_katsayi_service(db) if db else None
        self._dis_alan_svc = get_dis_alan_service(db) if db else None

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Sekme 1: Excel Import
        self._import_widget = QWidget()
        self._setup_ui()
        self._tabs.addTab(self._import_widget, "Excel Import")

        # Sekme 2: Import Karşılaştırma
        self._karsilastirma_widget = _KarsilastirmaWidget(db=self._db)
        self._tabs.addTab(self._karsilastirma_widget, "Import Karşılaştırma")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._tabs)

        self._connect_signals()

    # ─────────────────────────────────────────────────────────
    #  UI (Sekme 1 — Excel Import)
    # ─────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self._import_widget)
        root.setContentsMargins(20, 15, 20, 15)

        # Üst Bar
        top = QFrame(); top.setProperty("bg-role", "panel"); top.setMaximumHeight(56)
        top_lay = QHBoxLayout(top); top_lay.setContentsMargins(12, 6, 12, 6); top_lay.setSpacing(12)

        lbl = QLabel("Dış Alan Excel Import — RKS Onay Ekranı")
        lbl.setProperty("style-role", "section-title")
        top_lay.addWidget(lbl); top_lay.addStretch()

        # Dosya seçme
        self.btn_dosya = QPushButton("Excel Dosyası Seç")
        self.btn_dosya.setProperty("style-role", "secondary")
        self.btn_dosya.setFixedHeight(36)
        IconRenderer.set_button_icon(self.btn_dosya, "folder", color="#FFFFFF")
        top_lay.addWidget(self.btn_dosya)

        self.lbl_dosya = QLabel("Dosya seçilmedi")
        self.lbl_dosya.setProperty("style-role", "info")
        top_lay.addWidget(self.lbl_dosya)

        self.btn_oku = QPushButton("Dosyayı Oku ve Doğrula")
        self.btn_oku.setProperty("style-role", "action")
        self.btn_oku.setFixedHeight(36)
        self.btn_oku.setEnabled(False)
        top_lay.addWidget(self.btn_oku)

        root.addWidget(top)

        # Araç çubuğu (tümünü seç / yalnızca geçerlileri seç / kaydet)
        ara = QFrame(); ara.setProperty("bg-role", "panel"); ara.setMaximumHeight(48)
        ara_lay = QHBoxLayout(ara); ara_lay.setContentsMargins(12, 4, 12, 4); ara_lay.setSpacing(10)

        self.btn_tumunu_sec   = QPushButton("Tümünü Seç")
        self.btn_gecerlileri  = QPushButton("Yalnızca Geçerlileri Seç")
        self.btn_secimi_kaldir = QPushButton("Seçimi Kaldır")

        for btn in [self.btn_tumunu_sec, self.btn_gecerlileri, self.btn_secimi_kaldir]:
            btn.setFixedHeight(30)
            btn.setProperty("style-role", "secondary")
            btn.setEnabled(False)
            ara_lay.addWidget(btn)

        ara_lay.addStretch()

        self.lbl_ozet = QLabel("")
        self.lbl_ozet.setProperty("style-role", "info")
        ara_lay.addWidget(self.lbl_ozet)


        ara_lay.addStretch()

        self.btn_kaydet = QPushButton("SEÇİLİLERİ KAYDET")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setFixedHeight(34)
        self.btn_kaydet.setEnabled(False)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color="#FFFFFF")
        ara_lay.addWidget(self.btn_kaydet)

        root.addWidget(ara)

        # Ana tablo
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(SUTUNLAR))
        self.tablo.setHorizontalHeaderLabels([s[0] for s in SUTUNLAR])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setProperty("style-role", "table")
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        for i, (_, w, _) in enumerate(SUTUNLAR):
            if i == 0:
                self.tablo.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Fixed)
            elif i == len(SUTUNLAR) - 1:
                self.tablo.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Stretch)
            else:
                self.tablo.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Fixed)
            self.tablo.setColumnWidth(i, w)

        root.addWidget(self.tablo)

    # ─────────────────────────────────────────────────────────
    #  Sinyaller
    # ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.btn_dosya.clicked.connect(self._dosya_sec)
        self.btn_oku.clicked.connect(self._dosyayi_oku)
        self.btn_tumunu_sec.clicked.connect(lambda: self._toplu_sec(True))
        self.btn_gecerlileri.clicked.connect(self._gecerlileri_sec)
        self.btn_secimi_kaldir.clicked.connect(lambda: self._toplu_sec(False))
        self.btn_kaydet.clicked.connect(self._kaydet)

    # ─────────────────────────────────────────────────────────
    #  Dosya seçme
    # ─────────────────────────────────────────────────────────

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "",
            "Excel Dosyaları (*.xlsx *.xlsm);;Tüm Dosyalar (*)"
        )
        if yol:
            self._dosya_yolu = yol
            self.lbl_dosya.setText(yol.split("/")[-1])
            self.btn_oku.setEnabled(True)

    # ─────────────────────────────────────────────────────────
    #  Excel okuma (arka plan thread)
    # ─────────────────────────────────────────────────────────

    def _dosyayi_oku(self):
        if not hasattr(self, "_dosya_yolu"):
            return

        self.btn_oku.setEnabled(False)
        self.btn_oku.setText("Okunuyor…")
        self.tablo.setRowCount(0)
        self.lbl_ozet.setText("")

        from core.di import get_dis_alan_katsayi_service, get_dis_alan_import_service

        # Katsayı verisini ANA THREAD'de çek — worker thread'de DB'ye dokunulmaz
        katsayi_cache = {}
        if self._katsayi_svc:
            try:
                katsayi_sonuc = self._katsayi_svc.get_tum_aktif_dict()
                if katsayi_sonuc.basarili:
                    katsayi_cache = katsayi_sonuc.data or {}
                else:
                    logger.warning(f"Katsayı cache yüklenemedi: {katsayi_sonuc.mesaj}")
            except Exception as e:
                logger.warning(f"Katsayı cache yüklenemedi: {e}")

        svc = self._import_svc

        # Dönem F3'ten okunacak — 0 geçiyoruz
        self._worker = _OkuyucuWorker(svc, self._dosya_yolu, 0, 0, katsayi_cache)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.calistir)
        self._worker.bitti.connect(self._okuma_tamamlandi)
        self._worker.hata.connect(self._okuma_hatasi)
        self._worker.bitti.connect(self._thread.quit)
        self._worker.hata.connect(self._thread.quit)
        self._thread.start()

    def _okuma_tamamlandi(self, sonuc):
        self._sonuc = sonuc
        self.btn_oku.setEnabled(True)
        self.btn_oku.setText("Dosyayı Oku ve Doğrula")
        self._tabloyu_doldur(sonuc)
        self._ozet_guncelle()

        # Okunan dönemi dosya adının yanında göster
        ay_adlari = ["", "Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
        ay_ad = ay_adlari[sonuc.donem_ay] if 1 <= sonuc.donem_ay <= 12 else "?"
        self.lbl_dosya.setText(
            f"{sonuc.dosya}   |   📅 {ay_ad} {sonuc.donem_yil}"
        )
        self.lbl_dosya.setProperty("color-role", "primary")

        for btn in [self.btn_tumunu_sec, self.btn_gecerlileri, self.btn_secimi_kaldir]:
            btn.setEnabled(True)
        self.btn_kaydet.setEnabled(True)

        # Önceki import kontrolü — doğrudan SQLite ile, ana thread'de
        self._onceki_import_kontrol_db(sonuc)

    def _okuma_hatasi(self, mesaj):
        self.btn_oku.setEnabled(True)
        self.btn_oku.setText("Dosyayı Oku ve Doğrula")
        hata_goster(self, mesaj)

    # ─────────────────────────────────────────────────────────
    #  Tablo doldurucu
    # ─────────────────────────────────────────────────────────

    def _tabloyu_doldur(self, sonuc):
        self.tablo.setRowCount(0)
        self.tablo.setRowCount(len(sonuc.satirlar))

        for row_i, satir in enumerate(sonuc.satirlar):
            self.tablo.setRowHeight(row_i, 26)

            # Zemin ve yazı rengi
            if satir.durum == "HATA":
                bg, fg = RENK_HATA, YAZ_HATA
            elif satir.durum == "UYARI":
                bg, fg = RENK_UYARI, YAZ_UYARI
            else:
                bg, fg = RENK_TAMAM, YAZ_TAMAM

            def _item(text, center=False) -> QTableWidgetItem:
                it = QTableWidgetItem(str(text) if text is not None else "")
                it.setBackground(QBrush(bg))
                it.setForeground(QBrush(fg))
                if center:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return it

            # Kolon 0: Onay checkbox
            chk = QCheckBox()
            chk.setChecked(satir.gecerli)   # Varsayılan: geçerliler işaretli
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.addWidget(chk)
            chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk.toggled.connect(lambda checked, s=satir: setattr(s, "kullanici_onayladi", checked))
            self.tablo.setCellWidget(row_i, 0, chk_widget)

            # Satır no
            self.tablo.setItem(row_i, 1, _item(satir.satir_no, center=True))
            # Durum
            self.tablo.setItem(row_i, 2, _item(satir.durum, center=True))

            # Veri alanları
            for col_i, (_, _, alan) in enumerate(SUTUNLAR[3:], start=3):
                if alan == "mesaj":
                    tum = " | ".join(satir.hatalar + satir.uyarilar)
                    self.tablo.setItem(row_i, col_i, _item(tum))
                elif alan in ("Katsayi", "HesaplananSaat"):
                    val = satir.veri.get(alan)
                    txt = f"{val:.2f}" if isinstance(val, (int, float)) else ""
                    self.tablo.setItem(row_i, col_i, _item(txt, center=True))
                elif alan in ("VakaSayisi", "satir_no"):
                    self.tablo.setItem(row_i, col_i, _item(satir.veri.get(alan, ""), center=True))
                else:
                    self.tablo.setItem(row_i, col_i, _item(satir.veri.get(alan, "")))

    # ─────────────────────────────────────────────────────────
    #  Seçim yardımcıları
    # ─────────────────────────────────────────────────────────

    def _toplu_sec(self, durum: bool):
        for row_i in range(self.tablo.rowCount()):
            w = self.tablo.cellWidget(row_i, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.setChecked(durum)

    def _gecerlileri_sec(self):
        if not self._sonuc:
            return
        for row_i, satir in enumerate(self._sonuc.satirlar):
            w = self.tablo.cellWidget(row_i, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.setChecked(satir.gecerli)

    # ─────────────────────────────────────────────────────────
    #  Özet güncelle
    # ─────────────────────────────────────────────────────────

    def _ozet_guncelle(self):
        if not self._sonuc:
            return
        s = self._sonuc
        birim_str = f"{s.anabilim_dali} / {s.birim}".strip(" /")
        self.lbl_ozet.setText(
            f"{birim_str}  |  "
            f"Toplam: {s.toplam_satir}  |  "
            f"✓ Geçerli: {s.gecerli}  |  "
            f"⚠ Uyarılı: {s.uyarili}  |  "
            f"✗ Hatalı: {s.hatali}"
        )


    def _kaydet(self):
        if not self._sonuc:
            return

        if not self._db:
            hata_goster(self, "Veritabanı bağlantısı yok.")
            return

        # Kaç satır işaretli?
        isaretsiz = True
        for row_i in range(self.tablo.rowCount()):
            w = self.tablo.cellWidget(row_i, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    isaretsiz = False
                    break

        if isaretsiz:
            uyari_goster(self, "Kaydedilecek satır seçilmedi.")
            return

        # Hatalı ama onaylananları uyar
        hatali_onaylananlar = [
            s for s in self._sonuc.satirlar
            if not s.gecerli and s.kullanici_onayladi
        ]
        if hatali_onaylananlar:
            if not soru_sor(
                self,
                f"{len(hatali_onaylananlar)} hatalı satır onaylanmış.\n"
                "Bu satırlar eksik veya hatalı veriyle kaydedilecek.\n\n"
                "Devam etmek istiyor musunuz?",
            ):
                return

        from core.di import get_dis_alan_service, get_dis_alan_import_service
        from core.auth.session_context import SessionContext

        # Dönem kilidi — onaylı döneme import engeli
        if self._dis_alan_svc and self._sonuc:
            try:
                ana   = str(self._sonuc.anabilim_dali or "").strip()
                birim = str(self._sonuc.birim or "").strip()
                ay    = self._sonuc.donem_ay
                yil   = self._sonuc.donem_yil
                if ana and birim and ay and yil:
                    svc_dis_alan = self._dis_alan_svc
                    kilitli = svc_dis_alan.get_yillik_ozet_listesi(yil).veri or []
                    kilitli_donem = [
                        r for r in kilitli
                        if str(r.get("DonemAy","")) == str(ay)
                        and str(r.get("DonemYil","")) == str(yil)
                        and int(r.get("RksOnay", 0)) == 1
                    ]
                    if kilitli_donem:
                        kisi_n = len(kilitli_donem)
                        hata_goster(
                            self,
                            f"<b>{ana} / {birim}</b><br>"
                            f"{ay}/{yil} dönemi için <b>{kisi_n} kişi RKS onaylı</b>.<br><br>"
                            "Onaylanmış döneme yeni import yapılamaz.<br>"
                            "Onayı kaldırmak için RKS yöneticisiyle iletişime geçin."
                        )
                        return
            except Exception as e:
                logger.warning(f"Dönem kilidi kontrolü: {e}")

        svc = self._import_svc

        try:
            kaydeden = getattr(SessionContext(), "current_user", None) or "Import"
        except Exception:
            kaydeden = "Import"

        sonuc_yonetici = svc.kaydet(
            self._sonuc,
            dosya_yolu=self._dosya_yolu,
            kaydeden=kaydeden,
        )

        if not sonuc_yonetici.basarili:
            hata_goster(self, sonuc_yonetici.mesaj)
            return

        guncellenmis = sonuc_yonetici.data
        if guncellenmis is not None:
            tutanak_ozet = (
                f"Tutanak No : {guncellenmis.tutanak_no[:18]}…\n"
                if guncellenmis.tutanak_no else ""
            )

            bilgi_goster(
                self,
                f"Kaydedilen : {guncellenmis.kaydedilen} satır\n"
                f"Atlanan    : {guncellenmis.atlanan} satır\n"
                f"{tutanak_ozet}"
                f"\nExcel dosyası Dokumanlar arşivine eklendi.\n"
                f"Dönem özeti için 'Dönem Özeti Hesapla' butonunu kullanın."
            )

            # Tabloyu yenile (kayıt durumunu göster)
            self._tabloyu_doldur(guncellenmis)
            self.btn_kaydet.setEnabled(False)

        # Aynı dönem/birim için önceki import var mı kontrol et
        self._onceki_import_kontrol(guncellenmis, sadece_uyari=False)

    def _onceki_import_kontrol_db(self, sonuc):
        """
        Okuma tamamlandıktan sonra aynı dönem/birim için
        önceki import var mı kontrol eder.
        get_registry yerine doğrudan self._db.execute kullanır
        — ana thread'de güvenle çalışır.
        """
        if not self._db:
            return

        ana   = str(sonuc.anabilim_dali or "").strip()
        birim = str(sonuc.birim or "").strip()
        ay    = sonuc.donem_ay
        yil   = sonuc.donem_yil

        if not (ana and birim and ay and yil):
            return

        try:
            logger.info(
                f"onceki_import_kontrol_db sorgulaniyor: "
                f"ana='{ana}' birim='{birim}' ay={ay} yil={yil}"
            )
            from core.di import get_dis_alan_service
            tum = self._dis_alan_svc.get_calisma_listesi().veri or [] if self._dis_alan_svc else []

            ana_l   = ana.lower()
            birim_l = birim.lower()

            donem_rows = [
                r for r in tum
                if str(r.get("AnaBilimDali","")).strip().lower() == ana_l
                and str(r.get("Birim","")).strip().lower()        == birim_l
                and str(r.get("DonemAy",""))  == str(ay)
                and str(r.get("DonemYil","")) == str(yil)
            ]
            tutanaklar = {str(r.get("TutanakNo","")) for r in donem_rows if r.get("TutanakNo")}
            n_tutanak  = len(tutanaklar)
            n_kisi     = len({str(r.get("TCKimlik","")) or str(r.get("AdSoyad","")) for r in donem_rows})

            logger.info(
                f"onceki_import_kontrol: {ana}/{birim} {ay}/{yil} → "
                f"{n_tutanak} tutanak, {n_kisi} kişi"
            )

            if n_tutanak >= 1:
                ay_adlari = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
                uyari_goster(
                    self,
                    f"<b>{ana} / {birim}</b><br>"
                    f"{ay_adlari[ay]} {yil} dönemi için veritabanında zaten<br>"
                    f"<b>{n_tutanak} import</b> ve <b>{n_kisi} kişi</b> kayıtlı.<br><br>"
                    "Bu dosyayı kaydederseniz yeni bir liste oluşacak.<br>"
                    "Kayıt sonrası <b>Import Karşılaştırma</b> sekmesinden "
                    "iki listeyi karşılaştırıp birleştirebilirsiniz."
                )

        except Exception as e:
            logger.error(f"onceki_import_kontrol_db hatası: {e}")

    def _onceki_import_kontrol(self, sonuc, sadece_uyari: bool = False):
        """
        sadece_uyari=True  → okuma sonrası çağrılır, bilgi/uyarı mesajı verir
        sadece_uyari=False → kayıt sonrası çağrılır, karşılaştırma sekmesine yönlendirir
        """
        if not self._db or not sonuc:
            return

        ana   = str(sonuc.anabilim_dali or "").strip()
        birim = str(sonuc.birim or "").strip()
        ay    = sonuc.donem_ay
        yil   = sonuc.donem_yil

        if not (ana and birim and ay and yil):
            logger.warning(
                f"onceki_import_kontrol: eksik bilgi "
                f"ana='{ana}' birim='{birim}' ay={ay} yil={yil}"
            )
            return

        try:
            from core.di import get_dis_alan_service
            tum = self._dis_alan_svc.get_calisma_listesi().veri or [] if self._dis_alan_svc else []

            ana_lower   = ana.lower()
            birim_lower = birim.lower()

            donem_rows = [
                r for r in tum
                if str(r.get("AnaBilimDali","")).strip().lower() == ana_lower
                and str(r.get("Birim","")).strip().lower()        == birim_lower
                and str(r.get("DonemAy",""))                      == str(ay)
                and str(r.get("DonemYil",""))                     == str(yil)
            ]
            tutanaklar = {
                str(r.get("TutanakNo",""))
                for r in donem_rows
                if r.get("TutanakNo")
            }

            logger.info(
                f"onceki_import_kontrol: {ana}/{birim} {ay}/{yil} → "
                f"{len(donem_rows)} kayıt, {len(tutanaklar)} tutanak"
            )

            if sadece_uyari:
                # Okuma aşaması — kayıt yapılmadı, sadece bilgi ver
                if len(tutanaklar) >= 1:
                    ay_adlari = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                                 "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
                    kisi_n = len({str(r.get("TCKimlik","")) or str(r.get("AdSoyad",""))
                                  for r in donem_rows})
                    uyari_goster(
                        self,
                        f"<b>{ana} / {birim}</b><br>"
                        f"{ay_adlari[ay]} {yil} dönemi için zaten "
                        f"<b>{len(tutanaklar)} import</b> ve <b>{kisi_n} kişi</b> "
                        f"kayıtlı.<br><br>"
                        "Bu dosyayı kaydederseniz yeni bir import oluşacak.<br>"
                        "Kayıt sonrası <b>Import Karşılaştırma</b> sekmesinden "
                        "iki listeyi karşılaştırabilirsiniz."
                    )
            else:
                # Kayıt sonrası — karşılaştırma için yönlendir
                if len(tutanaklar) > 1:
                    if soru_sor(
                        self,
                        f"<b>{ana} / {birim}</b> — {ay}/{yil} dönemi için<br>"
                        f"<b>{len(tutanaklar)} farklı import</b> bulundu.<br><br>"
                        "Hangi listenin kullanılacağını belirlemek için<br>"
                        "<b>Import Karşılaştırma</b> sekmesine geçmek ister misiniz?",
                    ):
                        self._karsilastirma_widget.set_filtre(ana, birim, ay, yil)
                        self._tabs.setCurrentIndex(1)

        except Exception as e:
            logger.warning(f"onceki_import_kontrol: {e}")


# ─────────────────────────────────────────────────────────────
#  Import Karşılaştırma Widget (Sekme 2)
# ─────────────────────────────────────────────────────────────

def _int(v):
    try: return int(v)
    except: return 0

def _float_v(v):
    try: return float(str(v).replace(",","."))
    except: return 0.0

def _kisi_key(r):
    tc = str(r.get("TCKimlik","")).strip()
    return tc if tc else str(r.get("AdSoyad","")).strip().upper()


class _KarsilastirmaWidget(QWidget):
    """
    Aynı dönem ve birim için yüklenmiş iki farklı import listesini
    yan yana karşılaştırır, farkları vurgular, PDF raporu üretir.
    """

    AY_ADLARI = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                 "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._rows_cache: list[dict] = []
        self._analiz: dict | None    = None
        self._dis_alan_svc = get_dis_alan_service(db) if db else None
        self._setup_ui()
        self._connect_signals()

    # ── UI ────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)
        root.setSpacing(10)

        # Filtre
        top = QFrame()
        top.setProperty("bg-role", "panel")
        top.setMaximumHeight(56)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12,6,12,6); tl.setSpacing(10)

        lbl = QLabel("Import Karşılaştırma")
        lbl.setProperty("color-role", "primary")
        tl.addWidget(lbl); tl.addStretch()

        tl.addWidget(QLabel("Anabilim Dalı:"))
        self.cmb_ana = QComboBox(); self.cmb_ana.setFixedWidth(180)
        tl.addWidget(self.cmb_ana)

        tl.addWidget(QLabel("Birim:"))
        self.cmb_bir = QComboBox(); self.cmb_bir.setFixedWidth(150)
        tl.addWidget(self.cmb_bir)

        tl.addWidget(QLabel("Dönem:"))
        self.cmb_ay = QComboBox()
        self.cmb_ay.addItems(self.AY_ADLARI)
        self.cmb_ay.setCurrentIndex(QDate.currentDate().month()-1)
        self.cmb_ay.setFixedWidth(90)
        tl.addWidget(self.cmb_ay)

        self.cmb_yil = QComboBox()
        self.cmb_yil.addItems([str(y) for y in range(
            QDate.currentDate().year()-2, QDate.currentDate().year()+2)])
        self.cmb_yil.setCurrentText(str(QDate.currentDate().year()))
        self.cmb_yil.setFixedWidth(80)
        tl.addWidget(self.cmb_yil)

        self.btn_yukle = QPushButton("Yükle")
        self.btn_yukle.setProperty("style-role", "secondary")
        self.btn_yukle.setFixedHeight(36); self.btn_yukle.setFixedWidth(80)
        tl.addWidget(self.btn_yukle)

        root.addWidget(top)

        # Import listesi seçim paneli
        sel_frame = QFrame()
        sel_frame.setStyleSheet(
            "QFrame { background:#0D1A2A; border-radius:8px; border:0.5px solid #2A3A4A; }"
        )
        sel_lay = QHBoxLayout(sel_frame)
        sel_lay.setContentsMargins(14,10,14,10); sel_lay.setSpacing(16)
        sel_frame.setMaximumHeight(120)

        # Sol liste
        lft = QVBoxLayout()
        lft.addWidget(QLabel("  Liste A (Eski / Birinci):"))
        self.lst_a = QListWidget()
        self.lst_a.setMaximumHeight(70)
        self.lst_a.setProperty("bg-role", "panel")
        lft.addWidget(self.lst_a)

        # Sağ liste
        rgt = QVBoxLayout()
        rgt.addWidget(QLabel("  Liste B (Yeni / İkinci):"))
        self.lst_b = QListWidget()
        self.lst_b.setMaximumHeight(70)
        self.lst_b.setProperty("bg-role", "panel")
        rgt.addWidget(self.lst_b)

        self.btn_karsilastir = QPushButton("Karşılaştır")
        self.btn_karsilastir.setProperty("style-role", "action")
        self.btn_karsilastir.setFixedHeight(40)
        self.btn_karsilastir.setFixedWidth(120)
        self.btn_karsilastir.setEnabled(False)

        sel_lay.addLayout(lft, 1)
        sel_lay.addLayout(rgt, 1)
        sel_lay.addWidget(self.btn_karsilastir)
        root.addWidget(sel_frame)

        # Özet kartlar
        kl = QHBoxLayout(); kl.setSpacing(8)
        self.k_a_kisi  = self._kart("Liste A — Kişi",  "—")
        self.k_b_kisi  = self._kart("Liste B — Kişi",  "—")
        self.k_mukerrer= self._kart("Mükerrer",         "—", "#E65100")
        self.k_eksik_a = self._kart("A'da Eksik",       "—", "#B71C1C")
        self.k_eksik_b = self._kart("B'de Eksik",       "—", "#1565C0")
        self.k_fark    = self._kart("Vaka Farkı Olan",  "—", "#F57F17")
        for k in [self.k_a_kisi, self.k_b_kisi, self.k_mukerrer,
                  self.k_eksik_a, self.k_eksik_b, self.k_fark]:
            kl.addWidget(k)
        root.addLayout(kl)

        # Karşılaştırma tablosu
        self.tablo = QTableWidget()
        kolonlar = [
            ("Durum", 90), ("TC Kimlik", 115), ("Ad Soyad", 190),
            ("Vaka A", 70), ("Vaka B", 70), ("Saat A", 75), ("Saat B", 75),
            ("Fark", 120),
        ]
        self.tablo.setColumnCount(len(kolonlar))
        self.tablo.setHorizontalHeaderLabels([c[0] for c in kolonlar])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setProperty("style-role", "table")
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        hdr = self.tablo.horizontalHeader()
        for i, (_, w) in enumerate(kolonlar):
            if kolonlar[i][0] == "Ad Soyad":
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.tablo.setColumnWidth(i, w)
        root.addWidget(self.tablo)

        # Alt butonlar
        bot = QFrame()
        bot.setProperty("bg-role", "panel")
        bot.setMaximumHeight(50)
        bl = QHBoxLayout(bot)
        bl.setContentsMargins(12,6,12,6); bl.setSpacing(10)

        self.btn_sil_a = QPushButton("Liste A'yı Sil")
        self.btn_sil_a.setStyleSheet(
            "QPushButton { background:#B71C1C; color:#fff; border-radius:6px; "
            "font-weight:bold; padding:0 14px; } "
            "QPushButton:hover { background:#7F0000; } "
            "QPushButton:disabled { background:#2A1A1A; color:#556; }"
        )
        self.btn_sil_a.setFixedHeight(34)
        self.btn_sil_a.setEnabled(False)

        self.btn_sil_b = QPushButton("Liste B'yi Sil")
        self.btn_sil_b.setStyleSheet(
            "QPushButton { background:#1565C0; color:#fff; border-radius:6px; "
            "font-weight:bold; padding:0 14px; } "
            "QPushButton:hover { background:#0D47A1; } "
            "QPushButton:disabled { background:#1A1A2A; color:#556; }"
        )
        self.btn_sil_b.setFixedHeight(34)
        self.btn_sil_b.setEnabled(False)

        self.btn_birlestir = QPushButton("⊕  Listeleri Birleştir")
        self.btn_birlestir.setStyleSheet(
            "QPushButton { background:#2E7D32; color:#fff; border-radius:6px; "
            "font-weight:bold; padding:0 14px; } "
            "QPushButton:hover { background:#1B5E20; } "
            "QPushButton:disabled { background:#1A2A1A; color:#556; }"
        )
        self.btn_birlestir.setFixedHeight(34)
        self.btn_birlestir.setEnabled(False)

        self.btn_pdf = QPushButton("PDF Rapor")
        self.btn_pdf.setProperty("style-role", "secondary")
        self.btn_pdf.setFixedHeight(34)
        self.btn_pdf.setEnabled(False)

        bl.addWidget(self.btn_sil_a)
        bl.addWidget(self.btn_sil_b)
        bl.addWidget(self.btn_birlestir)
        bl.addStretch()
        bl.addWidget(self.btn_pdf)

        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("color-role", "primary")
        bl.addWidget(self.lbl_durum)

        root.addWidget(bot)

    def _kart(self, baslik, val, renk="#457B9D"):
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background:#1A2535; border-radius:8px; "
            f"border-left:3px solid {renk}; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(10,6,10,6); lay.setSpacing(2)
        lb = QLabel(baslik)
        lb.setProperty("color-role", "primary")
        lv = QLabel(str(val))
        lv.setProperty("color-role", "primary")
        lay.addWidget(lb); lay.addWidget(lv)
        setattr(f, "_lv", lv)
        return f

    def _kart_set(self, k, v):
        lv = getattr(k, "_lv", None)
        if lv is not None:
            lv.setText(str(v))

    # ── Sinyaller ─────────────────────────────────────────────

    def _connect_signals(self):
        self.cmb_ana.currentIndexChanged.connect(self._ana_degisti)
        self.btn_yukle.clicked.connect(self._yukle)
        self.lst_a.itemSelectionChanged.connect(self._secim_kontrol)
        self.lst_b.itemSelectionChanged.connect(self._secim_kontrol)
        self.btn_karsilastir.clicked.connect(self._karsilastir)
        self.btn_sil_a.clicked.connect(lambda: self._sil_liste("A"))
        self.btn_sil_b.clicked.connect(lambda: self._sil_liste("B"))
        self.btn_birlestir.clicked.connect(self._birlestir)
        self.btn_pdf.clicked.connect(self._pdf)

    def _secim_kontrol(self):
        ok = bool(self.lst_a.selectedItems() and self.lst_b.selectedItems())
        self.btn_karsilastir.setEnabled(ok)

    # ── Filtre doldur (dışarıdan çağrılabilir) ────────────────

    def set_filtre(self, ana: str, birim: str, ay: int, yil: int):
        """Import tamamlandıktan sonra otomatik doldurma için."""
        self.cmb_ana.setCurrentText(ana)
        self._ana_degisti()
        self.cmb_bir.setCurrentText(birim)
        self.cmb_ay.setCurrentIndex(ay - 1)
        self.cmb_yil.setCurrentText(str(yil))
        self._yukle()

    def _ana_degisti(self):
        if not self._dis_alan_svc:
            return
        try:
            rows = self._dis_alan_svc.get_calisma_listesi().veri or []
            ana = self.cmb_ana.currentText()
            birimler = sorted({
                str(r.get("Birim","")).strip()
                for r in rows
                if r.get("Birim") and (ana == "Tümü" or r.get("AnaBilimDali","") == ana)
            })
            self.cmb_bir.blockSignals(True)
            self.cmb_bir.clear()
            self.cmb_bir.addItems(birimler)
            self.cmb_bir.blockSignals(False)
        except Exception as e:
            logger.error(f"KarsilastirmaWidget._ana_degisti: {e}")

    # ── Veri yükle ────────────────────────────────────────────

    def _yukle(self):
        if not self._dis_alan_svc:
            self.lbl_durum.setText("Veritabanı bağlantısı yok")
            return

        ana   = self.cmb_ana.currentText().strip()
        birim = self.cmb_bir.currentText().strip()
        ay    = self.cmb_ay.currentIndex() + 1
        yil   = int(self.cmb_yil.currentText())

        try:
            rows = self._dis_alan_svc.get_calisma_listesi().veri or []
        except Exception as e:
            logger.error(f"KarsilastirmaWidget._yukle: {e}")
            return

        # Filtre — büyük/küçük harf duyarsız
        rows = [
            r for r in rows
            if _int(r.get("DonemAy")) == ay and _int(r.get("DonemYil")) == yil
        ]
        if ana:
            ana_l = ana.lower()
            rows = [r for r in rows if str(r.get("AnaBilimDali","")).strip().lower() == ana_l]
        if birim:
            birim_l = birim.lower()
            rows = [r for r in rows if str(r.get("Birim","")).strip().lower() == birim_l]

        self._rows_cache = rows

        # TutanakNo → kayıt tarihi ve kişi sayısı
        tutanaklar: dict[str, dict] = {}
        for r in rows:
            tn = str(r.get("TutanakNo","")).strip()
            if not tn:
                continue
            if tn not in tutanaklar:
                tutanaklar[tn] = {
                    "tarih": str(r.get("TutanakTarihi",""))[:10],
                    "kisiler": set(),
                }
            tutanaklar[tn]["kisiler"].add(_kisi_key(r))

        # Tarihe göre sırala
        sirali = sorted(tutanaklar.items(), key=lambda x: x[1]["tarih"])

        self.lst_a.clear()
        self.lst_b.clear()

        for tn, info in sirali:
            label = f"{info['tarih']}  |  {len(info['kisiler'])} kişi  |  {tn[:20]}…"
            item_a = QListWidgetItem(label)
            item_a.setData(Qt.ItemDataRole.UserRole, tn)
            item_b = QListWidgetItem(label)
            item_b.setData(Qt.ItemDataRole.UserRole, tn)
            self.lst_a.addItem(item_a)
            self.lst_b.addItem(item_b)

        if len(sirali) >= 2:
            self.lst_a.setCurrentRow(0)
            self.lst_b.setCurrentRow(len(sirali) - 1)
            self.lbl_durum.setText(
                f"{len(sirali)} import bulundu — A ve B'yi seçip Karşılaştır'a tıklayın"
            )
        elif len(sirali) == 1:
            self.lst_a.setCurrentRow(0)
            self.lbl_durum.setText("Yalnızca 1 import var — karşılaştırma için en az 2 import gerekli")
        else:
            self.lbl_durum.setText("Bu dönem için import bulunamadı")

    # ── Karşılaştır ───────────────────────────────────────────

    def _karsilastir(self):
        a_item = self.lst_a.selectedItems()
        b_item = self.lst_b.selectedItems()
        if not a_item or not b_item:
            return

        tn_a = a_item[0].data(Qt.ItemDataRole.UserRole)
        tn_b = b_item[0].data(Qt.ItemDataRole.UserRole)

        if tn_a == tn_b:
            uyari_goster(
                self,
                "Liste A ve Liste B için aynı import seçildi.\n"
                "Farklı iki import seçin.",
            )
            return

        rows_a = {_kisi_key(r): r for r in self._rows_cache
                  if str(r.get("TutanakNo","")) == tn_a}
        rows_b = {_kisi_key(r): r for r in self._rows_cache
                  if str(r.get("TutanakNo","")) == tn_b}

        tum_kisiler = sorted(set(rows_a) | set(rows_b))

        # Analiz
        sonuclar = []
        mukerrer = eksik_a = eksik_b = fark_vaka = 0

        for k in tum_kisiler:
            ra = rows_a.get(k)
            rb = rows_b.get(k)

            if ra and rb:
                # Her iki listede var
                va = _int(ra.get("VakaSayisi",0))
                vb = _int(rb.get("VakaSayisi",0))
                sa = _float_v(ra.get("HesaplananSaat",0))
                sb = _float_v(rb.get("HesaplananSaat",0))

                if va != vb:
                    durum = "FARK"
                    fark  = f"Vaka: A={va} B={vb} (Δ{vb-va:+d})"
                    fark_vaka += 1
                    bg = QColor("#4A3200"); fg = QColor("#FFE082")
                else:
                    durum = "EŞİT"
                    fark  = ""
                    mukerrer += 1
                    bg = None; fg = QColor("#A5D6A7")

                sonuclar.append({
                    "durum": durum, "key": k,
                    "tc": str(ra.get("TCKimlik","")),
                    "ad": str(ra.get("AdSoyad","")),
                    "va": va, "vb": vb, "sa": sa, "sb": sb,
                    "fark": fark, "bg": bg, "fg": fg,
                })
            elif ra and not rb:
                # Sadece A'da var
                eksik_b += 1
                va = _int(ra.get("VakaSayisi",0))
                sa = _float_v(ra.get("HesaplananSaat",0))
                sonuclar.append({
                    "durum": "SADECE A",
                    "key": k,
                    "tc": str(ra.get("TCKimlik","")),
                    "ad": str(ra.get("AdSoyad","")),
                    "va": va, "vb": 0, "sa": sa, "sb": 0.0,
                    "fark": "B listesinde yok",
                    "bg": QColor("#0A2A3A"), "fg": QColor("#64B5F6"),
                })
            else:
                # Sadece B'de var
                if not rb:
                    continue
                eksik_a += 1
                vb = _int(rb.get("VakaSayisi",0))
                sb = _float_v(rb.get("HesaplananSaat",0))
                sonuclar.append({
                    "durum": "SADECE B",
                    "key": k,
                    "tc": str(rb.get("TCKimlik","")),
                    "ad": str(rb.get("AdSoyad","")),
                    "va": 0, "vb": vb, "sa": 0.0, "sb": sb,
                    "fark": "A listesinde yok",
                    "bg": QColor("#2A0A0A"), "fg": QColor("#EF9A9A"),
                })

        # Önce sorunlular
        sira = {"SADECE A": 0, "SADECE B": 1, "FARK": 2, "EŞİT": 3}
        sonuclar.sort(key=lambda x: sira.get(x["durum"], 9))

        self._analiz = {
            "tn_a": tn_a, "tn_b": tn_b,
            "rows_a": rows_a, "rows_b": rows_b,
            "sonuclar": sonuclar,
            "mukerrer": mukerrer,
            "eksik_a": eksik_a, "eksik_b": eksik_b,
            "fark_vaka": fark_vaka,
        }

        self._tablo_doldur(sonuclar)
        self._kartlar_guncelle(rows_a, rows_b)

        self.btn_sil_a.setEnabled(True)
        self.btn_sil_b.setEnabled(True)
        self.btn_birlestir.setEnabled(True)
        self.btn_pdf.setEnabled(True)
        self.lbl_durum.setText(
            f"A: {len(rows_a)} kişi  |  B: {len(rows_b)} kişi  |  "
            f"Fark: {fark_vaka}  |  Sadece A: {eksik_b}  |  Sadece B: {eksik_a}"
        )

    def _tablo_doldur(self, sonuclar):
        from PySide6.QtGui import QBrush
        self.tablo.setRowCount(0)
        self.tablo.setRowCount(len(sonuclar))

        durum_ikon = {
            "EŞİT":    "✓  Eşit",
            "FARK":    "≠  Fark var",
            "SADECE A":"◀  Sadece A",
            "SADECE B":"▶  Sadece B",
        }

        for i, s in enumerate(sonuclar):
            self.tablo.setRowHeight(i, 24)
            bg = s["bg"]; fg = s["fg"]

            def _it(text, center=False, _bg=bg, _fg=fg):
                it = QTableWidgetItem(str(text) if text is not None else "")
                if _bg:
                    it.setBackground(QBrush(_bg))
                it.setForeground(QBrush(_fg))
                if center:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return it

            self.tablo.setItem(i, 0, _it(durum_ikon.get(s["durum"], s["durum"]), True))
            self.tablo.setItem(i, 1, _it(s["tc"], True))
            self.tablo.setItem(i, 2, _it(s["ad"]))
            self.tablo.setItem(i, 3, _it(str(s["va"]) if s["va"] else "—", True))
            self.tablo.setItem(i, 4, _it(str(s["vb"]) if s["vb"] else "—", True))
            self.tablo.setItem(i, 5, _it(f"{s['sa']:.2f}" if s["sa"] else "—", True))
            self.tablo.setItem(i, 6, _it(f"{s['sb']:.2f}" if s["sb"] else "—", True))
            self.tablo.setItem(i, 7, _it(s["fark"]))

    def _kartlar_guncelle(self, rows_a, rows_b):
        a = self._analiz
        if not a:
            return
        self._kart_set(self.k_a_kisi,   len(rows_a))
        self._kart_set(self.k_b_kisi,   len(rows_b))
        self._kart_set(self.k_mukerrer, a["mukerrer"])
        self._kart_set(self.k_eksik_a,  a["eksik_a"])
        self._kart_set(self.k_eksik_b,  a["eksik_b"])
        self._kart_set(self.k_fark,     a["fark_vaka"])

    # ── Listeleri Birleştir ───────────────────────────────────

    def _birlestir(self):
        """
        A ve B listelerini birleştirir:
          - Sadece A'da → korunur (zaten var)
          - Sadece B'de → A'nın TutanakNo'suyla eklenir
          - İkisinde de var, eşit → dokunulmaz
          - İkisinde de var, FARK VAR → kullanıcı hangisini tercih ettiğini seçer

        Sonuç: B listesi silinir, A listesi eksiksiz hale getirilir.
        """
        if not self._analiz or not self._db:
            return

        a = self._analiz
        farkli = [s for s in a["sonuclar"] if s["durum"] == "FARK"]
        sadece_b = [s for s in a["sonuclar"] if s["durum"] == "SADECE B"]

        # Fark varsa kullanıcıya sor
        tercih_b: set[str] = set()   # Fark olanlar için B'yi tercih edenler

        if farkli:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget as QW, QRadioButton, QButtonGroup, QDialogButtonBox

            dlg = QDialog(self)
            dlg.setWindowTitle("Fark Olan Kayıtlar — Hangisini Kullanacaksınız?")
            dlg.setMinimumWidth(560)
            dlg_lay = QVBoxLayout(dlg)

            ust = QLabel(
                f"<b>{len(farkli)} kayıtta vaka sayısı farklı.</b><br>"
                "Her biri için A listesini mi yoksa B listesini mi kullanmak istediğinizi seçin:"
            )
            ust.setWordWrap(True)
            dlg_lay.addWidget(ust)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            inner = QW()
            inner_lay = QVBoxLayout(inner)
            inner_lay.setSpacing(10)

            grp_list = []   # [(key, btn_a, btn_b)]
            for s in farkli:
                grp_frame = QFrame()
                grp_frame.setStyleSheet(
                    "QFrame { background:#1A2535; border-radius:6px; "
                    "border:0.5px solid #2A3A4A; }"
                )
                grp_lay = QVBoxLayout(grp_frame)
                grp_lay.setContentsMargins(12,8,12,8)
                grp_lay.setSpacing(4)

                lbl_kisi = QLabel(
                    f"<b>{s['ad']}</b>  |  TC: {s['tc']}"
                )
                lbl_kisi.setProperty("color-role", "primary")
                grp_lay.addWidget(lbl_kisi)

                rb_a = QRadioButton(
                    f"Liste A  —  Vaka: {s['va']}  |  Saat: {s['sa']:.2f}"
                )
                rb_b = QRadioButton(
                    f"Liste B  —  Vaka: {s['vb']}  |  Saat: {s['sb']:.2f}"
                )
                rb_a.setChecked(True)   # Varsayılan: A (eski liste)
                rb_a.setProperty("color-role", "primary")
                rb_b.setProperty("color-role", "primary")

                grp = QButtonGroup(grp_frame)
                grp.addButton(rb_a, 0)
                grp.addButton(rb_b, 1)

                grp_lay.addWidget(rb_a)
                grp_lay.addWidget(rb_b)
                inner_lay.addWidget(grp_frame)
                grp_list.append((s["key"], rb_a, rb_b))

            scroll.setWidget(inner)
            dlg_lay.addWidget(scroll)

            btns = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            btns.button(QDialogButtonBox.StandardButton.Ok).setText("Birleştir")
            btns.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            dlg_lay.addWidget(btns)

            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            # Kullanıcının tercihlerini al
            for key, rb_a_btn, rb_b_btn in grp_list:
                if rb_b_btn.isChecked():
                    tercih_b.add(key)

        # Onay mesajı
        msg = (
            f"Birleştirme özeti:\n\n"
            f"• Sadece B'de olan {len(sadece_b)} kişi A listesine eklenecek\n"
        )
        if farkli:
            a_sec = len(farkli) - len(tercih_b)
            b_sec = len(tercih_b)
            msg += (
                f"• Fark olan {len(farkli)} kayıtta:\n"
                f"  - {a_sec} kayıt için Liste A kullanılacak\n"
                f"  - {b_sec} kayıt için Liste B kullanılacak\n"
            )
        msg += f"\nİşlem sonrası B listesi silinecek.\nDevam etmek istiyor musunuz?"

        if not soru_sor(self, msg):
            return

        # ── Birleştirme işlemi ────────────────────────────────
        try:
            svc = self._dis_alan_svc
            tn_a = a["tn_a"]
            tn_b = a["tn_b"]
            eklenen = guncellenen = 0

            # 1. Sadece B'dekiler → A'nın TutanakNo'suyla ekle
            for s in sadece_b:
                rb = a["rows_b"][s["key"]]
                yeni = dict(rb)
                yeni["TutanakNo"] = tn_a   # A listesine dahil et
                kaydet_sonuc = svc.calisma_kaydet(yeni)
                if kaydet_sonuc.basarili:
                    eklenen += 1

            # 2. Fark olanlar için B tercih edilmişse A kaydını güncelle
            for s in farkli:
                if s["key"] in tercih_b:
                    ra = a["rows_a"][s["key"]]
                    rb = a["rows_b"][s["key"]]
                    guncelle_sonuc = svc.calisma_guncelle(
                        ra.get("TCKimlik", ""),
                        ra.get("DonemAy", ""),
                        ra.get("DonemYil", ""),
                        ra.get("TutanakNo", ""),
                        {
                            "VakaSayisi": rb.get("VakaSayisi"),
                            "HesaplananSaat": rb.get("HesaplananSaat"),
                            "Katsayi": rb.get("Katsayi"),
                        },
                    )
                    if guncelle_sonuc.basarili:
                        guncellenen += 1

            # 3. B listesini tamamen sil
            sil_sonuc = svc.tutanak_listesi_sil(tn_b)
            silinen = sil_sonuc.veri or 0

            logger.info(
                f"Import birleştirme: "
                f"eklenen={eklenen} güncellenen={guncellenen} silinen={silinen}"
            )

            bilgi_goster(
                self,
                f"Listelerin birleştirildi.\n\n"
                f"• {eklenen} kişi A listesine eklendi\n"
                f"• {guncellenen} kayıt B'deki değerle güncellendi\n"
                f"• B listesi ({silinen} kayıt) silindi\n\n"
                f"Artık yalnızca tek bir liste mevcut."
            )

            self._analiz = None
            self.tablo.setRowCount(0)
            self.btn_sil_a.setEnabled(False)
            self.btn_sil_b.setEnabled(False)
            self.btn_birlestir.setEnabled(False)
            self.btn_pdf.setEnabled(False)
            self._yukle()

        except Exception as e:
            logger.error(f"KarsilastirmaWidget._birlestir: {e}")
            hata_goster(self, str(e))

    # ── Listeyi Sil ───────────────────────────────────────────

    def _sil_liste(self, taraf: str):
        if not self._analiz or not self._dis_alan_svc:
            return

        tn = self._analiz["tn_a"] if taraf == "A" else self._analiz["tn_b"]
        kisi_n = len(self._analiz["rows_a"] if taraf == "A" else self._analiz["rows_b"])
        label  = f"Liste {'A' if taraf == 'A' else 'B'}"

        if not soru_sor(
            self,
            f"<b>{label}</b> — Tutanak: {tn[:24]}…<br>"
            f"Bu listedeki <b>{kisi_n} kişi</b>ye ait tüm kayıtlar silinecek.<br><br>"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?",
        ):
            return

        try:
            sil_sonuc = self._dis_alan_svc.tutanak_listesi_sil(tn)
            silinen = sil_sonuc.veri or 0

            bilgi_goster(self, f"{label} — {silinen} kayıt silindi.")
            self._analiz = None
            self.tablo.setRowCount(0)
            self.btn_sil_a.setEnabled(False)
            self.btn_sil_b.setEnabled(False)
            self.btn_birlestir.setEnabled(False)
            self.btn_pdf.setEnabled(False)
            self._yukle()
        except Exception as e:
            logger.error(f"KarsilastirmaWidget._sil_liste: {e}")
            hata_goster(self, str(e))

    # ── PDF Rapor ─────────────────────────────────────────────

    def _pdf(self):
        if not self._analiz:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "PDF Kaydet",
            f"import_karsilastirma_{self.cmb_ay.currentIndex()+1}_{self.cmb_yil.currentText()}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer,
                Table, TableStyle, HRFlowable
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            try:
                pdfmetrics.registerFont(TTFont("Arial","arial.ttf"))
                pdfmetrics.registerFont(TTFont("ArialBold","arialbd.ttf"))
                fn, fnb = "Arial", "ArialBold"
            except Exception:
                fn, fnb = "Helvetica", "Helvetica-Bold"
        except ImportError:
            hata_goster(self, "reportlab kurulu değil.\npip install reportlab")
            return

        a   = self._analiz
        ay  = self.cmb_ay.currentIndex() + 1
        yil = int(self.cmb_yil.currentText())
        ana = self.cmb_ana.currentText()
        bir = self.cmb_bir.currentText()

        doc = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=18*mm, rightMargin=18*mm,
            topMargin=18*mm, bottomMargin=18*mm
        )

        h1  = ParagraphStyle("H1", fontName=fnb, fontSize=14, leading=18, spaceAfter=4)
        h2  = ParagraphStyle("H2", fontName=fnb, fontSize=11, leading=14,
                             textColor=colors.HexColor("#1D3557"))
        sm  = ParagraphStyle("S",  fontName=fn,  fontSize=8,  leading=11,
                             textColor=colors.HexColor("#555555"))

        elements = []
        elements.append(Paragraph("DIŞ ALAN IMPORT KARŞILAŞTIRMA RAPORU", h1))
        elements.append(Paragraph(
            f"Dönem: {self.AY_ADLARI[ay-1]} {yil}  |  {ana} / {bir}  |  "
            f"Rapor: {datetime.now().strftime('%d.%m.%Y %H:%M')}", sm
        ))
        elements.append(Spacer(1, 5*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor("#1D3557")))
        elements.append(Spacer(1, 4*mm))

        # Özet
        elements.append(Paragraph("Özet", h2))
        ozet = [
            ["", "Liste A", "Liste B"],
            ["Tutanak", a["tn_a"][:28]+"…", a["tn_b"][:28]+"…"],
            ["Kişi Sayısı", str(len(a["rows_a"])), str(len(a["rows_b"]))],
            ["Toplam Vaka",
             str(sum(_int(r.get("VakaSayisi",0)) for r in a["rows_a"].values())),
             str(sum(_int(r.get("VakaSayisi",0)) for r in a["rows_b"].values()))],
        ]
        ozet_tbl = Table(ozet, colWidths=[40*mm, 65*mm, 65*mm])
        ozet_tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), fn),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("FONTNAME", (0,0), (-1,0),  fnb),
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1D3557")),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("GRID",      (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),
             [colors.HexColor("#F5F5F5"), colors.white]),
        ]))
        elements.append(ozet_tbl)
        elements.append(Spacer(1, 4*mm))

        # Fark özeti
        elements.append(Paragraph("Fark Özeti", h2))
        fark_ozet = [
            ["Durum", "Adet"],
            ["Her iki listede eşit", str(a["mukerrer"])],
            ["Vaka sayısı farklı",   str(a["fark_vaka"])],
            ["Sadece A'da",          str(a["eksik_b"])],
            ["Sadece B'de",          str(a["eksik_a"])],
        ]
        fo_tbl = Table(fark_ozet, colWidths=[100*mm, 30*mm])
        fo_tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0),(-1,-1), fn),
            ("FONTSIZE", (0,0),(-1,-1), 9),
            ("FONTNAME", (0,0),(-1,0),  fnb),
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#37474F")),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("GRID",      (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ]))
        elements.append(fo_tbl)
        elements.append(Spacer(1, 4*mm))

        # Detay tablosu
        elements.append(Paragraph("Detay Karşılaştırma", h2))
        det = [["Durum", "TC Kimlik", "Ad Soyad", "Vaka A", "Vaka B", "Fark"]]
        for s in a["sonuclar"]:
            det.append([
                s["durum"],
                s["tc"],
                s["ad"],
                str(s["va"]) if s["va"] else "—",
                str(s["vb"]) if s["vb"] else "—",
                s["fark"],
            ])

        renkler_pdf = {
            "SADECE A": colors.HexColor("#E3F2FD"),
            "SADECE B": colors.HexColor("#FFEBEE"),
            "FARK":     colors.HexColor("#FFF3E0"),
            "EŞİT":     colors.white,
        }
        satir_renkleri = []
        for i, s in enumerate(a["sonuclar"], start=1):
            c = renkler_pdf.get(s["durum"], colors.white)
            satir_renkleri.append(("BACKGROUND", (0,i), (-1,i), c))

        det_tbl = Table(det, colWidths=[25*mm, 28*mm, 55*mm, 16*mm, 16*mm, None])
        det_tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0),(-1,-1), fn),
            ("FONTSIZE", (0,0),(-1,-1), 8),
            ("FONTNAME", (0,0),(-1,0),  fnb),
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1D3557")),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("GRID",      (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
        ] + satir_renkleri))
        elements.append(det_tbl)

        try:
            doc.build(elements)
            bilgi_goster(self, f"Rapor kaydedildi:\n{path}")
        except Exception as e:
            hata_goster(self, f"PDF oluşturulamadı:\n{e}")
