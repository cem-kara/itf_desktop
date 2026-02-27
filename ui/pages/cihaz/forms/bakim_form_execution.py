# -*- coding: utf-8 -*-
"""Bakım Formu — Execution/Plan Form."""
import time
import os
from typing import Optional, Dict
from enum import Enum
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTextEdit, QDateEdit, QFileDialog, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from database.google.drive import GoogleDriveService
from ui.styles.components import STYLES as S
from ui.styles.colors import DarkTheme
from ui.pages.cihaz.services.bakim_workers import IslemKaydedici, DosyaYukleyici
from ui.pages.cihaz.services.bakim_utils import ay_ekle
from ui.pages.cihaz.components.bakim_widgets import FormPanel


# ════════════════════════════════════════════════════════════════════
#  MODE ENUM
# ════════════════════════════════════════════════════════════════════
class FormMode(Enum):
    """Form modu."""
    PLAN_CREATION = "plan_creation"      # Yeni plan oluştur
    EXECUTION_INFO = "execution_info"    # Mevcut plana bilgi gir


# ════════════════════════════════════════════════════════════════════
#  EXECUTION FORM
# ════════════════════════════════════════════════════════════════════
class _BakimGirisForm(QWidget):
    """Bakım Planı / Execution Formu."""
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None,
                 kullanici_adi: Optional[str] = None,
                 mode: FormMode = FormMode.PLAN_CREATION,
                 plan_data: Optional[Dict] = None,
                 action_guard=None,
                 parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._kullanici_adi = kullanici_adi or "Sistem"
        self._mode = mode
        self._plan_data = plan_data or {}
        self._action_guard = action_guard
        self._secilen_dosya = None
        self._mevcut_link = None
        self._drive_folder_id = None
        self._selected_cihaz_id = None
        self._uploader = None
        self._saver = None

        self._setup_ui()
        self._set_mode_ui()

    # ══════════════════════════════════════════════════════
    #  UI SETUP
    # ══════════════════════════════════════════════════════
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ─ Bakım Planı Seçimi ─
        self._panel_plan = FormPanel("Bakım Planı Seçimi")
        
        self.cmb_cihaz_sec = QComboBox()
        self.cmb_cihaz_sec.setStyleSheet(S["combo"])
        self.cmb_cihaz_sec.setMinimumHeight(40)
        self.cmb_cihaz_sec.setEditable(True)
        self.cmb_cihaz_sec.lineEdit().setPlaceholderText("Cihaz ara veya seç...")
        self._load_cihaz_list()
        self._panel_plan.add_field("Cihaz", self.cmb_cihaz_sec)
        
        self.cmb_periyot_plan = QComboBox()
        self.cmb_periyot_plan.setStyleSheet(S["combo"])
        self.cmb_periyot_plan.addItems([
            "Tek Seferlik",
            "3 Ay (Otomatik 4 Plan)",
            "6 Ay (Otomatik 2 Plan)",
            "1 Yıl (Tek Plan)"
        ])
        self.cmb_periyot_plan.setMinimumHeight(40)
        self.cmb_periyot_plan.currentIndexChanged.connect(self._periyot_plan_degisti)
        self._panel_plan.add_field("Plan Türü", self.cmb_periyot_plan)
        
        root.addWidget(self._panel_plan)

        # ─ Bakım Bilgileri ─
        self._panel_tarih = FormPanel("Bakım Bilgileri")
        
        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True)
        self.dt_plan.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_plan.setStyleSheet(S.get("date", ""))
        self.dt_plan.setMinimumHeight(36)
        self._panel_tarih.add_field("Planlanan Tarih", self.dt_plan)
        
        self.txt_tip = QLineEdit()
        self.txt_tip.setStyleSheet(S["input"])
        self.txt_tip.setPlaceholderText("Periyodik, Rutin, Acil, İyileştirme")
        self.txt_tip.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Tipi", self.txt_tip)
        
        self.txt_periyot = QLineEdit()
        self.txt_periyot.setStyleSheet(S["input"])
        self.txt_periyot.setPlaceholderText("3 Ay, 6 Ay, 1 Yıl")
        self.txt_periyot.setReadOnly(True)
        self.txt_periyot.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Periyodu", self.txt_periyot)
        
        self.txt_sira = QLineEdit()
        self.txt_sira.setStyleSheet(S["input"])
        self.txt_sira.setReadOnly(True)
        self.txt_sira.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Sırası", self.txt_sira)
        
        self.txt_bakim = QLineEdit()
        self.txt_bakim.setStyleSheet(S["input"])
        self.txt_bakim.setPlaceholderText("Bakım hakkında kısa açıklama")
        self.txt_bakim.setMinimumHeight(36)
        self._panel_tarih.add_full_width_field("Bakım Açıklaması", self.txt_bakim)
        
        root.addWidget(self._panel_tarih)

        # ─ İşlem Detayları ─
        self._panel_islem = FormPanel("🔨 İşlem Detayları")
        
        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Planlandı", "Yapıldı", "Gecikmiş"])
        self.cmb_durum.setMinimumHeight(36)
        self.cmb_durum.currentTextChanged.connect(self._durum_kontrol)
        self._panel_islem.add_field("✓ Bakım Durumu", self.cmb_durum)
        
        self.dt_bakim = QDateEdit(QDate.currentDate())
        self.dt_bakim.setCalendarPopup(True)
        self.dt_bakim.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_bakim.setStyleSheet(S.get("date", ""))
        self.dt_bakim.setMinimumHeight(36)
        self._panel_islem.add_field("✔️ Yapılan Tarih", self.dt_bakim)
        
        self.txt_islemler = QTextEdit()
        self.txt_islemler.setStyleSheet(S.get("input_text", ""))
        self.txt_islemler.setFixedHeight(80)
        self.txt_islemler.setPlaceholderText("✓ İşlem 1: ...\n✓ İşlem 2: ...")
        self._panel_islem.add_full_width_field("🛠️  Yapılan İşlemler", self.txt_islemler)
        
        root.addWidget(self._panel_islem)

        # ─ Donumansyon ─
        self._panel_dosya = FormPanel("📎 Dosya & Not")
        
        self.lbl_dosya = QLabel("📋 Rapor Yok")
        self.lbl_dosya.setStyleSheet(self._get_dosya_style("empty"))
        self._panel_dosya.add_field("Rapor Dosyası", self.lbl_dosya)
        
        btns = QHBoxLayout()
        self.btn_dosya_ac = QPushButton("📁 Dosya Seç")
        self.btn_dosya_ac.setStyleSheet(S.get("btn_secondary", ""))
        self.btn_dosya_ac.setMinimumHeight(36)
        self.btn_dosya_ac.clicked.connect(self._dosya_sec)
        btns.addWidget(self.btn_dosya_ac)
        
        btn_ac = QPushButton("🔗 Mevcut Raporu Aç")
        btn_ac.setStyleSheet(S.get("btn_secondary", ""))
        btn_ac.setMinimumHeight(36)
        btn_ac.setVisible(False)
        btn_ac.clicked.connect(self._dosyayi_ac)
        self.btn_dosya_ac_mevcut = btn_ac
        btns.addWidget(btn_ac)
        
        self._panel_dosya.layout_main.addLayout(btns, self._panel_dosya.row_counter)
        self._panel_dosya.row_counter += 1
        
        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S.get("input_text", ""))
        self.txt_aciklama.setFixedHeight(60)
        self.txt_aciklama.setPlaceholderText("Ek notlar, sorunlar, öneriler...")
        self._panel_dosya.add_full_width_field("Açıklama & Notlar", self.txt_aciklama)
        
        root.addWidget(self._panel_dosya)

        # ─ Progress & Buttons ─
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.btn_iptal = QPushButton("✕ İptal")
        self.btn_iptal.setStyleSheet(S.get("btn_secondary", ""))
        self.btn_iptal.setMinimumWidth(100)
        self.btn_iptal.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_iptal)
        
        self.btn_kaydet = QPushButton("💾 Kaydet")
        self.btn_kaydet.setStyleSheet(S.get("btn_primary", ""))
        self.btn_kaydet.setMinimumWidth(120)
        self.btn_kaydet.clicked.connect(self._save)
        btn_row.addWidget(self.btn_kaydet)
        
        root.addLayout(btn_row)
        root.addStretch()

    def _get_dosya_style(self, state):
        """Dosya label stili."""
        c = _get_colors()
        if state == "success":
            return f"color:white;font-weight:bold;padding:8px 12px;background:{c['green']};border-radius:4px;"
        elif state == "error":
            return f"color:white;font-weight:bold;padding:8px 12px;background:{c['red']};border-radius:4px;"
        else:
            return f"color:{c['muted']};font-style:italic;padding:8px 12px;background:{c['panel']};border-radius:4px;border:1px dashed {c['border']};"

    def _load_cihaz_list(self):
        """Cihaz listesini yükle."""
        self.cmb_cihaz_sec.clear()
        self.cmb_cihaz_sec.addItem("Cihaz seçin...", None)
        if not self._db:
            return
        try:
            repo = RepositoryRegistry(self._db).get("Cihazlar")
            cihazlar = repo.get_all() or []
            for c in cihazlar:
                cid = c.get("Cihazid", "")
                marka = c.get("Marka", "")
                if cid:
                    label = f"{cid} - {marka}" if marka else cid
                    self.cmb_cihaz_sec.addItem(label, cid)
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")

    def _periyot_plan_degisti(self):
        """Plan periyodu değişince sıra alanını güncelle."""
        periyot = self.cmb_periyot_plan.currentText()
        self.txt_periyot.setText(periyot.split("(")[0].strip())
        self.txt_sira.setText("1. Bakım")

    def _durum_kontrol(self):
        """Durum değişince islem alanını kontrol et."""
        durum = self.cmb_durum.currentText()
        c = _get_colors()
        
        self.dt_bakim.setEnabled(durum == "Yapıldı")
        self.txt_islemler.setEnabled(durum == "Yapıldı")
        
        if durum == "Yapıldı":
            self.txt_aciklama.setStyleSheet(
                S.get("input_text", "") + f"QTextEdit{{border:2px solid {c['amber']};}}"
            )
            self.txt_aciklama.setPlaceholderText("Yüksek Önem: İşlem detaylarını yazınız!")
        else:
            self.txt_aciklama.setStyleSheet(S.get("input_text", ""))
            self.txt_aciklama.setPlaceholderText("Ek notlar, sorunlar, öneriler...")

    def _set_mode_ui(self):
        """Moda göre UI'ı ayarla."""
        if self._mode == FormMode.PLAN_CREATION:
            # Yeni plan oluşturma modu
            self._panel_plan.setVisible(True)
            self.txt_tip.setEnabled(True)
            self.txt_bakim.setEnabled(True)
            self.cmb_durum.setCurrentIndex(0)  # Planlandı
            self.cmb_durum.setEnabled(True)
            if self._cihaz_id:
                self.cmb_cihaz_sec.setCurrentIndex(
                    max(0, self.cmb_cihaz_sec.findData(self._cihaz_id))
                )
                self.cmb_cihaz_sec.setEnabled(False)
        else:
            # Execution info modu
            self._panel_plan.setVisible(False)
            plan = self._plan_data
            self.txt_tip.setPlaceholderText(plan.get("BakimTipi", ""))
            self.txt_tip.setReadOnly(True)
            self.txt_bakim.setText(plan.get("Bakim", ""))
            self.txt_bakim.setReadOnly(True)
            self.txt_periyot.setText(plan.get("BakimPeriyodu", ""))
            self.txt_sira.setText(plan.get("BakimSirasi", ""))
            
            # Mevcut dosya varsa göster
            rapor = plan.get("Rapor", "")
            if rapor and rapor != "-":
                self._mevcut_link = rapor
                self.lbl_dosya.setText(f"✅ Mevcut Rapor")
                self.lbl_dosya.setStyleSheet(self._get_dosya_style("success"))
                self.btn_dosya_ac_mevcut.setVisible(True)

    # ══════════════════════════════════════════════════════
    #  DOSYA İŞLEMLERİ
    # ══════════════════════════════════════════════════════
    def _dosya_sec(self):
        """Dosya seç."""
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Bakım Raporu Seç",
            "",
            "Belgeler (*.pdf *.doc *.docx);;Resimler (*.jpg *.png);;Tüm (*.*)"
        )
        if yol:
            self._secilen_dosya = yol
            adi = os.path.basename(yol)
            boyut = os.path.getsize(yol) / 1024
            self.lbl_dosya.setText(f"✅ {adi} ({boyut:.0f} KB)")
            self.lbl_dosya.setStyleSheet(self._get_dosya_style("success"))

    def _dosyayi_ac(self):
        """Mevcut raporu aç."""
        if self._mevcut_link:
            QDesktopServices.openUrl(QUrl(self._mevcut_link))

    # ══════════════════════════════════════════════════════
    #  KAYIT İŞLEMİ
    # ══════════════════════════════════════════════════════
    def _save(self):
        """Kaydet."""
        if self._action_guard and not self._action_guard.check_and_warn(self, "cihaz.write", "Bakım Kaydetme"):
            return
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        
        # Cihaz ID'sini belirle
        cihaz_id = None
        if self._mode == FormMode.PLAN_CREATION:
            cihaz_id = self.cmb_cihaz_sec.currentData()
            if not cihaz_id:
                QMessageBox.warning(self, "Uyarı", "Lütfen bir cihaz seçiniz.")
                return
        else:
            cihaz_id = self._plan_data.get("Cihazid") or self._cihaz_id
            if not cihaz_id:
                QMessageBox.warning(self, "Uyarı", "Cihaz bilgisi bulunamadı.")
                return
        
        self._selected_cihaz_id = cihaz_id
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        # Dosya varsa yükle
        if self._secilen_dosya:
            self._uploader = DosyaYukleyici(self._secilen_dosya, self._drive_folder_id)
            self._uploader.yuklendi.connect(self._dosya_yuklendi)
            self._uploader.start()
        else:
            self._kaydet_devam("-")

    def _dosya_yuklendi(self, link: str):
        """Dosya yüklendi."""
        self._kaydet_devam(link)

    def _kaydet_devam(self, dosya_link: str):
        """Kaydetmeyi devam ettir."""
        if dosya_link == "-" and self._mevcut_link:
            dosya_link = self._mevcut_link

        # Form verilerini topla
        periyot_secim = self.cmb_periyot_plan.currentText()
        periyot = self.txt_periyot.text().strip()
        tarih = self.dt_plan.date().toPython()
        durum = self.cmb_durum.currentText().strip()
        yapilan = self.txt_islemler.toPlainText().strip()
        aciklama = self.txt_aciklama.toPlainText().strip()
        teknisyen = self._kullanici_adi
        bakim_tarihi = self.dt_bakim.date().toString("yyyy-MM-dd") if durum == "Yapıldı" else ""
        bakim = self.txt_bakim.text().strip()
        tip = self.txt_tip.text().strip() or "Periyodik"

        # Plan sayısını hesapla
        tekrar = 1
        ay_artis = 0
        if "3 Ay" in periyot_secim:
            tekrar, ay_artis = 4, 3
        elif "6 Ay" in periyot_secim:
            tekrar, ay_artis = 2, 6
        elif "1 Yıl" in periyot_secim:
            tekrar, ay_artis = 1, 12

        # Kayıtları oluştur
        base_id = int(time.time())
        kayitlar = []

        for i in range(tekrar):
            yeni_tarih = ay_ekle(tarih, i * ay_artis)
            tarih_str = yeni_tarih.strftime("%Y-%m-%d")

            s_durum = durum if i == 0 else "Planlandı"
            s_dosya = dosya_link if i == 0 else "-"
            s_yapilan = yapilan if i == 0 else "-"
            s_aciklama = aciklama if i == 0 else "-"
            s_teknisyen = teknisyen if i == 0 else "-"
            s_bakim_tarihi = bakim_tarihi if i == 0 else ""

            planid = f"{self._selected_cihaz_id}-BK-{base_id + i}"

            kayit = {
                "Planid": planid,
                "Cihazid": self._selected_cihaz_id,
                "BakimPeriyodu": periyot,
                "BakimSirasi": f"{i+1}. Bakım",
                "PlanlananTarih": tarih_str,
                "Bakim": bakim,
                "Durum": s_durum,
                "BakimTarihi": s_bakim_tarihi,
                "BakimTipi": tip,
                "YapilanIslemler": s_yapilan,
                "Aciklama": s_aciklama,
                "Teknisyen": s_teknisyen,
                "Rapor": s_dosya,
            }
            kayitlar.append(kayit)

        # Thread'de kaydet
        self._saver = IslemKaydedici(self._db, "INSERT", kayitlar)
        self._saver.islem_tamam.connect(self._kayit_basarili)
        self._saver.hata_olustu.connect(self._kayit_hatasi)
        self._saver.start()

    def _kayit_basarili(self):
        """Kayıt başarılı."""
        self.progress.setVisible(False)
        QMessageBox.information(self, "Başarılı", "Bakım kaydı/planı başarıyla oluşturuldu.")
        self._clear()
        self.saved.emit()

    def _kayit_hatasi(self, hata_mesaji: str):
        """Kayıt hatası."""
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {hata_mesaji}")

    def _clear(self):
        """Formu temizle."""
        self.txt_periyot.clear()
        self.txt_sira.clear()
        self.txt_bakim.clear()
        self.txt_tip.clear()
        self.txt_islemler.clear()
        self.txt_aciklama.clear()
        self.dt_plan.setDate(QDate.currentDate())
        self.dt_bakim.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)
        self.cmb_periyot_plan.setCurrentIndex(0)
        self._secilen_dosya = None
        self._mevcut_link = None
        self.lbl_dosya.setText("📋 Rapor Yok")
        self.lbl_dosya.setStyleSheet(self._get_dosya_style("empty"))
        self.btn_dosya_ac_mevcut.setVisible(False)

    def _cancel(self):
        """İptal."""
        self.close()

    def closeEvent(self, event):
        """Kapanırken thread'leri durdur."""
        if self._saver and self._saver.isRunning():
            self._saver.quit()
            self._saver.wait(500)
        if self._uploader and self._uploader.isRunning():
            self._uploader.quit()
            self._uploader.wait(500)
        event.accept()


def _get_colors():
    """Renkler."""
    return {
        "panel": getattr(DarkTheme, "PANEL", "#191d26"),
        "border": getattr(DarkTheme, "BORDER", "#242938"),
        "green": getattr(DarkTheme, "STATUS_SUCCESS", "#3ecf8e"),
        "red": getattr(DarkTheme, "STATUS_ERROR", "#f75f5f"),
        "amber": getattr(DarkTheme, "STATUS_WARNING", "#ffa500"),
        "muted": getattr(DarkTheme, "TEXT_MUTED", "#5a6278"),
    }
