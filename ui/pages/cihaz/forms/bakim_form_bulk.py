# -*- coding: utf-8 -*-
"""Bakım Formu — Toplu Plan Panel & Dialog."""
import time
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QListWidget,
    QListWidgetItem, QPushButton, QDateEdit, QMessageBox, QDialog, QProgressBar
)
from PySide6.QtCore import Qt, QDate
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S
from ui.styles.colors import DarkTheme
from ui.pages.cihaz.services.bakim_workers import IslemKaydedici
from ui.pages.cihaz.services.bakim_utils import ay_ekle


# ════════════════════════════════════════════════════════════════════
#  TOPLU PLAN PANELI
# ════════════════════════════════════════════════════════════════════
class TopluBakimPlanPanel(QWidget):
    """Toplu bakım planı oluşturma paneli."""

    def __init__(self, db=None, on_success=None, on_close=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._on_success = on_success
        self._on_close = on_close
        self._all_cihazlar = []
        self._saver = None
        self._setup_ui()
        self._load_cihazlar()

    def _setup_ui(self):
        """UI kurulumu."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Başlık
        lbl_hdr = QLabel("Seçilen cihazlar için periyodik bakım planları oluşturun")
        lbl_hdr.setStyleSheet(f"font-size:12px;font-weight:600;")
        root.addWidget(lbl_hdr)

        # ─ Marka Filtresi ─
        marka_row = QHBoxLayout()
        marka_row.setSpacing(8)
        marka_row.addWidget(QLabel("Marka:"))
        self.cmb_marka_filter = QComboBox()
        self.cmb_marka_filter.setStyleSheet(S["combo"])
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        self.cmb_marka_filter.currentIndexChanged.connect(self._refresh_cihaz_list)
        marka_row.addWidget(self.cmb_marka_filter, 1)
        root.addLayout(marka_row)

        # ─ Cihaz Listesi ─
        list_hdr = QHBoxLayout()
        list_hdr.addWidget(QLabel("Cihazlar:"))
        btn_select_all = QPushButton("Tümünü Seç")
        btn_select_all.setMaximumWidth(100)
        btn_select_all.setStyleSheet(S.get("btn_secondary", ""))
        btn_select_all.clicked.connect(self._select_all_visible)
        list_hdr.addWidget(btn_select_all)
        btn_clear = QPushButton("Seçimi Kaldır")
        btn_clear.setMaximumWidth(100)
        btn_clear.setStyleSheet(S.get("btn_secondary", ""))
        btn_clear.clicked.connect(self._clear_selection)
        list_hdr.addWidget(btn_clear)
        list_hdr.addStretch()
        root.addLayout(list_hdr)

        self.list_cihazlar = QListWidget()
        self.list_cihazlar.setStyleSheet(S["table"])
        self.list_cihazlar.setMinimumHeight(150)
        root.addWidget(self.list_cihazlar)

        # ─ Plan Ayarları ─
        ayarlar_lbl = QLabel("Plan Ayarları:")
        ayarlar_lbl.setStyleSheet("font-size:11px;font-weight:600;margin-top:8px;")
        root.addWidget(ayarlar_lbl)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(8)
        plan_row.addWidget(QLabel("Plan Türü:"))
        self.cmb_plan_tipi = QComboBox()
        self.cmb_plan_tipi.setStyleSheet(S["combo"])
        self.cmb_plan_tipi.addItems([
            "Tek Seferlik (1 Plan)",
            "3 Ay (4 Plan)",
            "6 Ay (2 Plan)",
            "1 Yıl (1 Plan)"
        ])
        plan_row.addWidget(self.cmb_plan_tipi)
        plan_row.addStretch()
        root.addLayout(plan_row)

        tarih_row = QHBoxLayout()
        tarih_row.setSpacing(8)
        tarih_row.addWidget(QLabel("Başlangıç Tarihi:"))
        self.dt_baslangic = QDateEdit(QDate.currentDate())
        self.dt_baslangic.setCalendarPopup(True)
        self.dt_baslangic.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_baslangic.setStyleSheet(S.get("date", ""))
        tarih_row.addWidget(self.dt_baslangic)
        tarih_row.addStretch()
        root.addLayout(tarih_row)

        # ─ Açıklama ─
        lbl_aciklama = QLabel("Açıklama (isteğe bağlı):")
        lbl_aciklama.setStyleSheet("font-size:10px;font-weight:600;")
        root.addWidget(lbl_aciklama)
        
        from PySide6.QtWidgets import QLineEdit
        self.txt_aciklama = QLineEdit()
        self.txt_aciklama.setStyleSheet(S["input"])
        self.txt_aciklama.setPlaceholderText("Örn: Yıllık Periyodik Bakım")
        root.addWidget(self.txt_aciklama)

        # ─ Progress ─
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)

        # ─ Butonlar ─
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_olustur = QPushButton("✅ Planları Oluştur")
        btn_olustur.setMinimumHeight(38)
        btn_olustur.setMinimumWidth(140)
        btn_olustur.setStyleSheet(S.get("btn_primary", ""))
        btn_olustur.clicked.connect(self._olustur_planlar)
        btn_layout.addWidget(btn_olustur)

        root.addLayout(btn_layout)

    def _load_cihazlar(self):
        """Tüm cihazları yükle."""
        self._all_cihazlar = []
        self.cmb_marka_filter.clear()
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        
        if not self._db:
            return
        
        try:
            repo = RepositoryRegistry(self._db).get("Cihazlar")
            self._all_cihazlar = repo.get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
            self._all_cihazlar = []

        markalar = sorted({c.get("Marka", "").strip() for c in self._all_cihazlar if c.get("Marka")})
        for marka in markalar:
            self.cmb_marka_filter.addItem(marka, marka)

        self._refresh_cihaz_list()

    def _refresh_cihaz_list(self):
        """Cihaz listesini güncelle."""
        self.list_cihazlar.clear()
        secili_marka = self.cmb_marka_filter.currentData()
        
        for cihaz in self._all_cihazlar:
            cid = cihaz.get("Cihazid", "")
            marka = (cihaz.get("Marka") or "").strip()
            if not cid:
                continue
            if secili_marka and marka != secili_marka:
                continue
            
            item = QListWidgetItem(f"{cid} - {marka}")
            item.setData(Qt.UserRole, cid)
            item.setCheckState(Qt.Unchecked)
            self.list_cihazlar.addItem(item)

    def _select_all_visible(self):
        """Tüm görünen cihazları seç."""
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.Checked)

    def _clear_selection(self):
        """Seçimi kaldır."""
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.Unchecked)

    def _olustur_planlar(self):
        """Planları oluştur."""
        secili_cihazlar = [
            self.list_cihazlar.item(i).data(Qt.UserRole)
            for i in range(self.list_cihazlar.count())
            if self.list_cihazlar.item(i).checkState() == Qt.Checked
        ]

        if not secili_cihazlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir cihaz seçin.")
            return

        plan_tipi = self.cmb_plan_tipi.currentText()
        baslangic_tarih = self.dt_baslangic.date().toPython()
        aciklama = self.txt_aciklama.text().strip() or "Periyodik Bakım"

        # Plan parametreleri
        tekrar = 1
        ay_artis = 0
        if "3 Ay" in plan_tipi:
            tekrar, ay_artis = 4, 3
        elif "6 Ay" in plan_tipi:
            tekrar, ay_artis = 2, 6
        elif "1 Yıl" in plan_tipi:
            tekrar, ay_artis = 1, 12

        base_id = int(time.time())
        kayitlar = []
        
        for cihaz_id in secili_cihazlar:
            for i in range(tekrar):
                yeni_tarih = ay_ekle(baslangic_tarih, i * ay_artis)
                tarih_str = yeni_tarih.strftime("%Y-%m-%d")

                kayit = {
                    "Planid": f"{cihaz_id}-BK-{base_id + i}",
                    "Cihazid": cihaz_id,
                    "BakimPeriyodu": plan_tipi.split("(")[0].strip(),
                    "BakimSirasi": f"{i+1}. Bakım",
                    "PlanlananTarih": tarih_str,
                    "Bakim": aciklama,
                    "Durum": "Planlandı",
                    "BakimTarihi": "",
                    "BakimTipi": "Periyodik",
                    "YapilanIslemler": "-",
                    "Aciklama": aciklama,
                    "Teknisyen": "-",
                    "Rapor": "-",
                }
                kayitlar.append(kayit)

        # DB'ye kaydet
        if not self._db:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return
        
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        self._saver = IslemKaydedici(self._db, "INSERT", kayitlar)
        self._saver.islem_tamam.connect(lambda: self._kayit_basarili(len(kayitlar)))
        self._saver.hata_olustu.connect(self._kayit_hatasi)
        self._saver.start()

    def _kayit_basarili(self, count: int):
        """Kayıt başarılı."""
        self.progress.setVisible(False)
        QMessageBox.information(
            self,
            "Başarılı",
            f"{count} bakım planı başarıyla oluşturuldu."
        )
        if self._on_success:
            self._on_success(count)
        if self._on_close:
            self._on_close()

    def _kayit_hatasi(self, hata: str):
        """Kayıt hatası."""
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Hata", f"Plan oluşturma başarısız: {hata}")


# ════════════════════════════════════════════════════════════════════
#  TOPLU PLAN DİALOGU
# ════════════════════════════════════════════════════════════════════
class TopluBakimPlanDlg(QDialog):
    """Toplu plan diyalog."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Toplu Bakım Planları")
        self.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._panel = TopluBakimPlanPanel(
            db=db,
            on_success=self.accept,
            on_close=self.close,
            parent=self,
        )
        layout.addWidget(self._panel)
