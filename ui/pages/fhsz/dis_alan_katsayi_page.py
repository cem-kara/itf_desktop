# ui/pages/fhsz/dis_alan_katsayi_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Katsayı Protokol Yönetim Sayfası

İşlevler:
  - Aktif protokolleri listele
  - Yeni protokol ekle (dialog)
  - Aktif protokolü pasife al
  - Tarihçeyi göster / gizle
"""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableView, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QDateEdit, QTextEdit, QDialogButtonBox,
    QAbstractItemView, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.pages.fhsz.dis_alan_katsayi_model import DisAlanKatsayiModel
from core.di import get_dis_alan_katsayi_service
from core.hata_yonetici import servis_calistir, bilgi_goster, hata_goster
from core.logger import logger


class DisAlanKatsayiPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db  = db
        self._svc = get_dis_alan_katsayi_service(db) if db else None
        self._tarihce_goster = False
        self._setup_ui()
        self._connect_signals()
        self._load_data()

    # =========================================================
    #  UI
    # =========================================================

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)

        # Üst bar
        top = QFrame()
        top.setProperty("bg-role", "panel")
        top.setMaximumHeight(56)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(12, 6, 12, 6)
        top_lay.setSpacing(12)

        lbl = QLabel("Katsayı Protokol Yönetimi")
        lbl.setProperty("style-role", "section-title")
        top_lay.addWidget(lbl)
        top_lay.addStretch()

        self.chk_tarihce = QCheckBox("Tarihçeyi Göster")
        self.chk_tarihce.setProperty("style-role", "info")
        top_lay.addWidget(self.chk_tarihce)

        root.addWidget(top)

        # Bilgi şeridi
        info = QLabel(
            "Katsayı = Ortalama Işın Süresi (dk) ÷ 60  |  "
            "Her AnaBilimDali + Birim ikilisi için ayrı protokol tanımlanır  |  "
            "Geçmiş protokoller tarihçe olarak korunur."
        )
        info.setProperty("style-role", "info")
        info.setWordWrap(True)
        root.addWidget(info)

        # Tablo
        self.model = DisAlanKatsayiModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setProperty("style-role", "table")
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.model.setup_columns(self.table)
        root.addWidget(self.table)

        # Alt butonlar
        btn_frame = QFrame()
        btn_frame.setProperty("bg-role", "panel")
        btn_frame.setMaximumHeight(50)
        btn_lay = QHBoxLayout(btn_frame)
        btn_lay.setContentsMargins(12, 6, 12, 6)
        btn_lay.setSpacing(10)

        self.btn_yeni = QPushButton("Yeni Protokol Ekle")
        self.btn_yeni.setProperty("style-role", "action")
        self.btn_yeni.setFixedHeight(34)
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color="#FFFFFF")

        self.btn_pasife_al = QPushButton("Pasife Al")
        self.btn_pasife_al.setProperty("style-role", "danger")
        self.btn_pasife_al.setFixedHeight(34)
        self.btn_pasife_al.setEnabled(False)

        self.btn_yenile = QPushButton("Yenile")
        self.btn_yenile.setProperty("style-role", "secondary")
        self.btn_yenile.setFixedHeight(34)
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color="#FFFFFF")

        btn_lay.addWidget(self.btn_yeni)
        btn_lay.addWidget(self.btn_pasife_al)
        btn_lay.addStretch()

        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("style-role", "info")
        btn_lay.addWidget(self.lbl_durum)

        btn_lay.addWidget(self.btn_yenile)
        root.addWidget(btn_frame)

    # =========================================================
    #  Sinyaller
    # =========================================================

    def _connect_signals(self):
        self.btn_yeni.clicked.connect(self._yeni_protokol)
        self.btn_pasife_al.clicked.connect(self._pasife_al)
        self.btn_yenile.clicked.connect(self._load_data)
        self.chk_tarihce.toggled.connect(self._tarihce_toggled)
        self.table.selectionModel().selectionChanged.connect(self._secim_degisti)

    # =========================================================
    #  Veri yükleme
    # =========================================================

    def _load_data(self):
        if not self._svc:
            self.lbl_durum.setText("Veritabanı bağlantısı yok")
            return
        try:
            sonuc = self._svc.get_tum_protokoller()
            if not sonuc.basarili:
                hata_goster(self, sonuc.mesaj)
                return
            tum = sonuc.veri or []
            if self._tarihce_goster:
                rows = tum
            else:
                rows = [r for r in tum if r.get("Aktif", 1)]
            self.model.set_data(rows)
            self.lbl_durum.setText(
                f"{len(rows)} protokol"
                + (f" ({len(tum) - len(rows)} pasif gizlendi)" if not self._tarihce_goster and tum else "")
            )
        except Exception as e:
            logger.error(f"KatsayiPage._load_data: {e}")
            self.lbl_durum.setText("Yükleme hatası")

    def _tarihce_toggled(self, checked):
        self._tarihce_goster = checked
        self._load_data()

    def _secim_degisti(self):
        secili = self._secili_satir()
        aktif = bool(secili and secili.get("Aktif", 0))
        self.btn_pasife_al.setEnabled(aktif)

    def _secili_satir(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.row_data(idx.row())

    # =========================================================
    #  Yeni Protokol
    # =========================================================

    def _yeni_protokol(self):
        dialog = _ProtokolDialog(self._svc, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

    # =========================================================
    #  Pasife Al
    # =========================================================

    def _pasife_al(self):
        satir = self._secili_satir()
        if not satir:
            return
        
        if not self._svc:
            hata_goster(self, "Servis bağlantısı kurulamadı.")
            return
        
        svc_instance = self._svc
        anabilim = satir.get("AnaBilimDali", "")
        birim    = satir.get("Birim", "")

        cevap = QMessageBox.question(
            self,
            "Pasife Al",
            f"<b>{anabilim} — {birim}</b> için aktif protokol pasife alınacak.\n\n"
            "Mevcut katsayı korunur, yeni kayıtlarda kullanılmaz.\n\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return

        servis_calistir(
            self, "KatsayiPage._pasife_al",
            lambda: svc_instance.protokol_pasife_al(anabilim, birim),
            basari_msg="Protokol pasife alındı."
        )
        self._load_data()


# ═══════════════════════════════════════════════════════════════
#  Yeni Protokol Dialog
# ═══════════════════════════════════════════════════════════════

class _ProtokolDialog(QDialog):
    def __init__(self, svc, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setWindowTitle("Yeni Katsayı Protokolü")
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Başlık
        baslik = QLabel("Yeni Katsayı Protokolü Ekle")
        baslik.setProperty("color-role", "primary")
        layout.addWidget(baslik)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_anabilim = QLineEdit()
        self.txt_anabilim.setPlaceholderText("ör: Ortopedi")
        form.addRow("AnaBilim Dalı *:", self.txt_anabilim)

        self.txt_birim = QLineEdit()
        self.txt_birim.setPlaceholderText("ör: Ameliyathane")
        form.addRow("Birim *:", self.txt_birim)

        self.spn_katsayi = QDoubleSpinBox()
        self.spn_katsayi.setRange(0.01, 1.00)
        self.spn_katsayi.setSingleStep(0.05)
        self.spn_katsayi.setDecimals(2)
        self.spn_katsayi.setValue(0.15)
        self.spn_katsayi.setToolTip("Katsayı = Ortalama Işın Süresi (dk) ÷ 60")
        form.addRow("Katsayı *:", self.spn_katsayi)

        self.spn_sure = QSpinBox()
        self.spn_sure.setRange(0, 480)
        self.spn_sure.setSuffix(" dk")
        self.spn_sure.setValue(30)
        form.addRow("Ort. İşlem Süresi:", self.spn_sure)

        self.txt_alan_tip = QLineEdit()
        self.txt_alan_tip.setPlaceholderText("ör: C-Kollu Skopi — Cerrahi Ekip")
        form.addRow("Alan Tip Açıklaması:", self.txt_alan_tip)

        self.txt_formul = QLineEdit()
        self.txt_formul.setPlaceholderText("ör: 30 dk × %30 ışın = 9 dk → 9/60 = 0.15")
        form.addRow("Formül Açıklaması:", self.txt_formul)

        self.txt_protokol_ref = QLineEdit()
        self.txt_protokol_ref.setPlaceholderText("ör: Protokol No / Uzman görüşü")
        form.addRow("Protokol Referansı:", self.txt_protokol_ref)

        self.dte_baslangic = QDateEdit()
        self.dte_baslangic.setCalendarPopup(True)
        self.dte_baslangic.setDate(QDate.currentDate())
        self.dte_baslangic.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Geçerlilik Başlangıcı *:", self.dte_baslangic)

        layout.addLayout(form)

        # Uyarı
        uyari = QLabel(
            "⚠  Aynı birim için mevcut aktif protokol varsa önce pasife alınmalıdır."
        )
        uyari.setProperty("color-role", "primary")
        uyari.setWordWrap(True)
        layout.addWidget(uyari)

        # Butonlar
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Kaydet")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")
        btns.accepted.connect(self._kaydet)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _kaydet(self):
        anabilim = self.txt_anabilim.text().strip()
        birim    = self.txt_birim.text().strip()

        if not anabilim or not birim:
            QMessageBox.warning(self, "Eksik Alan", "AnaBilim Dalı ve Birim zorunludur.")
            return

        veri = {
            "AnaBilimDali":        anabilim,
            "Birim":               birim,
            "Katsayi":             self.spn_katsayi.value(),
            "OrtSureDk":           self.spn_sure.value(),
            "AlanTipAciklama":     self.txt_alan_tip.text().strip(),
            "AciklamaFormul":      self.txt_formul.text().strip(),
            "ProtokolRef":         self.txt_protokol_ref.text().strip(),
            "GecerlilikBaslangic": self.dte_baslangic.date().toString("yyyy-MM-dd"),
            "GecerlilikBitis":     None,
            "Aktif":               1,
        }

        if not self._svc:
            hata_goster(self, "Servis bağlantısı kurulamadı.")
            return

        svc_instance = self._svc

        sonuc = svc_instance.protokol_ekle(veri)
        if sonuc.basarili:
            bilgi_goster(self, "Protokol eklendi.")
            self.accept()
        else:
            hata_goster(self, sonuc.mesaj)
