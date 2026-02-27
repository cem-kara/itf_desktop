# -*- coding: utf-8 -*-
"""Arıza Kayıt — Refactored List & Detail View."""
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QSplitter, QLabel, 
    QLineEdit, QComboBox, QPushButton, QHeaderView, QTabWidget, QFrame,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QModelIndex
from core.logger import logger
from core.paths import DATA_DIR
from core.date_utils import to_ui_date
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S
from ui.styles.colors import DarkTheme
from ui.pages.cihaz.models.ariza_model import (
    ArizaTableModel, ARIZA_COLUMNS, DURUM_COLOR, ONCELIK_COLOR
)


# ════════════════════════════════════════════════════════════════════
#  ANA FORM
# ════════════════════════════════════════════════════════════════════
class ArizaKayitForm(QWidget):
    """Arıza listesi, detay paneli ve işlem geçmişi."""

    def __init__(self, db=None, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard
        self._rows: List[Dict] = []
        self._all_rows: List[Dict] = []
        self._selected_ariza_id: Optional[str] = None

        self._base_docs_dir = Path(DATA_DIR) / "offline_uploads" / "cihazlar" / "belgeler"
        self._base_docs_dir.mkdir(parents=True, exist_ok=True)
        self._docs_dir = (self._base_docs_dir / cihaz_id if cihaz_id else self._base_docs_dir)
        self._docs_dir.mkdir(parents=True, exist_ok=True)

        self._active_form: Optional[QWidget] = None

        self._setup_ui()
        self._load_filter_combos()
        self._load_data()
        self._update_perf_tab_label()

    # ══════════════════════════════════════════════════════
    #  UI KURULUMU
    # ══════════════════════════════════════════════════════
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # KPI Şeridi
        root.addWidget(self._build_kpi_bar())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{getattr(DarkTheme, 'BORDER', '#242938')};")
        root.addWidget(sep)

        # Sekmeli alan
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 0 — Arıza Listesi
        list_tab = self._build_list_tab()
        self._tabs.addTab(list_tab, "Arıza Listesi")

        # Tab 1 — Performans
        self._perf_tab = QWidget()
        self._perf_tab.setStyleSheet(f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};")
        self._tabs.addTab(self._perf_tab, "Cihaz Performansı")

        root.addWidget(self._tabs, 1)

    def _build_kpi_bar(self) -> QWidget:
        """KPI Şeridi."""
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)

        self._kpi_labels: Dict[str, QLabel] = {}
        cards = [
            ("toplam", "TOPLAM ARIZA", "0", getattr(DarkTheme, "ACCENT", "#4f8ef7")),
            ("acik", "AÇIK / KRİTİK", "0 / 0", getattr(DarkTheme, "DANGER", "#f75f5f")),
            ("ort_sure", "ORT. ÇÖZÜM", "— gün", getattr(DarkTheme, "WARNING", "#f5a623")),
            ("kapali_ay", "BU AY KAPANDI", "0", getattr(DarkTheme, "SUCCESS", "#3ecf8e")),
            ("yinelenen", "YİNELENEN ARIZA", "0", getattr(DarkTheme, "DANGER", "#f75f5f")),
        ]
        
        for key, title, default, color in cards:
            layout.addWidget(self._make_kpi_card(key, title, default, color), 1)

        return bar

    def _make_kpi_card(self, key: str, title: str, default: str, color: str) -> QWidget:
        """KPI kartı."""
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{getattr(DarkTheme, 'PANEL', '#191d26')};border-radius:6px;margin:0 2px;}}"
            f"QWidget:hover{{background:{getattr(DarkTheme, 'BORDER', '#242938')};}}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(
            f"font-size:9px;font-weight:600;letter-spacing:0.06em;color:{getattr(DarkTheme, 'TEXT_MUTED', '#5a6278')};background:transparent;"
        )
        lbl_v = QLabel(default)
        lbl_v.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};background:transparent;")
        vl.addWidget(lbl_t)
        vl.addWidget(lbl_v)
        self._kpi_labels[key] = lbl_v
        return card

    def _update_kpi(self):
        """KPI'ları güncelle."""
        rows = self._all_rows
        if not rows:
            for k, v in [("toplam","0"),("acik","0 / 0"),("ort_sure","— gün"),("kapali_ay","0"),("yinelenen","0")]:
                self._kpi_labels[k].setText(v)
            return

        toplam = len(rows)
        acik = sum(1 for r in rows if r.get("Durum", "") in ("Açık", "Acik"))
        kritik = sum(1 for r in rows if r.get("Oncelik", "") == "Kritik" and r.get("Durum", "") in ("Açık", "Acik", "Devam Ediyor"))

        # Ortalama çözüm süresi
        sure_list = []
        for r in rows:
            if r.get("Durum", "") in ("Kapalı", "Kapali"):
                t = r.get("BaslangicTarihi", "")
                if t and len(t) >= 10:
                    try:
                        start = datetime.strptime(t[:10], "%Y-%m-%d")
                        sure_list.append((datetime.now() - start).days)
                    except ValueError:
                        pass
        ort_sure = f"{round(sum(sure_list)/len(sure_list), 1)} gün" if sure_list else "— gün"

        # Bu ay kapatılan
        now = datetime.now()
        kapali_ay = sum(1 for r in rows if r.get("Durum", "") in ("Kapalı", "Kapali") 
                       and (r.get("BaslangicTarihi", "") or "")[:7] == now.strftime("%Y-%m"))

        # Yinelenen
        cihaz_cnt = defaultdict(int)
        for r in rows:
            cihaz_cnt[r.get("Cihazid", "")] += 1
        yinelenen = sum(1 for c in cihaz_cnt.values() if c >= 2)

        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["acik"].setText(f"{acik} / {kritik}")
        self._kpi_labels["ort_sure"].setText(ort_sure)
        self._kpi_labels["kapali_ay"].setText(str(kapali_ay))
        self._kpi_labels["yinelenen"].setText(str(yinelenen))

    def _build_list_tab(self) -> QWidget:
        """Liste tabı."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(S.get("splitter", ""))
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([710, 350])

        layout.addWidget(splitter, 1)
        return tab

    def _build_left_panel(self) -> QWidget:
        """Sol Panel — Filtreler + Tablo."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filtre Bar
        filter_bar = QWidget()
        filter_bar.setStyleSheet(
            f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};border-bottom:1px solid {getattr(DarkTheme, 'BORDER', '#242938')};"
        )
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(10, 6, 10, 6)
        fb_layout.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍  Arıza No, Cihaz, Başlık…")
        self.txt_filter.setStyleSheet(S["input"])
        self.txt_filter.setMaximumWidth(220)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.txt_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setStyleSheet(S["combo"])
        self.cmb_durum_filter.setFixedWidth(160)
        self.cmb_durum_filter.addItem("Tüm Durumlar", None)
        self.cmb_durum_filter.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.cmb_durum_filter)

        self.cmb_oncelik_filter = QComboBox()
        self.cmb_oncelik_filter.setStyleSheet(S["combo"])
        self.cmb_oncelik_filter.setFixedWidth(150)
        for lbl, val in [("Tüm Öncelikler", None), ("Kritik", "Kritik"), 
                         ("Yüksek", "Yüksek"), ("Orta", "Orta"), ("Düşük", "Düşük")]:
            self.cmb_oncelik_filter.addItem(lbl, val)
        self.cmb_oncelik_filter.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.cmb_oncelik_filter)

        self.cmb_cihaz_filter = QComboBox()
        self.cmb_cihaz_filter.setStyleSheet(S["combo"])
        self.cmb_cihaz_filter.setFixedWidth(150)
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        self.cmb_cihaz_filter.currentIndexChanged.connect(self._apply_filters)
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))
        fb_layout.addWidget(self.cmb_cihaz_filter)

        fb_layout.addStretch()

        self.btn_yeni_ariza = QPushButton("+ Yeni Arıza")
        self.btn_yeni_ariza.setStyleSheet(S.get("btn_primary", ""))
        self.btn_yeni_ariza.clicked.connect(self._open_ariza_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni_ariza, "cihaz.write")
        fb_layout.addWidget(self.btn_yeni_ariza)

        layout.addWidget(filter_bar)

        # Tablo
        self._model = ArizaTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setStyleSheet(S["table"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for i, (_, _, w) in enumerate(ARIZA_COLUMNS):
            self.table.setColumnWidth(i, w)
        
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.Stretch)

        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.table, 1)

        # Sayaç
        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{getattr(DarkTheme, 'TEXT_MUTED', '#5a6278')};padding:4px 10px;"
            f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};border-top:1px solid {getattr(DarkTheme, 'BORDER', '#242938')};"
        )
        layout.addWidget(self.lbl_count)

        return panel

    def _build_right_panel(self) -> QWidget:
        """Sağ Panel — Detay + İşlem Penceresi."""
        from ui.pages.cihaz.forms.ariza_islem import ArizaIslemPenceresi
        
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};border-left:1px solid {getattr(DarkTheme, 'BORDER', '#242938')};"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Detay Header
        self._det_header = QWidget()
        self._det_header.setStyleSheet(
            f"background:{getattr(DarkTheme, 'PANEL', '#191d26')};border-bottom:1px solid {getattr(DarkTheme, 'BORDER', '#242938')};"
        )
        dh_layout = QVBoxLayout(self._det_header)
        dh_layout.setContentsMargins(14, 10, 14, 10)
        dh_layout.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir arıza seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{getattr(DarkTheme, 'TEXT_PRIMARY', '#eef0f5')};"
        )
        self.lbl_det_title.setWordWrap(True)
        dh_layout.addWidget(self.lbl_det_title)

        # Meta satırı
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.lbl_det_id = QLabel("—")
        self.lbl_det_tarih = QLabel("—")
        self.lbl_det_onc = QLabel("—")
        self.lbl_det_durum = QLabel("—")
        for w in [self.lbl_det_id, self.lbl_det_tarih, self.lbl_det_onc, self.lbl_det_durum]:
            w.setStyleSheet(f"font-size:11px;color:{getattr(DarkTheme, 'TEXT_MUTED', '#5a6278')};")
            meta_row.addWidget(w)
        meta_row.addStretch()
        dh_layout.addLayout(meta_row)

        layout.addWidget(self._det_header)

        # Aksiyon Çubuğu
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};border-bottom:1px solid {getattr(DarkTheme, 'BORDER', '#242938')};"
        )
        bb_layout = QHBoxLayout(btn_bar)
        bb_layout.setContentsMargins(10, 6, 10, 6)
        bb_layout.setSpacing(8)

        lbl_title = QLabel("İşlem Geçmişi")
        lbl_title.setStyleSheet(f"font-size:11px;font-weight:600;color:{getattr(DarkTheme, 'TEXT_SECONDARY', '#c8cdd8')};")
        bb_layout.addWidget(lbl_title)
        bb_layout.addStretch()

        self.btn_islem_ekle = QPushButton("+ İşlem Ekle")
        self.btn_islem_ekle.setStyleSheet(S.get("btn_secondary", S.get("btn_primary", "")))
        self.btn_islem_ekle.setEnabled(False)
        self.btn_islem_ekle.clicked.connect(self._open_islem_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_islem_ekle, "cihaz.write")
        bb_layout.addWidget(self.btn_islem_ekle)

        layout.addWidget(btn_bar)

        # İşlem Penceresi
        self.islem_penceresi = ArizaIslemPenceresi(self._db)
        layout.addWidget(self.islem_penceresi, 1)

        return panel

    # ══════════════════════════════════════════════════════
    #  VERİ & FİLTRELEME
    # ══════════════════════════════════════════════════════
    def _load_filter_combos(self):
        """Filtre combobox'larını yükle."""
        self.cmb_durum_filter.blockSignals(True)
        self.cmb_durum_filter.clear()
        self.cmb_durum_filter.addItem("Tüm Durumlar", None)
        if self._db:
            try:
                repo = RepositoryRegistry(self._db).get("Sabitler")
                for s in repo.get_all():
                    if s.get("Kod") == "Ariza_Durum":
                        me = s.get("MenuEleman", "")
                        if me:
                            self.cmb_durum_filter.addItem(me, me)
            except Exception as e:
                logger.error(f"Durum filtresi yüklenemedi: {e}")
        self.cmb_durum_filter.blockSignals(False)
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))

    def _load_data(self):
        """Arıza verilerini yükle."""
        if not self._db:
            self._all_rows = []
            self._rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._update_kpi()
            return
        try:
            repo = RepositoryRegistry(self._db).get("Cihaz_Ariza")
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid", "")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get("BaslangicTarihi") or ""), reverse=True)
            self._all_rows = rows
            self._refresh_cihaz_filter()
            self._update_kpi()
            self._apply_filters()
            if rows:
                self.table.selectRow(0)
        except Exception as e:
            logger.error(f"Arıza kayıtları yüklenemedi: {e}")
            self._all_rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")

    def _refresh_cihaz_filter(self):
        """Cihaz filtresini güncelle."""
        self.cmb_cihaz_filter.blockSignals(True)
        self.cmb_cihaz_filter.clear()
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        cihazlar = sorted({str(r.get("Cihazid", "")) for r in self._all_rows if r.get("Cihazid")})
        for c in cihazlar:
            self.cmb_cihaz_filter.addItem(c, c)
        self.cmb_cihaz_filter.blockSignals(False)

    def _apply_filters(self):
        """Filtreleri uygula."""
        filtered = list(self._all_rows)

        sel_durum = self.cmb_durum_filter.currentData()
        if sel_durum:
            filtered = [r for r in filtered if r.get("Durum", "") == sel_durum]

        sel_onc = self.cmb_oncelik_filter.currentData()
        if sel_onc:
            filtered = [r for r in filtered if r.get("Oncelik", "") == sel_onc]

        if not self._cihaz_id:
            sel_cihaz = self.cmb_cihaz_filter.currentData()
            if sel_cihaz:
                filtered = [r for r in filtered if str(r.get("Cihazid", "")) == sel_cihaz]

        txt = self.txt_filter.text().strip().lower()
        if txt:
            filtered = [r for r in filtered
                       if txt in str(r.get("Arizaid", "")).lower()
                       or txt in str(r.get("Cihazid", "")).lower()
                       or txt in str(r.get("Baslik", "")).lower()]

        self._rows = filtered
        self._model.set_rows(filtered)
        self.lbl_count.setText(f"{len(filtered)} kayıt")

    # ══════════════════════════════════════════════════════
    #  DETAY & FORM
    # ══════════════════════════════════════════════════════
    def _on_row_selected(self, current, _previous):
        """Satır seçilince."""
        if not current.isValid():
            return
        row = self._model.get_row(current.row())
        if not row:
            return
        ariza_id = row.get("Arizaid")
        self._selected_ariza_id = ariza_id
        self._update_detail(row)
        if ariza_id:
            self.islem_penceresi.set_ariza_id(ariza_id)
        self.btn_islem_ekle.setEnabled(bool(ariza_id))

    def _update_detail(self, row: Dict):
        """Detay panelini güncelle."""
        title = f"{row.get('Cihazid', '')}  —  {row.get('Baslik', '')}"
        self.lbl_det_title.setText(title)

        ariza_id = row.get("Arizaid", "")
        self.lbl_det_id.setText(f"#{ariza_id[-10:] if len(ariza_id) > 10 else ariza_id}")

        tarih = to_ui_date(row.get("BaslangicTarihi", ""), "")
        self.lbl_det_tarih.setText(f"📅 {tarih}")

        oncelik = row.get("Oncelik", "")
        onc_color = ONCELIK_COLOR.get(oncelik, getattr(DarkTheme, "TEXT_MUTED", "#5a6278"))
        self.lbl_det_onc.setText(oncelik or "—")
        self.lbl_det_onc.setStyleSheet(f"font-size:11px;font-weight:700;color:{onc_color};")

        durum = row.get("Durum", "")
        dur_color = DURUM_COLOR.get(durum, getattr(DarkTheme, "TEXT_MUTED", "#5a6278"))
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(f"font-size:11px;font-weight:700;color:{dur_color};")

    def _open_ariza_form(self):
        """Yeni arıza formu aç."""
        from ui.pages.cihaz.forms.ariza_girisi_form import ArizaGirisForm
        if self._action_guard and not self._action_guard.check_and_warn(self, "cihaz.write", "Ariza Kaydi"):
            return
        cihaz_id = self._cihaz_id
        form = ArizaGirisForm(self._db, cihaz_id=cihaz_id, action_guard=self._action_guard, parent=self)
        form.saved.connect(self._load_data)
        form.show()

    def _open_islem_form(self):
        """İşlem formu aç."""
        from ui.pages.cihaz.forms.ariza_islem import ArizaIslemForm
        if not self._selected_ariza_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir arıza seçin.")
            return
        form = ArizaIslemForm(self._db, ariza_id=self._selected_ariza_id, action_guard=self._action_guard, parent=self)
        form.saved.connect(self._load_data)
        form.show()

    def _on_tab_changed(self, idx: int):
        """Tab değişince."""
        if idx == 1:
            self._refresh_perf_tab()

    def _refresh_perf_tab(self):
        """Performans tabını güncelle (TODO)."""
        pass

    def _update_perf_tab_label(self):
        """Performans tab etiketini güncelle."""
        if hasattr(self, "_tabs"):
            label = "Arıza Geçmişi" if self._cihaz_id else "Cihaz Performansı"
            self._tabs.setTabText(1, label)

    # ══════════════════════════════════════════════════════
    #  PUBLIK METOTLAR
    # ══════════════════════════════════════════════════════
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        """Cihaz ID'sini ayarla."""
        self._cihaz_id = cihaz_id
        if cihaz_id:
            self._docs_dir = self._base_docs_dir / cihaz_id
            self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._load_filter_combos()
        self._load_data()
        self._update_perf_tab_label()
