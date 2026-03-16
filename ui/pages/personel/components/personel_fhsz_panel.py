# -*- coding: utf-8 -*-
"""
Personel FHSZ Paneli
────────────────────
Personelin FHSZ_Puantaj tablosundaki kayıtlarını görüntüler.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QTableView, QHeaderView
)
from PySide6.QtCore import Qt

from core.di import get_fhsz_service
from core.hesaplamalar import sua_hak_edis_hesapla
from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles.components import STYLES as S

AY_ISIMLERI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

# Dönem sıralaması (ay adı -> sıra no)
AY_SIRA = {ay: i for i, ay in enumerate(AY_ISIMLERI)}

# FHSZ Puantaj Tablo Sütunları
FHSZ_COLUMNS = [
    ("AitYil",              "Yıl",              80),
    ("Donem",               "Dönem",            80),
    ("AylikGun",            "Top. Gün",         90),
    ("KullanilanIzin",      "Top. İzin",       100),
    ("FiiliCalismaSaat",    "Fiili Saat",      100),
    ("KumulatifSaat",       "Kümülatif Saat",  120),
    ("SuaHakEdis",          "Hak Edilen Şua",  120),
]


class FhszTableModel(BaseTableModel):
    """FHSZ puantaj kayıtları için tablo modeli."""
    
    def __init__(self, data=None, parent=None):
        super().__init__(FHSZ_COLUMNS, data, parent)

    def _display(self, key, row):
        """Hücre gösterim değeri."""
        value = row.get(key, "")
        return str(value) if value else ""

    def _align(self, key):
        """Hücre hizalama - sayısal değerler ortada."""
        if key in ("AitYil", "Donem", "AylikGun", "KullanilanIzin", "FiiliCalismaSaat", "KumulatifSaat", "SuaHakEdis"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


class PersonelFhszPanel(QWidget):
    """Personel FHSZ Puantaj bilgilerini gösteren panel."""

    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = personel_id
        self.fhsz_records = []
        
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Özet Bilgiler
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(20)

        # Toplam Kayıt Sayısı
        grp_toplam = QGroupBox("FHSZ Puantaj Özeti")
        grp_toplam.setProperty("style-role", "group")
        g = QGridLayout(grp_toplam)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setContentsMargins(14, 12, 14, 12)

        self.lbl_toplam_kayit = self._add_stat(g, 0, "Toplam Kayıt", "stat_value")
        self.lbl_toplam_gun = self._add_stat(g, 1, "Toplam Aylık Gün", "stat_value")
        self.lbl_toplam_izin = self._add_stat(g, 2, "Toplam Kullanılan İzin", "stat_value")
        self.lbl_toplam_saat = self._add_stat(g, 3, "Toplam Fiili Çalışma", "stat_highlight")

        g.setRowStretch(4, 1)
        summary_layout.addWidget(grp_toplam)

        grp_son_yil = QGroupBox("Yıl Bazlı Gösterge")
        grp_son_yil.setProperty("style-role", "group")
        g2 = QGridLayout(grp_son_yil)
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(6)
        g2.setContentsMargins(14, 12, 14, 12)

        self.lbl_yil_sayisi = self._add_stat(g2, 0, "Toplam Yıl", "stat_value")
        self.lbl_son_yil = self._add_stat(g2, 1, "Son Kayıt Yılı", "stat_value")
        self.lbl_son_yil_saat = self._add_stat(g2, 2, "Son Yıl Fiili Saat", "stat_highlight")
        self.lbl_son_yil_sua = self._add_stat(g2, 3, "Son Yıl Hak Edilen Şua", "stat_green")

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setProperty("bg-role", "separator")
        g2.addWidget(sep, 4, 0, 1, 2)

        self.lbl_yillik_ort_saat = self._add_stat(g2, 5, "Yıllık Ortalama Fiili Saat", "stat_value")

        g2.setRowStretch(6, 1)
        summary_layout.addWidget(grp_son_yil)

        summary_layout.addStretch()

        main_layout.addLayout(summary_layout)

        # 2. Puantaj Kayıtları Tablosu
        grp_kayitlar = QGroupBox("Puantaj Kayıtları")
        grp_kayitlar.setProperty("style-role", "group")
        v_kayitlar = QVBoxLayout(grp_kayitlar)

        self._table_model = FhszTableModel()
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setProperty("style-role", "table")
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table_view.setAlternatingRowColors(True)

        # Kolon genişliği ayarları
        header = self._table_view.horizontalHeader()
        for i, col_info in enumerate(FHSZ_COLUMNS):
            width = col_info[2]
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            self._table_view.setColumnWidth(i, width)
        header.setSectionResizeMode(len(FHSZ_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)

        v_kayitlar.addWidget(self._table_view)
        main_layout.addWidget(grp_kayitlar)

        main_layout.addStretch()

    def _add_stat(self, grid, row, text, style_key):
        """İstatistik satırı ekle."""
        lbl = QLabel(text)
        lbl.setProperty("style-role", "stat-label")
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setProperty("style-role", style_key)
        grid.addWidget(val, row, 1)
        return val

    def load_data(self):
        """FHSZ puantaj verilerini yükle."""
        if not self.db or not self.personel_id:
            return

        try:
            fhsz_svc = get_fhsz_service(self.db)
            raw_records = fhsz_svc.get_puantaj_listesi(personel_id=self.personel_id).veri or []

            def safe_int(val):
                try:
                    return int(str(val or "0").strip())
                except (ValueError, TypeError):
                    return 0

            def safe_float(val):
                try:
                    return float(str(val or "0").replace(",", ".").strip())
                except (ValueError, TypeError):
                    return 0.0

            def donem_sira(val):
                text = str(val or "").strip()
                if text in AY_SIRA:
                    return AY_SIRA[text]
                try:
                    return int(text)
                except (ValueError, TypeError):
                    return 99

            # puantaj_rapor mantığı: yıl bazında toplam satır üret (Donem = Toplam)
            yil_map = {}
            for rec in raw_records:
                yil_key = str(rec.get("AitYil", "")).strip()
                yil_map.setdefault(yil_key, []).append(rec)

            computed_records = []
            for yil in sorted(yil_map.keys(), key=safe_int, reverse=True):
                yil_rows = sorted(yil_map[yil], key=lambda r: donem_sira(r.get("Donem")))

                toplam_gun = 0
                toplam_izin = 0
                toplam_saat = 0.0

                for rec in yil_rows:
                    toplam_gun += safe_int(rec.get("AylikGun"))
                    toplam_izin += safe_int(rec.get("KullanilanIzin"))
                    toplam_saat += safe_float(rec.get("FiiliCalismaSaat"))

                toplam_sua = sua_hak_edis_hesapla(toplam_saat)

                computed_records.append({
                    "AitYil": yil,
                    "Donem": "Toplam",
                    "AylikGun": str(toplam_gun),
                    "KullanilanIzin": str(toplam_izin),
                    "FiiliCalismaSaat": f"{toplam_saat:.0f}",
                    "KumulatifSaat": f"{toplam_saat:.0f}",
                    "SuaHakEdis": f"{float(toplam_sua):.0f}",
                })

            self.fhsz_records = computed_records

            self._update_ui()

        except Exception as e:
            logger.error(f"FHSZ puantaj verisi yükleme hatası ({self.personel_id}): {e}")
            self._clear_ui()

    def _update_ui(self):
        """UI'ı güncel verilerle doldur."""
        def safe_float(val):
            try:
                return float(str(val or "0").replace(",", ".").strip())
            except (ValueError, TypeError):
                return 0.0
        
        def safe_int(val):
            try:
                return int(str(val or "0").strip())
            except (ValueError, TypeError):
                return 0
        
        # Özet İstatistikler
        toplam_kayit = len(self.fhsz_records)
        toplam_gun = sum(safe_int(r.get("AylikGun")) for r in self.fhsz_records)
        toplam_izin = sum(safe_int(r.get("KullanilanIzin")) for r in self.fhsz_records)
        toplam_saat = sum(safe_float(r.get("FiiliCalismaSaat")) for r in self.fhsz_records)
        yillik_ort_saat = (toplam_saat / toplam_kayit) if toplam_kayit > 0 else 0.0

        son_yil_row = self.fhsz_records[0] if self.fhsz_records else {}
        son_yil = str(son_yil_row.get("AitYil", "—"))
        son_yil_saat = safe_float(son_yil_row.get("FiiliCalismaSaat"))
        son_yil_sua = safe_float(son_yil_row.get("SuaHakEdis"))

        self.lbl_toplam_kayit.setText(str(toplam_kayit))
        self.lbl_toplam_gun.setText(f"{toplam_gun:.0f}")
        self.lbl_toplam_izin.setText(f"{toplam_izin:.0f}")
        self.lbl_toplam_saat.setText(f"{toplam_saat:.0f}")
        self.lbl_yil_sayisi.setText(str(toplam_kayit))
        self.lbl_son_yil.setText(son_yil)
        self.lbl_son_yil_saat.setText(f"{son_yil_saat:.0f}")
        self.lbl_son_yil_sua.setText(f"{son_yil_sua:.0f}")
        self.lbl_yillik_ort_saat.setText(f"{yillik_ort_saat:.1f}")

        # Tablo
        self._table_model.set_data(self.fhsz_records)

    def _clear_ui(self):
        """UI'ı temizle."""
        self.lbl_toplam_kayit.setText("—")
        self.lbl_toplam_gun.setText("—")
        self.lbl_toplam_izin.setText("—")
        self.lbl_toplam_saat.setText("—")
        self.lbl_yil_sayisi.setText("—")
        self.lbl_son_yil.setText("—")
        self.lbl_son_yil_saat.setText("—")
        self.lbl_son_yil_sua.setText("—")
        self.lbl_yillik_ort_saat.setText("—")
        self._table_model.set_data([])

    def set_embedded_mode(self, mode):
        """Gömülü mod ayarı (gelecekte ihtiyaç duyulursa)."""
        pass
