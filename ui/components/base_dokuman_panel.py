"""
BaseDokumanPanel — Cihaz ve Personel belge panellerinin ortak tabanı.

Alt sınıflar sadece konfigürasyonu verir, 200+ satır UI/logic tekrarlanmaz.

Kullanım:
    class CihazDokumanPanel(BaseDokumanPanel):
        def __init__(self, cihaz_id, db=None, parent=None):
            super().__init__(
                entity_type  = "cihaz",
                entity_id    = cihaz_id,
                folder_name  = "Cihaz_Belgeler",
                doc_type     = "Cihaz_Belge",
                belge_tur_kod= "Cihaz_Belge_Tur",   # Sabitler'deki Kod değeri
                db=db, parent=parent,
            )
"""
import os
import subprocess
import platform
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QComboBox, QLineEdit,
    QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QColor

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from core.services.dokuman_service import DokumanService
from database.repository_registry import RepositoryRegistry

C = DarkTheme
_ACCENT   = getattr(C, "ACCENT",         "#4d9de0")
_TEXT_SEC = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_ERROR    = "#e05c5c"


class BaseDokumanPanel(QWidget):
    """
    Belge yükleme + listeleme paneli.

    Alt sınıfların override etmesi gereken bir şey yok;
    sadece __init__'te super().__init__(...) çağrılır.
    """

    saved = Signal()

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        folder_name: str,
        doc_type: str,
        belge_tur_kod: str,
        db=None,
        sabitler_cache=None,
        parent=None,
    ):
        """
        Args:
            entity_type:    "cihaz" | "personel" | "rke"
            entity_id:      Cihaz ID, TC no, EkipmanNo vb.
            folder_name:    Drive/local klasör adı ("Cihaz_Belgeler" vb.)
            doc_type:       Dokumanlar.DocType değeri ("Cihaz_Belge" vb.)
            belge_tur_kod:  Sabitler tablosundaki Kod değeri ("Cihaz_Belge_Tur")
            db:             SQLite bağlantısı
            sabitler_cache: Önceden yüklenmiş Sabitler listesi (opsiyonel)
        """
        super().__init__(parent)
        self._entity_type  = entity_type
        self._entity_id    = str(entity_id) if entity_id else ""
        self._folder_name  = folder_name
        self._doc_type     = doc_type
        self._belge_tur_kod = belge_tur_kod
        self._db           = db
        self._sabitler     = sabitler_cache or []
        self._dokumanlari  = []
        self._iliskili_id  = None
        self._iliskili_tip = None

        self._svc = DokumanService(db) if db else None

        self._setup_ui()
        self._load_belge_turleri()
        self._load_dokumanlari()

    # ──────────────────────────────────────────────────────────
    #  Public API  (dışarıdan çağrılan)
    # ──────────────────────────────────────────────────────────

    def set_entity_id(self, entity_id: str):
        """Entity ID'yi güncelle ve veriyi yenile (cihaz kaydedilince çağrılır)."""
        self._entity_id = str(entity_id) if entity_id else ""
        self._svc = DokumanService(self._db) if self._db else None
        if self._entity_id:
            self.setEnabled(True)
            self._load_dokumanlari()
        else:
            self._tablo.setRowCount(0)

    def load_data(self):
        """Belgeleri yeniden yükle."""
        self._load_dokumanlari()

    def set_related_record(self, iliskili_id=None, iliskili_tip=None):
        """Yeni yüklenecek belgeler için ilişkili kayıt bağlamı ayarlar."""
        self._iliskili_id = str(iliskili_id).strip() if iliskili_id else None
        self._iliskili_tip = str(iliskili_tip).strip() if iliskili_tip else None

    # Geriye dönük uyumluluk alias'ları
    def set_cihaz_id(self, cihaz_id: str):
        self.set_entity_id(cihaz_id)

    def set_embedded_mode(self, _embedded: bool):
        pass

    # ──────────────────────────────────────────────────────────
    #  UI kurulumu
    # ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Uyarı (entity_id yoksa)
        if not self._entity_id:
            warn = QLabel("Lütfen önce kaydı kaydedin")
            warn.setStyleSheet(
                f"color:{_ERROR}; font-size:12px;"
                f"background:rgba(224,92,92,.1);"
                f"border:1px solid rgba(224,92,92,.3);"
                f"border-radius:6px; padding:10px;"
            )
            root.addWidget(warn)

        # ── Yükleme formu ──────────────────────────────────────
        form = QFrame()
        form.setStyleSheet(
            "background:rgba(255,255,255,0.03);"
            "border:1px solid rgba(255,255,255,0.07);"
            "border-radius:8px;"
        )
        fl = QVBoxLayout(form)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        fl.addWidget(self._lbl("Belge Yükle", bold=True, color=_ACCENT, size=13))

        # Belge Türü + Seçilen Dosya + Dosya Seç Butonu (yan yana)
        r1 = QHBoxLayout()
        r1.setSpacing(10)
        
        # Belge Türü
        r1.addWidget(self._lbl("Belge Türü:", w=80))
        self._combo_tur = QComboBox()
        self._combo_tur.setStyleSheet(S.get("input_combo", ""))
        self._combo_tur.setMinimumHeight(30)
        r1.addWidget(self._combo_tur, 1)
        
        # Seçilen Dosya
        r1.addWidget(self._lbl("Seçilen Dosya:", w=90))
        self._inp_dosya = QLineEdit()
        self._inp_dosya.setPlaceholderText("Dosya seçilmedi...")
        self._inp_dosya.setReadOnly(True)
        self._inp_dosya.setStyleSheet(S.get("input_field", ""))
        self._inp_dosya.setMinimumHeight(30)
        r1.addWidget(self._inp_dosya, 2)
        
        # Dosya Seç Butonu
        btn_sec = QPushButton("Dosya Seç")
        btn_sec.setStyleSheet(S.get("btn_action", ""))
        btn_sec.setMinimumHeight(30)
        btn_sec.setMaximumWidth(120)
        btn_sec.clicked.connect(self._browse)
        r1.addWidget(btn_sec, 0)
        fl.addLayout(r1)

        # Açıklama + Yükle butonu (yan yana)
        r2 = QHBoxLayout()
        r2.setSpacing(10)
        r2.addWidget(self._lbl("Açıklama:", w=80))
        self._inp_aciklama = QLineEdit()
        self._inp_aciklama.setPlaceholderText("Belge hakkında notlar...")
        self._inp_aciklama.setStyleSheet(S.get("input_field", ""))
        self._inp_aciklama.setMinimumHeight(30)
        r2.addWidget(self._inp_aciklama, 2)
        
        self._btn_yukle = QPushButton("Belgeyi Yükle")
        self._btn_yukle.setStyleSheet(S.get("save_btn", ""))
        self._btn_yukle.setMinimumHeight(30)
        self._btn_yukle.setMaximumWidth(140)
        self._btn_yukle.clicked.connect(self._upload)
        r2.addWidget(self._btn_yukle, 0)
        fl.addLayout(r2)

        if not self._entity_id:
            form.setEnabled(False)

        root.addWidget(form)

        # ── Belgeler listesi ───────────────────────────────────
        root.addWidget(self._lbl("Yüklü Belgeler", bold=True, color=_ACCENT, size=12))

        self._tablo = QTableWidget()
        self._tablo.setColumnCount(4)
        self._tablo.setHorizontalHeaderLabels(
            ["Belge Türü", "Dosya Adı", "Açıklama", "Tarih"]
        )
        self._tablo.setStyleSheet(S.get("table", ""))
        self._tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tablo.setAlternatingRowColors(True)
        self._tablo.setMinimumHeight(200)
        hh = self._tablo.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tablo.doubleClicked.connect(self._ac)
        self._tablo.setToolTip("Dosyayı açmak için çift tıklayın")
        root.addWidget(self._tablo)

        root.addStretch()
        scroll.setWidget(content)
        main.addWidget(scroll)

    # ──────────────────────────────────────────────────────────
    #  Veri yükleme
    # ──────────────────────────────────────────────────────────

    def _load_belge_turleri(self):
        """Sabitler'den belge türlerini yükle."""
        default = ["Belge", "Rapor", "Sertifika", "Diğer"]
        try:
            if not self._db:
                self._combo_tur.addItems(default)
                return

            # Cache'den veya DB'den oku
            sabitler = self._sabitler
            if not sabitler:
                from core.di import get_cihaz_service as _cs_f; sabitler = _cs_f(self._db).get_sabitler()

            turleri = [
                s.get("MenuEleman", "")
                for s in sabitler
                if str(s.get("Kod", "")).strip() == self._belge_tur_kod
                and s.get("MenuEleman", "")
            ]

            if turleri:
                self._combo_tur.addItems(turleri)
                if "Diğer" not in turleri:
                    self._combo_tur.addItem("Diğer")
            else:
                self._combo_tur.addItems(default)
        except Exception as e:
            logger.warning(f"BaseDokumanPanel: belge türleri yüklenemedi: {e}")
            self._combo_tur.addItems(default)

    def _load_dokumanlari(self):
        """DB'den belgeleri yükle ve tabloya doldur."""
        self._tablo.setRowCount(0)
        if not self._svc or not self._entity_id:
            return

        try:
            self._dokumanlari = self._svc.get_belgeler(
                self._entity_type, self._entity_id
            )
        except Exception as e:
            logger.error(f"BaseDokumanPanel: belgeler yüklenemedi: {e}")
            return

        self._tablo.setRowCount(len(self._dokumanlari))
        for row, doc in enumerate(self._dokumanlari):
            tarih = doc.get("YuklenmeTarihi", "")
            try:
                tarih_str = datetime.fromisoformat(tarih).strftime("%d.%m.%Y %H:%M")
            except Exception:
                tarih_str = tarih[:16] if len(tarih) > 16 else tarih or "-"

            item_dosya = QTableWidgetItem(doc.get("DisplayName") or doc.get("Belge", ""))
            item_dosya.setToolTip("Çift tıklayarak dosyayı aç")
            item_dosya.setForeground(QColor(_ACCENT))

            self._tablo.setItem(row, 0, QTableWidgetItem(doc.get("BelgeTuru", "")))
            self._tablo.setItem(row, 1, item_dosya)
            self._tablo.setItem(row, 2, QTableWidgetItem(doc.get("BelgeAciklama", "") or "-"))
            self._tablo.setItem(row, 3, QTableWidgetItem(tarih_str))

    # ──────────────────────────────────────────────────────────
    #  Eventler
    # ──────────────────────────────────────────────────────────

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Belge Seç", "",
            "Belgeler (*.pdf *.doc *.docx *.xlsx *.xls *.jpg *.png *.txt);;Tüm Dosyalar (*.*)"
        )
        if path:
            self._inp_dosya.setText(path)

    def _upload(self):
        if not self._svc:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        file_path = self._inp_dosya.text().strip()
        belge_tur = self._combo_tur.currentText()
        aciklama  = self._inp_aciklama.text().strip()

        if not file_path:
            QMessageBox.warning(self, "Hata", "Lütfen bir dosya seçin.")
            return
        if not belge_tur or belge_tur == "Belge türü yok":
            QMessageBox.warning(self, "Hata", "Lütfen belge türü seçin.")
            return

        # ⚠️ DB'de entity gerçekten var mı kontrol et
        try:
            from core.di import get_registry; registry = get_registry(self._db)
            # entity_type'a göre tablo adını belirle
            table_name_map = {
                "personel": "Personel",
                "cihaz": "Cihaz",
                "rke": "RKE",
            }
            table_name = table_name_map.get(self._entity_type)
            if table_name:
                repo = registry.get(table_name)
                if repo:
                    existing = repo.get_by_id(self._entity_id)
                    if not existing:
                        QMessageBox.warning(
                            self, "Hata",
                            f"Bu {self._entity_type} kaydı henüz oluşturulmamış.\n\n"
                            f"Lütfen önce kaydı kaydediniz, sonra belge yükleyiniz."
                        )
                        return
        except Exception as e:
            logger.warning(f"BaseDokumanPanel: Entity DB kontrol hatası: {e}")
            # Kontrol başarısız olsa da devam et

        self._btn_yukle.setEnabled(False)
        self._btn_yukle.setText("Yükleniyor...")

        try:
            sonuc = self._svc.upload_and_save(
                file_path   = file_path,
                entity_type = self._entity_type,
                entity_id   = self._entity_id,
                belge_turu  = belge_tur,
                folder_name = self._folder_name,
                doc_type    = self._doc_type,
                aciklama    = aciklama,
                iliskili_id = self._iliskili_id,
                iliskili_tip= self._iliskili_tip,
            )

            if not sonuc["ok"]:
                QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{sonuc['error']}")
                return

            mod_text = "Drive'a yüklendi" if sonuc["mode"] == "drive" else "Yerel klasöre kaydedildi"
            self._inp_dosya.clear()
            self._inp_aciklama.clear()
            self._load_dokumanlari()

            if self._iliskili_tip == "Personel_Saglik_Takip" and self._iliskili_id:
                try:
                    from core.di import get_registry; registry = get_registry(self._db)
                    saglik_repo = registry.get("Personel_Saglik_Takip")
                    saglik_repo.update(self._iliskili_id, {
                        "RaporDosya": sonuc.get("drive_link") or sonuc.get("belge_adi") or ""
                    })
                except Exception as upd_err:
                    logger.warning(f"BaseDokumanPanel: RaporDosya güncellenemedi: {upd_err}")

            QMessageBox.information(self, "Başarılı", f"{belge_tur}\n{mod_text}.")
            self.saved.emit()

        except Exception as e:
            logger.error(f"BaseDokumanPanel: upload hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{e}")
        finally:
            self._btn_yukle.setEnabled(True)
            self._btn_yukle.setText("Belgeyi Yükle")

    def _ac(self, index):
        """Tabloda çift tıklanan dosyayı aç."""
        if index.column() != 1:
            return
        row = index.row()
        if row >= len(self._dokumanlari):
            return

        doc = self._dokumanlari[row]
        drive_link = doc.get("DrivePath", "")
        local_path = doc.get("LocalPath", "")

        try:
            if drive_link:
                QDesktopServices.openUrl(QUrl(drive_link))
                return

            if not local_path or not os.path.exists(local_path):
                QMessageBox.warning(
                    self, "Dosya Bulunamadı",
                    f"Dosya bulunamadı:\n{local_path}\n\nDosya silinmiş veya taşınmış olabilir."
                )
                return

            if platform.system() == "Windows":
                os.startfile(str(local_path))
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(local_path)])
            else:
                subprocess.run(["xdg-open", str(local_path)])

        except Exception as e:
            logger.error(f"BaseDokumanPanel: dosya açma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı:\n{e}")

    # ──────────────────────────────────────────────────────────
    #  Yardımcı
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _lbl(text, bold=False, color=None, size=11, w=None):
        lbl = QLabel(text)
        style = f"font-size:{size}px;"
        if bold:
            style += "font-weight:700;"
        if color:
            style += f"color:{color};"
        else:
            style += f"color:{_TEXT_SEC};"
        if w:
            style += f"min-width:{w}px;"
        lbl.setStyleSheet(style)
        return lbl
