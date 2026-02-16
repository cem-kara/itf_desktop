# -*- coding: utf-8 -*-
"""
RKE Envanter YÃ¶netimi SayfasÄ±
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
â€¢ Sol: Ekipman ekle / gÃ¼ncelle formu + muayene geÃ§miÅŸi
â€¢ SaÄŸ: QAbstractTableModel + QSortFilterProxyModel tablosu
â€¢ itf_desktop mimarisine uygun (get_registry(db), core.logger, GoogleDriveService)
"""
from PySide6.QtCore import Qt, QDate, QThread, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit,
    QDateEdit, QGroupBox, QMessageBox, QTableView, QHeaderView,
    QTextEdit, QAbstractItemView, QMenu, QSplitter
)
from PySide6.QtGui import QColor, QCursor, QIntValidator

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager

# â”€â”€â”€ Merkezi Stiller â”€â”€â”€
S = ThemeManager.get_all_component_styles()

# â”€â”€â”€ Tablo sÃ¼tun tanÄ±mlarÄ± â”€â”€â”€
COLUMNS = [
    ("KayitNo",         "ID",            80),
    ("EkipmanNo",       "Ekipman No",   120),
    ("KoruyucuNumarasi","Koruyucu No",  130),
    ("AnaBilimDali",    "ABD",          140),
    ("Birim",           "Birim",        130),
    ("KoruyucuCinsi",   "Cins",         130),
    ("KontrolTarihi",   "Son Kontrol",  110),
    ("Durum",           "Durum",         90),
]

DURUM_RENK = {
    "KullanÄ±ma Uygun":       QColor("#4ade80"),
    "KullanÄ±ma Uygun DeÄŸil": QColor("#f87171"),
    "Hurda":                  QColor("#ef4444"),
    "Tamirde":                QColor("#facc15"),
    "KayÄ±p":                  QColor("#a78bfa"),
}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TABLO MODELÄ°
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class RKETableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row     = self._data[index.row()]
        col_key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col_key, ""))

        if role == Qt.ForegroundRole and col_key == "Durum":
            durum = str(row.get("Durum", ""))
            return DURUM_RENK.get(durum, QColor("#8b8fa3"))

        if role == Qt.TextAlignmentRole:
            if col_key in ("KayitNo", "KontrolTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  WORKER THREAD'LER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class VeriYukleyiciThread(QThread):
    """Sabitler + RKE_List + RKE_Muayene verisini arka planda yÃ¼kler."""
    veri_hazir   = Signal(dict, dict, list, list)  # sabitler, kisaltma_maps, rke_data, muayene_data
    hata_olustu  = Signal(str)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db = SQLiteManager()
            registry = get_registry(db)

            sabitler = {}
            maps     = {"AnaBilimDali": {}, "Birim": {}, "Koruyucu_Cinsi": {}}
            kodlar   = ["AnaBilimDali", "Birim", "Koruyucu_Cinsi", "Bedeni"]

            all_sabit = registry.get("Sabitler").get_all()
            for kod in kodlar:
                sabitler[kod] = []
                for satir in [x for x in all_sabit if x.get("Kod") == kod]:
                    eleman    = str(satir.get("MenuEleman", "")).strip()
                    kisaltma  = str(satir.get("Aciklama",   "")).strip()
                    if eleman:
                        sabitler[kod].append(eleman)
                        if kod in maps and kisaltma:
                            maps[kod][eleman] = kisaltma

            rke_data     = registry.get("RKE_List").get_all()
            muayene_data = registry.get("RKE_Muayene").get_all()

            self.veri_hazir.emit(sabitler, maps, rke_data, muayene_data)
        except Exception as e:
            exc_logla("RKEYonetim.Worker", e)
            self.hata_olustu.emit(f"Veri yÃ¼kleme hatasÄ±: {e}")
        finally:
            if db:
                db.close()


class IslemKaydediciThread(QThread):
    """INSERT veya UPDATE iÅŸlemini arka planda yapar."""
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, mod, veri_dict):
        super().__init__()
        self._mod  = mod       # "INSERT" | "UPDATE"
        self._veri = veri_dict

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)
            repo     = registry.get("RKE_List")

            if self._mod == "INSERT":
                repo.insert(self._veri)
            elif self._mod == "UPDATE":
                repo.update(self._veri.get("KayitNo"), self._veri)

            self.islem_tamam.emit()
        except Exception as e:
            exc_logla("RKEYonetim.Worker", e)
            self.hata_olustu.emit(f"Ä°ÅŸlem hatasÄ±: {e}")
        finally:
            if db:
                db.close()


class GecmisYukleyiciThread(QThread):
    """SeÃ§ili ekipmanÄ±n muayene geÃ§miÅŸini yÃ¼kler."""
    gecmis_hazir = Signal(list)

    def __init__(self, ekipman_no):
        super().__init__()
        self._ekipman_no = ekipman_no

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from core.di import get_registry
        db = None
        try:
            db       = SQLiteManager()
            registry = get_registry(db)
            all_data = registry.get("RKE_Muayene").get_all()
            gecmis   = [x for x in all_data if str(x.get("EkipmanNo")) == str(self._ekipman_no)]
            gecmis.sort(key=lambda x: x.get("FMuayeneTarihi", ""), reverse=True)
            self.gecmis_hazir.emit(gecmis)
        except Exception as e:
            logger.error(f"GeÃ§miÅŸ yÃ¼kleme hatasÄ±: {e}")
            self.gecmis_hazir.emit([])
        finally:
            if db:
                db.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ANA SAYFA
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class RKEYonetimPage(QWidget):
    """
    RKE Envanter YÃ¶netimi sayfasÄ±.
    db: SQLiteManager instance
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db          = db
        self._sabitler    = {}
        self._kisaltma    = {}
        self._rke_listesi = []
        self._muayene     = []
        self._secili      = None   # dict | None
        self.ui           = {}
        self._combo_db    = {}     # ui_key â†’ sabit_kod

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  UI
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # â”€â”€ SOL: FORM â”€â”€
        form_container = QWidget()
        form_lay = QVBoxLayout(form_container)
        form_lay.setContentsMargins(0, 0, 0, 0)
        form_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 8, 0)
        inner.setSpacing(12)

        # Gizli alanlar
        self.ui["KayitNo"] = QLineEdit()
        self.ui["KayitNo"].setVisible(False)

        # 1. Kimlik
        grp_kimlik = QGroupBox("ğŸ”–  Kimlik Bilgileri")
        grp_kimlik.setStyleSheet(S.get("group", ""))
        v_kimlik = QVBoxLayout(grp_kimlik)
        v_kimlik.setSpacing(10)

        row1 = QHBoxLayout()
        self.ui["EkipmanNo"]        = self._make_input("Ekipman No (Otomatik)", row1, read_only=True)
        self.ui["KoruyucuNumarasi"] = self._make_input("Koruyucu No (Tam Kod)", row1, read_only=True)
        v_kimlik.addLayout(row1)

        row2 = QHBoxLayout()
        self.ui["Barkod"]              = self._make_input("Barkod", row2)
        self.ui["Varsa_DemirbaÅŸ_No"]   = self._make_input("DemirbaÅŸ No", row2)
        v_kimlik.addLayout(row2)

        inner.addWidget(grp_kimlik)

        # 2. Ã–zellikler
        grp_ozel = QGroupBox("âš™ï¸  Ekipman Ã–zellikleri")
        grp_ozel.setStyleSheet(S.get("group", ""))
        v_ozel = QVBoxLayout(grp_ozel)
        v_ozel.setSpacing(10)

        self.ui["AnaBilimDali"] = self._make_combo("Ana Bilim DalÄ± *", v_ozel, required=True)
        self._combo_db["AnaBilimDali"] = "AnaBilimDali"

        row3 = QHBoxLayout()
        self.ui["Birim"]         = self._make_combo("Birim", row3)
        self.ui["KoruyucuCinsi"] = self._make_combo("Koruyucu Cinsi", row3)
        self._combo_db["Birim"]         = "Birim"
        self._combo_db["KoruyucuCinsi"] = "Koruyucu_Cinsi"
        v_ozel.addLayout(row3)

        row4 = QHBoxLayout()
        self.ui["Bedeni"]         = self._make_combo("Beden", row4)
        self.ui["KursunEsdegeri"] = self._make_combo("KurÅŸun EÅŸdeÄŸeri", row4, editable=True)
        self._combo_db["Bedeni"] = "Bedeni"
        v_ozel.addLayout(row4)

        # KurÅŸun sabit seÃ§enekler
        for val in ["0.25 mmPb", "0.35 mmPb", "0.50 mmPb", "1.0 mmPb"]:
            self.ui["KursunEsdegeri"].addItem(val)

        row5 = QHBoxLayout()
        self.ui["HizmetYili"]  = self._make_input("Ãœretim YÄ±lÄ±", row5)
        self.ui["KayitTarih"]  = self._make_date("Envanter GiriÅŸ", row5)
        v_ozel.addLayout(row5)

        self.ui["HizmetYili"].setValidator(QIntValidator(1900, 2100))
        self.ui["HizmetYili"].setPlaceholderText("Ã–rn: 2024")

        lbl_acik = QLabel("AÃ§Ä±klama:")
        lbl_acik.setStyleSheet(S.get("label", ""))
        self.ui["AÃ§iklama"] = QTextEdit()
        self.ui["AÃ§iklama"].setMaximumHeight(60)
        self.ui["AÃ§iklama"].setStyleSheet(S.get("input", ""))
        v_ozel.addWidget(lbl_acik)
        v_ozel.addWidget(self.ui["AÃ§iklama"])

        inner.addWidget(grp_ozel)

        # 3. Durum
        grp_durum = QGroupBox("ğŸŸ¢  Durum Bilgileri")
        grp_durum.setStyleSheet(S.get("group", ""))
        v_durum = QVBoxLayout(grp_durum)
        v_durum.setSpacing(10)

        row6 = QHBoxLayout()
        self.ui["Durum"] = self._make_combo("Durum", row6)
        for d in ["KullanÄ±ma Uygun", "KullanÄ±ma Uygun DeÄŸil", "Hurda", "Tamirde", "KayÄ±p"]:
            self.ui["Durum"].addItem(d)
        self.ui["KontrolTarihi"] = self._make_date("Son Kontrol Tarihi", row6)
        v_durum.addLayout(row6)

        inner.addWidget(grp_durum)

        # 4. Muayene GeÃ§miÅŸi
        grp_gecmis = QGroupBox("ğŸ“‹  Muayene GeÃ§miÅŸi")
        grp_gecmis.setStyleSheet(S.get("group", ""))
        v_gecmis = QVBoxLayout(grp_gecmis)

        self._gecmis_model = _GecmisTableModel()
        self._gecmis_view  = QTableView()
        self._gecmis_view.setModel(self._gecmis_model)
        self._gecmis_view.setStyleSheet(S.get("table", ""))
        self._gecmis_view.verticalHeader().setVisible(False)
        self._gecmis_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._gecmis_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._gecmis_view.setFixedHeight(140)
        hdr = self._gecmis_view.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        v_gecmis.addWidget(self._gecmis_view)

        inner.addWidget(grp_gecmis)
        inner.addStretch()

        scroll.setWidget(content)
        form_lay.addWidget(scroll, 1)

        # Progress
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        form_lay.addWidget(self._pbar)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(8)

        self.btn_temizle = QPushButton("âœ•  TEMÄ°ZLE / YENÄ°")
        self.btn_temizle.setStyleSheet(S.get("cancel_btn", ""))
        self.btn_temizle.setFixedHeight(40)
        self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))

        self.btn_kaydet = QPushButton("âœ“  KAYDET")
        self.btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self.btn_kaydet.setFixedHeight(40)
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))

        h_btn.addWidget(self.btn_temizle)
        h_btn.addWidget(self.btn_kaydet)
        form_lay.addLayout(h_btn)

        root.addWidget(form_container, 30)

        # Dikey ayraÃ§
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        root.addWidget(sep)

        # â”€â”€ SAÄ: LÄ°STE â”€â”€
        list_container = QWidget()
        list_lay = QVBoxLayout(list_container)
        list_lay.setContentsMargins(0, 0, 0, 0)
        list_lay.setSpacing(8)

        # Filtre Paneli
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S.get("filter_panel", ""))
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)

        self._cmb_filter_abd = QComboBox()
        self._cmb_filter_abd.addItem("TÃ¼m BÃ¶lÃ¼mler")
        self._cmb_filter_abd.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_abd)

        self._cmb_filter_birim = QComboBox()
        self._cmb_filter_birim.addItem("TÃ¼m Birimler")
        self._cmb_filter_birim.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_birim)

        self._cmb_filter_cins = QComboBox()
        self._cmb_filter_cins.addItem("TÃ¼m Cinsler")
        self._cmb_filter_cins.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_cins)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("ğŸ” Ara...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        self._txt_ara.setFixedWidth(180)
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_yenile = QPushButton("âŸ³ Yenile")
        self._btn_yenile.setToolTip("Listeyi Yenile")
        self._btn_yenile.setFixedSize(100, 36)
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        fl.addWidget(self._btn_yenile)

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(20)
        _sep_k.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        fl.addWidget(_sep_k)

        self.btn_kapat = QPushButton("âœ• Kapat")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setFixedSize(100, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        fl.addWidget(self.btn_kapat)

        list_lay.addWidget(filter_frame)

        # Tablo
        self._model = RKETableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setStyleSheet(S.get("table", ""))
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)

        hdr2 = self._table.horizontalHeader()
        hdr2.setSectionResizeMode(QHeaderView.Stretch)
        # KayitNo sÃ¼tununu gizle
        self._table.setColumnHidden(0, True)
        # Durum sÃ¼tunu iÃ§eriÄŸe gÃ¶re
        hdr2.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeToContents)

        list_lay.addWidget(self._table, 1)

        # Footer
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayÄ±t")
        self._lbl_sayi.setStyleSheet(S.get("footer_label", "color:#8b8fa3; font-size:11px;"))
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()
        list_lay.addLayout(footer)

        root.addWidget(list_container, 70)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  YARDIMCI WIDGET FABRÄ°KALARI
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _make_input(self, label, parent_layout, read_only=False, placeholder=""):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        inp = QLineEdit()
        if read_only:
            inp.setReadOnly(True)
            inp.setStyleSheet("background-color: #2b2b2b; color: #aaa; border: 1px solid #3a3a3a; border-radius: 5px; padding: 5px;")
        else:
            inp.setStyleSheet(S.get("input", ""))
        if placeholder:
            inp.setPlaceholderText(placeholder)
        lay.addWidget(inp)
        parent_layout.addWidget(container, 1)
        return inp

    def _make_combo(self, label, parent_layout, required=False, editable=False):
        if isinstance(parent_layout, QVBoxLayout):
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(S.get("required_label" if required else "label", ""))
            lay.addWidget(lbl)
            cmb = QComboBox()
            cmb.setStyleSheet(S.get("combo", ""))
            cmb.setEditable(editable)
            lay.addWidget(cmb)
            parent_layout.addWidget(container)
        else:
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(S.get("required_label" if required else "label", ""))
            lay.addWidget(lbl)
            cmb = QComboBox()
            cmb.setStyleSheet(S.get("combo", ""))
            cmb.setEditable(editable)
            lay.addWidget(cmb)
            parent_layout.addWidget(container, 1)
        return cmb

    def _make_date(self, label, parent_layout):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        de = QDateEdit()
        de.setStyleSheet(S.get("date", ""))
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setDisplayFormat("yyyy-MM-dd")

        ThemeManager.setup_calendar_popup(de)

        lay.addWidget(de)
        parent_layout.addWidget(container, 1)
        return de

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  SÄ°NYALLER
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _connect_signals(self):
        self.btn_kaydet.clicked.connect(self._on_save)
        self.btn_temizle.clicked.connect(self._on_clear)
        self._btn_yenile.clicked.connect(self.load_data)
        self._txt_ara.textChanged.connect(self._proxy.setFilterFixedString)
        self._cmb_filter_abd.currentTextChanged.connect(self._apply_filter)
        self._cmb_filter_birim.currentTextChanged.connect(self._apply_filter)
        self._cmb_filter_cins.currentTextChanged.connect(self._apply_filter)
        self._table.doubleClicked.connect(self._on_row_double_click)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        # Otomatik kod hesaplama
        self.ui["AnaBilimDali"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["Birim"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["KoruyucuCinsi"].currentIndexChanged.connect(self._hesapla_kod)
        self.ui["KayitTarih"].dateChanged.connect(self._tarih_hesapla)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  VERÄ°
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def load_data(self):
        # Ã–nceki thread hÃ¢lÃ¢ Ã§alÄ±ÅŸÄ±yorsa yeni baÅŸlatma
        if hasattr(self, "_loader") and self._loader.isRunning():
            return
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self._loader = VeriYukleyiciThread()
        self._loader.veri_hazir.connect(self._on_data_ready)
        self._loader.hata_olustu.connect(self._on_error)
        self._loader.finished.connect(lambda: self._pbar.setVisible(False))
        self._loader.start()

    def _on_data_ready(self, sabitler, maps, rke_data, muayene_data):
        self._sabitler    = sabitler
        self._kisaltma    = maps
        self._rke_listesi = rke_data
        self._muayene     = muayene_data

        # Form combolarÄ±nÄ± doldur
        for ui_key, db_kod in self._combo_db.items():
            w = self.ui.get(ui_key)
            if w and db_kod in self._sabitler:
                w.blockSignals(True)
                curr = w.currentText()
                w.clear()
                w.addItem("")
                w.addItems(sorted(self._sabitler[db_kod]))
                idx = w.findText(curr)
                w.setCurrentIndex(idx if idx >= 0 else 0)
                w.blockSignals(False)

        # Filtre combolarÄ±nÄ± doldur
        def fill_filter(widget, items, default_text):
            widget.blockSignals(True)
            curr = widget.currentText()
            widget.clear()
            widget.addItem(default_text)
            widget.addItems(sorted(items))
            idx = widget.findText(curr)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            widget.blockSignals(False)

        abd_set   = set(str(r.get("AnaBilimDali", "")).strip() for r in rke_data if r.get("AnaBilimDali"))
        birim_set = set(str(r.get("Birim", "")).strip() for r in rke_data if r.get("Birim"))
        cins_set  = set(str(r.get("KoruyucuCinsi", "")).strip() for r in rke_data if r.get("KoruyucuCinsi"))

        fill_filter(self._cmb_filter_abd,   abd_set,   "TÃ¼m BÃ¶lÃ¼mler")
        fill_filter(self._cmb_filter_birim, birim_set, "TÃ¼m Birimler")
        fill_filter(self._cmb_filter_cins,  cins_set,  "TÃ¼m Cinsler")

        self._apply_filter()

    def _apply_filter(self):
        f_abd   = self._cmb_filter_abd.currentText()
        f_birim = self._cmb_filter_birim.currentText()
        f_cins  = self._cmb_filter_cins.currentText()

        filtered = []
        for r in self._rke_listesi:
            if f_abd   != "TÃ¼m BÃ¶lÃ¼mler" and str(r.get("AnaBilimDali",   "")).strip() != f_abd:   continue
            if f_birim != "TÃ¼m Birimler" and str(r.get("Birim",           "")).strip() != f_birim: continue
            if f_cins  != "TÃ¼m Cinsler"  and str(r.get("KoruyucuCinsi",  "")).strip() != f_cins:  continue
            filtered.append(r)

        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayÄ±t")

    def _on_row_double_click(self, index):
        src_idx  = self._proxy.mapToSource(index)
        row_data = self._model.get_row(src_idx.row())
        if not row_data:
            return
        self._secili = row_data
        self._fill_form(row_data)
        self._gecmis_yukle(row_data.get("EkipmanNo", ""))
        self.btn_kaydet.setText("âœ“  GÃœNCELLE")
        self.btn_kaydet.setStyleSheet(
            "background-color: #e65100; color: white; font-weight: bold; "
            "border-radius: 6px; padding: 6px 16px; font-size: 13px;"
        )

    def _show_context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        menu.setStyleSheet(S.get("context_menu", ""))
        act_sec = menu.addAction("âœï¸  DÃ¼zenle")
        act_sec.triggered.connect(lambda: self._on_row_double_click(idx))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _fill_form(self, data: dict):
        """Mevcut veriyi forma doldurur."""
        for key, w in self.ui.items():
            val = str(data.get(key, ""))
            if isinstance(w, QLineEdit):
                w.setText(val)
            elif isinstance(w, QComboBox):
                i = w.findText(val)
                if i >= 0:
                    w.setCurrentIndex(i)
                elif w.isEditable():
                    w.setEditText(val)
            elif isinstance(w, QDateEdit) and val:
                d = QDate.fromString(val, "yyyy-MM-dd")
                if d.isValid():
                    w.setDate(d)
            elif isinstance(w, QTextEdit):
                w.setPlainText(val)

    def _gecmis_yukle(self, ekipman_no):
        if not ekipman_no:
            return
        # Ã–nceki geÃ§miÅŸ thread'i hÃ¢lÃ¢ Ã§alÄ±ÅŸÄ±yorsa bekle
        if hasattr(self, "_gecmis_loader") and self._gecmis_loader.isRunning():
            return
        self._gecmis_loader = GecmisYukleyiciThread(ekipman_no)
        self._gecmis_loader.gecmis_hazir.connect(self._gecmis_goster)
        self._gecmis_loader.start()

    def _gecmis_goster(self, data):
        self._gecmis_model.set_data(data)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  KAYDET / TEMÄ°ZLE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _on_save(self):
        if not self.ui["EkipmanNo"].text().strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Ekipman No zorunludur (Ana Bilim DalÄ± ve Cinsi seÃ§in).")
            return

        veri = {}
        for key, w in self.ui.items():
            if isinstance(w, QLineEdit):
                veri[key] = w.text().strip()
            elif isinstance(w, QComboBox):
                veri[key] = w.currentText().strip()
            elif isinstance(w, QDateEdit):
                veri[key] = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, QTextEdit):
                veri[key] = w.toPlainText().strip()

        mod = "UPDATE" if self._secili else "INSERT"
        if mod == "UPDATE":
            veri["KayitNo"] = self._secili.get("KayitNo")

        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self.btn_kaydet.setEnabled(False)

        self._saver = IslemKaydediciThread(mod, veri)
        self._saver.islem_tamam.connect(self._on_save_success)
        self._saver.hata_olustu.connect(self._on_error)
        self._saver.start()

    def _on_save_success(self):
        self._pbar.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        QMessageBox.information(self, "BaÅŸarÄ±lÄ±", "Ä°ÅŸlem tamamlandÄ±.")
        self._on_clear()
        self.load_data()

    def _on_clear(self):
        self._secili = None
        for w in self.ui.values():
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
            elif isinstance(w, QDateEdit):
                w.setDate(QDate.currentDate())
            elif isinstance(w, QTextEdit):
                w.clear()

        self.ui["HizmetYili"].setText(str(QDate.currentDate().year()))
        self.ui["Durum"].setCurrentText("KullanÄ±ma Uygun")
        self._gecmis_model.set_data([])

        self.btn_kaydet.setText("âœ“  KAYDET")
        self.btn_kaydet.setStyleSheet(S.get("save_btn", ""))

    def _hesapla_kod(self):
        """Ana Bilim DalÄ± / Birim / Cins deÄŸiÅŸtiÄŸinde EkipmanNo ve KoruyucuNo hesaplar."""
        abd  = self.ui["AnaBilimDali"].currentText()
        birim = self.ui["Birim"].currentText()
        cins  = self.ui["KoruyucuCinsi"].currentText()

        def kisaltma(grup, deger):
            if not deger:
                return "UNK"
            m = self._kisaltma.get(grup, {})
            return m.get(deger, deger[:3].upper())

        k_abd  = kisaltma("AnaBilimDali",    abd)
        k_bir  = kisaltma("Birim",           birim)
        k_cins = kisaltma("Koruyucu_Cinsi",  cins)

        sayac_genel = sum(1 for k in self._rke_listesi if str(k.get("KoruyucuCinsi", "")).strip() == cins)
        sayac_yerel = sum(
            1 for k in self._rke_listesi
            if str(k.get("KoruyucuCinsi", "")).strip() == cins
            and str(k.get("AnaBilimDali", "")).strip() == abd
            and str(k.get("Birim", "")).strip() == birim
        )

        if not self._secili:
            self.ui["EkipmanNo"].setText(f"RKE-{k_cins}-{str(sayac_genel + 1).zfill(3)}")

        if abd and birim and cins:
            self.ui["KoruyucuNumarasi"].setText(
                f"{k_abd}-{k_bir}-{k_cins}-{str(sayac_yerel + 1).zfill(3)}"
            )

    def _tarih_hesapla(self):
        if not self._secili:
            giris = self.ui["KayitTarih"].date()
            self.ui["KontrolTarihi"].setDate(giris.addYears(1))

    def _on_error(self, msg):
        self._pbar.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        logger.error(f"RKEYonetim hatasÄ±: {msg}")
        QMessageBox.critical(self, "Hata", msg)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  GEÃ‡MIÅ TABLO MODELÄ° (KÃ¼Ã§Ã¼k yardÄ±mcÄ±)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_GECMIS_COLS = [
    ("FMuayeneTarihi",  "Fiz. Tarih"),
    ("FizikselDurum",   "Fiziksel SonuÃ§"),
    ("Aciklamalar",     "AÃ§Ä±klama"),
]

class _GecmisTableModel(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data    = []
        self._keys    = [c[0] for c in _GECMIS_COLS]
        self._headers = [c[1] for c in _GECMIS_COLS]

    def rowCount(self, parent=QModelIndex()):  return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(_GECMIS_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self._data[index.row()]
        col = self._keys[index.column()]
        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "FizikselDurum":
            return QColor("#f87171") if "DeÄŸil" in str(row.get(col, "")) else QColor("#4ade80")
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


