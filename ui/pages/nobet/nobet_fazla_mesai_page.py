# -*- coding: utf-8 -*-
"""
nobet_fazla_mesai_page.py — Fazla Mesai Yönetimi

Sekmeler:
  1. Personel Tablosu  — hedef/çalışılan/fazla/devir + toplu FM bildir
  2. Aylık Karşılaştırma — son 6 ay bar grafik (SVG)

Aksiyonlar: FM Bildir / PDF / Excel/CSV
"""
from __future__ import annotations

import csv
from calendar import monthrange
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QTabWidget,
    QScrollArea,
)
from PySide6.QtSvgWidgets import QSvgWidget

from core.di import get_registry
from core.logger import logger

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

FM_ESIK = 7.0  # saat


def _dk_s(dk: int) -> float:
    return round(dk / 60, 1)

def _fmt(s: float) -> str:
    if s == 0: return "—"
    return f"+{s:.1f}" if s > 0 else f"{s:.1f}"

def _it(text: str, data=None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    if data is not None:
        it.setData(Qt.ItemDataRole.UserRole, data)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


class NobetFazlaMesaiPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db; self._ag = action_guard
        self._yil = date.today().year
        self._ay  = date.today().month
        self._birim_id = ""; self._birim_adi = ""
        self.setProperty("bg-role","page")
        self._build()
        if db:
            self._birimleri_doldur()

    def _reg(self): return get_registry(self._db)

    # ── UI ────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        lay.addWidget(self._build_toolbar())
        lay.addWidget(self._build_ozet_bar())
        tabs = QTabWidget()
        tabs.addTab(self._build_tablo_tab(), "📋  Personel Tablosu")
        tabs.addTab(self._build_grafik_tab(), "📊  Aylık Karşılaştırma")
        lay.addWidget(tabs, 1)

    def _build_toolbar(self) -> QFrame:
        bar = QFrame(); bar.setProperty("bg-role","panel"); bar.setFixedHeight(46)
        h = QHBoxLayout(bar); h.setContentsMargins(12,0,12,0); h.setSpacing(8)
        btn_g = QPushButton("‹"); btn_g.setFixedSize(28,28)
        btn_g.setProperty("style-role","secondary"); btn_g.clicked.connect(self._ay_geri)
        h.addWidget(btn_g)
        self._lbl_ay = QLabel()
        self._lbl_ay.setFixedWidth(120); self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role","section-title"); h.addWidget(self._lbl_ay)
        btn_i = QPushButton("›"); btn_i.setFixedSize(28,28)
        btn_i.setProperty("style-role","secondary"); btn_i.clicked.connect(self._ay_ileri)
        h.addWidget(btn_i)
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
            f = QFrame(); fl = QVBoxLayout(f); fl.setContentsMargins(8,4,8,4); fl.setSpacing(1)
            v = QLabel("—"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(f"font-size:18px;font-weight:bold;color:{renk};")
            b = QLabel(baslik); b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setStyleSheet("font-size:9px;color:#6b7280;")
            fl.addWidget(v); fl.addWidget(b); self._kartlar[key] = v; h.addWidget(f,1)
            if key != "devir":
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#2a3a4a;"); h.addWidget(sep)
        return bar

    def _build_tablo_tab(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(8,8,8,4); lay.setSpacing(4)

        self._tbl = QTableWidget(0, 10)
        self._tbl.setHorizontalHeaderLabels([
            "✔","Ad Soyad","Birim",
            "Hedef\n(s)","Çalışılan\n(s)",
            "Bu Ay\n(s)","Önceki\nDevir (s)",
            "Toplam\n(s)","Durum","Bildirim\nTarihi"])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tbl.setColumnWidth(0, 30)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in (2,3,4,5,6,7,8,9):
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
        except Exception as e:
            logger.error(f"birimleri_doldur: {e}")

    def _yukle(self):
        if not self._db: return
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")
        self._yukle_tablo()
        self._yukle_grafik()

    def _mh_rows(self, yil: int, ay: int) -> list[dict]:
        """Belirli ay için NB_MesaiHesap satırları."""
        try:
            reg = self._reg()
            rows = reg.get("NB_MesaiHesap").get_all() or []
            return [r for r in rows
                    if int(r.get("Yil",0))==yil and int(r.get("Ay",0))==ay
                    and (not self._birim_id
                         or str(r.get("BirimID",""))==self._birim_id)]
        except Exception:
            return []

    def _yukle_tablo(self):
        try:
            reg   = self._reg()
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","")
                     for p in (reg.get("Personel").get_all() or [])}
            b_map = {r["BirimID"]: r.get("BirimAdi","")
                     for r in (reg.get("NB_Birim").get_all() or [])}

            ilgili = sorted(self._mh_rows(self._yil, self._ay),
                            key=lambda r: p_map.get(str(r.get("PersonelID","")), ""))

            self._tbl.setSortingEnabled(False)
            self._tbl.setRowCount(0)
            toplam_f = bekliyor = bildirildi_s = devir_top = 0.0

            for r in ilgili:
                pid    = str(r.get("PersonelID",""))
                bid    = str(r.get("BirimID",""))
                hedef  = _dk_s(int(r.get("HedefDakika",0)))
                calis  = _dk_s(int(r.get("CalisDakika",0)))
                bu_ay  = _dk_s(int(r.get("FazlaDakika",0)))
                devir  = _dk_s(int(r.get("DevirDakika",0)))
                top    = _dk_s(int(r.get("ToplamFazlaDakika",0)))
                odenen = int(r.get("OdenenDakika",0))
                devire = _dk_s(int(r.get("DevireGidenDakika",0)))
                durum  = str(r.get("HesapDurumu",""))
                tarih  = str(r.get("HesapTarihi","") or "")[:10]

                toplam_f  += max(0, bu_ay)
                devir_top += max(0, devire)

                bil_mi = (odenen > 0 and durum == "tamamlandi")
                if bil_mi:
                    fm_lbl, fm_renk = "✔ Bildirildi", "#2ec98e"; bildirildi_s += 1
                elif top > FM_ESIK:
                    fm_lbl, fm_renk = "⏳ Bekliyor", "#f59e0b"; bekliyor += 1
                elif abs(top) <= FM_ESIK:
                    fm_lbl, fm_renk = "⇄ Alacak/Verecek", "#f3c55a"
                else:
                    fm_lbl, fm_renk = "↓ Eksik", "#e85555"

                ri = self._tbl.rowCount()
                self._tbl.insertRow(ri)

                chk = QTableWidgetItem("☐")
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                chk.setForeground(QColor("#6b7280"))
                chk.setData(Qt.ItemDataRole.UserRole, r.get("HesapID",""))
                self._tbl.setItem(ri, 0, chk)

                ad_i = QTableWidgetItem(p_map.get(pid, pid))
                ad_i.setData(Qt.ItemDataRole.UserRole, r.get("HesapID",""))
                self._tbl.setItem(ri, 1, ad_i)
                self._tbl.setItem(ri, 2, _it(b_map.get(bid, bid)))
                self._tbl.setItem(ri, 3, _it(f"{hedef:.1f}"))
                self._tbl.setItem(ri, 4, _it(f"{calis:.1f}"))

                for ci, (val, esik) in enumerate([(bu_ay, FM_ESIK), (devir, 0), (top, FM_ESIK)], 5):
                    itm = _it(_fmt(val) if val != 0 else "—")
                    if val > esik:   itm.setForeground(QColor("#f59e0b"))
                    elif val < 0:    itm.setForeground(QColor("#e85555"))
                    elif val > 0:    itm.setForeground(QColor("#f3c55a"))
                    self._tbl.setItem(ri, ci, itm)

                d_itm = _it(fm_lbl); d_itm.setForeground(QColor(fm_renk))
                self._tbl.setItem(ri, 8, d_itm)
                self._tbl.setItem(ri, 9, _it(tarih if bil_mi else "—"))

            self._tbl.setSortingEnabled(True)

            self._kartlar["personel"].setText(str(len(ilgili)))
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
                f"{len(ilgili)} kayıt  |  {int(bekliyor)} bekliyor  |  "
                f"{int(bildirildi_s)} bildirildi")
            self._btn_bildir.setEnabled(False)
            self._btn_pdf.setEnabled(len(ilgili) > 0)
            self._btn_excel.setEnabled(len(ilgili) > 0)
        except Exception as e:
            logger.error(f"_yukle_tablo: {e}")

    def _yukle_grafik(self):
        """Son 6 ay için bar grafik — SVG."""
        try:
            # Son 6 ayı hesapla
            aylar = []
            y, m = self._yil, self._ay
            for _ in range(6):
                aylar.insert(0, (y, m))
                m -= 1
                if m == 0: m, y = 12, y-1

            # Her ay ortalama fazla saat
            veri: list[tuple[str, float, float, float]] = []  # (etiket, ortalama, maks, bildirildi_oran)
            for y, m in aylar:
                rows = self._mh_rows(y, m)
                if not rows:
                    veri.append((f"{_AY[m][:3]}\n{y}", 0, 0, 0))
                    continue
                fazlalar = [_dk_s(int(r.get("FazlaDakika",0))) for r in rows]
                ort = sum(fazlalar) / len(fazlalar)
                maks = max(fazlalar)
                bil = sum(1 for r in rows
                          if int(r.get("OdenenDakika",0)) > 0
                          and str(r.get("HesapDurumu",""))=="tamamlandi")
                veri.append((f"{_AY[m][:3]}\n{y}", round(ort,1), round(maks,1),
                             round(bil/len(rows)*100)))

            svg = self._svg_grafik(veri)
            self._svg.load(svg.encode("utf-8"))

            ozet = "  |  ".join(
                f"{v[0].replace(chr(10),' ')}: ort {v[1]:+.1f}s" for v in veri)
            self._lbl_grafik.setText(ozet)
        except Exception as e:
            logger.error(f"_yukle_grafik: {e}")

    def _svg_grafik(self, veri: list) -> str:
        """6 bar + çizgi grafik — SVG string döner."""
        W, H = 860, 320
        PAD_L, PAD_R, PAD_T, PAD_B = 60, 20, 30, 60
        graf_w = W - PAD_L - PAD_R
        graf_h = H - PAD_T - PAD_B
        n = len(veri)
        bar_w = int(graf_w / n * 0.5)

        # Değer aralığı
        tum_degeler = [abs(v[1]) for v in veri] + [abs(v[2]) for v in veri]
        maks_val = max(tum_degeler + [FM_ESIK + 5])
        min_val  = min(v[1] for v in veri)
        if min_val > 0: min_val = 0

        def yx(val: float) -> int:
            return PAD_T + int((maks_val - val) / (maks_val - min_val) * graf_h)

        def xx(i: int) -> int:
            return PAD_L + int((i + 0.5) * graf_w / n)

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="#0d1b2a"/>',
        ]

        # Yatay ızgara çizgileri
        for tick in range(int(min_val), int(maks_val)+1, max(1, int((maks_val-min_val)/5))):
            y_tick = yx(tick)
            renk = "#f59e0b" if abs(tick - FM_ESIK) < 0.5 else "#1e2e40"
            lines.append(
                f'<line x1="{PAD_L}" y1="{y_tick}" x2="{W-PAD_R}" y2="{y_tick}" '
                f'stroke="{renk}" stroke-width="{"1.5" if abs(tick-FM_ESIK)<0.5 else "0.5"}"/>')
            lines.append(
                f'<text x="{PAD_L-6}" y="{y_tick+4}" text-anchor="end" '
                f'font-size="10" fill="#6b7280">{tick:+.0f}</text>')

        # FM eşik etiketi
        y_esik = yx(FM_ESIK)
        lines.append(
            f'<text x="{W-PAD_R+3}" y="{y_esik+4}" font-size="9" fill="#f59e0b">+{FM_ESIK:.0f}s</text>')

        # Barlar
        y0 = yx(0)
        for i, (lbl, ort, maks, bil_pct) in enumerate(veri):
            x = xx(i)
            # Ortalama bar
            if ort >= 0:
                yy = yx(ort); bar_h = y0 - yy
                fill = "#f59e0b" if ort > FM_ESIK else "#4d9ee8"
            else:
                yy = y0; bar_h = yx(ort) - y0
                fill = "#e85555"
            lines.append(
                f'<rect x="{x-bar_w//2}" y="{yy}" width="{bar_w}" '
                f'height="{max(bar_h,1)}" fill="{fill}" opacity="0.85" rx="2"/>')
            # Değer etiketi
            if ort != 0:
                ly = yy - 5 if ort >= 0 else yy + bar_h + 14
                lines.append(
                    f'<text x="{x}" y="{ly}" text-anchor="middle" '
                    f'font-size="10" font-weight="bold" fill="{fill}">{ort:+.1f}</text>')
            # Bildirim yüzdesi (küçük yeşil bar)
            if bil_pct > 0:
                bil_h = int(abs(bar_h) * bil_pct / 100)
                bil_y = yy + max(bar_h,1) - bil_h if ort >= 0 else yy
                lines.append(
                    f'<rect x="{x-bar_w//2}" y="{bil_y}" width="{bar_w}" '
                    f'height="{bil_h}" fill="#2ec98e" opacity="0.7" rx="2"/>')
            # Ay etiketi
            for j, satir in enumerate(lbl.split("\n")):
                lines.append(
                    f'<text x="{x}" y="{H-PAD_B+16+j*13}" text-anchor="middle" '
                    f'font-size="10" fill="#6b7280">{satir}</text>')

        # Sıfır çizgisi
        lines.append(
            f'<line x1="{PAD_L}" y1="{y0}" x2="{W-PAD_R}" y2="{y0}" '
            f'stroke="#3a5a7a" stroke-width="1"/>')

        # Maks çizgisi (noktalı)
        pts = " ".join(f"{xx(i)},{yx(v[2])}" for i, v in enumerate(veri) if v[2] != 0)
        if pts:
            lines.append(
                f'<polyline points="{pts}" fill="none" stroke="#6b7280" '
                f'stroke-width="1" stroke-dasharray="4,3"/>')

        # Lejant
        for xi, (renk, lbl) in enumerate([
            ("#4d9ee8","Ort. Fazla (≤+7s)"),
            ("#f59e0b","Ort. Fazla (>+7s)"),
            ("#2ec98e","Bildirilen kısım"),
            ("#6b7280","Maks (noktalı)"),
        ]):
            lx = PAD_L + xi * 200
            lines.append(
                f'<rect x="{lx}" y="{H-14}" width="10" height="10" fill="{renk}" rx="2"/>')
            lines.append(
                f'<text x="{lx+14}" y="{H-5}" font-size="9" fill="#6b7280">{lbl}</text>')

        lines.append("</svg>")
        return "\n".join(lines)

    # ── Checkbox ───────────────────────────────────────────────

    def _chk_toggle(self, row: int, col: int):
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
        ids = self._secili()
        if not ids: return
        cevap = QMessageBox.question(
            self,"Fazla Mesai Bildir",
            f"{len(ids)} personel için FM bildirimi yapılacak.\n"
            "Devire giden bakiyeler sıfırlanacak. Emin misiniz?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes: return
        try:
            reg   = self._reg()
            simdi = datetime.now().isoformat(sep=" ", timespec="seconds")
            tamam = 0
            for hid in ids:
                mh = reg.get("NB_MesaiHesap").get_all() or []
                k  = next((r for r in mh if r.get("HesapID")==hid), None)
                if not k: continue
                top = int(k.get("ToplamFazlaDakika",0))
                reg.get("NB_MesaiHesap").update(hid, {
                    "OdenenDakika":      top,
                    "DevireGidenDakika": 0,
                    "HesapDurumu":       "tamamlandi",
                    "HesapTarihi":       simdi,
                    "updated_at":        simdi,
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

            doc = SimpleDocTemplate(yol, pagesize=landscape(A4),
                leftMargin=1.5*cm,rightMargin=1.5*cm,
                topMargin=1.5*cm,bottomMargin=1.5*cm)
            h = []
            h.append(Paragraph(f"Fazla Mesai Raporu — {_AY[self._ay]} {self._yil}",bs))
            h.append(Paragraph(
                f"Birim: {birim_str}  |  "
                f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",as_))
            h.append(Spacer(1,0.3*cm))

            basliklar = ["Ad Soyad","Birim","Hedef (s)","Çalışılan (s)",
                         "Bu Ay (s)","Önceki Devir (s)","Toplam (s)","Durum","Bildirim"]
            veri = [basliklar]
            for r in range(self._tbl.rowCount()):
                satir = []
                for c in range(1,10):
                    itm = self._tbl.item(r,c)
                    satir.append(itm.text() if itm else "—")
                veri.append(satir)

            gen = [4.5*cm,2.5*cm,1.8*cm,2*cm,1.8*cm,2.2*cm,1.8*cm,3.5*cm,2*cm]
            tbl = Table(veri,colWidths=gen,repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
                ("FONTSIZE",(0,0),(-1,-1),7.5),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("ALIGN",(0,1),(1,-1),"LEFT"),
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
                f"FM eşiği ±{FM_ESIK:.0f}s  |  {self._tbl.rowCount()} kayıt",as_))
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
            basliklar = ["Ad Soyad","Birim","Hedef (s)","Çalışılan (s)",
                         "Bu Ay (s)","Önceki Devir (s)","Toplam (s)","Durum","Bildirim"]
            satirlar = [basliklar]
            for r in range(self._tbl.rowCount()):
                satirlar.append([
                    (self._tbl.item(r,c) or QTableWidgetItem()).text()
                    for c in range(1,10)])
            with open(yol,"w",newline="",encoding="utf-8-sig") as f:
                csv.writer(f).writerows(satirlar)
            QMessageBox.information(self,"CSV Kaydedildi",yol)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def load_data(self):
        if self._db: self._birimleri_doldur()
