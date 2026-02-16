# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QScrollArea, QTableView, QHeaderView
)
from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from core.logger import logger
from ui.theme_manager import ThemeManager
from datetime import datetime, timedelta, date

# Stil tanımları
S = ThemeManager.get_all_component_styles()

# İzin Listesi Tablo sütunları
IZIN_COLUMNS = [
    ("IzinTipi",        "İzin Türü",        120),
    ("BaslamaTarihi",   "Başlangıç",        100),
    ("BitisTarihi",     "Bitiş",            100),
    ("Gun",             "Gün",               60),
    ("Aciklama",        "Açıklama",         200),
]

class RecentLeaveTableModel(QAbstractTableModel):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._keys = [c[0] for c in IZIN_COLUMNS]
        self._headers = [c[1] for c in IZIN_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(IZIN_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col_key = self._keys[index.column()]
        if role == Qt.DisplayRole:
            value = row.get(col_key, "")
            # Tarih formatlamasını _fmt_date fonksiyonuna bırakalım.
            if "Tarihi" in col_key:
                return self._fmt_date(value)
            return str(value)
        if role == Qt.TextAlignmentRole:
            if col_key == "GunSayisi":
                return Qt.AlignCenter
            if "Tarihi" in col_key:
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def _fmt_date(self, val):
        if not val: return "-"
        try:
            dt = None
            if isinstance(val, (datetime, date)):
                dt = val
            elif isinstance(val, QDate):
                dt = val.toPython()
            else:
                val_str = str(val).strip()
                if ' ' in val_str:
                    val_str = val_str.split(' ')[0]
                if '-' in val_str:
                    dt = datetime.strptime(val_str, "%Y-%m-%d")

            if dt:
                return dt.strftime("%d.%m.%Y")

        except Exception as e:
            logger.warning(f"Tarih formatlama hatası: {val} - {e}")
        return str(val)


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
        grp_yillik = QGroupBox("📅  Yıllık İzin Durumu")
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

        g.setRowStretch(7, 1)
        summary_layout.addWidget(grp_yillik)

        # Şua ve Diğer
        grp_diger = QGroupBox("☢️  Şua ve Diğer İzinler")
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
        self.lbl_diger = self._add_stat(g2, 6, "Toplam Rapor/Mazeret", "stat_value")

        g2.setRowStretch(7, 1)
        summary_layout.addWidget(grp_diger)

        main_layout.addLayout(summary_layout)

        # Son 1 Yıllık İzinler Listesi
        grp_recent_leaves = QGroupBox("🗓️  Geçmiş İzin Hareketleri")
        grp_recent_leaves.setStyleSheet(S["group"])
        v_recent_leaves = QVBoxLayout(grp_recent_leaves)

        self._leave_table_model = RecentLeaveTableModel()
        self._leave_table_view = QTableView()
        self._leave_table_view.setModel(self._leave_table_model)
        self._leave_table_view.setStyleSheet(S["table"])
        self._leave_table_view.verticalHeader().setVisible(False)
        self._leave_table_view.setEditTriggers(QTableView.NoEditTriggers)
        self._leave_table_view.setSelectionBehavior(QTableView.SelectRows)
        self._leave_table_view.setSelectionMode(QTableView.SingleSelection)
        self._leave_table_view.setAlternatingRowColors(True)

        header = self._leave_table_view.horizontalHeader()
        # Sütun genişliklerini ayarla ve kullanıcı tarafından yeniden boyutlandırmaya izin ver.
        # Son sütun (Açıklama) kalan alanı dolduracak şekilde genişler.
        for i, col_info in enumerate(IZIN_COLUMNS):
            width = col_info[2]
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self._leave_table_view.setColumnWidth(i, width)
        header.setSectionResizeMode(len(IZIN_COLUMNS) - 1, QHeaderView.Stretch)
        
        v_recent_leaves.addWidget(self._leave_table_view)
        main_layout.addWidget(grp_recent_leaves)

        main_layout.addStretch()

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["stat_label"])
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(S[style_key])
        grid.addWidget(val, row, 1)
        return val

    def load_data(self):
        if not self.db or not self.personel_id:
            return

        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self.db)

            # İzin Bilgisi
            izin_repo = registry.get("Izin_Bilgi")
            self.izin_data = izin_repo.get_by_id(self.personel_id) or {}

            # Tüm İzin Hareketleri
            izin_giris_repo = registry.get("Izin_Giris")
            all_leaves = izin_giris_repo.get_all()
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
        self.lbl_diger.setText(str(self.izin_data.get("RaporMazeretTop", "0")))

        # Son İzinler Tablosu
        self._leave_table_model.set_data(self.recent_leaves)


    def _clear_ui(self):
        for lbl in [self.lbl_y_devir, self.lbl_y_hak, self.lbl_y_toplam,
                    self.lbl_y_kullanilan, self.lbl_y_kalan, self.lbl_s_hak,
                    self.lbl_s_kul, self.lbl_s_kalan, self.lbl_s_cari, self.lbl_diger]:
            lbl.setText("—")
        self._leave_table_model.set_data([])

    def set_embedded_mode(self, mode):
        # Bu panel zaten bir modül içinde gömülü olduğu için özel bir embedded mode ayarı gerekmeyebilir.
        # Ancak gelecekte başlıkları gizleme vb. gibi ihtiyaçlar olursa buraya eklenebilir.
        pass