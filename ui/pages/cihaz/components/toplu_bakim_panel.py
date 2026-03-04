from core.di import get_cihaz_service as _get_cihaz_service
# -*- coding: utf-8 -*-
import time
from datetime import datetime
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QDateEdit, QLineEdit, QMessageBox,
)

from core.logger import logger

from ui.styles.colors import C as _C
from ui.styles.components import STYLES as S


def ay_ekle(kaynak_tarih: datetime, ay_sayisi: int) -> datetime:
    return kaynak_tarih + relativedelta(months=ay_sayisi)


class TopluBakimPlanPanel(QWidget):
    """Birden fazla cihaz için toplu bakım planlaması (sağ panel içinde)."""

    def __init__(self, db=None, on_success=None, on_close=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.toplam_plan = 0
        self._all_cihazlar: List[Dict] = []
        self._on_success = on_success
        self._on_close = on_close
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Toplu Bakım Planı Oluştur")
        title.setProperty("color-role", "accent")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title.style().unpolish(title)
        title.style().polish(title)
        layout.addWidget(title)

        lbl_marka = QLabel("Marka Filtresi:")
        lbl_marka.setProperty("color-role", "primary")
        lbl_marka.setStyleSheet("font-weight: 600;")
        lbl_marka.style().unpolish(lbl_marka)
        lbl_marka.style().polish(lbl_marka)
        layout.addWidget(lbl_marka)

        self.cmb_marka_filter = QComboBox()
        self.cmb_marka_filter.setStyleSheet(S["combo"])
        self.cmb_marka_filter.setMinimumHeight(32)
        self.cmb_marka_filter.currentIndexChanged.connect(self._refresh_cihaz_list)
        layout.addWidget(self.cmb_marka_filter)

        lbl_cihaz = QLabel("Cihazlar Seçin:")
        lbl_cihaz.setProperty("color-role", "primary")
        lbl_cihaz.setStyleSheet("font-weight: 600;")
        lbl_cihaz.style().unpolish(lbl_cihaz)
        lbl_cihaz.style().polish(lbl_cihaz)
        layout.addWidget(lbl_cihaz)

        self.list_cihazlar = QListWidget()
        self.list_cihazlar.setStyleSheet(S.get("list", ""))
        self.list_cihazlar.setMaximumHeight(200)
        self.list_cihazlar.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_cihazlar)

        select_row = QHBoxLayout()
        btn_tumunu_sec = QPushButton("Tümünü Seç")
        btn_tumunu_sec.setStyleSheet(S.get("btn_secondary", ""))
        btn_tumunu_sec.clicked.connect(self._select_all_visible)
        select_row.addWidget(btn_tumunu_sec)

        btn_temizle = QPushButton("Seçimi Temizle")
        btn_temizle.setStyleSheet(S.get("btn_secondary", ""))
        btn_temizle.clicked.connect(self._clear_selection)
        select_row.addWidget(btn_temizle)

        select_row.addStretch()
        layout.addLayout(select_row)

        lbl_plan = QLabel("Bakım Planı Türü:")
        lbl_plan.setProperty("color-role", "primary")
        lbl_plan.setStyleSheet("font-weight: 600;")
        lbl_plan.style().unpolish(lbl_plan)
        lbl_plan.style().polish(lbl_plan)
        layout.addWidget(lbl_plan)

        self.cmb_plan_tipi = QComboBox()
        self.cmb_plan_tipi.setStyleSheet(S["combo"])
        self.cmb_plan_tipi.setMinimumHeight(36)
        self.cmb_plan_tipi.addItems([
            "📌 Tek Seferlik",
            "🔄 3 Ay (4 Plan)",
            "⏱️  6 Ay (2 Plan)",
            "📆 1 Yıl (1 Plan)",
        ])
        layout.addWidget(self.cmb_plan_tipi)

        lbl_tarih = QLabel("Başlangıç Tarihi:")
        lbl_tarih.setProperty("color-role", "primary")
        lbl_tarih.setStyleSheet("font-weight: 600;")
        lbl_tarih.style().unpolish(lbl_tarih)
        lbl_tarih.style().polish(lbl_tarih)
        layout.addWidget(lbl_tarih)

        self.dt_baslangic = QDateEdit(QDate.currentDate())
        self.dt_baslangic.setCalendarPopup(True)
        self.dt_baslangic.setDisplayFormat("dddd, d MMMM yyyy")
        self.dt_baslangic.setStyleSheet(S["date"])
        self.dt_baslangic.setMinimumHeight(36)
        layout.addWidget(self.dt_baslangic)

        lbl_acik = QLabel("Bakım Açıklaması (isteğe bağlı):")
        lbl_acik.setProperty("color-role", "primary")
        lbl_acik.setStyleSheet("font-weight: 600;")
        lbl_acik.style().unpolish(lbl_acik)
        lbl_acik.style().polish(lbl_acik)
        layout.addWidget(lbl_acik)

        self.txt_aciklama = QLineEdit()
        self.txt_aciklama.setStyleSheet(S["input"])
        self.txt_aciklama.setPlaceholderText("Periyodik rutin bakım, ...")
        self.txt_aciklama.setMinimumHeight(36)
        layout.addWidget(self.txt_aciklama)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_iptal = QPushButton("❌ İptal")
        btn_iptal.setMinimumHeight(38)
        btn_iptal.setStyleSheet(
            f"QPushButton{{background:{_C['panel']};border:1px solid {_C['border']};"
            f"border-radius:6px;color:{_C['text']};font-weight:bold;}}"
        )
        btn_iptal.clicked.connect(self._on_close or (lambda: None))
        btn_layout.addWidget(btn_iptal)

        btn_layout.addStretch()

        btn_olustur = QPushButton("✅ Planları Oluştur")
        btn_olustur.setMinimumHeight(38)
        btn_olustur.setMinimumWidth(120)
        btn_olustur.setStyleSheet(
            f"QPushButton{{background:{_C['green']};border:none;"
            f"border-radius:6px;color:white;font-weight:bold;font-size:12px;}}"
            f"QPushButton:hover{{background:#2e7d32;}}"
        )
        btn_olustur.clicked.connect(self._olustur_planlar)
        btn_layout.addWidget(btn_olustur)

        layout.addLayout(btn_layout)
        self._load_cihazlar()

    def _load_cihazlar(self):
        self._all_cihazlar = []
        self.cmb_marka_filter.clear()
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        try:
            repo = _get_cihaz_service(self._db)._r.get("Cihazlar")
            self._all_cihazlar = repo.get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
            self._all_cihazlar = []

        markalar = sorted({c.get("Marka", "").strip() for c in self._all_cihazlar if c.get("Marka")})
        for marka in markalar:
            self.cmb_marka_filter.addItem(marka, marka)

        self._refresh_cihaz_list()

    def _refresh_cihaz_list(self):
        self.list_cihazlar.clear()
        secili_marka = self.cmb_marka_filter.currentData()
        for cihaz in self._all_cihazlar:
            c_id = cihaz.get("Cihazid", "")
            c_marka = (cihaz.get("Marka") or "").strip()
            if not c_id:
                continue
            if secili_marka and c_marka != secili_marka:
                continue
            item = QListWidgetItem(f"{c_id} - {c_marka}")
            item.setData(Qt.ItemDataRole.UserRole, c_id)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_cihazlar.addItem(item)

    def _select_all_visible(self):
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.CheckState.Checked)

    def _clear_selection(self):
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _olustur_planlar(self):
        secili_cihazlar = [
            self.list_cihazlar.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list_cihazlar.count())
            if self.list_cihazlar.item(i).checkState() == Qt.CheckState.Checked
        ]

        if not secili_cihazlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir cihaz seçin.")
            return

        plan_tipi = self.cmb_plan_tipi.currentText()
        baslangic_tarih = self.dt_baslangic.date().toPython()
        aciklama = self.txt_aciklama.text().strip() or "Periyodik Bakım"

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

        try:
            repo = _get_cihaz_service(self._db)._r.get("Periyodik_Bakim")
            for kayit in kayitlar:
                repo.insert(kayit)
            self.toplam_plan = len(kayitlar)
            if self._on_success:
                self._on_success(self.toplam_plan)
            if self._on_close:
                self._on_close()
        except Exception as e:
            logger.error(f"Toplu planlama başarısız: {e}")
            QMessageBox.critical(self, "Hata", f"Planlama başarısız: {e}")
