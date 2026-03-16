# -*- coding: utf-8 -*-
"""
personel_import.py — Toplu Personel Excel İçe Aktarma Sihirbazı
Kurumların personel listesini Excel (.xlsx) dosyasından hızlıca sisteme eklemek için sihirbaz.
Dozimetre import sayfası örnek alınmıştır.
"""
from __future__ import annotations
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QTableView, QMessageBox
)
from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel
from core.logger import logger

class PersonelImportPage(QWidget):
      def _normalize_record(self, kayit):
        """
        Excel'den gelen bir personel kaydını normalize eder:
        - KimlikNo: string, baştaki sıfırlar korunur, başlık varyasyonları desteklenir
        - Tarih alanları: DB formatına çevrilir
        - Boşluklar kırpılır
        """
        from core.date_utils import to_db_date
        columns = [
            "KimlikNo","AdSoyad","DogumYeri","DogumTarihi","HizmetSinifi",
            "KadroUnvani","GorevYeri","KurumSicilNo","MemuriyeteBaslamaTarihi",
            "CepTelefonu","Eposta","MezunOlunanOkul","MezunOlunanFakulte",
            "MezuniyetTarihi","DiplomaNo","MezunOlunanOkul2",
            "MezunOlunanFakulte2","MezuniyetTarihi2","DiplomaNo2",
            "Resim","Diploma1","Diploma2","OzlukDosyasi","Durum",
            "AyrilisTarihi","AyrilmaNedeni","MuayeneTarihi","Sonuc"
        ]
        date_fields = [
            "DogumTarihi","MemuriyeteBaslamaTarihi","MezuniyetTarihi",
            "MezuniyetTarihi2","AyrilisTarihi","MuayeneTarihi"
        ]
        # KimlikNo başlık varyasyonları
        kimlik_keys = [
            "KimlikNo", "Kimlik_No", "TC", "TC Kimlik No", "TC_Kimlik_No", "TCKimlikNo", "TCKimlik", "T.C. Kimlik No"
        ]
        # Excel'den gelen başlıkları normalize et (küçük harf, boşluk/altçizgi sil)
        def normkey(k):
            return str(k).replace(" ", "").replace("_", "").replace(".", "").lower()
        kayit_keys_norm = {normkey(k): k for k in kayit.keys()}
        out = {}
        for col in columns:
            val = ""
            if col == "KimlikNo":
                # KimlikNo için varyasyonları sırayla dene
                for k in kimlik_keys:
                    nk = normkey(k)
                    if nk in kayit_keys_norm:
                        val = kayit.get(kayit_keys_norm[nk], "")
                        break
                if pd.isna(val):
                    val = ""
                val = str(val).strip()
                if val and val.isdigit() and len(val) < 11:
                    val = val.zfill(11)
            else:
                # Diğer alanlar için doğrudan başlık eşleştir
                nk = normkey(col)
                if nk in kayit_keys_norm:
                    val = kayit.get(kayit_keys_norm[nk], "")
                if pd.isna(val):
                    val = ""
                if col in date_fields:
                    val = to_db_date(val)
                if isinstance(val, str):
                    val = val.strip()
            out[col] = val
        return out
      def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Toplu Personel Excel İçe Aktar")
        self.resize(800, 600)
        self._build_ui()
        self._data = []

      def _build_ui(self):
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("Excel Dosyası Seç (.xlsx)")
        self.btn_select.clicked.connect(self._select_file)
        btn_layout.addWidget(self.btn_select)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        self.table = QTableView()
        self.model = BaseTableModel([], [])
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        self.btn_import = QPushButton("İçe Aktar")
        self.btn_import.clicked.connect(self._import_data)
        self.btn_import.setEnabled(False)
        layout.addWidget(self.btn_import)

      def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyası (*.xlsx)")
        if not file_path:
            return
        try:
            df = pd.read_excel(file_path)
            if df.empty:
                self.lbl_status.setText("Seçilen dosyada veri bulunamadı.")
                self.btn_import.setEnabled(False)
                return
            self._data = df.to_dict(orient="records")
            # Sütunları (db_key, başlık, genişlik) tuple'ına çevir
            columns = [(col, col, 120) for col in df.columns]
            self.model = BaseTableModel(columns, self._data)
            self.table.setModel(self.model)
            self.lbl_status.setText(f"{len(self._data)} kayıt yüklendi.")
            self.btn_import.setEnabled(True)
        except Exception as e:
            logger.error(f"Excel okuma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Excel dosyası okunamadı:\n{e}")
            self.btn_import.setEnabled(False)

      def _import_data(self):
        # PersonelService'e erişim için doğrudan self._db kullan
        if self._db is None:
            QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı bulunamadı. Lütfen uygulamayı yeniden başlatın.")
            return

        try:
            from core.di import get_personel_service
            svc = get_personel_service(self._db)
        except Exception as e:
            logger.error(f"Personel servisi başlatılamadı: {e}")
            QMessageBox.critical(self, "Hata", f"Personel servisi başlatılamadı:\n{e}")
            return

        basarili = 0
        hatali = 0
        hata_listesi = []
        for idx, kayit in enumerate(self._data, 1):
            norm = self._normalize_record(kayit)
            sonuc = svc.ekle(norm)
            if sonuc.basarili:
                basarili += 1
            else:
                hatali += 1
                # Hatalı alanı detaylı göster
                kimlik = norm.get("KimlikNo", "")
                hata_listesi.append(f"{idx}. satır (KimlikNo: {kimlik}): {sonuc.mesaj}")

        msg = f"{basarili} kayıt başarıyla eklendi."
        if hatali > 0:
            msg += f"\n{hatali} kayıt eklenemedi."
            if len(hata_listesi) <= 10:
                msg += "\n\nHatalı kayıtlar:\n" + "\n".join(hata_listesi)
            else:
                msg += "\n(Hatalı kayıtların ilk 10'u):\n" + "\n".join(hata_listesi[:10])

        if basarili > 0:
            QMessageBox.information(self, "İçe Aktarma Tamamlandı", msg)
        else:
            QMessageBox.critical(self, "Hiçbir Kayıt Eklenemedi", msg)