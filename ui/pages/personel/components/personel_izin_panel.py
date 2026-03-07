# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QTableView, QHeaderView
)
from PySide6.QtCore import Qt
from ui.components.base_table_model import BaseTableModel
from core.di import get_izin_service
from core.logger import logger
from ui.styles.components import STYLES as S
# datetime artık BaseTableModel içinde

# İzin Listesi Tablo sütunları
IZIN_COLUMNS = [
    ("IzinTipi",        "İzin Türü",        120),
    ("BaslamaTarihi",   "Başlangıç",        100),
    ("BitisTarihi",     "Bitiş",            100),
    ("Gun",             "Gün",               60),
    ("Aciklama",        "Açıklama",         200),
]

class RecentLeaveTableModel(BaseTableModel):
    def __init__(self, data=None, parent=None):
        super().__init__(IZIN_COLUMNS, data, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if "Tarihi" in key:
            return self._fmt_date(val, "-")
        return str(val) if val else ""

    def _align(self, key):
        if key in ("GunSayisi",) or "Tarihi" in key:
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


class PersonelIzinPanel(QWidget):
    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = personel_id
        self.izin_data = {}
        self.recent_leaves = []

        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # İzin Durumu Özetleri
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(20)

        # Yıllık İzin
        grp_yillik = QGroupBox("Yıllık İzin Durumu")
        grp_yillik.setStyleSheet(S["group"])
        g = QGridLayout(grp_yillik)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setContentsMargins(14, 12, 14, 12)

        self.lbl_y_devir = self._add_stat(g, 0, "Devir Eden İzin", "stat_value")
        self.lbl_y_hak = self._add_stat(g, 1, "Bu Yıl Hak Edilen", "stat_value")

        sep1 = QFrame(); sep1.setFixedHeight(1); sep1.setStyleSheet(S["separator"])
        g.addWidget(sep1, 2, 0, 1, 2)

        self.lbl_y_toplam = self._add_stat(g, 3, "TOPLAM İZİN HAKKI", "stat_highlight")
        self.lbl_y_kullanilan = self._add_stat(g, 4, "Kullanılan Yıllık İzin", "stat_red")

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet(S["separator"])
        g.addWidget(sep2, 5, 0, 1, 2)

        self.lbl_y_kalan = self._add_stat(g, 6, "KALAN YILLIK İZİN", "stat_green")
        self.lbl_diger_kullanilan = self._add_stat(g, 7, "Kullanılan Diğer İzinler", "stat_highlight")

        g.setRowStretch(8, 1)
        summary_layout.addWidget(grp_yillik)

        # Şua ve Diğer
        grp_diger = QGroupBox("Şua ve Diğer İzinler")
        grp_diger.setStyleSheet(S["group"])
        g2 = QGridLayout(grp_diger)
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(6)
        g2.setContentsMargins(14, 12, 14, 12)

        self.lbl_s_hak = self._add_stat(g2, 0, "Hak Edilen Şua İzin", "stat_value")
        self.lbl_s_kul = self._add_stat(g2, 1, "Kullanılan Şua İzinleri", "stat_red")

        sep3 = QFrame(); sep3.setFixedHeight(1); sep3.setStyleSheet(S["separator"])
        g2.addWidget(sep3, 2, 0, 1, 2)

        self.lbl_s_kalan = self._add_stat(g2, 3, "KALAN ŞUA İZNİ", "stat_green")

        sep4 = QFrame(); sep4.setFixedHeight(1); sep4.setStyleSheet(S["separator"])
        g2.addWidget(sep4, 4, 0, 1, 2)

        self.lbl_s_cari = self._add_stat(g2, 5, "Cari Yıl Şua Kazanım", "stat_value")

        g2.setRowStretch(6, 1)
        summary_layout.addWidget(grp_diger)

        main_layout.addLayout(summary_layout)

        # Son 1 Yıllık İzinler Listesi
        grp_recent_leaves = QGroupBox("Geçmiş İzin Hareketleri")
        grp_recent_leaves.setStyleSheet(S["group"])
        v_recent_leaves = QVBoxLayout(grp_recent_leaves)

        self._leave_table_model = RecentLeaveTableModel()
        self._leave_table_view = QTableView()
        self._leave_table_view.setModel(self._leave_table_model)
        self._leave_table_view.setStyleSheet(S["table"])
        self._leave_table_view.verticalHeader().setVisible(False)
        self._leave_table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._leave_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._leave_table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._leave_table_view.setAlternatingRowColors(True)

        header = self._leave_table_view.horizontalHeader()
        # Sütun genişliklerini ayarla ve kullanıcı tarafından yeniden boyutlandırmaya izin ver.
        # Son sütun (Açıklama) kalan alanı dolduracak şekilde genişler.
        for i, col_info in enumerate(IZIN_COLUMNS):
            width = col_info[2]
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            self._leave_table_view.setColumnWidth(i, width)
        header.setSectionResizeMode(len(IZIN_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        
        v_recent_leaves.addWidget(self._leave_table_view)
        main_layout.addWidget(grp_recent_leaves)

        main_layout.addStretch()

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["stat_label"])
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet(S[style_key])
        grid.addWidget(val, row, 1)
        return val

    def load_data(self):
        if not self.db or not self.personel_id:
            return

        try:
            izin_svc = get_izin_service(self.db)

            # İzin Bilgisi
            self.izin_data = izin_svc.get_izin_bilgi_repo().get_by_id(self.personel_id) or {}

            # Tüm İzin Hareketleri
            all_leaves = izin_svc.get_izin_giris_repo().get_all()
            self.recent_leaves = [
                l for l in all_leaves if str(l.get("Personelid", "")).strip() == self.personel_id
            ]
            self.recent_leaves.sort(key=lambda x: x.get("BaslangicTarihi", ""), reverse=True)

            self._update_ui()

        except Exception as e:
            logger.error(f"Personel izin verisi yükleme hatası ({self.personel_id}): {e}")
            # Hata durumunda UI'ı temizle
            self._clear_ui()

    def _update_ui(self):
        # İzin Durumu
        self.lbl_y_devir.setText(str(self.izin_data.get("YillikDevir", "0")))
        self.lbl_y_hak.setText(str(self.izin_data.get("YillikHakedis", "0")))
        self.lbl_y_toplam.setText(str(self.izin_data.get("YillikToplamHak", "0")))
        self.lbl_y_kullanilan.setText(str(self.izin_data.get("YillikKullanilan", "0")))
        self.lbl_y_kalan.setText(str(self.izin_data.get("YillikKalan", "0")))
        self.lbl_s_hak.setText(str(self.izin_data.get("SuaKullanilabilirHak", "0")))
        self.lbl_s_kul.setText(str(self.izin_data.get("SuaKullanilan", "0")))
        self.lbl_s_kalan.setText(str(self.izin_data.get("SuaKalan", "0")))
        self.lbl_s_cari.setText(str(self.izin_data.get("SuaCariYilKazanim", "0")))

        # Kullanılan Diğer İzinler (yıllık ve şua dışındaki)
        diger_kullanilan = sum(
            float(l.get("Gun", 0)) for l in self.recent_leaves
            if l.get("IzinTipi", "").strip() not in ("Yıllık İzin", "Şua İzin", "Şua İzni")
        )
        self.lbl_diger_kullanilan.setText(f"{diger_kullanilan:.0f}")

        # Son İzinler Tablosu
        self._leave_table_model.set_data(self.recent_leaves)


    def _clear_ui(self):
        for lbl in [self.lbl_y_devir, self.lbl_y_hak, self.lbl_y_toplam,
                    self.lbl_y_kullanilan, self.lbl_y_kalan, self.lbl_s_hak,
                    self.lbl_s_kul, self.lbl_s_kalan, self.lbl_s_cari,
                    self.lbl_diger_kullanilan]:
            lbl.setText("—")
        self._leave_table_model.set_data([])

    def set_embedded_mode(self, mode):
        # Bu panel zaten bir modül içinde gömülü olduğu için özel bir embedded mode ayarı gerekmeyebilir.
        # Ancak gelecekte başlıkları gizleme vb. gibi ihtiyaçlar olursa buraya eklenebilir.
        pass
