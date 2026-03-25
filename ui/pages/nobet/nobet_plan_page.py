# -*- coding: utf-8 -*-
"""
nobet_plan_page.py — Nöbet Planlama (Excel benzeri görünüm)

Tablo yapısı:
  Sütun 0: Tarih
  Sütun 1: Gün
  Sonraki sütunlar: VardiyaGrubu başlığı (merged) + her slot için kişi adı

  Örnek:  Tarih | Gün | ── 08:00-20:00 ──────── | ── 20:00-08:00 ──────── |
                       | Kişi1 | Kişi2 | Kişi3   | Kişi1 | Kişi2 | Kişi3   |

Özellikler:
  - Hücreye çift tıkla: nöbet ekle / kaldır
  - Sağ tıkla: kontekst menüsü
  - Hafta sonu satırları: mavi arka plan
  - Dini bayram: turuncu satır
  - Onaylı plan: yeşil ton
  - Sol panel: birim/dönem + kişi tercihleri
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QScrollArea,
    QGroupBox, QMessageBox, QMenu, QProgressBar,
    QDialog, QFormLayout, QDialogButtonBox, QSizePolicy,
)

from core.di import get_nobet_service
from core.logger import logger

_AY_TR = ["",
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_GUN_TR = [
    "Pazartesi", "Salı", "Çarşamba",
    "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# Renk paleti
C = {
    "haftasonu_bg": "#1a2a4a",   # cumartesi/pazar satır bg
    "dini_bg":      "#2a1e00",   # dini bayram
    "tatil_bg":     "#2a1010",   # resmi tatil
    "onay_bg":      "#0a2010",   # onaylı plan
    "normal_bg":    "#0f1623",   # normal gün
    "kisi_bg":      "#162035",   # kişi adı hücresi
    "kisi_bg_hs":   "#1a3060",   # kişi adı - hafta sonu
    "kisi_bg_onay": "#0d2818",   # kişi adı - onaylı
    "bos_kisi":     "#0d1525",   # boş slot
    "bos_kisi_hs":  "#141c35",   # boş slot - hafta sonu
    "header_bg":    "#0a1020",   # vardiya grubu header
    "tarih_renk":   "#8aabcf",
    "gun_renk_hs":  "#4d9ee8",   # hafta sonu gün adı
    "gun_renk":     "#6a90b4",
    "kisi_renk":    "#c2d8ef",
    "bos_renk":     "#2a3a50",
    "tatil_simge":  "#e85555",
    "dini_simge":   "#e8a030",
}

FM_GONULLU_RENK = "#4d9ee8"   # FM Gönüllü işareti rengi
FM_GONULLU_ETIKET = "FM Gönüllü"

MAX_SLOT_PER_GRUP = 6  # tek grupta gösterilecek max kişi sütunu


class _ManuelDialog(QDialog):
    def __init__(self, tarih, personeller, vardiyalar, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Nöbet Ekle — {tarih}")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20,20,20,20)
        lay.setSpacing(12)
        lbl = QLabel(f"<b>{tarih}</b>")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        form = QFormLayout()
        self._cmb_p = QComboBox()
        self._cmb_p.setEditable(True)
        self._cmb_p.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for p in personeller:
            self._cmb_p.addItem(p.get("AdSoyad",""), userData=p.get("pid",""))
        form.addRow("Personel:", self._cmb_p)
        self._cmb_v = QComboBox()
        for v in vardiyalar:
            lbl2 = f"{v.get('VardiyaAdi','')} ({v.get('BasSaat','')}–{v.get('BitSaat','')})"
            self._cmb_v.addItem(lbl2, userData=v.get("VardiyaID",""))
        form.addRow("Vardiya:", self._cmb_v)
        self._cmb_tur = QComboBox()
        self._cmb_tur.addItem("Normal", userData="normal")
        self._cmb_tur.addItem("Fazla Mesai", userData="fazla_mesai")
        form.addRow("Tür:", self._cmb_tur)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "PersonelID": self._cmb_p.currentData(),
            "VardiyaID":  self._cmb_v.currentData(),
            "NobetTuru":  self._cmb_tur.currentData(),
        }


class NobetPlanPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._ag  = action_guard
        self._yil = date.today().year
        self._ay  = date.today().month
        self._plan_data  = []
        self._v_map      = {}
        self._p_map      = {}
        self._pid_list   = []
        self._tatil_set  = set()
        self._dini_set   = set()
        self._onay_durumu = "yok"
        self._slot_sayisi = 4
        self._birim_adi   = ""
        self._birim_id    = ""
        self._fm_gonullu: set  = set()   # FM Gönüllü pid seti
        # Vardiya grubu yapısı: [{"GrupAdi", "BasSaat", "BitSaat", "VardiyaIDler":[]}]
        self._gruplar: list[dict] = []
        self.setProperty("bg-role", "page")
        self._build()
        if db:
            self._birimleri_yukle()

    def _svc(self):
        return get_nobet_service(self._db)

    def _reg(self):
        from core.di import get_registry
        return get_registry(self._db)

    def _ay_etiketi(self):
        return f"{_AY_TR[self._ay]}\n{self._yil}"

    # ──────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────

    def _build(self):
        ana = QHBoxLayout(self)
        ana.setContentsMargins(0,0,0,0)
        ana.setSpacing(0)
        ana.addWidget(self._build_sol())
        orta = QWidget()
        orta.setProperty("bg-role","page")
        ol = QVBoxLayout(orta)
        ol.setContentsMargins(0,0,0,0)
        ol.setSpacing(0)
        ol.addWidget(self._build_onay_bar())
        ol.addWidget(self._build_tablo(), 1)
        ol.addWidget(self._build_footer())
        ana.addWidget(orta, 1)
        ana.addWidget(self._build_bilgi_panel())

    def _grp(self, baslik):
        g = QGroupBox(baslik)
        g.setProperty("style-role","group")
        return g

    def _build_sol(self):
        sol = QFrame()
        sol.setFixedWidth(230)
        sol.setProperty("bg-role","panel")
        lay = QVBoxLayout(sol)
        lay.setContentsMargins(12,14,12,14)
        lay.setSpacing(10)

        g1 = self._grp("Dönem")
        gl = QVBoxLayout(g1)
        nav = QHBoxLayout()
        bg = QPushButton("‹")
        bg.setFixedSize(28,28)
        bg.setProperty("style-role","secondary")
        bg.clicked.connect(self._ay_geri)
        self._lbl_ay = QLabel()
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role","section-title")
        bi = QPushButton("›")
        bi.setFixedSize(28,28)
        bi.setProperty("style-role","secondary")
        bi.clicked.connect(self._ay_ileri)
        nav.addWidget(bg); nav.addWidget(self._lbl_ay,1); nav.addWidget(bi)
        gl.addLayout(nav)
        lay.addWidget(g1)

        g2 = self._grp("Birim")
        bl = QVBoxLayout(g2)
        self._cmb_birim = QComboBox()
        self._cmb_birim.currentIndexChanged.connect(self._on_birim)
        bl.addWidget(self._cmb_birim)
        lay.addWidget(g2)

        g3 = self._grp("Ön Hazırlık")
        hl = QVBoxLayout(g3)
        hl.setSpacing(4)
        self._lbl_hazirlik = QLabel("— Henüz onaylanmadı —")
        self._lbl_hazirlik.setWordWrap(True)
        self._lbl_hazirlik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_hazirlik.setStyleSheet(
            "font-size:10px;color:#e85555;padding:2px;")
        hl.addWidget(self._lbl_hazirlik)
        self._btn_hazirlik = QPushButton("✔  Hazırlığı Onayla")
        self._btn_hazirlik.setProperty("style-role","action")
        self._btn_hazirlik.setFixedHeight(28)
        self._btn_hazirlik.setEnabled(False)
        self._btn_hazirlik.clicked.connect(self._hazirlik_onayla)
        hl.addWidget(self._btn_hazirlik)
        self._btn_hazirlik_iptal = QPushButton("Onayı Geri Al")
        self._btn_hazirlik_iptal.setProperty("style-role","danger")
        self._btn_hazirlik_iptal.setFixedHeight(24)
        self._btn_hazirlik_iptal.setVisible(False)
        self._btn_hazirlik_iptal.clicked.connect(self._hazirlik_iptal)
        hl.addWidget(self._btn_hazirlik_iptal)
        lay.addWidget(g3)

        g4 = self._grp("Planlama")
        pl = QVBoxLayout(g4)
        pl.setSpacing(6)
        self._btn_oto = QPushButton("⚡  Otomatik Plan")
        self._btn_oto.setProperty("style-role","action")
        self._btn_oto.setFixedHeight(32)
        self._btn_oto.setEnabled(False)   # Hazırlık onayına kadar kilitli
        self._btn_oto.setToolTip("Önce 'Ön Hazırlık' onaylanmalıdır")
        self._btn_oto.clicked.connect(self._oto_plan)
        pl.addWidget(self._btn_oto)
        self._btn_temizle = QPushButton("✕  Taslağı Temizle")
        self._btn_temizle.setProperty("style-role","danger")
        self._btn_temizle.setFixedHeight(28)
        self._btn_temizle.clicked.connect(self._temizle)
        pl.addWidget(self._btn_temizle)
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(3)
        self._pbar.setRange(0,0)
        self._pbar.setVisible(False)
        pl.addWidget(self._pbar)
        lay.addWidget(g4)

        g5_onay = self._grp("Onay")
        ol2 = QVBoxLayout(g5_onay)
        self._lbl_onay = QLabel("—")
        self._lbl_onay.setWordWrap(True)
        self._lbl_onay.setStyleSheet("font-size:11px;")
        ol2.addWidget(self._lbl_onay)
        br = QHBoxLayout()
        self._btn_onayla = QPushButton("✔  Onayla")
        self._btn_onayla.setProperty("style-role","action")
        self._btn_onayla.setFixedHeight(28)
        self._btn_onayla.setEnabled(False)
        self._btn_onayla.clicked.connect(self._onayla)
        br.addWidget(self._btn_onayla)
        self._btn_ogeri = QPushButton("Geri Al")
        self._btn_ogeri.setProperty("style-role","secondary")
        self._btn_ogeri.setFixedHeight(28)
        self._btn_ogeri.setVisible(False)
        self._btn_ogeri.clicked.connect(self._onay_geri_al)
        br.addWidget(self._btn_ogeri)
        ol2.addLayout(br)
        lay.addWidget(g5_onay)

        g5 = self._grp("Personel Tercihleri")
        ql = QVBoxLayout(g5)
        ql.setContentsMargins(4,6,4,4)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        self._p_widget = QWidget()
        self._p_lay    = QVBoxLayout(self._p_widget)
        self._p_lay.setContentsMargins(2,2,2,2)
        self._p_lay.setSpacing(2)
        sc.setWidget(self._p_widget)
        ql.addWidget(sc)
        lay.addWidget(g5, 1)
        return sol

    def _build_onay_bar(self):
        bar = QFrame()
        bar.setProperty("bg-role","elevated")
        bar.setFixedHeight(26)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16,0,16,0)
        self._lbl_onay_bar = QLabel("")
        self._lbl_onay_bar.setStyleSheet("font-size:11px;")
        h.addWidget(self._lbl_onay_bar)
        h.addStretch()
        self._lbl_plan_bilgi = QLabel("")
        self._lbl_plan_bilgi.setProperty("color-role","muted")
        self._lbl_plan_bilgi.setStyleSheet("font-size:10px;")
        h.addWidget(self._lbl_plan_bilgi)
        btn_bilgi = QPushButton("📋  Ay Bilgileri")
        btn_bilgi.setProperty("style-role","secondary")
        btn_bilgi.setFixedHeight(20)
        btn_bilgi.setStyleSheet("font-size:10px;")
        btn_bilgi.clicked.connect(
            lambda: self._bilgi_panel.setVisible(
                not self._bilgi_panel.isVisible()))
        h.addWidget(btn_bilgi)
        return bar

    def _build_tablo(self):
        self._tablo = QTableWidget(0,0)
        self._tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tablo.verticalHeader().setVisible(False)
        self._tablo.setShowGrid(True)
        self._tablo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tablo.customContextMenuRequested.connect(self._kontekst_menu)
        self._tablo.cellDoubleClicked.connect(self._cift_tikla)
        self._tablo.horizontalHeader().setDefaultSectionSize(110)
        return self._tablo

    def _build_bilgi_panel(self) -> QFrame:
        """Sağ taraf bilgi/hatırlatma paneli."""
        self._bilgi_panel = QFrame()
        self._bilgi_panel.setFixedWidth(260)
        self._bilgi_panel.setProperty("bg-role","panel")

        lay = QVBoxLayout(self._bilgi_panel)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        # Başlık + aç/kapat butonu
        hdr = QFrame()
        hdr.setProperty("bg-role","elevated")
        hdr.setFixedHeight(32)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12,0,8,0)
        lbl = QLabel("📋  Ay Bilgileri")
        lbl.setStyleSheet("font-size:12px;font-weight:600;color:#8aabcf;")
        hl.addWidget(lbl, 1)
        self._btn_bilgi_kapat = QPushButton("✕")
        self._btn_bilgi_kapat.setFixedSize(22,22)
        self._btn_bilgi_kapat.setProperty("style-role","secondary")
        self._btn_bilgi_kapat.setToolTip("Paneli gizle")
        self._btn_bilgi_kapat.clicked.connect(
            lambda: self._bilgi_panel.setVisible(False))
        hl.addWidget(self._btn_bilgi_kapat)
        lay.addWidget(hdr)

        # İçerik (kaydırılabilir)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        self._bilgi_icerik = QWidget()
        self._bilgi_lay    = QVBoxLayout(self._bilgi_icerik)
        self._bilgi_lay.setContentsMargins(10,10,10,10)
        self._bilgi_lay.setSpacing(10)
        sc.setWidget(self._bilgi_icerik)
        lay.addWidget(sc, 1)

        return self._bilgi_panel

    def _bilgi_guncelle(self):
        """Bilgi panelini ay ve birim verisiyle doldurur."""
        lay = self._bilgi_lay
        # Temizle
        while lay.count():
            w = lay.takeAt(0).widget()
            if w: w.deleteLater()

        if not self._birim_adi:
            lay.addWidget(QLabel("Birim seçin",
                styleSheet="color:#555;font-size:11px;"))
            lay.addStretch()
            return

        try:
            from core.hesaplamalar import ay_is_gunu
            reg = self._reg()

            # ── Ay özeti ────────────────────────────────────────
            self._bilgi_blok(lay, "📅  Ay Özeti")

            t_rows = reg.get("Tatiller").get_all() or []
            ab = f"{self._yil:04d}-{self._ay:02d}-01"
            ae = f"{self._yil:04d}-{self._ay:02d}-31"
            tatiller = [str(r.get("Tarih","")) for r in t_rows
                        if ab <= str(r.get("Tarih","")) <= ae
                        and str(r.get("TatilTuru","")) in ("Resmi","DiniBayram")]
            resmi    = [t for t in tatiller
                        if next((r for r in t_rows
                                 if r.get("Tarih")==t
                                 and r.get("TatilTuru")=="Resmi"), None)]
            dini     = [t for t in tatiller
                        if next((r for r in t_rows
                                 if r.get("Tarih")==t
                                 and r.get("TatilTuru")=="DiniBayram"), None)]

            gun_sayisi = monthrange(self._yil, self._ay)[1]
            is_gunu    = ay_is_gunu(self._yil, self._ay, tatil_listesi=tatiller)
            hedef_saat = is_gunu * 7

            self._bilgi_satir(lay, "Toplam gün",    f"{gun_sayisi} gün")
            self._bilgi_satir(lay, "İş günü",       f"{is_gunu} gün",
                              renk="#2ec98e")
            self._bilgi_satir(lay, "Hedef mesai",   f"{hedef_saat} saat",
                              renk="#4d9ee8")
            if resmi:
                self._bilgi_satir(lay, "Resmi tatil",
                                  f"{len(resmi)} gün", renk="#e85555")
            if dini:
                self._bilgi_satir(lay, "Dini bayram",
                                  f"{len(dini)} gün", renk="#e8a030")

            # Hafta sonu sayısı
            hs = sum(1 for g in range(1, gun_sayisi+1)
                     if date(self._yil, self._ay, g).weekday() >= 5)
            self._bilgi_satir(lay, "Hafta sonu", f"{hs} gün",
                              renk="#6b7280")

            # ── İzindeki personel ────────────────────────────────
            iz_rows   = reg.get("Izin_Giris").get_all() or []
            p_rows    = reg.get("Personel").get_all() or []
            p_ad      = {str(p["KimlikNo"]): p.get("AdSoyad","")
                         for p in p_rows}
            ay_bas_d  = date(self._yil, self._ay, 1)
            ay_bit_d  = date(self._yil, self._ay, gun_sayisi)

            izinliler: list[dict] = []
            for r in iz_rows:
                pid = str(r.get("Personelid",""))
                if pid not in self._pid_set():
                    continue
                if str(r.get("Durum","")).strip() not in (
                        "Onaylandı","onaylandi","onaylı","approved"):
                    continue
                try:
                    bas = date.fromisoformat(str(r.get("BaslamaTarihi","")))
                    bit = date.fromisoformat(str(r.get("BitisTarihi","")))
                except Exception:
                    continue
                # Bu ayla kesişiyor mu?
                if bit < ay_bas_d or bas > ay_bit_d:
                    continue
                giren_bas = max(bas, ay_bas_d)
                giren_bit = min(bit, ay_bit_d)
                gun_str   = (f"{giren_bas.day}-{giren_bit.day} "
                             f"{_AY_TR[self._ay]}"
                             if giren_bas != giren_bit
                             else f"{giren_bas.day} {_AY_TR[self._ay]}")
                izinliler.append({
                    "ad":     p_ad.get(pid, pid),
                    "tur":    str(r.get("IzinTipi","")),
                    "tarih":  gun_str,
                    "sure":   (giren_bit - giren_bas).days + 1,
                })
            izinliler.sort(key=lambda x: x["tarih"])

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color:#1e2d40;")
            lay.addWidget(sep)

            if izinliler:
                self._bilgi_blok(lay,
                    f"🏖️  İzindeki Personel ({len(izinliler)})")
                for iz in izinliler:
                    w  = QWidget()
                    rl = QHBoxLayout(w)
                    rl.setContentsMargins(4,2,4,2)
                    rl.setSpacing(4)
                    ad_lbl = QLabel(iz["ad"][:18])
                    ad_lbl.setStyleSheet(
                        "font-size:11px;color:#c2d8ef;font-weight:600;")
                    rl.addWidget(ad_lbl, 1)
                    bilgi = QLabel(iz["tarih"])
                    bilgi.setStyleSheet(
                        "font-size:10px;color:#e8a030;")
                    bilgi.setAlignment(Qt.AlignmentFlag.AlignRight)
                    rl.addWidget(bilgi)
                    lay.addWidget(w)
                    # İzin türü
                    tur_lbl = QLabel(
                        f"  {iz['tur']}  —  {iz['sure']} gün")
                    tur_lbl.setStyleSheet(
                        "font-size:10px;color:#6b7280;"
                        "padding-left:4px;")
                    lay.addWidget(tur_lbl)
            else:
                self._bilgi_blok(lay, "🏖️  İzindeki Personel")
                ekl = QLabel("Bu ay izinli personel yok")
                ekl.setStyleSheet("font-size:11px;color:#555;padding:4px;")
                ekl.setWordWrap(True)
                lay.addWidget(ekl)

            # ── Plan durumu özeti ─────────────────────────────────
            if self._plan_data:
                sep2 = QFrame()
                sep2.setFrameShape(QFrame.Shape.HLine)
                sep2.setStyleSheet("color:#1e2d40;")
                lay.addWidget(sep2)

                self._bilgi_blok(lay, "📊  Plan Özeti")
                toplam     = len(self._plan_data)
                gun_sayisi2 = monthrange(self._yil, self._ay)[1]
                dolu_gunler = len({
                    str(s.get("NobetTarihi",""))
                    for s in self._plan_data})
                self._bilgi_satir(lay, "Toplam atama",
                                  str(toplam), renk="#2ec98e")
                self._bilgi_satir(lay, "Dolu gün",
                                  f"{dolu_gunler}/{gun_sayisi2}")
                # Kişi başı ortalama
                kisi_sayi = {
                    str(s.get("PersonelID",""))
                    for s in self._plan_data}
                if kisi_sayi:
                    ort = round(toplam / len(kisi_sayi), 1)
                    self._bilgi_satir(lay, "Kişi başı ort.",
                                      f"{ort} nöbet")

        except Exception as e:
            logger.error(f"bilgi_guncelle: {e}")
            ekl = QLabel(f"Yüklenemedi: {e}")
            ekl.setStyleSheet("color:#e85555;font-size:10px;")
            ekl.setWordWrap(True)
            lay.addWidget(ekl)

        lay.addStretch()

    def _pid_set(self) -> set[str]:
        return set(self._pid_list)

    def _bilgi_blok(self, lay, baslik: str):
        lbl = QLabel(baslik)
        lbl.setStyleSheet(
            "font-size:11px;font-weight:600;color:#8aabcf;"
            "padding:4px 0 2px 0;")
        lay.addWidget(lbl)

    def _bilgi_satir(self, lay, anahtar: str, deger: str,
                     renk: str = "#c2d8ef"):
        w   = QWidget()
        rl  = QHBoxLayout(w)
        rl.setContentsMargins(4, 1, 4, 1)
        k   = QLabel(anahtar)
        k.setStyleSheet("font-size:11px;color:#6b7280;")
        d   = QLabel(deger)
        d.setStyleSheet(f"font-size:11px;color:{renk};font-weight:600;")
        d.setAlignment(Qt.AlignmentFlag.AlignRight)
        rl.addWidget(k, 1)
        rl.addWidget(d)
        lay.addWidget(w)

    def _build_footer(self):
        f = QFrame()
        f.setProperty("bg-role","panel")
        f.setFixedHeight(24)
        h = QHBoxLayout(f)
        h.setContentsMargins(12,0,12,0)
        self._lbl_status = QLabel("")
        self._lbl_status.setProperty("color-role","muted")
        self._lbl_status.setStyleSheet("font-size:10px;")
        h.addWidget(self._lbl_status)
        return f

    # ──────────────────────────────────────────────────────────
    #  Veri
    # ──────────────────────────────────────────────────────────

    def _birimleri_yukle(self):
        try:
            self._cmb_birim.blockSignals(True)
            self._cmb_birim.clear()
            self._cmb_birim.addItem("— Birim Seçin —", userData=("",""))
            for b in (self._svc().get_birimler().veri or []):
                if isinstance(b,dict):
                    self._cmb_birim.addItem(b.get("BirimAdi",""), userData=(b.get("BirimAdi",""), b.get("BirimID","")))
                else:
                    self._cmb_birim.addItem(str(b), userData=(str(b),""))
            self._cmb_birim.blockSignals(False)
        except Exception as e:
            logger.error(f"birimleri_yukle: {e}")

    def _on_birim(self):
        data = self._cmb_birim.currentData()
        if not data: return
        self._birim_adi, self._birim_id = data
        self._yukle()

    def _ay_geri(self):
        self._ay, self._yil = (12, self._yil-1) if self._ay==1 else (self._ay-1, self._yil)
        self._yukle()

    def _ay_ileri(self):
        self._ay, self._yil = (1, self._yil+1) if self._ay==12 else (self._ay+1, self._yil)
        self._yukle()

    def _yukle(self):
        self._lbl_ay.setText(self._ay_etiketi())
        if not self._birim_adi: return
        try:
            svc = self._svc()
            reg = self._reg()

            v_rows = reg.get("NB_Vardiya").get_all() or []
            self._v_map = {str(v["VardiyaID"]): dict(v) for v in v_rows}

            p_rows = reg.get("Personel").get_all() or []
            self._p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_rows}

            t_rows = reg.get("Tatiller").get_all() or []
            ab = f"{self._yil:04d}-{self._ay:02d}-01"
            ae = f"{self._yil:04d}-{self._ay:02d}-31"
            self._tatil_set = {str(r.get("Tarih","")) for r in t_rows
                               if ab<=str(r.get("Tarih",""))<=ae and str(r.get("TatilTuru",""))=="Resmi"}
            self._dini_set  = {str(r.get("Tarih","")) for r in t_rows
                               if ab<=str(r.get("Tarih",""))<=ae and str(r.get("TatilTuru",""))=="DiniBayram"}

            sonuc = svc.get_plan(self._yil, self._ay, self._birim_adi)
            self._plan_data = sonuc.veri or [] if sonuc.basarili else []
            for r in self._plan_data:
                if not r.get("AdSoyad"):
                    r["AdSoyad"] = self._p_map.get(str(r.get("PersonelID","")), "")

            onay_rows = (svc.onay_getir(self._yil,self._ay,self._birim_adi).veri or [])
            self._onay_durumu = onay_rows[0].get("Durum","yok") if onay_rows else "yok"

            self._pid_list = self._personel_listesi()

            try:
                a_rows = reg.get("NB_BirimAyar").get_all() or []
                ayar   = next((r for r in a_rows if str(r.get("BirimID",""))==self._birim_id), None)
                self._slot_sayisi = int((ayar or {}).get("GunlukSlotSayisi", 4))
            except Exception:
                self._slot_sayisi = 4

            # FM Gönüllü seti: NB_PersonelTercih'ten oku
            try:
                reg = self._reg()
                t_rows = reg.get("NB_PersonelTercih").get_all() or []
                bid = self._birim_id
                self._fm_gonullu = {
                    str(r.get("PersonelID",""))
                    for r in t_rows
                    if str(r.get("BirimID","")) == bid
                    and int(r.get("Yil", 0)) == self._yil
                    and int(r.get("Ay",  0)) == self._ay
                    and str(r.get("NobetTercihi","")) == "fazla_mesai_gonullu"
                }
            except Exception:
                self._fm_gonullu = set()

            # Grupları al
            self._gruplar = self._gruplari_olustur()

        except Exception as e:
            logger.error(f"yukle: {e}")
            self._plan_data = []
            self._pid_list  = []
            self._gruplar   = []

        self._ciz()
        self._onay_guncelle()
        self._tercih_goster()
        self._bilgi_guncelle()
        self._hazirlik_guncelle()

    def _personel_listesi(self):
        try:
            from core.di import get_nb_birim_personel_service
            if self._birim_id:
                pids = get_nb_birim_personel_service(self._db).personel_pid_listesi(self._birim_id)
                if pids:
                    return sorted(pids, key=lambda p: self._p_map.get(p,""))
        except Exception:
            pass
        try:
            p_rows = self._reg().get("Personel").get_all() or []
            return sorted(
                [str(p["KimlikNo"]) for p in p_rows
                 if str(p.get("GorevYeri","")).strip()==self._birim_adi],
                key=lambda p: self._p_map.get(p,""))
        except Exception:
            return []

    def _gruplari_olustur(self):
        """
        Her ANA VARDİYA → ayrı kolon grubu.

        Örnek: "24 Saat Nöbet" grubu iki vardiyaya sahipse:
          - VardiyaID_1: Gündüz 08:00-20:00  → kendi slot sütunları
          - VardiyaID_2: Gece   20:00-08:00  → kendi slot sütunları

        Plan indeksi: {tarih: {vardiya_id: [kisi_adlari]}}
        Her kişi bir vardiyaya atanır, tabloda doğru kolona düşer.
        """
        try:
            reg    = self._reg()
            g_rows = reg.get("NB_VardiyaGrubu").get_all() or []
            v_rows = reg.get("NB_Vardiya").get_all() or []

            aktif_gruplar = sorted(
                [g for g in g_rows
                 if str(g.get("BirimID","")) == self._birim_id
                 and int(g.get("Aktif",1))],
                key=lambda g: int(g.get("Sira",1)))

            if not aktif_gruplar:
                raise ValueError("Grup yok")

            sonuc = []
            for g in aktif_gruplar:
                gid   = g["GrupID"]
                ana_v = sorted(
                    [v for v in v_rows
                     if str(v.get("GrupID","")) == gid
                     and v.get("Rol","ana") == "ana"
                     and int(v.get("Aktif",1))],
                    key=lambda v: int(v.get("Sira",1)))

                for v in ana_v:
                    bas = v.get("BasSaat","")
                    bit = v.get("BitSaat","")
                    sonuc.append({
                        "GrupAdi":      v.get("VardiyaAdi", f"{bas}-{bit}"),
                        "Baslik":       f"{bas} - {bit}",
                        "VardiyaID":    v["VardiyaID"],   # tek vardiya
                        "VardiyaIDler": [v["VardiyaID"]], # uyumluluk
                        "slot_sayisi":  min(self._slot_sayisi, MAX_SLOT_PER_GRUP),
                        "BasSaat":      bas,
                    })
            return sonuc if sonuc else self._gruplar_fallback()
        except Exception:
            return self._gruplar_fallback()

    def _gruplar_fallback(self):
        """NB_VardiyaGrubu tanımlı değilse BasSaat'e göre varsayılan."""
        ana_v = sorted(
            [(vid, v) for vid,v in self._v_map.items()
             if v.get("Rol","ana") == "ana"],
            key=lambda x: x[1].get("BasSaat","00:00"))
        if not ana_v:
            return []
        sonuc = []
        for vid, v in ana_v:
            bas = v.get("BasSaat","")
            bit = v.get("BitSaat","")
            sonuc.append({
                "GrupAdi":      v.get("VardiyaAdi", f"{bas}-{bit}"),
                "Baslik":       f"{bas} - {bit}",
                "VardiyaID":    vid,
                "VardiyaIDler": [vid],
                "slot_sayisi":  min(self._slot_sayisi, MAX_SLOT_PER_GRUP),
                "BasSaat":      bas,
            })
        return sonuc

    # ──────────────────────────────────────────────────────────
    #  Tablo çizimi (Excel benzeri)
    # ──────────────────────────────────────────────────────────

    def _ciz(self):
        self._tablo.clearSpans()
        self._tablo.setRowCount(0)
        self._tablo.setColumnCount(0)

        if not self._gruplar:
            self._lbl_status.setText("Birim seçin veya vardıya tanımlayın")
            return

        gun_sayisi = monthrange(self._yil, self._ay)[1]

        # Sütun yapısı:
        # [0]=Tarih [1]=Gün  |  Grup1: slot_sayisi sütun  |  Grup2: slot_sayisi sütun  | ...
        toplam_slot = sum(g["slot_sayisi"] for g in self._gruplar)
        toplam_sutun = 2 + toplam_slot
        self._tablo.setColumnCount(toplam_sutun)
        self._tablo.setRowCount(2 + gun_sayisi)  # satır0=grup header, satır1=? (yok), satır2..=günler

        # Aslında 2 header satırı yerine 1 satır header + setSpan kullanalım
        # Satır 0: "Tarih" | "Gün" | GrupBaslık(merged) | GrupBaslık(merged) |...
        # Satır 1..gun_sayisi+1: gün verileri
        self._tablo.setRowCount(1 + gun_sayisi)

        bold = QFont()
        bold.setBold(True)
        bold_kucuk = QFont()
        bold_kucuk.setBold(True)
        bold_kucuk.setPointSize(9)

        # ── Satır 0: Başlıklar ──
        def header_item(txt, renk="#8aabcf"):
            it = QTableWidgetItem(txt)
            it.setFont(bold)
            it.setBackground(QBrush(QColor(C["header_bg"])))
            it.setForeground(QColor(renk))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            return it

        self._tablo.setItem(0, 0, header_item("Tarih"))
        self._tablo.setColumnWidth(0, 90)
        self._tablo.setItem(0, 1, header_item("Gün"))
        self._tablo.setColumnWidth(1, 95)

        ci = 2
        for g in self._gruplar:
            n = g["slot_sayisi"]
            try:
                bas_h = int(g.get("BasSaat","08:00").split(":")[0])
                h_renk = "#f59e0b" if (bas_h >= 19 or bas_h < 6) else "#4d9ee8"
            except Exception:
                h_renk = "#8aabcf"
            it = header_item(g["Baslik"], h_renk)
            self._tablo.setItem(0, ci, it)
            if n > 1:
                self._tablo.setSpan(0, ci, 1, n)
            for k in range(n):
                self._tablo.setColumnWidth(ci+k, 115)
            ci += n

        self._tablo.setRowHeight(0, 28)

        # ── Plan indeksi: {tarih: {vardiya_id: [kisi_adlari, ...]}} ──
        plan_idx:   dict[str, dict[str, list[str]]]  = {}
        satir_idx:  dict[str, dict[str, list[dict]]] = {}

        for s in self._plan_data:
            tarih = str(s.get("NobetTarihi",""))
            vid   = str(s.get("VardiyaID",""))
            ad    = str(s.get("AdSoyad","") or
                        self._p_map.get(str(s.get("PersonelID","")), ""))
            plan_idx.setdefault(tarih, {}).setdefault(vid, []).append(ad)
            satir_idx.setdefault(tarih, {}).setdefault(vid, []).append(s)

        onaylanmis = self._onay_durumu in ("onaylandi","yururlukte")

        # ── Gün satırları ──
        for gun in range(1, gun_sayisi+1):
            ri    = gun  # 0=header, 1=1.gün, ...
            tarih = f"{self._yil:04d}-{self._ay:02d}-{gun:02d}"
            gund  = date(self._yil, self._ay, gun)
            is_hw = gund.weekday() >= 5
            is_t  = tarih in self._tatil_set
            is_d  = tarih in self._dini_set

            # Satır arka plan rengi
            if is_d:
                row_bg = C["dini_bg"]
            elif is_t:
                row_bg = C["tatil_bg"]
            elif is_hw:
                row_bg = C["haftasonu_bg"]
            elif onaylanmis:
                row_bg = C["onay_bg"]
            else:
                row_bg = C["normal_bg"]

            self._tablo.setRowHeight(ri, 28)

            # Tarih hücresi: "1.07.2025"
            tarih_str = f"{gun}.{self._ay:02d}.{self._yil}"
            tarih_item = QTableWidgetItem(tarih_str)
            tarih_item.setBackground(QBrush(QColor(row_bg)))
            tarih_item.setForeground(QColor(C["gun_renk_hs"] if is_hw else C["tarih_renk"]))
            tarih_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tarih_item.setFont(bold_kucuk)
            tarih_item.setData(Qt.ItemDataRole.UserRole,
                               {"tarih": tarih, "gun": gun, "tip": "tarih"})
            self._tablo.setItem(ri, 0, tarih_item)

            # Gün hücresi: "Salı"
            gun_adi = _GUN_TR[gund.weekday()]
            if is_d:
                gun_adi += " \U0001f54c"
            elif is_t:
                gun_adi += " \U0001f3c1"
            gun_item = QTableWidgetItem(gun_adi)
            gun_item.setBackground(QBrush(QColor(row_bg)))
            gun_item.setForeground(QColor(C["gun_renk_hs"] if is_hw else C["gun_renk"]))
            gun_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                       Qt.AlignmentFlag.AlignLeft)
            gun_item.setData(Qt.ItemDataRole.UserRole,
                             {"tarih": tarih, "gun": gun, "tip": "gun"})
            self._tablo.setItem(ri, 1, gun_item)

            # Kişi sütunları
            ci = 2
            for g in self._gruplar:
                vid        = g["VardiyaID"]
                kisiler    = plan_idx.get(tarih, {}).get(vid, [])
                satirlar_g = satir_idx.get(tarih, {}).get(vid, [])
                n          = g["slot_sayisi"]
                for ki in range(n):
                    ad    = kisiler[ki] if ki < len(kisiler) else ""
                    satir = satirlar_g[ki] if ki < len(satirlar_g) else None
                    kisi_item = QTableWidgetItem(ad if ad else "—")
                    kisi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if ad:
                        bg = (C["kisi_bg_onay"] if onaylanmis else
                              C["kisi_bg_hs"]   if is_hw      else
                              C["kisi_bg"])
                        kisi_item.setForeground(QColor(C["kisi_renk"]))
                        kisi_item.setFont(bold_kucuk)
                    else:
                        # Boş slot — tatil/dini değilse kırmızı uyarı
                        if is_d or is_t:
                            bg = row_bg
                            kisi_item.setText("")
                            kisi_item.setForeground(QColor("#444"))
                        elif is_hw:
                            bg = C["bos_kisi_hs"]
                            kisi_item.setForeground(QColor("#e85555"))
                        else:
                            bg = "#1a0a0a"   # koyu kırmızı — boş slot uyarısı
                            kisi_item.setForeground(QColor("#e85555"))
                    kisi_item.setBackground(QBrush(QColor(bg)))
                    kisi_item.setData(Qt.ItemDataRole.UserRole, {
                        "tarih": tarih, "gun": gun,
                        "vardiya_id": vid, "slot_ki": ki,
                        "satir": satir, "tip": "kisi",
                    })
                    self._tablo.setItem(ri, ci+ki, kisi_item)
                ci += n

        # Başlık satırı sabitle
        self._tablo.horizontalHeader().setVisible(False)

        self._lbl_status.setText(
            f"{self._birim_adi}  |  {_AY_TR[self._ay]} {self._yil}  |  "
            f"{len(self._plan_data)} nöbet  |  Durum: {self._onay_durumu}")
        self._lbl_plan_bilgi.setText(
            f"Slot: {self._slot_sayisi}/gün  |  Toplam: {len(self._plan_data)}")

    # ──────────────────────────────────────────────────────────
    #  Onay & Sol Panel
    # ──────────────────────────────────────────────────────────

    def _onay_guncelle(self):
        d = {
            "yok":        ("Plan yok",                  "#6b7280"),
            "taslak":     ("\U0001f4cb  Taslak",          "#f59e0b"),
            "onaylandi":  ("✔  Onaylandı",      "#22c55e"),
            "yururlukte": ("✔  Yürürlükte","#22c55e"),
        }
        metin, renk = d.get(self._onay_durumu,("?","#888"))
        self._lbl_onay.setText(f"<span style='color:{renk}'>{metin}</span>")
        self._lbl_onay_bar.setText(
            f"<span style='color:{renk}'>{metin}</span>  "
            f"<span style='color:#555;font-size:10px;'>"
            f"{_AY_TR[self._ay]} {self._yil} — {self._birim_adi}</span>")
        onaylanmis = self._onay_durumu in ("onaylandi","yururlukte")
        self._btn_onayla.setEnabled(self._onay_durumu=="taslak" and bool(self._plan_data))
        self._btn_ogeri.setVisible(onaylanmis)
        # Otomatik Plan: hem hazırlık onaylı hem de plan onaylı değil olmalı
        hazirlik_ok = getattr(self, "_hazirlik_onaylandi", False)
        self._btn_oto.setEnabled(hazirlik_ok and not onaylanmis)
        self._btn_oto.setToolTip(
            "" if hazirlik_ok
            else "Önce 'Ön Hazırlık' onaylanmalıdır")
        self._btn_temizle.setEnabled(self._onay_durumu=="taslak")

    def _tercih_goster(self):
        lay = self._p_lay
        while lay.count():
            w = lay.takeAt(0).widget()
            if w: w.deleteLater()
        if not self._pid_list:
            lay.addWidget(QLabel("Personel yok",
                styleSheet="color:#555;font-size:11px;"))
            return

        # Başlık
        baslik = QLabel("● = FM Gönüllü  ○ = Zorunlu")
        baslik.setStyleSheet("font-size:10px;color:#3a5a7a;padding:2px 4px;")
        lay.addWidget(baslik)

        plan_sayi: dict[str,int] = {}
        for s in self._plan_data:
            pid = str(s.get("PersonelID",""))
            plan_sayi[pid] = plan_sayi.get(pid,0)+1

        for pid in self._pid_list:
            ad     = self._p_map.get(pid, pid)
            fm     = pid in self._fm_gonullu
            renk   = FM_GONULLU_RENK if fm else "#4a6080"
            dot_ch = "●" if fm else "○"
            etiket = FM_GONULLU_ETIKET if fm else "Zorunlu"
            sayi   = plan_sayi.get(pid, 0)

            row = QWidget()
            row.setProperty("bg-role", "panel")
            row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(4)

            dot = QLabel(dot_ch)
            dot.setFixedWidth(14)
            dot.setStyleSheet(f"color:{renk};font-size:13px;")
            dot.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dot.setToolTip(f"Tıkla → FM Gönüllü değiştir\nMevcut: {etiket}")
            rl.addWidget(dot)

            ad_lbl = QLabel(ad[:20])
            ad_lbl.setStyleSheet("font-size:11px;")
            ad_lbl.setToolTip(f"{ad} — {etiket}")
            rl.addWidget(ad_lbl, 1)

            sayi_lbl = QLabel(str(sayi) if sayi else "—")
            sayi_lbl.setFixedWidth(24)
            sayi_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            sayi_lbl.setStyleSheet(
                f"font-size:10px;"
                f"color:{'#f59e0b' if sayi > 12 else '#6b7280'};")
            rl.addWidget(sayi_lbl)

            _pid = pid
            row.mousePressEvent = lambda e, p=_pid: \
                self._fm_toggler(p, e.globalPosition().toPoint())
            dot.mousePressEvent = lambda e, p=_pid: \
                self._fm_toggler(p, e.globalPosition().toPoint())

            lay.addWidget(row)
        lay.addStretch()

    def _fm_toggler(self, pid: str, global_pos=None):
        """FM Gönüllü durumunu aç/kapat."""
        from PySide6.QtGui import QCursor
        fm = pid in self._fm_gonullu
        yeni = "zorunlu" if fm else "fazla_mesai_gonullu"
        menu = QMenu(self._p_widget)
        act  = menu.addAction(
            "FM Gönüllü → Zorunlu yap" if fm else "Zorunlu → FM Gönüllü yap")
        menu.addSeparator()
        menu.addAction("İptal")
        pos = global_pos if global_pos is not None else QCursor.pos()
        secilen = menu.exec(pos)
        if not secilen or secilen.text() == "İptal":
            return
        try:
            svc   = self._svc()
            sonuc = svc.sadece_tercih_guncelle(
                personel_id   = pid,
                yil           = self._yil,
                ay            = self._ay,
                nobet_tercihi = yeni,
                birim         = self._birim_adi,
            )
            if sonuc.basarili:
                if yeni == "fazla_mesai_gonullu":
                    self._fm_gonullu.add(pid)
                else:
                    self._fm_gonullu.discard(pid)
                self._tercih_goster()
            else:
                QMessageBox.critical(self, "Hata", sonuc.mesaj)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  Kontekst Menü & Tıklamalar
    # ──────────────────────────────────────────────────────────

    def _kontekst_menu(self, pos):
        item = self._tablo.itemAt(pos)
        if not item: return
        veri = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(veri,dict) or veri.get("tip") not in ("kisi","tarih","gun"): return
        tarih    = veri.get("tarih","")
        satir    = veri.get("satir")
        is_d     = tarih in self._dini_set
        onaylanmis = self._onay_durumu in ("onaylandi","yururlukte")
        menu = QMenu(self._tablo)
        if not onaylanmis:
            a1 = menu.addAction("+ Nöbet Ekle")
            a1.triggered.connect(lambda: self._manuel_ekle(tarih))
        if satir and not onaylanmis:
            menu.addSeparator()
            v = self._v_map.get(satir.get("VardiyaID",""),{})
            ad = satir.get("AdSoyad","") or self._p_map.get(str(satir.get("PersonelID","")), "")
            a2 = menu.addAction(f"✕  {ad} — {v.get('VardiyaAdi','?')} kaldır")
            sid = satir["SatirID"]
            a2.triggered.connect(lambda checked=False,s=sid: self._satir_kaldir(s))
        if is_d and not onaylanmis:
            menu.addSeparator()
            a3 = menu.addAction("⚠  Fazla Mesai Ekle (Dini Bayram)")
            a3.triggered.connect(lambda: self._manuel_ekle(tarih, fazla=True))
        if menu.actions():
            menu.exec(self._tablo.viewport().mapToGlobal(pos))

    def _cift_tikla(self, row, col):
        if row == 0: return
        if self._onay_durumu in ("onaylandi","yururlukte"): return
        item = self._tablo.item(row, col)
        if not item: return
        veri = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(veri,dict) and veri.get("tarih"):
            self._manuel_ekle(veri["tarih"])

    # ──────────────────────────────────────────────────────────
    #  Aksiyonlar
    # ──────────────────────────────────────────────────────────

    def _hazirlik_guncelle(self):
        """NB_HazirlikOnay tablosunu kontrol et, UI'yi güncelle."""
        if not self._birim_id:
            self._hazirlik_onaylandi = False
            self._lbl_hazirlik.setText("— Birim seçin —")
            self._btn_hazirlik.setEnabled(False)
            self._btn_hazirlik_iptal.setVisible(False)
            return
        try:
            reg  = self._reg()
            rows = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay),
                None)
            onaylandi = bool(kayit)
            self._hazirlik_onaylandi = onaylandi
            if onaylandi:
                tarih = str(kayit.get("OnayTarihi",""))[:10]
                self._lbl_hazirlik.setText(
                    f"<span style='color:#2ec98e'>✔ Onaylandı</span>"
                    f"<br><span style='font-size:9px;color:#6b7280'>{tarih}</span>")
                self._btn_hazirlik.setEnabled(False)
                self._btn_hazirlik_iptal.setVisible(True)
            else:
                self._lbl_hazirlik.setText(
                    "<span style='color:#e85555'>✗ Onaylanmadı</span>")
                self._btn_hazirlik.setEnabled(True)
                self._btn_hazirlik_iptal.setVisible(False)
        except Exception as e:
            logger.error(f"_hazirlik_guncelle: {e}")
            self._hazirlik_onaylandi = False

    def _hazirlik_onayla(self):
        """Ön hazırlığı onayla — NB_HazirlikOnay'a kaydet."""
        if not self._birim_id:
            return
        try:
            from datetime import datetime
            reg   = self._reg()
            simdi = datetime.now().isoformat(sep=" ", timespec="seconds")
            rows  = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay),
                None)
            if kayit:
                reg.get("NB_HazirlikOnay").update(
                    kayit["OnayID"],
                    {"Durum": "onaylandi", "OnayTarihi": simdi})
            else:
                import uuid
                reg.get("NB_HazirlikOnay").insert({
                    "OnayID":     str(uuid.uuid4()),
                    "BirimID":    self._birim_id,
                    "Yil":        self._yil,
                    "Ay":         self._ay,
                    "Durum":      "onaylandi",
                    "OnayTarihi": simdi,
                    "created_at": simdi,
                })
            self._hazirlik_guncelle()
            self._onay_guncelle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _hazirlik_iptal(self):
        """Hazırlık onayını geri al."""
        cevap = QMessageBox.question(
            self, "Hazırlık Onayı Geri Al",
            "Ön hazırlık onayı geri alınacak.\n"
            "Otomatik Plan butonu kilitlenecek.\nEmin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes:
            return
        try:
            reg   = self._reg()
            rows  = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay),
                None)
            if kayit:
                reg.get("NB_HazirlikOnay").delete(kayit["OnayID"])
            self._hazirlik_guncelle()
            self._onay_guncelle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _oto_plan(self):
        if not self._birim_adi:
            QMessageBox.warning(self,"Uyarı","Birim seçin."); return
        if QMessageBox.question(self,"Otomatik Plan",
            f"{_AY_TR[self._ay]} {self._yil} — {self._birim_adi}\n\n"
            "Otomatik taslak oluşturulsun mu?\nMevcut taslak silinir.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes: return
        try:
            self._pbar.setVisible(True)
            self._btn_oto.setEnabled(False)
            s = self._svc().otomatik_plan_olustur(self._yil,self._ay,self._birim_adi)
            self._pbar.setVisible(False)
            self._btn_oto.setEnabled(True)
            if s.basarili:
                uyari = (s.veri or {}).get("uyarilar",[])
                msg = s.mesaj + ("\n\n⚠ Uyarılar:\n"+
                    "\n".join(f"• {u}" for u in uyari[:10]) if uyari else "")
                QMessageBox.information(self,"Tamamlandı",msg)
                self._yukle()
            else:
                QMessageBox.critical(self,"Hata",s.mesaj)
        except Exception as e:
            self._pbar.setVisible(False); self._btn_oto.setEnabled(True)
            QMessageBox.critical(self,"Hata",str(e))

    def _temizle(self):
        if not self._birim_adi: return
        if QMessageBox.question(self,"Taslağı Temizle",
            "Tüm taslak satırlar iptal edilsin mi?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes: return
        try:
            s = self._svc().taslak_temizle(self._yil,self._ay,self._birim_adi)
            if s.basarili: self._yukle()
            else: QMessageBox.critical(self,"Hata",s.mesaj)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def _onayla(self):
        if not self._birim_adi: return
        if QMessageBox.question(self,"Planı Onayla",
            f"{_AY_TR[self._ay]} {self._yil} planı onaylansın mı?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes: return
        try:
            svc = self._svc()
            onayla = ""
            try:
                from core.auth.session_context import get_session
                onayla = get_session().user_id or ""
            except Exception: pass
            s = svc.onayla(self._yil,self._ay,self._birim_adi,onayla)
            if s.basarili:
                QMessageBox.information(self,"Onaylandı",s.mesaj)
                self._yukle()
            else: QMessageBox.critical(self,"Hata",s.mesaj)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def _onay_geri_al(self):
        if QMessageBox.question(self,"Onayi Geri Al","Plan onayı geri alınacak.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes: return
        try:
            bid = self._birim_id
            if not bid:
                svc = self._svc()
                bid = svc._birim_id_coz(self._birim_adi) if hasattr(svc,"_birim_id_coz") else ""
            if not bid:
                QMessageBox.warning(self,"Hata","Birim ID bulunamadı."); return
            s = self._svc().plan.onay_geri_al(bid,self._yil,self._ay)
            if s.basarili: self._yukle()
            else: QMessageBox.critical(self,"Hata",s.mesaj)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def _manuel_ekle(self, tarih, fazla=False):
        try:
            svc = self._svc()
            v_sonuc = svc.get_vardiyalar(self._birim_adi)
            vardiyalar = v_sonuc.veri or [] if v_sonuc.basarili else []
            if not vardiyalar:
                QMessageBox.warning(self, "Uyarı",
                    "Bu birimde vardiya tanımlı değil.")
                return
            personeller = [
                {"pid": p, "AdSoyad": self._p_map.get(p, p)}
                for p in self._pid_list
            ]
            dialog = _ManuelDialog(tarih, personeller, vardiyalar, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            veri = dialog.get_data()
            if fazla:
                veri["NobetTuru"] = "fazla_mesai"

            bid = self._birim_id
            if not bid:
                bid = (svc._birim_id_coz(self._birim_adi)
                       if hasattr(svc, "_birim_id_coz") else "")

            plan_s = svc.plan.plan_al_veya_olustur(bid, self._yil, self._ay)
            if not plan_s.basarili:
                QMessageBox.critical(self, "Hata", plan_s.mesaj)
                return

            ekle_s = svc.plan.satir_ekle(
                plan_id      = plan_s.veri["PlanID"],
                personel_id  = veri["PersonelID"],
                vardiya_id   = veri["VardiyaID"],
                nobet_tarihi = tarih,
                kaynak       = "manuel",
                nobet_turu   = veri["NobetTuru"])

            if ekle_s.basarili:
                self._yukle()
            else:
                # Kısıt hatası — kullanıcıya override seçeneği sun
                cevap = QMessageBox.question(
                    self, "Kısıt Uyarısı",
                    f"⚠  {ekle_s.mesaj}\n\n"
                    "Yine de eklemek istiyor musunuz?\n"
                    "(Özel durum / acil müdahale için)",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)

                if cevap == QMessageBox.StandardButton.Yes:
                    # Kısıtı yok sayarak zorla ekle
                    ekle_s2 = svc.plan.satir_ekle(
                        plan_id      = plan_s.veri["PlanID"],
                        personel_id  = veri["PersonelID"],
                        vardiya_id   = veri["VardiyaID"],
                        nobet_tarihi = tarih,
                        kaynak       = "manuel_override",
                        nobet_turu   = veri["NobetTuru"],
                        kisit_atla   = True)
                    if ekle_s2.basarili:
                        self._yukle()
                    else:
                        QMessageBox.critical(self, "Hata", ekle_s2.mesaj)

        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _satir_kaldir(self, satir_id):
        try:
            s = self._svc().plan.satir_iptal(satir_id)
            if s.basarili: self._yukle()
            else: QMessageBox.critical(self,"Hata",s.mesaj)
        except Exception as e:
            QMessageBox.critical(self,"Hata",str(e))

    def load_data(self):
        self._birimleri_yukle()
