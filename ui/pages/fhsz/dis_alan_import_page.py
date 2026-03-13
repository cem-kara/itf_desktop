# ui/pages/fhsz/dis_alan_import_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Excel Import Ekranı

Akış:
  1. Kullanıcı dosya seçer ve dönemi belirler
  2. "Dosyayı Oku" â†’ önizleme tablosu dolup hatalı satırlar kırmızı gösterilir
  3. Kullanıcı hatalı satırları işaretler (onayla / atla)
  4. "Seçilileri Kaydet" â†’ sadece işaretlenenler DB'ye gider
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QCheckBox, QSplitter,
    QTextEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtGui import QColor, QBrush, QFont

from core.logger import logger
from ui.styles.components import STYLES as S
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
    ("Durum",         90,  "durum"),
    ("TC Kimlik",    130,  "TCKimlik"),
    ("Ad Soyad",     200,  "AdSoyad"),
    ("Alan",         210,  "IslemTipi"),
    ("Vaka",          60,  "VakaSayisi"),
    ("Katsayı",       72,  "Katsayi"),
    ("Saat",          72,  "HesaplananSaat"),
    ("Tutanak No",   140,  "TutanakNo"),
    ("Tarih",        100,  "TutanakTarihi"),
    ("Hata / Uyarı", 320,  "mesaj"),
]


class _OkuyucuWorker(QObject):
    """Excel okumayı arka planda yapar â€” UI donmaz."""
    bitti  = Signal(object)   # ImportSonucu
    hata   = Signal(str)

    def __init__(self, svc, dosya, ay, yil):
        super().__init__()
        self._svc   = svc
        self._dosya = dosya
        self._ay    = ay
        self._yil   = yil

    def calistir(self):
        try:
            sonuc = self._svc.excel_oku(self._dosya, self._ay, self._yil)
            self.bitti.emit(sonuc)
        except Exception as e:
            self.hata.emit(str(e))


class DisAlanImportPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db     = db
        self._sonuc  = None   # Son okunan ImportSonucu
        self._thread = None

        self._setup_ui()
        self._connect_signals()

    # =========================================================
    #  UI
    # =========================================================

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)

        # Ãœst Bar
        top = QFrame(); top.setStyleSheet(S["filter_panel"]); top.setMaximumHeight(56)
        top_lay = QHBoxLayout(top); top_lay.setContentsMargins(12, 6, 12, 6); top_lay.setSpacing(12)

        lbl = QLabel("Dış Alan Excel Import â€” RKS Onay Ekranı")
        lbl.setStyleSheet("font-size:15px; font-weight:bold; color:#1D75FE;")
        top_lay.addWidget(lbl); top_lay.addStretch()

        # Dönem seçimi
        top_lay.addWidget(QLabel("Dönem:"))
        self.cmb_ay = QComboBox()
        self.cmb_ay.addItems(["Ocak","Åubat","Mart","Nisan","Mayıs","Haziran",
                               "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"])
        self.cmb_ay.setCurrentIndex(datetime.now().month - 1)
        self.cmb_ay.setFixedWidth(100)
        top_lay.addWidget(self.cmb_ay)

        self.cmb_yil = QComboBox()
        self.cmb_yil.addItems([str(y) for y in range(datetime.now().year - 2, datetime.now().year + 3)])
        self.cmb_yil.setCurrentText(str(datetime.now().year))
        self.cmb_yil.setFixedWidth(100)
        top_lay.addWidget(self.cmb_yil)

        # Dosya seçme
        self.btn_dosya = QPushButton("Excel Dosyası Seç")
        self.btn_dosya.setStyleSheet(S.get("secondary_btn", S["save_btn"]))
        self.btn_dosya.setFixedHeight(36)
        IconRenderer.set_button_icon(self.btn_dosya, "folder", color="#FFFFFF")
        top_lay.addWidget(self.btn_dosya)

        self.lbl_dosya = QLabel("Dosya seçilmedi")
        self.lbl_dosya.setStyleSheet("font-size:11px; color:#888;")
        top_lay.addWidget(self.lbl_dosya)

        self.btn_oku = QPushButton("Dosyayı Oku ve Doğrula")
        self.btn_oku.setStyleSheet(S["save_btn"])
        self.btn_oku.setFixedHeight(36)
        self.btn_oku.setEnabled(False)
        top_lay.addWidget(self.btn_oku)

        root.addWidget(top)

        # Araç çubuğu (tümünü seç / yalnızca geçerlileri seç / kaydet)
        ara = QFrame(); ara.setStyleSheet(S["filter_panel"]); ara.setMaximumHeight(48)
        ara_lay = QHBoxLayout(ara); ara_lay.setContentsMargins(12, 4, 12, 4); ara_lay.setSpacing(10)

        self.btn_tumunu_sec   = QPushButton("Tümünü Seç")
        self.btn_gecerlileri  = QPushButton("Yalnızca Geçerlileri Seç")
        self.btn_secimi_kaldir = QPushButton("Seçimi Kaldır")

        for btn in [self.btn_tumunu_sec, self.btn_gecerlileri, self.btn_secimi_kaldir]:
            btn.setFixedHeight(30)
            btn.setStyleSheet(S.get("secondary_btn", S["save_btn"]))
            btn.setEnabled(False)
            ara_lay.addWidget(btn)

        ara_lay.addStretch()

        self.lbl_ozet = QLabel("")
        self.lbl_ozet.setStyleSheet("font-size:11px; color:#aaa;")
        ara_lay.addWidget(self.lbl_ozet)

        ara_lay.addStretch()

        self.btn_kaydet = QPushButton("SEÇİLİLERİ KAYDET")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
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
        self.tablo.setStyleSheet(S["table"])
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

    # =========================================================
    #  Sinyaller
    # =========================================================

    def _connect_signals(self):
        self.btn_dosya.clicked.connect(self._dosya_sec)
        self.btn_oku.clicked.connect(self._dosyayi_oku)
        self.btn_tumunu_sec.clicked.connect(lambda: self._toplu_sec(True))
        self.btn_gecerlileri.clicked.connect(self._gecerlileri_sec)
        self.btn_secimi_kaldir.clicked.connect(lambda: self._toplu_sec(False))
        self.btn_kaydet.clicked.connect(self._kaydet)

    # =========================================================
    #  Dosya seçme
    # =========================================================

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "",
            "Excel Dosyaları (*.xlsx *.xlsm);;Tüm Dosyalar (*)"
        )
        if yol:
            self._dosya_yolu = yol
            self.lbl_dosya.setText(yol.split("/")[-1])
            self.btn_oku.setEnabled(True)

    # =========================================================
    #  Excel okuma (arka plan thread)
    # =========================================================

    def _dosyayi_oku(self):
        if not hasattr(self, "_dosya_yolu"):
            return

        self.btn_oku.setEnabled(False)
        self.btn_oku.setText("Okunuyorâ€¦")
        self.tablo.setRowCount(0)
        self.lbl_ozet.setText("")

        from core.di import get_registry
        from core.services.dis_alan_import_service import DisAlanImportService

        svc = DisAlanImportService(get_registry(self._db) if self._db else None)

        ay  = self.cmb_ay.currentIndex() + 1
        yil = int(self.cmb_yil.currentText())

        self._worker = _OkuyucuWorker(svc, self._dosya_yolu, ay, yil)
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
        pdf_path = getattr(sonuc, "conflict_report_pdf_path", "")
        txt_path = getattr(sonuc, "conflict_report_path", "")
        if pdf_path or txt_path:
            rapor = pdf_path or txt_path
            QMessageBox.warning(
                self,
                "Çakışma Raporu",
                "Aynı kişi + dönem için çakışan bilgiler tespit edildi.\n"
                "Eski ve yeni kayıtları içeren rapor oluşturuldu.\n\n"
                f"Rapor dosyası:\n{rapor}\n\n"
                "Lütfen ilgili birime iletip doğru bilgiyi isteyin."
            )
        for btn in [self.btn_tumunu_sec, self.btn_gecerlileri,
                    self.btn_secimi_kaldir, self.btn_kaydet]:
            btn.setEnabled(True)

    def _okuma_hatasi(self, mesaj):
        self.btn_oku.setEnabled(True)
        self.btn_oku.setText("Dosyayı Oku ve Doğrula")
        QMessageBox.critical(self, "Okuma Hatası", mesaj)

    # =========================================================
    #  Tablo doldurucu
    # =========================================================

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

    # =========================================================
    #  Seçim yardımcıları
    # =========================================================

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

    # =========================================================
    #  Ã–zet güncelle
    # =========================================================

    def _ozet_guncelle(self):
        if not self._sonuc:
            return
        s = self._sonuc
        birim_str = f"{s.anabilim_dali} / {s.birim}".strip(" /")
        self.lbl_ozet.setText(
            f"{birim_str}  |  "
            f"Toplam: {s.toplam_satir}  |  "
            f"âœ“ Geçerli: {s.gecerli}  |  "
            f"âš  Uyarılı: {s.uyarili}  |  "
            f"âœ— Hatalı: {s.hatali}"
        )

    # =========================================================
    #  Kaydet
    # =========================================================

    def _kaydet(self):
        if not self._sonuc:
            return

        if not self._db:
            QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı yok.")
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
            QMessageBox.warning(self, "Seçim Yok", "Kaydedilecek satır seçilmedi.")
            return

        # Hatalı ama onaylananları uyar
        hatali_onaylananlar = [
            s for s in self._sonuc.satirlar
            if not s.gecerli and s.kullanici_onayladi
        ]
        if hatali_onaylananlar:
            cevap = QMessageBox.question(
                self,
                "Hatalı Satırlar Var",
                f"{len(hatali_onaylananlar)} hatalı satır onaylanmış.\n"
                "Bu satırlar eksik veya hatalı veriyle kaydedilecek.\n\n"
                "Devam etmek istiyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if cevap != QMessageBox.StandardButton.Yes:
                return

        from core.di import get_registry
        from core.services.dis_alan_import_service import DisAlanImportService
        from core.auth.session_context import SessionContext

        svc = DisAlanImportService(get_registry(self._db))

        try:
            ctx = SessionContext()
            kaydeden = getattr(ctx, "user", None) or getattr(ctx, "get_current_user", lambda: None)() or "Import"
        except Exception:
            kaydeden = "Import"

        guncellenmis = svc.kaydet(
            self._sonuc,
            dosya_yolu=self._dosya_yolu,
            kaydeden=kaydeden,
        )

        tutanak_ozet = (
            f"Tutanak No : {guncellenmis.tutanak_no[:18]}â€¦\n"
            if guncellenmis.tutanak_no else ""
        )
        QMessageBox.information(
            self,
            "Import Tamamlandı",
            f"Kaydedilen : {guncellenmis.kaydedilen} satır\n"
            f"Atlanan    : {guncellenmis.atlanan} satır\n"
            f"{tutanak_ozet}"
            f"\nExcel dosyası Dokumanlar arşivine eklendi.\n"
            f"Dönem özeti için 'Dönem Ã–zeti Hesapla' butonunu kullanın."
        )

        # Tabloyu yenile (kayıt durumunu göster)
        self._tabloyu_doldur(guncellenmis)
        self.btn_kaydet.setEnabled(False)



