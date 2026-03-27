# -*- coding: utf-8 -*-
"""
nobet_ozet_page.py — Personel Nöbet & Fazla Mesai Özeti

Sekmeler:
  1. Nöbet Özeti     — kişi başı nöbet/saat/hedef/fazla, haftalık dağılım
  2. İzin Durumu     — kim izinli, kaç gün, hedef saat etkisi
  3. Fazla Mesai     — FM raporu takibi

FM Kuralı:
  - +7s üzeri → FM raporu bekliyor  (turuncu)
  - ±7s arası → Alacak/Verecek       (normal, sarı)
  - -7s altı  → Eksik                (kırmızı)
  - FM raporu alındıktan sonra → "Rapor Alındı" işaretle → 0'a sıfırla
  - Önceki ayın deviri → bu ayın toplam fazlasına eklenir
  - Parasal hesap YOK
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
    QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
    QScrollArea,
)

from core.di import get_registry
from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}

HEDEF_GUNLUK = {
    "normal":  7.0,
    "emzirme": 5.5,
    "sendika": 6.2,
    "sua":     0.0,
    "rapor":   7.0,
    "yillik":  7.0,
    "idari":   7.0,
}

FM_ESIK = 7.0  # saat — bu eşiğin üstü FM raporu bekliyor


# ══════════════════════════════════════════════════════════════
#  Yardımcılar
# ══════════════════════════════════════════════════════════════

def _networkdays(bas: date, bit: date, tatiller: set) -> int:
    if bas > bit:
        return 0
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


def _hedef_saat(pid: str, birim_id: str, yil: int, ay: int, reg) -> float:
    """(ay_is_gunu - izin_is_gunu) × günlük_saat (Excel NETWORKDAYS mantığı)."""
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
            izin_is += _networkdays(
                max(bas, ay_bas), min(bit, ay_bit), tatil)
        return round(max(0, ay_is - izin_is) * gun_s, 1)
    except Exception as e:
        logger.debug(f"_hedef_saat({pid}): {e}")
        return round(20 * 7.0, 1)


def _it(text: str, pid: str = "") -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setData(Qt.ItemDataRole.UserRole, pid)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


def _simdi() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


# ══════════════════════════════════════════════════════════════
#  Ana Sayfa
# ══════════════════════════════════════════════════════════════

class NobetOzetPage(QWidget):

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
    #  UI İnşası
    # ──────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_nobet_tab(),  "Nöbet Özeti")
        self._tabs.addTab(self._build_dagilim_tab(),"Günlük Dağılım")
        self._tabs.addTab(self._build_izin_tab(),   "İzin Durumu")
        self._tabs.addTab(self._build_fm_tab(),     "Fazla Mesai")
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
        btn_g.setProperty("style-role", "secondary")
        btn_g.clicked.connect(self._ay_geri)
        h.addWidget(btn_g)

        self._lbl_ay = QLabel()
        self._lbl_ay.setFixedWidth(130)
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role", "section-title")
        h.addWidget(self._lbl_ay)

        btn_i = QPushButton("›")
        btn_i.setFixedSize(28, 28)
        btn_i.setProperty("style-role", "secondary")
        btn_i.clicked.connect(self._ay_ileri)
        h.addWidget(btn_i)

        h.addSpacing(16)
        lbl = QLabel("Birim:")
        lbl.setProperty("color-role", "muted")
        h.addWidget(lbl)

        self._cmb_birim = QComboBox()
        self._cmb_birim.setMinimumWidth(180)
        self._cmb_birim.currentIndexChanged.connect(self._on_birim_sec)
        h.addWidget(self._cmb_birim)
        h.addStretch()

        btn_yenile = QPushButton("Yenile")
        btn_yenile.setProperty("style-role", "secondary")
        btn_yenile.setFixedHeight(28)
        IconRenderer.set_button_icon(
            btn_yenile, "refresh", color=IconColors.MUTED, size=14)
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

    def _build_nobet_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        self._tbl_nobet = self._tablo([
            "Ad Soyad", "Nöbet", "Hedef Tipi",
            "Çalışılan s", "Hedef s", "Fark", "Durum",
        ])
        lay.addWidget(self._tbl_nobet, 1)

        self._lbl_nobet_alt = QLabel("")
        self._lbl_nobet_alt.setProperty("color-role", "muted")
        self._lbl_nobet_alt.setStyleSheet("font-size:11px;padding:2px 4px;")
        lay.addWidget(self._lbl_nobet_alt)
        return w

    def _build_dagilim_tab(self) -> QWidget:
        """Personel × gün matrisi — o gün nöbet varsa işaretli."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        self._tbl_dag = QTableWidget(0, 0)
        self._tbl_dag.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_dag.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_dag.setAlternatingRowColors(True)
        self._tbl_dag.verticalHeader().setVisible(False)
        self._tbl_dag.setShowGrid(True)
        lay.addWidget(self._tbl_dag, 1)

        self._lbl_dag_alt = QLabel("")
        self._lbl_dag_alt.setProperty("color-role", "muted")
        self._lbl_dag_alt.setStyleSheet("font-size:11px;padding:2px 4px;")
        lay.addWidget(self._lbl_dag_alt)
        return w

    def _build_izin_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        self._tbl_izin = self._tablo([
            "Ad Soyad", "Başlangıç", "Bitiş",
            "İş Günü", "İzin Tipi", "Hedef Etkisi",
        ])
        lay.addWidget(self._tbl_izin, 1)

        self._lbl_izin_alt = QLabel("")
        self._lbl_izin_alt.setProperty("color-role", "muted")
        self._lbl_izin_alt.setStyleSheet("font-size:11px;padding:2px 4px;")
        lay.addWidget(self._lbl_izin_alt)
        return w

    def _build_fm_tab(self) -> QWidget:
        """
        FM Kuralı:
          Toplam > +7s → FM Bildirimi bekliyor (turuncu)
          ±7s arası    → Alacak/Verecek (sarı, normal kabul)
          < -7s        → Eksik mesai (kırmızı)
          FM Bildir    → DevireGidenDakika = 0, bakiye sıfırlanır
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 4)
        lay.setSpacing(4)

        aciklama = QLabel(
            "  ●  <b>+7s üzeri</b>: FM bildirimi bekliyor  "
            "●  <b>±7s arası</b>: Alacak/Verecek (normal)  "
            "●  FM Bildir → bakiye sıfırlanır")
        aciklama.setProperty("color-role", "muted")
        aciklama.setStyleSheet("font-size:10px;padding:4px 8px;")
        lay.addWidget(aciklama)

        # Çoklu seçim için checkbox sütunlu tablo
        self._tbl_fm = QTableWidget(0, 7)
        self._tbl_fm.setHorizontalHeaderLabels([
            "Seç", "Ad Soyad",
            "Bu Ay\nFazla",
            "Önceki\nDevir",
            "Toplam\nFazla",
            "FM\nDurumu",
            "Devire\nGiden",
        ])
        hdr = self._tbl_fm.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tbl_fm.setColumnWidth(0, 30)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 7):
            hdr.setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl_fm.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_fm.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_fm.setAlternatingRowColors(True)
        self._tbl_fm.verticalHeader().setVisible(False)
        self._tbl_fm.setShowGrid(False)
        self._tbl_fm.setSortingEnabled(True)
        # Checkbox sütununa tıklayınca seçimi aç/kapat
        self._tbl_fm.cellClicked.connect(self._fm_chk_toggle)
        lay.addWidget(self._tbl_fm, 1)

        alt = QHBoxLayout()

        self._btn_fm_tumunu = QPushButton("Tümünü Seç")
        self._btn_fm_tumunu.setProperty("style-role", "secondary")
        self._btn_fm_tumunu.setFixedHeight(28)
        IconRenderer.set_button_icon(
            self._btn_fm_tumunu, "check_square", color=IconColors.MUTED, size=14)
        self._btn_fm_tumunu.clicked.connect(self._fm_tumunu_sec)
        alt.addWidget(self._btn_fm_tumunu)

        self._btn_fm_bildir = QPushButton("Fazla Mesai Bildir")
        self._btn_fm_bildir.setProperty("style-role", "action")
        self._btn_fm_bildir.setFixedHeight(28)
        self._btn_fm_bildir.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_fm_bildir, "clipboard_list", color=IconColors.PRIMARY, size=14)
        self._btn_fm_bildir.clicked.connect(self._fm_bildir)
        alt.addWidget(self._btn_fm_bildir)

        self._btn_fm_pdf = QPushButton("PDF")
        self._btn_fm_pdf.setProperty("style-role", "secondary")
        self._btn_fm_pdf.setFixedHeight(28)
        self._btn_fm_pdf.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_fm_pdf, "file_pdf", color=IconColors.MUTED, size=14)
        self._btn_fm_pdf.clicked.connect(self._fm_pdf)
        alt.addWidget(self._btn_fm_pdf)

        alt.addStretch()
        self._lbl_fm_alt = QLabel("")
        self._lbl_fm_alt.setProperty("color-role", "muted")
        self._lbl_fm_alt.setStyleSheet("font-size:11px;")
        alt.addWidget(self._lbl_fm_alt)
        lay.addLayout(alt)
        return w

    def _build_footer(self) -> QFrame:
        f = QFrame()
        f.setProperty("bg-role", "panel")
        f.setFixedHeight(24)
        h = QHBoxLayout(f)
        h.setContentsMargins(12, 0, 12, 0)
        self._lbl_status = QLabel("")
        self._lbl_status.setProperty("color-role", "muted")
        self._lbl_status.setStyleSheet("font-size:10px;")
        h.addWidget(self._lbl_status)
        return f

    # ──────────────────────────────────────────────────────────
    #  Navigasyon
    # ──────────────────────────────────────────────────────────

    def _ay_geri(self):
        if self._ay == 1:
            self._ay, self._yil = 12, self._yil - 1
        else:
            self._ay -= 1
        self._yukle()

    def _ay_ileri(self):
        if self._ay == 12:
            self._ay, self._yil = 1, self._yil + 1
        else:
            self._ay += 1
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
        if not self._db:
            return
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")
        self._yukle_nobet()
        self._yukle_dagilim()
        self._yukle_izin()
        self._yukle_fm()
        birim_str = self._cmb_birim.currentText() or "Tüm Birimler"
        self._lbl_status.setText(
            f"Güncellendi: {_AY[self._ay]} {self._yil}  —  {birim_str}")

    def _pid_listesi(self) -> list[tuple[str,str]]:
        """[(pid, ad), ...] seçili birime göre."""
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            if self._birim_id:
                bp   = reg.get("NB_BirimPersonel").get_all() or []
                pids = [
                    str(r.get("PersonelID","")) for r in bp
                    if str(r.get("BirimID","")) == self._birim_id
                    and int(r.get("Aktif",1))]
            else:
                pids = list(p_map.keys())
            return sorted(
                [(p, p_map.get(p,p)) for p in pids if p],
                key=lambda x: x[1])
        except Exception:
            return []

    def _plan_verileri(self) -> tuple[set, dict]:
        """(birim_plan_ids, v_sure) — bu ay bu birim plan satırları için."""
        try:
            reg = self._reg()
            plan_rows = reg.get("NB_Plan").get_all() or []
            birim_plan_ids = {
                str(p["PlanID"]) for p in plan_rows
                if int(p.get("Yil",0)) == self._yil
                and int(p.get("Ay",0)) == self._ay
                and (not self._birim_id
                     or str(p.get("BirimID","")) == self._birim_id)
            }
            v_rows = reg.get("NB_Vardiya").get_all() or []
            v_sure = {str(v["VardiyaID"]): int(v.get("SureDakika",720))
                      for v in v_rows}
            return birim_plan_ids, v_sure
        except Exception:
            return set(), {}

    # ──────────────────────────────────────────────────────────
    #  Sekme 1: Nöbet Özeti
    # ──────────────────────────────────────────────────────────

    def _yukle_nobet(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            if not pidler:
                self._tbl_nobet.setRowCount(0)
                return

            ay_bas = date(self._yil, self._ay, 1).isoformat()
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1]).isoformat()
            birim_plan_ids, v_sure = self._plan_verileri()

            satir_rows  = reg.get("NB_PlanSatir").get_all() or []
            nobet_sayac: dict[str,int]   = {}
            saat_sayac:  dict[str,float] = {}

            for s in satir_rows:
                if str(s.get("Durum","")) != "aktif":
                    continue
                if str(s.get("PlanID","")) not in birim_plan_ids:
                    continue
                t = str(s.get("NobetTarihi",""))
                if not (ay_bas <= t <= ay_bit):
                    continue
                pid = str(s.get("PersonelID",""))
                nobet_sayac[pid] = nobet_sayac.get(pid, 0) + 1
                saat_sayac[pid]  = (saat_sayac.get(pid, 0.0)
                                    + v_sure.get(str(s.get("VardiyaID","")), 720) / 60)

            toplam = sum(nobet_sayac.values())
            ort    = toplam / max(len(pidler), 1)

            self._tbl_nobet.setSortingEnabled(False)
            self._tbl_nobet.setRowCount(0)

            for pid, ad in pidler:
                tip     = _hedef_tipi(pid, self._birim_id, self._yil, self._ay, reg)
                hedef   = _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                calisan = round(saat_sayac.get(pid, 0.0), 1)
                sayi    = nobet_sayac.get(pid, 0)
                fark    = round(calisan - hedef, 1)

                ri = self._tbl_nobet.rowCount()
                self._tbl_nobet.insertRow(ri)
                self._tbl_nobet.setItem(ri, 0, _it(ad, pid))
                self._tbl_nobet.setItem(ri, 1, _it(str(sayi), pid))

                tip_itm = _it(tip.capitalize() if tip else "Normal", pid)
                if tip not in ("normal","rapor","yillik","idari",""):
                    tip_itm.setForeground(QColor("#f59e0b"))
                self._tbl_nobet.setItem(ri, 2, tip_itm)

                self._tbl_nobet.setItem(ri, 3, _it(f"{calisan:.0f}", pid))
                self._tbl_nobet.setItem(ri, 4, _it(f"{hedef:.0f}", pid))

                isaret = "+" if fark > 0 else ""
                fark_itm = _it(f"{isaret}{fark:.0f}", pid)
                if fark > FM_ESIK:
                    fark_itm.setForeground(QColor("#f59e0b"))
                elif fark < -FM_ESIK:
                    fark_itm.setForeground(QColor("#e85555"))
                else:
                    fark_itm.setForeground(QColor("#2ec98e"))
                self._tbl_nobet.setItem(ri, 5, fark_itm)

                # Dağılım durumu
                if sayi == 0:
                    dag, dag_renk = "Yok", "#e85555"
                elif sayi < ort * 0.75:
                    dag, dag_renk = "↓ Düşük", "#e85555"
                elif sayi > ort * 1.25:
                    dag, dag_renk = "↑ Yüksek", "#f59e0b"
                else:
                    dag, dag_renk = "Dengeli", "#2ec98e"
                dag_itm = _it(dag, pid)
                dag_itm.setForeground(QColor(dag_renk))
                self._tbl_nobet.setItem(ri, 6, dag_itm)

            self._tbl_nobet.setSortingEnabled(True)
            self._lbl_nobet_alt.setText(
                f"{len(pidler)} personel  |  "
                f"Toplam {toplam} nöbet  |  "
                f"Kişi başı ort. {ort:.1f}")
        except Exception as e:
            logger.error(f"yukle_nobet: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 2: Günlük Dağılım
    # ──────────────────────────────────────────────────────────

    def _yukle_dagilim(self):
        """Personel × gün matrisi — nöbet günlerini görsel olarak göster."""
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            if not pidler:
                self._tbl_dag.setRowCount(0)
                self._tbl_dag.setColumnCount(0)
                return

            ay_son = monthrange(self._yil, self._ay)[1]
            ay_bas = date(self._yil, self._ay, 1).isoformat()
            ay_bit = date(self._yil, self._ay, ay_son).isoformat()
            birim_plan_ids, _ = self._plan_verileri()

            satir_rows = reg.get("NB_PlanSatir").get_all() or []
            # {pid: {gun_no, ...}}
            nobet_gunler: dict[str, set] = {}
            for s in satir_rows:
                if str(s.get("Durum","")) != "aktif":
                    continue
                if str(s.get("PlanID","")) not in birim_plan_ids:
                    continue
                t = str(s.get("NobetTarihi",""))
                if not (ay_bas <= t <= ay_bit):
                    continue
                try:
                    gun_no = int(t.split("-")[2])
                except Exception:
                    continue
                pid = str(s.get("PersonelID",""))
                nobet_gunler.setdefault(pid, set()).add(gun_no)

            # Tatil/hafta sonu setleri
            tatil_set   = _tatil_set(self._yil, self._ay, reg)
            haftasonu   = {
                g for g in range(1, ay_son+1)
                if date(self._yil, self._ay, g).weekday() in (5, 6)
            }
            tatil_gunler = {
                int(t.split("-")[2]) for t in tatil_set
                if t.startswith(f"{self._yil:04d}-{self._ay:02d}-")
            }

            # Tablo boyutu: satır=personel, sütun=ad + 31 gün
            n_gun = ay_son
            self._tbl_dag.setSortingEnabled(False)
            self._tbl_dag.setRowCount(len(pidler))
            self._tbl_dag.setColumnCount(1 + n_gun)

            # Başlıklar
            basliklar = ["Ad Soyad"] + [str(g) for g in range(1, n_gun+1)]
            self._tbl_dag.setHorizontalHeaderLabels(basliklar)
            self._tbl_dag.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents)
            for i in range(1, 1+n_gun):
                self._tbl_dag.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Fixed)
                self._tbl_dag.setColumnWidth(i, 24)

            for ri, (pid, ad) in enumerate(pidler):
                ad_itm = QTableWidgetItem(ad)
                ad_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_dag.setItem(ri, 0, ad_itm)
                gunler = nobet_gunler.get(pid, set())
                for g in range(1, n_gun+1):
                    itm = QTableWidgetItem()
                    itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if g in gunler:
                        itm.setText("●")
                        itm.setForeground(QColor("#2ec98e"))
                    elif g in tatil_gunler:
                        itm.setBackground(QColor("#2a1a1a"))
                    elif g in haftasonu:
                        itm.setBackground(QColor("#1a2a3a"))
                    self._tbl_dag.setItem(ri, g, itm)

            self._lbl_dag_alt.setText(
                f"{len(pidler)} personel  |  "
                f"● Nöbet  ■ Tatil  □ Hafta sonu")
        except Exception as e:
            logger.error(f"yukle_dagilim: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 3: İzin Durumu
    # ──────────────────────────────────────────────────────────

    def _yukle_izin(self):
        try:
            reg    = self._reg()
            pidler = {pid for pid, _ in self._pid_listesi()}
            p_all  = reg.get("Personel").get_all() or []
            p_map  = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            tatil  = _tatil_set(self._yil, self._ay, reg)
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])

            iz_rows  = reg.get("Izin_Giris").get_all() or []
            kayitlar = []
            for r in iz_rows:
                pid = str(r.get("Personelid","")).strip()
                if pidler and pid not in pidler:
                    continue
                if str(r.get("Durum","")).strip() not in ONAY_DURUMLAR:
                    continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                kb = max(bas, ay_bas)
                ke = min(bit, ay_bit)
                if kb > ke:
                    continue
                is_gunu = _networkdays(kb, ke, tatil)
                if is_gunu == 0:
                    continue
                tip   = _hedef_tipi(pid, self._birim_id, self._yil, self._ay, reg)
                etki  = round(is_gunu * HEDEF_GUNLUK.get(tip, 7.0), 1)
                kayitlar.append({
                    "pid":    pid,
                    "ad":     p_map.get(pid, pid),
                    "bas":    kb.strftime("%d.%m"),
                    "bit":    ke.strftime("%d.%m"),
                    "is_gun": is_gunu,
                    "tip":    str(r.get("IzinTuru", r.get("Tur","—"))),
                    "etki":   etki,
                })
            kayitlar.sort(key=lambda x: x["ad"])

            self._tbl_izin.setSortingEnabled(False)
            self._tbl_izin.setRowCount(0)
            for k in kayitlar:
                ri = self._tbl_izin.rowCount()
                self._tbl_izin.insertRow(ri)
                self._tbl_izin.setItem(ri, 0, _it(k["ad"], k["pid"]))
                self._tbl_izin.setItem(ri, 1, _it(k["bas"], k["pid"]))
                self._tbl_izin.setItem(ri, 2, _it(k["bit"], k["pid"]))
                self._tbl_izin.setItem(ri, 3, _it(f"{k['is_gun']} iş günü", k["pid"]))
                self._tbl_izin.setItem(ri, 4, _it(k["tip"], k["pid"]))
                e_itm = _it(f"-{k['etki']:.0f} s", k["pid"])
                e_itm.setForeground(QColor("#e85555"))
                self._tbl_izin.setItem(ri, 5, e_itm)
            self._tbl_izin.setSortingEnabled(True)

            self._lbl_izin_alt.setText(
                f"{len(kayitlar)} izin kaydı  |  "
                f"{len({k['pid'] for k in kayitlar})} personel")
        except Exception as e:
            logger.error(f"yukle_izin: {e}")

    # ──────────────────────────────────────────────────────────
    #  Sekme 4: Fazla Mesai
    # ──────────────────────────────────────────────────────────

    def _yukle_fm(self):
        try:
            reg    = self._reg()
            pidler = self._pid_listesi()
            if not pidler:
                self._tbl_fm.setRowCount(0)
                return

            ay_bas = date(self._yil, self._ay, 1).isoformat()
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1]).isoformat()
            birim_plan_ids, v_sure = self._plan_verileri()
            satir_rows = reg.get("NB_PlanSatir").get_all() or []

            saat_sayac: dict[str, float] = {}
            for s in satir_rows:
                if str(s.get("Durum","")) != "aktif":
                    continue
                if str(s.get("PlanID","")) not in birim_plan_ids:
                    continue
                t = str(s.get("NobetTarihi",""))
                if not (ay_bas <= t <= ay_bit):
                    continue
                pid = str(s.get("PersonelID",""))
                saat_sayac[pid] = (saat_sayac.get(pid, 0.0)
                    + v_sure.get(str(s.get("VardiyaID","")), 720) / 60)

            # Önceki ay
            if self._ay == 1:
                ony, ona = self._yil - 1, 12
            else:
                ony, ona = self._yil, self._ay - 1

            mh_rows = reg.get("NB_MesaiHesap").get_all() or []

            def _mh(pid: str, yil: int, ay: int) -> dict:
                return next(
                    (r for r in mh_rows
                     if str(r.get("PersonelID","")) == pid
                     and int(r.get("Yil",0)) == yil
                     and int(r.get("Ay",0)) == ay
                     and (not self._birim_id
                          or str(r.get("BirimID","")) == self._birim_id)),
                    {})

            self._tbl_fm.setSortingEnabled(False)
            self._tbl_fm.setRowCount(0)
            fm_bekleyen = 0

            for pid, ad in pidler:
                hedef    = _hedef_saat(pid, self._birim_id, self._yil, self._ay, reg)
                calisan  = round(saat_sayac.get(pid, 0.0), 1)
                bu_ay_f  = round(calisan - hedef, 1)

                # Önceki devir — DB kaydı yoksa canlı hesapla
                onceki_kayit = _mh(pid, ony, ona)
                if onceki_kayit and int(onceki_kayit.get("DevireGidenDakika", -1)) >= 0:
                    # DB kaydı var ve doldurulmuş → kullan
                    devir = float(onceki_kayit.get("DevireGidenDakika", 0)) / 60
                else:
                    # DB kaydı yok → önceki ayın fazlasını canlı hesapla
                    devir = self._onceki_ay_bakiye(pid, ony, ona, reg)

                toplam_f = round(bu_ay_f + devir, 1)

                # Mevcut kayıtta FM bildirildi mi?
                bu_kayit  = _mh(pid, self._yil, self._ay)
                bildirildi = int(bu_kayit.get("OdenenDakika", 0)) > 0

                # Devire giden: bildirildi ise 0, yoksa toplam
                devire_g = 0.0 if bildirildi else toplam_f

                if toplam_f > FM_ESIK and not bildirildi:
                    fm_bekleyen += 1

                ri = self._tbl_fm.rowCount()
                self._tbl_fm.insertRow(ri)

                # Sütun 0: Checkbox
                chk_itm = QTableWidgetItem("Seç")
                chk_itm.setData(Qt.ItemDataRole.UserRole, pid)
                chk_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                chk_itm.setForeground(QColor("#6b7280"))
                self._tbl_fm.setItem(ri, 0, chk_itm)

                # Sütun 1: Ad Soyad
                self._tbl_fm.setItem(ri, 1, _it(ad, pid))

                # Sütun 2: Bu ay fazla
                isaret = "+" if bu_ay_f > 0 else ""
                bu_itm = _it(f"{isaret}{bu_ay_f:.0f} s", pid)
                if bu_ay_f > FM_ESIK:
                    bu_itm.setForeground(QColor("#f59e0b"))
                elif bu_ay_f < -FM_ESIK:
                    bu_itm.setForeground(QColor("#e85555"))
                self._tbl_fm.setItem(ri, 2, bu_itm)

                # Sütun 3: Önceki devir
                if devir == 0:
                    devir_lbl = "—"
                else:
                    isaret_d = "+" if devir > 0 else ""
                    devir_lbl = f"{isaret_d}{devir:.0f} s"
                devir_itm = _it(devir_lbl, pid)
                if devir > FM_ESIK:
                    devir_itm.setForeground(QColor("#f59e0b"))
                elif devir < -FM_ESIK:
                    devir_itm.setForeground(QColor("#e85555"))
                self._tbl_fm.setItem(ri, 3, devir_itm)

                # Sütun 4: Toplam
                isaret2 = "+" if toplam_f > 0 else ""
                top_itm = _it(f"{isaret2}{toplam_f:.0f} s", pid)
                if toplam_f > FM_ESIK:
                    top_itm.setForeground(QColor("#f59e0b"))
                elif toplam_f < -FM_ESIK:
                    top_itm.setForeground(QColor("#e85555"))
                else:
                    top_itm.setForeground(QColor("#f3c55a"))
                self._tbl_fm.setItem(ri, 4, top_itm)

                # Sütun 5: FM Durumu
                if bildirildi:
                    r_lbl  = "Bildirildi"
                    r_renk = "#2ec98e"
                elif toplam_f > FM_ESIK:
                    r_lbl  = "Bekliyor"
                    r_renk = "#f59e0b"
                elif abs(toplam_f) <= FM_ESIK:
                    r_lbl  = "Alacak/Verecek"
                    r_renk = "#f3c55a"
                else:
                    r_lbl  = "↓ Eksik"
                    r_renk = "#e85555"
                r_itm = _it(r_lbl, pid)
                r_itm.setForeground(QColor(r_renk))
                self._tbl_fm.setItem(ri, 5, r_itm)

                # Sütun 6: Devire giden
                isaret3 = "+" if devire_g > 0 else ""
                d_itm = _it(
                    f"{isaret3}{devire_g:.0f} s" if devire_g != 0 else "—",
                    pid)
                if devire_g > FM_ESIK:
                    d_itm.setForeground(QColor("#f59e0b"))
                self._tbl_fm.setItem(ri, 6, d_itm)

            self._tbl_fm.setSortingEnabled(True)
            secili = self._fm_secili_pidler()
            self._btn_fm_bildir.setEnabled(len(secili) > 0)
            self._btn_fm_pdf.setEnabled(self._tbl_fm.rowCount() > 0)
            self._lbl_fm_alt.setText(
                f"{len(pidler)} personel  |  "
                f"FM bildirimi bekleyen: {fm_bekleyen}")
        except Exception as e:
            logger.error(f"yukle_fm: {e}")

    # ──────────────────────────────────────────────────────────
    #  FM Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _fm_chk_toggle(self, row: int, col: int):
        """Checkbox sütununa tıklayınca seçimi aç/kapat."""
        if col != 0:
            return
        itm = self._tbl_fm.item(row, 0)
        if not itm:
            return
        secili = itm.text() == "Seçili"
        itm.setText("Seç" if secili else "Seçili")
        itm.setForeground(QColor(
            "#6b7280" if secili else "#2ec98e"))
        self._btn_fm_bildir.setEnabled(
            len(self._fm_secili_pidler()) > 0)

    def _fm_tumunu_sec(self):
        """Tüm satırları seç/seçimi kaldır."""
        tum_secili = all(
            (self._tbl_fm.item(r, 0) or QTableWidgetItem()).text() == "Seçili"
            for r in range(self._tbl_fm.rowCount()))
        for r in range(self._tbl_fm.rowCount()):
            itm = self._tbl_fm.item(r, 0)
            if itm:
                itm.setText("Seç" if tum_secili else "Seçili")
                itm.setForeground(QColor(
                    "#6b7280" if tum_secili else "#2ec98e"))
        self._btn_fm_bildir.setEnabled(
            not tum_secili and self._tbl_fm.rowCount() > 0)

    def _fm_secili_pidler(self) -> list[str]:
        return [
            self._tbl_fm.item(r, 0).data(Qt.ItemDataRole.UserRole)
            for r in range(self._tbl_fm.rowCount())
            if self._tbl_fm.item(r, 0)
            and self._tbl_fm.item(r, 0).text() == "Seçili"
        ]

    def _fm_bildir(self):
        """Seçili personel için FM bildir — bakiyeyi sıfırla."""
        pidler = self._fm_secili_pidler()
        if not pidler:
            return
        try:
            reg = self._reg()
            ay_bas = date(self._yil, self._ay, 1).isoformat()
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1]).isoformat()
            birim_plan_ids, v_sure = self._plan_verileri()
            satir_rows = reg.get("NB_PlanSatir").get_all() or []
            mh_rows    = reg.get("NB_MesaiHesap").get_all() or []
            plan_rows  = reg.get("NB_Plan").get_all() or []

            if self._ay == 1:
                ony, ona = self._yil - 1, 12
            else:
                ony, ona = self._yil, self._ay - 1

            for pid in pidler:
                calisan = sum(
                    v_sure.get(str(s.get("VardiyaID","")), 720) / 60
                    for s in satir_rows
                    if str(s.get("PersonelID","")) == pid
                    and str(s.get("Durum","")) == "aktif"
                    and str(s.get("PlanID","")) in birim_plan_ids
                    and ay_bas <= str(s.get("NobetTarihi","")) <= ay_bit)
                hedef   = _hedef_saat(
                    pid, self._birim_id, self._yil, self._ay, reg)
                bu_ay_f = round(calisan - hedef, 1)
                fazla_dk = int(bu_ay_f * 60)

                onceki  = next(
                    (r for r in mh_rows
                     if str(r.get("PersonelID","")) == pid
                     and int(r.get("Yil",0)) == ony
                     and int(r.get("Ay",0)) == ona
                     and (not self._birim_id
                          or str(r.get("BirimID","")) == self._birim_id)),
                    {})
                devir_dk  = int(onceki.get("DevireGidenDakika", 0)) \
                    if onceki else int(
                        self._onceki_ay_bakiye(pid, ony, ona, reg) * 60)
                toplam_dk = fazla_dk + devir_dk

                bu_kayit = next(
                    (r for r in mh_rows
                     if str(r.get("PersonelID","")) == pid
                     and int(r.get("Yil",0)) == self._yil
                     and int(r.get("Ay",0)) == self._ay
                     and (not self._birim_id
                          or str(r.get("BirimID","")) == self._birim_id)),
                    None)

                simdi = _simdi()
                veri = {
                    "OdenenDakika":      toplam_dk,
                    "DevireGidenDakika": 0,   # ← bakiye sıfırlandı
                    "HesapDurumu":       "tamamlandi",
                    "HesapTarihi":       simdi,
                    "updated_at":        simdi,
                }
                if bu_kayit:
                    reg.get("NB_MesaiHesap").update(bu_kayit["HesapID"], veri)
                else:
                    plan = next(
                        (p for p in plan_rows
                         if int(p.get("Yil",0)) == self._yil
                         and int(p.get("Ay",0)) == self._ay
                         and (not self._birim_id
                              or str(p.get("BirimID","")) == self._birim_id)),
                        None)
                    reg.get("NB_MesaiHesap").insert({
                        "HesapID":           str(uuid.uuid4()),
                        "PersonelID":        pid,
                        "BirimID":           self._birim_id or "",
                        "PlanID":            plan["PlanID"] if plan else "",
                        "Yil":               self._yil,
                        "Ay":                self._ay,
                        "CalisDakika":       int(calisan * 60),
                        "HedefDakika":       int(hedef * 60),
                        "FazlaDakika":       fazla_dk,
                        "DevirDakika":       devir_dk,
                        "ToplamFazlaDakika": toplam_dk,
                        "created_at":        simdi,
                        **veri,
                    })

            QMessageBox.information(
                self, "Tamamlandı",
                f"{len(pidler)} personel için FM bildirildi.\n"
                f"Bakiyeler sıfırlandı.")
            self._yukle_fm()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            logger.error(f"_fm_bildir: {e}")

    def _fm_pdf(self):
        """Fazla mesai tablosunu PDF olarak kaydet."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle,
                Paragraph, Spacer)
            import tempfile, os
            from PySide6.QtWidgets import QFileDialog

            # Kayıt yolu
            varsayilan = (
                f"FM_Rapor_{_AY[self._ay]}_{self._yil}"
                f"{'_' + self._birim_adi if self._birim_adi else ''}.pdf"
            )
            yol, _ = QFileDialog.getSaveFileName(
                self, "PDF Kaydet", varsayilan,
                "PDF Dosyası (*.pdf)")
            if not yol:
                return

            styles = getSampleStyleSheet()
            baslik_stil = ParagraphStyle(
                "baslik", parent=styles["Title"],
                fontSize=14, spaceAfter=6)
            alt_stil = ParagraphStyle(
                "alt", parent=styles["Normal"],
                fontSize=9, textColor=colors.grey)

            doc = SimpleDocTemplate(
                yol, pagesize=landscape(A4),
                leftMargin=1.5*cm, rightMargin=1.5*cm,
                topMargin=1.5*cm, bottomMargin=1.5*cm)

            hikaye = []

            # Başlık
            birim_str = self._birim_adi or "Tüm Birimler"
            hikaye.append(Paragraph(
                f"Fazla Mesai Raporu — {_AY[self._ay]} {self._yil}",
                baslik_stil))
            hikaye.append(Paragraph(
                f"Birim: {birim_str}  |  Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                alt_stil))
            hikaye.append(Spacer(1, 0.5*cm))

            # Tablo başlıkları
            sutunlar = [
                "Ad Soyad", "Bu Ay\nFazla",
                "Önceki\nDevir", "Toplam\nFazla",
                "FM Durumu", "Devire\nGiden"]
            veri = [sutunlar]

            # Satırları doldur
            for r in range(self._tbl_fm.rowCount()):
                satir = []
                for c in range(1, 7):  # 0=checkbox, 1-6=veri
                    itm = self._tbl_fm.item(r, c)
                    satir.append(itm.text() if itm else "—")
                veri.append(satir)

            genislikler = [5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 4*cm, 2.5*cm]
            tbl = Table(veri, colWidths=genislikler, repeatRows=1)
            tbl.setStyle(TableStyle([
                # Başlık
                ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,0), 9),
                ("ALIGN",       (0,0), (-1,0), "CENTER"),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [colors.white, colors.HexColor("#f0f4f8")]),
                ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
                ("FONTSIZE",    (0,1), (-1,-1), 8),
                ("ALIGN",       (1,1), (-1,-1), "CENTER"),
                ("ALIGN",       (0,1), (0,-1), "LEFT"),
                ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#d1d5db")),
                ("TOPPADDING",  (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING", (0,0), (-1,-1), 6),
            ]))
            hikaye.append(tbl)

            # Alt not
            hikaye.append(Spacer(1, 0.3*cm))
            hikaye.append(Paragraph(
                f"Toplam {self._tbl_fm.rowCount()} personel  |  "
                f"FM ±{FM_ESIK:.0f}s eşiği",
                alt_stil))

            doc.build(hikaye)
            QMessageBox.information(
                self, "PDF Kaydedildi",
                f"Dosya kaydedildi:\n{yol}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            logger.error(f"_fm_pdf: {e}")

    def _onceki_ay_bakiye(self, pid: str, yil: int, ay: int,
                          reg, derinlik: int = 0) -> float:
        """
        Önceki ayın devire giden bakiyesini hesaplar.
        NB_MesaiHesap kaydı yoksa o ayın fazlasını canlı hesaplar.
        Özyinelemeli — en fazla 12 ay geriye gider.
        """
        if derinlik > 12:
            return 0.0
        try:
            # O aya ait plan satırlarından çalışılan saati hesapla
            plan_rows  = reg.get("NB_Plan").get_all() or []
            satir_rows = reg.get("NB_PlanSatir").get_all() or []
            v_rows     = reg.get("NB_Vardiya").get_all() or []
            v_sure     = {str(v["VardiyaID"]): int(v.get("SureDakika",720))
                          for v in v_rows}

            ay_bas = date(yil, ay, 1).isoformat()
            ay_bit = date(yil, ay, monthrange(yil, ay)[1]).isoformat()

            birim_plan_ids = {
                str(p["PlanID"]) for p in plan_rows
                if int(p.get("Yil",0)) == yil
                and int(p.get("Ay",0)) == ay
                and (not self._birim_id
                     or str(p.get("BirimID","")) == self._birim_id)
            }

            if not birim_plan_ids:
                return 0.0

            calisan = sum(
                v_sure.get(str(s.get("VardiyaID","")), 720) / 60
                for s in satir_rows
                if str(s.get("PersonelID","")) == pid
                and str(s.get("Durum","")) == "aktif"
                and str(s.get("PlanID","")) in birim_plan_ids
                and ay_bas <= str(s.get("NobetTarihi","")) <= ay_bit
            )
            hedef   = _hedef_saat(pid, self._birim_id, yil, ay, reg)
            bu_ay_f = round(calisan - hedef, 1)

            # Bu aydan önceki devir (özyinelemeli)
            if ay == 1:
                ony, ona = yil - 1, 12
            else:
                ony, ona = yil, ay - 1

            mh_rows      = reg.get("NB_MesaiHesap").get_all() or []
            onceki_kayit = next(
                (r for r in mh_rows
                 if str(r.get("PersonelID","")) == pid
                 and int(r.get("Yil",0)) == ony
                 and int(r.get("Ay",0)) == ona
                 and (not self._birim_id
                      or str(r.get("BirimID","")) == self._birim_id)),
                None)

            if onceki_kayit and int(onceki_kayit.get("DevireGidenDakika",-1)) >= 0:
                onceki_devir = float(onceki_kayit.get("DevireGidenDakika", 0)) / 60
            else:
                onceki_devir = self._onceki_ay_bakiye(
                    pid, ony, ona, reg, derinlik + 1)

            # Eğer bu ay için FM raporu alındıysa devire giden 0
            bu_kayit = next(
                (r for r in mh_rows
                 if str(r.get("PersonelID","")) == pid
                 and int(r.get("Yil",0)) == yil
                 and int(r.get("Ay",0)) == ay
                 and (not self._birim_id
                      or str(r.get("BirimID","")) == self._birim_id)),
                None)
            if bu_kayit and int(bu_kayit.get("OdenenDakika",0)) > 0:
                return 0.0  # Rapor alınmış, devir yok

            return round(bu_ay_f + onceki_devir, 1)

        except Exception as e:
            logger.debug(f"_onceki_ay_bakiye({pid} {yil}/{ay}): {e}")
            return 0.0
        if self._db:
            self._birimleri_doldur()
            self._yukle()
