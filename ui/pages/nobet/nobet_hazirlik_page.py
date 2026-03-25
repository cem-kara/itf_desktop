# -*- coding: utf-8 -*-
"""
nobet_hazirlik_page.py — Nöbet Ön Hazırlık

Nöbet planı oluşturmadan ÖNCE bakılması gereken ekran.

Sekmeler:
  1. Personel Durumu   — hedef saat, FM isteği, önceki devir bakiyesi, uyarılar
  2. İzin Takvimi      — ay içinde hangi günler kaç kişi izinli (takvim + sayı)
  3. Kapasite Analizi  — birim ihtiyacı vs personel hedefi karşılaştırması
  4. Uyarılar & Notlar — önemli durumların özeti

Aksiyonlar:
  - FM Gönüllü ve HedefTipi buradan düzenlenebilir
  - PDF çıktısı alınabilir
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QComboBox as QCmb,
    QSplitter, QScrollArea, QGridLayout,
)

from core.di import get_registry
from core.logger import logger

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
_GUN = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]

ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}

HEDEF_GUNLUK = {
    "normal":  7.0, "emzirme": 5.5, "sendika": 6.2,
    "sua":     0.0, "rapor":   7.0, "yillik":  7.0, "idari": 7.0,
}
HEDEF_TIPLER = [
    ("normal","Normal  (7.0 s/gün)"), ("emzirme","Emzirme (5.5 s/gün)"),
    ("sendika","Sendika (6.2 s/gün)"), ("sua","Şua İzni (0 s/gün)"),
    ("rapor","Raporlu (7.0 s/gün)"), ("yillik","Yıllık İzin (7.0 s/gün)"),
    ("idari","İdari İzin (7.0 s/gün)"),
]

DEVIR_ESIK = 14.0   # saat — bu eşiğin üstü uyarı (≈2 nöbet)
FM_ESIK    = 7.0    # saat


def _networkdays(bas: date, bit: date, tatiller: set) -> int:
    if bas > bit: return 0
    sayi, g = 0, bas
    while g <= bit:
        if g.weekday() < 5 and g.isoformat() not in tatiller:
            sayi += 1
        g += timedelta(days=1)
    return sayi


def _tatil_set(yil: int, ay: int, reg) -> set:
    try:
        rows   = reg.get("Tatiller").get_all() or []
        ay_bas = f"{yil:04d}-{ay:02d}-01"
        ay_bit = f"{yil:04d}-{ay:02d}-31"
        return {
            str(r.get("Tarih",""))
            for r in rows
            if ay_bas <= str(r.get("Tarih","")) <= ay_bit
            and str(r.get("TatilTuru","Resmi")) in ("Resmi","DiniBayram")
        }
    except Exception:
        return set()


def _hedef_tipi(pid: str, birim_id: str, yil: int, ay: int, reg) -> str:
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next(
            (r for r in rows
             if str(r.get("PersonelID","")) == pid
             and str(r.get("BirimID","")) == birim_id
             and int(r.get("Yil",0)) == yil
             and int(r.get("Ay",0)) == ay),
            None)
        return str((k or {}).get("HedefTipi","normal")).lower()
    except Exception:
        return "normal"


def _fm_gonullu(pid: str, birim_id: str, yil: int, ay: int, reg) -> bool:
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next(
            (r for r in rows
             if str(r.get("PersonelID","")) == pid
             and str(r.get("BirimID","")) == birim_id
             and int(r.get("Yil",0)) == yil
             and int(r.get("Ay",0)) == ay),
            None)
        return str((k or {}).get("NobetTercihi","")) == "fazla_mesai_gonullu"
    except Exception:
        return False


def _hedef_saat(pid: str, birim_id: str, yil: int, ay: int, reg) -> float:
    try:
        tatil  = _tatil_set(yil, ay, reg)
        ay_bas = date(yil, ay, 1)
        ay_bit = date(yil, ay, monthrange(yil, ay)[1])
        ay_is  = _networkdays(ay_bas, ay_bit, tatil)
        tip    = _hedef_tipi(pid, birim_id, yil, ay, reg)
        gun_s  = HEDEF_GUNLUK.get(tip, 7.0)
        rows   = reg.get("Izin_Giris").get_all() or []
        izin_is = 0
        for r in rows:
            if str(r.get("Personelid","")).strip() != str(pid).strip():
                continue
            if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR:
                continue
            try:
                bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                bit = date.fromisoformat(str(r.get("BitisTarihi","")))
            except Exception:
                continue
            izin_is += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
        return round(max(0, ay_is - izin_is) * gun_s, 1)
    except Exception:
        return round(20 * 7.0, 1)


def _it(text: str, pid: str = "") -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setData(Qt.ItemDataRole.UserRole, pid)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


def _simdi() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


# ══════════════════════════════════════════════════════════════
#  Tercih Düzenleme Dialogu
# ══════════════════════════════════════════════════════════════

class _TercihDialog(QDialog):
    def __init__(self, pid: str, ad: str, yil: int, ay: int,
                 kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Tercih Düzenle — {ad}")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(QLabel(
            f"<b>{ad}</b>  —  {_AY[ay]} {yil}"))
        form = QFormLayout()
        self._chk_fm = QCheckBox("FM Gönüllüsü")
        self._chk_fm.setChecked(
            (kayit or {}).get("NobetTercihi","") == "fazla_mesai_gonullu")
        form.addRow("Fazla Mesai:", self._chk_fm)
        self._cmb = QComboBox()
        for val, lbl in HEDEF_TIPLER:
            self._cmb.addItem(lbl, userData=val)
        mevcut = (kayit or {}).get("HedefTipi","normal")
        idx = next((i for i,(v,_) in enumerate(HEDEF_TIPLER) if v==mevcut), 0)
        self._cmb.setCurrentIndex(idx)
        form.addRow("Hedef Tipi:", self._cmb)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "NobetTercihi": ("fazla_mesai_gonullu"
                             if self._chk_fm.isChecked() else "zorunlu"),
            "HedefTipi": self._cmb.currentData(),
        }


# ══════════════════════════════════════════════════════════════
#  Ana Sayfa
# ══════════════════════════════════════════════════════════════

class NobetHazirlikPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db        = db
        self._yil       = date.today().year
        self._ay        = date.today().month
        self._birim_id  = ""
        self._birim_adi = ""
        self.setProperty("bg-role", "page")
        self._build()
        if db:
            self._birimleri_doldur()
            self._yukle()

    def _reg(self):
        return get_registry(self._db)

    # ──────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_personel_tab(),  "Personel Durumu")
        self._tabs.addTab(self._build_takvim_tab(),    "İzin Takvimi")
        self._tabs.addTab(self._build_kapasite_tab(),  "Kapasite Analizi")
        self._tabs.addTab(self._build_uyari_tab(),     "Uyarılar & Notlar")
        lay.addWidget(self._tabs, 1)
        lay.addWidget(self._build_footer())

    def _build_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("bg-role", "panel")
        bar.setFixedHeight(46)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(8)

        btn_g = QPushButton("‹")
        btn_g.setFixedSize(28, 28)
        btn_g.setProperty("style-role","secondary")
        btn_g.clicked.connect(self._ay_geri)
        h.addWidget(btn_g)

        self._lbl_ay = QLabel()
        self._lbl_ay.setFixedWidth(130)
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role","section-title")
        h.addWidget(self._lbl_ay)

        btn_i = QPushButton("›")
        btn_i.setFixedSize(28, 28)
        btn_i.setProperty("style-role","secondary")
        btn_i.clicked.connect(self._ay_ileri)
        h.addWidget(btn_i)

        h.addSpacing(16)
        lbl = QLabel("Birim:")
        lbl.setProperty("color-role","muted")
        h.addWidget(lbl)

        self._cmb_birim = QComboBox()
        self._cmb_birim.setMinimumWidth(180)
        self._cmb_birim.currentIndexChanged.connect(self._on_birim_sec)
        h.addWidget(self._cmb_birim)
        h.addStretch()

        btn_pdf = QPushButton("⬇ PDF")
        btn_pdf.setProperty("style-role","secondary")
        btn_pdf.setFixedHeight(28)
        btn_pdf.clicked.connect(self._pdf_al)
        h.addWidget(btn_pdf)

        btn_yenile = QPushButton("↺ Yenile")
        btn_yenile.setProperty("style-role","secondary")
        btn_yenile.setFixedHeight(28)
        btn_yenile.clicked.connect(self._yukle)
        h.addWidget(btn_yenile)
        return bar

    @staticmethod
    def _tablo(sutunlar: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(sutunlar))
        tbl.setHorizontalHeaderLabels(sutunlar)
        tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(sutunlar)):
            tbl.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        tbl.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setSortingEnabled(True)
        return tbl

    def _build_personel_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        aciklama = QLabel(
            "  Nöbet planı yapmadan önce her personelin hazır olup olmadığını kontrol edin.  "
            "Çift tıkla → FM Gönüllü / Hedef Tipi düzenle")
        aciklama.setProperty("color-role","muted")
        aciklama.setStyleSheet("font-size:10px;padding:4px 8px;")
        lay.addWidget(aciklama)

        self._tbl_per = self._tablo([
            "Ad Soyad", "Hedef\nSaat", "Hedef\nTipi",
            "FM\nGönüllü", "İzin\nGünü", "Önceki\nDevir",
            "Durum",
        ])
        self._tbl_per.doubleClicked.connect(self._tercih_duzenle)
        lay.addWidget(self._tbl_per, 1)

        alt = QHBoxLayout()
        self._btn_tercih = QPushButton("✎  Tercih Düzenle")
        self._btn_tercih.setProperty("style-role","secondary")
        self._btn_tercih.setFixedHeight(28)
        self._btn_tercih.setEnabled(False)
        self._btn_tercih.clicked.connect(self._tercih_duzenle)
        alt.addWidget(self._btn_tercih)
        alt.addStretch()
        self._lbl_per_alt = QLabel("")
        self._lbl_per_alt.setProperty("color-role","muted")
        self._lbl_per_alt.setStyleSheet("font-size:11px;")
        alt.addWidget(self._lbl_per_alt)
        lay.addLayout(alt)

        self._tbl_per.selectionModel().selectionChanged.connect(
            lambda: self._btn_tercih.setEnabled(
                self._tbl_per.currentRow() >= 0))
        return w

    def _build_takvim_tab(self) -> QWidget:
        """İzin takvimi: gün × kişi matrisi + günlük izinli sayısı."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        # Üst: günlük izinli sayısı (bar chart yerine renkli hücreler)
        self._tbl_takvim_ozet = QTableWidget(1, 0)
        self._tbl_takvim_ozet.verticalHeader().setVisible(False)
        self._tbl_takvim_ozet.setMaximumHeight(48)
        self._tbl_takvim_ozet.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_takvim_ozet.setShowGrid(True)
        lay.addWidget(self._tbl_takvim_ozet)

        # Alt: personel × gün matrisi
        self._tbl_takvim = QTableWidget(0, 0)
        self._tbl_takvim.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_takvim.setAlternatingRowColors(True)
        self._tbl_takvim.verticalHeader().setVisible(False)
        self._tbl_takvim.setShowGrid(True)
        lay.addWidget(self._tbl_takvim, 1)

        self._lbl_takvim_alt = QLabel("")
        self._lbl_takvim_alt.setProperty("color-role","muted")
        self._lbl_takvim_alt.setStyleSheet("font-size:11px;padding:2px 4px;")
        lay.addWidget(self._lbl_takvim_alt)
        return w

    def _build_kapasite_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 8)
        lay.setSpacing(12)

        # Üst: özet kartlar
        self._kart_frame = QFrame()
        self._kart_frame.setProperty("bg-role","panel")
        self._kart_lay = QHBoxLayout(self._kart_frame)
        self._kart_lay.setContentsMargins(12, 8, 12, 8)
        self._kart_lay.setSpacing(16)
        lay.addWidget(self._kart_frame)

        # Alt: personel hedef tablosu
        self._tbl_kap = self._tablo([
            "Ad Soyad", "Hedef\nSaat", "Hedef\nTipi",
            "Aylık İş\nGünü", "İzin\nİş Günü", "Net\nGün",
        ])
        lay.addWidget(self._tbl_kap, 1)

        self._lbl_kap_alt = QLabel("")
        self._lbl_kap_alt.setProperty("color-role","muted")
        self._lbl_kap_alt.setStyleSheet("font-size:11px;padding:2px 4px;")
        lay.addWidget(self._lbl_kap_alt)
        return w

    def _build_uyari_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 8)
        lay.setSpacing(8)

        baslik = QLabel("Planlama Öncesi Uyarılar")
        baslik.setProperty("style-role","section-title")
        lay.addWidget(baslik)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._uyari_widget = QWidget()
        self._uyari_lay = QVBoxLayout(self._uyari_widget)
        self._uyari_lay.setContentsMargins(0, 0, 0, 0)
        self._uyari_lay.setSpacing(6)
        self._uyari_lay.addStretch()
        scroll.setWidget(self._uyari_widget)
        lay.addWidget(scroll, 1)
        return w

    def _build_footer(self) -> QFrame:
        f = QFrame()
        f.setProperty("bg-role","panel")
        f.setFixedHeight(24)
        h = QHBoxLayout(f)
        h.setContentsMargins(12, 0, 12, 0)
        self._lbl_status = QLabel("")
        self._lbl_status.setProperty("color-role","muted")
        self._lbl_status.setStyleSheet("font-size:10px;")
        h.addWidget(self._lbl_status)
        return f

    # ──────────────────────────────────────────────────────────
    #  Navigasyon
    # ──────────────────────────────────────────────────────────

    def _ay_geri(self):
        if self._ay == 1: self._ay, self._yil = 12, self._yil-1
        else: self._ay -= 1
        self._yukle()

    def _ay_ileri(self):
        if self._ay == 12: self._ay, self._yil = 1, self._yil+1
        else: self._ay += 1
        self._yukle()

    def _on_birim_sec(self):
        self._birim_id  = self._cmb_birim.currentData() or ""
        self._birim_adi = self._cmb_birim.currentText() or ""
        self._yukle()

    # ──────────────────────────────────────────────────────────
    #  Ortak Yardımcılar
    # ──────────────────────────────────────────────────────────

    def _birimleri_doldur(self):
        try:
            rows = sorted(
                self._reg().get("NB_Birim").get_all() or [],
                key=lambda r: r.get("BirimAdi",""))
            self._cmb_birim.blockSignals(True)
            self._cmb_birim.clear()
            self._cmb_birim.addItem("Tüm Birimler", userData="")
            for r in rows:
                self._cmb_birim.addItem(
                    r.get("BirimAdi",""), userData=r["BirimID"])
            self._cmb_birim.blockSignals(False)
        except Exception as e:
            logger.error(f"birimleri_doldur: {e}")

    def _yukle(self):
        if not self._db: return
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")
        self._yukle_personel()
        self._yukle_takvim()
        self._yukle_kapasite()
        self._yukle_uyarilar()
        self._lbl_status.setText(
            f"Güncellendi: {_AY[self._ay]} {self._yil}  —  "
            f"{self._cmb_birim.currentText() or 'Tüm Birimler'}")

    def _pid_listesi(self) -> list[tuple[str,str]]:
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            if self._birim_id:
                bp   = reg.get("NB_BirimPersonel").get_all() or []
                pids = [str(r.get("PersonelID","")) for r in bp
                        if str(r.get("BirimID","")) == self._birim_id
                        and int(r.get("Aktif",1))]
            else:
                pids = list(p_map.keys())
            return sorted(
                [(p, p_map.get(p,p)) for p in pids if p],
                key=lambda x: x[1])
        except Exception:
            return []

    def _onceki_devir(self, pid: str, reg) -> float:
        """Önceki ayın devire giden FM bakiyesi."""
        try:
            if self._ay == 1: ony, ona = self._yil-1, 12
            else: ony, ona = self._yil, self._ay-1
            mh_rows = reg.get("NB_MesaiHesap").get_all() or []
            kayit   = next(
                (r for r in mh_rows
                 if str(r.get("PersonelID","")) == pid
                 and int(r.get("Yil",0)) == ony
                 and int(r.get("Ay",0)) == ona
                 and (not self._birim_id
                      or str(r.get("BirimID","")) == self._birim_id)),
                None)
            return float((kayit or {}).get("DevireGidenDakika", 0)) / 60
        except Exception:
            return 0.0

    def _izin_gun_sayisi(self, pid: str, reg) -> int:
        """Kişinin bu aydaki izin iş günü sayısı."""
        try:
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            rows   = reg.get("Izin_Giris").get_all() or []
            toplam = 0
            for r in rows:
                if str(r.get("Personelid","")).strip() != pid.strip():
                    continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR:
                    continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                toplam += _networkdays(
                    max(bas,ay_bas), min(bit,ay_bit), tatil)
            return toplam
        except Exception:
            return 0

    # ──────────────────────────────────────────────────────────
    #  Sekme 1: Personel Durumu
    # ──────────────────────────────────────────────────────────

    def _yukle_personel(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            ay_is  = _networkdays(ay_bas, ay_bit, tatil)

            self._tbl_per.setSortingEnabled(False)
            self._tbl_per.setRowCount(0)

            uyari_sayi  = 0
            fm_sayi     = 0

            for pid, ad in pidler:
                tip      = _hedef_tipi(pid, self._birim_id,
                                       self._yil, self._ay, reg)
                hedef    = _hedef_saat(pid, self._birim_id,
                                       self._yil, self._ay, reg)
                fm       = _fm_gonullu(pid, self._birim_id,
                                       self._yil, self._ay, reg)
                izin_gun = self._izin_gun_sayisi(pid, reg)
                devir    = self._onceki_devir(pid, reg)
                if fm:
                    fm_sayi += 1

                ri = self._tbl_per.rowCount()
                self._tbl_per.insertRow(ri)
                self._tbl_per.setItem(ri, 0, _it(ad, pid))
                self._tbl_per.setItem(ri, 1, _it(f"{hedef:.0f} s", pid))

                # Hedef tipi
                tip_itm = _it(tip.capitalize() if tip else "Normal", pid)
                if tip not in ("normal","rapor","yillik","idari",""):
                    tip_itm.setForeground(QColor("#f59e0b"))
                self._tbl_per.setItem(ri, 2, tip_itm)

                # FM Gönüllü
                fm_itm = _it("● FM" if fm else "○", pid)
                fm_itm.setForeground(QColor("#4d9ee8" if fm else "#6b7280"))
                self._tbl_per.setItem(ri, 3, fm_itm)

                # İzin günü
                izin_itm = _it(
                    f"{izin_gun} iş günü" if izin_gun else "—", pid)
                if izin_gun > 0:
                    izin_itm.setForeground(QColor("#f59e0b"))
                self._tbl_per.setItem(ri, 4, izin_itm)

                # Önceki devir
                if devir == 0:
                    devir_lbl = "—"
                    devir_renk = "#6b7280"
                elif devir > 0:
                    devir_lbl  = f"+{devir:.0f} s"
                    devir_renk = "#f59e0b" if devir > DEVIR_ESIK else "#f3c55a"
                else:
                    devir_lbl  = f"{devir:.0f} s"
                    devir_renk = "#e85555"
                devir_itm = _it(devir_lbl, pid)
                devir_itm.setForeground(QColor(devir_renk))
                self._tbl_per.setItem(ri, 5, devir_itm)

                # Durum
                uyarilar = []
                if hedef == 0 and tip == "sua":
                    uyarilar.append("Şua — nöbet yok")
                elif izin_gun >= ay_is:
                    uyarilar.append("Tam ay izin")
                elif devir > DEVIR_ESIK:
                    uyarilar.append(f"Yüksek devir ⚠")
                    uyari_sayi += 1

                durum_lbl  = "  ".join(uyarilar) if uyarilar else "✔ Hazır"
                durum_renk = "#e85555" if uyarilar else "#2ec98e"
                durum_itm  = _it(durum_lbl, pid)
                durum_itm.setForeground(QColor(durum_renk))
                self._tbl_per.setItem(ri, 6, durum_itm)

            self._tbl_per.setSortingEnabled(True)
            self._lbl_per_alt.setText(
                f"{len(pidler)} personel  |  "
                f"{fm_sayi} FM Gönüllü  |  "
                f"{uyari_sayi} uyarı")
        except Exception as e:
            logger.error(f"yukle_personel: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 2: İzin Takvimi
    # ──────────────────────────────────────────────────────────

    def _yukle_takvim(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            ay_son = monthrange(self._yil, self._ay)[1]
            ay_bas_s = date(self._yil, self._ay, 1).isoformat()
            ay_bit_s = date(self._yil, self._ay, ay_son).isoformat()
            tatil    = _tatil_set(self._yil, self._ay, reg)
            haftasonu = {
                g for g in range(1, ay_son+1)
                if date(self._yil, self._ay, g).weekday() in (5,6)}
            tatil_gunler = {
                int(t.split("-")[2]) for t in tatil
                if t.startswith(f"{self._yil:04d}-{self._ay:02d}-")}

            iz_rows = reg.get("Izin_Giris").get_all() or []
            pid_set = {pid for pid,_ in pidler}

            # İzin günleri {pid: {gun_no}}
            izin_map: dict[str,set] = {}
            for r in iz_rows:
                pid = str(r.get("Personelid","")).strip()
                if pid_set and pid not in pid_set:
                    continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR:
                    continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                ay_bas_d = date(self._yil, self._ay, 1)
                ay_bit_d = date(self._yil, self._ay, ay_son)
                g = max(bas, ay_bas_d)
                while g <= min(bit, ay_bit_d):
                    izin_map.setdefault(pid, set()).add(g.day)
                    g += timedelta(days=1)

            # Günlük izinli sayısı
            gun_izin_sayi = {
                g: sum(1 for pid,_ in pidler if g in izin_map.get(pid,set()))
                for g in range(1, ay_son+1)}

            # Özet satır (üst tablo)
            self._tbl_takvim_ozet.setColumnCount(1 + ay_son)
            self._tbl_takvim_ozet.setHorizontalHeaderLabels(
                [""] + [str(g) for g in range(1, ay_son+1)])
            self._tbl_takvim_ozet.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Fixed)
            self._tbl_takvim_ozet.setColumnWidth(0, 80)
            for i in range(1, 1+ay_son):
                self._tbl_takvim_ozet.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Fixed)
                self._tbl_takvim_ozet.setColumnWidth(i, 24)
            lbl_itm = QTableWidgetItem("İzinli")
            lbl_itm.setForeground(QColor("#6b7280"))
            self._tbl_takvim_ozet.setItem(0, 0, lbl_itm)
            for g in range(1, ay_son+1):
                sayi = gun_izin_sayi[g]
                itm  = QTableWidgetItem(str(sayi) if sayi else "")
                itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if sayi == 0:
                    bg = QColor("#1a2a1a")
                elif sayi <= 2:
                    bg = QColor("#2a3a1a")
                elif sayi <= 4:
                    bg = QColor("#3a2a10")
                else:
                    bg = QColor("#3a1a1a")
                itm.setBackground(bg)
                if sayi > 0:
                    itm.setForeground(QColor("#f59e0b" if sayi>4 else "#f3c55a"))
                # Hafta sonu / tatil gri
                if g in haftasonu or g in tatil_gunler:
                    itm.setBackground(QColor("#1e1e2e"))
                self._tbl_takvim_ozet.setItem(0, g, itm)

            # Personel × gün matrisi
            self._tbl_takvim.setRowCount(len(pidler))
            self._tbl_takvim.setColumnCount(1 + ay_son)
            basliklar = ["Ad Soyad"] + [
                f"{g}\n{_GUN[date(self._yil,self._ay,g).weekday()]}"
                for g in range(1, ay_son+1)]
            self._tbl_takvim.setHorizontalHeaderLabels(basliklar)
            self._tbl_takvim.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents)
            for i in range(1, 1+ay_son):
                self._tbl_takvim.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Fixed)
                self._tbl_takvim.setColumnWidth(i, 24)

            for ri, (pid, ad) in enumerate(pidler):
                ad_itm = QTableWidgetItem(ad)
                ad_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_takvim.setItem(ri, 0, ad_itm)
                gunler = izin_map.get(pid, set())
                for g in range(1, ay_son+1):
                    itm = QTableWidgetItem()
                    itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if g in gunler:
                        itm.setText("İ")
                        itm.setBackground(QColor("#3a2a10"))
                        itm.setForeground(QColor("#f59e0b"))
                    elif g in tatil_gunler:
                        itm.setBackground(QColor("#2a1a1a"))
                    elif g in haftasonu:
                        itm.setBackground(QColor("#1a2a3a"))
                    self._tbl_takvim.setItem(ri, g, itm)

            izinli_kisi = len([p for p,_ in pidler if izin_map.get(p)])
            maks_gun    = max(gun_izin_sayi.values(), default=0)
            self._lbl_takvim_alt.setText(
                f"{izinli_kisi} personel izinli  |  "
                f"En yoğun gün: {maks_gun} kişi  |  "
                f"İ = İzin  □ = Hafta sonu")
        except Exception as e:
            logger.error(f"yukle_takvim: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 3: Kapasite Analizi
    # ──────────────────────────────────────────────────────────

    def _yukle_kapasite(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            ay_is  = _networkdays(ay_bas, ay_bit, tatil)
            ay_son = monthrange(self._yil, self._ay)[1]

            # Birim ayarlarından slot sayısı
            ayar = {}
            if self._birim_id:
                a_rows = reg.get("NB_BirimAyar").get_all() or []
                ayar   = next(
                    (r for r in a_rows
                     if str(r.get("BirimID","")) == self._birim_id), {})
            slot_sayisi = int(ayar.get("GunlukSlotSayisi", 4))

            # Vardiya grubu sayısı
            g_rows   = reg.get("NB_VardiyaGrubu").get_all() or []
            v_rows   = reg.get("NB_Vardiya").get_all() or []
            grup_ids = [
                str(g["GrupID"]) for g in g_rows
                if (not self._birim_id or str(g.get("BirimID",""))==self._birim_id)
                and int(g.get("Aktif",1))]
            ana_v_sayisi = sum(
                1 for v in v_rows
                if str(v.get("GrupID","")) in set(grup_ids)
                and str(v.get("Rol","ana")) == "ana"
                and int(v.get("Aktif",1)))

            # Dini bayram günleri
            dini_rows = reg.get("Tatiller").get_all() or []
            ay_bas_s = f"{self._yil:04d}-{self._ay:02d}-01"
            ay_bit_s = f"{self._yil:04d}-{self._ay:02d}-31"
            dini_sayi = sum(
                1 for r in dini_rows
                if ay_bas_s <= str(r.get("Tarih","")) <= ay_bit_s
                and str(r.get("TatilTuru","")) == "DiniBayram")

            # Toplam nöbet ihtiyacı
            aktif_gun = ay_son - dini_sayi
            toplam_nobet = aktif_gun * slot_sayisi * ana_v_sayisi

            # Personel toplam hedef saati
            toplam_hedef = sum(
                _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                for pid, _ in pidler)

            # Nöbet başı ortalama süre (dakika → saat)
            v_sureleri = [
                int(v.get("SureDakika",720)) / 60
                for v in v_rows
                if str(v.get("GrupID","")) in set(grup_ids)
                and str(v.get("Rol","ana")) == "ana"]
            ort_sure = sum(v_sureleri)/len(v_sureleri) if v_sureleri else 12.0
            toplam_nobet_saat = toplam_nobet * ort_sure

            # Kart widget'ları güncelle
            while self._kart_lay.count():
                itm = self._kart_lay.takeAt(0)
                if itm.widget(): itm.widget().deleteLater()

            def _kart(baslik: str, deger: str, renk: str = "#4d9ee8"):
                f = QFrame()
                f.setProperty("bg-role","panel")
                f.setMinimumWidth(130)
                l = QVBoxLayout(f)
                l.setContentsMargins(12, 8, 12, 8)
                l.setSpacing(2)
                v_lbl = QLabel(deger)
                v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v_lbl.setStyleSheet(
                    f"font-size:22px;font-weight:bold;color:{renk};")
                b_lbl = QLabel(baslik)
                b_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                b_lbl.setProperty("color-role","muted")
                b_lbl.setStyleSheet("font-size:10px;")
                l.addWidget(v_lbl)
                l.addWidget(b_lbl)
                return f

            fark = toplam_hedef - toplam_nobet_saat
            fark_renk = "#2ec98e" if abs(fark) < 50 else "#f59e0b"

            self._kart_lay.addWidget(_kart("Ay İş Günü",    str(ay_is)))
            self._kart_lay.addWidget(_kart("Toplam Nöbet",  str(toplam_nobet)))
            self._kart_lay.addWidget(_kart("Nöbet İhtiyacı (s)",
                                           f"{toplam_nobet_saat:.0f}"))
            self._kart_lay.addWidget(_kart("Personel Hedefi (s)",
                                           f"{toplam_hedef:.0f}"))
            self._kart_lay.addWidget(_kart("Fark",
                                           f"{fark:+.0f} s", fark_renk))
            self._kart_lay.addWidget(_kart("FM Gönüllü",
                str(sum(1 for pid,_ in pidler
                        if _fm_gonullu(pid,self._birim_id,
                                       self._yil,self._ay,reg))), "#4d9ee8"))
            self._kart_lay.addStretch()

            # Personel hedef tablosu
            self._tbl_kap.setSortingEnabled(False)
            self._tbl_kap.setRowCount(0)
            for pid, ad in pidler:
                tip     = _hedef_tipi(pid, self._birim_id,
                                      self._yil, self._ay, reg)
                hedef   = _hedef_saat(pid, self._birim_id,
                                      self._yil, self._ay, reg)
                gun_s   = HEDEF_GUNLUK.get(tip, 7.0)
                net_gun = round(hedef / gun_s, 1) if gun_s > 0 else 0
                izin_gun= self._izin_gun_sayisi(pid, reg)
                ri      = self._tbl_kap.rowCount()
                self._tbl_kap.insertRow(ri)
                self._tbl_kap.setItem(ri, 0, _it(ad, pid))
                self._tbl_kap.setItem(ri, 1, _it(f"{hedef:.0f} s", pid))
                tip_itm = _it(tip.capitalize(), pid)
                if tip not in ("normal","rapor","yillik","idari",""):
                    tip_itm.setForeground(QColor("#f59e0b"))
                self._tbl_kap.setItem(ri, 2, tip_itm)
                self._tbl_kap.setItem(ri, 3, _it(str(ay_is), pid))
                izin_itm = _it(str(izin_gun) if izin_gun else "—", pid)
                if izin_gun > 0:
                    izin_itm.setForeground(QColor("#f59e0b"))
                self._tbl_kap.setItem(ri, 4, izin_itm)
                self._tbl_kap.setItem(ri, 5, _it(f"{net_gun:.0f}", pid))

            self._tbl_kap.setSortingEnabled(True)
            self._lbl_kap_alt.setText(
                f"{len(pidler)} personel  |  "
                f"Slot/gün: {slot_sayisi}  |  Ana vardiya: {ana_v_sayisi}  |  "
                f"Dini bayram: {dini_sayi} gün")
        except Exception as e:
            logger.error(f"yukle_kapasite: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 4: Uyarılar
    # ──────────────────────────────────────────────────────────

    def _yukle_uyarilar(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            ay_is  = _networkdays(ay_bas, ay_bit, tatil)

            # Eski widget'ları temizle
            while self._uyari_lay.count() > 1:
                itm = self._uyari_lay.takeAt(0)
                if itm.widget(): itm.widget().deleteLater()

            uyarilar = []

            for pid, ad in pidler:
                tip      = _hedef_tipi(pid, self._birim_id,
                                       self._yil, self._ay, reg)
                hedef    = _hedef_saat(pid, self._birim_id,
                                       self._yil, self._ay, reg)
                izin_gun = self._izin_gun_sayisi(pid, reg)
                devir    = self._onceki_devir(pid, reg)
                fm       = _fm_gonullu(pid, self._birim_id,
                                       self._yil, self._ay, reg)

                if hedef == 0 and tip != "sua":
                    uyarilar.append(
                        ("⚠", f"{ad} — Bu ay çalışma hedefi 0 saat "
                         f"(izin: {izin_gun} iş günü)", "#e85555"))
                elif devir > DEVIR_ESIK:
                    uyarilar.append(
                        ("💰", f"{ad} — Önceki aydan +{devir:.0f}s "
                         f"FM bakiyesi var, bu ay fazla yükleme yapmayın",
                         "#f59e0b"))
                elif izin_gun > 0 and not fm:
                    pass  # izinli ama FM değil — normal
                if izin_gun >= ay_is:
                    uyarilar.append(
                        ("📅", f"{ad} — Tam ay izinli, nöbete dahil edilmeyecek",
                         "#4d9ee8"))

            # İzin yoğunluğu
            iz_rows = reg.get("Izin_Giris").get_all() or []
            pid_set = {pid for pid,_ in pidler}
            gun_sayi = {}
            for r in iz_rows:
                pid = str(r.get("Personelid","")).strip()
                if pid_set and pid not in pid_set: continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                g = max(bas, ay_bas)
                while g <= min(bit, ay_bit):
                    gun_sayi[g] = gun_sayi.get(g, 0) + 1
                    g += timedelta(days=1)

            yogun_gunler = sorted(
                [(g, s) for g,s in gun_sayi.items()
                 if s >= max(3, len(pidler)*0.3)],
                key=lambda x: -x[1])
            if yogun_gunler:
                gunler_str = ", ".join(
                    f"{g.strftime('%d.%m')}({s}k)"
                    for g, s in yogun_gunler[:5])
                uyarilar.append(
                    ("📆", f"Yoğun izin günleri: {gunler_str} — "
                     f"slot doldurmak zorlaşabilir", "#f59e0b"))

            # FM gönüllü yok uyarısı
            fm_sayi = sum(
                1 for pid,_ in pidler
                if _fm_gonullu(pid,self._birim_id,self._yil,self._ay,reg))
            if fm_sayi == 0:
                uyarilar.append(
                    ("ℹ", "Bu birimde FM gönüllüsü yok — "
                     "boş slotlar otomatik doldurulamayacak", "#4d9ee8"))

            if not uyarilar:
                uyarilar.append(
                    ("✔", "Tespit edilen kritik uyarı yok — "
                     "nöbet planlamaya hazır", "#2ec98e"))

            # Widget oluştur
            for icon, metin, renk in uyarilar:
                f = QFrame()
                f.setProperty("bg-role","panel")
                h = QHBoxLayout(f)
                h.setContentsMargins(12, 8, 12, 8)
                h.setSpacing(12)
                icon_lbl = QLabel(icon)
                icon_lbl.setFixedWidth(24)
                icon_lbl.setStyleSheet(f"font-size:16px;color:{renk};")
                h.addWidget(icon_lbl)
                metin_lbl = QLabel(metin)
                metin_lbl.setWordWrap(True)
                metin_lbl.setStyleSheet(f"font-size:12px;color:{renk};")
                h.addWidget(metin_lbl, 1)
                self._uyari_lay.insertWidget(
                    self._uyari_lay.count()-1, f)

        except Exception as e:
            logger.error(f"yukle_uyarilar: {e}")

    # ──────────────────────────────────────────────────────────
    #  Tercih Düzenleme
    # ──────────────────────────────────────────────────────────

    def _tercih_duzenle(self):
        row = self._tbl_per.currentRow()
        if row < 0: return
        itm = self._tbl_per.item(row, 0)
        pid = itm.data(Qt.ItemDataRole.UserRole)
        ad  = itm.text()
        try:
            reg    = self._reg()
            t_rows = reg.get("NB_PersonelTercih").get_all() or []
            kayit  = next(
                (r for r in t_rows
                 if str(r.get("PersonelID","")) == pid
                 and str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay),
                None)
            dialog = _TercihDialog(
                pid, ad, self._yil, self._ay, kayit, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            veri = dialog.get_data()
            simdi = _simdi()
            if kayit:
                reg.get("NB_PersonelTercih").update(
                    kayit["TercihID"], {**veri, "updated_at": simdi})
            else:
                reg.get("NB_PersonelTercih").insert({
                    "TercihID":   str(uuid.uuid4()),
                    "PersonelID": pid,
                    "BirimID":    self._birim_id or "",
                    "Yil":        self._yil,
                    "Ay":         self._ay,
                    "created_at": simdi,
                    **veri,
                })
            self._yukle_personel()
            self._yukle_uyarilar()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  PDF Çıktısı
    # ──────────────────────────────────────────────────────────

    def _pdf_al(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle,
                Paragraph, Spacer, HRFlowable)
            from PySide6.QtWidgets import QFileDialog

            birim_str = self._birim_adi or "Tüm Birimler"
            varsayilan = (
                f"Nobet_OnHazirlik_{_AY[self._ay]}_{self._yil}"
                f"{'_'+self._birim_adi.replace(' ','_') if self._birim_adi else ''}.pdf")
            yol, _ = QFileDialog.getSaveFileName(
                self, "PDF Kaydet", varsayilan,
                "PDF Dosyası (*.pdf)")
            if not yol:
                return

            reg    = self._reg()
            pidler = self._pid_listesi()
            styles = getSampleStyleSheet()
            baslik_s = ParagraphStyle(
                "b", parent=styles["Title"], fontSize=14, spaceAfter=4)
            alt_s = ParagraphStyle(
                "a", parent=styles["Normal"], fontSize=9,
                textColor=colors.grey, spaceAfter=8)
            sec_s = ParagraphStyle(
                "s", parent=styles["Heading2"], fontSize=11, spaceAfter=4)

            doc  = SimpleDocTemplate(
                yol, pagesize=landscape(A4),
                leftMargin=1.5*cm, rightMargin=1.5*cm,
                topMargin=1.5*cm, bottomMargin=1.5*cm)
            hikaye = []

            hikaye.append(Paragraph(
                f"Nöbet Ön Hazırlık Raporu — {_AY[self._ay]} {self._yil}",
                baslik_s))
            hikaye.append(Paragraph(
                f"Birim: {birim_str}  |  "
                f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                alt_s))
            hikaye.append(HRFlowable(width="100%", thickness=0.5,
                                     color=colors.lightgrey))
            hikaye.append(Spacer(1, 0.3*cm))

            # 1. Personel Durumu Tablosu
            hikaye.append(Paragraph("1. Personel Durumu", sec_s))
            basliklar = [
                "Ad Soyad","Hedef\nSaat","Hedef\nTipi",
                "FM\nGönüllü","İzin\nGünü","Önceki\nDevir","Durum"]
            veri = [basliklar]
            for pid, ad in pidler:
                tip    = _hedef_tipi(pid, self._birim_id,
                                     self._yil, self._ay, reg)
                hedef  = _hedef_saat(pid, self._birim_id,
                                     self._yil, self._ay, reg)
                fm     = _fm_gonullu(pid, self._birim_id,
                                     self._yil, self._ay, reg)
                izin   = self._izin_gun_sayisi(pid, reg)
                devir  = self._onceki_devir(pid, reg)
                veri.append([
                    ad,
                    f"{hedef:.0f} s",
                    tip.capitalize(),
                    "FM ✔" if fm else "—",
                    f"{izin} gün" if izin else "—",
                    f"+{devir:.0f}s" if devir > 0
                    else (f"{devir:.0f}s" if devir < 0 else "—"),
                    "⚠ Yüksek devir" if devir > DEVIR_ESIK else "✔",
                ])
            tbl = Table(
                veri,
                colWidths=[5*cm,2*cm,2.5*cm,2*cm,2*cm,2.5*cm,3*cm],
                repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0,0),(-1,0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",   (0,0),(-1,0), colors.white),
                ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0),(-1,-1), 8),
                ("ALIGN",       (0,0),(-1,-1), "CENTER"),
                ("ALIGN",       (0,1),(0,-1),  "LEFT"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white, colors.HexColor("#f0f4f8")]),
                ("FONTNAME",    (0,1),(-1,-1), "Helvetica"),
                ("GRID",        (0,0),(-1,-1), 0.3,
                 colors.HexColor("#d1d5db")),
                ("TOPPADDING",  (0,0),(-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LEFTPADDING", (0,0),(-1,-1), 5),
                ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
            ]))
            hikaye.append(tbl)
            hikaye.append(Spacer(1, 0.5*cm))

            doc.build(hikaye)
            QMessageBox.information(
                self, "PDF Kaydedildi", f"Dosya:\n{yol}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            logger.error(f"_pdf_al: {e}")

    def load_data(self):
        if self._db:
            self._birimleri_doldur()
            self._yukle()
