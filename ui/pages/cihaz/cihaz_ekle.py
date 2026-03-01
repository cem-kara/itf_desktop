# -*- coding: utf-8 -*-
"""Cihaz Ekle — v3 (Personel modulu mimarisi ile uyumlu)."""
import re
from typing import Any

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QLineEdit,
    QComboBox, QDateEdit, QFileDialog, QMessageBox, QTabWidget, QGroupBox
)

from core.logger import logger
from database.repository_registry import RepositoryRegistry
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
        box_media, box_media_v = self._section_box("Medya ve Dosyalar")
        grid_media = self._make_group_grid()

        self._add_line(grid_media, 0, 0, "Cihaz ID", "Cihazid", read_only=True)
        self._add_combo(grid_media, 0, 1, "Cihaz Tipi", "CihazTipi", "Cihaz_Tipi")
        self._add_combo(grid_media, 1, 0, "Ana Bilim Dali", "AnaBilimDali", "AnaBilimDali")
        self._add_combo(grid_media, 1, 1, "Kaynak", "Kaynak", "Kaynak")

        box_media_v.addLayout(grid_media)
        form_grid.addWidget(box_media, 0, 0)

        # 2. Kimlik Bilgileri grubu: Marka, Model, Seri No, Amaç, Birim, Bulunduğu Bina
        box_kimlik, box_kimlik_v = self._section_box("Kimlik Bilgileri")
        grid_kimlik = self._make_group_grid()

        self._add_combo(grid_kimlik, 0, 0, "Marka", "Marka", "Marka")
        self._add_line(grid_kimlik, 0, 1, "Model", "Model")
        self._add_line(grid_kimlik, 1, 0, "Seri No", "SeriNo")
        self._add_combo(grid_kimlik, 1, 1, "Amac", "Amac", "Amac")
        self._add_combo(grid_kimlik, 2, 0, "Birim", "Birim", "Birim")
        self._add_line(grid_kimlik, 2, 1, "Bulundugu Bina", "BulunduguBina")

        box_kimlik_v.addLayout(grid_kimlik)
        form_grid.addWidget(box_kimlik, 0, 1)

        # 3. NDK Lisans Bilgileri grubu
        box_lisans, box_lisans_v = self._section_box("NDK Lisans Bilgileri")
        grid_lisans = self._make_group_grid()

        self._add_line(grid_lisans, 0, 0, "Lisans No", "NDKLisansNo")
        self._add_line(grid_lisans, 0, 1, "NDK Seri No", "NDKSeriNo")
        self._add_combo(grid_lisans, 1, 0, "Lisans Durum", "LisansDurum", "Lisans_Durum")
        self._add_date(grid_lisans, 1, 1, "Lisans Bitis", "BitisTarihi")
        self._add_line(grid_lisans, 2, 0, "Sorumlu", "Sorumlusu")
        self._add_line(grid_lisans, 2, 1, "RKS", "RKS")
        self._add_file(grid_lisans, 3, 0, "Lisans Belgesi", "NDKLisansBelgesi", colspan=2)

        box_lisans_v.addLayout(grid_lisans)
        form_grid.addWidget(box_lisans, 1, 0)

        # 4. Teknik Hizmetler grubu
        box_teknik, box_teknik_v = self._section_box("Teknik Hizmetler")
        grid_teknik = self._make_group_grid()

        self._add_date(grid_teknik, 0, 0, "Hizmete Giris", "HizmeteGirisTarihi", colspan=2)
        self._add_combo(grid_teknik, 1, 0, "Garanti Durum", "GarantiDurumu", "Garanti_Durum")
        self._add_date(grid_teknik, 1, 1, "Garanti Bitis", "GarantiBitisTarihi")
        self._add_combo(grid_teknik, 2, 0, "Periyodik Bakim", "BakimDurum", "Bakim_Durum")
        self._add_combo(grid_teknik, 2, 1, "Kalibrasyon", "KalibrasyonGereklimi", "Kalibrasyon_Durum")

        box_teknik_v.addLayout(grid_teknik)
        form_grid.addWidget(box_teknik, 1, 1)

        main.addStretch()

        # Tab 1 Footer: Sadece "Kaydet & ÜTS Sorgula"
        footer1 = QFrame()
        footer1.setFixedHeight(64)
        footer1.setStyleSheet(f"background:{C.BG_SECONDARY}; border-top:1px solid {C.BORDER_PRIMARY};")
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
        footer2.setStyleSheet(f"background:{C.BG_SECONDARY}; border-top:1px solid {C.BORDER_PRIMARY};")
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
        footer3.setStyleSheet(f"background:{C.BG_SECONDARY}; border-top:1px solid {C.BORDER_PRIMARY};")
        fl3 = QHBoxLayout(footer3)
        fl3.setContentsMargins(16, 0, 16, 0)
        fl3.addStretch()

        btn_belgeler_done = QPushButton("✓ Tamamla")
        btn_belgeler_done.setStyleSheet(S["save_btn"])
        btn_belgeler_done.clicked.connect(self._finish_belgeler)
        fl3.addWidget(btn_belgeler_done)

        tab_belgeler_lay.addWidget(footer3)
        self._tabs.addTab(tab_belgeler, "Belgeler")
        # NOT: Tab'ı başta disabled yapmıyoruz, bunu kullanıcı tıklayabilsin
        # Panel içinde cihaz_id check'i yapılacak

        root.addStretch()

    def _section_box(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        """QGroupBox tabanlı grup başlığı (Personel modülü ile uyumlu)."""
        box = QGroupBox(title)
        box.setStyleSheet(S["group"])
        vbox = QVBoxLayout(box)
        vbox.setContentsMargins(8, 12, 8, 8)
        vbox.setSpacing(8)
        return box, vbox

    def _make_group_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        return grid

    def _add_line(self, grid, row, col, label, key, read_only=False):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        edit = QLineEdit()
        edit.setStyleSheet(S["input"])
        edit.setReadOnly(read_only)
        self._fields[key] = edit
        grid.addWidget(lbl, row * 2, col)
        grid.addWidget(edit, row * 2 + 1, col)

    def _add_combo(self, grid, row, col, label, key, db_kodu):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        combo = QComboBox()
        combo.setStyleSheet(S["combo"])
        combo.setProperty("db_kodu", db_kodu)
        self._fields[key] = combo
        grid.addWidget(lbl, row * 2, col)
        grid.addWidget(combo, row * 2 + 1, col)

    def _add_date(self, grid, row, col, label, key, colspan=1):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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

        try:
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Cihazlar")

            repo.insert(data)
            
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
        if self._uts_mode and callable(self._on_saved):
            # ÜTS işlemi tamamlandı, artık form'u kapatabiliriz
            logger.info("ÜTS işlemi tamamlandı, form kapatılıyor.")
            self._on_saved()

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


