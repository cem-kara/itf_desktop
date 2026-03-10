# -*- coding: utf-8 -*-
"""Cihaz Ekle — v3 (Personel modulu mimarisi ile uyumlu)."""
import re
from typing import Any, cast

from PySide6.QtCore import Qt, QDate, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QLineEdit,
    QComboBox, QDateEdit, QFileDialog, QMessageBox, QTabWidget, QGroupBox
)

from core.logger import logger
from core.di import get_cihaz_service as _get_cihaz_service
from core.di import get_dokuman_service
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.pages.cihaz.components.cihaz_teknik_uts_scraper import CihazTeknikUtsScraper
from ui.pages.cihaz.components.cihaz_dokuman_panel import CihazDokumanPanel

C = DarkTheme


class CihazEklePage(QWidget):
    saved = Signal(dict)
    canceled = Signal()

    def __init__(self, db=None, on_saved=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._svc = _get_cihaz_service(db) if db else None
        self._on_saved = on_saved
        self._action_guard = action_guard

        self._fields: dict[str, Any] = {}
        self._abbr_maps = {
            "AnaBilimDali": {},
            "Cihaz_Tipi": {},
            "Kaynak": {},
        }
        self._next_seq = 1
        self._teknik_uts_panel = None
        self._belgeler_panel = None
        self._uts_mode = False  # Cihaz kaydedildi, ÜTS bekliyor mu?
        self._dokuman_uploader = None

        self.setStyleSheet(S["page"])
        self._setup_ui()
        self._load_sabitler()

    # ─── UI ─────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(52)
        header.setProperty("bg-role", "panel")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        title = QLabel("Cihaz Ekle")
        title.setProperty("color-role", "primary")
        title.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        hl.addWidget(title)
        hl.addStretch()
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(cast(str, S.get("tabs", "") or ""))
        root.addWidget(self._tabs, 1)

        # Tab 1: Cihaz Bilgileri (Personel ekle gibi iki sütun)
        tab_form = QWidget()
        tab_form_lay = QVBoxLayout(tab_form)
        tab_form_lay.setContentsMargins(0, 0, 0, 0)
        tab_form_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(S["scroll"])
        tab_form_lay.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # Formu ortala (personel_ekle.py gibi)
        content_layout.addStretch()

        # Sol kolon: Medya ve Kimlik Bilgileri
        left = QWidget()
        left.setFixedWidth(500)
        left_col = QVBoxLayout(left)
        left_col.setSpacing(16)
        left_col.setContentsMargins(0, 0, 0, 0)

        # 1) Medya ve Dosyalar
        left_grp = QGroupBox("Medya ve Dosyalar")
        left_grp.setStyleSheet(S["group"])
        left_lay = QGridLayout(left_grp)
        left_lay.setSpacing(8)
        left_lay.setColumnStretch(0, 1)
        left_lay.setColumnStretch(1, 1)
        self._add_line(left_lay, 0, 0, "Cihaz ID", "Cihazid", read_only=True)
        self._add_combo(left_lay, 0, 1, "Cihaz Tipi", "CihazTipi", "Cihaz_Tipi")
        self._add_combo(left_lay, 1, 0, "Ana Bilim Dali", "AnaBilimDali", "AnaBilimDali")
        self._add_combo(left_lay, 1, 1, "Kaynak", "Kaynak", "Kaynak")
        left_col.addWidget(left_grp)

        # 2) Kimlik Bilgileri
        kimlik_grp = QGroupBox("Kimlik Bilgileri")
        kimlik_grp.setStyleSheet(S["group"])
        kimlik_lay = QGridLayout(kimlik_grp)
        kimlik_lay.setSpacing(8)
        kimlik_lay.setColumnStretch(0, 1)
        kimlik_lay.setColumnStretch(1, 1)
        self._add_combo(kimlik_lay, 0, 0, "Marka", "Marka", "Marka")
        self._add_line(kimlik_lay, 0, 1, "Model", "Model")
        self._add_line(kimlik_lay, 1, 0, "Seri No", "SeriNo")
        self._add_combo(kimlik_lay, 1, 1, "Amac", "Amac", "Amac")
        self._add_combo(kimlik_lay, 2, 0, "Birim", "Birim", "Birim")
        self._add_line(kimlik_lay, 2, 1, "Bulundugu Bina", "BulunduguBina")
        left_col.addWidget(kimlik_grp)
        left_col.addStretch()
        content_layout.addWidget(left, alignment=Qt.AlignmentFlag.AlignTop)

        # Sağ kolon: NDK + Teknik Hizmetler
        right = QWidget()
        right.setFixedWidth(600)
        right_lay = QVBoxLayout(right)
        right_lay.setSpacing(16)
        right_lay.setContentsMargins(0, 0, 0, 0)

        # NDK Lisans Bilgileri
        ndk_grp = QGroupBox("NDK Lisans Bilgileri")
        ndk_grp.setStyleSheet(S["group"])
        ndk_lay = QGridLayout(ndk_grp)
        ndk_lay.setSpacing(8)
        ndk_lay.setColumnStretch(0, 1)
        ndk_lay.setColumnStretch(1, 1)
        self._add_line(ndk_lay, 0, 0, "Lisans No", "NDKLisansNo")
        self._add_line(ndk_lay, 0, 1, "NDK Seri No", "NDKSeriNo")
        self._add_combo(ndk_lay, 1, 0, "Lisans Durum", "LisansDurum", "Lisans_Durum")
        self._add_date(ndk_lay, 1, 1, "Lisans Bitis", "BitisTarihi")
        self._add_line(ndk_lay, 2, 0, "Sorumlu", "Sorumlusu")
        self._add_line(ndk_lay, 2, 1, "RKS", "RKS")
        self._add_file(ndk_lay, 3, 0, "Lisans Belgesi", "NDKLisansBelgesi", colspan=2)
        right_lay.addWidget(ndk_grp)

        # Teknik Hizmetler
        teknik_grp = QGroupBox("Teknik Hizmetler")
        teknik_grp.setStyleSheet(S["group"])
        teknik_lay = QGridLayout(teknik_grp)
        teknik_lay.setSpacing(8)
        teknik_lay.setColumnStretch(0, 1)
        teknik_lay.setColumnStretch(1, 1)
        self._add_date(teknik_lay, 0, 0, "Hizmete Giris", "HizmeteGirisTarihi", colspan=2)
        self._add_combo(teknik_lay, 1, 0, "Garanti Durum", "GarantiDurumu", "Garanti_Durum")
        self._add_date(teknik_lay, 1, 1, "Garanti Bitis", "GarantiBitisTarihi")
        self._add_combo(teknik_lay, 2, 0, "Periyodik Bakim", "BakimDurum", "Bakim_Durum")
        self._add_combo(teknik_lay, 2, 1, "Kalibrasyon", "KalibrasyonGereklimi", "Kalibrasyon_Durum")
        right_lay.addWidget(teknik_grp)

        right_lay.addStretch()
        content_layout.addWidget(right)

        # Formu ortala
        content_layout.addStretch()

        # Tab 1 Footer: Kaydet & ÜTS Sorgula
        footer1 = QFrame()
        footer1.setFixedHeight(64)
        footer1.setProperty("bg-role", "panel")
        footer1.setProperty("border-role", "top")
        fl1 = QHBoxLayout(footer1)
        fl1.setContentsMargins(16, 0, 16, 0)
        fl1.addStretch()
        self.btn_save = QPushButton("Kaydet & ÜTS Sorgula")
        self.btn_save.setStyleSheet(S["action_btn"])
        IconRenderer.set_button_icon(self.btn_save, "save", color=C.BTN_PRIMARY_TEXT, size=16)
        self.btn_save.clicked.connect(self._save)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_save, "cihaz.write")
        fl1.addWidget(self.btn_save)
        # Temizle butonu
        btn_clear = QPushButton("Temizle")
        btn_clear.setStyleSheet(S["btn_refresh"])
        IconRenderer.set_button_icon(btn_clear, "refresh", color=C.TEXT_PRIMARY, size=14)
        btn_clear.clicked.connect(self._clear_form)
        fl1.addWidget(btn_clear)
        btn_cancel1 = QPushButton("İptal")
        btn_cancel1.setStyleSheet(S["btn_refresh"])
        btn_cancel1.clicked.connect(self.canceled.emit)
        fl1.addWidget(btn_cancel1)
        tab_form_lay.addWidget(footer1)
        self._tabs.addTab(tab_form, "Cihaz Bilgileri")

        # ── Tab 2: ÜTS Sorgulama ──
        tab_uts = QWidget()
        tab_uts_lay = QVBoxLayout(tab_uts)
        tab_uts_lay.setContentsMargins(0, 0, 0, 0)
        tab_uts_lay.setSpacing(0)

        self._teknik_uts_panel = CihazTeknikUtsScraper(cihaz_id="", db=self._db, parent=tab_uts)
        self._teknik_uts_panel.data_ready.connect(self._populate_uts_data)
        self._teknik_uts_panel.saved.connect(self._on_uts_completed)
        self._teknik_uts_panel.canceled.connect(self._on_uts_completed)
        tab_uts_lay.addWidget(self._teknik_uts_panel, 1)

        # Tab 2 Footer: Sadece "İptal"
        footer2 = QFrame()
        footer2.setFixedHeight(64)
        footer2.setProperty("bg-role", "panel")
        footer2.setProperty("border-role", "top")
        footer2.style().unpolish(footer2)
        footer2.style().polish(footer2)
        fl2 = QHBoxLayout(footer2)
        fl2.setContentsMargins(16, 0, 16, 0)
        fl2.addStretch()

        btn_uts_cancel = QPushButton("İptal")
        btn_uts_cancel.setStyleSheet(S["btn_refresh"])
        btn_uts_cancel.clicked.connect(self._cancel_uts)
        fl2.addWidget(btn_uts_cancel)

        tab_uts_lay.addWidget(footer2)
        self._tabs.addTab(tab_uts, "ÜTS Sorgulama")

        # ── Tab 3: Belgeler (Yükleme) ──
        tab_belgeler = QWidget()
        tab_belgeler_lay = QVBoxLayout(tab_belgeler)
        tab_belgeler_lay.setContentsMargins(0, 0, 0, 0)
        tab_belgeler_lay.setSpacing(0)

        self._belgeler_panel = CihazDokumanPanel(cihaz_id="", db=self._db, parent=tab_belgeler)
        self._belgeler_panel.saved.connect(self._on_belgeler_saved)
        tab_belgeler_lay.addWidget(self._belgeler_panel, 1)

        footer3 = QFrame()
        footer3.setFixedHeight(64)
        footer3.setProperty("bg-role", "panel")
        footer3.setProperty("border-role", "top")
        footer3.style().unpolish(footer3)
        footer3.style().polish(footer3)
        fl3 = QHBoxLayout(footer3)
        fl3.setContentsMargins(16, 0, 16, 0)
        fl3.addStretch()

        btn_belgeler_done = QPushButton("✓ Tamamla")
        btn_belgeler_done.setStyleSheet(S["save_btn"])
        btn_belgeler_done.clicked.connect(self._finish_belgeler)
        fl3.addWidget(btn_belgeler_done)

        tab_belgeler_lay.addWidget(footer3)
        self._tabs.addTab(tab_belgeler, "Belgeler")
        # Başlangıçta ÜTS ve Belgeler sekmelerini devre dışı bırak — cihaz kaydedilince etkinleşecek
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)

        root.addStretch()

    def _make_group_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        return grid

    def _add_line(self, grid, row, col, label, key, read_only=False):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        edit = QLineEdit()
        edit.setStyleSheet(S["input"])
        edit.setReadOnly(read_only)
        self._fields[key] = edit
        layout.addWidget(lbl)
        layout.addWidget(edit)
        grid.addWidget(container, row, col)

    def _add_combo(self, grid, row, col, label, key, db_kodu):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        combo = QComboBox()
        combo.setStyleSheet(S["combo"])
        combo.setProperty("db_kodu", db_kodu)
        self._fields[key] = combo
        layout.addWidget(lbl)
        layout.addWidget(combo)
        grid.addWidget(container, row, col)

    def _add_date(self, grid, row, col, label, key, colspan=1):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        date = QDateEdit()
        date.setStyleSheet(S["date"])
        date.setCalendarPopup(True)
        date.setDisplayFormat("dd.MM.yyyy")
        date.setDate(QDate.currentDate())
        self._fields[key] = date
        layout.addWidget(lbl)
        layout.addWidget(date)
        grid.addWidget(container, row, col, 1, colspan)

    def _add_file(self, grid, row, col, label, key, colspan=1):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        wrap = QHBoxLayout()
        line = QLineEdit()
        line.setStyleSheet(S["input"])
        btn = QPushButton("Sec")
        btn.setStyleSheet(S["btn_refresh"])
        btn.clicked.connect(lambda: self._pick_file(line))
        wrap.addWidget(line)
        wrap.addWidget(btn)
        container = QWidget()
        container.setLayout(wrap)
        self._fields[key] = line
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(container, row * 2 + 1, col, 1, colspan)

    def _pick_file(self, line: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Sec", "", "Tumu (*.*)")
        if path:
            line.setText(path)

    # ─── Veri yukleme ve cihaz no ──────────────────────

    def _load_sabitler(self):
        if not self._db or not self._svc:
            return
        try:
            sabitler = self._svc.get_sabitler()
            grouped: dict[str, list[str]] = {}
            for row in sabitler:
                kod = str(row.get("Kod", "")).strip()
                eleman = str(row.get("MenuEleman", "")).strip()
                aciklama = str(row.get("Aciklama", "")).strip()
                if not kod or not eleman:
                    continue
                grouped.setdefault(kod, []).append(eleman)
                if kod in self._abbr_maps and aciklama:
                    self._abbr_maps[kod][eleman] = aciklama

            for key, widget in self._fields.items():
                if isinstance(widget, QComboBox):
                    kod = widget.property("db_kodu")
                    if kod and kod in grouped:
                        widget.clear()
                        widget.addItem("")
                        widget.addItems(sorted(grouped[kod]))

            self._next_seq = self._calc_next_sequence()

            for key in ("AnaBilimDali", "CihazTipi", "Kaynak"):
                w = self._fields.get(key)
                if isinstance(w, QComboBox):
                    w.currentTextChanged.connect(self._update_cihaz_id)

            self._update_cihaz_id()

        except Exception as e:
            logger.error(f"CihazEkle sabitler yuklenemedi: {e}")

    def _calc_next_sequence(self) -> int:
        if not self._svc:
            return 1
        try:
            return self._svc.get_next_cihaz_sequence()
        except Exception as e:
            logger.debug(f"Cihaz ID hesaplama hatasi: {e}")
            return 1

    def _update_cihaz_id(self):
        abd = self._get_text("AnaBilimDali")
        tip = self._get_text("CihazTipi")
        kaynak = self._get_text("Kaynak")

        k_abd = self._abbr_maps.get("AnaBilimDali", {}).get(abd, "GEN")
        k_tip = self._abbr_maps.get("Cihaz_Tipi", {}).get(tip, "CHZ")
        k_kaynak = self._abbr_maps.get("Kaynak", {}).get(kaynak, "D")

        seq = str(self._next_seq).zfill(3)
        cihaz_id = f"{k_abd}-{k_tip}-{k_kaynak}-{seq}"
        self._set_text("Cihazid", cihaz_id)

    # ─── Save ──────────────────────────────────────────

    def _save(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Cihaz Kaydetme"
        ):
            return
        cihaz_id = self._get_text("Cihazid")
        marka = self._get_text("Marka")
        birim = self._get_text("Birim")

        if not cihaz_id or not marka or not birim:
            QMessageBox.warning(self, "Eksik", "Cihaz ID, Marka ve Birim zorunludur.")
            return

        data = self._collect_form_data()

        if not self._svc:
            QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı yok")
            return

        try:
            self._svc.cihaz_ekle(data)

            # --- NDK Lisans Belgesi dosyasını DokumanService ile yükle ---
            ndk_belge_path = self._get_value("NDKLisansBelgesi")
            if ndk_belge_path:
                try:
                    # Background uploader thread using DI-provided DokumanService
                    class _DokumanUploader(QThread):
                        finished = Signal(dict)
                        error = Signal(str)
                        def __init__(self, db, file_path, entity_id):
                            super().__init__()
                            self._db = db
                            self._file = file_path
                            self._eid = entity_id
                        def run(self):
                            try:
                                svc = get_dokuman_service(self._db)
                                res = svc.upload_and_save(
                                    file_path=self._file,
                                    entity_type="cihaz",
                                    entity_id=self._eid,
                                    belge_turu="NDK Lisansı",
                                    folder_name="Cihaz_Belgeler",
                                    doc_type="Cihaz_Belge",
                                    custom_name=None
                                )
                                self.finished.emit(res)
                            except Exception as e:
                                self.error.emit(str(e))

                    self._dokuman_uploader = _DokumanUploader(self._db, ndk_belge_path, cihaz_id)
                    def _on_upload_finished(res: dict):
                        if res.get("ok"):
                            logger.info(f"NDK Lisans Belgesi yüklendi (async): {res.get('belge_adi')}")
                        else:
                            logger.warning(f"NDK Lisans Belgesi yüklenemedi (async): {res.get('error')}")
                            QMessageBox.warning(self, "Belge Yükleme Hatası", f"NDK Lisans Belgesi yüklenemedi: {res.get('error')}")
                        self._dokuman_uploader = None

                    def _on_upload_error(msg: str):
                        logger.error(f"NDK belge async yükleme hatası: {msg}")
                        QMessageBox.warning(self, "Belge Yükleme Hatası", f"NDK Lisans Belgesi yüklenirken hata oluştu: {msg}")
                        self._dokuman_uploader = None

                    self._dokuman_uploader.finished.connect(_on_upload_finished)
                    self._dokuman_uploader.error.connect(_on_upload_error)
                    self._dokuman_uploader.start()
                except Exception as ex:
                    logger.error(f"NDK Lisans Belgesi upload thread başlatılamadı: {ex}")

            # Cihaz başarıyla kaydedildi - ÜTS paneline cihaz_id ver
            if self._teknik_uts_panel is not None:
                self._teknik_uts_panel.cihaz_id = str(cihaz_id)
                logger.info(f"Cihaz kaydedildi: {cihaz_id}. ÜTS paneli aktif.")
            
            # Belgeler panel'e de cihaz_id ver
            if self._belgeler_panel is not None:
                self._belgeler_panel.set_cihaz_id(str(cihaz_id))
                logger.info(f"Belgeler paneli aktif: {cihaz_id}")
            
            # Kaydet butonunu disable et (tekrar kaydetmesin)
            self.btn_save.setEnabled(False)
            self.btn_save.setText("✓ Kaydedildi")
            
            # ÜTS modunu aktif et (form kapanmasın)
            self._uts_mode = True
            
            # Sekmeleri etkinleştir: ÜTS ve Belgeler artık erişilebilir
            try:
                self._tabs.setTabEnabled(1, True)
                self._tabs.setTabEnabled(2, True)
            except Exception:
                pass

            # ÜTS sekmesine geç
            self._tabs.setCurrentIndex(1)
            
            # Kullanıcıya bilgi ver
            QMessageBox.information(
                self,
                "Cihaz Kaydedildi",
                f"Cihaz başarıyla kaydedildi: {cihaz_id}\n\n"
                "Şimdi 'ÜTS Sorgulama' sekmesinden teknik bilgileri ekleyebilirsiniz.\n\n"
                "'Belgeler' sekmesinden cihaz belgelerini yükleyebilirsiniz.\n\n"
                "Not: Form otomatik kapanmayacak."
            )

            # Signal emit et ama callback çağırma (form kapanmasın)
            self.saved.emit(data)
        except Exception as e:
            logger.error(f"Cihaz kaydetme hatasi: {e}")
            QMessageBox.critical(self, "Hata", f"Kaydetme hatasi: {e}")

    def _collect_form_data(self) -> dict:
        cols = [
            "Cihazid","CihazTipi","Marka","Model","Amac","Kaynak","SeriNo","NDKSeriNo",
            "HizmeteGirisTarihi","RKS","Sorumlusu","NDKLisansNo",
            "BitisTarihi","LisansDurum","AnaBilimDali","Birim",
            "BulunduguBina","GarantiDurumu","GarantiBitisTarihi",
            "KalibrasyonGereklimi","BakimDurum","NDKLisansBelgesi"
        ]

        out = {}
        for col in cols:
            out[col] = self._get_value(col)
        return out

    def _get_value(self, key: str):
        widget = self._fields.get(key)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QDateEdit):
            return widget.date().toString("yyyy-MM-dd")
        return ""

    def _get_text(self, key: str) -> str:
        widget = self._fields.get(key)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""

    def _set_text(self, key: str, value: str):
        widget = self._fields.get(key)
        if isinstance(widget, QLineEdit):
            widget.setText(value)

    def _populate_uts_data(self, data: dict):
        """
        ÜTS scraper'dan gelen veriyi form field'larına doldur.
        
        NOT: Form'da sadece temel cihaz bilgileri var (Marka, Model).
        Detaylı teknik bilgiler (Sinif, GmdnKod, Firma, etc.) Cihaz_Teknik
        tablosuna kaydedilir ve cihaz detay ekranında gösterilir.
        """
        logger.info(f"📥 ÜTS data populate başlıyor: {len(data)} alan")
        logger.debug(f"📋 Gelen alanlar: {list(data.keys())}")
        logger.debug(f"📝 Form field'ları: {list(self._fields.keys())}")
        
        # Form'da mevcut field'ları doldur
        field_mapping = {
            "Marka": "Marka",         # ÜTS → Form
            "Model": "Model",         # ÜTS → Form (versiyonModel → Model)
        }
        
        filled_count = 0
        for uts_field, form_field in field_mapping.items():
            if uts_field in data and data[uts_field]:
                value = str(data[uts_field]).strip()
                if value:
                    try:
                        # Combo'ysa özel işlem yap
                        widget = self._fields.get(form_field)
                        if isinstance(widget, QComboBox):
                            # Combo'da değer varsa seç, yoksa addItem yapma (Sabitler'den gelir)
                            index = widget.findText(value)
                            if index >= 0:
                                widget.setCurrentIndex(index)
                                filled_count += 1
                                logger.debug(f"  ✓ {form_field} (combo): {value}")
                            else:
                                logger.debug(f"  ⚠ {form_field} combo'da '{value}' bulunamadı")
                        else:
                            # LineEdit veya diğer
                            self._set_text(form_field, value)
                            filled_count += 1
                            logger.debug(f"  ✓ {form_field}: {value}")
                    except Exception as e:
                        logger.warning(f"  ✗ {form_field} doldurulamadı: {e}")
        
        if filled_count > 0:
            logger.info(f"✅ Form populate tamamlandı: {filled_count} alan dolduruldu")
            QMessageBox.information(
                self,
                "ÜTS Verisi Yüklendi",
                f"Temel bilgiler form'a aktarıldı ({filled_count} alan).\n\n"
                "Detaylı teknik bilgiler (Sınıf, GMDN, Firma, vb.) "
                "Cihaz_Teknik tablosuna kaydedildi.\n\n"
                "Cihaz kaydedildikten sonra 'Cihaz Merkez' ekranında "
                "'Teknik Bilgiler' sekmesinden görüntüleyebilirsiniz."
            )
        else:
            logger.warning("⚠ Form'a hiçbir alan aktarılamadı")

    def _clear_form(self):
        for widget in self._fields.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())

        self._next_seq = self._calc_next_sequence()
        self._update_cihaz_id()

    def _on_uts_completed(self):
        """ÜTS panelinden kaydet/iptal yapıldığında çalışır."""
        if self._uts_mode:
            logger.info("ÜTS işlemi tamamlandı, kullanıcıya belge yüklemek isteyip istemediği sorulacak.")
            yanit = QMessageBox.question(
                self,
                "Belgeler Yükleme",
                "Cihaz kaydı ve ÜTS işlemi tamamlandı. Şimdi belge yüklemek ister misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if yanit == QMessageBox.StandardButton.Yes:
                # Belgeler sekmesine yönlendir
                self._tabs.setCurrentIndex(2)
            # Form açık kalacak, kapanmayacak

    def _cancel_uts(self):
        """ÜTS panelinde İptal butonuna basıldığında."""
        reply = QMessageBox.question(
            self,
            "Operasyonu İptal Et",
            "Emin misiniz? Kaydedilen cihaz verisi kalmayacak.\n"
            "ÜTS sorgulması iptal edilecek.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Tab 1'e dön
            self._tabs.setCurrentIndex(0)
            
            # Formu temizle
            self._clear_form()
            
            # Belgeler panelini sıfırla
            if self._belgeler_panel is not None:
                self._belgeler_panel.set_cihaz_id("")
            
            # Kaydet butonunu enable et
            self.btn_save.setEnabled(True)
            self.btn_save.setText("Kaydet & ÜTS Sorgula")
            
            # Mode'u kapat
            self._uts_mode = False
            # Sekmeleri tekrar devre dışı bırak
            try:
                self._tabs.setTabEnabled(1, False)
                self._tabs.setTabEnabled(2, False)
            except Exception:
                pass
            
            logger.info("ÜTS işlemi iptal edildi.")

    def _on_belgeler_saved(self):
        """Belgeler panel'den belge başarıyla yüklendiğinde."""
        logger.info("Belge yüklenme işlemi tamamlandı.")

    def _finish_belgeler(self):
        """Belgeler tab'ında 'Tamamla' butonuna basıldığında."""
        logger.info("Belgeler yükleme işlemi tamamlandı, form kapatılıyor.")
        
        # Form kapatma callback'ini çağır
        if callable(self._on_saved):
            self._on_saved()
