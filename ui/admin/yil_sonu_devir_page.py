"""
Yıl Sonu Devir İşlemleri Sayfası

Özellikler:
- Yıllık izin devir hesaplama
- Şua izni devir hesaplama
- Batch güncelleme
- İşlem logları
"""
from __future__ import annotations

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QLabel,
    QMessageBox,
    QCheckBox,
    QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.colors import DarkTheme as C
from ui.styles.components import STYLES
from ui.styles.icons import Icons, IconRenderer


class DevirWorker(QThread):
    """Yıl sonu devir işlemini arka planda yapan worker"""
    
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(bool, str)  # success, message

    def __init__(self, registry: RepositoryRegistry):
        super().__init__()
        self._registry = registry

    def run(self):
        try:
            self.log_signal.emit("⏳ Veritabanına bağlanılıyor...")
            
            personel_repo = self._registry.get("Personel")
            izin_bilgi_repo = self._registry.get("Izin_Bilgi")
            
            # 1. Verileri çek
            self.log_signal.emit("📥 Veriler çekiliyor...")
            
            personel_list = personel_repo.get_all() or []
            izin_bilgi_list = izin_bilgi_repo.get_all() or []
            
            if not izin_bilgi_list:
                self.log_signal.emit("İşlenecek izin bilgisi bulunamadı.")
                self.finished_signal.emit(False, "İzin bilgisi bulunamadı")
                return
            
            # Personel haritası oluştur (TC -> Başlama Tarihi)
            baslama_map = {}
            for p in personel_list:
                tc = str(p.get("KimlikNo", "")).strip()
                baslama = p.get("MemuriyeteBaslamaTarihi", "")
                if tc:
                    baslama_map[tc] = baslama
            
            self.log_signal.emit(f"İşleniyor: {len(izin_bilgi_list)} kayıt...")
            
            basarili = 0
            hatali = 0
            
            # Her izin kaydını güncelle
            for i, izin in enumerate(izin_bilgi_list):
                tc = str(izin.get("TCKimlik", "")).strip()
                
                if not tc:
                    hatali += 1
                    continue
                
                try:
                    # --- A. YILLIK İZİN HESABI ---
                    eski_hakedis = int(izin.get("YillikHakedis", 0) or 0)
                    mevcut_kalan = int(float(str(izin.get("YillikKalan", 0) or 0)))
                    
                    # 1. Yeni Devir (Kalan ile Hakediş'in küçüğü)
                    yeni_devir = min(mevcut_kalan, eski_hakedis)
                    
                    # 2. Yeni Hakediş (hizmet yılına göre)
                    hizmet_yili = self._hizmet_yili_hesapla(baslama_map.get(tc, ""))
                    yeni_hakedis = 30 if hizmet_yili >= 10 else (20 if hizmet_yili > 0 else 0)
                    
                    # 3. Yıllık İzin Güncelleme
                    yeni_toplam = yeni_devir + yeni_hakedis
                    
                    # --- B. ŞUA İZNİ HESABI ---
                    # Cari yıl kazanımı -> Yeni yıl hakkı olur
                    sua_cari = int(izin.get("SuaCariYilKazanim", 0) or 0)
                    yeni_sua_hak = sua_cari
                    
                    # Güncelleme verisi
                    guncelleme = {
                        "TCKimlik": tc,
                        "YillikDevir": yeni_devir,
                        "YillikHakedis": yeni_hakedis,
                        "YillikToplamHak": yeni_toplam,
                        "YillikKullanilan": 0,
                        "YillikKalan": yeni_toplam,
                        "SuaKullanilabilirHak": yeni_sua_hak,
                        "SuaKullanilan": 0,
                        "SuaKalan": yeni_sua_hak,
                        "SuaCariYilKazanim": 0,
                    }
                    
                    # Güncelle
                    izin_bilgi_repo.update(tc, guncelleme)
                    basarili += 1
                    
                    if i % 10 == 0:
                        self.log_signal.emit(f"İşleniyor... {tc} ({i+1}/{len(izin_bilgi_list)})")
                    
                except Exception as e:
                    self.log_signal.emit(f"Hata ({tc}): {e}")
                    hatali += 1
                
                # Progress güncelle
                progress = int((i + 1) / len(izin_bilgi_list) * 100)
                self.progress_signal.emit(progress)
            
            # Sonuç
            self.log_signal.emit("=" * 50)
            self.log_signal.emit(f"✅ İşlem tamamlandı!")
            self.log_signal.emit(f"   Başarılı: {basarili}")
            self.log_signal.emit(f"   Hatalı: {hatali}")
            self.log_signal.emit("=" * 50)
            
            self.finished_signal.emit(True, f"Başarılı: {basarili}, Hatalı: {hatali}")
            
        except Exception as e:
            error_msg = f"❌ KRİTİK HATA: {str(e)}"
            self.log_signal.emit(error_msg)
            logger.error(f"Yıl sonu devir hatası: {e}", exc_info=True)
            self.finished_signal.emit(False, str(e))

    def _hizmet_yili_hesapla(self, tarih_str: str) -> int:
        """Hizmet yılını hesapla"""
        if not tarih_str:
            return 0
        
        try:
            # Farklı tarih formatlarını dene
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    baslama = datetime.strptime(str(tarih_str), fmt)
                    bugun = datetime.now()
                    yil_farki = bugun.year - baslama.year
                    # Ay-gün kontrolü
                    if (bugun.month, bugun.day) < (baslama.month, baslama.day):
                        yil_farki -= 1
                    return max(0, yil_farki)
                except ValueError:
                    continue
            return 0
        except Exception as e:
            logger.warning(f"Hizmet yılı hesaplama hatası: {e}")
            return 0


class YilSonuDevirPage(QWidget):
    """Yıl sonu devir işlemleri sayfası"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._worker = None
        
        self._setup_ui()

    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Uyarı grubu
        grp_uyari = QGroupBox("DİKKAT: YIL SONU İŞLEMİ")
        grp_uyari.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e81123;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                color: #e81123;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        
        v_uyari = QVBoxLayout(grp_uyari)
        
        lbl_bilgi = QLabel(
            "Bu işlem <b>YILDA BİR KEZ (Yılbaşında)</b> yapılmalıdır.<br><br>"
            "<b>Yapılacak İşlemler:</b><br>"
            "1. <b>Yıllık İzin:</b> Eski devirler silinir, sadece bu yılın artan hakkı devreder.<br>"
            "2. <b>Şua İzni:</b> 'Cari Yıl Kazanım' sütunundaki hak, 'Kullanılabilir Hak'ka taşınır.<br>"
            "3. <b>Genel:</b> Tüm 'Kullanılan' sayaçları sıfırlanır ve yeni yıl hakedişleri eklenir.<br><br>"
            "<i style='color: #f7b731;'>Lütfen işlemden önce veritabanı yedeği alınız!</i>"
        )
        lbl_bilgi.setWordWrap(True)
        lbl_bilgi.setProperty("color-role", "secondary")
        lbl_bilgi.setStyleSheet("font-weight: normal; font-size: 13px; padding: 8px;")
        lbl_bilgi.style().unpolish(lbl_bilgi)
        lbl_bilgi.style().polish(lbl_bilgi)
        v_uyari.addWidget(lbl_bilgi)
        
        self.chk_onay = QCheckBox("Riskleri anladım, işlemi onaylıyorum.")
        self.chk_onay.setProperty("color-role", "err")
        self.chk_onay.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.chk_onay.style().unpolish(self.chk_onay)
        self.chk_onay.style().polish(self.chk_onay)
        self.chk_onay.stateChanged.connect(self._onay_degisti)
        v_uyari.addWidget(self.chk_onay)
        
        layout.addWidget(grp_uyari)
        
        # Log alanı
        layout.addWidget(QLabel("İşlem Logları:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C.BG_SECONDARY};
                color: {C.STATUS_SUCCESS};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid {C.INPUT_BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.txt_log)
        
        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setVisible(False)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {C.INPUT_BORDER};
                border-radius: 4px;
                text-align: center;
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {C.STATUS_ERROR};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.pbar)
        
        # Başlat butonu
        self.btn_baslat = QPushButton("DEVİR İŞLEMİNİ BAŞLAT")
        self.btn_baslat.setFixedHeight(50)
        self.btn_baslat.setEnabled(False)
        self.btn_baslat.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BG_TERTIARY};
                color: {C.TEXT_DISABLED};
                font-weight: bold;
                font-size: 14px;
                border: 1px solid {C.INPUT_BORDER};
                border-radius: 6px;
            }}
        """)
        self.btn_baslat.clicked.connect(self._islemi_baslat)
        layout.addWidget(self.btn_baslat)

    def _onay_degisti(self):
        """Onay checkbox değiştiğinde buton durumunu ayarla"""
        if self.chk_onay.isChecked():
            self.btn_baslat.setEnabled(True)
            self.btn_baslat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C.STATUS_ERROR};
                    color: {C.TEXT_PRIMARY};
                    font-weight: bold;
                    font-size: 14px;
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {C.BTN_DANGER_HOVER};
                }}
            """)
        else:
            self.btn_baslat.setEnabled(False)
            self.btn_baslat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C.BG_TERTIARY};
                    color: {C.TEXT_DISABLED};
                    font-weight: bold;
                    font-size: 14px;
                    border: 1px solid {C.INPUT_BORDER};
                    border-radius: 6px;
                }}
            """)

    def _islemi_baslat(self):
        """Devir işlemini başlat"""
        # Son onay
        reply = QMessageBox.question(
            self,
            "Son Onay",
            "Yıl sonu devir işlemini başlatmak istediğinizden emin misiniz?\n\n"
            "Bu işlem GERİ ALINAMAZ!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # UI'yı kilitle
        self.btn_baslat.setEnabled(False)
        self.chk_onay.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setValue(0)
        self.txt_log.clear()
        
        # Worker başlat
        from core.di import get_registry
        registry = get_registry(self._db)
        
        self._worker = DevirWorker(registry)
        self._worker.log_signal.connect(self._log_ekle)
        self._worker.progress_signal.connect(self.pbar.setValue)
        self._worker.finished_signal.connect(self._islem_bitti)
        self._worker.start()
        
        logger.info("Yıl sonu devir işlemi başlatıldı")

    def _log_ekle(self, mesaj: str):
        """Log mesajı ekle"""
        self.txt_log.append(mesaj)

    def _islem_bitti(self, success: bool, message: str):
        """İşlem tamamlandı"""
        # UI'yı aç
        self.chk_onay.setChecked(False)
        self.chk_onay.setEnabled(True)
        self.pbar.setVisible(False)
        
        # Sonuç mesajı
        if success:
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"Yıl sonu devir işlemi başarıyla tamamlandı.\n\n{message}"
            )
            logger.info(f"Yıl sonu devir işlemi tamamlandı: {message}")
        else:
            QMessageBox.critical(
                self,
                "İşlem Başarısız",
                f"Yıl sonu devir işlemi sırasında hata oluştu:\n\n{message}"
            )
            logger.error(f"Yıl sonu devir işlemi başarısız: {message}")
