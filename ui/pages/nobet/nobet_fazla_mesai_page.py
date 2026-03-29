# -*- coding: utf-8 -*-
"""
nobet_fazla_mesai_page.py — Fazla Mesai Yönetimi (Birleşik)

Veri kaynağı önceliği:
  1. NB_MesaiHesap → plan onayında otomatik kaydedilen hesap
  2. NB_PlanSatir  → plan onaylanmamışsa canlı hesap (fallback)

Sekmeler:
  1. Personel Tablosu  — checkbox + toplu FM bildir + PDF + Excel
  2. Aylık Karşılaştırma — son 6 ay SVG bar grafik
"""
from __future__ import annotations

import csv
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QTabWidget,
)
from PySide6.QtSvgWidgets import QSvgWidget

from core.di import get_registry
from core.logger import logger

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}

HEDEF_GUNLUK = {
    "normal":7.0,"emzirme":5.5,"sendika":6.2,
    "sua":0.0,"rapor":7.0,"yillik":7.0,"idari":7.0,
}

FM_ESIK = 7.0  # saat


# ── Yardımcılar ────────────────────────────────────────────────

def _networkdays(bas: date, bit: date, tatiller: set) -> int:
    if bas > bit: return 0
    n, g = 0, bas
    while g <= bit:
        if g.weekday() < 5 and g.isoformat() not in tatiller: n += 1
        g += timedelta(days=1)
    return n

def _tatil_set(yil: int, ay: int, reg) -> set:
    try:
        rows = reg.get("Tatiller").get_all() or []
        ab, ae = f"{yil:04d}-{ay:02d}-01", f"{yil:04d}-{ay:02d}-31"
        return {str(r.get("Tarih","")) for r in rows
                if ab <= str(r.get("Tarih","")) <= ae
                and str(r.get("TatilTuru","Resmi")) in ("Resmi","DiniBayram")}
    except Exception: return set()

def _hedef_tipi(pid, birim_id, yil, ay, reg) -> str:
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next((r for r in rows
                  if str(r.get("PersonelID",""))==pid
                  and str(r.get("BirimID",""))==birim_id
                  and int(r.get("Yil",0))==yil
                  and int(r.get("Ay",0))==ay), None)
        return str((k or {}).get("HedefTipi","normal")).lower()
    except Exception: return "normal"

def _hedef_saat(pid, birim_id, yil, ay, reg) -> float:
    try:
        tatil  = _tatil_set(yil, ay, reg)
        ay_bas = date(yil, ay, 1)
        ay_bit = date(yil, ay, monthrange(yil, ay)[1])
        ay_is  = _networkdays(ay_bas, ay_bit, tatil)
        gun_s  = HEDEF_GUNLUK.get(_hedef_tipi(pid, birim_id, yil, ay, reg), 7.0)
        iz_rows = reg.get("Izin_Giris").get_all() or []
        iz_is = 0
        for r in iz_rows:
            if str(r.get("Personelid","")).strip() != pid: continue
            if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
            try:
                bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                bit = date.fromisoformat(str(r.get("BitisTarihi","")))
            except Exception: continue
            iz_is += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
        return round(max(0, ay_is - iz_is) * gun_s, 1)
    except Exception: return round(20*7.0, 1)

def _simdi() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")

def _fmt(s: float) -> str:
    if s == 0: return "—"
    return f"+{s:.1f}" if s > 0 else f"{s:.1f}"

def _it(text: str, data=None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    if data is not None: it.setData(Qt.ItemDataRole.UserRole, data)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


# ══════════════════════════════════════════════════════════════
#  Ana Sayfa
# ══════════════════════════════════════════════════════════════

class NobetFazlaMesaiPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db; self._ag = action_guard
        self._yil = date.today().year
        self._ay  = date.today().month
        self._birim_id = ""; self._birim_adi = ""
        self.setProperty("bg-role","page")
        self._build()
        if db: self._birimleri_doldur()

    def _reg(self): return get_registry(self._db)

    # ── UI ──────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        lay.addWidget(self._build_ozet_bar())
        tabs = QTabWidget()
        tabs.addTab(self._build_tablo_tab(),  "📋  Personel Tablosu")
        tabs.addTab(self._build_grafik_tab(), "📊  Aylık Karşılaştırma")
        lay.addWidget(tabs, 1)

    def _build_toolbar(self) -> QFrame:
        bar = QFrame(); bar.setProperty("bg-role","panel"); bar.setFixedHeight(46)
        h = QHBoxLayout(bar); h.setContentsMargins(12,0,12,0); h.setSpacing(8)
        for txt, slot in [("‹", self._ay_geri), ("›", self._ay_ileri)]:
            btn = QPushButton(txt); btn.setFixedSize(28,28)
            btn.setProperty("style-role","secondary"); btn.clicked.connect(slot)
            if txt == "‹": h.addWidget(btn)
            else:
                self._lbl_ay = QLabel()
                self._lbl_ay.setFixedWidth(120)
                self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._lbl_ay.setProperty("style-role","section-title")
                h.addWidget(self._lbl_ay)
                h.addWidget(btn)
        h.addSpacing(16)
        lbl = QLabel("Birim:"); lbl.setProperty("color-role","muted"); h.addWidget(lbl)
        self._cmb_birim = QComboBox(); self._cmb_birim.setMinimumWidth(200)
        self._cmb_birim.currentIndexChanged.connect(self._on_birim); h.addWidget(self._cmb_birim)
        h.addStretch()
        btn_r = QPushButton("↺  Yenile"); btn_r.setProperty("style-role","secondary")
        btn_r.setFixedHeight(28); btn_r.clicked.connect(self._yukle); h.addWidget(btn_r)
        return bar

    def _build_ozet_bar(self) -> QFrame:
        bar = QFrame(); bar.setProperty("bg-role","panel"); bar.setFixedHeight(68)
        h = QHBoxLayout(bar); h.setContentsMargins(16,6,16,6); h.setSpacing(0)
        self._kartlar: dict[str,QLabel] = {}
        for key, baslik, renk in [
            ("personel",  "Personel",           "#4d9ee8"),
            ("toplam_f",  "Toplam Fazla (s)",   "#f59e0b"),
            ("bildirildi","Bildirildi",          "#2ec98e"),
            ("bekliyor",  "FM Bekliyor",         "#f59e0b"),
            ("devir",     "Devire Giden (s)",    "#4d9ee8"),
        ]:
            f = QFrame(); fl = QVBoxLayout(f)
            fl.setContentsMargins(8,4,8,4); fl.setSpacing(1)
            v = QLabel("—"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(f"font-size:18px;font-weight:bold;color:{renk};")
            b = QLabel(baslik); b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setStyleSheet("font-size:9px;color:#6b7280;")
            fl.addWidget(v); fl.addWidget(b)
            self._kartlar[key] = v; h.addWidget(f, 1)
            if key != "devir":
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#2a3a4a;"); h.addWidget(sep)
        return bar

    def _build_tablo_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(8,8,8,4); lay.setSpacing(4)

        # Açıklama bandı
        acik = QLabel(
            "  ●  <b>Plan onaylıysa</b> kayıtlı hesap kullanılır  "
            "●  <b>Taslaksa</b> canlı hesap yapılır  "
            f"●  FM eşiği: ±{FM_ESIK:.0f}s")
        acik.setProperty("color-role","muted")
        acik.setStyleSheet("font-size:10px;padding:4px 8px;")
        lay.addWidget(acik)

        self._tbl = QTableWidget(0, 9)
        self._tbl.setHorizontalHeaderLabels([
            "✔","Ad Soyad",
            "Hedef\n(s)","Çalışılan\n(s)",
            "Bu Ay\n(s)","Önceki\nDevir (s)",
            "Toplam\n(s)","Durum",
            "Bildirim\nTarihi"])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tbl.setColumnWidth(0, 30)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2,9):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.setSortingEnabled(True)
        self._tbl.cellClicked.connect(self._chk_toggle)
        lay.addWidget(self._tbl, 1)

        alt = QHBoxLayout()
        self._btn_tumunu = QPushButton("☑  Tümünü Seç")
        self._btn_tumunu.setProperty("style-role","secondary")
        self._btn_tumunu.setFixedHeight(30); self._btn_tumunu.clicked.connect(self._tumunu_sec)
        alt.addWidget(self._btn_tumunu)

        self._btn_bildir = QPushButton("📋  Fazla Mesai Bildir")
        self._btn_bildir.setProperty("style-role","action")
        self._btn_bildir.setFixedHeight(30); self._btn_bildir.setEnabled(False)
        self._btn_bildir.clicked.connect(self._bildir); alt.addWidget(self._btn_bildir)

        self._btn_pdf = QPushButton("⬇ PDF")
        self._btn_pdf.setProperty("style-role","secondary")
        self._btn_pdf.setFixedHeight(30); self._btn_pdf.clicked.connect(self._pdf_al)
        alt.addWidget(self._btn_pdf)

        self._btn_excel = QPushButton("📊 Excel/CSV")
        self._btn_excel.setProperty("style-role","secondary")
        self._btn_excel.setFixedHeight(30); self._btn_excel.clicked.connect(self._excel_al)
        alt.addWidget(self._btn_excel)

        alt.addStretch()
        self._lbl_alt = QLabel(""); self._lbl_alt.setProperty("color-role","muted")
        self._lbl_alt.setStyleSheet("font-size:11px;"); alt.addWidget(self._lbl_alt)
        lay.addLayout(alt)
        return w

    def _build_grafik_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(8,8,8,8); lay.setSpacing(8)
        lbl = QLabel("Son 6 Ay — Kişi Başı Ortalama Fazla Mesai (saat)")
        lbl.setProperty("style-role","section-title"); lay.addWidget(lbl)
        self._svg = QSvgWidget(); self._svg.setMinimumHeight(300)
        lay.addWidget(self._svg, 1)
        self._lbl_grafik = QLabel("")
        self._lbl_grafik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_grafik.setProperty("color-role","muted")
        self._lbl_grafik.setStyleSheet("font-size:10px;")
        lay.addWidget(self._lbl_grafik)
        return w

    # ── Navigasyon ─────────────────────────────────────────────

    def _ay_geri(self):
        if self._ay==1: self._ay,self._yil=12,self._yil-1
        else: self._ay-=1
        self._yukle()

    def _ay_ileri(self):
        if self._ay==12: self._ay,self._yil=1,self._yil+1
        else: self._ay+=1
        self._yukle()

    def _on_birim(self):
        self._birim_id  = self._cmb_birim.currentData() or ""
        self._birim_adi = self._cmb_birim.currentText() or ""
        self._yukle()

    # ── Veri ───────────────────────────────────────────────────

    def _birimleri_doldur(self):
        try:
            reg  = self._reg()
            rows = sorted(reg.get("NB_Birim").get_all() or [],
                          key=lambda r: r.get("BirimAdi",""))
            self._cmb_birim.blockSignals(True)
            self._cmb_birim.clear()
            self._cmb_birim.addItem("Tüm Birimler", userData="")
            for r in rows:
                self._cmb_birim.addItem(r.get("BirimAdi",""), userData=r["BirimID"])
            self._cmb_birim.blockSignals(False)
            self._on_birim()
        except Exception as e: logger.error(f"birimleri_doldur: {e}")

    def _pid_listesi(self) -> list[tuple[str,str]]:
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            if self._birim_id:
                bp   = reg.get("NB_BirimPersonel").get_all() or []
                pids = [str(r.get("PersonelID","")) for r in bp
                        if str(r.get("BirimID",""))==self._birim_id
                        and int(r.get("Aktif",1))]
            else:
                pids = list(p_map.keys())
            return sorted([(p, p_map.get(p,p)) for p in pids if p],
                          key=lambda x: x[1])
        except Exception: return []

    def _plan_verileri(self, yil=None, ay=None) -> tuple[set, dict]:
        """Bu ay için plan_ids ve vardiya süre haritası."""
        yil = yil or self._yil; ay = ay or self._ay
        try:
            reg = self._reg()
            plan_rows = reg.get("NB_Plan").get_all() or []
            ids = {str(p["PlanID"]) for p in plan_rows
                   if int(p.get("Yil",0))==yil and int(p.get("Ay",0))==ay
                   and (not self._birim_id
                        or str(p.get("BirimID",""))==self._birim_id)}
            v_rows = reg.get("NB_Vardiya").get_all() or []
            v_sure = {str(v["VardiyaID"]): int(v.get("SureDakika",720)) for v in v_rows}
            return ids, v_sure
        except Exception: return set(), {}

    def _canlı_hesapla(self, pid: str, yil: int, ay: int) -> tuple[float,float,float]:
        """NB_PlanSatir'dan canlı hesap → (hedef_s, calisan_s, fazla_s)."""
        try:
            reg = self._reg()
            hedef   = _hedef_saat(pid, self._birim_id, yil, ay, reg)
            ids, v_sure = self._plan_verileri(yil, ay)
            ay_bas = date(yil, ay, 1).isoformat()
            ay_bit = date(yil, ay, monthrange(yil,ay)[1]).isoformat()
            satir_rows = reg.get("NB_PlanSatir").get_all() or []
            calisan = sum(
                v_sure.get(str(s.get("VardiyaID","")),720)/60
                for s in satir_rows
                if str(s.get("PersonelID",""))==pid
                and str(s.get("Durum",""))=="aktif"
                and str(s.get("PlanID","")) in ids
                and ay_bas <= str(s.get("NobetTarihi","")) <= ay_bit)
            return hedef, round(calisan,1), round(calisan-hedef,1)
        except Exception:
            return 140.0, 0.0, 0.0

    def _onceki_devir(self, pid: str) -> float:
        """Önceki ayın devir bakiyesi — DB > canlı."""
        ony = self._yil-1 if self._ay==1 else self._yil
        ona = 12 if self._ay==1 else self._ay-1
        try:
            reg = self._reg()
            mh  = reg.get("NB_MesaiHesap").get_all() or []
            k   = next((r for r in mh
                        if str(r.get("PersonelID",""))==pid
                        and int(r.get("Yil",0))==ony
                        and int(r.get("Ay",0))==ona
                        and (not self._birim_id
                             or str(r.get("BirimID",""))==self._birim_id)), None)
            if k and int(k.get("DevireGidenDakika",-1)) >= 0:
                return float(k.get("DevireGidenDakika",0))/60
            # Canlı hesap (max 2 seviye)
            return self._canli_devir(pid, ony, ona, 0)
        except Exception: return 0.0

    def _canli_devir(self, pid, yil, ay, derinlik) -> float:
        if derinlik > 3: return 0.0
        try:
            reg = self._reg()
            hedef = _hedef_saat(pid, self._birim_id, yil, ay, reg)
            ids, v_sure = self._plan_verileri(yil, ay)
            if not ids: return 0.0
            ay_bas = date(yil,ay,1).isoformat()
            ay_bit = date(yil,ay,monthrange(yil,ay)[1]).isoformat()
            satir_rows = reg.get("NB_PlanSatir").get_all() or []
            calisan = sum(
                v_sure.get(str(s.get("VardiyaID","")),720)/60
                for s in satir_rows
                if str(s.get("PersonelID",""))==pid
                and str(s.get("Durum",""))=="aktif"
                and str(s.get("PlanID","")) in ids
                and ay_bas <= str(s.get("NobetTarihi","")) <= ay_bit)
            bu_ay_f = round(calisan - hedef, 1)
            ony = yil-1 if ay==1 else yil
            ona = 12 if ay==1 else ay-1
            mh  = reg.get("NB_MesaiHesap").get_all() or []
            k   = next((r for r in mh
                        if str(r.get("PersonelID",""))==pid
                        and int(r.get("Yil",0))==ony
                        and int(r.get("Ay",0))==ona), None)
            if k and int(k.get("DevireGidenDakika",-1))>=0:
                onceki = float(k.get("DevireGidenDakika",0))/60
            else:
                onceki = self._canli_devir(pid, ony, ona, derinlik+1)
            bu_mh = next((r for r in mh
                          if str(r.get("PersonelID",""))==pid
                          and int(r.get("Yil",0))==yil
                          and int(r.get("Ay",0))==ay), None)
            if bu_mh and int(bu_mh.get("OdenenDakika",0))>0:
                return 0.0
            return round(bu_ay_f + onceki, 1)
        except Exception: return 0.0

    def _yukle(self):
        if not self._db: return
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")
        self._yukle_tablo()
        self._yukle_grafik()

    def _yukle_tablo(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            mh_all = reg.get("NB_MesaiHesap").get_all() or []

            def mh_bul(pid):
                return next((r for r in mh_all
                             if str(r.get("PersonelID",""))==pid
                             and int(r.get("Yil",0))==self._yil
                             and int(r.get("Ay",0))==self._ay
                             and (not self._birim_id
                                  or str(r.get("BirimID",""))==self._birim_id)), None)

            self._tbl.setSortingEnabled(False)
            self._tbl.setRowCount(0)
            toplam_f = bekliyor = bildirildi_s = devir_top = 0.0
            self._pid_veri: dict[str,dict] = {}  # FM bildir için

            for pid, ad in pidler:
                mh = mh_bul(pid)

                if mh:
                    # DB kaydı var → kullan
                    hedef   = float(mh.get("HedefDakika",0))/60
                    calisan = float(mh.get("CalisDakika",0))/60
                    bu_ay   = float(mh.get("FazlaDakika",0))/60
                    devir   = float(mh.get("DevirDakika",0))/60
                    top     = float(mh.get("ToplamFazlaDakika",0))/60
                    odenen  = int(mh.get("OdenenDakika",0))
                    tarih   = str(mh.get("HesapTarihi","") or "")[:10]
                    kaynak  = "📊"  # DB kaydı
                else:
                    # Canlı hesap
                    hedef, calisan, bu_ay = self._canlı_hesapla(pid, self._yil, self._ay)
                    devir  = self._onceki_devir(pid)
                    top    = round(bu_ay + devir, 1)
                    odenen = 0
                    tarih  = ""
                    kaynak = "⚡"  # Canlı

                self._pid_veri[pid] = {
                    "hedef_dk": int(hedef*60), "calis_dk": int(calisan*60),
                    "fazla_dk": int(bu_ay*60), "devir_dk": int(devir*60),
                    "toplam_dk": int(top*60), "mh": mh,
                }

                toplam_f  += max(0, bu_ay)
                devir_top += max(0, top if odenen==0 else 0)

                bil_mi = (odenen > 0)
                if bil_mi:
                    fm_lbl, fm_renk = "✔ Bildirildi", "#2ec98e"; bildirildi_s+=1
                elif top > FM_ESIK:
                    fm_lbl, fm_renk = "⏳ Bekliyor", "#f59e0b"; bekliyor+=1
                elif abs(top) <= FM_ESIK:
                    fm_lbl, fm_renk = "⇄ Alacak/Verecek", "#f3c55a"
                else:
                    fm_lbl, fm_renk = "↓ Eksik", "#e85555"

                ri = self._tbl.rowCount()
                self._tbl.insertRow(ri)

                chk = QTableWidgetItem("☐")
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                chk.setForeground(QColor("#6b7280"))
                chk.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl.setItem(ri, 0, chk)

                ad_itm = QTableWidgetItem(f"{kaynak} {ad}")
                ad_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl.setItem(ri, 1, ad_itm)

                self._tbl.setItem(ri, 2, _it(f"{hedef:.1f}"))
                self._tbl.setItem(ri, 3, _it(f"{calisan:.1f}"))

                for ci, (val, esik) in enumerate([(bu_ay, FM_ESIK),(devir,0),(top,FM_ESIK)], 4):
                    itm = _it(_fmt(val))
                    if val > esik:   itm.setForeground(QColor("#f59e0b"))
                    elif val < 0:    itm.setForeground(QColor("#e85555"))
                    elif val > 0:    itm.setForeground(QColor("#f3c55a"))
                    self._tbl.setItem(ri, ci, itm)

                d_itm = _it(fm_lbl); d_itm.setForeground(QColor(fm_renk))
                self._tbl.setItem(ri, 7, d_itm)
                self._tbl.setItem(ri, 8, _it(tarih if bil_mi else "—"))

            self._tbl.setSortingEnabled(True)
            self._kartlar["personel"].setText(str(len(pidler)))
            self._kartlar["toplam_f"].setText(f"{toplam_f:.0f}")
            self._kartlar["bildirildi"].setText(str(int(bildirildi_s)))
            self._kartlar["bildirildi"].setStyleSheet(
                f"font-size:18px;font-weight:bold;"
                f"color:{'#2ec98e' if bildirildi_s>0 else '#6b7280'};")
            self._kartlar["bekliyor"].setText(str(int(bekliyor)))
            self._kartlar["bekliyor"].setStyleSheet(
                f"font-size:18px;font-weight:bold;"
                f"color:{'#f59e0b' if bekliyor>0 else '#6b7280'};")
            self._kartlar["devir"].setText(f"{devir_top:.0f}")
            self._lbl_alt.setText(
                f"{len(pidler)} kişi  |  {int(bekliyor)} bekliyor  |  "
                f"{int(bildirildi_s)} bildirildi  |  "
                f"📊=DB kaydı  ⚡=Canlı hesap")
            self._btn_bildir.setEnabled(False)
        except Exception as e:
            logger.error(f"_yukle_tablo: {e}")

    # ── Grafik ─────────────────────────────────────────────────

    def _ay_fm_ort(self, yil: int, ay: int) -> tuple[float, float, float]:
        """(ortalama_fazla, maks_fazla, bildirildi_pct) → DB veya canlı."""
        try:
            reg = self._reg()
            pidler = self._pid_listesi()
            if not pidler: return 0, 0, 0
            mh_all = reg.get("NB_MesaiHesap").get_all() or []
            fazlalar, bildirildi = [], 0
            for pid, _ in pidler:
                k = next((r for r in mh_all
                          if str(r.get("PersonelID",""))==pid
                          and int(r.get("Yil",0))==yil
                          and int(r.get("Ay",0))==ay
                          and (not self._birim_id
                               or str(r.get("BirimID",""))==self._birim_id)), None)
                if k:
                    f = float(k.get("FazlaDakika",0))/60
                    if int(k.get("OdenenDakika",0)) > 0: bildirildi += 1
                else:
                    _, _, f = self._canlı_hesapla(pid, yil, ay)
                fazlalar.append(f)
            if not fazlalar: return 0, 0, 0
            ort  = sum(fazlalar)/len(fazlalar)
            maks = max(fazlalar)
            bil_pct = bildirildi/len(fazlalar)*100
            return round(ort,1), round(maks,1), round(bil_pct)
        except Exception: return 0, 0, 0

    def _yukle_grafik(self):
        try:
            aylar = []
            y, m = self._yil, self._ay
            for _ in range(6):
                aylar.insert(0, (y, m))
                m -= 1
                if m == 0: m, y = 12, y-1

            veri = []
            for y, m in aylar:
                ort, maks, bil_pct = self._ay_fm_ort(y, m)
                veri.append((f"{_AY[m][:3]}\n{y}", ort, maks, bil_pct))

            svg = self._svg_grafik(veri)
            self._svg.load(svg.encode("utf-8"))
            ozet = "  |  ".join(
                f"{v[0].replace(chr(10),' ')}: {v[1]:+.1f}s" for v in veri)
            self._lbl_grafik.setText(ozet)
        except Exception as e:
            logger.error(f"_yukle_grafik: {e}")

    def _svg_grafik(self, veri: list) -> str:
        W, H = 860, 320
        PL, PR, PT, PB = 60, 20, 30, 60
        gw = W-PL-PR; gh = H-PT-PB
        n = len(veri)
        bw = int(gw/n*0.5)

        vals = [abs(v[1]) for v in veri] + [abs(v[2]) for v in veri]
        maks_v = max(vals + [FM_ESIK+5])
        min_v  = min(v[1] for v in veri)
        if min_v > 0: min_v = 0

        def yx(v): return PT + int((maks_v-v)/(maks_v-min_v)*gh)
        def xx(i): return PL + int((i+0.5)*gw/n)

        ln = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
              f'<rect width="{W}" height="{H}" fill="#0d1b2a"/>']

        # Izgara
        span = max(1, int((maks_v-min_v)/5))
        for tick in range(int(min_v), int(maks_v)+1, span):
            yt = yx(tick)
            near_esik = abs(tick - FM_ESIK) < 0.5
            c = "#f59e0b" if near_esik else "#1e2e40"
            sw = "1.5" if near_esik else "0.5"
            ln.append(f'<line x1="{PL}" y1="{yt}" x2="{W-PR}" y2="{yt}" stroke="{c}" stroke-width="{sw}"/>')
            ln.append(f'<text x="{PL-6}" y="{yt+4}" text-anchor="end" font-size="10" fill="#6b7280">{tick:+.0f}</text>')

        ln.append(f'<text x="{W-PR+3}" y="{yx(FM_ESIK)+4}" font-size="9" fill="#f59e0b">+{FM_ESIK:.0f}s</text>')

        y0 = yx(0)
        for i, (lbl, ort, maks, bil_pct) in enumerate(veri):
            x = xx(i)
            if ort >= 0:
                yb = yx(ort); bh = max(y0-yb, 1)
                fill = "#f59e0b" if ort>FM_ESIK else "#4d9ee8"
            else:
                yb = y0; bh = max(yx(ort)-y0, 1); fill = "#e85555"
            ln.append(f'<rect x="{x-bw//2}" y="{yb}" width="{bw}" height="{bh}" fill="{fill}" opacity="0.85" rx="2"/>')
            if ort != 0:
                ly = yb-5 if ort>=0 else yb+bh+14
                ln.append(f'<text x="{x}" y="{ly}" text-anchor="middle" font-size="10" font-weight="bold" fill="{fill}">{ort:+.1f}</text>')
            if bil_pct > 0:
                bih = int(bh*bil_pct/100)
                biy = yb+bh-bih if ort>=0 else yb
                ln.append(f'<rect x="{x-bw//2}" y="{biy}" width="{bw}" height="{bih}" fill="#2ec98e" opacity="0.7" rx="2"/>')
            for j, s in enumerate(lbl.split("\n")):
                ln.append(f'<text x="{x}" y="{H-PB+16+j*13}" text-anchor="middle" font-size="10" fill="#6b7280">{s}</text>')

        ln.append(f'<line x1="{PL}" y1="{y0}" x2="{W-PR}" y2="{y0}" stroke="#3a5a7a" stroke-width="1"/>')
        pts = " ".join(f"{xx(i)},{yx(v[2])}" for i,v in enumerate(veri) if v[2]!=0)
        if pts:
            ln.append(f'<polyline points="{pts}" fill="none" stroke="#6b7280" stroke-width="1" stroke-dasharray="4,3"/>')

        for xi, (renk, txt) in enumerate([
            ("#4d9ee8","Ort. Fazla (≤+7s)"),("#f59e0b","Ort. Fazla (>+7s)"),
            ("#2ec98e","Bildirilen kısım"),("#6b7280","Maks (noktalı)"),
        ]):
            lx = PL + xi*200
            ln.append(f'<rect x="{lx}" y="{H-14}" width="10" height="10" fill="{renk}" rx="2"/>')
            ln.append(f'<text x="{lx+14}" y="{H-5}" font-size="9" fill="#6b7280">{txt}</text>')

        ln.append("</svg>")
        return "\n".join(ln)

    # ── Checkbox ───────────────────────────────────────────────

    def _chk_toggle(self, row, col):
        if col != 0: return
        itm = self._tbl.item(row, 0)
        if not itm: return
        sec = itm.text() == "☑"
        itm.setText("☐" if sec else "☑")
        itm.setForeground(QColor("#6b7280" if sec else "#2ec98e"))
        self._btn_bildir.setEnabled(bool(self._secili()))

    def _tumunu_sec(self):
        tum = all((self._tbl.item(r,0) or QTableWidgetItem()).text()=="☑"
                  for r in range(self._tbl.rowCount()))
        for r in range(self._tbl.rowCount()):
            itm = self._tbl.item(r,0)
            if itm:
                itm.setText("☐" if tum else "☑")
                itm.setForeground(QColor("#6b7280" if tum else "#2ec98e"))
        self._btn_bildir.setEnabled(not tum and self._tbl.rowCount()>0)

    def _secili(self) -> list[str]:
        return [self._tbl.item(r,0).data(Qt.ItemDataRole.UserRole)
                for r in range(self._tbl.rowCount())
                if self._tbl.item(r,0) and self._tbl.item(r,0).text()=="☑"]

    # ── FM Bildir ──────────────────────────────────────────────

    def _bildir(self):
        pidler = self._secili()
        if not pidler: return
        cevap = QMessageBox.question(
            self,"Fazla Mesai Bildir",
            f"{len(pidler)} personel için FM bildirimi yapılacak.\n"
            "Devire giden bakiyeler sıfırlanacak. Emin misiniz?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes: return
        try:
            reg   = self._reg()
            simdi = _simdi()
            plan_rows = reg.get("NB_Plan").get_all() or []
            tamam = 0
            for pid in pidler:
                vr = self._pid_veri.get(pid, {})
                toplam_dk = vr.get("toplam_dk", 0)
                mh = vr.get("mh")
                kayit_veri = {
                    "OdenenDakika":      toplam_dk,
                    "DevireGidenDakika": 0,
                    "HesapDurumu":       "tamamlandi",
                    "HesapTarihi":       simdi,
                    "updated_at":        simdi,
                }
                if mh:
                    reg.get("NB_MesaiHesap").update(mh["HesapID"], kayit_veri)
                else:
                    # Canlı hesaptan yeni kayıt oluştur
                    plan = next((p for p in plan_rows
                                 if int(p.get("Yil",0))==self._yil
                                 and int(p.get("Ay",0))==self._ay
                                 and (not self._birim_id
                                      or str(p.get("BirimID",""))==self._birim_id)), None)
                    reg.get("NB_MesaiHesap").insert({
                        "HesapID":           str(uuid.uuid4()),
                        "PersonelID":        pid,
                        "BirimID":           self._birim_id or "",
                        "PlanID":            plan["PlanID"] if plan else "",
                        "Yil":               self._yil,
                        "Ay":                self._ay,
                        "CalisDakika":       vr.get("calis_dk",0),
                        "HedefDakika":       vr.get("hedef_dk",0),
                        "FazlaDakika":       vr.get("fazla_dk",0),
                        "DevirDakika":       vr.get("devir_dk",0),
                        "ToplamFazlaDakika": toplam_dk,
                        "created_at":        simdi,
                        **kayit_veri,
                    })
                tamam += 1
            QMessageBox.information(self,"Tamamlandı",
                f"{tamam} personel FM bildirimi yapıldı.")
            self._yukle()
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    # ── PDF ────────────────────────────────────────────────────

    def _pdf_al(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer)
            from PySide6.QtWidgets import QFileDialog
            yol, _ = QFileDialog.getSaveFileName(
                self,"PDF Kaydet",
                f"FM_Rapor_{_AY[self._ay]}_{self._yil}.pdf","PDF (*.pdf)")
            if not yol: return
            birim_str = self._birim_adi or "Tüm Birimler"
            styles = getSampleStyleSheet()
            bs  = ParagraphStyle("b",parent=styles["Title"],fontSize=13,spaceAfter=3)
            as_ = ParagraphStyle("a",parent=styles["Normal"],fontSize=8,
                                 textColor=colors.grey,spaceAfter=6)
            doc = SimpleDocTemplate(yol,pagesize=landscape(A4),
                leftMargin=1.5*cm,rightMargin=1.5*cm,
                topMargin=1.5*cm,bottomMargin=1.5*cm)
            h = []
            h.append(Paragraph(f"Fazla Mesai Raporu — {_AY[self._ay]} {self._yil}",bs))
            h.append(Paragraph(
                f"Birim: {birim_str}  |  "
                f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",as_))
            h.append(Spacer(1,0.3*cm))
            basliklar = ["Ad Soyad","Hedef (s)","Çalışılan (s)",
                         "Bu Ay (s)","Önceki Devir (s)","Toplam (s)","Durum","Bildirim"]
            veri = [basliklar]
            for r in range(self._tbl.rowCount()):
                veri.append([(self._tbl.item(r,c) or QTableWidgetItem()).text()
                              for c in range(1,9)])
            gen = [4.5*cm,1.8*cm,2*cm,1.8*cm,2.2*cm,1.8*cm,3.5*cm,2*cm]
            tbl = Table(veri,colWidths=gen,repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
                ("FONTSIZE",(0,0),(-1,-1),7.5),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("ALIGN",(0,1),(0,-1),"LEFT"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white,colors.HexColor("#f0f4f8")]),
                ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#d1d5db")),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),4),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ]))
            h.append(tbl)
            h.append(Spacer(1,0.3*cm))
            h.append(Paragraph(
                f"FM eşiği ±{FM_ESIK:.0f}s  |  {self._tbl.rowCount()} kayıt  |  "
                f"📊=DB kaydı  ⚡=Canlı hesap",as_))
            doc.build(h)
            QMessageBox.information(self,"PDF Kaydedildi",yol)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e)); logger.error(f"_pdf_al: {e}")

    # ── Excel/CSV ──────────────────────────────────────────────

    def _excel_al(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            yol, _ = QFileDialog.getSaveFileName(
                self,"CSV Kaydet",
                f"FM_Rapor_{_AY[self._ay]}_{self._yil}.csv","CSV (*.csv)")
            if not yol: return
            basliklar = ["Ad Soyad","Hedef (s)","Çalışılan (s)",
                         "Bu Ay (s)","Önceki Devir (s)","Toplam (s)","Durum","Bildirim"]
            satirlar = [basliklar]
            for r in range(self._tbl.rowCount()):
                satirlar.append([(self._tbl.item(r,c) or QTableWidgetItem()).text()
                                 for c in range(1,9)])
            with open(yol,"w",newline="",encoding="utf-8-sig") as f:
                csv.writer(f).writerows(satirlar)
            QMessageBox.information(self,"CSV Kaydedildi",yol)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def load_data(self):
        if self._db: self._birimleri_doldur()
