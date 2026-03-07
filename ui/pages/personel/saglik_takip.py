# -*- coding: utf-8 -*-
import os
import uuid
import platform
import subprocess
from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableView,
    QDateEdit, QMessageBox, QFileDialog, QSizePolicy,
)

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
            return "A\u00e7" if row.get("_RaporPath") else "-"
        return super()._display(key, row)

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        return None

    def _bg(self, key, row):
        if key == "Durum":
            return self.status_bg(row.get("Durum", ""))
        return None


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

    # -- Filtre \u00e7ubu\u011fu -------------------------------------------------------

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

        self.btn_toplu = QPushButton("Toplu Yillik Plan")
        self.btn_toplu.setProperty("style-role", "action")
        self.btn_toplu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_toplu, "clipboard_list", color=IconColors.PRIMARY, size=14)
        lay.addWidget(self.btn_toplu)

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

        # \u00dcst: personel se\u00e7imi + kapat
        top_row = QHBoxLayout()
        lbl_personel = QLabel("Personel ad\u0131")
        lbl_personel.setProperty("style-role", "section-title")
        top_row.addWidget(lbl_personel)

        self.cmb_personel = QComboBox()
        self.cmb_personel.setMinimumWidth(200)
        top_row.addWidget(self.cmb_personel, 1)

        self.btn_form_kapat = QPushButton()
        self.btn_form_kapat.setProperty("style-role", "danger")
        self.btn_form_kapat.setFixedSize(28, 28)
        self.btn_form_kapat.setToolTip("Kapat")
        self.btn_form_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_form_kapat, "x", color=IconColors.DANGER, size=12)
        top_row.addWidget(self.btn_form_kapat)
        form_lay.addLayout(top_row)

        # 4 muayene kutusu \u2014 yatayda
        exam_row = QHBoxLayout()
        exam_row.setSpacing(12)
        exam_labels = {
            "Dermatoloji": "Dermatoloji",
            "Dahiliye":    "Dahiliye",
            "Goz":         "G\u00f6z",
            "Goruntuleme": "G\u00f6r\u00fcntüleme",
        }
        for key in self._exam_keys:
            exam_row.addWidget(self._create_exam_box(key, exam_labels[key]))
        form_lay.addLayout(exam_row)

        # Rapor dosyas\u0131 sat\u0131r\u0131
        rapor_row = QHBoxLayout()
        rapor_row.setSpacing(8)

        self.btn_rapor = QPushButton("Rapor Se\u00e7")
        self.btn_rapor.setProperty("style-role", "secondary")
        self.btn_rapor.setFixedWidth(100)
        self.btn_rapor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_rapor, "upload", color=IconColors.PRIMARY, size=13)
        rapor_row.addWidget(self.btn_rapor)

        self.inp_rapor = QLineEdit()
        self.inp_rapor.setReadOnly(True)
        self.inp_rapor.setPlaceholderText("Dosya se\u00e7ilmedi...")
        rapor_row.addWidget(self.inp_rapor, 1)
        form_lay.addLayout(rapor_row)

        # Notlar sat\u0131r\u0131
        not_row = QHBoxLayout()
        lbl_not = QLabel("Notlar")
        lbl_not.setProperty("style-role", "form")
        not_row.addWidget(lbl_not)
        self.inp_not = QLineEdit()
        self.inp_not.setPlaceholderText("A\u00e7\u0131klama veya not...")
        not_row.addWidget(self.inp_not, 1)
        form_lay.addLayout(not_row)

        # Kaydet / \u0130ptal
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=IconColors.PRIMARY, size=14)
        btn_row.addWidget(self.btn_kaydet)

        self.btn_temizle = QPushButton("\u0130ptal")
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

    # -------------------------------------------------------------------------
    # Sinyal ba\u011flant\u0131lar\u0131
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_kaydet.clicked.connect(self._save_record)
        self.btn_temizle.clicked.connect(self._clear_form)
        self.btn_yeni.clicked.connect(self._show_form_panel)
        self.btn_form_kapat.clicked.connect(self._hide_form_panel)
        self.btn_rapor.clicked.connect(self._pick_report)
        self.btn_toplu.clicked.connect(self._bulk_plan_year)
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
    # Form panel g\u00f6ster / gizle
    # -------------------------------------------------------------------------

    def _show_form_panel(self):
        self._editing_id = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        self.cmb_personel.setCurrentIndex(-1)
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        self.form_panel.setVisible(True)

    def _hide_form_panel(self):
        self.form_panel.setVisible(False)

    # -------------------------------------------------------------------------
    # Veri y\u00fckleme
    # -------------------------------------------------------------------------

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_saglik_service as _svc_factory
            from core.paths import DATA_DIR
            _svc          = _svc_factory(self._db)
            personel_repo = _svc._r.get("Personel")
            takip_repo    = _svc._r.get("Personel_Saglik_Takip")
            dokuman_repo  = _svc._r.get("Dokumanlar")

            all_personel = personel_repo.get_all()
            self._personel_rows = [
                p for p in all_personel
                if str(p.get("Durum", "")).strip().lower() != "pasif"
            ]

            self.cmb_personel.clear()
            for p in sorted(self._personel_rows, key=lambda x: str(x.get("AdSoyad", ""))):
                kimlik = str(p.get("KimlikNo", "")).strip()
                ad     = str(p.get("AdSoyad", "")).strip()
                birim  = str(p.get("GorevYeri", "")).strip()
                self.cmb_personel.addItem(
                    f"{ad} ({kimlik})",
                    {"KimlikNo": kimlik, "AdSoyad": ad, "Birim": birim},
                )

            self._takip_rows = takip_repo.get_all()

            rapor_map: dict = {}
            docs = dokuman_repo.get_where({"EntityType": "personel"})
            for doc in docs:
                if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                    continue
                entity_id = str(doc.get("EntityId", "")).strip()
                rel_id    = str(doc.get("IliskiliBelgeID", "")).strip()
                if entity_id and rel_id:
                    rapor_map[(entity_id, rel_id)] = doc

            for takip in self._takip_rows:
                personelid = str(takip.get("Personelid", "")).strip()
                kayit_no   = str(takip.get("KayitNo", "")).strip()
                doc        = rapor_map.get((personelid, kayit_no))

                rapor_path = ""
                if doc:
                    local_path = str(doc.get("LocalPath", "")).strip()
                    drive_path = str(doc.get("DrivePath", "")).strip()
                    belge_adi  = str(doc.get("Belge", "")).strip()
                    tc_no      = str(doc.get("EntityId", "")).strip() or personelid

                    logger.info(
                        f"RAPOR [{kayit_no}] doc found: "
                        f"LocalPath={local_path[:50] if local_path else 'EMPTY'}, Belge={belge_adi}"
                    )

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

                logger.info(
                    f"RAPOR [{kayit_no}] FINAL _RaporPath: {rapor_path[:80] if rapor_path else 'EMPTY'}"
                )
                takip["_RaporPath"] = rapor_path

            self._all_rows = self._build_takip_list_rows(self._takip_rows, all_personel)
            self._fill_filter_combos()
            self._apply_filters()
            logger.info(f"Saglik takip yuklendi: {len(self._all_rows)} kayit")
        except Exception as exc:
            logger.error(f"Saglik takip yukleme hatasi: {exc}")

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
    # Muayene yard\u0131mc\u0131lar\u0131
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
            exam_data.append((tarih, durum))

        dates   = [d for d, _ in exam_data if parse_date(d)]
        latest  = max(dates) if dates else ""
        sonraki = ""
        if latest:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            try:
                sonraki = d.replace(year=d.year + 1).isoformat()
            except ValueError:
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        statuses = [s for _, s in exam_data if s]
        if "Uygun De\u011fil" in statuses:
            sonuc = "Uygun De\u011fil"
            durum = "Riskli"
        elif "Şartl\u0131 Uygun" in statuses:
            sonuc = "Şartl\u0131 Uygun"
            durum = "Gecerli"
        elif "Uygun" in statuses:
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
                belge_turu   = "Periyodik Sa\u011fl\u0131k Muayene Raporu",
                folder_name  = "Saglik_Raporlari",
                doc_type     = "Personel_Belge",
                custom_name  = custom_name,
                iliskili_id  = str(kayit_no),
                iliskili_tip = "Personel_Saglik_Takip",
            )
            if not sonuc.get("ok"):
                err = str(sonuc.get("error", "Bilinmeyen y\u00fckleme hatas\u0131"))
                QMessageBox.warning(self, "Yukleme Hatasi", f"Rapor y\u00fcklenemedi:\n{err}")
                return ""
            rapor_ref = str(sonuc.get("drive_link") or sonuc.get("local_path") or "").strip()
            logger.info(f"Saglik raporu yuklendi [{sonuc.get('mode', 'none')}]: {custom_name}")
            return rapor_ref
        except Exception as exc:
            logger.error(f"Saglik rapor yukleme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Rapor yuklenemedi:\n{exc}")
            return ""

    # -------------------------------------------------------------------------
    # Kaydet
    # -------------------------------------------------------------------------

    def _save_record(self):
        if self.cmb_personel.currentIndex() < 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lutfen personel seciniz.")
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

        try:
            from core.di import get_saglik_service as _svc_factory
            _svc          = _svc_factory(self._db)
            takip_repo    = _svc._r.get("Personel_Saglik_Takip")
            personel_repo = _svc._r.get("Personel")
            mevcut = takip_repo.get_by_id(payload["KayitNo"])
            if mevcut:
                takip_repo.update(payload["KayitNo"], payload)
            else:
                takip_repo.insert(payload)
            personel_repo.update(payload["Personelid"], {
                "MuayeneTarihi": muayene_db,
                "Sonuc":         sonuc,
            })
            QMessageBox.information(self, "Basarili", "Saglik takip kaydi kaydedildi.")
            self._clear_form()
            self.load_data()
        except Exception as exc:
            logger.error(f"Saglik takip kaydetme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Kayit sirasinda hata olustu:\n{exc}")

    # -------------------------------------------------------------------------
    # Se\u00e7im & Temizlik
    # -------------------------------------------------------------------------

    def _on_select_row(self, *_):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        row = self.model.get_row(idx.row())
        if not row:
            return

        kayit_no  = str(row.get("KayitNo", "")).strip()
        takip_row = None
        for t in self._takip_rows:
            if str(t.get("KayitNo", "")).strip() == kayit_no:
                takip_row = t
                break
        if not takip_row:
            return

        personelid = str(takip_row.get("Personelid", "")).strip()
        self._editing_id           = takip_row.get("KayitNo")
        self._selected_report_path = ""
        self.inp_not.setText(str(takip_row.get("Notlar", "")))

        rapor_dosya = str(takip_row.get("RaporDosya", ""))
        self.inp_rapor.setText(os.path.basename(rapor_dosya) if rapor_dosya else "")

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
            self._on_exam_status_changed(key)

        for i in range(self.cmb_personel.count()):
            info = self.cmb_personel.itemData(i)
            if info and str(info.get("KimlikNo", "")) == personelid:
                self.cmb_personel.setCurrentIndex(i)
                break

    def _clear_form(self):
        self._editing_id           = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        self.form_panel.setVisible(False)

    def _bulk_plan_year(self):
        target_year = self.cmb_yil.currentData()
        if not target_year:
            target_year = date.today().year
        if not self._personel_rows:
            QMessageBox.warning(self, "Uyari", "Planlanacak aktif personel bulunamadi.")
            return
        try:
            from core.di import get_saglik_service as _svc_factory
            _svc       = _svc_factory(self._db)
            takip_repo = _svc._r.get("Personel_Saglik_Takip")
            mevcut     = takip_repo.get_all()
            mevcut_keys = {
                (str(r.get("Personelid", "")), int(r.get("Yil") or 0)) for r in mevcut
            }
            added = 0
            for p in self._personel_rows:
                pid = str(p.get("KimlikNo", "")).strip()
                if not pid or (pid, int(target_year)) in mevcut_keys:
                    continue
                plan_date = date(int(target_year), 1, 15)
                takip_repo.insert({
                    "KayitNo":                  uuid.uuid4().hex[:12].upper(),
                    "Personelid":               pid,
                    "AdSoyad":                  str(p.get("AdSoyad", "")).strip(),
                    "Birim":                    str(p.get("GorevYeri", "")).strip(),
                    "Yil":                      int(target_year),
                    "MuayeneTarihi":            "",
                    "SonrakiKontrolTarihi":     plan_date.isoformat(),
                    "Sonuc":                    "",
                    "Durum":                    "Planlandi",
                    "DermatolojiMuayeneTarihi": "",
                    "DermatolojiDurum":         "",
                    "DahiliyeMuayeneTarihi":    "",
                    "DahiliyeDurum":            "",
                    "GozMuayeneTarihi":         "",
                    "GozDurum":                 "",
                    "GoruntulemeMuayeneTarihi": "",
                    "GoruntulemeDurum":         "",
                    "RaporDosya":               "",
                    "Notlar":                   "",
                })
                added += 1
            self.load_data()
            QMessageBox.information(
                self, "Tamam", f"{added} personel icin yillik plan olusturuldu."
            )
        except Exception as exc:
            logger.error(f"Toplu plan hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Toplu planlama sirasinda hata:\n{exc}")

    # -------------------------------------------------------------------------
    # \u00c7ift t\u0131klama \u2014 rapor a\u00e7
    # -------------------------------------------------------------------------

    def _on_table_double_click(self, index):
        if not index.isValid():
            return
        if index.column() != len(TABLE_COLUMNS) - 1:
            return
        row = self.model.get_row(index.row())
        if not row:
            return
        rapor_path = str(row.get("_RaporPath", "")).strip()
        if not rapor_path:
            QMessageBox.information(self, "Bilgi", "Bu kay\u0131t i\u00e7in rapor dosyas\u0131 bulunmuyor.")
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

                if self._db and personelid and kayit_no:
                    try:
                        from core.di import get_saglik_service as _svc_factory
                        _svc         = _svc_factory(self._db)
                        dokuman_repo = _svc._r.get("Dokumanlar")
                        docs = dokuman_repo.get_where({
                            "EntityType": "personel",
                            "EntityId":   personelid,
                        })
                        for doc in docs:
                            if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                                continue
                            if str(doc.get("IliskiliBelgeID", "")).strip() != kayit_no:
                                continue
                            db_local = str(doc.get("LocalPath", "")).strip()
                            db_belge = str(doc.get("Belge",     "")).strip()
                            if db_local:
                                candidates.append(db_local)
                            if db_belge:
                                candidates.append(
                                    os.path.join(
                                        DATA_DIR, "offline_uploads",
                                        "personel", personelid, db_belge,
                                    )
                                )
                            break
                    except Exception as exc:
                        logger.warning(f"Rapor yolu DB fallback hatasi: {exc}")

                for candidate in candidates:
                    if candidate and os.path.isfile(candidate):
                        resolved_path = candidate
                        break

            if not os.path.isfile(resolved_path):
                QMessageBox.warning(
                    self, "Dosya Bulunamad\u0131",
                    f"Rapor dosyas\u0131 bulunamad\u0131:\n\n{rapor_path}\n\n"
                    f"Dosya silinmi\u015f veya yol de\u011fi\u015fmi\u015f olabilir.",
                )
                logger.warning(f"Saglik raporu dosyas\u0131 bulunamad\u0131: {rapor_path}")
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
            QMessageBox.critical(self, "Hata", f"Rapor a\u00e7\u0131lamad\u0131:\n\n{str(e)}\n\nYol: {rapor_path}")
