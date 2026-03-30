"""
nobet_birim_yonetim.py — NB_Birim yönetim ekranı (Admin Panel sekmesi)

Özellikler:
  - Birim listesi (tablo)
  - Yeni birim ekleme
  - Birim düzenleme
  - Aktif / Pasif toggle
  - Soft delete
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QLineEdit, QComboBox, QSpinBox, QMessageBox,
    QHeaderView,
)

from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors


# ══════════════════════════════════════════════════════════════
#  BİRİM EKLEME / DÜZENLEME DİALOGU
# ══════════════════════════════════════════════════════════════

class _BirimDialog(QDialog):
    """Birim ekle / düzenle formu."""

    TIPLER = ["radyoloji", "nükleer_tıp", "patoloji", "diğer"]

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self._kayit = kayit or {}
        self.setWindowTitle("Yeni Birim" if not kayit else "Birim Düzenle")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 24)

        def _satir(lbl_text, widget, zorunlu=False):
            row = QHBoxLayout()
            lbl = QLabel(lbl_text + (" *" if zorunlu else ""))
            lbl.setFixedWidth(110)
            lbl.setProperty("color-role", "primary")
            row.addWidget(lbl)
            row.addWidget(widget)
            lay.addLayout(row)
            return widget

        self._inp_adi = _satir("Birim Adı", QLineEdit(
            self._kayit.get("BirimAdi", "")), zorunlu=True)
        self._inp_adi.setPlaceholderText("ör: Acil Radyoloji")

        self._inp_kodu = _satir("Birim Kodu", QLineEdit(
            self._kayit.get("BirimKodu", "")))
        self._inp_kodu.setPlaceholderText("Boş bırakılırsa otomatik üretilir")

        self._cmb_tip = QComboBox()
        for t in self.TIPLER:
            self._cmb_tip.addItem(t)
        idx = self._cmb_tip.findText(self._kayit.get("BirimTipi", "radyoloji"))
        if idx >= 0:
            self._cmb_tip.setCurrentIndex(idx)
        _satir("Tür", self._cmb_tip)

        self._spn_sira = QSpinBox()
        self._spn_sira.setRange(1, 999)
        self._spn_sira.setValue(int(self._kayit.get("Sira", 99)))
        _satir("Sıra", self._spn_sira)

        self._inp_aciklama = _satir("Açıklama", QLineEdit(
            self._kayit.get("Aciklama", "")))
        self._inp_aciklama.setPlaceholderText("İsteğe bağlı")

        lay.addSpacing(8)

        # Zorunlu alan notu
        not_lbl = QLabel("* Zorunlu alan")
        not_lbl.setProperty("color-role", "muted")
        not_lbl.setStyleSheet("font-size: 11px;")
        lay.addWidget(not_lbl)

        lay.addSpacing(8)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.setFixedWidth(90)
        btn_iptal.clicked.connect(self.reject)
        btn_row.addWidget(btn_iptal)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        btn_kaydet.setFixedWidth(90)
        btn_kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(btn_kaydet)

        lay.addLayout(btn_row)

    def _kaydet(self):
        adi = self._inp_adi.text().strip()
        if not adi:
            QMessageBox.warning(self, "Uyarı", "Birim adı boş olamaz.")
            self._inp_adi.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "BirimAdi":  self._inp_adi.text().strip(),
            "BirimKodu": self._inp_kodu.text().strip().upper(),
            "BirimTipi": self._cmb_tip.currentText(),
            "Sira":      self._spn_sira.value(),
            "Aciklama":  self._inp_aciklama.text().strip(),
        }


# ══════════════════════════════════════════════════════════════
#  NÖBET BİRİMLERİ SAYFA
# ══════════════════════════════════════════════════════════════

class NobetBirimYonetimPage(QWidget):
    """Admin Panel > Nöbet Birimleri sekmesi."""

    SUTUNLAR = ["Birim Adı", "Kod", "Tür", "Sıra", "Durum"]

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setProperty("bg-role", "page")
        self._build()
        self._yukle()

    # ─── UI ──────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        # Başlık satırı
        hdr = QHBoxLayout()
        baslik = QLabel("Nöbet Birimleri")
        baslik.setProperty("style-role", "section-title")
        hdr.addWidget(baslik)

        aciklama = QLabel("— NB_Birim tablosu. Sabitler tablosundan bağımsız.")
        aciklama.setProperty("color-role", "muted")
        aciklama.setStyleSheet("font-size: 12px;")
        hdr.addWidget(aciklama)
        hdr.addStretch()

        self._btn_yeni = QPushButton("Yeni Birim")
        self._btn_yeni.setProperty("style-role", "action")
        self._btn_yeni.setFixedWidth(130)
        IconRenderer.set_button_icon(
            self._btn_yeni, "plus", color=IconColors.PRIMARY, size=14)
        self._btn_yeni.clicked.connect(self._yeni)
        hdr.addWidget(self._btn_yeni)
        lay.addLayout(hdr)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setProperty("bg-role", "elevated")
        lay.addWidget(sep)

        # Tablo
        self._tbl = QTableWidget(0, len(self.SUTUNLAR))
        self._tbl.setHorizontalHeaderLabels(self.SUTUNLAR)
        self._tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl.setColumnWidth(1, 120)
        self._tbl.setColumnWidth(2, 130)
        self._tbl.setColumnWidth(3, 60)
        self._tbl.setColumnWidth(4, 80)
        self._tbl.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.doubleClicked.connect(self._duzenle)
        self._tbl.selectionModel().selectionChanged.connect(
            self._secim_degisti)
        lay.addWidget(self._tbl, 1)

        # Alt butonlar
        alt = QHBoxLayout()

        self._btn_duzenle = QPushButton("Düzenle")
        self._btn_duzenle.setProperty("style-role", "secondary")
        self._btn_duzenle.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_duzenle, "edit", color=IconColors.MUTED, size=14)
        self._btn_duzenle.clicked.connect(self._duzenle)
        alt.addWidget(self._btn_duzenle)

        self._btn_toggle = QPushButton("Pasife Al")
        self._btn_toggle.setProperty("style-role", "secondary")
        self._btn_toggle.setEnabled(False)
        self._btn_toggle.clicked.connect(self._toggle)
        alt.addWidget(self._btn_toggle)

        self._btn_sil = QPushButton("Sil")
        self._btn_sil.setProperty("style-role", "danger")
        self._btn_sil.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_sil, "trash", color=IconColors.DANGER, size=14)
        self._btn_sil.clicked.connect(self._sil)
        alt.addWidget(self._btn_sil)

        alt.addStretch()

        self._lbl_durum = QLabel("")
        self._lbl_durum.setProperty("color-role", "muted")
        self._lbl_durum.setStyleSheet("font-size: 11px;")
        alt.addWidget(self._lbl_durum)

        lay.addLayout(alt)

    # ─── Veri ────────────────────────────────────────────────

    def _svc(self):
        try:
            from core.di import get_nb_birim_service
            return get_nb_birim_service(self._db)
        except Exception as e:
            logger.error(f"NbBirimService: {e}")
            return None

    def _yukle(self):
        svc = self._svc()
        if not svc:
            self._lbl_durum.setText("Servis bağlantısı kurulamadı")
            return
        try:
            sonuc = svc.get_birimler(sadece_aktif=False)
            birimler = sonuc.veri or [] if sonuc.basarili else []

            self._tbl.setRowCount(0)
            for b in birimler:
                ri  = self._tbl.rowCount()
                bid = b.get("BirimID", "")
                self._tbl.insertRow(ri)

                def _item(text, birim_id=bid):
                    itm = QTableWidgetItem(str(text))
                    itm.setData(Qt.ItemDataRole.UserRole, birim_id)
                    return itm

                self._tbl.setItem(ri, 0, _item(b.get("BirimAdi", "")))
                self._tbl.setItem(ri, 1, _item(b.get("BirimKodu", "")))
                self._tbl.setItem(ri, 2, _item(b.get("BirimTipi", "radyoloji")))
                self._tbl.setItem(ri, 3, _item(b.get("Sira", 99)))

                aktif       = int(b.get("Aktif", 1))
                durum_item  = _item("Aktif" if aktif else "Pasif")
                if not aktif:
                    durum_item.setForeground(QColor("#e85555"))
                self._tbl.setItem(ri, 4, durum_item)

            self._lbl_durum.setText(
                f"{len(birimler)} birim"
                + (f"  ({sum(1 for b in birimler if not int(b.get('Aktif',1)))} pasif)"
                   if any(not int(b.get("Aktif", 1)) for b in birimler) else "")
            )
        except Exception as e:
            logger.error(f"Birim yükleme: {e}")
            self._lbl_durum.setText(f"Yükleme hatası: {e}")

    def _secili_id(self) -> str:
        row = self._tbl.currentRow()
        if row < 0:
            return ""
        itm = self._tbl.item(row, 0)
        return itm.data(Qt.ItemDataRole.UserRole) if itm else ""

    def _secim_degisti(self):
        var = bool(self._secili_id())
        self._btn_duzenle.setEnabled(var)
        self._btn_toggle.setEnabled(var)
        self._btn_sil.setEnabled(var)
        # Toggle buton metni
        if var:
            row   = self._tbl.currentRow()
            aktif = (self._tbl.item(row, 4).text() == "Aktif"
                     if self._tbl.item(row, 4) else True)
            self._btn_toggle.setText("Pasife Al" if aktif else "Aktife Al")
            IconRenderer.set_button_icon(
                self._btn_toggle,
                "x" if aktif else "check",
                color=IconColors.MUTED if aktif else IconColors.SUCCESS,
                size=14,
            )

    # ─── Aksiyonlar ──────────────────────────────────────────

    def _yeni(self):
        dialog = _BirimDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        svc  = self._svc()
        veri = dialog.get_data()
        sonuc = svc.birim_ekle(
            birim_adi  = veri["BirimAdi"],
            birim_kodu = veri["BirimKodu"],
            birim_tipi = veri["BirimTipi"],
            sira       = veri["Sira"],
            aciklama   = veri["Aciklama"],
        )
        if sonuc.basarili:
            self._yukle()
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _duzenle(self):
        bid = self._secili_id()
        if not bid:
            return
        svc     = self._svc()
        kayit_s = svc.get_birim(bid)
        if not kayit_s.basarili:
            QMessageBox.critical(self, "Hata", "Birim bilgisi alınamadı.")
            return
        dialog = _BirimDialog(kayit=kayit_s.veri, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = svc.birim_guncelle(
            birim_id   = bid,
            birim_adi  = veri["BirimAdi"],
            birim_kodu = veri["BirimKodu"],
            birim_tipi = veri["BirimTipi"],
            sira       = veri["Sira"],
            aciklama   = veri["Aciklama"],
        )
        if sonuc.basarili:
            self._yukle()
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _toggle(self):
        bid = self._secili_id()
        if not bid:
            return
        svc   = self._svc()
        sonuc = svc.birim_aktif_toggle(bid)
        if sonuc.basarili:
            self._yukle()
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _sil(self):
        bid = self._secili_id()
        if not bid:
            return
        row = self._tbl.currentRow()
        adi = self._tbl.item(row, 0).text() if row >= 0 else ""
        cevap = QMessageBox.question(
            self, "Onay",
            f"'{adi}' birimi silinsin mi?\n\n"
            "Bağlı vardiya grubu yoksa silinir. "
            "Bu işlem geri alınabilir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        svc   = self._svc()
        sonuc = svc.birim_sil(bid)
        if sonuc.basarili:
            self._yukle()
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))
