from core.di import get_cihaz_service as _get_cihaz_service
# -*- coding: utf-8 -*-
import time
from datetime import datetime
from typing import Dict, List, cast

from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QDateEdit, QLineEdit, QFileDialog,
)

from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, uyari_goster



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
        layout.addWidget(title)

        lbl_marka = QLabel("Marka Filtresi:")
        lbl_marka.setProperty("color-role", "primary")
        lbl_marka.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_marka)

        self.cmb_marka_filter = QComboBox()
        self.cmb_marka_filter.setMinimumHeight(32)
        self.cmb_marka_filter.currentIndexChanged.connect(self._refresh_cihaz_list)
        layout.addWidget(self.cmb_marka_filter)

        # Sözleşme seçimi dropdown (Dokumanlar içinden)
        lbl_sozlesme = QLabel("Sözleşme seç (isteğe bağlı):")
        lbl_sozlesme.setProperty("color-role", "primary")
        lbl_sozlesme.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_sozlesme)

        self.cmb_sozlesme = QComboBox()
        self.cmb_sozlesme.setMinimumHeight(32)
        self.cmb_sozlesme.currentIndexChanged.connect(self._on_sozlesme_changed)
        layout.addWidget(self.cmb_sozlesme)

        # Yeni sözleşme ekle butonu
        self.btn_yeni_sozlesme = QPushButton("Sözleşme Yükle")
        self.btn_yeni_sozlesme.setProperty("style-role", "secondary")
        self.btn_yeni_sozlesme.setMinimumHeight(32)
        self.btn_yeni_sozlesme.clicked.connect(self._on_add_sozlesme)
        layout.addWidget(self.btn_yeni_sozlesme)

        lbl_cihaz = QLabel("Cihazlar Seçin:")
        lbl_cihaz.setProperty("color-role", "primary")
        lbl_cihaz.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_cihaz)

        self.list_cihazlar = QListWidget()
        self.list_cihazlar.setMaximumHeight(200)
        self.list_cihazlar.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_cihazlar)

        select_row = QHBoxLayout()
        btn_tumunu_sec = QPushButton("Tümünü Seç")
        btn_tumunu_sec.setProperty("style-role", "secondary")
        btn_tumunu_sec.clicked.connect(self._select_all_visible)
        select_row.addWidget(btn_tumunu_sec)

        btn_temizle = QPushButton("Seçimi Temizle")
        btn_temizle.setProperty("style-role", "secondary")
        btn_temizle.clicked.connect(self._clear_selection)
        select_row.addWidget(btn_temizle)

        select_row.addStretch()
        layout.addLayout(select_row)

        lbl_plan = QLabel("Bakım Planı Türü:")
        lbl_plan.setProperty("color-role", "primary")
        lbl_plan.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_plan)

        self.cmb_plan_tipi = QComboBox()
        self.cmb_plan_tipi.setMinimumHeight(36)
        self.cmb_plan_tipi.addItems([
            "Tek Seferlik",
            "3 Ay (4 Plan)",
            "6 Ay (2 Plan)",
            "1 Yıl (1 Plan)",
        ])
        layout.addWidget(self.cmb_plan_tipi)

        lbl_tarih = QLabel("Başlangıç Tarihi:")
        lbl_tarih.setProperty("color-role", "primary")
        lbl_tarih.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_tarih)

        self.dt_baslangic = QDateEdit(QDate.currentDate())
        self.dt_baslangic.setCalendarPopup(True)
        self.dt_baslangic.setDisplayFormat("dddd, d MMMM yyyy")
        self.dt_baslangic.setMinimumHeight(36)
        layout.addWidget(self.dt_baslangic)

        lbl_acik = QLabel("Bakım Açıklaması (isteğe bağlı):")
        lbl_acik.setProperty("color-role", "primary")
        lbl_acik.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_acik)

        self.txt_aciklama = QLineEdit()
        self.txt_aciklama.setPlaceholderText("Periyodik rutin bakım, ...")
        self.txt_aciklama.setMinimumHeight(36)
        layout.addWidget(self.txt_aciklama)

        # Sözleşme DokümanId (opsiyonel)
        lbl_soz = QLabel("Sözleşme DokümanId (opsiyonel):")
        lbl_soz.setProperty("color-role", "primary")
        lbl_soz.setStyleSheet("font-weight: 600;")
        layout.addWidget(lbl_soz)

        self.le_sozlesme_id = QLineEdit()
        self.le_sozlesme_id.setPlaceholderText("DokumanId girin veya boş bırakın")
        self.le_sozlesme_id.setMinimumHeight(36)
        layout.addWidget(self.le_sozlesme_id)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setMinimumHeight(38)
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.clicked.connect(self._on_close or (lambda: None))
        btn_layout.addWidget(btn_iptal)

        btn_layout.addStretch()

        btn_olustur = QPushButton("Planları Oluştur")
        btn_olustur.setMinimumHeight(38)
        btn_olustur.setMinimumWidth(120)
        btn_olustur.setProperty("style-role", "success-filled")
        btn_olustur.clicked.connect(self._olustur_planlar)
        btn_layout.addWidget(btn_olustur)

        layout.addLayout(btn_layout)
        self._load_cihazlar()

    def _load_cihazlar(self):
        self._all_cihazlar = []
        self.cmb_marka_filter.clear()
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        try:
            svc = _get_cihaz_service(self._db)
            self._all_cihazlar = svc.get_cihaz_listesi().veri or []
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
            self._all_cihazlar = []

        markalar = sorted({c.get("Marka", "").strip() for c in self._all_cihazlar if c.get("Marka")})
        for marka in markalar:
            self.cmb_marka_filter.addItem(marka, marka)

        self._refresh_cihaz_list()
        # load sozlesme list from Dokumanlar where EntityType='sozlesme'
        try:
            from core.di import get_dokuman_service
            svc = get_dokuman_service(self._db)
            sozler = svc.get_belgeler("sozlesme").veri or []
            # Expecting each row to have DokumanId and DisplayName
            self.cmb_sozlesme.clear()
            self.cmb_sozlesme.addItem("(Yok)", None)
            for s in sozler:
                dokid = s.get("DokumanId") or s.get("IliskiliBelgeID") or s.get("Belge")
                # Show the 'Belge' column (stored filename) in combo instead of DisplayName
                label = s.get("Belge") or s.get("DisplayName") or dokid
                self.cmb_sozlesme.addItem(str(label or ""), dokid)
        except Exception as e:
            logger.warning(f"Sözleşme listesi yüklenemedi: {e}")

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
            # If a sozlesme is selected, optionally filter devices here (skipped for now)
            item = QListWidgetItem(f"{c_id} - {c_marka}")
            item.setData(Qt.ItemDataRole.UserRole, c_id)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_cihazlar.addItem(item)

    def _on_sozlesme_changed(self, idx: int):
        """When user selects a sozlesme from dropdown, fill the SozlesmeId field."""
        try:
            dokid = self.cmb_sozlesme.itemData(idx)
            if dokid is None:
                # fallback to currentData
                dokid = self.cmb_sozlesme.currentData()
            if hasattr(self, 'le_sozlesme_id') and dokid:
                self.le_sozlesme_id.setText(str(dokid))
            elif hasattr(self, 'le_sozlesme_id'):
                self.le_sozlesme_id.clear()
        except Exception:
            # non-fatal: just ignore
            pass

    def _on_add_sozlesme(self):
        """Open file dialog, upload selected file as a 'sozlesme' document and select it."""
        try:
            # Require a brand to be selected
            marka = self.cmb_marka_filter.currentData()
            if not marka:
                uyari_goster(self, "Lütfen önce bir marka seçin.")
                return

            dlg = QFileDialog(self)
            dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
            dlg.setNameFilter("PDF Files (*.pdf);;All Files (*)")
            if dlg.exec() != QFileDialog.DialogCode.Accepted:
                return
            paths = dlg.selectedFiles()
            if not paths:
                return
            file_path = paths[0]

            from core.di import get_dokuman_service
            svc = get_dokuman_service(self._db)
            # Use entryid=<marka> as entity_id so we can track which brand the
            # agreement belongs to
            entity_id = f"{marka}"
            res = svc.upload_and_save(
                file_path=file_path,
                entity_type="sozlesme",
                entity_id=entity_id,
                belge_turu="Sözleşme",
                folder_name="Sozlesme",
                doc_type="Sozlesme",
                aciklama=f"Toplu plan sırasında yüklenen sözleşme (marka={marka})",
            )
            if not res.get("ok"):
                hata_goster(self, f"Sözleşme yüklenemedi: {res.get('error')}")
                return

            dokid = res.get("dokuman_id") or res.get("dokuman_id")
            # Use saved filename (belge_adi) as the combo label when possible
            label = res.get("belge_adi") or res.get("DisplayName") or dokid
            # add to combo and select
            self.cmb_sozlesme.addItem(str(label or ""), dokid)
            idx = self.cmb_sozlesme.findData(dokid)
            if idx >= 0:
                self.cmb_sozlesme.setCurrentIndex(idx)
            bilgi_goster(self, "Sözleşme yüklendi ve seçildi.")
        except Exception as e:
            logger.error(f"Sözleşme yükleme hatası: {e}")
            hata_goster(self, f"Sözleşme yükleme hatası: {e}")

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
            uyari_goster(self, "Lütfen en az bir cihaz seçin.")
            return

        plan_tipi = self.cmb_plan_tipi.currentText()
        baslangic_date = self.dt_baslangic.date().toPython()
        baslangic_tarih = cast(datetime, baslangic_date) if baslangic_date else datetime.now()
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
                    "SozlesmeId": (self.le_sozlesme_id.text().strip() or None),
                }
                kayitlar.append(kayit)

        try:
            svc = _get_cihaz_service(self._db)
            # If user selected a sozlesme, use its DokumanId
            selected_soz = None
            try:
                selected_soz = self.cmb_sozlesme.currentData()
            except Exception:
                selected_soz = None
            for kayit in kayitlar:
                if selected_soz:
                    kayit["SozlesmeId"] = selected_soz
                svc.bakim_ekle(kayit)
            self.toplam_plan = len(kayitlar)
            if self._on_success:
                self._on_success(self.toplam_plan)
            if self._on_close:
                self._on_close()
        except Exception as e:
            logger.error(f"Toplu planlama başarısız: {e}")
            hata_goster(self, f"Planlama başarısız: {e}")
