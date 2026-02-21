# -*- coding: utf-8 -*-
"""
Cihaz Teknik Panel
─────────────────────────────────────
Teknik Bilgiler sekmesi icin cihaz teknik verilerini salt-okunur gosterir.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from database.repository_registry import RepositoryRegistry

C = DarkTheme

class CihazTeknikPanel(QWidget):
    """
    Cihaz Merkez ekranindaki 'Teknik Bilgiler' sekmesi icerigi.
    Cihaz teknik verilerini salt-okunur gosterir.
    """
    saved = Signal()

    def __init__(self, cihaz_id, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.cihaz_id = str(cihaz_id) if cihaz_id is not None else ""
        self.teknik_data = {}
        self._widgets = {}  # Alan adi -> Widget
        self._groups = {}   # Grup ID -> {widget, fields}
        self._link_fields = set()

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S["scroll"])

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Form grid
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(16)
        form_grid.setVerticalSpacing(16)
        form_grid.setColumnStretch(0, 1)
        layout.addLayout(form_grid)

        # 1. Tanimlayici Bilgiler
        grp_tanim, grid_tanim = self._create_section("Tanimlayici Bilgiler", "tanim")

        self._add_line(grid_tanim, 0, 0, "Cihaz ID", "Cihazid", "tanim", read_only=True)
        self._add_line(grid_tanim, 0, 1, "Urun Tanimi", "UrunTanimi", "tanim")
        self._add_line(grid_tanim, 1, 0, "Birincil Urun No", "BirincilUrunNumarasi", "tanim")
        self._add_line(grid_tanim, 1, 1, "Firma", "Firma", "tanim")
        self._add_line(grid_tanim, 2, 0, "Marka", "Marka", "tanim")
        self._add_line(grid_tanim, 2, 1, "Urun Adi", "UrunAdi", "tanim")
        self._add_line(grid_tanim, 3, 0, "Urun Kunyesi", "UrunKunye", "tanim")
        self._add_line(grid_tanim, 3, 1, "Turkce Etiket", "TurkceEtiket", "tanim")
        self._add_line(grid_tanim, 4, 0, "Orijinal Etiket", "OrijinalEtiket", "tanim")
        self._add_line(grid_tanim, 4, 1, "Versiyon/Model", "VersiyonModel", "tanim")
        self._add_line(grid_tanim, 5, 0, "Referans/Katalog No", "ReferansKatalogNo", "tanim")
        self._add_line(grid_tanim, 5, 1, "Urun Sayisi", "UrunSayisi", "tanim")
        self._add_line(grid_tanim, 6, 0, "Urun Aciklamasi", "UrunAciklamasi", "tanim", colspan=2)

        form_grid.addWidget(grp_tanim, 0, 0)

        # 2. Ithal/Imal Bilgileri
        grp_ithal, grid_ithal = self._create_section("Ithal/Imal Bilgileri", "ithal")

        self._add_line(grid_ithal, 0, 0, "Ithal/Imal Bilgisi", "IthalImalBilgisi", "ithal")
        self._add_line(grid_ithal, 0, 1, "Mensei Ulke", "MenseiUlke", "ithal")
        self._add_line(grid_ithal, 1, 0, "Ithal Edilen Ulke", "IthalEdilenUlke", "ithal")
        self._add_yesno_combo(grid_ithal, 1, 1, "Yerli Mali Belgesi Var mi", "YerliMaliBelgesiVarMi", "ithal")

        form_grid.addWidget(grp_ithal, 1, 0)

        # 3. Ozellikler
        grp_ozellik, grid_ozellik = self._create_section("Ozellikler", "ozellik")

        self._add_line(grid_ozellik, 0, 0, "MRG Guvenlik Bilgisi", "MRGGuvenlikBilgisi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 0, 1, "Lateks Iceriyor mu", "LateksIceriyorMu", "ozellik")
        self._add_yesno_combo(grid_ozellik, 1, 0, "Ftalat/DEHP Iceriyor mu", "FtalatDEHPIceriyorMu", "ozellik")
        self._add_yesno_combo(grid_ozellik, 1, 1, "Iyonize Radyasyon Icerir mi", "IyonizeRadyasyonIcerirMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 2, 0, "Nanomateryal Iceriyor mu", "NanomateryalIceriyorMu", "ozellik")
        self._add_yesno_combo(grid_ozellik, 2, 1, "Vucuda Implante Edilebilir mi", "ImplanteEdilebilirMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 3, 0, "Tek Kullanimlik mi", "TekKullanimlikMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 3, 1, "Sinirli Kullanim Sayisi Var mi", "SinirliKullanimSayisiVarMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 4, 0, "Tek Hasta Kullanim mi", "TekHastaKullanimMi", "ozellik")

        self._add_yesno_combo(grid_ozellik, 5, 0, "Raf Omru Var mi", "RafOmruVarMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 5, 1, "Kalibrasyona Tabi mi", "KalibrasyonaTabiMi", "ozellik")
        self._add_line(grid_ozellik, 6, 0, "Kalibrasyon Periyodu (Ay)", "KalibrasyonPeriyoduAy", "ozellik")
        self._add_yesno_combo(grid_ozellik, 6, 1, "Bakima Tabi mi", "BakimaTabiMi", "ozellik")
        self._add_line(grid_ozellik, 7, 0, "Bakim Periyodu (Ay)", "BakimPeriyoduAy", "ozellik")
        self._add_yesno_combo(grid_ozellik, 7, 1, "Steril Paketlendi mi", "SterilPaketlendiMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 8, 0, "Kullanim Oncesi Sterilizasyon Gerekli mi", "KullanimOncesiSterilizasyonGerekliMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 8, 1, "Ek-3 Kapsaminda mi", "Ek3KapsamindaMi", "ozellik")
        self._add_yesno_combo(grid_ozellik, 9, 0, "Bilesen/Aksesuar mi", "BilesenAksesuarMi", "ozellik")
        self._add_line(grid_ozellik, 9, 1, "Ekstra Bilgi Linki", "EkstraBilgiLinki", "ozellik")

        form_grid.addWidget(grp_ozellik, 2, 0)

        # 4. Urun Belgeleri ve Gorseller
        grp_belge, grid_belge = self._create_section("Urun Belgeleri ve Gorseller", "belge")

        self._add_file(grid_belge, 0, 0, "Urun Belgeleri", "UrunBelgeleri", "belge", colspan=2)
        self._add_file(grid_belge, 1, 0, "Urun Gorsel Dosyasi", "UrunGorselDosyasi", "belge", colspan=2)

        form_grid.addWidget(grp_belge, 3, 0)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_section(self, title, group_id):
        """Baslik + ince ayirici + icerik alanini olusturur."""
        section = QWidget()
        section.setStyleSheet("background: transparent;")

        vbox = QVBoxLayout(section)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        header_row = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {C.ACCENT}; font-weight: 700; font-size: 13px;"
        )
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        vbox.addLayout(header_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {C.BORDER_PRIMARY};")
        divider.setFixedHeight(1)
        vbox.addWidget(divider)

        content_widget = QWidget()
        grid = QGridLayout(content_widget)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 160)
        grid.setColumnMinimumWidth(2, 160)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        vbox.addWidget(content_widget)

        self._groups[group_id] = {
            "widget": content_widget,
            "fields": []
        }

        return section, grid

    def _add_line(self, grid, row, col, label, key, group_id, read_only=False, colspan=1):
        """Label degeri ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        value = QLabel("")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setWordWrap(True)
        value.setStyleSheet(
            f"background: transparent; color: {C.TEXT_PRIMARY}; font-weight: 500;"
        )
        self._widgets[key] = value
        self._groups[group_id]["fields"].append(key)
        base_col = col * 2
        span_cols = max(1, colspan * 2 - 1)
        grid.addWidget(lbl, row, base_col, 1, 1)
        grid.addWidget(value, row, base_col + 1, 1, span_cols)

    def _add_yesno_combo(self, grid, row, col, label, key, group_id, colspan=1):
        """Evet/Hayir degeri label olarak ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        value = QLabel("")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setWordWrap(True)
        value.setStyleSheet(
            f"background: transparent; color: {C.TEXT_PRIMARY}; font-weight: 500;"
        )
        self._widgets[key] = value
        self._groups[group_id]["fields"].append(key)
        base_col = col * 2
        span_cols = max(1, colspan * 2 - 1)
        grid.addWidget(lbl, row, base_col, 1, 1)
        grid.addWidget(value, row, base_col + 1, 1, span_cols)

    def _add_file(self, grid, row, col, label, key, group_id, colspan=1):
        """Dosya degeri label olarak ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        value = QLabel("")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setWordWrap(True)
        value.setOpenExternalLinks(True)
        value.setTextFormat(Qt.RichText)
        value.setStyleSheet(
            f"background: transparent; color: {C.ACCENT}; font-weight: 500;"
        )
        self._widgets[key] = value
        self._link_fields.add(key)
        self._groups[group_id]["fields"].append(key)
        base_col = col * 2
        span_cols = max(1, colspan * 2 - 1)
        grid.addWidget(lbl, row, base_col, 1, 1)
        grid.addWidget(value, row, base_col + 1, 1, span_cols)

    def _load_data(self):
        """Teknik verileri alana yukle."""
        if self.db and self.cihaz_id:
            try:
                registry = RepositoryRegistry(self.db)
                teknik_repo = registry.get("Cihaz_Teknik")
                teknik = teknik_repo.get_by_id(self.cihaz_id)
                if teknik:
                    self.teknik_data = teknik
                else:
                    self.teknik_data = {"Cihazid": self.cihaz_id}
            except Exception as e:
                logger.error(f"Teknik veri yukleme hatasi: {e}")
                self.teknik_data = {"Cihazid": self.cihaz_id}

        for key, widget in self._widgets.items():
            value = self.teknik_data.get(key, "")
            if key in self._link_fields and value:
                try:
                    uri = Path(str(value)).expanduser().resolve().as_uri()
                    widget.setText(f"<a href=\"{uri}\">{value}</a>")
                except Exception:
                    widget.setText(str(value))
            else:
                widget.setText(str(value or "-"))

    def load_data(self):
        """Veri yenileme (gerekirse)."""
        self._load_data()

    def set_embedded_mode(self, embedded: bool):
        """Gomulu mod ayari."""
        pass
