# -*- coding: utf-8 -*-
import uuid
import os
import platform
import subprocess
from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QTableView, QHeaderView, QComboBox, QDateEdit, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QModelIndex, Signal, QUrl
from PySide6.QtGui import QCursor
from PySide6.QtGui import QDesktopServices

from core.logger import logger
from core.date_utils import to_ui_date, parse_date, to_db_date
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import DarkTheme as C, Colors
from ui.styles.components import STYLES as S

SAGLIK_COLUMNS = [
    ("MuayeneTarihi", "Muayene Tarihi", 120),
    ("MuayeneTuru", "Muayene Türü", 150),
    ("Sonuc", "Sonuç", 150),
    ("Aciklama", "Açıklama", 250),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol", 120),
    ("Rapor", "Rapor", 90),
]

class SaglikTableModel(BaseTableModel):
    """Sağlık takip kayıtları için tablo modeli (BaseTableModel extend'i)."""
    
    def __init__(self, data=None, parent=None):
        super().__init__(SAGLIK_COLUMNS, data, parent)

    def _display(self, key, row):
        """Hücre gösterim değeri - tarih kolonları özel formatlanır."""
        if key == "Rapor":
            return "Aç" if row.get("_RaporDoc") else "-"
        value = row.get(key, "")
        if "Tarihi" in key:
            return self._fmt_date(value, "-")
        return str(value) if value else ""

    def _align(self, key):
        """Hücre hizalama - tarihler ortada."""
        if "Tarihi" in key:
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

class PersonelSaglikPanel(QWidget):
    open_documents = Signal(str)

    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = personel_id
        self.saglik_records = []
        self._last_kayit_no = ""
        self._rapor_map = {}
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Sağlık Durum Özeti
        summary_group = QGroupBox("Sağlık Durum Özeti")
        summary_group.setStyleSheet(S["group"])
        summary_layout = QGridLayout(summary_group)
        summary_layout.setHorizontalSpacing(20)
        summary_layout.setVerticalSpacing(8)

        self.lbl_son_muayene = self._add_stat(summary_layout, 0, 0, "Son Muayene Tarihi")
        self.lbl_sonraki_muayene = self._add_stat(summary_layout, 0, 1, "Sonraki Muayene Tarihi")
        self.lbl_durum = self._add_stat(summary_layout, 0, 2, "Genel Sağlık Durumu")
        summary_layout.setColumnStretch(2, 1)

        self.btn_muayene_ekle = QPushButton("Muayene Ekle")
        self.btn_muayene_ekle.setStyleSheet(S["refresh_btn"])
        self.btn_muayene_ekle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_muayene_ekle.clicked.connect(self._show_entry_group)
        summary_layout.addWidget(self.btn_muayene_ekle, 0, 3, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_rapor_uyari = QLabel("")
        self.lbl_rapor_uyari.setStyleSheet(
            f"color: {Colors.RED_500}; font-size: 12px; font-weight: 600;"
            f"background: rgba(224,92,92,.10); border: 1px solid rgba(224,92,92,.30);"
            "border-radius: 6px; padding: 8px;"
        )
        self.lbl_rapor_uyari.setVisible(False)
        summary_layout.addWidget(self.lbl_rapor_uyari, 1, 0, 1, 4)
        main_layout.addWidget(summary_group)

        # 2. Muayene Girişi
        self.entry_group = QGroupBox("Muayene Girişi")
        self.entry_group.setStyleSheet(S["group"])
        entry_layout = QVBoxLayout(self.entry_group)
        entry_layout.setContentsMargins(12, 12, 12, 12)
        entry_layout.setSpacing(12)

        entry_top = QHBoxLayout()
        entry_top.addStretch()
        self.btn_muayene_kapat = QPushButton("Kapat")
        self.btn_muayene_kapat.setStyleSheet(S["cancel_btn"])
        self.btn_muayene_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_muayene_kapat.clicked.connect(self._hide_entry_group)
        entry_top.addWidget(self.btn_muayene_kapat)
        entry_layout.addLayout(entry_top)
        
        self._setup_entry_form(entry_layout)
        self.entry_group.setVisible(False)
        main_layout.addWidget(self.entry_group)

        # 3. Geçmiş Muayene Kayıtları
        history_group = QGroupBox("Geçmiş Muayene Kayıtları")
        history_group.setStyleSheet(S["group"])
        history_layout = QVBoxLayout(history_group)

        history_top = QHBoxLayout()
        history_top.addStretch()
        self.btn_secili_muayene_rapor = QPushButton("Seçili Muayeneye Rapor Yükle")
        self.btn_secili_muayene_rapor.setStyleSheet(S["refresh_btn"])
        self.btn_secili_muayene_rapor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_secili_muayene_rapor.clicked.connect(self._go_documents_for_selected)
        history_top.addWidget(self.btn_secili_muayene_rapor)
        history_layout.addLayout(history_top)

        self._table_model = SaglikTableModel()
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setStyleSheet(S["table"])
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.doubleClicked.connect(self._on_table_double_click)

        header = self._table_view.horizontalHeader()
        for i, col_info in enumerate(SAGLIK_COLUMNS):
            width = col_info[2]
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            self._table_view.setColumnWidth(i, width)
        header.setSectionResizeMode(len(SAGLIK_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)

        history_layout.addWidget(self._table_view)
        main_layout.addWidget(history_group, 1)

    def _setup_entry_form(self, layout):
        """Muayene giriş formu"""
        STATUS_OPTIONS = ["", "Uygun", "Şartlı Uygun", "Uygun Değil"]
        self._exam_widgets = {}
        
        # Form grid
        form_grid = QGridLayout()
        form_grid.setContentsMargins(0, 0, 0, 0)
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(10)
        
        # Başlıklar
        lbl_muayene_turu = QLabel("Muayene Türü")
        lbl_muayene_turu.setProperty("color-role", "muted")
        lbl_muayene_turu.setStyleSheet("font-weight: 600;")
        lbl_muayene_turu.style().unpolish(lbl_muayene_turu)
        lbl_muayene_turu.style().polish(lbl_muayene_turu)
        form_grid.addWidget(lbl_muayene_turu, 0, 0)
        
        lbl_tarih = QLabel("Tarih")
        lbl_tarih.setProperty("color-role", "muted")
        lbl_tarih.setStyleSheet("font-weight: 600;")
        lbl_tarih.style().unpolish(lbl_tarih)
        lbl_tarih.style().polish(lbl_tarih)
        form_grid.addWidget(lbl_tarih, 0, 1)
        
        lbl_durum = QLabel("Durum")
        lbl_durum.setProperty("color-role", "muted")
        lbl_durum.setStyleSheet("font-weight: 600;")
        lbl_durum.style().unpolish(lbl_durum)
        lbl_durum.style().polish(lbl_durum)
        form_grid.addWidget(lbl_durum, 0, 2)
        
        # Muayene türleri
        exams = [
            ("Dermatoloji", "Dermatoloji"),
            ("Dahiliye", "Dahiliye"),
            ("Goz", "Göz"),
            ("Goruntuleme", "Görüntüleme")
        ]
        
        for idx, (key, label) in enumerate(exams, start=1):
            # Label
            lbl = QLabel(label)
            lbl.setProperty("color-role", "primary")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            form_grid.addWidget(lbl, idx, 0)
            
            # Tarih
            de = QDateEdit(QDate.currentDate())
            de.setDisplayFormat("dd.MM.yyyy")
            de.setCalendarPopup(True)
            de.setMinimumHeight(32)
            de.setStyleSheet(S["date"])
            form_grid.addWidget(de, idx, 1)
            
            # Durum
            cmb = QComboBox()
            cmb.addItems(STATUS_OPTIONS)
            cmb.setMinimumHeight(32)
            cmb.setStyleSheet(S["combo"])
            form_grid.addWidget(cmb, idx, 2)
            
            self._exam_widgets[key] = {"tarih": de, "durum": cmb}
        
        layout.addLayout(form_grid)
        
        # Not alanı
        note_layout = QVBoxLayout()
        note_layout.setSpacing(4)
        lbl_not = QLabel("Açıklama")
        lbl_not.setProperty("color-role", "muted")
        lbl_not.style().unpolish(lbl_not)
        lbl_not.style().polish(lbl_not)
        note_layout.addWidget(lbl_not)
        self.inp_not = QLineEdit()
        self.inp_not.setStyleSheet(S["input"])
        self.inp_not.setPlaceholderText("Açıklama giriniz...")
        note_layout.addWidget(self.inp_not)
        layout.addLayout(note_layout)
        
        # Kaydet butonu
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_saglik_raporu = QPushButton("Sağlık Raporu Yükle")
        self.btn_saglik_raporu.setStyleSheet(S["refresh_btn"])
        self.btn_saglik_raporu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_saglik_raporu.clicked.connect(self._go_documents)
        btn_layout.addWidget(self.btn_saglik_raporu)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_kaydet)
        layout.addLayout(btn_layout)

    def _add_stat(self, grid, row, col, text):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(text)
        lbl_t.setProperty("color-role", "muted")
        lbl_t.setStyleSheet("font-size: 11px;")
        lbl_t.style().unpolish(lbl_t)
        lbl_t.style().polish(lbl_t)
        l.addWidget(lbl_t)
        
        val = QLabel("—")
        val.setProperty("color-role", "primary")
        val.setStyleSheet("font-size: 14px; font-weight: 500;")
        val.style().unpolish(val)
        val.style().polish(val)
        l.addWidget(val)
        
        grid.addWidget(container, row, col)
        return val

    def load_data(self):
        if not self.db or not self.personel_id: return
        try:
            from core.di import get_saglik_service as _sf
            repo = _sf(self.db)._r.get("Personel_Saglik_Takip")
            all_records = repo.get_all()
            
            self.saglik_records = [r for r in all_records if str(r.get("Personelid", "")).strip() == self.personel_id]
            self.saglik_records.sort(key=lambda x: x.get("MuayeneTarihi", ""), reverse=True)
            self._last_kayit_no = str(self.saglik_records[0].get("KayitNo", "")).strip() if self.saglik_records else ""

            # İlişkili rapor dokümanlarını eşle
            self._rapor_map = {}
            kayit_nolari = {
                str(r.get("KayitNo", "")).strip() for r in self.saglik_records if str(r.get("KayitNo", "")).strip()
            }
            if kayit_nolari:
                dokuman_repo = _sf(self.db)._r.get("Dokumanlar")
                docs = dokuman_repo.get_where({
                    "EntityType": "personel",
                    "EntityId": self.personel_id,
                })
                for doc in docs:
                    if str(doc.get("IliskiliBelgeTipi", "")).strip() != "Personel_Saglik_Takip":
                        continue
                    rel_id = str(doc.get("IliskiliBelgeID", "")).strip()
                    if rel_id in kayit_nolari and rel_id not in self._rapor_map:
                        self._rapor_map[rel_id] = doc

            for rec in self.saglik_records:
                rec["_RaporDoc"] = self._rapor_map.get(str(rec.get("KayitNo", "")).strip())
            
            self._update_ui()
        except Exception as e:
            logger.error(f"Personel sağlık verisi yükleme hatası ({self.personel_id}): {e}")
            self._clear_ui()

    def _update_ui(self):
        self._table_model.set_data(self.saglik_records)
        if self.saglik_records:
            latest_record = self.saglik_records[0]
            self.lbl_son_muayene.setText(to_ui_date(latest_record.get("MuayeneTarihi"), "—"))
            self.lbl_sonraki_muayene.setText(to_ui_date(latest_record.get("SonrakiKontrolTarihi"), "—"))
            self.lbl_durum.setText(latest_record.get("Sonuc", "Belirsiz"))

            raporsuz_sayi = sum(1 for rec in self.saglik_records if not rec.get("_RaporDoc"))
            if raporsuz_sayi > 0:
                self.lbl_rapor_uyari.setText(f"Sağlık raporu yüklenmemiş {raporsuz_sayi} adet muayene vardır.")
                self.lbl_rapor_uyari.setVisible(True)
            else:
                self.lbl_rapor_uyari.setVisible(False)
            
            next_check_date_str = latest_record.get("SonrakiKontrolTarihi")
            if next_check_date_str:
                try:
                    next_check_date = datetime.strptime(str(next_check_date_str).split(' ')[0], '%Y-%m-%d').date()
                    if next_check_date < date.today():
                        self.lbl_sonraki_muayene.setStyleSheet("font-size: 14px; font-weight: bold;")
                    else:
                        self.lbl_sonraki_muayene.setProperty("color-role", "primary")
                        self.lbl_sonraki_muayene.setStyleSheet("font-size: 14px; font-weight: 500;")
                        self.lbl_sonraki_muayene.style().unpolish(self.lbl_sonraki_muayene)
                        self.lbl_sonraki_muayene.style().polish(self.lbl_sonraki_muayene)
                except ValueError: pass
        else:
            self._clear_ui()

    def _clear_ui(self):
        self.lbl_son_muayene.setText("—")
        self.lbl_sonraki_muayene.setText("—")
        self.lbl_durum.setText("—")
        self.lbl_rapor_uyari.setVisible(False)
        self._table_model.set_data([])

    def _exam_date_if_set(self, key):
        """Durum seçildiyse tarih döndür, yoksa boş string."""
        w = self._exam_widgets[key]
        if not str(w["durum"].currentText()).strip():
            return ""
        return to_db_date(w["tarih"].date().toString("yyyy-MM-dd"))

    def _compute_summary(self):
        """Muayene verilerinden özet bilgi hesapla."""
        exam_keys = ["Dermatoloji", "Dahiliye", "Goz", "Goruntuleme"]
        exam_data = []
        
        for key in exam_keys:
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
            except ValueError:  # 29 Şubat durumu
                sonraki = d.replace(month=2, day=28, year=d.year + 1).isoformat()

        statuses = [s for _, s in exam_data if s]
        if "Uygun Değil" in statuses:
            sonuc = "Uygun Değil"
            durum = "Riskli"
        elif "Şartlı Uygun" in statuses:
            sonuc = "Şartlı Uygun"
            durum = "Gecerli"
        elif "Uygun" in statuses:
            sonuc = "Uygun"
            try:
                sonraki_date = parse_date(sonraki)
                if sonraki_date and sonraki_date < date.today():
                    durum = "Gecikmis"
                else:
                    durum = "Gecerli"
            except:
                durum = "Gecerli"
        else:
            sonuc = ""
            durum = "Planlandı"

        return latest, sonraki, sonuc, durum

    def _on_save(self):
        """Muayene kaydını kaydet."""
        if not self.db or not self.personel_id:
            return
            
        muayene_db, sonraki_db, sonuc, durum = self._compute_summary()
        
        if not sonuc:
            QMessageBox.warning(self, "Eksik Bilgi", "En az bir muayene sonucu girilmelidir.")
            return

        kritik_durum_var = any(
            str(self._exam_widgets[key]["durum"].currentText()).strip() in {"Şartlı Uygun", "Uygun Değil"}
            for key in self._exam_widgets
        )
        aciklama = self.inp_not.text().strip()
        if kritik_durum_var and not aciklama:
            QMessageBox.warning(self, "Eksik Bilgi", "Şartlı Uygun/Uygun Değil seçiminde açıklama zorunludur.")
            return

        kayit_no = uuid.uuid4().hex[:12].upper()
        
        # Personel verisini al
        try:
            from core.di import get_saglik_service as _sf
            personel_repo = _sf(self.db)._r.get("Personel")
            personel_data = personel_repo.get_by_id(self.personel_id)
            
            if not personel_data:
                QMessageBox.warning(self, "Hata", "Personel bilgisi bulunamadı.")
                return
                
            payload = {
                "KayitNo": kayit_no,
                "Personelid": self.personel_id,
                "AdSoyad": personel_data.get("AdSoyad", ""),
                "Birim": personel_data.get("GorevYeri", ""),
                "Yil": int(datetime.now().year),
                "MuayeneTarihi": muayene_db,
                "SonrakiKontrolTarihi": sonraki_db,
                "Sonuc": sonuc,
                "Durum": durum,
                "MuayeneTuru": sonuc,  # Özet muayene türü
                "Aciklama": aciklama,
                "DermatolojiMuayeneTarihi": self._exam_date_if_set("Dermatoloji"),
                "DermatolojiDurum": str(self._exam_widgets["Dermatoloji"]["durum"].currentText()).strip(),
                "DahiliyeMuayeneTarihi": self._exam_date_if_set("Dahiliye"),
                "DahiliyeDurum": str(self._exam_widgets["Dahiliye"]["durum"].currentText()).strip(),
                "GozMuayeneTarihi": self._exam_date_if_set("Goz"),
                "GozDurum": str(self._exam_widgets["Goz"]["durum"].currentText()).strip(),
                "GoruntulemeMuayeneTarihi": self._exam_date_if_set("Goruntuleme"),
                "GoruntulemeDurum": str(self._exam_widgets["Goruntuleme"]["durum"].currentText()).strip(),
                "RaporDosya": "",
                "Notlar": aciklama,
            }

            takip_repo = _sf(self.db)._r.get("Personel_Saglik_Takip")
            takip_repo.insert(payload)
            self._last_kayit_no = kayit_no

            # Ana personel tablosundaki özet bilgiyi de güncelle
            personel_sonuc = "uygun" if sonuc == "Uygun" else sonuc
            personel_repo.update(self.personel_id, {
                "MuayeneTarihi": muayene_db,
                "Sonuc": personel_sonuc,
            })

            QMessageBox.information(self, "Başarılı", "Muayene kaydı başarıyla eklendi.")
            
            # Formu temizle
            for key in self._exam_widgets:
                self._exam_widgets[key]["tarih"].setDate(QDate.currentDate())
                self._exam_widgets[key]["durum"].setCurrentIndex(0)
            self.inp_not.clear()
            
            # Verileri yeniden yükle
            self.load_data()

        except Exception as e:
            logger.error(f"Muayene kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata oluştu:\n{e}")

    def _show_entry_group(self):
        self.entry_group.setVisible(True)

    def _hide_entry_group(self):
        self.entry_group.setVisible(False)

    def _on_table_double_click(self, index):
        if not index.isValid():
            return
        if index.column() != len(SAGLIK_COLUMNS) - 1:
            return

        row = self._table_model.get_row(index.row()) if hasattr(self._table_model, "get_row") else None
        if not row:
            return

        doc = row.get("_RaporDoc")
        if not doc:
            QMessageBox.information(self, "Bilgi", "Bu kayıt için bağlı sağlık raporu bulunamadı.")
            return

        drive_link = str(doc.get("DrivePath", "")).strip()
        local_path = str(doc.get("LocalPath", "")).strip()

        try:
            if drive_link:
                QDesktopServices.openUrl(QUrl(drive_link))
                return

            if not local_path or not os.path.exists(local_path):
                QMessageBox.warning(self, "Dosya Bulunamadı", "Bağlı rapor dosyasına erişilemedi.")
                return

            if platform.system() == "Windows":
                os.startfile(str(local_path))
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(local_path)])
            else:
                subprocess.run(["xdg-open", str(local_path)])
        except Exception as e:
            logger.error(f"Sağlık raporu açma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Rapor açılamadı:\n{e}")

    def _go_documents(self):
        if not self._last_kayit_no:
            QMessageBox.warning(self, "Eksik Bilgi", "Önce muayene kaydı oluşturulmalı.")
            return
        self.open_documents.emit(self._last_kayit_no)

    def _go_documents_for_selected(self):
        selected = self._table_view.selectionModel().selectedRows() if self._table_view.selectionModel() else []
        if not selected:
            QMessageBox.information(self, "Bilgi", "Lütfen önce geçmiş tablosundan bir muayene kaydı seçin.")
            return

        row_index = selected[0].row()
        row_data = self._table_model.get_row(row_index) if hasattr(self._table_model, "get_row") else None
        kayit_no = str((row_data or {}).get("KayitNo", "")).strip()

        if not kayit_no:
            QMessageBox.warning(self, "Hata", "Seçili kaydın KayitNo bilgisi bulunamadı.")
            return

        self.open_documents.emit(kayit_no)

    def set_embedded_mode(self, mode):
        pass