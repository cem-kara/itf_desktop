# -*- coding: utf-8 -*-
"""RKE Raporlama Merkezi — Refactored Main Page."""
from typing import List, Dict, Optional
import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QRadioButton, QButtonGroup, QFrame, QSizePolicy, QApplication, QMessageBox,
)
from PySide6.QtGui import QColor, QCursor

from core.logger import logger
from ui.styles.colors import DarkTheme
from ui.styles.components import STYLES
from ui.pages.rke.models.rke_rapor_model import RaporTableModel, RAPOR_WIDTHS
from ui.pages.rke.services.rke_rapor_workers import RaporVeriYukleyici, RaporOlusturucuWorker


# ── STİL SABİTLERİ ─────────────────────────────────────────────────
_BG0 = DarkTheme.BG_PRIMARY
_BG1 = DarkTheme.BG_PRIMARY
_BG2 = DarkTheme.BG_SECONDARY
_BG3 = DarkTheme.BG_ELEVATED
_BD = DarkTheme.BORDER_PRIMARY
_BD2 = DarkTheme.BORDER_PRIMARY
_TX0 = DarkTheme.TEXT_PRIMARY
_TX1 = DarkTheme.TEXT_SECONDARY
_TX2 = DarkTheme.TEXT_MUTED
_RED = DarkTheme.STATUS_ERROR
_AMBER = DarkTheme.STATUS_WARNING
_GREEN = DarkTheme.STATUS_SUCCESS
_BLUE = DarkTheme.ACCENT
_CYAN = DarkTheme.ACCENT2
_PURP = DarkTheme.RKE_PURP
_MONO = DarkTheme.MONOSPACE

_S_COMBO = STYLES["input_combo"]
_S_TABLE = STYLES["table"]


# ══════════════════════════════════════════════════════════════════
#  ANA PENCERE
# ══════════════════════════════════════════════════════════════════
class RKERaporPage(QWidget):
    """RKE Raporlama Merkezi Sayfası."""
    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self.setWindowTitle("RKE Raporlama Merkezi")
        self.resize(1200, 820)
        self.setStyleSheet(f"background:{_BG1};color:{_TX0};")

        self.ham_veriler: List[Dict] = []
        self.filtrelenmis_veri: List[Dict] = []
        self._kpi: Dict[str, QLabel] = {}
        
        # Repository'leri hazırla
        self._registry = None
        self._rke_repo = None
        self._muayene_repo = None
        if self._db:
            try:
                from core.di import get_registry
                self._registry = get_registry(self._db)
                self._rke_repo = self._registry.get("RKE_List")
                self._muayene_repo = self._registry.get("RKE_Muayene")
            except Exception as e:
                logger.error(f"Repository başlatma hatası: {e}")

        self._setup_ui()

    # ─────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._mk_kpi_bar())
        root.addWidget(self._mk_control_panel())
        root.addWidget(self._mk_table_panel(), 1)

    # ─────────────────────────────────────────────────────────────
    #  KPI BAR
    # ─────────────────────────────────────────────────────────────
    def _mk_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{_BG1};border-bottom:1px solid {_BD};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)
        for key, title, val, color in [
            ("toplam", "TOPLAM KAYIT", "0", _BLUE),
            ("uygun", "KULLANIMA UYGUN", "0", _GREEN),
            ("uygun_d", "UYGUN DEĞİL", "0", _RED),
            ("hurda_a", "HURDA ADAYI", "0", _AMBER),
            ("kaynak", "FARKLI EKİPMAN", "0", _TX2),
        ]:
            hl.addWidget(self._mk_kpi_card(key, title, val, color), 1)
        return bar

    def _mk_kpi_card(self, key, title, val, color) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_BG1};")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet(f"background:{color};border:none;")
        content = QWidget()
        content.setStyleSheet(f"background:{_BG1};")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)
        lt = QLabel(title)
        lt.setStyleSheet(f"color:{_TX2};background:transparent;font-family:{_MONO};"
                         f"font-size:8px;font-weight:700;letter-spacing:2px;")
        lv = QLabel(val)
        lv.setStyleSheet(f"color:{color};background:transparent;font-family:{_MONO};"
                         f"font-size:20px;font-weight:700;")
        vl.addWidget(lt)
        vl.addWidget(lv)
        hl.addWidget(accent)
        hl.addWidget(content, 1)
        self._kpi[key] = lv
        return w

    # ─────────────────────────────────────────────────────────────
    #  KONTROL PANELİ
    # ─────────────────────────────────────────────────────────────
    def _mk_control_panel(self) -> QWidget:
        outer = QWidget()
        outer.setFixedHeight(110)
        outer.setStyleSheet(f"background:{_BG1};border-bottom:1px solid {_BD};")
        hl = QHBoxLayout(outer)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.setSpacing(20)

        # Rapor Türü
        sec_widget = QWidget()
        sec_widget.setStyleSheet("background:transparent;")
        sec_widget.setFixedWidth(280)
        sv = QVBoxLayout(sec_widget)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(6)
        sec_lbl = QLabel("RAPOR TÜRÜ")
        sec_lbl.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:8px;"
                              f"font-weight:700;letter-spacing:2px;")
        sv.addWidget(sec_lbl)

        rb_ss = (f"QRadioButton{{color:{_TX1};font-family:{_MONO};font-size:11px;padding:3px;}}"
                 f"QRadioButton::indicator{{width:14px;height:14px;border-radius:7px;"
                 f"border:2px solid {_BD2};background:{_BG3};}}"
                 f"QRadioButton::indicator:checked{{background:{_PURP};border-color:{_PURP};}}"
                 f"QRadioButton:hover{{color:{_TX0};}}")
        self.rb_genel = QRadioButton("A. Kontrol Raporu (Genel)")
        self.rb_genel.setChecked(True)
        self.rb_hurda = QRadioButton("B. Hurda (HEK) Raporu")
        self.rb_kisi = QRadioButton("C. Personel Bazlı Raporlar")
        self.bg = QButtonGroup(self)
        for rb in (self.rb_genel, self.rb_hurda, self.rb_kisi):
            rb.setStyleSheet(rb_ss)
            self.bg.addButton(rb)
            sv.addWidget(rb)
        self.bg.buttonClicked.connect(self.filtrele)
        hl.addWidget(sec_widget)

        # Dikey ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"background:{_BD};width:1px;")
        hl.addWidget(sep)

        # Filtreler
        fil_widget = QWidget()
        fil_widget.setStyleSheet("background:transparent;")
        fv = QVBoxLayout(fil_widget)
        fv.setContentsMargins(0, 0, 0, 0)
        fv.setSpacing(6)
        fil_lbl = QLabel("FİLTRELER")
        fil_lbl.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:8px;"
                              f"font-weight:700;letter-spacing:2px;")
        fv.addWidget(fil_lbl)
        fh = QHBoxLayout()
        fh.setSpacing(10)
        fh.setContentsMargins(0, 0, 0, 0)
        for attr, title, mw in [("cmb_abd", "ANA BİLİM DALI", 170),
                                 ("cmb_birim", "BİRİM", 160),
                                 ("cmb_tarih", "İŞLEM TARİHİ", 150)]:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.setContentsMargins(0, 0, 0, 0)
            l = QLabel(title)
            l.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:8px;font-weight:700;letter-spacing:1px;")
            w = QComboBox()
            w.setFixedHeight(28)
            w.setMinimumWidth(mw)
            w.setStyleSheet(_S_COMBO)
            col.addWidget(l)
            col.addWidget(w)
            fh.addLayout(col)
            setattr(self, attr, w)
        self.cmb_abd.currentIndexChanged.connect(self.abd_birim_degisti)
        self.cmb_birim.currentIndexChanged.connect(self.abd_birim_degisti)
        self.cmb_tarih.currentIndexChanged.connect(self.filtrele)
        fv.addLayout(fh)
        hl.addWidget(fil_widget, 1)

        # Ayraç
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"background:{_BD};width:1px;")
        hl.addWidget(sep2)

        # Butonlar
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(btn_widget)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(6)
        btn_lbl = QLabel("İŞLEMLER")
        btn_lbl.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:8px;"
                              f"font-weight:700;letter-spacing:2px;")
        bv.addWidget(btn_lbl)

        self.btn_yenile = QPushButton("⟳  VERİLERİ YENILE")
        self.btn_yenile.setFixedHeight(30)
        self.btn_yenile.setMinimumWidth(180)
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {_BD2};border-radius:5px;"
            f"color:{_TX1};font-family:{_MONO};font-size:9px;letter-spacing:1px;}}"
            f"QPushButton:hover{{color:{_TX0};border-color:{_TX1};}}")
        self.btn_yenile.clicked.connect(self.load_data)

        self.btn_olustur = QPushButton("📄  PDF RAPOR OLUŞTUR")
        self.btn_olustur.setObjectName("btn_kaydet")
        self.btn_olustur.setFixedHeight(30)
        self.btn_olustur.setMinimumWidth(180)
        self.btn_olustur.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_olustur.setStyleSheet(
            f"QPushButton{{background:{_RED};border:none;border-radius:5px;"
            f"color:#fff;font-family:{_MONO};font-size:9px;font-weight:800;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:#f06060;}}"
            f"QPushButton:disabled{{background:{_BD};color:{_TX2};}}")
        self.btn_olustur.clicked.connect(self.rapor_baslat)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_olustur, "cihaz.write")

        bv.addWidget(self.btn_yenile)
        bv.addWidget(self.btn_olustur)
        hl.addWidget(btn_widget)
        return outer

    # ─────────────────────────────────────────────────────────────
    #  TABLO PANELİ
    # ─────────────────────────────────────────────────────────────
    def _mk_table_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background:{_BG0};")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        self._rapor_model = RaporTableModel()
        self.tablo = QTableView()
        self.tablo.setModel(self._rapor_model)
        self.tablo.setStyleSheet(_S_TABLE)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        self.tablo.setSortingEnabled(True)
        hdr = self.tablo.horizontalHeader()
        for i, w in enumerate(RAPOR_WIDTHS):
            hdr.setSectionResizeMode(i, QHeaderView.Stretch if i == len(RAPOR_WIDTHS) - 1 else QHeaderView.Interactive)
            if i != len(RAPOR_WIDTHS) - 1:
                hdr.resizeSection(i, w)
        vl.addWidget(self.tablo, 1)

        foot = QWidget()
        foot.setFixedHeight(30)
        foot.setStyleSheet(f"background:{_BG1};border-top:1px solid {_BD};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(12, 0, 12, 0)
        self.lbl_durum = QLabel("")
        self.lbl_durum.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:9px;")
        self.lbl_sayi = QLabel("0 kayıt")
        self.lbl_sayi.setStyleSheet(f"color:{_TX2};font-family:{_MONO};font-size:9px;")
        fl.addWidget(self.lbl_durum)
        fl.addStretch()
        fl.addWidget(self.lbl_sayi)
        vl.addWidget(foot)
        return panel

    # ─────────────────────────────────────────────────────────────
    #  KPI GÜNCELLEME
    # ─────────────────────────────────────────────────────────────
    def _update_kpi(self, rows: List[Dict]):
        toplam = len(rows)
        uygun = sum(1 for r in rows if "Değil" not in r.get("Sonuc", "") and r.get("Sonuc", ""))
        uygun_d = sum(1 for r in rows if "Değil" in r.get("Sonuc", ""))
        kaynak = len({r.get("EkipmanNo", "") for r in rows})
        for k, v in [("toplam", toplam), ("uygun", uygun), ("uygun_d", uygun_d),
                     ("hurda_a", uygun_d), ("kaynak", kaynak)]:
            if k in self._kpi:
                self._kpi[k].setText(str(v))

    # ─────────────────────────────────────────────────────────────
    #  YARDIMCI FONKSIYONLAR
    # ─────────────────────────────────────────────────────────────
    def _tc(self, s: str) -> Optional[datetime.date]:
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except:
                continue
        return None

    # ─────────────────────────────────────────────────────────────
    #  MANTIK
    # ─────────────────────────────────────────────────────────────
    def load_data(self):
        """Veri yükleme metodu."""
        if not self._db or not self._rke_repo:
            QMessageBox.warning(self, "Bağlantı Yok", "Veritabanı bağlantısı kurulamadı.")
            return
        
        try:
            self.btn_olustur.setEnabled(False)
            self.btn_yenile.setText("⟳  YÜKLENİYOR...")
            self.lbl_durum.setText("Veriler yükleniyor...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.loader = RaporVeriYukleyici(self._rke_repo, self._muayene_repo)
            self.loader.veri_hazir.connect(self.veriler_geldi)
            self.loader.hata_olustu.connect(self._yukleme_hata)
            self.loader.finished.connect(self._yukle_bitti)
            self.loader.start()

        except Exception as e:
            logger.error(f"Veri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {e}")

    def _yukle_bitti(self):
        QApplication.restoreOverrideCursor()
        self.btn_olustur.setEnabled(True)
        self.btn_yenile.setText("⟳  VERİLERİ YENILE")
        self.lbl_durum.setText("")

    def _yukleme_hata(self, msg: str):
        logger.error(f"Veri yükleme hatası: {msg}")
        QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {msg}")

    def veriler_geldi(self, data, headers, abd_l, birim_l, tarih_l):
        self.ham_veriler = data
        for cmb, baslik, liste in [(self.cmb_abd, "Tüm Bölümler", abd_l),
                                    (self.cmb_birim, "Tüm Birimler", birim_l),
                                    (self.cmb_tarih, "Tüm Tarihler", tarih_l)]:
            cmb.blockSignals(True)
            cur = cmb.currentText()
            cmb.clear()
            cmb.addItem(baslik)
            cmb.addItems(liste)
            idx = cmb.findText(cur)
            cmb.setCurrentIndex(idx if idx >= 0 else 0)
            cmb.blockSignals(False)
        self.abd_birim_degisti()

    def abd_birim_degisti(self):
        fa = self.cmb_abd.currentText()
        fb = self.cmb_birim.currentText()
        t = set()
        for r in self.ham_veriler:
            if "Tüm" not in fa and r.get('ABD', '') != fa:
                continue
            if "Tüm" not in fb and r.get('Birim', '') != fb:
                continue
            if r.get('Tarih'):
                t.add(r['Tarih'])
        sirali = sorted(t, reverse=True, key=lambda x: self._tc(x) or datetime.date.min)
        self.cmb_tarih.blockSignals(True)
        self.cmb_tarih.clear()
        self.cmb_tarih.addItem("Tüm Tarihler")
        self.cmb_tarih.addItems(sirali)
        self.cmb_tarih.blockSignals(False)
        self.filtrele()

    def filtrele(self):
        fa = self.cmb_abd.currentText()
        fb = self.cmb_birim.currentText()
        ft = self.cmb_tarih.currentText()
        filtered = []
        for r in self.ham_veriler:
            if "Tüm" not in fa and r.get('ABD', '') != fa:
                continue
            if "Tüm" not in fb and r.get('Birim', '') != fb:
                continue
            if "Tüm" not in ft and r.get('Tarih', '') != ft:
                continue
            if self.rb_hurda.isChecked() and "Değil" not in r.get('Sonuc', ''):
                continue
            filtered.append(r)
        self.filtrelenmis_veri = filtered
        self._rapor_model.set_rows(filtered)
        self.lbl_sayi.setText(f"{len(filtered)} kayıt gösteriliyor")
        self._update_kpi(filtered)

    def rapor_baslat(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Rapor Oluşturma"
        ):
            return
        if not self.filtrelenmis_veri:
            QMessageBox.warning(self, "Uyarı", "Rapor alınacak veri yok.")
            return
        mod = 1
        if self.rb_hurda.isChecked():
            mod = 2
        elif self.rb_kisi.isChecked():
            mod = 3
        ozet = f"{self.cmb_abd.currentText()} – {self.cmb_birim.currentText()}"
        self.btn_olustur.setEnabled(False)
        self.btn_olustur.setText("İşleniyor...")
        self.lbl_durum.setText("PDF oluşturuluyor...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.worker = RaporOlusturucuWorker(mod, self.filtrelenmis_veri, {"ozet": ozet})
        self.worker.log_mesaji.connect(self.lbl_durum.setText)
        self.worker.islem_bitti.connect(self._rapor_tamam)
        self.worker.start()

    def _rapor_tamam(self):
        QApplication.restoreOverrideCursor()
        self.btn_olustur.setEnabled(True)
        self.btn_olustur.setText("📄  PDF RAPOR OLUŞTUR")
        QMessageBox.information(self, "Tamamlandı", "Rapor işlemleri tamamlandı.")
        self.lbl_durum.setText("Hazır.")

    def closeEvent(self, event):
        for a in ("loader", "worker"):
            t = getattr(self, a, None)
            if t and t.isRunning():
                t.quit()
                t.wait(500)
        event.accept()


# Main window alias
RKERaporPenceresi = RKERaporPage
