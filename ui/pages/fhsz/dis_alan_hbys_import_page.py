# -*- coding: utf-8 -*-
"""
Dış Alan HBYS Referans Import Ekranı

Akış:
  1. Kullanıcı IT'den gelen Excel/CSV dosyasını seçer
  2. Kolon başlıkları otomatik algılanır, kullanıcı sistem alanlarıyla eşleştirir
  3. Önizleme tablosu doldurulur
  4. "Kaydet" ile veriler referans tablosuna yazılır
  5. Denetim motoru referans verisi güncellenir
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from core.logger import logger
from ui.styles.icons import IconRenderer

SISTEM_ALANLARI = [
    ("AnaBilimDali", "Klinik"),
    ("Birim", "Birim/Ameliyathane"),
    ("DonemAy", "Ay"),
    ("DonemYil", "Yıl"),
    ("ToplamVaka", "Toplam Vaka"),
    ("OrtIslemSureDk", "Ort. Süre (dk)"),
    ("PersonelSayisi", "Personel Sayısı"),
    ("CKolluOrani", "C-Kollu Oranı"),
]

class DisAlanHbysImportPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._dosya_yolu = None
        self._header_map = {}
        self._veri = None  # DataFrame veya None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)

        # Üst bar
        top = QFrame()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("HBYS Referans Import")
        lbl.setProperty("style-role", "title")
        top_lay.addWidget(lbl)
        top_lay.addStretch()
        self.btn_dosya = QPushButton("Dosya Seç")
        IconRenderer.set_button_icon(self.btn_dosya, "folder", size=16)
        self.btn_dosya.setProperty("style-role", "secondary")
        top_lay.addWidget(self.btn_dosya)
        self.lbl_dosya = QLabel("Dosya seçilmedi")
        self.lbl_dosya.setProperty("color-role", "muted")
        top_lay.addWidget(self.lbl_dosya)
        root.addWidget(top)

        # Kolon eşleştirme paneli
        es_panel = QFrame()
        es_lay = QHBoxLayout(es_panel)
        es_lay.setContentsMargins(8, 4, 8, 4)
        self.cmb_map = {}
        for sys_key, sys_label in SISTEM_ALANLARI:
            es_lay.addWidget(QLabel(sys_label + ":"))
            cmb = QComboBox()
            cmb.setFixedWidth(140)
            self.cmb_map[sys_key] = cmb
            es_lay.addWidget(cmb)
        root.addWidget(es_panel)

        # Önizleme tablosu
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(SISTEM_ALANLARI))
        self.tablo.setHorizontalHeaderLabels([x[1] for x in SISTEM_ALANLARI])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        for i in range(len(SISTEM_ALANLARI)):
            self.tablo.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tablo)

        # Kaydet butonu
        btn_panel = QFrame()
        btn_lay = QHBoxLayout(btn_panel)
        btn_lay.addStretch()
        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setProperty("style-role", "action")
        IconRenderer.set_button_icon(self.btn_kaydet, "save", size=16)
        self.btn_kaydet.setEnabled(False)
        btn_lay.addWidget(self.btn_kaydet)
        root.addWidget(btn_panel)

    def _connect_signals(self):
        self.btn_dosya.clicked.connect(self._dosya_sec)
        self.btn_kaydet.clicked.connect(self._kaydet)

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Excel/CSV Dosyası Seç", "",
            "Excel Dosyaları (*.xlsx *.xlsm);;CSV Dosyaları (*.csv);;Tüm Dosyalar (*)"
        )
        if not yol:
            return
        self._dosya_yolu = yol
        self.lbl_dosya.setText(yol.split("/")[-1])
        self._oku_ve_eslestir()

    def _oku_ve_eslestir(self):
        # Excel/CSV başlıklarını oku
        if not self._dosya_yolu:
            QMessageBox.warning(self, "Dosya Yok", "Lütfen önce bir dosya seçin.")
            self.btn_kaydet.setEnabled(False)
            return
        try:
            import pandas as pd
            if self._dosya_yolu.endswith(".csv"):
                df = pd.read_csv(self._dosya_yolu, nrows=100)
            else:
                df = pd.read_excel(self._dosya_yolu, nrows=100)
            basliklar = list(df.columns)
            # Kolon eşleştirme comboboxlarını doldur
            for sys_key, _ in SISTEM_ALANLARI:
                cmb = self.cmb_map[sys_key]
                cmb.clear()
                cmb.addItems(["(Yok)"] + basliklar)
                # Otomatik eşleştirme
                for b in basliklar:
                    if sys_key.lower() in b.lower():
                        cmb.setCurrentText(b)
                        break
            self._veri = df
            self._tabloyu_doldur()
            self.btn_kaydet.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Okuma Hatası", str(e))
            self.btn_kaydet.setEnabled(False)

    def _tabloyu_doldur(self):
        df = self._veri
        self.tablo.setRowCount(0)
        if df is None:
            return
        try:
            import pandas as pd
            if not isinstance(df, pd.DataFrame) or df.empty:
                return
            self.tablo.setRowCount(min(50, len(df)))
            for row_i in range(min(50, len(df))):
                for col_i, (sys_key, _) in enumerate(SISTEM_ALANLARI):
                    cmb = self.cmb_map[sys_key]
                    col = cmb.currentText()
                    val = "" if col == "(Yok)" else str(df.iloc[row_i][col]) if col in df.columns else ""
                    self.tablo.setItem(row_i, col_i, QTableWidgetItem(val))
        except Exception:
            return

    def _kaydet(self):
        # Eşleştirme haritası
        header_map = {sys_key: self.cmb_map[sys_key].currentText() for sys_key, _ in SISTEM_ALANLARI}
        if any(v == "(Yok)" for v in header_map.values()):
            QMessageBox.warning(self, "Eşleştirme Eksik", "Tüm alanlar eşleştirilmeli.")
            return
        # Verileri hazırla
        df = self._veri
        veri_list = []
        try:
            import pandas as pd
            if not isinstance(df, pd.DataFrame) or df.empty:
                QMessageBox.warning(self, "Veri Yok", "Tabloda veri bulunamadı.")
                return
            for i in range(len(df)):
                kayit = {}
                for sys_key, _ in SISTEM_ALANLARI:
                    col = header_map[sys_key]
                    kayit[sys_key] = df.iloc[i][col] if col in df.columns else None
                veri_list.append(kayit)
        except Exception as e:
            QMessageBox.critical(self, "Veri Hatası", str(e))
            return
        # Servis ile kaydet
        try:
            from core.di import get_dis_alan_hbys_service
            svc = get_dis_alan_hbys_service(self._db)
            kayit_sayisi = svc.excel_import(veri_list)
            QMessageBox.information(self, "Import Tamamlandı", f"{kayit_sayisi} kayıt başarıyla eklendi.")
            self.btn_kaydet.setEnabled(False)
        except Exception as e:
            logger.error(f"HBYS import kaydet hata: {e}")
            QMessageBox.critical(self, "Kayıt Hatası", str(e))
