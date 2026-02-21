# -*- coding: utf-8 -*-
import os
import uuid
from datetime import date, datetime

from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel, QDate, QPropertyAnimation, QEasingCurve, QRect, QSize
from PySide6.QtGui import QCursor, QPainter, QColor, QBrush, QFont, QPen, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QScrollArea,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableView, QHeaderView,
    QDateEdit, QMessageBox, QFileDialog, QGroupBox
)

from core.logger import logger
from core.date_utils import parse_date, to_db_date, to_ui_date
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
STATUS_OPTIONS = ["Uygun", "Sartli Uygun", "Uygun Degil"]

TABLE_COLUMNS = [
    ("AdSoyad", "Ad Soyad"),
    ("Birim", "Birim"),
    ("MuayeneTarihi", "Muayene"),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol"),
    ("Sonuc", "Sonuc"),
    ("Durum", "Durum"),
]


# ─── Muayene Timeline Widget ───────────────────────────────
class MuayeneTimelineWidget(QWidget):
    """
    Personelin muayene geçmişini dikey timeline olarak gösteren widget.
    - Tarih noktaları: Dikey çizgi üzerinde
    - Renk kodu: Uygun (yeşil), Şartlı (sarı), Uygun Değil (kırmızı)
    - Hover: Muayene detaylarını göster
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._exams: list[dict] = []  # [{"tarih": "2026-01-15", "sonuc": "Uygun", "notlar": "..."}, ...]
        self.setMinimumHeight(300)
        self.setStyleSheet("background: transparent;")
    
    def set_exams(self, exams: list[dict]):
        """Muayene liste ekle ve timeline'ı redraw et."""
        # Tarihe göre sırala (en eski → en yeni)
        self._exams = sorted(exams, key=lambda x: x.get("MuayeneTarihi", ""))
        self.update()
    
    def paintEvent(self, event):
        if not self._exams:
            p = QPainter(self)
            p.setFont(QFont("", 9))
            p.setPen(QColor(DarkTheme.TEXT_MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, "Muayene geçmişi boş")
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Padding ve layout
        m = 20  # margin
        cx = m + 20  # Timeline merkezine x
        top_y = m
        bot_y = self.height() - m
        
        if len(self._exams) > 1:
            item_height = (bot_y - top_y) / (len(self._exams) - 1) if len(self._exams) > 1 else 40
        else:
            item_height = 40
            top_y = self.height() // 2 - 20
        
        # Ana çizgi (timeline)
        p.setPen(QPen(QColor(DarkTheme.BG_TERTIARY), 2))
        p.drawLine(cx, top_y, cx, bot_y)
        
        # Her muayene noktası
        for i, exam in enumerate(self._exams):
            y = top_y + i * item_height
            
            # Status rengine göre renk seç
            status_color = self._get_status_color(exam.get("Durum", "Uygun"))
            
            # Nokta çiz (daire)
            p.setBrush(QBrush(status_color))
            p.setPen(QPen(QColor(DarkTheme.BG_PRIMARY), 2))
            radius = 6
            p.drawEllipse(int(cx - radius), int(y - radius), radius * 2, radius * 2)
            
            # Tarih ve sonuç yazı (nodeun sağında)
            text_x = cx + 16
            tarih_str = to_ui_date(exam.get("MuayeneTarihi", ""), "—")
            sonuc_str = exam.get("Sonuc", "")
            
            # Tarih
            p.setFont(QFont("", 8, QFont.Bold))
            p.setPen(QColor(DarkTheme.TEXT_PRIMARY))
            p.drawText(int(text_x), int(y - 8), f"{tarih_str}")
            
            # Sonuç/Durum
            p.setFont(QFont("", 7))
            p.setPen(QColor(DarkTheme.TEXT_MUTED))
            p.drawText(int(text_x), int(y + 6), f"{sonuc_str}")
        
        p.end()
    
    def _get_status_color(self, status: str) -> QColor:
        """Status'a göre renk döndür."""
        s = str(status).strip().lower()
        if "uygun" in s and "değil" not in s and "şartlı" not in s:
            # Uygun → yeşil
            return QColor(34, 197, 94)  # green-500
        elif "şartlı" in s:
            # Şartlı Uygun → sarı
            return QColor(234, 179, 8)  # yellow-500
        else:
            # Uygun Değil → kırmızı
            return QColor(239, 68, 68)  # red-500


class SaglikTakipTableModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._keys = [c[0] for c in TABLE_COLUMNS]
        self._headers = [c[1] for c in TABLE_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(TABLE_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            value = row.get(key, "")
            if key in ("MuayeneTarihi", "SonrakiKontrolTarihi"):
                return to_ui_date(value, "")
            return str(value)

        if role == Qt.TextAlignmentRole:
            if key in ("MuayeneTarihi", "SonrakiKontrolTarihi", "Sonuc", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, idx):
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None


class SaglikTakipPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._all_rows = []
        self._takip_rows = []
        self._personel_rows = []
        self._editing_id = None
        self._selected_report_path = ""
        self._drive_folders = {}
        self._exam_keys = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
        self._exam_widgets = {}
        self._drawer = None  # Sağdan açılan panel
        self._drawer_width = 450  # Drawer genişliği
        self._timeline_widget = None  # Muayene timeline
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(0)

        # ── Ana İçerik: Filtre + Tablo (Sol) ──
        main_container = QWidget()
        main_lay = QVBoxLayout(main_container)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(8)

        # Filtre paneli
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fb = QHBoxLayout(filter_frame)
        fb.setContentsMargins(12, 8, 12, 8)
        fb.setSpacing(8)

        self.cmb_yil = QComboBox()
        self.cmb_yil.setStyleSheet(S["combo"])
        self.cmb_yil.addItem("Tum Yillar", 0)
        this_year = date.today().year
        for y in range(this_year + 1, this_year - 4, -1):
            self.cmb_yil.addItem(str(y), y)
        self.cmb_yil.setCurrentIndex(1)
        fb.addWidget(self.cmb_yil)

        self.cmb_birim_filter = QComboBox()
        self.cmb_birim_filter.setStyleSheet(S["combo"])
        self.cmb_birim_filter.addItem("Tum Birimler")
        fb.addWidget(self.cmb_birim_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setStyleSheet(S["combo"])
        self.cmb_durum_filter.addItems(["Tum Durumlar", "Planlandi", "Gecerli", "Gecikmis", "Riskli"])
        fb.addWidget(self.cmb_durum_filter)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ad soyad ara...")
        self.search.setStyleSheet(S["search"])
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        fb.addWidget(self.search)

        fb.addStretch()

        self.btn_toplu = QPushButton("Toplu Yillik Plan")
        self.btn_toplu.setStyleSheet(S["action_btn"])
        self.btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_toplu, "clipboard_list", color=DarkTheme.TEXT_PRIMARY, size=14)
        fb.addWidget(self.btn_toplu)

        self.btn_yeni = QPushButton("Yeni Ekle")
        self.btn_yeni.setStyleSheet(S["save_btn"])
        self.btn_yeni.setFixedSize(110, 36)
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        fb.addWidget(self.btn_yeni)

        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setStyleSheet(S["refresh_btn"])
        self.btn_yenile.setFixedSize(100, 36)
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fb.addWidget(self.btn_yenile)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setStyleSheet(S["close_btn"])
        self.btn_kapat.setFixedSize(100, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        fb.addWidget(self.btn_kapat)
        main_lay.addWidget(filter_frame)

        # Tablo
        self.model = SaglikTakipTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setStyleSheet(S["table"])
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, len(TABLE_COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        main_lay.addWidget(self.table, 1)

        self.lbl_info = QLabel("0 kayit")
        self.lbl_info.setStyleSheet(S["footer_label"])
        main_lay.addWidget(self.lbl_info)

        root.addWidget(main_container, 1)

        # ── Sağdan Açılan Drawer (Form) ──
        self._drawer = QFrame()
        self._drawer.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkTheme.BG_SECONDARY};
                border-left: 1px solid {DarkTheme.BORDER_PRIMARY};
            }}
        """)
        self._drawer.setFixedWidth(0)  # Başlangıçta gizli

        drawer_lay = QVBoxLayout(self._drawer)
        drawer_lay.setContentsMargins(0, 0, 0, 0)
        drawer_lay.setSpacing(0)

        # Drawer başlık
        drawer_header = QFrame()
        drawer_header.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkTheme.BG_PRIMARY};
                border-bottom: 1px solid {DarkTheme.BORDER_PRIMARY};
                padding: 12px;
            }}
        """)
        header_lay = QHBoxLayout(drawer_header)
        header_lay.setContentsMargins(12, 12, 12, 12)
        
        lbl_drawer_title = QLabel("Sağlık Kontrolü Detay")
        lbl_drawer_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {DarkTheme.TEXT_PRIMARY};")
        header_lay.addWidget(lbl_drawer_title)
        header_lay.addStretch()

        btn_drawer_close = QPushButton()
        btn_drawer_close.setFixedSize(32, 32)
        btn_drawer_close.setStyleSheet(S["close_btn"])
        btn_drawer_close.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(btn_drawer_close, "x", color=DarkTheme.TEXT_PRIMARY, size=16)
        btn_drawer_close.clicked.connect(self._close_drawer)
        header_lay.addWidget(btn_drawer_close)
        drawer_lay.addWidget(drawer_header)

        # Drawer scroll içerik
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        form_content = QWidget()
        form_content.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_content)
        form_lay.setContentsMargins(12, 12, 12, 12)
        form_lay.setSpacing(12)

        # Muayene Geçmişi Timeline
        grp_timeline = QGroupBox("Muayene Geçmişi")
        grp_timeline.setStyleSheet(S["group"])
        timeline_lay = QVBoxLayout(grp_timeline)
        timeline_lay.setContentsMargins(12, 12, 12, 12)
        self._timeline_widget = MuayeneTimelineWidget()
        timeline_lay.addWidget(self._timeline_widget)
        form_lay.addWidget(grp_timeline)

        # Kimlik ve Muayene
        grp_kimlik = QGroupBox("Kimlik ve Muayene")
        grp_kimlik.setStyleSheet(S["group"])
        g1 = QGridLayout(grp_kimlik)
        g1.setContentsMargins(12, 12, 12, 12)
        g1.setHorizontalSpacing(10)
        g1.setVerticalSpacing(8)

        g1.addWidget(QLabel("Personel"), 0, 0)
        self.cmb_personel = QComboBox()
        self.cmb_personel.setStyleSheet(S["combo"])
        self.cmb_personel.setEditable(True)
        self.cmb_personel.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_personel.lineEdit().setPlaceholderText("Personel seciniz...")
        g1.addWidget(self.cmb_personel, 0, 1)

        form_lay.addWidget(grp_kimlik)

        # Muayene durumları
        grp_durum = QGroupBox("Durum Bilgileri")
        grp_durum.setStyleSheet(S["group"])
        g2 = QGridLayout(grp_durum)
        g2.setContentsMargins(12, 12, 12, 12)
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(8)

        self._add_exam_fields(g2, 0, "Dermatoloji", "Dermatoloji Muayenesi")
        self._add_exam_fields(g2, 1, "Dahiliye", "Dahiliye Muayenesi")
        self._add_exam_fields(g2, 2, "Goz", "Goz Muayenesi")
        self._add_exam_fields(g2, 3, "Goruntuleme", "Goruntuleme Teknikleri (Varsa)")

        form_lay.addWidget(grp_durum)

        # Ek Bilgiler
        grp_ek = QGroupBox("Ek Bilgiler")
        grp_ek.setStyleSheet(S["group"])
        g3 = QGridLayout(grp_ek)
        g3.setContentsMargins(12, 12, 12, 12)
        g3.setHorizontalSpacing(10)
        g3.setVerticalSpacing(8)

        g3.addWidget(QLabel("Rapor"), 0, 0)
        rapor_row = QHBoxLayout()
        self.inp_rapor = QLineEdit()
        self.inp_rapor.setStyleSheet(S["input"])
        self.inp_rapor.setReadOnly(True)
        rapor_row.addWidget(self.inp_rapor, 1)
        self.btn_rapor = QPushButton("Sec")
        self.btn_rapor.setStyleSheet(S["action_btn"])
        self.btn_rapor.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_rapor, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        rapor_row.addWidget(self.btn_rapor)
        g3.addLayout(rapor_row, 0, 1)

        g3.addWidget(QLabel("Not"), 1, 0)
        self.inp_not = QLineEdit()
        self.inp_not.setStyleSheet(S["input"])
        g3.addWidget(self.inp_not, 1, 1)
        form_lay.addWidget(grp_ek)
        form_lay.addStretch()

        scroll.setWidget(form_content)
        drawer_lay.addWidget(scroll, 1)

        # Drawer butonları
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 12)
        btn_row.setSpacing(8)
        self.btn_temizle = QPushButton("Temizle / Yeni")
        self.btn_temizle.setStyleSheet(S["action_btn"])
        self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_temizle, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        btn_row.addWidget(self.btn_temizle)
        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        btn_row.addWidget(self.btn_kaydet)
        drawer_lay.addLayout(btn_row)

        root.addWidget(self._drawer)

    def _connect_signals(self):
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_kaydet.clicked.connect(self._save_record)
        self.btn_temizle.clicked.connect(self._clear_form)
        self.btn_yeni.clicked.connect(self._new_record)
        self.btn_rapor.clicked.connect(self._pick_report)
        self.btn_toplu.clicked.connect(self._bulk_plan_year)
        self.search.textChanged.connect(self._apply_filters)
        self.cmb_yil.currentIndexChanged.connect(self._apply_filters)
        self.cmb_birim_filter.currentTextChanged.connect(self._apply_filters)
        self.cmb_durum_filter.currentTextChanged.connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._on_select_row)
        for key in self._exam_keys:
            self._exam_widgets[key]["durum"].currentTextChanged.connect(
                lambda _txt, k=key: self._on_exam_status_changed(k)
            )

    def load_data(self):
        if not self._db:
            return
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            personel_repo = registry.get("Personel")
            takip_repo = registry.get("Personel_Saglik_Takip")
            sabit_repo = registry.get("Sabitler")

            all_personel = personel_repo.get_all()
            self._personel_rows = [
                p for p in all_personel
                if str(p.get("Durum", "")).strip().lower() != "pasif"
            ]

            self.cmb_personel.clear()
            for p in sorted(self._personel_rows, key=lambda x: str(x.get("AdSoyad", ""))):
                kimlik = str(p.get("KimlikNo", "")).strip()
                ad = str(p.get("AdSoyad", "")).strip()
                birim = str(p.get("GorevYeri", "")).strip()
                label = f"{ad} ({kimlik})"
                self.cmb_personel.addItem(label, {"KimlikNo": kimlik, "AdSoyad": ad, "Birim": birim})

            self._takip_rows = takip_repo.get_all()
            self._drive_folders = {
                str(r.get("MenuEleman", "")).strip(): str(r.get("Aciklama", "")).strip()
                for r in sabit_repo.get_all()
                if r.get("Kod") == "Sistem_DriveID" and r.get("Aciklama", "").strip()
            }
            self._all_rows = self._build_personel_list_rows(all_personel)
            self._fill_filter_combos()
            self._apply_filters()
            logger.info(f"Saglik takip yüklendi: {len(self._all_rows)} kayit")
        except Exception as exc:
            logger.error(f"Saglik takip yukleme hatasi: {exc}")

    def _build_personel_list_rows(self, all_personel):
        rows = []
        for p in all_personel:
            if str(p.get("Durum", "")).strip().lower() == "pasif":
                continue

            muayene = to_db_date(p.get("MuayeneTarihi", ""))
            d_muayene = parse_date(muayene)
            if d_muayene:
                try:
                    sonraki = d_muayene.replace(year=d_muayene.year + 1).isoformat()
                except ValueError:
                    sonraki = d_muayene.replace(month=2, day=28, year=d_muayene.year + 1).isoformat()
            else:
                sonraki = ""

            sonuc = str(p.get("Sonuc", "")).strip()
            s_low = sonuc.lower()
            if s_low == "uygun degil":
                durum = "Riskli"
            elif s_low == "sartli uygun":
                durum = "Gecerli"
            elif s_low == "uygun":
                durum = "Gecikmis" if (parse_date(sonraki) and parse_date(sonraki) < date.today()) else "Gecerli"
            else:
                durum = "Planlandi"

            yil = d_muayene.year if d_muayene else date.today().year
            rows.append({
                "KayitNo": "",
                "Personelid": str(p.get("KimlikNo", "")).strip(),
                "AdSoyad": str(p.get("AdSoyad", "")).strip(),
                "Birim": str(p.get("GorevYeri", "")).strip(),
                "Yil": yil,
                "MuayeneTarihi": muayene,
                "SonrakiKontrolTarihi": sonraki,
                "Sonuc": sonuc,
                "Durum": durum,
            })
        return rows

    def _fill_filter_combos(self):
        curr = self.cmb_birim_filter.currentText()
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
        query = self.search.text().strip().lower()
        yil = self.cmb_yil.currentData()
        birim_filter = self.cmb_birim_filter.currentText()
        durum_filter = self.cmb_durum_filter.currentText()
        out = []
        for row in self._all_rows:
            row_yil = int(row.get("Yil") or 0)
            if yil and row_yil != int(yil):
                continue

            if birim_filter != "Tum Birimler":
                if str(row.get("Birim", "")).strip() != birim_filter:
                    continue

            if durum_filter != "Tum Durumlar":
                if str(row.get("Durum", "")).strip() != durum_filter:
                    continue

            ad = str(row.get("AdSoyad", "")).lower()
            birim = str(row.get("Birim", "")).lower()
            if query and query not in ad and query not in birim:
                continue
            out.append(row)
        out.sort(key=lambda r: (str(r.get("AdSoyad", "")), str(r.get("MuayeneTarihi", ""))), reverse=False)
        self.model.set_rows(out)
        self.lbl_info.setText(f"{len(out)} kayit")

    def _add_exam_fields(self, layout, row_idx, key, title):
        box = QGroupBox(title)
        box.setStyleSheet(S["group"])
        gl = QGridLayout(box)
        gl.setContentsMargins(10, 8, 10, 8)
        gl.setHorizontalSpacing(8)
        gl.setVerticalSpacing(6)

        lbl_tarih = QLabel("Muayene Tarihi")
        lbl_tarih.setStyleSheet(S.get("label", ""))
        gl.addWidget(lbl_tarih, 0, 0)

        de = QDateEdit(QDate.currentDate())
        de.setDisplayFormat("dd.MM.yyyy")
        de.setCalendarPopup(True)
        de.setStyleSheet(S["date"])
        ThemeManager.setup_calendar_popup(de)
        gl.addWidget(de, 0, 1)

        lbl_durum = QLabel("Durum")
        lbl_durum.setStyleSheet(S.get("label", ""))
        gl.addWidget(lbl_durum, 0, 2)

        cmb = QComboBox()
        cmb.addItems([""] + STATUS_OPTIONS)
        cmb.setStyleSheet(S["combo"])
        gl.addWidget(cmb, 0, 3)

        layout.addWidget(box, row_idx, 0, 1, 2)
        self._exam_widgets[key] = {"tarih": de, "durum": cmb}

    def _on_exam_status_changed(self, key):
        # Artık açıklama alanı yok, boş bırakıyoruz
        pass

    def _safe_date_from_widget(self, widget):
        if not widget:
            return ""
        return to_db_date(widget.date().toString("yyyy-MM-dd"))

    def _exam_date_if_set(self, key):
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return self._safe_date_from_widget(w["tarih"])

    def _compute_summary(self):
        exam_data = []
        for key in self._exam_keys:
            w = self._exam_widgets[key]
            tarih_db = self._exam_date_if_set(key)
            durum = str(w["durum"].currentText()).strip()
            exam_data.append((tarih_db, durum))

        dates = [d for d, _ in exam_data if parse_date(d)]
        latest = max(dates) if dates else ""
        sonraki = ""
        if latest:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            try:
                sonraki = d.replace(year=d.year + 1).isoformat()
            except ValueError:
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        statuses = [s for _, s in exam_data if s]
        if "Uygun Degil" in statuses:
            sonuc = "Uygun Degil"
            durum = "Riskli"
        elif "Sartli Uygun" in statuses:
            sonuc = "Sartli Uygun"
            durum = "Gecerli"
        elif "Uygun" in statuses:
            sonuc = "Uygun"
            if parse_date(sonraki) and parse_date(sonraki) < date.today():
                durum = "Gecikmis"
            else:
                durum = "Gecerli"
        else:
            sonuc = ""
            durum = "Planlandi"

        return latest, sonraki, sonuc, durum

    def _pick_report(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Rapor Sec", "", "Dosyalar (*.pdf *.jpg *.jpeg *.png)"
        )
        if path:
            self._selected_report_path = path
            self.inp_rapor.setText(path)

    def _get_report_folder_id(self):
        """Sabitler/Sistem_DriveID kayitlarindan saglik rapor klasorunu bulur."""
        keys = [
            "Saglik_Raporlari",
                ]
        for key in keys:
            folder_id = str(self._drive_folders.get(key, "")).strip()
            if folder_id:
                return folder_id
        return ""

    def _upload_report_to_drive(self, tc_no, kayit_no):
        """Seçilen raporu Drive'a yükler (veya offline modda yerel klasöre) ve link döndürür."""
        if not self._selected_report_path:
            return self.inp_rapor.text().strip()
        if not os.path.exists(self._selected_report_path):
            QMessageBox.warning(self, "Uyari", "Secilen rapor dosyasi bulunamadi.")
            return ""

        try:
            from core.di import get_cloud_adapter
            
            cloud = get_cloud_adapter()
            ext = os.path.splitext(self._selected_report_path)[1]
            custom_name = f"{tc_no}_{kayit_no}_SaglikRapor{ext}"
            
            # Offline modda folder_id gereksiz ama offline_folder_name gerekli
            folder_id = None
            if cloud.is_online:
                folder_id = self._get_report_folder_id()
                if not folder_id:
                    QMessageBox.warning(
                        self,
                        "Drive Ayari Eksik",
                        "Sabitler tablosunda Sistem_DriveID icin saglik rapor klasoru bulunamadi."
                    )
                    return ""
            
            link = cloud.upload_file(
                self._selected_report_path,
                parent_folder_id=folder_id,
                custom_name=custom_name,
                offline_folder_name="Saglik_Raporlari"
            )
            
            if not link:
                if cloud.is_online:
                    QMessageBox.warning(self, "Drive", "Rapor Drive'a yuklenemedi.")
                return ""
            
            mode_text = "Drive'a yuklendi" if cloud.is_online else "yerel klasore kaydedildi"
            logger.info(f"Saglik raporu {mode_text}: {custom_name}")
            return str(link).strip()
        except Exception as exc:
            logger.error(f"Saglik rapor yukleme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Rapor yuklenemedi:\n{exc}")
            return ""

    def _save_record(self):
        if self.cmb_personel.currentIndex() < 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Lutfen personel seciniz.")
            return

        personel_data = self.cmb_personel.currentData()
        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        kayit_no = self._editing_id or uuid.uuid4().hex[:12].upper()
        rapor_link = self._upload_report_to_drive(
            personel_data.get("KimlikNo", ""),
            kayit_no
        )
        if self._selected_report_path and not rapor_link:
            return

        payload = {
            "KayitNo": kayit_no,
            "Personelid": personel_data.get("KimlikNo", ""),
            "AdSoyad": personel_data.get("AdSoyad", ""),
            "Birim": personel_data.get("Birim", ""),
            "Yil": int(self.cmb_yil.currentData() or date.today().year),
            "MuayeneTarihi": muayene_db,
            "SonrakiKontrolTarihi": sonraki_db,
            "Sonuc": sonuc,
            "Durum": durum,
            "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
            "DermatolojiDurum": str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
            "DahiliyeMuayeneTarihi": self._exam_date_if_set("Dahiliye"),
            "DahiliyeDurum": str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
            "GozMuayeneTarihi": self._exam_date_if_set("Goz"),
            "GozDurum": str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
            "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
            "GoruntulemeDurum": str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
            "RaporDosya": rapor_link,
            "Notlar": self.inp_not.text().strip(),
        }

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            takip_repo = registry.get("Personel_Saglik_Takip")
            personel_repo = registry.get("Personel")
            mevcut = takip_repo.get_by_id(payload["KayitNo"])
            if mevcut:
                takip_repo.update(payload["KayitNo"], payload)
            else:
                takip_repo.insert(payload)

            personel_sonuc = "uygun" if sonuc == "Uygun" else sonuc
            personel_repo.update(payload["Personelid"], {
                "MuayeneTarihi": muayene_db,
                "Sonuc": personel_sonuc,
            })

            QMessageBox.information(self, "Basarili", "Saglik takip kaydi kaydedildi.")
            self._clear_form()
            self.load_data()
        except Exception as exc:
            logger.error(f"Saglik takip kaydetme hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Kayit sirasinda hata olustu:\n{exc}")

    def _find_personel_takip_row(self, personelid):
        selected_year = int(self.cmb_yil.currentData() or 0)
        candidates = [
            r for r in self._takip_rows
            if str(r.get("Personelid", "")).strip() == str(personelid).strip()
        ]
        if selected_year:
            yearly = [r for r in candidates if int(r.get("Yil") or 0) == selected_year]
            if yearly:
                candidates = yearly
        if not candidates:
            return None
        candidates.sort(
            key=lambda r: (
                to_db_date(r.get("MuayeneTarihi", "")),
                str(r.get("updated_at", "")),
                str(r.get("KayitNo", "")),
            ),
            reverse=True
        )
        return candidates[0]

    def _on_select_row(self, *_):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        row = self.model.get_row(idx.row())
        if not row:
            return

        personelid = str(row.get("Personelid", "")).strip()
        takip_row = self._find_personel_takip_row(personelid) or {}

        self._editing_id = takip_row.get("KayitNo")
        self._selected_report_path = ""
        self.inp_not.setText(str(takip_row.get("Notlar", "")))
        self.inp_rapor.setText(str(takip_row.get("RaporDosya", "")))
        mapping = [
            ("Dermatoloji", "DermatolojiMuayeneTarihi", "DermatolojiDurum"),
            ("Dahiliye", "DahiliyeMuayeneTarihi", "DahiliyeDurum"),
            ("Goz", "GozMuayeneTarihi", "GozDurum"),
            ("Goruntuleme", "GoruntulemeMuayeneTarihi", "GoruntulemeDurum"),
        ]
        for key, col_t, col_d in mapping:
            w = self._exam_widgets[key]
            w["durum"].setCurrentText(str(takip_row.get(col_d, "")))
            d = parse_date(takip_row.get(col_t, ""))
            if d:
                w["tarih"].setDate(QDate(d.year, d.month, d.day))
            else:
                w["tarih"].setDate(QDate.currentDate())
            self._on_exam_status_changed(key)

        for i in range(self.cmb_personel.count()):
            info = self.cmb_personel.itemData(i)
            if info and str(info.get("KimlikNo", "")) == personelid:
                self.cmb_personel.setCurrentIndex(i)
                break

        # Timeline güncelle
        self._update_timeline_for_person(personelid)
        
        # Drawer'ı aç
        self._open_drawer()
    
    def _update_timeline_for_person(self, personelid: str):
        """Kişinin tüm muayene geçmişini timeline'a göster."""
        if not self._timeline_widget:
            return
        
        # Personel için tüm muayene kayıtlarını filtrele
        person_exams = [r for r in self._all_rows if str(r.get("Personelid", "")).strip() == personelid]
        
        # Muayene geçmişini timeline'a geç
        self._timeline_widget.set_exams(person_exams)

    def _new_record(self):
        """Yeni kayıt eklemek için formu temizle ve drawer'ı aç."""
        self._editing_id = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        self.cmb_personel.setCurrentIndex(-1)
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        self._open_drawer()

    def _clear_form(self):
        self._editing_id = None
        self._selected_report_path = ""
        self.inp_rapor.clear()
        self.inp_not.clear()
        for key in self._exam_keys:
            self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
            self._exam_widgets[key]["durum"].setCurrentIndex(0)
        # Drawer'ı kapat
        self._close_drawer()

    def _bulk_plan_year(self):
        target_year = self.cmb_yil.currentData()
        if not target_year:
            target_year = date.today().year
        if not self._personel_rows:
            QMessageBox.warning(self, "Uyari", "Planlanacak aktif personel bulunamadi.")
            return

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            takip_repo = registry.get("Personel_Saglik_Takip")
            mevcut = takip_repo.get_all()
            mevcut_keys = {(str(r.get("Personelid", "")), int(r.get("Yil") or 0)) for r in mevcut}

            added = 0
            for p in self._personel_rows:
                pid = str(p.get("KimlikNo", "")).strip()
                if not pid or (pid, int(target_year)) in mevcut_keys:
                    continue
                plan_date = date(int(target_year), 1, 15)
                takip_repo.insert({
                    "KayitNo": uuid.uuid4().hex[:12].upper(),
                    "Personelid": pid,
                    "AdSoyad": str(p.get("AdSoyad", "")).strip(),
                    "Birim": str(p.get("GorevYeri", "")).strip(),
                    "Yil": int(target_year),
                    "MuayeneTarihi": "",
                    "SonrakiKontrolTarihi": plan_date.isoformat(),
                    "Sonuc": "",
                    "Durum": "Planlandi",
                    "DermatolojiMuayeneTarihi": "",
                    "DermatolojiDurum": "",
                    "DahiliyeMuayeneTarihi": "",
                    "DahiliyeDurum": "",
                    "GozMuayeneTarihi": "",
                    "GozDurum": "",
                    "GoruntulemeMuayeneTarihi": "",
                    "GoruntulemeDurum": "",
                    "RaporDosya": "",
                    "Notlar": "",
                })
                added += 1

            self.load_data()
            QMessageBox.information(self, "Tamam", f"{added} personel icin yillik plan olusturuldu.")
        except Exception as exc:
            logger.error(f"Toplu plan hatasi: {exc}")
            QMessageBox.critical(self, "Hata", f"Toplu planlama sirasinda hata:\n{exc}")

    def _open_drawer(self):
        """Sağdan drawer'ı animasyonlu aç."""
        if not self._drawer or self._drawer.width() == self._drawer_width:
            return
        
        anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
        anim.setDuration(250)
        anim.setStartValue(0)
        anim.setEndValue(self._drawer_width)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        # Minimum genişliği de ayarla
        self._drawer.setMinimumWidth(self._drawer_width)

    def _close_drawer(self):
        """Drawer'ı animasyonlu kapat."""
        if not self._drawer or self._drawer.width() == 0:
            return
        
        anim = QPropertyAnimation(self._drawer, b"maximumWidth", self)
        anim.setDuration(200)
        anim.setStartValue(self._drawer.width())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(lambda: self._drawer.setMinimumWidth(0))
        anim.start(QPropertyAnimation.DeleteWhenStopped)
