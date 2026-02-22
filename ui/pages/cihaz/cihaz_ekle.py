# -*- coding: utf-8 -*-
"""Cihaz Ekle — v3 (Personel modulu mimarisi ile uyumlu)."""
import re
from typing import Any

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGroupBox, QGridLayout, QLineEdit,
    QComboBox, QDateEdit, QFileDialog, QMessageBox, QTabWidget
)

from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.pages.cihaz.components.cihaz_teknik_uts_scraper import CihazTeknikUtsScraper

C = DarkTheme


class CihazEklePage(QWidget):
    saved = Signal(dict)

    def __init__(self, db=None, on_saved=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._on_saved = on_saved

        self._fields: dict[str, Any] = {}
        self._abbr_maps = {
            "AnaBilimDali": {},
            "Cihaz_Tipi": {},
            "Kaynak": {},
        }
        self._next_seq = 1
        self._teknik_uts_panel = None
        self._uts_mode = False  # Cihaz kaydedildi, ÜTS bekliyor mu?

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
        header.setStyleSheet(f"background:{C.BG_SECONDARY}; border-bottom:1px solid {C.BORDER_PRIMARY};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)

        title = QLabel("Cihaz Ekle")
        title.setStyleSheet(f"font-size:14px; font-weight:700; color:{C.TEXT_PRIMARY}; background:transparent;")
        hl.addWidget(title)
        hl.addStretch()
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tabs", ""))
        root.addWidget(self._tabs, 1)

        # ── Tab 1: Cihaz bilgileri formu ──
        tab_form = QWidget()
        tab_form_lay = QVBoxLayout(tab_form)
        tab_form_lay.setContentsMargins(0, 0, 0, 0)
        tab_form_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S["scroll"])
        tab_form_lay.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)

        main = QVBoxLayout(content)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(16)
        form_grid.setVerticalSpacing(16)
        form_grid.setColumnStretch(0, 1)
        form_grid.setColumnStretch(1, 1)
        main.addLayout(form_grid)

        # 1. Medya ve Dosyalar grubu: Cihaz ID, Cihaz Tipi, Ana Bilim Dalı, Kaynak
        box_media = self._group_box("Medya ve Dosyalar")
        grid_media = QGridLayout()
        grid_media.setHorizontalSpacing(12)
        grid_media.setVerticalSpacing(10)

        self._add_line(grid_media, 0, 0, "Cihaz ID", "Cihazid", read_only=True)
        self._add_combo(grid_media, 0, 1, "Cihaz Tipi", "CihazTipi", "Cihaz_Tipi")
        self._add_combo(grid_media, 1, 0, "Ana Bilim Dali", "AnaBilimDali", "AnaBilimDali")
        self._add_combo(grid_media, 1, 1, "Kaynak", "Kaynak", "Kaynak")

        box_media.setLayout(grid_media)
        form_grid.addWidget(box_media, 0, 0)

        # 2. Kimlik Bilgileri grubu: Marka, Model, Seri No, Amaç, Birim, Bulunduğu Bina
        box_kimlik = self._group_box("Kimlik Bilgileri")
        grid_kimlik = QGridLayout()
        grid_kimlik.setHorizontalSpacing(12)
        grid_kimlik.setVerticalSpacing(10)

        self._add_combo(grid_kimlik, 0, 0, "Marka", "Marka", "Marka")
        self._add_line(grid_kimlik, 0, 1, "Model", "Model")
        self._add_line(grid_kimlik, 1, 0, "Seri No", "SeriNo")
        self._add_combo(grid_kimlik, 1, 1, "Amac", "Amac", "Amac")
        self._add_combo(grid_kimlik, 2, 0, "Birim", "Birim", "Birim")
        self._add_line(grid_kimlik, 2, 1, "Bulundugu Bina", "BulunduguBina")

        box_kimlik.setLayout(grid_kimlik)
        form_grid.addWidget(box_kimlik, 0, 1)

        # 3. NDK Lisans Bilgileri grubu
        box_lisans = self._group_box("NDK Lisans Bilgileri")
        grid_lisans = QGridLayout()
        grid_lisans.setHorizontalSpacing(12)
        grid_lisans.setVerticalSpacing(10)

        self._add_line(grid_lisans, 0, 0, "Lisans No", "NDKLisansNo")
        self._add_line(grid_lisans, 0, 1, "NDK Seri No", "NDKSeriNo")
        self._add_combo(grid_lisans, 1, 0, "Lisans Durum", "LisansDurum", "Lisans_Durum")
        self._add_date(grid_lisans, 1, 1, "Lisans Bitis", "BitisTarihi")
        self._add_line(grid_lisans, 2, 0, "Sorumlu", "Sorumlusu")
        self._add_line(grid_lisans, 2, 1, "RKS", "RKS")
        self._add_file(grid_lisans, 3, 0, "Lisans Belgesi", "NDKLisansBelgesi", colspan=2)

        box_lisans.setLayout(grid_lisans)
        form_grid.addWidget(box_lisans, 1, 0)

        # 4. Teknik Hizmetler grubu
        box_teknik = self._group_box("Teknik Hizmetler")
        grid_teknik = QGridLayout()
        grid_teknik.setHorizontalSpacing(12)
        grid_teknik.setVerticalSpacing(10)

        self._add_date(grid_teknik, 0, 0, "Hizmete Giris", "HizmeteGirisTarihi", colspan=2)
        self._add_combo(grid_teknik, 1, 0, "Garanti Durum", "GarantiDurumu", "Garanti_Durum")
        self._add_date(grid_teknik, 1, 1, "Garanti Bitis", "GarantiBitisTarihi")
        self._add_combo(grid_teknik, 2, 0, "Periyodik Bakim", "BakimDurum", "Bakim_Durum")
        self._add_combo(grid_teknik, 2, 1, "Kalibrasyon", "KalibrasyonGereklimi", "Kalibrasyon_Durum")

        box_teknik.setLayout(grid_teknik)
        form_grid.addWidget(box_teknik, 1, 1)

        main.addStretch()

        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet(f"background:{C.BG_SECONDARY}; border-top:1px solid {C.BORDER_PRIMARY};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 0, 16, 0)

        self.btn_clear = QPushButton("Temizle")
        self.btn_clear.setStyleSheet(S["btn_refresh"])
        self.btn_clear.clicked.connect(self._clear_form)
        fl.addWidget(self.btn_clear)

        fl.addStretch()

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setStyleSheet(S["action_btn"])
        IconRenderer.set_button_icon(self.btn_save, "save", color=C.BTN_PRIMARY_TEXT, size=16)
        self.btn_save.clicked.connect(self._save)
        fl.addWidget(self.btn_save)

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
        self._tabs.addTab(tab_uts, "ÜTS Sorgulama")

        root.addWidget(footer)

    def _group_box(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(S["group"])
        return box

    def _add_line(self, grid, row, col, label, key, read_only=False):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        edit = QLineEdit()
        edit.setStyleSheet(S["input"])
        edit.setReadOnly(read_only)
        self._fields[key] = edit
        grid.addWidget(lbl, row * 2, col)
        grid.addWidget(edit, row * 2 + 1, col)

    def _add_combo(self, grid, row, col, label, key, db_kodu):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        combo = QComboBox()
        combo.setStyleSheet(S["combo"])
        combo.setProperty("db_kodu", db_kodu)
        self._fields[key] = combo
        grid.addWidget(lbl, row * 2, col)
        grid.addWidget(combo, row * 2 + 1, col)

    def _add_date(self, grid, row, col, label, key, colspan=1):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        date = QDateEdit()
        date.setStyleSheet(S["date"])
        date.setCalendarPopup(True)
        date.setDisplayFormat("dd.MM.yyyy")
        date.setDate(QDate.currentDate())
        self._fields[key] = date
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(date, row * 2 + 1, col, 1, colspan)

    def _add_file(self, grid, row, col, label, key, colspan=1):
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
        if not self._db:
            return
        try:
            registry = RepositoryRegistry(self._db)
            sabitler = registry.get("Sabitler").get_all()

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
        try:
            registry = RepositoryRegistry(self._db)
            cihazlar = registry.get("Cihazlar").get_all()
            max_id = 0
            for row in cihazlar:
                cid = str(row.get("Cihazid", "")).strip()
                digits = re.sub(r"\D", "", cid)
                if digits:
                    num = int(digits)
                    if 0 < num < 900000 and num > max_id:
                        max_id = num
            return max_id + 1 if max_id else 1
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
        cihaz_id = self._get_text("Cihazid")
        marka = self._get_text("Marka")
        birim = self._get_text("Birim")

        if not cihaz_id or not marka or not birim:
            QMessageBox.warning(self, "Eksik", "Cihaz ID, Marka ve Birim zorunludur.")
            return

        data = self._collect_form_data()

        try:
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Cihazlar")

            repo.insert(data)
            
            # Cihaz başarıyla kaydedildi - ÜTS paneline cihaz_id ver
            if self._teknik_uts_panel is not None:
                self._teknik_uts_panel.cihaz_id = str(cihaz_id)
                logger.info(f"Cihaz kaydedildi: {cihaz_id}. ÜTS paneli aktif.")
            
            # Kaydet butonunu disable et (tekrar kaydetmesin)
            self.btn_save.setEnabled(False)
            self.btn_save.setText("✓ Kaydedildi")
            
            # ÜTS modunu aktif et (form kapanmasın)
            self._uts_mode = True
            
            # ÜTS sekmesine geç
            self._tabs.setCurrentIndex(1)
            
            # Kullanıcıya bilgi ver
            QMessageBox.information(
                self,
                "Cihaz Kaydedildi",
                f"Cihaz başarıyla kaydedildi: {cihaz_id}\n\n"
                "Şimdi 'ÜTS Sorgulama' sekmesinden teknik bilgileri ekleyebilirsiniz.\n\n"
                "Not: Form otomatik kapanmayacak. ÜTS bilgilerini ekledikten sonra "
                "formu manuel olarak kapatabilirsiniz."
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
        if self._uts_mode and callable(self._on_saved):
            # ÜTS işlemi tamamlandı, artık form'u kapatabiliriz
            logger.info("ÜTS işlemi tamamlandı, form kapatılıyor.")
            self._on_saved()
