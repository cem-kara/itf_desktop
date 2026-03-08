# -*- coding: utf-8 -*-
import os
import uuid
import platform
import subprocess
from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import Qt, QDate, QUrl, QModelIndex, QEvent, QThread, Signal as _Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableView,
    QDateEdit, QMessageBox, QFileDialog, QSizePolicy,
    QStyledItemDelegate, QApplication,
)
# =============================================================================
# Delegate: Rapor Sütunu Buton
# =============================================================================
class RaporButtonDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            value = index.data()
            if value in ("Raporu Aç", "⚠ Rapor Eksik"):
                row = index.row()
                if self._parent:
                    self._parent.handle_rapor_button_clicked(row, value)
                return True
        return super().editorEvent(event, model, option, index)

from core.logger import logger
from core.date_utils import parse_date, to_db_date, to_ui_date
from core.services.dokuman_service import DokumanService
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer, IconColors

STATUS_OPTIONS = ["Uygun", "Şartlı Uygun", "Uygun Değil"]

TABLE_COLUMNS = [
    ("AdSoyad",              "Ad Soyad",         200),
    ("Birim",                "Birim",             200),
    ("MuayeneTarihi",        "Muayene",         150),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol", 150),
    ("Sonuc",                "Sonuç",           150),
    ("Durum",                "Durum",           100),
    ("Rapor",                "Rapor",            80),
]


# =============================================================================
# Model
# =============================================================================

class SaglikTakipTableModel(BaseTableModel):
    DATE_KEYS    = frozenset({"MuayeneTarihi", "SonrakiKontrolTarihi"})
    ALIGN_CENTER = frozenset({"MuayeneTarihi", "SonrakiKontrolTarihi", "Sonuc", "Durum", "Rapor"})

    def __init__(self, rows=None, parent=None):
        super().__init__(TABLE_COLUMNS, rows, parent)

    def _display(self, key, row):
        if key == "Rapor":
            rapor_path = row.get("_RaporPath")
            if rapor_path and str(rapor_path).strip():
                return "Raporu Aç"
            muayene = row.get("MuayeneTarihi")
            if muayene and str(muayene).strip():
                return "⚠ Rapor Eksik"
            return "-"
        return super()._display(key, row)

    def _fg(self, key, row):
        from PySide6.QtGui import QColor
        if key == "Rapor":
            muayene = row.get("MuayeneTarihi") if row else None
            if muayene and str(muayene).strip() and not row.get("_RaporPath"):
                return QColor("#f59e0b")   # turuncu — rapor eksik uyarısı
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        return None

    def _bg(self, key, row):
        if key == "Durum":
            return self.status_bg(row.get("Durum", ""))
        return None



# =============================================================================
# Worker: arka planda veri yükleme
# =============================================================================

class _SaglikLoader(QThread):
    finished = _Signal(dict)
    error    = _Signal(str)

    def __init__(self, db):
        super().__init__()
        self._db = db

    def run(self):
        try:
            from core.di import get_saglik_service as _svc_factory
            from core.paths import DATA_DIR
            _svc          = _svc_factory(self._db)
            personel_repo = _svc._r.get("Personel")
            takip_repo    = _svc._r.get("Personel_Saglik_Takip")
            dokuman_repo  = _svc._r.get("Dokumanlar")

            all_personel  = personel_repo.get_all()
            personel_rows = [
                p for p in all_personel
                if str(p.get("Durum", "")).strip().lower() != "pasif"
            ]
            takip_rows = takip_repo.get_all()

            rapor_map: dict = {}
            docs = dokuman_repo.get_where({"EntityType": "personel"})
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                    continue
                entity_id = str(doc.get("EntityId", "")).strip()
                rel_id    = str(doc.get("IliskiliBelgeID", "")).strip()
                if entity_id and rel_id:
                    rapor_map[(entity_id, rel_id)] = doc

            for takip in takip_rows:
                personelid = str(takip.get("Personelid", "")).strip()
                kayit_no   = str(takip.get("KayitNo",    "")).strip()
                doc        = rapor_map.get((personelid, kayit_no))

                rapor_path = ""
                if doc:
                    local_path = str(doc.get("LocalPath", "")).strip()
                    drive_path = str(doc.get("DrivePath", "")).strip()
                    belge_adi  = str(doc.get("Belge",     "")).strip()
                    tc_no      = str(doc.get("EntityId",  "")).strip() or personelid

                    if local_path and os.path.isfile(local_path):
                        rapor_path = local_path
                    elif drive_path:
                        rapor_path = drive_path
                    else:
                        rapor_path = local_path

                    canonical_path = ""
                    if belge_adi and tc_no:
                        canonical_path = os.path.join(
                            DATA_DIR, "offline_uploads", "personel", tc_no, belge_adi
                        )
                    if canonical_path and os.path.isfile(canonical_path):
                        rapor_path = canonical_path
                    elif local_path and os.path.isdir(local_path) and belge_adi:
                        joined = os.path.join(local_path, belge_adi)
                        if os.path.isfile(joined):
                            rapor_path = joined

                if not rapor_path:
                    rapor_dosya = str(takip.get("RaporDosya", "")).strip()
                    if rapor_dosya:
                        if not os.path.isabs(rapor_dosya) and not rapor_dosya.startswith(
                            ("http://", "https://")
                        ):
                            basename  = os.path.basename(rapor_dosya)
                            canonical = os.path.join(
                                DATA_DIR, "offline_uploads", "personel", personelid, basename
                            )
                            rapor_path = canonical if os.path.isfile(canonical) else rapor_dosya
                        else:
                            rapor_path = rapor_dosya

                takip["_RaporPath"] = rapor_path

            self.finished.emit({
                "all_personel":  all_personel,
                "personel_rows": personel_rows,
                "takip_rows":    takip_rows,
            })
        except Exception as exc:
            self.error.emit(str(exc))



class _SaglikSaver(QThread):
    """Kaydetme işlemini arka planda yapar."""
    finished = _Signal(str)   # "ok" veya "rapor_ok"
    error    = _Signal(str)

    def __init__(self, db, mode: str, payload: dict):
        super().__init__()
        self._db      = db
        self._mode    = mode     # "full" veya "rapor"
        self._payload = payload

    def run(self):
        try:
            from core.di import get_saglik_service as _svc_factory
            _svc       = _svc_factory(self._db)
            takip_repo = _svc._r.get("Personel_Saglik_Takip")

            if self._mode == "rapor":
                takip_repo.update(self._payload["KayitNo"], {"RaporDosya": self._payload["RaporDosya"]})
                self.finished.emit("rapor_ok")
                return

            # full kayıt
            personel_repo = _svc._r.get("Personel")
            mevcut = takip_repo.get_by_id(self._payload["KayitNo"])
            if mevcut:
                takip_repo.update(self._payload["KayitNo"], self._payload)
            else:
                takip_repo.insert(self._payload)

            muayene_db = self._payload.get("MuayeneTarihi", "")
            if muayene_db:
                from core.date_utils import parse_date as _pd
                mevcut_p = personel_repo.get_by_id(self._payload["Personelid"]) or {}
                mevcut_t = _pd(mevcut_p.get("MuayeneTarihi"))
                yeni_t   = _pd(muayene_db)
                if yeni_t and (not mevcut_t or yeni_t >= mevcut_t):
                    personel_repo.update(self._payload["Personelid"], {
                        "MuayeneTarihi": muayene_db,
                        "Sonuc":         self._payload.get("Sonuc", ""),
                    })
            self.finished.emit("ok")
        except Exception as exc:
            self.error.emit(str(exc))

# =============================================================================
# Sayfa
# =============================================================================

class SaglikTakipPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db   = db
        self._all_rows:      list[dict] = []
        self._takip_rows:    list[dict] = []
        self._personel_rows: list[dict] = []
        self._editing_id:    Optional[str] = None
        self._rapor_only_mode: bool = False
        self._selected_report_path = ""
        self._exam_keys    = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
        self._exam_widgets: dict = {}
        self._setup_ui()
        self._connect_signals()

    # -------------------------------------------------------------------------
    # UI Kurulum
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 10, 10, 10)
        main_lay.setSpacing(8)

        # 1. Filtre çubuğu
        main_lay.addWidget(self._build_filter_bar())

        # 2. Form paneli — filtre ile tablo arasında, gizli başlar
        self.form_panel = self._build_form_panel()
        self.form_panel.setVisible(False)
        main_lay.addWidget(self.form_panel)

        # 3. Tablo
        self._build_table_widget()
        main_lay.addWidget(self.table, 1)

        # 4. Durum satırı
        self.lbl_info = QLabel("")
        self.lbl_info.setProperty("style-role", "footer")
        main_lay.addWidget(self.lbl_info)

    # -- Filtre çubu\u011fu -------------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        frame = QFrame()
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        self.cmb_yil = QComboBox()
        self.cmb_yil.addItem("Tum Yillar", 0)
        this_year = date.today().year
        for y in range(this_year + 1, this_year - 4, -1):
            self.cmb_yil.addItem(str(y), y)
        self.cmb_yil.setCurrentIndex(1)
        lay.addWidget(self.cmb_yil)

        self.cmb_birim_filter = QComboBox()
        self.cmb_birim_filter.addItem("Tum Birimler")
        lay.addWidget(self.cmb_birim_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.addItems(
            ["Tum Durumlar", "Planlandi", "Gecerli", "Gecikmis", "Riskli"]
        )
        lay.addWidget(self.cmb_durum_filter)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ad soyad ara...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        lay.addWidget(self.search)

        lay.addStretch()



        self.btn_yeni = QPushButton("Yeni Ekle")
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.setFixedSize(110, 36)
        self.btn_yeni.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_yeni)

        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setFixedSize(100, 36)
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "sync", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_yenile)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setProperty("style-role", "danger")
        self.btn_kapat.setFixedSize(100, 36)
        self.btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=IconColors.DANGER, size=14)
        lay.addWidget(self.btn_kapat)

        return frame

    # -- Form paneli ----------------------------------------------------------

    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        form_lay = QVBoxLayout(panel)
        form_lay.setContentsMargins(12, 10, 12, 10)
        form_lay.setSpacing(10)

        # Üst: başlık + personel combo/label + kapat
        top_row = QHBoxLayout()

        self.lbl_form_title = QLabel("Yeni Kayıt")
        self.lbl_form_title.setProperty("style-role", "section-title")
        top_row.addWidget(self.lbl_form_title)

        self.cmb_personel = QComboBox()
        self.cmb_personel.setMinimumWidth(200)
        top_row.addWidget(self.cmb_personel, 1)

        # Salt-okunur personel etiketi (rapor-only modda görünür)
        self.lbl_personel_ro = QLabel("")
        self.lbl_personel_ro.setProperty("style-role", "section-title")
        self.lbl_personel_ro.setVisible(False)
        top_row.addWidget(self.lbl_personel_ro, 1)

        self.btn_form_kapat = QPushButton()
        self.btn_form_kapat.setProperty("style-role", "danger")
        self.btn_form_kapat.setFixedSize(28, 28)
        self.btn_form_kapat.setToolTip("Kapat")
        self.btn_form_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_form_kapat, "x", color=IconColors.DANGER, size=12)
        top_row.addWidget(self.btn_form_kapat)
        form_lay.addLayout(top_row)

        # 4 muayene kutusu — gizlenebilir bölüm
        self.exam_section = QWidget()
        exam_lay = QVBoxLayout(self.exam_section)
        exam_lay.setContentsMargins(0, 0, 0, 0)
        exam_lay.setSpacing(0)
        exam_row = QHBoxLayout()
        exam_row.setSpacing(12)
        exam_labels = {
            "Dermatoloji": "Dermatoloji",
            "Dahiliye":    "Dahiliye",
            "Goz":         "Göz",
            "Goruntuleme": "Görüntüleme",
        }
        for key in self._exam_keys:
            exam_row.addWidget(self._create_exam_box(key, exam_labels[key]))
        exam_lay.addLayout(exam_row)
        form_lay.addWidget(self.exam_section)

        # Rapor dosyası satırı
        rapor_row = QHBoxLayout()
        rapor_row.setSpacing(8)

        self.btn_rapor = QPushButton("Rapor Seç")
        self.btn_rapor.setProperty("style-role", "secondary")
        self.btn_rapor.setFixedWidth(100)
        self.btn_rapor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_rapor, "upload", color=IconColors.PRIMARY, size=13)
        rapor_row.addWidget(self.btn_rapor)

        self.inp_rapor = QLineEdit()
        self.inp_rapor.setReadOnly(True)
        self.inp_rapor.setPlaceholderText("Dosya seçilmedi...")
        rapor_row.addWidget(self.inp_rapor, 1)
        form_lay.addLayout(rapor_row)

        # Notlar satırı
        not_row = QHBoxLayout()
        lbl_not = QLabel("Notlar")
        lbl_not.setProperty("style-role", "form")
        not_row.addWidget(lbl_not)
        self.inp_not = QLineEdit()
        self.inp_not.setPlaceholderText("Açıklama veya not...")
        not_row.addWidget(self.inp_not, 1)
        form_lay.addLayout(not_row)

        # Kaydet / İptal
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=IconColors.PRIMARY, size=14)
        btn_row.addWidget(self.btn_kaydet)

        self.btn_temizle = QPushButton("İptal")
        self.btn_temizle.setProperty("style-role", "secondary")
        self.btn_temizle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_temizle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        IconRenderer.set_button_icon(self.btn_temizle, "x", color=IconColors.MUTED, size=14)
        btn_row.addWidget(self.btn_temizle)
        form_lay.addLayout(btn_row)

        return panel

    def _create_exam_box(self, key: str, label: str) -> QFrame:
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        vlay = QVBoxLayout(box)
        vlay.setContentsMargins(10, 8, 10, 10)
        vlay.setSpacing(4)

        title = QLabel(label)
        title.setProperty("style-role", "section-title")
        vlay.addWidget(title)

        lbl_tarih = QLabel("Muayene Tarihi")
        lbl_tarih.setProperty("style-role", "form")
        vlay.addWidget(lbl_tarih)

        de = QDateEdit(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        de.setCalendarPopup(True)
        vlay.addWidget(de)

        lbl_durum = QLabel("Durum")
        lbl_durum.setProperty("style-role", "form")
        vlay.addWidget(lbl_durum)

        cmb = QComboBox()
        cmb.addItems([""] + STATUS_OPTIONS)
        vlay.addWidget(cmb)

        self._exam_widgets[key] = {"tarih": de, "durum": cmb}
        return box

    # -- Tablo ----------------------------------------------------------------

    def _build_table_widget(self):
        self.table = QTableView()
        self.model = SaglikTakipTableModel([])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.model.setup_columns(self.table)
        # Seçili satırda metin her zaman beyaz — model rengini ezmez
        self.table.setStyleSheet(
            "QTableView::item:selected { color: #ffffff; }"
        )

        # Rapor sütununa buton delegate ata
        rapor_col = [i for i, (k, _, _) in enumerate(TABLE_COLUMNS) if k == "Rapor"]
        if rapor_col:
            self.table.setItemDelegateForColumn(rapor_col[0], RaporButtonDelegate(self))
    def handle_rapor_button_clicked(self, row_idx: int, value: str):
        row = self.model.get_row(row_idx)
        if not row:
            return
        if value == "Raporu Aç":
            # Raporu aç fonksiyonu (mevcut)
            rapor_path = str(row.get("_RaporPath", "")).strip()
            if not rapor_path:
                QMessageBox.information(self, "Bilgi", "Bu kayıt için rapor dosyası bulunmuyor.")
                return
            try:
                if rapor_path.startswith(("http://", "https://")):
                    QDesktopServices.openUrl(QUrl(rapor_path))
                    logger.info(f"Saglik raporu acildi (online): {rapor_path}")
                    return
                from core.paths import DATA_DIR
                resolved_path = rapor_path
                if not os.path.isfile(resolved_path):
                    personelid = str(row.get("Personelid", "")).strip()
                    kayit_no   = str(row.get("KayitNo",    "")).strip()
                    file_name  = os.path.basename(rapor_path)
                    candidates = []
                    if file_name and personelid:
                        candidates.append(
                            os.path.join(DATA_DIR, "offline_uploads", "personel", personelid, file_name)
                        )
                    if rapor_path and not os.path.isabs(rapor_path):
                        candidates.append(os.path.join(DATA_DIR, rapor_path))
                    for candidate in candidates:
                        if candidate and os.path.isfile(candidate):
                            resolved_path = candidate
                            break
                if not os.path.isfile(resolved_path):
                    QMessageBox.warning(
                        self, "Dosya Bulunamadı",
                        f"Rapor dosyası bulunamadı:\n\n{rapor_path}\n\nDosya silinmiş veya yol değişmiş olabilir."
                    )
                    logger.warning(f"Saglik raporu dosyası bulunamadı: {rapor_path}")
                    return
                if platform.system() == "Windows":
                    os.startfile(str(resolved_path))
                elif platform.system() == "Darwin":
                    subprocess.run(["open", str(resolved_path)])
                else:
                    subprocess.run(["xdg-open", str(resolved_path)])
                logger.info(f"Saglik raporu acildi (local): {resolved_path}")
            except Exception as e:
                logger.error(f"Saglik raporu acma hatasi: {e}")
                QMessageBox.critical(self, "Hata", f"Rapor açılamadı:\n\n{str(e)}\n\nYol: {rapor_path}")
        elif value == "⚠ Rapor Eksik":
            kayit_no = str(row.get("KayitNo", "")).strip()
            takip_row = next(
                (t for t in self._takip_rows if str(t.get("KayitNo", "")).strip() == kayit_no),
                None,
            )
            if takip_row:
                self._show_rapor_panel(takip_row)

    # -------------------------------------------------------------------------
    # Sinyal ba\u011flantıları
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_kaydet.clicked.connect(self._save_record)
        self.btn_temizle.clicked.connect(self._clear_form)
        self.btn_yeni.clicked.connect(self._show_form_panel)
        self.btn_form_kapat.clicked.connect(self._hide_form_panel)
        self.btn_rapor.clicked.connect(self._pick_report)
        self.search.textChanged.connect(self._apply_filters)
        self.cmb_yil.currentIndexChanged.connect(self._apply_filters)
        self.cmb_birim_filter.currentTextChanged.connect(self._apply_filters)
        self.cmb_durum_filter.currentTextChanged.connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._on_select_row)
        self.table.doubleClicked.connect(self._on_table_double_click)
        for key in self._exam_keys:
            self._exam_widgets[key]["durum"].currentTextChanged.connect(
                lambda _txt, k=key: self._on_exam_status_changed(k)
            )

    # -------------------------------------------------------------------------
    # Form panel g\öster / gizle
    # -------------------------------------------------------------------------

    def _show_form_panel(self):
        """Yeni kayıt — tüm alanlar boş, exam_section görünür."""
        self._editing_id = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        self.cmb_personel.setCurrentIndex(-1)
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        self.lbl_form_title.setText("Yeni Kayıt")
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self.inp_not.setVisible(True)
        self._rapor_only_mode = False
        self.form_panel.setVisible(True)

    def _fill_form_from_takip(self, takip_row: dict):
        """Form widget'larını verilen takip kaydıyla doldurur (panel göstermez)."""
        rapor_dosya = str(takip_row.get("RaporDosya", ""))
        self.inp_rapor.setText(os.path.basename(rapor_dosya) if rapor_dosya else "")
        self.inp_not.setText(str(takip_row.get("Notlar", "")))

        personelid = str(takip_row.get("Personelid", "")).strip()
        for i in range(self.cmb_personel.count()):
            info = self.cmb_personel.itemData(i)
            if info and str(info.get("KimlikNo", "")) == personelid:
                self.cmb_personel.setCurrentIndex(i)
                break

        mapping = [
            ("Dermatoloji", "DermatolojiMuayeneTarihi", "DermatolojiDurum"),
            ("Dahiliye",    "DahiliyeMuayeneTarihi",    "DahiliyeDurum"),
            ("Goz",         "GozMuayeneTarihi",         "GozDurum"),
            ("Goruntuleme", "GoruntulemeMuayeneTarihi",  "GoruntulemeDurum"),
        ]
        for key, col_t, col_d in mapping:
            w = self._exam_widgets[key]
            w["durum"].setCurrentText(str(takip_row.get(col_d, "")))
            d = parse_date(takip_row.get(col_t, ""))
            w["tarih"].setDate(QDate(d.year, d.month, d.day) if d else QDate.currentDate())

    def _show_edit_panel(self, takip_row: dict):
        """Mevcut kaydı düzenle — tüm alanlar dolu, exam_section görünür."""
        self._editing_id           = str(takip_row.get("KayitNo", ""))
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self._fill_form_from_takip(takip_row)
        self.lbl_form_title.setText("Kaydı Düzenle")
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self.inp_not.setVisible(True)
        self._rapor_only_mode = False
        self.form_panel.setVisible(True)

    def _show_rapor_panel(self, takip_row: dict):
        """Sadece rapor yükle — exam_section gizli, personel salt-okunur."""
        self._editing_id = str(takip_row.get("KayitNo", ""))
        self._selected_report_path = ""
        self.inp_rapor.clear()

        # Personel adını salt-okunur göster
        ad = str(takip_row.get("AdSoyad", "")).strip()
        pid = str(takip_row.get("Personelid", "")).strip()
        self.lbl_personel_ro.setText(f"{ad} ({pid})")
        self.cmb_personel.setVisible(False)
        self.lbl_personel_ro.setVisible(True)

        self.lbl_form_title.setText("Rapor Yükle")
        self.exam_section.setVisible(False)
        self.inp_not.setVisible(False)
        self._rapor_only_mode = True
        self.form_panel.setVisible(True)

    def _hide_form_panel(self):
        self.form_panel.setVisible(False)

    # -------------------------------------------------------------------------
    # Veri yükleme
    # -------------------------------------------------------------------------

    def load_data(self):
        if not self._db:
            return
        # Madde 1: önceki thread hâlâ çalışıyorsa yeni istek yok say
        if hasattr(self, "_loader") and self._loader and self._loader.isRunning():
            return
        self.btn_yenile.setEnabled(False)
        self.lbl_info.setText("Yükleniyor...")
        # Madde 4: yükleme sırasında form paneli etkileşime kapalı
        self.form_panel.setEnabled(False)
        self._loader = _SaglikLoader(self._db)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, result: dict):
        self.btn_yenile.setEnabled(True)
        self.form_panel.setEnabled(True)
        all_personel         = result["all_personel"]
        self._personel_rows  = result["personel_rows"]
        self._takip_rows     = result["takip_rows"]

        self.cmb_personel.clear()
        for p in sorted(self._personel_rows, key=lambda x: str(x.get("AdSoyad", ""))):
            kimlik = str(p.get("KimlikNo", "")).strip()
            ad     = str(p.get("AdSoyad",  "")).strip()
            birim  = str(p.get("GorevYeri","")).strip()
            self.cmb_personel.addItem(
                f"{ad} ({kimlik})",
                {"KimlikNo": kimlik, "AdSoyad": ad, "Birim": birim},
            )

        self._all_rows = self._build_takip_list_rows(self._takip_rows, all_personel)
        self._fill_filter_combos()
        self._apply_filters()

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        self.form_panel.setEnabled(True)
        self.lbl_info.setText("Yükleme hatası")
        logger.error(f"Saglik takip yukleme hatasi: {msg}")

    def _build_takip_list_rows(self, takip_rows, all_personel) -> list[dict]:
        personel_map = {
            str(p.get("KimlikNo", "")).strip(): str(p.get("Durum", "")).strip().lower()
            for p in all_personel
        }
        rows = []
        for takip in takip_rows:
            personelid = str(takip.get("Personelid", "")).strip()
            if personel_map.get(personelid, "") == "pasif":
                continue
            rows.append({
                "KayitNo":              str(takip.get("KayitNo", "")).strip(),
                "Personelid":           personelid,
                "AdSoyad":              str(takip.get("AdSoyad", "")).strip(),
                "Birim":                str(takip.get("Birim", "")).strip(),
                "Yil":                  int(takip.get("Yil") or 0),
                "MuayeneTarihi":        to_db_date(takip.get("MuayeneTarihi", "")),
                "SonrakiKontrolTarihi": to_db_date(takip.get("SonrakiKontrolTarihi", "")),
                "Sonuc":                str(takip.get("Sonuc", "")).strip(),
                "Durum":                str(takip.get("Durum", "")).strip(),
                "_RaporPath":           str(takip.get("_RaporPath", "")).strip(),
            })
        return rows

    def _fill_filter_combos(self):
        curr     = self.cmb_birim_filter.currentText()
        birimler = sorted({
            str(r.get("Birim", "")).strip()
            for r in self._all_rows
            if str(r.get("Birim", "")).strip()
        })
        self.cmb_birim_filter.blockSignals(True)
        self.cmb_birim_filter.clear()
        self.cmb_birim_filter.addItem("Tum Birimler")
        self.cmb_birim_filter.addItems(birimler)
        idx = self.cmb_birim_filter.findText(curr)
        self.cmb_birim_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_birim_filter.blockSignals(False)

    def _apply_filters(self):
        query        = self.search.text().strip().lower()
        yil          = self.cmb_yil.currentData()
        birim_filter = self.cmb_birim_filter.currentText()
        durum_filter = self.cmb_durum_filter.currentText()
        out = []
        for row in self._all_rows:
            row_yil = int(row.get("Yil") or 0)
            if yil and row_yil != int(yil):
                continue
            if birim_filter != "Tum Birimler" and str(row.get("Birim", "")).strip() != birim_filter:
                continue
            if durum_filter != "Tum Durumlar" and str(row.get("Durum", "")).strip() != durum_filter:
                continue
            ad    = str(row.get("AdSoyad", "")).lower()
            birim = str(row.get("Birim", "")).lower()
            if query and query not in ad and query not in birim:
                continue
            out.append(row)
        out.sort(key=lambda r: (str(r.get("AdSoyad", "")), str(r.get("MuayeneTarihi", ""))))
        self.model.set_data(out)
        self.lbl_info.setText(f"{len(out)} kayit")

    # -------------------------------------------------------------------------
    # Muayene yardımcıları
    # -------------------------------------------------------------------------

    def _on_exam_status_changed(self, key):
        pass

    def _safe_date_from_widget(self, widget) -> str:
        if not widget:
            return ""
        return to_db_date(widget.date().toString("yyyy-MM-dd"))

    def _exam_date_if_set(self, key) -> str:
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return self._safe_date_from_widget(w["tarih"])

    def _compute_summary(self):
        exam_data = []
        for key in self._exam_keys:
            w     = self._exam_widgets[key]
            tarih = self._exam_date_if_set(key)
            durum = str(w["durum"].currentText()).strip()
            exam_data.append((key, tarih, durum))

        dates   = [t for _, t, _ in exam_data if parse_date(t)]
        latest  = max(dates) if dates else ""
        sonraki = ""
        if latest:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            try:
                sonraki = d.replace(year=d.year + 1).isoformat()
            except ValueError:
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        # Sadece Göz, Dermatoloji, Dahiliye Sonuc/Durum hesabını etkiler
        _KRITIK = {"Dermatoloji", "Dahiliye", "Goz"}
        kritik  = [d for k, _, d in exam_data if k in _KRITIK and d]
        tum     = [d for _, _, d in exam_data if d]

        if "Uygun Değil" in kritik:
            # Kritiklerden biri Uygun Değil → Sonuç = Uygun Değil, Durum = Riskli
            sonuc = "Uygun Değil"
            durum = "Riskli"
        elif "Şartlı Uygun" in kritik:
            # Kritiklerden biri Şartlı Uygun → Sonuç = Şartlı Uygun, Durum = Riskli
            sonuc = "Şartlı Uygun"
            durum = "Riskli"
        elif "Uygun" in tum:
            sonuc = "Uygun"
            sonraki_tarih = parse_date(sonraki)
            durum = "Gecikmis" if (sonraki_tarih and sonraki_tarih < date.today()) else "Gecerli"
        else:
            sonuc = ""
            durum = "Planlandi"

        return latest, sonraki, sonuc, durum


    # -------------------------------------------------------------------------
    # Rapor
    # -------------------------------------------------------------------------

    def _pick_report(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Rapor Sec", "", "Dosyalar (*.pdf *.jpg *.jpeg *.png)"
        )
        if path:
            self._selected_report_path = path
            self.inp_rapor.setText(os.path.basename(path))

    def _upload_report(self, tc_no, kayit_no) -> str:
        if not self._selected_report_path:
            return self.inp_rapor.text().strip()
        if not os.path.exists(self._selected_report_path):
            QMessageBox.warning(self, "Uyari", "Secilen rapor dosyasi bulunamadi.")
            return ""
        try:
            ext         = os.path.splitext(self._selected_report_path)[1]
            custom_name = f"{tc_no}_{kayit_no}_SaglikRapor{ext}"
            svc         = DokumanService(self._db)
            sonuc       = svc.upload_and_save(
                file_path    = self._selected_report_path,
                entity_type  = "personel",
                entity_id    = str(tc_no),
                belge_turu   = "Periyodik Sa\u011flık Muayene Raporu",
                folder_name  = "Saglik_Raporlari",
                doc_type     = "Personel_Belge",
                custom_name  = custom_name,
                iliskili_id  = str(kayit_no),
                iliskili_tip = "Personel_Saglik_Takip",
            )
            if not sonuc.get("ok"):
                err = str(sonuc.get("error", "Bilinmeyen yükleme hatası"))
                QMessageBox.warning(self, "Yukleme Hatasi", f"Rapor yüklenemedi:\n{err}")
                return ""
            rapor_ref = str(sonuc.get("drive_link") or sonuc.get("local_path") or "").strip()

            return rapor_ref
        except Exception as exc:
            logger.error(f"Saglik rapor yukleme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Rapor yuklenemedi:\n{exc}")
            return ""

    # -------------------------------------------------------------------------
    # Çift tıklama — düzenle
    # -------------------------------------------------------------------------

    def _on_table_double_click(self, index):
        """Rapor sütunu hariç çift tıklama → kaydı düzenle."""
        if not index.isValid():
            return
        # Rapor sütununu delegate zaten ele alıyor — buraya düşmez, yine de guard
        rapor_col = next(
            (i for i, (k, *_) in enumerate(TABLE_COLUMNS) if k == "Rapor"), -1
        )
        if index.column() == rapor_col:
            return
        row = self.model.get_row(index.row())
        if not row:
            return
        kayit_no  = str(row.get("KayitNo", "")).strip()
        takip_row = next(
            (t for t in self._takip_rows if str(t.get("KayitNo", "")).strip() == kayit_no),
            None,
        )
        if takip_row:
            self._show_edit_panel(takip_row)

    # -------------------------------------------------------------------------
    # Kaydet
    # -------------------------------------------------------------------------

    def _save_record(self):
        if self._rapor_only_mode:
            self._save_rapor_only()
        else:
            self._save_full_record()

    def _save_rapor_only(self):
        """Sadece RaporDosya alanını günceller — diğer alanlara dokunmaz."""
        if not self._editing_id:
            QMessageBox.warning(self, "Hata", "Güncellenecek kayıt bulunamadı.")
            return

        # Hangi personele ait olduğunu mevcut kayıttan al
        takip_row = next(
            (t for t in self._takip_rows
             if str(t.get("KayitNo", "")).strip() == self._editing_id),
            None,
        )
        if not takip_row:
            QMessageBox.warning(self, "Hata", "Kayıt bulunamadı.")
            return

        tc_no = str(takip_row.get("Personelid", "")).strip()
        rapor_link = self._upload_report(tc_no, self._editing_id)
        if self._selected_report_path and not rapor_link:
            return  # yükleme hatası zaten uyarıldı

        if not rapor_link:
            QMessageBox.warning(self, "Eksik", "Lütfen bir rapor dosyası seçin.")
            return

        self._start_save(
            mode="rapor",
            payload={"KayitNo": self._editing_id, "RaporDosya": rapor_link},
        )

    def _save_full_record(self):
        """Tüm muayene alanlarını kaydeder."""
        if self.cmb_personel.currentIndex() < 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lutfen personel seciniz.")
            return

        # Durum seçili ama tarih gelecekteyse uyar
        _ETIKETLER = {"Dermatoloji": "Dermatoloji", "Dahiliye": "Dahiliye",
                      "Goz": "Göz", "Goruntuleme": "Görüntüleme"}
        gelecek = [
            _ETIKETLER.get(key, key)
            for key in self._exam_keys
            if str(self._exam_widgets[key]["durum"].currentText()).strip()
            and (lambda t: t is not None and t > date.today())(
                parse_date(self._exam_widgets[key]["tarih"].date().toString("yyyy-MM-dd"))
            )
        ]
        if gelecek:
            mesaj = "Şu muayene(ler) için tarih bugünden ileri:\n\n" + ", ".join(gelecek) + "\n\nYine de kaydetmek istiyor musunuz?"
            cevap = QMessageBox.question(
                self, "Tarih Kontrolü", mesaj,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if cevap != QMessageBox.StandardButton.Yes:
                return

        personel_data                        = self.cmb_personel.currentData()
        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        kayit_no   = self._editing_id or uuid.uuid4().hex[:12].upper()
        rapor_link = self._upload_report(personel_data.get("KimlikNo", ""), kayit_no)
        if self._selected_report_path and not rapor_link:
            return

        payload = {
            "KayitNo":                  kayit_no,
            "Personelid":               personel_data.get("KimlikNo", ""),
            "AdSoyad":                  personel_data.get("AdSoyad", ""),
            "Birim":                    personel_data.get("Birim", ""),
            "Yil":                      int(self.cmb_yil.currentData() or date.today().year),
            "MuayeneTarihi":            muayene_db,
            "SonrakiKontrolTarihi":     sonraki_db,
            "Sonuc":                    sonuc,
            "Durum":                    durum,
            "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
            "DermatolojiDurum":         str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
            "DahiliyeMuayeneTarihi":    self._exam_date_if_set("Dahiliye"),
            "DahiliyeDurum":            str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
            "GozMuayeneTarihi":         self._exam_date_if_set("Goz"),
            "GozDurum":                 str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
            "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
            "GoruntulemeDurum":         str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
            "RaporDosya":               rapor_link,
            "Notlar":                   self.inp_not.text().strip(),
        }

        self._start_save(mode="full", payload=payload)

    def _start_save(self, mode: str, payload: dict):
        """Kaydetme worker'ını başlatır, UI'ı kilitler."""
        self.btn_kaydet.setEnabled(False)
        self.form_panel.setEnabled(False)
        self._saver = _SaglikSaver(self._db, mode, payload)
        self._saver.finished.connect(self._on_save_finished)
        self._saver.error.connect(self._on_save_error)
        self._saver.start()

    def _on_save_finished(self, result: str):
        self.btn_kaydet.setEnabled(True)
        self.form_panel.setEnabled(True)
        if result == "rapor_ok":
            QMessageBox.information(self, "Başarılı", "Rapor kaydedildi.")
        else:
            QMessageBox.information(self, "Başarılı", "Sağlık takip kaydı kaydedildi.")
        self._clear_form()
        self.load_data()

    def _on_save_error(self, msg: str):
        self.btn_kaydet.setEnabled(True)
        self.form_panel.setEnabled(True)
        logger.error(f"Saglik takip kaydetme hatasi: {msg}")
        QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata oluştu:\n{msg}")

    # -------------------------------------------------------------------------
    # Seçim & Temizlik
    # -------------------------------------------------------------------------

    def _on_select_row(self, *_):
        """Sadece durum çubuğunu günceller. _editing_id'ye dokunmaz."""
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        row = self.model.get_row(idx.row())
        if not row:
            return
        ad    = str(row.get("AdSoyad", "")).strip()
        birim = str(row.get("Birim",   "")).strip()
        durum = str(row.get("Durum",   "")).strip()
        self.lbl_info.setText(f"{ad}  |  {birim}  |  {durum}")

    def _clear_form(self):
        self._editing_id           = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        # Panel bileşenlerini varsayılan görünüme döndür
        self.exam_section.setVisible(True)
        self.cmb_personel.setVisible(True)
        self.lbl_personel_ro.setVisible(False)
        self.inp_not.setVisible(True)
        self._rapor_only_mode = False
        self.form_panel.setVisible(False)

