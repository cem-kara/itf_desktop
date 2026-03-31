# -*- coding: utf-8 -*-
"""
nobet_hazirlik_page.py — Nöbet Ön Hazırlık (İçerik Modülü)

Sadece personel durum tablosunu render eder.
Toolbar, kapasite bar, onay → nobet_merkez_page.py tarafından yönetilir.

Dışarıya açık metodlar:
  yukle(birim_id, birim_adi, yil, ay)  — merkez tarafından çağrılır
  tercih_duzenle()                      — seçili satır için dialog
  personel_ozet() -> dict               — {izinli, fm, uyari} sayıları
"""
from __future__ import annotations
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QComboBox,
)
from core.di import get_registry
from core.hata_yonetici import hata_goster
from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}
HEDEF_GUNLUK  = {"normal":7.0,"emzirme":5.5,"sendika":6.2}
HEDEF_TIPLER  = [
    ("normal","Normal  (7.0 s/gün)"),("emzirme","Emzirme (5.5 s/gün)"),
    ("sendika","Sendika (6.2 s/gün)"),
]
DEVIR_ESIK = 14.0


def _networkdays(bas, bit, tatiller):
    if bas > bit: return 0
    n, g = 0, bas
    while g <= bit:
        if g.weekday() < 5 and g.isoformat() not in tatiller: n += 1
        g += timedelta(days=1)
    return n

def _tatil_set(yil, ay, reg):
    try:
        rows = reg.get("Tatiller").get_all() or []
        ab, ae = f"{yil:04d}-{ay:02d}-01", f"{yil:04d}-{ay:02d}-31"
        return {str(r.get("Tarih","")) for r in rows
                if ab <= str(r.get("Tarih","")) <= ae
                and str(r.get("TatilTuru","")) in ("Resmi","DiniBayram")}
    except: return set()

def _hedef_tipi(pid, birim_id, yil, ay, reg):
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next((r for r in rows
                  if str(r.get("PersonelID",""))==pid
                  and str(r.get("BirimID",""))==birim_id
                  and int(r.get("Yil",0))==yil
                  and int(r.get("Ay",0))==ay), None)
        return str((k or {}).get("HedefTipi","normal")).lower()
    except: return "normal"

def _fm_gonullu(pid, birim_id, yil, ay, reg):
    try:
        rows = reg.get("NB_PersonelTercih").get_all() or []
        k = next((r for r in rows
                  if str(r.get("PersonelID",""))==pid
                  and str(r.get("BirimID",""))==birim_id
                  and int(r.get("Yil",0))==yil
                  and int(r.get("Ay",0))==ay), None)
        return str((k or {}).get("NobetTercihi",""))=="fazla_mesai_gonullu"
    except: return False

def _hedef_saat(pid, birim_id, yil, ay, reg):
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
            if str(r.get("Personelid","")).strip() != str(pid).strip(): continue
            if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
            try:
                bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                bit = date.fromisoformat(str(r.get("BitisTarihi","")))
            except: continue
            izin_is += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
        return round(max(0, ay_is - izin_is) * gun_s, 1)
    except: return round(20*7.0, 1)

def _it(text, pid=""):
    it = QTableWidgetItem(str(text))
    it.setData(Qt.ItemDataRole.UserRole, pid)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


class _TercihDialog(QDialog):
    def __init__(self, ad, yil, ay, kayit=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Tercih — {ad}")
        self.setModal(True); self.setMinimumWidth(340)
        self.setProperty("bg-role","page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20,20,20,20); lay.setSpacing(10)
        lay.addWidget(QLabel(f"<b>{ad}</b>  —  {_AY[ay]} {yil}"))
        form = QFormLayout()
        self._chk = QCheckBox("FM Gönüllüsü")
        self._chk.setChecked((kayit or {}).get("NobetTercihi","")=="fazla_mesai_gonullu")
        form.addRow("Fazla Mesai:", self._chk)
        self._cmb = QComboBox()
        for val, lbl in HEDEF_TIPLER: self._cmb.addItem(lbl, userData=val)
        mevcut = (kayit or {}).get("HedefTipi","normal")
        self._cmb.setCurrentIndex(next((i for i,(v,_) in enumerate(HEDEF_TIPLER) if v==mevcut),0))
        form.addRow("Hedef Tipi:", self._cmb)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "NobetTercihi": "fazla_mesai_gonullu" if self._chk.isChecked() else "zorunlu",
            "HedefTipi": self._cmb.currentData(),
        }


class NobetHazirlikPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db; self._yil = date.today().year
        self._ay = date.today().month
        self._birim_id = ""; self._birim_adi = ""
        self.setProperty("bg-role","page")
        self._build()

    def _reg(self): return get_registry(self._db)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8,8,8,4); lay.setSpacing(4)

        ust = QHBoxLayout()
        ust.addWidget(QLabel("Personel Durumu", styleSheet="font-weight:bold;"))
        ust.addStretch()
        ust.addWidget(QLabel("Çift tıkla → FM / Hedef Tipi düzenle",
                             styleSheet="font-size:10px;color:#6b7280;"))
        lay.addLayout(ust)

        self._tbl = QTableWidget(0, 7)
        self._tbl.setHorizontalHeaderLabels(
            ["Ad Soyad","Hedef\nSaat","Hedef\nTipi",
             "FM\nGönüllü","İzin\nGünü","Önceki\nDevir","Durum"])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1,7):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.setSortingEnabled(True)
        self._tbl.doubleClicked.connect(self.tercih_duzenle)
        lay.addWidget(self._tbl, 1)

        alt = QHBoxLayout()
        self._btn_tercih = QPushButton("Tercih Düzenle")
        self._btn_tercih.setProperty("style-role","secondary")
        self._btn_tercih.setFixedHeight(28)
        self._btn_tercih.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_tercih, "edit", color=IconColors.MUTED, size=14)
        self._btn_tercih.clicked.connect(self.tercih_duzenle)
        alt.addWidget(self._btn_tercih)
        alt.addStretch()
        self._lbl_alt = QLabel("")
        self._lbl_alt.setStyleSheet("font-size:11px;color:#6b7280;")
        alt.addWidget(self._lbl_alt)
        lay.addLayout(alt)

        self._tbl.selectionModel().selectionChanged.connect(
            lambda: self._btn_tercih.setEnabled(self._tbl.currentRow() >= 0))

    # ── Dışarıya açık API ─────────────────────────────────────

    def yukle(self, birim_id, birim_adi, yil, ay):
        self._birim_id = birim_id; self._birim_adi = birim_adi
        self._yil = yil; self._ay = ay
        if birim_id:
            self._yukle_personel()
        else:
            self._tbl.setRowCount(0); self._lbl_alt.setText("")

    def tercih_duzenle(self):
        row = self._tbl.currentRow()
        if row < 0: return
        itm = self._tbl.item(row, 0)
        pid = itm.data(Qt.ItemDataRole.UserRole); ad = itm.text()
        try:
            reg    = self._reg()
            t_rows = reg.get("NB_PersonelTercih").get_all() or []
            kayit  = next((r for r in t_rows
                           if str(r.get("PersonelID",""))==pid
                           and str(r.get("BirimID",""))==self._birim_id
                           and int(r.get("Yil",0))==self._yil
                           and int(r.get("Ay",0))==self._ay), None)
            dialog = _TercihDialog(ad, self._yil, self._ay, kayit, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            veri  = dialog.get_data()
            simdi = datetime.now().isoformat(sep=" ", timespec="seconds")
            if kayit:
                reg.get("NB_PersonelTercih").update(kayit["TercihID"],{**veri,"updated_at":simdi})
            else:
                reg.get("NB_PersonelTercih").insert({
                    "TercihID":str(uuid.uuid4()),"PersonelID":pid,
                    "BirimID":self._birim_id or "","Yil":self._yil,
                    "Ay":self._ay,"created_at":simdi,**veri})
            self._yukle_personel()
        except Exception as e:
            hata_goster(self, str(e), "Hata")

    def personel_ozet(self):
        """Merkez kapasite barı için {izinli, fm, uyari}."""
        try:
            reg = self._reg()
            pidler = self._pid_listesi()
            izinli = fm = uyari = 0
            for pid, _ in pidler:
                iz = self._izin_gun_sayisi(pid, reg)
                dv = self._onceki_devir(pid, reg)
                if iz > 0: izinli += 1
                if _fm_gonullu(pid, self._birim_id, self._yil, self._ay, reg): fm += 1
                if dv > DEVIR_ESIK: uyari += 1
            return {"izinli": izinli, "fm": fm, "uyari": uyari}
        except: return {"izinli":0,"fm":0,"uyari":0}

    # ── İç metodlar ───────────────────────────────────────────

    def _pid_listesi(self):
        if not self._birim_id: return []
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            pids  = [str(r.get("PersonelID","")) for r in bp
                     if str(r.get("BirimID",""))==self._birim_id and int(r.get("Aktif",1))]
            return sorted([(p, p_map.get(p,p)) for p in pids if p], key=lambda x: x[1])
        except: return []

    def _izin_gun_sayisi(self, pid, reg):
        try:
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay, monthrange(self._yil, self._ay)[1])
            rows   = reg.get("Izin_Giris").get_all() or []
            toplam = 0
            for r in rows:
                if str(r.get("Personelid","")).strip() != pid.strip(): continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR: continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except: continue
                toplam += _networkdays(max(bas,ay_bas), min(bit,ay_bit), tatil)
            return toplam
        except: return 0

    def _onceki_devir(self, pid, reg):
        try:
            if self._ay==1: ony,ona = self._yil-1,12
            else: ony,ona = self._yil,self._ay-1
            mh = reg.get("NB_MesaiHesap").get_all() or []
            k  = next((r for r in mh
                       if str(r.get("PersonelID",""))==pid
                       and int(r.get("Yil",0))==ony and int(r.get("Ay",0))==ona
                       and (not self._birim_id or str(r.get("BirimID",""))==self._birim_id)),None)
            return float((k or {}).get("DevireGidenDakika",0))/60
        except: return 0.0

    def _yukle_personel(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay, monthrange(self._yil, self._ay)[1])
            ay_is  = _networkdays(ay_bas, ay_bit, tatil)
            self._tbl.setSortingEnabled(False)
            self._tbl.setRowCount(0)
            fm_sayi = uyari_sayi = izinli_sayi = 0

            for pid, ad in pidler:
                tip      = _hedef_tipi(pid, self._birim_id, self._yil, self._ay, reg)
                hedef    = _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                fm       = _fm_gonullu(pid, self._birim_id, self._yil, self._ay, reg)
                izin_gun = self._izin_gun_sayisi(pid, reg)
                devir    = self._onceki_devir(pid, reg)
                if fm: fm_sayi += 1
                if izin_gun > 0: izinli_sayi += 1

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
                if izin_gun > 0: iz_itm.setForeground(QColor("#f59e0b"))
                self._tbl.setItem(ri, 4, iz_itm)

                if devir==0:  dl,dr = "—","#6b7280"
                elif devir>0: dl,dr = (f"+{devir:.0f} s","#f59e0b" if devir>DEVIR_ESIK else "#f3c55a")
                else:         dl,dr = f"{devir:.0f} s","#e85555"
                dv_itm = _it(dl, pid); dv_itm.setForeground(QColor(dr))
                self._tbl.setItem(ri, 5, dv_itm)

                if hedef==0 and tip=="sua":   sl,sr = "Şua — nöbet yok","#6b7280"
                elif izin_gun>=ay_is:          sl,sr = "Tam ay izin","#6b7280"
                elif devir>DEVIR_ESIK:         sl,sr = "Yüksek devir","#f59e0b"; uyari_sayi+=1
                else:                          sl,sr = "Hazır","#2ec98e"
                st_itm = _it(sl, pid); st_itm.setForeground(QColor(sr))
                self._tbl.setItem(ri, 6, st_itm)

            self._tbl.setSortingEnabled(True)
            self._lbl_alt.setText(
                f"{len(pidler)} personel  |  {izinli_sayi} izinli  |  "
                f"{fm_sayi} FM Gönüllü  |  {uyari_sayi} uyarı")
        except Exception as e:
            logger.error(f"yukle_personel: {e}")
