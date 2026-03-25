# -*- coding: utf-8 -*-
"""
nobet_hazirlik_page.py — Nöbet Ön Hazırlık

Tek sayfa, iki bölüm:
  1. Kapasite özeti (üst bar)
     Toplam Gün | İş Günü | Resmi Tatil | Dini Bayram | Toplam Nöbet | Hedef Mesai
  2. Personel durum tablosu
     Ad Soyad | Hedef Saat | Hedef Tipi | FM Gönüllü | İzin Günü | Önceki Devir | Durum
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
    QHeaderView, QAbstractItemView, QDialog, QDialogButtonBox,
    QFormLayout, QCheckBox, QMessageBox,
)

from core.di import get_registry
from core.logger import logger

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}
HEDEF_GUNLUK  = {
    "normal":7.0, "emzirme":5.5, "sendika":6.2,
    "sua":0.0,    "rapor":7.0,   "yillik":7.0, "idari":7.0,
}
HEDEF_TIPLER = [
    ("normal","Normal  (7.0 s/gün)"), ("emzirme","Emzirme (5.5 s/gün)"),
    ("sendika","Sendika (6.2 s/gün)"), ("sua","Şua İzni (0 s/gün)"),
    ("rapor","Raporlu"), ("yillik","Yıllık İzin"), ("idari","İdari İzin"),
]
DEVIR_ESIK = 14.0  # saat — bu eşiğin üstü uyarı


# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────

def _networkdays(bas: date, bit: date, tatiller: set) -> int:
    if bas > bit: return 0
    n, g = 0, bas
    while g <= bit:
        if g.weekday() < 5 and g.isoformat() not in tatiller: n += 1
        g += timedelta(days=1)
    return n


def _tatil_set_by_tur(yil: int, ay: int, reg, tur: str = None) -> set:
    try:
        rows = reg.get("Tatiller").get_all() or []
        ab, ae = f"{yil:04d}-{ay:02d}-01", f"{yil:04d}-{ay:02d}-31"
        return {
            str(r.get("Tarih","")) for r in rows
            if ab <= str(r.get("Tarih","")) <= ae
            and (tur is None and str(r.get("TatilTuru","Resmi")) in ("Resmi","DiniBayram")
                 or tur is not None and str(r.get("TatilTuru","")) == tur)
        }
    except Exception: return set()


def _hedef_tipi(pid: str, birim_id: str, yil: int, ay: int, reg) -> str:
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next((r for r in rows
                  if str(r.get("PersonelID","")) == pid
                  and str(r.get("BirimID","")) == birim_id
                  and int(r.get("Yil",0)) == yil
                  and int(r.get("Ay",0)) == ay), None)
        return str((k or {}).get("HedefTipi","normal")).lower()
    except Exception: return "normal"


def _fm_gonullu(pid: str, birim_id: str, yil: int, ay: int, reg) -> bool:
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next((r for r in rows
                  if str(r.get("PersonelID","")) == pid
                  and str(r.get("BirimID","")) == birim_id
                  and int(r.get("Yil",0)) == yil
                  and int(r.get("Ay",0)) == ay), None)
        return str((k or {}).get("NobetTercihi","")) == "fazla_mesai_gonullu"
    except Exception: return False


def _hedef_saat(pid: str, birim_id: str, yil: int, ay: int, reg) -> float:
    try:
        tatil  = _tatil_set_by_tur(yil, ay, reg)
        ay_bas = date(yil, ay, 1)
        ay_bit = date(yil, ay, monthrange(yil, ay)[1])
        ay_is  = _networkdays(ay_bas, ay_bit, tatil)
        tip    = _hedef_tipi(pid, birim_id, yil, ay, reg)
        gun_s  = HEDEF_GUNLUK.get(tip, 7.0)
        rows   = reg.get("Izin_Giris").get_all() or []
        izin_is = 0
        for r in rows:
            if str(r.get("Personelid","")).strip() != str(pid).strip(): continue
            if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
            try:
                bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                bit = date.fromisoformat(str(r.get("BitisTarihi","")))
            except Exception: continue
            izin_is += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
        return round(max(0, ay_is - izin_is) * gun_s, 1)
    except Exception: return round(20*7.0, 1)


def _it(text: str, pid: str = "") -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setData(Qt.ItemDataRole.UserRole, pid)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


# ── Tercih Dialogu ────────────────────────────────────────────────────

class _TercihDialog(QDialog):
    def __init__(self, ad: str, yil: int, ay: int,
                 kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Tercih — {ad}")
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setProperty("bg-role","page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20,20,20,20)
        lay.setSpacing(10)
        lay.addWidget(QLabel(f"<b>{ad}</b>  —  {_AY[ay]} {yil}"))
        form = QFormLayout()
        self._chk = QCheckBox("FM Gönüllüsü")
        self._chk.setChecked(
            (kayit or {}).get("NobetTercihi","") == "fazla_mesai_gonullu")
        form.addRow("Fazla Mesai:", self._chk)
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
                             if self._chk.isChecked() else "zorunlu"),
            "HedefTipi": self._cmb.currentData(),
        }


# ══════════════════════════════════════════════════════════════════════
#  Ana Sayfa
# ══════════════════════════════════════════════════════════════════════

class NobetHazirlikPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db        = db
        self._yil       = date.today().year
        self._ay        = date.today().month
        self._birim_id  = ""
        self._birim_adi = ""
        self.setProperty("bg-role","page")
        self._build()
        if db:
            self._birimleri_doldur()
            self._yukle()

    def _reg(self): return get_registry(self._db)

    # ── UI ──────────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        lay.addWidget(self._build_kapasite_bar())
        lay.addWidget(self._build_tablo_bolumu(), 1)

    def _build_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("bg-role","panel")
        bar.setFixedHeight(46)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12,0,12,0)
        h.setSpacing(8)

        btn_g = QPushButton("‹")
        btn_g.setFixedSize(28,28)
        btn_g.setProperty("style-role","secondary")
        btn_g.clicked.connect(self._ay_geri)
        h.addWidget(btn_g)

        self._lbl_ay = QLabel()
        self._lbl_ay.setFixedWidth(130)
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role","section-title")
        h.addWidget(self._lbl_ay)

        btn_i = QPushButton("›")
        btn_i.setFixedSize(28,28)
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

        btn_yenile = QPushButton("↺")
        btn_yenile.setFixedSize(28,28)
        btn_yenile.setProperty("style-role","secondary")
        btn_yenile.clicked.connect(self._yukle)
        h.addWidget(btn_yenile)
        return bar

    def _build_kapasite_bar(self) -> QFrame:
        """9 kartlık üst özet bar."""
        bar = QFrame()
        bar.setProperty("bg-role","panel")
        bar.setFixedHeight(74)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16,6,16,6)
        h.setSpacing(0)

        self._kartlar: dict[str,QLabel] = {}
        bilgiler = [
            ("toplam_gun",   "Toplam Gün",       "#4d9ee8"),
            ("is_gunu",      "İş Günü",           "#4d9ee8"),
            ("resmi_tatil",  "Resmi Tatil",       "#6b7280"),
            ("dini_bayram",  "Dini Bayram",       "#6b7280"),
            ("toplam_nobet", "Toplam Nöbet",      "#2ec98e"),
            ("hedef_mesai",  "Kişi Başı Hedef",   "#f59e0b"),
            ("izinli_kisi",  "İzinli Personel",   "#f59e0b"),
            ("fm_gonullu",   "FM Gönüllü",        "#4d9ee8"),
            ("uyari",        "Uyarı",             "#e85555"),
        ]
        for key, baslik, renk in bilgiler:
            f = QFrame()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(8,4,8,4)
            fl.setSpacing(1)
            deger_lbl = QLabel("—")
            deger_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            deger_lbl.setStyleSheet(
                f"font-size:18px;font-weight:bold;color:{renk};")
            baslik_lbl = QLabel(baslik)
            baslik_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            baslik_lbl.setStyleSheet("font-size:9px;color:#6b7280;")
            fl.addWidget(deger_lbl)
            fl.addWidget(baslik_lbl)
            self._kartlar[key] = deger_lbl
            h.addWidget(f, 1)
            if key != "uyari":
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#2a3a4a;")
                h.addWidget(sep)
        return bar

    def _build_tablo_bolumu(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8,8,8,4)
        lay.setSpacing(4)

        ust = QHBoxLayout()
        lbl = QLabel("Personel Durumu")
        lbl.setProperty("style-role","section-title")
        ust.addWidget(lbl)
        ust.addStretch()
        ipucu = QLabel("Çift tıkla → FM / Hedef Tipi düzenle")
        ipucu.setProperty("color-role","muted")
        ipucu.setStyleSheet("font-size:10px;")
        ust.addWidget(ipucu)
        lay.addLayout(ust)

        self._tbl = QTableWidget(0, 7)
        self._tbl.setHorizontalHeaderLabels([
            "Ad Soyad","Hedef\nSaat","Hedef\nTipi",
            "FM\nGönüllü","İzin\nGünü","Önceki\nDevir","Durum",
        ])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1,7):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.setSortingEnabled(True)
        self._tbl.doubleClicked.connect(self._tercih_duzenle)
        self._tbl.selectionModel().selectionChanged.connect(
            lambda: self._btn_tercih.setEnabled(
                self._tbl.currentRow() >= 0))
        lay.addWidget(self._tbl, 1)

        alt = QHBoxLayout()
        self._btn_tercih = QPushButton("✎  Tercih Düzenle")
        self._btn_tercih.setProperty("style-role","secondary")
        self._btn_tercih.setFixedHeight(28)
        self._btn_tercih.setEnabled(False)
        self._btn_tercih.clicked.connect(self._tercih_duzenle)
        alt.addWidget(self._btn_tercih)
        alt.addStretch()
        self._lbl_alt = QLabel("")
        self._lbl_alt.setProperty("color-role","muted")
        self._lbl_alt.setStyleSheet("font-size:11px;")
        alt.addWidget(self._lbl_alt)
        lay.addLayout(alt)
        return w

    # ── Navigasyon ───────────────────────────────────────────────────────

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

    # ── Yükleme ──────────────────────────────────────────────────────────

    def _birimleri_doldur(self):
        try:
            rows = sorted(self._reg().get("NB_Birim").get_all() or [],
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
        self._yukle_kapasite()
        self._yukle_personel()

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
            return sorted([(p, p_map.get(p,p)) for p in pids if p],
                          key=lambda x: x[1])
        except Exception: return []

    def _izin_gun_sayisi(self, pid: str, reg) -> int:
        try:
            tatil  = _tatil_set_by_tur(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            rows   = reg.get("Izin_Giris").get_all() or []
            toplam = 0
            for r in rows:
                if str(r.get("Personelid","")).strip() != pid.strip(): continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception: continue
                toplam += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
            return toplam
        except Exception: return 0

    def _onceki_devir(self, pid: str, reg) -> float:
        try:
            if self._ay == 1: ony, ona = self._yil-1, 12
            else: ony, ona = self._yil, self._ay-1
            mh = reg.get("NB_MesaiHesap").get_all() or []
            k  = next((r for r in mh
                       if str(r.get("PersonelID","")) == pid
                       and int(r.get("Yil",0)) == ony
                       and int(r.get("Ay",0)) == ona
                       and (not self._birim_id
                            or str(r.get("BirimID","")) == self._birim_id)),
                      None)
            return float((k or {}).get("DevireGidenDakika", 0)) / 60
        except Exception: return 0.0

    # ── Kapasite Özeti ─────────────────────────────────────────────────

    def _yukle_kapasite(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set_by_tur(self._yil, self._ay, reg)
            resmi  = _tatil_set_by_tur(self._yil, self._ay, reg, "Resmi")
            dini   = _tatil_set_by_tur(self._yil, self._ay, reg, "DiniBayram")
            ay_son = monthrange(self._yil, self._ay)[1]
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay, ay_son)
            is_gun = _networkdays(ay_bas, ay_bit, tatil)

            # Slot ve ana vardiya sayısı
            slot = 4
            ana_v = 2
            if self._birim_id:
                a_rows = reg.get("NB_BirimAyar").get_all() or []
                ayar   = next((r for r in a_rows
                               if str(r.get("BirimID",""))==self._birim_id), {})
                slot   = int(ayar.get("GunlukSlotSayisi", 4))
                g_rows = reg.get("NB_VardiyaGrubu").get_all() or []
                v_rows = reg.get("NB_Vardiya").get_all() or []
                gids   = {str(g["GrupID"]) for g in g_rows
                          if str(g.get("BirimID","")) == self._birim_id
                          and int(g.get("Aktif",1))}
                ana_v  = sum(1 for v in v_rows
                             if str(v.get("GrupID","")) in gids
                             and str(v.get("Rol","ana")) == "ana"
                             and int(v.get("Aktif",1)))
                if ana_v == 0: ana_v = 2

            aktif_gun    = ay_son - len(dini)
            toplam_nobet = aktif_gun * slot * ana_v
            hedef_toplam = sum(
                _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                for pid,_ in pidler)
            kisi_basi = is_gun * 7  # iş günü × 7 saat

            self._kartlar["toplam_gun"].setText(str(ay_son))
            self._kartlar["is_gunu"].setText(str(is_gun))
            self._kartlar["resmi_tatil"].setText(str(len(resmi)))
            self._kartlar["dini_bayram"].setText(str(len(dini)))
            self._kartlar["toplam_nobet"].setText(str(toplam_nobet))
            self._kartlar["hedef_mesai"].setText(f"{kisi_basi:.0f} s")
            # izinli_kisi, fm_gonullu, uyari → _yukle_personel tarafından güncellenir
        except Exception as e:
            logger.error(f"yukle_kapasite: {e}")

    # ── Personel Durum Tablosu ─────────────────────────────────────────

    def _yukle_personel(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set_by_tur(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            ay_is  = _networkdays(ay_bas, ay_bit, tatil)

            self._tbl.setSortingEnabled(False)
            self._tbl.setRowCount(0)
            fm_sayi = uyari_sayi = 0

            for pid, ad in pidler:
                tip      = _hedef_tipi(pid,self._birim_id,self._yil,self._ay,reg)
                hedef    = _hedef_saat(pid,self._birim_id,self._yil,self._ay,reg)
                fm       = _fm_gonullu(pid,self._birim_id,self._yil,self._ay,reg)
                izin_gun = self._izin_gun_sayisi(pid, reg)
                devir    = self._onceki_devir(pid, reg)
                if fm: fm_sayi += 1

                ri = self._tbl.rowCount()
                self._tbl.insertRow(ri)
                self._tbl.setItem(ri, 0, _it(ad, pid))
                self._tbl.setItem(ri, 1, _it(f"{hedef:.0f} s", pid))

                tip_itm = _it(tip.capitalize() if tip else "Normal", pid)
                if tip not in ("normal","rapor","yillik","idari",""):
                    tip_itm.setForeground(QColor("#f59e0b"))
                self._tbl.setItem(ri, 2, tip_itm)

                fm_itm = _it("● FM" if fm else "○", pid)
                fm_itm.setForeground(QColor("#4d9ee8" if fm else "#6b7280"))
                self._tbl.setItem(ri, 3, fm_itm)

                iz_itm = _it(f"{izin_gun} gün" if izin_gun else "—", pid)
                if izin_gun > 0:
                    iz_itm.setForeground(QColor("#f59e0b"))
                self._tbl.setItem(ri, 4, iz_itm)

                if devir == 0:    devir_lbl, devir_renk = "—", "#6b7280"
                elif devir > 0:   devir_lbl, devir_renk = (
                    f"+{devir:.0f} s",
                    "#f59e0b" if devir > DEVIR_ESIK else "#f3c55a")
                else:             devir_lbl, devir_renk = f"{devir:.0f} s", "#e85555"
                devir_itm = _it(devir_lbl, pid)
                devir_itm.setForeground(QColor(devir_renk))
                self._tbl.setItem(ri, 5, devir_itm)

                if hedef == 0 and tip == "sua":
                    d_lbl, d_renk = "Şua — nöbet yok", "#6b7280"
                elif izin_gun >= ay_is:
                    d_lbl, d_renk = "Tam ay izin", "#6b7280"
                elif devir > DEVIR_ESIK:
                    d_lbl, d_renk = "⚠ Yüksek devir", "#f59e0b"
                    uyari_sayi += 1
                else:
                    d_lbl, d_renk = "✔ Hazır", "#2ec98e"
                d_itm = _it(d_lbl, pid)
                d_itm.setForeground(QColor(d_renk))
                self._tbl.setItem(ri, 6, d_itm)

            self._tbl.setSortingEnabled(True)

            # Kapasite barındaki 3 dinamik kartı güncelle
            izinli_sayi = sum(
                1 for pid,_ in pidler
                if self._izin_gun_sayisi(pid, reg) > 0)
            self._kartlar["izinli_kisi"].setText(str(izinli_sayi))
            self._kartlar["izinli_kisi"].setStyleSheet(
                f"font-size:18px;font-weight:bold;"
                f"color:{'#f59e0b' if izinli_sayi > 0 else '#6b7280'};")
            self._kartlar["fm_gonullu"].setText(str(fm_sayi))
            uyari_renk = "#e85555" if uyari_sayi > 0 else "#2ec98e"
            self._kartlar["uyari"].setText(str(uyari_sayi))
            self._kartlar["uyari"].setStyleSheet(
                f"font-size:18px;font-weight:bold;color:{uyari_renk};")

            self._lbl_alt.setText(
                f"{len(pidler)} personel  |  "
                f"{izinli_sayi} izinli  |  "
                f"{fm_sayi} FM Gönüllü  |  "
                f"{uyari_sayi} uyarı")
        except Exception as e:
            logger.error(f"yukle_personel: {e}")

    # ── Tercih Düzenleme ──────────────────────────────────────────────

    def _tercih_duzenle(self):
        row = self._tbl.currentRow()
        if row < 0: return
        itm = self._tbl.item(row, 0)
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
                 and int(r.get("Ay",0)) == self._ay), None)
            dialog = _TercihDialog(ad, self._yil, self._ay, kayit, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            veri  = dialog.get_data()
            simdi = datetime.now().isoformat(sep=" ", timespec="seconds")
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
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ── PDF ───────────────────────────────────────────────────────────

    def _pdf_al(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle,
                Paragraph, Spacer)
            from PySide6.QtWidgets import QFileDialog

            yol, _ = QFileDialog.getSaveFileName(
                self, "PDF Kaydet",
                f"Hazirlik_{_AY[self._ay]}_{self._yil}.pdf",
                "PDF Dosyası (*.pdf)")
            if not yol: return

            reg    = self._reg()
            pidler = self._pid_listesi()
            styles = getSampleStyleSheet()
            bs = ParagraphStyle("b", parent=styles["Title"],
                                fontSize=13, spaceAfter=3)
            as_ = ParagraphStyle("a", parent=styles["Normal"],
                                 fontSize=8, textColor=colors.grey, spaceAfter=6)

            doc = SimpleDocTemplate(
                yol, pagesize=landscape(A4),
                leftMargin=1.5*cm, rightMargin=1.5*cm,
                topMargin=1.5*cm, bottomMargin=1.5*cm)
            h = []

            birim_str = self._birim_adi or "Tüm Birimler"
            h.append(Paragraph(
                f"Nöbet Ön Hazırlık — {_AY[self._ay]} {self._yil}", bs))
            h.append(Paragraph(
                f"Birim: {birim_str}  |  "
                f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", as_))
            h.append(Spacer(1, 0.3*cm))

            # Kapasite satırı
            tatil  = _tatil_set_by_tur(self._yil, self._ay, reg)
            resmi  = _tatil_set_by_tur(self._yil, self._ay, reg, "Resmi")
            dini   = _tatil_set_by_tur(self._yil, self._ay, reg, "DiniBayram")
            ay_son = monthrange(self._yil, self._ay)[1]
            is_gun = _networkdays(
                date(self._yil,self._ay,1),
                date(self._yil,self._ay,ay_son), tatil)
            hedef_top = sum(
                _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                for pid,_ in pidler)

            kap = Table(
                [["Toplam Gün","İş Günü","Resmi Tatil",
                  "Dini Bayram","Hedef Mesai (s)"],
                 [str(ay_son), str(is_gun), str(len(resmi)),
                  str(len(dini)), f"{hedef_top:.0f}"]],
                colWidths=[3.5*cm]*5, repeatRows=1)
            kap.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0,0),(-1,0),colors.white),
                ("FONTNAME",  (0,0),(-1,-1),"Helvetica-Bold"),
                ("FONTSIZE",  (0,0),(-1,-1),9),
                ("ALIGN",     (0,0),(-1,-1),"CENTER"),
                ("GRID",      (0,0),(-1,-1),0.3,colors.lightgrey),
                ("TOPPADDING",(0,0),(-1,-1),5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f4f8")]),
            ]))
            h.append(kap)
            h.append(Spacer(1, 0.4*cm))

            # Personel tablosu
            veri = [["Ad Soyad","Hedef\nSaat","Hedef\nTipi",
                     "FM\nGönüllü","İzin\nGünü","Önceki\nDevir","Durum"]]
            tatil_p = _tatil_set_by_tur(self._yil, self._ay, reg)
            ay_bas  = date(self._yil, self._ay, 1)
            ay_bit  = date(self._yil, self._ay, ay_son)
            ay_is   = _networkdays(ay_bas, ay_bit, tatil_p)

            for pid, ad in pidler:
                tip   = _hedef_tipi(pid,self._birim_id,self._yil,self._ay,reg)
                hedef = _hedef_saat(pid,self._birim_id,self._yil,self._ay,reg)
                fm    = _fm_gonullu(pid,self._birim_id,self._yil,self._ay,reg)
                izin  = self._izin_gun_sayisi(pid, reg)
                devir = self._onceki_devir(pid, reg)
                if hedef == 0 and tip == "sua":   durum = "Şua"
                elif izin >= ay_is:               durum = "Tam ay izin"
                elif devir > DEVIR_ESIK:          durum = "⚠ Yüksek devir"
                else:                             durum = "✔ Hazır"
                veri.append([
                    ad, f"{hedef:.0f} s", tip.capitalize(),
                    "FM ✔" if fm else "—",
                    f"{izin} gün" if izin else "—",
                    f"+{devir:.0f}s" if devir>0
                    else (f"{devir:.0f}s" if devir<0 else "—"),
                    durum,
                ])
            tbl = Table(veri,
                        colWidths=[5*cm,2*cm,2.5*cm,1.8*cm,2*cm,2.5*cm,3*cm],
                        repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0,0),(-1,0),colors.white),
                ("FONTNAME",  (0,0),(-1,0),"Helvetica-Bold"),
                ("FONTNAME",  (0,1),(-1,-1),"Helvetica"),
                ("FONTSIZE",  (0,0),(-1,-1),8),
                ("ALIGN",     (0,0),(-1,-1),"CENTER"),
                ("ALIGN",     (0,1),(0,-1),"LEFT"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white,colors.HexColor("#f0f4f8")]),
                ("GRID",      (0,0),(-1,-1),0.3,colors.HexColor("#d1d5db")),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),5),
                ("VALIGN",    (0,0),(-1,-1),"MIDDLE"),
            ]))
            h.append(tbl)
            doc.build(h)
            QMessageBox.information(self,"PDF Kaydedildi", yol)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))
            logger.error(f"_pdf_al: {e}")

    def load_data(self):
        if self._db:
            self._birimleri_doldur()
            self._yukle()
