# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.di import get_nobet_service
from core.logger import logger
from ui.components.base_table_model import BaseTableModel


NOBET_COLUMNS = [
    ("NobetTarihi", "Tarih", 95),
    ("BirimAdi", "Birim", 150),
    ("VardiyaAdi", "Vardiya", 140),
    ("SaatAraligi", "Saat", 110),
    ("Sure", "Süre", 80),
    ("PlanDurum", "Plan", 90),
]

MESAI_COLUMNS = [
    ("Donem", "Dönem", 90),
    ("BirimAdi", "Birim", 150),
    ("Calisilan", "Çalışılan", 90),
    ("Hedef", "Hedef", 90),
    ("Fazla", "Bu Ay Fazla", 100),
    ("Devir", "Önceki Devir", 100),
    ("Toplam", "Toplam", 90),
    ("Odenen", "Ödenen", 90),
    ("DevireGiden", "Devire Giden", 100),
]


class NobetTableModel(BaseTableModel):
    DATE_KEYS = frozenset({"NobetTarihi"})
    ALIGN_CENTER = frozenset({"NobetTarihi", "SaatAraligi", "Sure", "PlanDurum"})

    def __init__(self, rows=None, parent=None):
        super().__init__(NOBET_COLUMNS, rows, parent)

    def _fg(self, key: str, row: dict):
        if key == "PlanDurum":
            return self.status_fg(str(row.get("PlanDurum", "")).title())
        return None


class MesaiTableModel(BaseTableModel):
    ALIGN_CENTER = frozenset({
        "Donem", "Calisilan", "Hedef", "Fazla", "Devir", "Toplam", "Odenen", "DevireGiden"
    })

    def __init__(self, rows=None, parent=None):
        super().__init__(MESAI_COLUMNS, rows, parent)

    def _fg(self, key: str, row: dict):
        if key in {"Fazla", "Toplam", "DevireGiden"}:
            ham = float(row.get(f"_{key}", 0) or 0)
            if ham > 0:
                return self.status_fg("Aktif")
            if ham < 0:
                return self.status_fg("Pasif")
        return None


class PersonelNobetMesaiPanel(QWidget):
    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = str(personel_id)
        self._svc = get_nobet_service(db) if db else None
        self._nobet_satirlari: list[dict] = []
        self._mesai_satirlari: list[dict] = []
        self._toplam_nobet_sayisi = 0
        self._toplam_nobet_dakika = 0
        self._toplam_fazla_dakika = 0
        self._son_bakiye_dakika = 0

        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)

        self.lbl_toplam_nobet = self._create_stat_card(summary_layout, "Toplam Nöbet")
        self.lbl_toplam_saat = self._create_stat_card(summary_layout, "Toplam Nöbet Saati")
        self.lbl_toplam_fazla = self._create_stat_card(summary_layout, "Toplam Fazla Mesai")
        self.lbl_son_bakiye = self._create_stat_card(summary_layout, "Son Devir Bakiyesi")

        main_layout.addLayout(summary_layout)

        grp_nobet = QGroupBox("Nöbet Geçmişi")
        grp_nobet.setProperty("style-role", "group")
        nobet_layout = QVBoxLayout(grp_nobet)
        self._nobet_model = NobetTableModel()
        self._nobet_table = QTableView()
        self._nobet_table.setModel(self._nobet_model)
        self._nobet_table.setProperty("style-role", "table")
        self._nobet_table.verticalHeader().setVisible(False)
        self._nobet_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._nobet_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._nobet_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._nobet_table.setAlternatingRowColors(True)
        self._nobet_model.setup_columns(self._nobet_table, stretch_keys=["BirimAdi", "VardiyaAdi"])
        nobet_layout.addWidget(self._nobet_table)
        main_layout.addWidget(grp_nobet, 1)

        grp_mesai = QGroupBox("Aylık Mesai Özeti")
        grp_mesai.setProperty("style-role", "group")
        mesai_layout = QVBoxLayout(grp_mesai)
        self._mesai_model = MesaiTableModel()
        self._mesai_table = QTableView()
        self._mesai_table.setModel(self._mesai_model)
        self._mesai_table.setProperty("style-role", "table")
        self._mesai_table.verticalHeader().setVisible(False)
        self._mesai_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._mesai_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._mesai_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._mesai_table.setAlternatingRowColors(True)
        self._mesai_model.setup_columns(self._mesai_table, stretch_keys=["BirimAdi"])
        header = self._mesai_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        mesai_layout.addWidget(self._mesai_table)
        main_layout.addWidget(grp_mesai, 1)

    def _create_stat_card(self, parent_layout: QHBoxLayout, title: str) -> QLabel:
        card = QFrame()
        card.setProperty("bg-role", "elevated")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        value_label = QLabel("—")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setProperty("style-role", "stat-value")

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setProperty("style-role", "stat-label")

        layout.addWidget(value_label)
        layout.addWidget(title_label)
        parent_layout.addWidget(card, 1)
        return value_label

    @staticmethod
    def _fmt_saat(dakika: int) -> str:
        isaret = "-" if dakika < 0 else ""
        dakika = abs(int(dakika))
        return f"{isaret}{dakika // 60}s {dakika % 60:02d}dk"

    def load_data(self):
        if not self._svc or not self.personel_id:
            return

        try:
            self._nobet_satirlari = self._nobet_gecmisi_getir()
            self._mesai_satirlari = self._mesai_ozeti_getir()
            self._nobet_model.set_data(self._nobet_satirlari)
            self._mesai_model.set_data(self._mesai_satirlari)
            self._update_summary()
        except Exception as exc:
            logger.error(f"Personel nöbet/mesai paneli yükleme hatası ({self.personel_id}): {exc}")
            self._nobet_model.set_data([])
            self._mesai_model.set_data([])
            self._clear_summary()

    def _nobet_gecmisi_getir(self) -> list[dict]:
        sonuc_yonetici = self._svc.get_personel_nobet_gecmisi(self.personel_id)
        rows = sonuc_yonetici.veri or [] if sonuc_yonetici.basarili else []

        toplam_nobet_sayisi = 0
        toplam_nobet_dakika = 0
        gosterim = []
        for r in rows:
            sure_dk = int(r.get("SureDakika", 0) or 0)
            toplam_nobet_sayisi += 1
            toplam_nobet_dakika += sure_dk
            gosterim.append({
                "NobetTarihi": r.get("NobetTarihi", ""),
                "BirimAdi":    r.get("BirimAdi", ""),
                "VardiyaAdi":  r.get("VardiyaAdi", ""),
                "SaatAraligi": r.get("SaatAraligi", ""),
                "Sure":        self._fmt_saat(sure_dk),
                "_SureDakika": sure_dk,
                "PlanDurum":   r.get("PlanDurum", ""),
            })

        self._toplam_nobet_sayisi = toplam_nobet_sayisi
        self._toplam_nobet_dakika = toplam_nobet_dakika
        return gosterim

    def _mesai_ozeti_getir(self) -> list[dict]:
        sonuc_yonetici = self._svc.get_personel_mesai_ozeti(self.personel_id)
        ilgili = sonuc_yonetici.veri or [] if sonuc_yonetici.basarili else []

        sonuc = []
        toplam_fazla_dakika = 0
        son_bakiye_dakika = 0
        for row in ilgili:
            calis        = int(row.get("CalisDakika", 0) or 0)
            hedef        = int(row.get("HedefDakika", 0) or 0)
            fazla        = int(row.get("FazlaDakika", 0) or 0)
            devir        = int(row.get("DevirDakika", 0) or 0)
            toplam       = int(row.get("ToplamFazlaDakika", 0) or 0)
            odenen       = int(row.get("OdenenDakika", 0) or 0)
            devire_giden = int(row.get("DevireGidenDakika", 0) or 0)
            toplam_fazla_dakika += fazla
            if not sonuc:
                son_bakiye_dakika = devire_giden

            sonuc.append({
                "Donem":       f"{int(row.get('Ay', 0) or 0):02d}/{int(row.get('Yil', 0) or 0)}",
                "BirimAdi":    row.get("BirimAdi", ""),
                "Calisilan":   self._fmt_saat(calis),
                "Hedef":       self._fmt_saat(hedef),
                "Fazla":       self._fmt_saat(fazla),
                "Devir":       self._fmt_saat(devir),
                "Toplam":      self._fmt_saat(toplam),
                "Odenen":      self._fmt_saat(odenen),
                "DevireGiden": self._fmt_saat(devire_giden),
                "_Fazla":      fazla,
                "_Toplam":     toplam,
                "_DevireGiden":devire_giden,
            })

        self._toplam_fazla_dakika = toplam_fazla_dakika
        self._son_bakiye_dakika   = son_bakiye_dakika
        return sonuc

    def _update_summary(self):
        self.lbl_toplam_nobet.setText(str(self._toplam_nobet_sayisi))
        self.lbl_toplam_saat.setText(self._fmt_saat(self._toplam_nobet_dakika))
        self.lbl_toplam_fazla.setText(self._fmt_saat(self._toplam_fazla_dakika))
        self.lbl_son_bakiye.setText(self._fmt_saat(self._son_bakiye_dakika))

    def _clear_summary(self):
        for label in (
            self.lbl_toplam_nobet,
            self.lbl_toplam_saat,
            self.lbl_toplam_fazla,
            self.lbl_son_bakiye,
        ):
            label.setText("—")

    def set_embedded_mode(self, mode):
        _ = mode
