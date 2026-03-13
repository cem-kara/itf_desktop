# ui/pages/fhsz/puantaj_rapor_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Puantaj Raporu â€” Arayüz Taslağı
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate

from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from core.di import get_dis_alan_service
from core.services.dis_alan_service import _izin_gunu_hesapla

KOLONLAR = [
    ("TC Kimlik", 120),
    ("Ad Soyad", 180),
    ("Anabilim Dalı", 160),
    ("Alan", 200),
    ("Vaka Sayısı", 80),
    ("Katsayı", 80),
    ("Saat", 80),
    ("Küm. Saat", 90),
    ("İzin Gün", 80),
    ("Tutanak No", 120),
]

C_TC, C_AD, C_ANA, C_ALAN, C_VAKA, C_KATSAYI, C_SAAT, C_KUM, C_IZIN, C_TUTANAK = range(10)

class DisAlanPuantajRaporPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._svc = get_dis_alan_service(db) if db else None
        self.tablo: QTableWidget
        self.lbl_ozet: QLabel
        self.cmb_anabilim: QComboBox
        self.cmb_birim: QComboBox
        self.cmb_ay: QComboBox
        self.cmb_yil: QComboBox
        self.btn_raporla: QPushButton
        self.btn_export: QPushButton
        self._rows_cache = []
        self._setup_ui()
        self._connect_signals()
        self._load_all_rows()

    def _connect_signals(self):
        self.cmb_anabilim.currentIndexChanged.connect(self._on_anabilim_changed)
        self.btn_raporla.clicked.connect(self._load_data)
        self.btn_export.clicked.connect(self._export_excel)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)

        # Ãœst filtre paneli
        top = QFrame(self)
        top.setStyleSheet(S["filter_panel"])
        top.setMaximumHeight(56)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(12, 6, 12, 6)
        top_lay.setSpacing(12)

        lbl = QLabel("Dış Alan Puantaj Raporu")
        lbl.setStyleSheet("font-size:15px; font-weight:bold; color:#1D75FE;")
        top_lay.addWidget(lbl)
        top_lay.addStretch()

        # Anabilim Dalı
        lbl_ana = QLabel("Anabilim Dalı:")
        top_lay.addWidget(lbl_ana)
        self.cmb_anabilim = QComboBox()
        self.cmb_anabilim.setFixedWidth(160)
        top_lay.addWidget(self.cmb_anabilim)

        # Birim
        lbl_birim = QLabel("Birim:")
        top_lay.addWidget(lbl_birim)
        self.cmb_birim = QComboBox()
        self.cmb_birim.setFixedWidth(160)
        top_lay.addWidget(self.cmb_birim)

        # Dönem seçimi
        lbl_donem = QLabel("Dönem:")
        top_lay.addWidget(lbl_donem)
        self.cmb_ay = QComboBox()
        self.cmb_ay.addItems([
            "Ocak", "Åubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ])
        self.cmb_ay.setCurrentIndex(QDate.currentDate().month() - 1)
        self.cmb_ay.setFixedWidth(100)
        top_lay.addWidget(self.cmb_ay)

        self.cmb_yil = QComboBox()
        self.cmb_yil.addItems([
            str(y) for y in range(QDate.currentDate().year() - 2, QDate.currentDate().year() + 3)
        ])
        self.cmb_yil.setCurrentText(str(QDate.currentDate().year()))
        self.cmb_yil.setFixedWidth(100)
        top_lay.addWidget(self.cmb_yil)

        self.btn_raporla = QPushButton("Raporu Getir")
        self.btn_raporla.setStyleSheet(S["save_btn"])
        self.btn_raporla.setFixedHeight(36)
        IconRenderer.set_button_icon(self.btn_raporla, "search", color="#FFFFFF")
        top_lay.addWidget(self.btn_raporla)

        self.btn_export = QPushButton("Excel'e Aktar")
        self.btn_export.setStyleSheet(S["save_btn"])
        self.btn_export.setFixedHeight(36)
        IconRenderer.set_button_icon(self.btn_export, "download", color="#FFFFFF")
        top_lay.addWidget(self.btn_export)

        root.addWidget(top)

        # Tablo
        self.tablo = QTableWidget(self)
        self.tablo.setColumnCount(len(KOLONLAR))
        self.tablo.setHorizontalHeaderLabels([c[0] for c in KOLONLAR])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setStyleSheet(S["table"])
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for i, (_, w) in enumerate(KOLONLAR):
            self.tablo.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.tablo.setColumnWidth(i, w)
        root.addWidget(self.tablo)

        # Alt bilgi
        self.lbl_ozet = QLabel("", self)
        self.lbl_ozet.setStyleSheet("font-size:11px; color:#aaa;")
        root.addWidget(self.lbl_ozet)
    def _export_excel(self):
        try:
            import pandas as pd
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Eksik Paket", "'pandas' paketi yüklü değil.\n\nKurulum: pip install pandas openpyxl")
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "Excel'e Aktar", "puantaj_raporu.xlsx", "Excel Dosyası (*.xlsx)")
        if not path:
            return
        # Tabloyu DataFrame'e aktar
        data = []
        headers = []
        for i in range(self.tablo.columnCount()):
            header_item = self.tablo.horizontalHeaderItem(i)
            header_text = ""
            if header_item is not None and hasattr(header_item, "text") and callable(header_item.text):
                header_text = header_item.text()
            headers.append(header_text)
        for row in range(self.tablo.rowCount()):
            row_data = []
            for col in range(self.tablo.columnCount()):
                item = self.tablo.item(row, col)
                val = ""
                if item is not None and hasattr(item, "text") and callable(item.text):
                    val = item.text()
                row_data.append(val)
            data.append(row_data)
        df = pd.DataFrame(data, columns=headers)
        try:
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Başarılı", f"Excel dosyası kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel kaydedilemedi:\n{e}")

        # (Burada arayüz ekleme kodları gereksiz, kaldırıldı)

    def _load_all_rows(self):
        if not self._svc:
            return
        try:
            self._rows_cache = self._svc._r.get("Dis_Alan_Calisma").get_all() or []
        except Exception:
            self._rows_cache = []
        self._update_anabilim_combo()

    def _update_anabilim_combo(self):
        anabilimler = sorted(set(r.get("AnaBilimDali", "") for r in self._rows_cache if r.get("AnaBilimDali")))
        self.cmb_anabilim.blockSignals(True)
        self.cmb_anabilim.clear()
        self.cmb_anabilim.addItem("Tümü")
        self.cmb_anabilim.addItems(anabilimler)
        self.cmb_anabilim.blockSignals(False)
        self._on_anabilim_changed()

    def _on_anabilim_changed(self):
        secili_ana = self.cmb_anabilim.currentText()
        if secili_ana == "Tümü":
            birimler = sorted(set(r.get("Birim", "") for r in self._rows_cache if r.get("Birim")))
        else:
            birimler = sorted(set(r.get("Birim", "") for r in self._rows_cache if r.get("AnaBilimDali", "") == secili_ana and r.get("Birim")))
        self.cmb_birim.blockSignals(True)
        self.cmb_birim.clear()
        self.cmb_birim.addItem("Tümü")
        self.cmb_birim.addItems(birimler)
        self.cmb_birim.blockSignals(False)

    def _load_data(self):
        if not self._svc:
            return
        ay = self.cmb_ay.currentIndex() + 1
        yil = int(self.cmb_yil.currentText())
        ana = self.cmb_anabilim.currentText()
        birim = self.cmb_birim.currentText()
        rows_all = self._rows_cache or (self._svc._r.get("Dis_Alan_Calisma").get_all() or [])

        # Filtre uygula
        if ana != "Tümü":
            rows_all = [r for r in rows_all if r.get("AnaBilimDali", "") == ana]
        if birim != "Tümü":
            rows_all = [r for r in rows_all if r.get("Birim", "") == birim]

        def _to_int(val):
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        def _to_float(val):
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                return 0.0

        def _person_key(r):
            tc = str(r.get("TCKimlik", "")).strip()
            if tc:
                return f"tc:{tc}"
            ad = str(r.get("AdSoyad", "")).strip()
            return f"ad:{ad}"

        # Yıl bazlı kümülatif hesap
        yil_rows = [r for r in rows_all if _to_int(r.get("DonemYil", 0)) == yil]
        kum_map = {}
        for r in yil_rows:
            if _to_int(r.get("DonemAy", 0)) <= ay:
                key = _person_key(r)
                kum_map[key] = kum_map.get(key, 0.0) + _to_float(r.get("HesaplananSaat", 0))

        rows = [
            r for r in rows_all
            if _to_int(r.get("DonemAy", 0)) == ay and _to_int(r.get("DonemYil", 0)) == yil
        ]

        for r in rows:
            key = _person_key(r)
            kum = round(kum_map.get(key, 0.0), 2)
            r["_kumulatif_saat"] = kum
            r["_izin_gun_hakki"] = _izin_gunu_hesapla(kum)
        self._fill_table(rows)

    def _fill_table(self, rows):
        self.tablo.setRowCount(0)
        self.tablo.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tablo.setItem(i, C_TC, QTableWidgetItem(str(r.get("TCKimlik", ""))))
            self.tablo.setItem(i, C_AD, QTableWidgetItem(str(r.get("AdSoyad", ""))))
            self.tablo.setItem(i, C_ANA, QTableWidgetItem(str(r.get("AnaBilimDali", ""))))
            self.tablo.setItem(i, C_ALAN, QTableWidgetItem(str(r.get("IslemTipi", ""))))
            self.tablo.setItem(i, C_VAKA, QTableWidgetItem(str(r.get("VakaSayisi", ""))))
            self.tablo.setItem(i, C_KATSAYI, QTableWidgetItem(str(r.get("Katsayi", ""))))
            self.tablo.setItem(i, C_SAAT, QTableWidgetItem(str(r.get("HesaplananSaat", ""))))
            self.tablo.setItem(i, C_KUM, QTableWidgetItem(str(r.get("_kumulatif_saat", ""))))
            self.tablo.setItem(i, C_IZIN, QTableWidgetItem(str(r.get("_izin_gun_hakki", ""))))
            self.tablo.setItem(i, C_TUTANAK, QTableWidgetItem(str(r.get("TutanakNo", ""))))
        self.lbl_ozet.setText(f"Toplam kayıt: {len(rows)}")

    # Not: Henüz veri yükleme veya servis bağlantısı yok, sadece arayüz.

