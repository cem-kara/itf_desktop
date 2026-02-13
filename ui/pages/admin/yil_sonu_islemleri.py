# -*- coding: utf-8 -*-
"""
Yıl Sonu Devir İşlemleri
═══════════════════════════════════════════════════════════════
Eski sistem (Google Sheets) → Yeni mimari (SQLite + RepositoryRegistry)

Tablolar (database/table_config.py):
  • Izin_Bilgi  — PK: TCKimlik
  • Personel    — PK: KimlikNo  (MemuriyeteBaslamaTarihi için join)

Yapılacak işlemler (her yılbaşında bir kez):
  1. Yıllık İzin:
       - Yeni Devir    = min(YillikKalan, YillikHakedis)
       - Yeni Hakediş  = hizmet yılına göre (≥10 yıl → 30 gün, diğer → 20 gün)
       - YillikKullanilan → 0 (sıfırla)
  2. Şua İzni:
       - SuaCariYilKazanim → SuaKullanilabilirHak (taşı)
       - SuaKullanilan     → 0 (sıfırla)
       - SuaCariYilKazanim → 0 (boşalt)

Mimari:
  • Worker: QThread içinde SQLiteManager + RepositoryRegistry (lazy import)
  • Sayfa:  QWidget; db=None kabul eder (worker kendi bağlantısını açar)
  • Stiller: ThemeManager.get_all_component_styles()
  • Loglama: core.logger + Signal(str) ile UI log alanı
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar,
    QLabel, QMessageBox, QCheckBox,
    QGroupBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()


# ══════════════════════════════════════════════════════════════
#  WORKER
# ══════════════════════════════════════════════════════════════
class DevirWorker(QThread):
    """
    Yıl sonu devir hesaplamalarını arka planda yürütür.
    Bağlantıyı kendisi açar; dışarıdan db almaz.

    Sinyaller
    ---------
    log_sinyali      (str)   -> UI log alanına mesaj yaz
    progress_sinyali (int)   -> QProgressBar değeri (0-100)
    islem_bitti      (bool)  -> True = başarılı, False = hata
    """
    log_sinyali      = Signal(str)
    progress_sinyali = Signal(int)
    islem_bitti      = Signal(bool)

    # ----------------------------------------------------------
    def run(self):
        db = None
        try:
            from database.sqlite_manager import SQLiteManager
            from database.repository_registry import RepositoryRegistry

            self.log_sinyali.emit("Veritabanina baglaniliyor...")
            db       = SQLiteManager()
            registry = RepositoryRegistry(db)

            repo_izin     = registry.get("Izin_Bilgi")
            repo_personel = registry.get("Personel")

            # 1. Tüm kayıtları çek
            self.log_sinyali.emit("Veriler cekiliyor...")
            tum_izin     = repo_izin.get_all()
            tum_personel = repo_personel.get_all()

            if not tum_izin:
                self.log_sinyali.emit("Islenecek kayit bulunamadi.")
                self.islem_bitti.emit(False)
                return

            # 2. Join haritası: TCKimlik → MemuriyeteBaslamaTarihi
            #    (Izin_Bilgi.TCKimlik  ==  Personel.KimlikNo)
            baslama_map: dict = {
                str(p.get("KimlikNo", "")).strip(): str(p.get("MemuriyeteBaslamaTarihi", ""))
                for p in tum_personel
                if p.get("KimlikNo")
            }

            toplam   = len(tum_izin)
            basarili = 0
            hata     = 0
            self.log_sinyali.emit(
                f"{toplam} kayit bulundu. Hesaplamalar basliyor...\n"
                + "-" * 46
            )

            # 3. Kayıt döngüsü
            for i, row in enumerate(tum_izin):
                tc = str(row.get("TCKimlik", "")).strip()
                if not tc:
                    hata += 1
                    self.progress_sinyali.emit(int((i + 1) / toplam * 100))
                    continue

                try:
                    guncelleme = self._hesapla(row, baslama_map.get(tc, ""))
                    repo_izin.update(tc, guncelleme)
                    basarili += 1
                    if i % 10 == 0:
                        self.log_sinyali.emit(f"  TC:{tc} islendi")

                except Exception as exc:
                    hata += 1
                    logger.error(f"DevirWorker - TC={tc}: {exc}")
                    self.log_sinyali.emit(f"  Hata ({tc}): {exc}")

                self.progress_sinyali.emit(int((i + 1) / toplam * 100))

            # 4. Özet
            self.log_sinyali.emit("-" * 46)
            self.log_sinyali.emit(
                f"Islem tamamlandi.\n"
                f"   Basarili : {basarili}\n"
                f"   Hatali   : {hata}"
            )
            self.islem_bitti.emit(True)

        except Exception as exc:
            logger.error(f"DevirWorker kritik hata: {exc}")
            self.log_sinyali.emit(f"KRITIK HATA: {exc}")
            self.islem_bitti.emit(False)
        finally:
            if db:
                db.close()

    # ----------------------------------------------------------
    #  Is Mantigi: tek satir icin devir hesabi
    # ----------------------------------------------------------
    def _hesapla(self, row: dict, baslama_str: str) -> dict:
        """
        Bir Izin_Bilgi satiri icin yil sonu devir degerlerini hesaplar.
        Yalnizca degisen alanlari dondurur (update() icin).
        """
        yeni: dict = {}

        # A. YILLIK IZIN
        mevcut_hakedis = self._int(row.get("YillikHakedis"))
        mevcut_kalan   = self._int(row.get("YillikKalan"))

        # Devir = min(kalan, hakedis) -- en fazla hakedis kadar devir
        yeni_devir   = min(mevcut_kalan, mevcut_hakedis)

        # Yeni hakedis: hizmet yilina gore
        hizmet_yil   = self._hizmet_yili(baslama_str)
        yeni_hakedis = 30 if hizmet_yil >= 10 else (20 if hizmet_yil > 0 else 0)

        yeni["YillikDevir"]      = yeni_devir
        yeni["YillikHakedis"]    = yeni_hakedis
        yeni["YillikToplamHak"]  = yeni_devir + yeni_hakedis
        yeni["YillikKullanilan"] = 0
        yeni["YillikKalan"]      = yeni_devir + yeni_hakedis

        # B. SUA IZNI
        # Cari yil kazanimi -> yeni yilin kullanilabilir hakki
        yeni_sua_hak = self._int(row.get("SuaCariYilKazanim"))

        yeni["SuaKullanilabilirHak"] = yeni_sua_hak
        yeni["SuaKullanilan"]        = 0
        yeni["SuaKalan"]             = yeni_sua_hak
        yeni["SuaCariYilKazanim"]    = 0   # Yeni yil icin bosalt

        return yeni

    # ----------------------------------------------------------
    @staticmethod
    def _int(val) -> int:
        """Guvenli int donusumu: float string, virgul, None."""
        try:
            return int(float(str(val).replace(",", ".")))
        except Exception:
            return 0

    @staticmethod
    def _hizmet_yili(tarih_str: str) -> int:
        """MemuriyeteBaslamaTarihi -> hizmet yili sayisi."""
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                baslama = datetime.strptime(str(tarih_str).strip(), fmt)
                bugun   = datetime.now()
                return (
                    bugun.year - baslama.year
                    - ((bugun.month, bugun.day) < (baslama.month, baslama.day))
                )
            except Exception:
                continue
        return 0


# ══════════════════════════════════════════════════════════════
#  SAYFA
# ══════════════════════════════════════════════════════════════
class YilSonuIslemleriPage(QWidget):
    """
    Yil Sonu Devir Islemleri sayfasi.

    Parametreler
    ------------
    db : SQLiteManager | None
        Ana pencereden gecirilebilir; worker kendi baglantisinı actigi icin
        bu sayfa icin zorunlu degildir.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db     = db
        self._worker = None
        self._setup_ui()
        self._connect_signals()

    # ----------------------------------------------------------
    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(14)

        # Uyari Grubu
        grp_uyari = QGroupBox("DIKKAT - YIL SONU ISLEMI")
        grp_uyari.setStyleSheet(
            "QGroupBox {"
            "  border: 1px solid #c62828;"
            "  border-radius: 6px;"
            "  margin-top: 10px;"
            "  font-weight: bold;"
            "  color: #ef5350;"
            "  font-size: 13px;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  left: 12px;"
            "  padding: 0 6px;"
            "}"
        )
        v_uyari = QVBoxLayout(grp_uyari)
        v_uyari.setSpacing(10)

        lbl_bilgi = QLabel(
            "Bu islem <b>YILDA BIR KEZ (Yilbasinda)</b> yapilmalidir.<br><br>"
            "<b>Yapilacak Islemler:</b><br>"
            "1. <b>Yillik Izin:</b> Eski devir silinir; sadece bu yilin artan hakki devreder. "
            "Yeni yil hakedis <i>(&ge;10 yil &rarr; 30 gun, &lt;10 yil &rarr; 20 gun)</i> hesaplanir.<br>"
            "2. <b>Sua Izni:</b> 'Cari Yil Kazanim' &rarr; 'Kullanilabilir Hak' sutununa tasinir.<br>"
            "3. <b>Genel:</b> Tum 'Kullanilan' sayaclar sifirlanir.<br><br>"
            "<i>Lutfen islemden once yedek aliniz!</i>"
        )
        lbl_bilgi.setWordWrap(True)
        lbl_bilgi.setStyleSheet(
            f"{S.get('label', '')} font-weight: normal; font-size: 12px;"
        )
        v_uyari.addWidget(lbl_bilgi)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.08);")
        v_uyari.addWidget(sep)

        self._chk_onay = QCheckBox("Riskleri anladim, islemi onayliyorum.")
        self._chk_onay.setStyleSheet(
            "QCheckBox { color: #ef5350; font-weight: bold; font-size: 13px; }"
            "QCheckBox::indicator { width: 16px; height: 16px; }"
        )
        v_uyari.addWidget(self._chk_onay)
        main.addWidget(grp_uyari)

        # Log Alani
        lbl_log = QLabel("Islem Loglari:")
        lbl_log.setStyleSheet(S.get("label", "color:#8b8fa3; font-size:11px;"))
        main.addWidget(lbl_log)

        self._txt_log = QTextEdit()
        self._txt_log.setReadOnly(True)
        self._txt_log.setStyleSheet(
            "background-color: #0d1117;"
            "color: #3fb950;"
            "font-family: 'Consolas', 'IBM Plex Mono', monospace;"
            "font-size: 12px;"
            "border: 1px solid #30363d;"
            "border-radius: 6px;"
            "padding: 8px;"
        )
        self._txt_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(self._txt_log, 1)

        # Ilerleme Cubugu
        self._pbar = QProgressBar()
        self._pbar.setValue(0)
        self._pbar.setFixedHeight(6)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        main.addWidget(self._pbar)

        # Alt Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)

        self._btn_baslat = QPushButton("Devir Islemini Baslat")
        self._btn_baslat.setFixedHeight(46)
        self._btn_baslat.setEnabled(False)
        self._btn_baslat.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_baslat.setStyleSheet(self._style_btn_pasif())

        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setFixedHeight(30)
        sep_v.setStyleSheet("background-color: rgba(255,255,255,0.08);")

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setFixedHeight(46)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))

        h_btn.addWidget(self._btn_baslat, 1)
        h_btn.addWidget(sep_v)
        h_btn.addWidget(self.btn_kapat)
        main.addLayout(h_btn)

    # ----------------------------------------------------------
    def _connect_signals(self):
        self._chk_onay.stateChanged.connect(self._on_onay_degisti)
        self._btn_baslat.clicked.connect(self._on_baslat)

    # ----------------------------------------------------------
    def _on_onay_degisti(self):
        if self._chk_onay.isChecked():
            self._btn_baslat.setEnabled(True)
            self._btn_baslat.setStyleSheet(self._style_btn_aktif())
        else:
            self._btn_baslat.setEnabled(False)
            self._btn_baslat.setStyleSheet(self._style_btn_pasif())

    def _on_baslat(self):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Uyari", "Onceki islem henuz tamamlanmadi.")
            return

        self._btn_baslat.setEnabled(False)
        self._btn_baslat.setText("Isleniyor...")
        self._chk_onay.setEnabled(False)
        self._pbar.setValue(0)
        self._pbar.setVisible(True)
        self._txt_log.clear()

        self._worker = DevirWorker()
        self._worker.log_sinyali.connect(self._txt_log.append)
        self._worker.progress_sinyali.connect(self._pbar.setValue)
        self._worker.islem_bitti.connect(self._on_islem_bitti)
        self._worker.start()

    def _on_islem_bitti(self, basarili: bool):
        self._pbar.setVisible(False)
        self._chk_onay.setChecked(False)
        self._chk_onay.setEnabled(True)
        self._btn_baslat.setText("Devir Islemini Baslat")

        if basarili:
            QMessageBox.information(
                self,
                "Tamamlandi",
                "Yil sonu devir islemi basariyla tamamlandi.\n"
                "Tum degisiklikler yerel veritabanina kaydedildi.",
            )
        else:
            QMessageBox.critical(
                self,
                "Hata",
                "Islem sirasinda bir hata olustu.\n"
                "Detaylar icin log alanini inceleyiniz.",
            )

    # ----------------------------------------------------------
    @staticmethod
    def _style_btn_aktif() -> str:
        return (
            "QPushButton {"
            "  background-color: #c62828;"
            "  color: white;"
            "  font-weight: bold;"
            "  font-size: 13px;"
            "  border-radius: 6px;"
            "  border: none;"
            "}"
            "QPushButton:hover { background-color: #b71c1c; }"
        )

    @staticmethod
    def _style_btn_pasif() -> str:
        return (
            "QPushButton {"
            "  background-color: #2a2a2a;"
            "  color: #555;"
            "  font-weight: bold;"
            "  font-size: 13px;"
            "  border-radius: 6px;"
            "  border: none;"
            "}"
        )
