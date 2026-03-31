# -*- coding: utf-8 -*-
"""
nobet_plan_page.py — Nöbet Plan İçerik Modülü

Sadece takvim grid ve manuel nöbet panelini render eder.
Navigasyon, onay, aksiyonlar → NobetMerkezPage tarafından yönetilir.

Dışarıya açık API:
  yukle(birim_id, birim_adi, yil, ay)
  get_onay_durumu() -> str
  get_plan_data() -> list
  hazirlik_onay_degisti(onaylandi: bool)
"""
from __future__ import annotations
from calendar import monthrange
from datetime import date
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QScrollArea, QGridLayout,
    QSizePolicy, QLineEdit,
)
from core.di import get_nobet_service
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor, uyari_goster
from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors

_AY  = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
         "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
_GUN = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]


class _Hucre(QFrame):
    tiklandi = Signal(object, list)

    def __init__(self, gun: date, parent=None):
        super().__init__(parent)
        self.gun = gun
        self._nobetler: list[dict] = []
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        ust = QWidget()
        ust_l = QHBoxLayout(ust)
        ust_l.setContentsMargins(0, 0, 0, 0)
        ust_l.setSpacing(4)
        self._lbl = QLabel()
        self._lbl.setStyleSheet("font-size:11px;font-weight:600;")
        self._revizyon_badge = QLabel("REV")
        self._revizyon_badge.setVisible(False)
        self._revizyon_badge.setStyleSheet(
            "font-size:9px;font-weight:700;color:#f8fafc;"
            "background:#f59e0b;padding:1px 4px;border-radius:6px;"
        )
        ust_l.addWidget(self._lbl, 1)
        ust_l.addWidget(self._revizyon_badge, 0, Qt.AlignmentFlag.AlignRight)
        lay.addWidget(ust)
        self._alan = QWidget()
        al = QVBoxLayout(self._alan)
        al.setContentsMargins(0,0,0,0); al.setSpacing(0)
        lay.addWidget(self._alan, 1)

    def guncelle(self, nobetler, tatil=False, dini=False, secili=False,
                 eksik_slot=False, revizyon_var=False):
        self._nobetler = nobetler
        g, a = self.gun.day, self.gun.weekday()
        hf = a >= 5
        self._revizyon_badge.setVisible(revizyon_var)
        if secili:
            bg = "rgba(0,180,216,0.12)"
        elif dini:
            bg = "rgba(232,160,48,0.07)"
        elif tatil or hf:
            bg = "rgba(255,255,255,0.02)"
        else:
            bg = "transparent"

        if eksik_slot:
            border = "3px solid #e85555"
        elif secili:
            border = "3px solid #00b4d8"
        elif dini:
            border = "2px solid #e8a030"
        else:
            border = "2px solid rgba(255,255,255,0.06)"
        self.setStyleSheet(f"_Hucre{{background:{bg};border:{border};border-radius:0px;}}")
        renk = "#e8a030" if dini else ("#e85555" if tatil else "#4d9ee8" if hf else "#8aabcf")
        etiket = "(Dini Tatil)" if dini else ("(Resmi Tatil)" if tatil else "")
        self._lbl.setText(
            f"<span style='color:{renk}'>{g} {_GUN[a]} {etiket}</span>")
        al = self._alan.layout()
        while al.count():
            w = al.takeAt(0).widget()
            if w: w.deleteLater()
        for n in nobetler[:8]:
            ad = str(n.get("AdSoyad") or n.get("PersonelID",""))[:15]
            lb = QLabel(ad)
            lb.setStyleSheet("font-size:10px;padding:1px 3px;border-radius:2px;"
                             "background:rgba(0,180,216,0.15);color:#a8d4ef;")
            al.addWidget(lb)
        if len(nobetler) > 8:
            al.addWidget(QLabel(f"+{len(nobetler)-8}",
                                styleSheet="font-size:9px;color:#6a90b4;"))

    def mousePressEvent(self, e):
        self.tiklandi.emit(self.gun, self._nobetler)
        super().mousePressEvent(e)


class _BosHucre(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "_BosHucre{"
            "background:transparent;"
            "border:0px ;"
            "border-radius:0px;"
            "}"
        )


class NobetPlanPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role","page")
        self._db   = db
        self._yil  = date.today().year
        self._ay   = date.today().month
        self._birim_id  = ""
        self._birim_adi = ""
        self._onay_durumu  = "yok"
        self._plan_data:  list[dict]      = []
        self._p_map:      dict[str,str]   = {}
        self._v_map:      dict[str,dict]  = {}
        self._tatil:      set[str]        = set()
        self._dini:       set[str]        = set()
        self._eksik_slot_gunleri: set[str] = set()
        self._revizyon_gunleri: set[str] = set()
        self._hucreler:   dict[str,_Hucre]= {}
        self._secili_gun: Optional[date]  = None
        self._hazirlik_ok: bool           = False
        self._secili_satir: Optional[dict] = None
        self._build()

    def _svc(self): return get_nobet_service(self._db)

    # ── UI ────────────────────────────────────────────────────

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self._sol = self._build_sol()
        root.addWidget(self._sol, 0)
        root.addWidget(self._build_takvim(), 1)
        self._sag = self._build_sag()
        self._sag.setVisible(False)
        root.addWidget(self._sag, 0)

    def _build_sol(self) -> QFrame:
        p = QFrame(); p.setFixedWidth(260)
        p.setProperty("bg-role","panel")
        lay = QVBoxLayout(p); lay.setContentsMargins(12,16,12,16); lay.setSpacing(10)
        lbl_baslik = QLabel("Personel Nöbet Dağılımı")
        lbl_baslik.setProperty("style-role", "section-title")
        lay.addWidget(lbl_baslik)
        self._lbl_sol_ozet = QLabel("—")
        self._lbl_sol_ozet.setProperty("style-role","stat-label")
        self._lbl_sol_ozet.setProperty("color-role", "muted")
        lay.addWidget(self._lbl_sol_ozet)
        self._sol_sc = QScrollArea(); self._sol_sc.setWidgetResizable(True)
        self._sol_sc.setFrameShape(QFrame.Shape.NoFrame)
        self._sol_w = QWidget(); self._sol_l = QVBoxLayout(self._sol_w)
        self._sol_l.setContentsMargins(0,0,0,0); self._sol_l.setSpacing(4)
        self._sol_sc.setWidget(self._sol_w)
        lay.addWidget(self._sol_sc, 1)
        return p

    def _build_takvim(self) -> QWidget:
        w = QWidget(); wl = QVBoxLayout(w)
        wl.setContentsMargins(0,0,0,0); wl.setSpacing(0)
        hdr = QFrame(); hdr.setProperty("bg-role","elevated"); hdr.setFixedHeight(32)
        hl = QGridLayout(hdr); hl.setContentsMargins(8,0,8,0); hl.setSpacing(1)
        for i, g in enumerate(_GUN):
            lb = QLabel(g); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setStyleSheet(f"font-size:11px;font-weight:600;"
                             f"color:{'#e85555' if i>=5 else '#6a90b4'};")
            hl.addWidget(lb, 0, i)
        wl.addWidget(hdr)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        self._tw = QWidget(); self._tl = QGridLayout(self._tw)
        self._tl.setContentsMargins(0,0,0,0); self._tl.setSpacing(0)
        self._tl.setVerticalSpacing(0)
        for c in range(7): self._tl.setColumnStretch(c,1)
        sc.setWidget(self._tw); wl.addWidget(sc,1)
        return w

    def _build_sag(self) -> QFrame:
        p = QFrame(); p.setFixedWidth(360)
        p.setProperty("bg-role","panel")
        lay = QVBoxLayout(p); lay.setContentsMargins(14,16,14,16); lay.setSpacing(10)
        hdr = QHBoxLayout()
        lbl_hdr = QLabel("Plan Revizyonu")
        lbl_hdr.setProperty("style-role", "section-title")
        hdr.addWidget(lbl_hdr)
        hdr.addStretch()
        kapat = QPushButton(""); kapat.setFixedSize(24,24)
        kapat.setProperty("style-role","secondary")
        IconRenderer.set_button_icon(
            kapat, "x", color=IconColors.MUTED, size=12)
        kapat.clicked.connect(lambda: p.setVisible(False))
        hdr.addWidget(kapat); lay.addLayout(hdr)
        self._lbl_m_gun = QLabel("—")
        self._lbl_m_gun.setProperty("style-role","stat-label")
        self._lbl_m_gun.setProperty("color-role", "muted")
        lay.addWidget(self._lbl_m_gun)

        lbl_mevcut = QLabel("Mevcut Nöbetler")
        lbl_mevcut.setProperty("style-role", "section-title")
        lay.addWidget(lbl_mevcut)
        self._ms = QScrollArea(); self._ms.setWidgetResizable(True)
        self._ms.setFrameShape(QFrame.Shape.NoFrame); self._ms.setFixedHeight(250)
        self._ms.setProperty("bg-role", "elevated")
        self._mw = QWidget(); self._ml = QVBoxLayout(self._mw)
        self._ml.setContentsMargins(8,8,8,8); self._ml.setSpacing(6)
        self._ms.setWidget(self._mw); lay.addWidget(self._ms)

        self._btn_form_ac = QPushButton("Ekle")
        self._btn_form_ac.setProperty("style-role", "action")
        self._btn_form_ac.setFixedHeight(28)
        self._btn_form_ac.setVisible(False)
        self._btn_form_ac.clicked.connect(lambda: self._revizyon_alani_goster(True))
        lay.addWidget(self._btn_form_ac)

        lbl_secili = QLabel("Seçili Revizyon Kaydı")
        lbl_secili.setProperty("style-role", "section-title")
        lay.addWidget(lbl_secili)
        self._lbl_secili_satir = QLabel("Değiştirilecek kayıt seçilmedi")
        self._lbl_secili_satir.setProperty("color-role", "muted")
        self._lbl_secili_satir.setProperty("bg-role", "elevated")
        self._lbl_secili_satir.setContentsMargins(10, 8, 10, 8)
        self._lbl_secili_satir.setWordWrap(True)
        lay.addWidget(self._lbl_secili_satir)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); lay.addWidget(sep)

        form_hdr = QHBoxLayout()
        lbl_form = QLabel("Yeni Ekle / Revizyon")
        lbl_form.setProperty("style-role", "section-title")
        form_hdr.addWidget(lbl_form)
        form_hdr.addStretch()

        self._btn_form_toggle = QPushButton("Gizle")
        self._btn_form_toggle.setProperty("style-role", "secondary")
        self._btn_form_toggle.setFixedHeight(24)
        self._btn_form_toggle.clicked.connect(self._revizyon_alani_toggle)
        form_hdr.addWidget(self._btn_form_toggle)
        lay.addLayout(form_hdr)

        self._revizyon_form = QWidget()
        form_lay = QVBoxLayout(self._revizyon_form)
        form_lay.setContentsMargins(0, 0, 0, 0)
        form_lay.setSpacing(8)

        def _row(l, w):
            h = QHBoxLayout(); lb = QLabel(l); lb.setFixedWidth(65)
            lb.setProperty("style-role", "stat-label")
            lb.setProperty("color-role", "muted")
            h.addWidget(lb); h.addWidget(w); form_lay.addLayout(h); return w

        self._cmb_mv = _row("Vardiya:", QComboBox())
        self._cmb_mp = _row("Personel:", QComboBox())
        self._cmb_mp.setEditable(True)
        self._cmb_mp.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._cmb_mt = _row("Tür:", QComboBox())
        for t in ["normal","fazla_mesai"]: self._cmb_mt.addItem(t)

        self._txt_neden = _row("Neden:", QLineEdit())
        self._txt_neden.setPlaceholderText("Örn: Raporlu personel yerine değişim")

        self._btn_mekle = QPushButton("Yeni Ekle")
        self._btn_mekle.setProperty("style-role","action")
        self._btn_mekle.setFixedHeight(32)
        self._btn_mekle.clicked.connect(self._manuel_kaydet)

        self._btn_degistir = QPushButton("Nöbeti Değiştir")
        self._btn_degistir.setProperty("style-role","warning")
        self._btn_degistir.setFixedHeight(32)
        self._btn_degistir.clicked.connect(self._nobet_degistir)

        self._btn_secim_temizle = QPushButton("Seçimi Temizle")
        self._btn_secim_temizle.setProperty("style-role","secondary")
        self._btn_secim_temizle.setFixedHeight(30)
        self._btn_secim_temizle.clicked.connect(self._degisim_secimini_temizle)

        aksiyon = QHBoxLayout()
        aksiyon.setSpacing(8)
        aksiyon.addWidget(self._btn_mekle, 1)
        aksiyon.addWidget(self._btn_degistir, 1)
        form_lay.addLayout(aksiyon)
        form_lay.addWidget(self._btn_secim_temizle)

        lay.addWidget(self._revizyon_form)
        self._revizyon_alani_goster(False)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); lay.addWidget(sep2)
        self._btn_gecmis = QPushButton("Revizyon Geçmişi")
        self._btn_gecmis.setProperty("style-role", "secondary")
        self._btn_gecmis.setFixedHeight(30)
        self._btn_gecmis.clicked.connect(self._revizyon_gecmisi_goster)
        lay.addWidget(self._btn_gecmis)
        lay.addStretch()
        return p

    def _revizyon_alani_toggle(self):
        self._revizyon_alani_goster(not self._revizyon_form.isVisible())

    def _revizyon_alani_goster(self, gorunur: bool):
        self._revizyon_form.setVisible(gorunur)
        self._btn_form_toggle.setText("Gizle" if gorunur else "Göster")

    # ── Dışarıya Açık API ─────────────────────────────────────

    def yukle(self, birim_id: str, birim_adi: str, yil: int, ay: int):
        self._birim_id = birim_id; self._birim_adi = birim_adi
        self._yil = yil; self._ay = ay
        self._yukle_data()

    def get_onay_durumu(self) -> str:
        return self._onay_durumu

    def get_plan_data(self) -> list:
        return self._plan_data

    def hazirlik_onay_degisti(self, onaylandi: bool):
        self._hazirlik_ok = onaylandi

    # ── Veri ──────────────────────────────────────────────────

    def _yukle_data(self):
        if not self._birim_id:
            self._plan_data = []; self._onay_durumu = "yok"; self._ciz(); return
        try:
            svc = self._svc(); reg = svc._r
            try:
                self._v_map = {str(v["VardiyaID"]): dict(v)
                               for v in (reg.get("NB_Vardiya").get_all() or [])}
            except Exception: self._v_map = {}
            try:
                self._p_map = {str(p["KimlikNo"]): p.get("AdSoyad","")
                               for p in (reg.get("Personel").get_all() or [])}
            except Exception: self._p_map = {}
            try:
                t_rows = reg.get("Tatiller").get_all() or []
                ab = f"{self._yil:04d}-{self._ay:02d}-01"
                ae = f"{self._yil:04d}-{self._ay:02d}-31"
                self._tatil = {str(r.get("Tarih","")) for r in t_rows
                               if ab <= str(r.get("Tarih","")) <= ae
                               and r.get("TatilTuru") == "Resmi"}
                self._dini  = {str(r.get("Tarih","")) for r in t_rows
                               if ab <= str(r.get("Tarih","")) <= ae
                               and r.get("TatilTuru") == "DiniBayram"}
            except Exception: self._tatil = set(); self._dini = set()

            # Durum tutarlılığı için birim çözümünü metne bırakma; doğrudan BirimID kullan.
            sonuc = svc.get_plan(self._yil, self._ay, self._birim_id)
            self._plan_data = sonuc.veri or [] if sonuc.basarili else []
            for r in self._plan_data:
                if not r.get("AdSoyad"):
                    r["AdSoyad"] = self._p_map.get(str(r.get("PersonelID","")), "")
                if not r.get("VardiyaAdi"):
                    r["VardiyaAdi"] = self._v_map.get(
                        str(r.get("VardiyaID","")), {}).get("VardiyaAdi","")
            try:
                rows = (svc.onay_getir(self._yil, self._ay, self._birim_id).veri or [])
                self._onay_durumu = rows[0].get("Durum","yok") if rows else "yok"
            except Exception: self._onay_durumu = "yok"
            self._eksik_slot_gunleri = self._eksik_slot_gunlerini_hesapla(reg)
            self._revizyon_gunleri = self._revizyon_gunlerini_hesapla()
        except Exception as e:
            logger.error(f"plan._yukle_data: {e}")
            self._plan_data = []; self._onay_durumu = "yok"
            self._eksik_slot_gunleri = set()
            self._revizyon_gunleri = set()
        self._ciz()
        self._manuel_sec_yukle()
        self._sol_panel_guncelle()

    def _revizyon_gunlerini_hesapla(self) -> set[str]:
        if not self._birim_id:
            return set()
        try:
            plan = self._svc().plan.get_plan(self._birim_id, self._yil, self._ay)
            if not plan:
                return set()
            sonuc = self._svc().plan.get_satirlar(plan["PlanID"], sadece_aktif=False)
            if not sonuc.basarili:
                return set()

            revizyon_gunleri: set[str] = set()
            for satir in (sonuc.veri or []):
                tarih = str(satir.get("NobetTarihi", "")).strip()
                if not tarih:
                    continue
                if str(satir.get("Durum", "aktif")) != "aktif" or satir.get("OncekiSatirID"):
                    revizyon_gunleri.add(tarih)
            return revizyon_gunleri
        except Exception as e:
            logger.error(f"revizyon_gunlerini_hesapla: {e}")
            return set()

    def _eksik_slot_gunlerini_hesapla(self, reg) -> set[str]:
        if self._onay_durumu == "yok" and not self._plan_data:
            return set()

        try:
            ayar_rows = reg.get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in ayar_rows if str(r.get("BirimID", "")) == str(self._birim_id)),
                None,
            )
            slot_sayisi = int((ayar or {}).get("GunlukSlotSayisi", 4) or 4)
        except Exception:
            slot_sayisi = 4

        try:
            grup_rows = reg.get("NB_VardiyaGrubu").get_all() or []
            aktif_grup_idleri = {
                str(r.get("GrupID", ""))
                for r in grup_rows
                if str(r.get("BirimID", "")) == str(self._birim_id)
                and int(r.get("Aktif", 1))
            }
            v_rows = reg.get("NB_Vardiya").get_all() or []
            aktif_ana_vardiya_sayisi = sum(
                1 for v in v_rows
                if str(v.get("GrupID", "")) in aktif_grup_idleri
                and str(v.get("Rol", "ana")) == "ana"
                and int(v.get("Aktif", 1))
            )
        except Exception:
            aktif_ana_vardiya_sayisi = 0

        if slot_sayisi <= 0 or aktif_ana_vardiya_sayisi <= 0:
            return set()

        beklenen = slot_sayisi * aktif_ana_vardiya_sayisi
        if beklenen <= 0:
            return set()

        sayim: dict[str, int] = {}
        for n in self._plan_data:
            tarih = str(n.get("NobetTarihi", "")).strip()
            if tarih:
                sayim[tarih] = sayim.get(tarih, 0) + 1

        eksik: set[str] = set()
        ay_son = monthrange(self._yil, self._ay)[1]
        for gun_no in range(1, ay_son + 1):
            tarih = date(self._yil, self._ay, gun_no).isoformat()
            if tarih in self._dini:
                continue
            if sayim.get(tarih, 0) < beklenen:
                eksik.add(tarih)
        return eksik

    def _sol_panel_guncelle(self):
        while self._sol_l.count():
            w = self._sol_l.takeAt(0).widget()
            if w: w.deleteLater()

        if not self._birim_id:
            self._lbl_sol_ozet.setText("Birim seçin")
            self._sol_l.addWidget(QLabel("Personel listesi için birim seçin",
                styleSheet="color:#6a90b4;font-size:11px;"))
            self._sol_l.addStretch()
            return

        sayim: dict[str, int] = {}
        for n in self._plan_data:
            pid = str(n.get("PersonelID", "")).strip()
            if pid:
                sayim[pid] = sayim.get(pid, 0) + 1

        personeller: list[tuple[str, str]] = []
        try:
            p_rows = self._svc()._r.get("Personel").get_all() or []
            for p in sorted(p_rows, key=lambda x: x.get("AdSoyad", "")):
                if str(p.get("GorevYeri", "")).strip() == self._birim_adi:
                    pid = str(p.get("KimlikNo", ""))
                    ad = p.get("AdSoyad", "")
                    if pid:
                        personeller.append((pid, ad))
        except Exception as e:
            logger.error(f"sol_panel_personel: {e}")

        if not personeller and sayim:
            for pid, adet in sorted(sayim.items(), key=lambda x: x[1], reverse=True):
                personeller.append((pid, self._p_map.get(pid, pid)))

        toplam_nobet = sum(sayim.values())
        self._lbl_sol_ozet.setText(
            f"{len(personeller)} personel • {toplam_nobet} nöbet")

        if not personeller:
            self._sol_l.addWidget(QLabel("Personel bulunamadı",
                styleSheet="color:#6a90b4;font-size:11px;"))
            self._sol_l.addStretch()
            return

        for pid, ad in personeller:
            rw = QWidget(); rl = QHBoxLayout(rw)
            rl.setContentsMargins(0,0,0,0); rl.setSpacing(8)
            lb_ad = QLabel(ad or pid)
            lb_ad.setStyleSheet("font-size:11px;color:#cfe4f6;")
            lb_say = QLabel(str(sayim.get(pid, 0)))
            lb_say.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb_say.setMinimumWidth(28)
            lb_say.setStyleSheet(
                "font-size:11px;font-weight:600;color:#a8d4ef;"
                "padding:1px 6px;border-radius:8px;"
                "background:rgba(0,180,216,0.15);")
            rl.addWidget(lb_ad, 1); rl.addWidget(lb_say, 0)
            self._sol_l.addWidget(rw)
        self._sol_l.addStretch()

    # ── Takvim ────────────────────────────────────────────────

    def _ciz(self):
        while self._tl.count():
            item = self._tl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._hucreler.clear()
        if not self._birim_id:
            lbl = QLabel("Birim seçin")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color:#6b7280;font-size:14px;")
            self._tl.addWidget(lbl, 0, 0, 1, 7); return

        nobet_map: dict[str,list] = {}
        for n in self._plan_data:
            t = str(n.get("NobetTarihi",""))
            if t: nobet_map.setdefault(t,[]).append(n)

        ay_son = monthrange(self._yil, self._ay)[1]
        ilk_gun = date(self._yil, self._ay, 1)
        baslangic_kolon = ilk_gun.weekday()

        gun_no = 1
        for row in range(6):
            for col in range(7):
                hucre_index = row * 7 + col
                if hucre_index < baslangic_kolon or gun_no > ay_son:
                    self._tl.addWidget(_BosHucre(), row, col)
                    continue

                gun = date(self._yil, self._ay, gun_no)
                t = gun.isoformat()
                h = _Hucre(gun)
                h.guncelle(nobet_map.get(t,[]),
                           tatil=(t in self._tatil), dini=(t in self._dini),
                           secili=(gun == self._secili_gun),
                           eksik_slot=(t in self._eksik_slot_gunleri),
                           revizyon_var=(t in self._revizyon_gunleri))
                h.tiklandi.connect(self._gun_tiklandi)
                self._tl.addWidget(h, row, col)
                self._hucreler[t] = h
                gun_no += 1

    def _gun_tiklandi(self, gun: date, nobetler: list):
        self._secili_gun = gun
        self._secili_satir = None
        secili_tarih = gun.isoformat()
        for t, h in self._hucreler.items():
            h.guncelle([n for n in self._plan_data
                        if str(n.get("NobetTarihi","")) == t],
                       tatil=(t in self._tatil), dini=(t in self._dini),
                       secili=(h.gun == self._secili_gun),
                       eksik_slot=(t in self._eksik_slot_gunleri),
                       revizyon_var=(t in self._revizyon_gunleri))
        self._sag.setVisible(True)
        self._lbl_m_gun.setText(f"{gun.day} {_AY[gun.month]} {gun.year}")
        self._degisim_secimini_temizle()
        bos_veya_eksik = (len(nobetler) == 0) or (secili_tarih in self._eksik_slot_gunleri)
        self._btn_form_ac.setVisible(bos_veya_eksik)
        self._revizyon_alani_goster(False)
        while self._ml.count():
            w = self._ml.takeAt(0).widget()
            if w: w.deleteLater()
        for n in nobetler:
            ad = str(n.get("AdSoyad") or n.get("PersonelID",""))
            vas = n.get("VardiyaAdi",""); sid = str(n.get("SatirID",""))
            rw = QWidget(); rl = QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0)
            lb = QLabel(f"{ad}  {vas}"); lb.setStyleSheet("font-size:11px;")
            bd = QPushButton("");bd.setFixedSize(18,18)
            bd.setProperty("style-role", "secondary")
            IconRenderer.set_button_icon(
                bd, "edit", color=IconColors.DANGER, size=11)
            bd.clicked.connect(lambda _, satir=dict(n): self._degisim_sec(satir))
            bs = QPushButton(""); bs.setFixedSize(18,18)
            bs.setProperty("style-role","danger")
            IconRenderer.set_button_icon(
                bs, "x", color=IconColors.DANGER, size=11)
            bs.clicked.connect(lambda _,s=sid: self._nobet_sil(s))
            rl.addWidget(lb,1); rl.addWidget(bd); rl.addWidget(bs); self._ml.addWidget(rw)
        if not nobetler:
            self._ml.addWidget(QLabel("Nöbet yok",
                styleSheet="color:#6a90b4;font-size:11px;"))

    def _degisim_sec(self, satir: dict):
        self._secili_satir = dict(satir)
        self._revizyon_alani_goster(True)
        ad = str(satir.get("AdSoyad") or satir.get("PersonelID", ""))
        vardiya = str(satir.get("VardiyaAdi", ""))
        self._lbl_secili_satir.setText(
            f"Seçili kayıt: {ad} / {vardiya} değiştirilecek"
        )
        idx_v = self._cmb_mv.findData(satir.get("VardiyaID", ""))
        if idx_v >= 0:
            self._cmb_mv.setCurrentIndex(idx_v)

    def _degisim_secimini_temizle(self):
        self._secili_satir = None
        self._lbl_secili_satir.setText("Değiştirilecek kayıt seçilmedi")

    def _revizyon_gecmisi_goster(self):
        if not self._secili_gun:
            bilgi_goster(self, "Önce takvimden bir gün seçin.")
            return
        try:
            tarih = self._secili_gun.isoformat()
            sonuc = self._svc().gun_gecmisi_getir(
                self._yil, self._ay, self._birim_id, tarih)
            if not sonuc.basarili:
                hata_goster(self, str(sonuc.mesaj or sonuc.hata))
                return

            gecmis = [
                r for r in (sonuc.veri or [])
                if str(r.get("Durum", "")) != "aktif" or r.get("OncekiSatirID")
            ]
            if not gecmis:
                bilgi_goster(self, "Bu gün için revizyon geçmişi yok.")
                return

            satirlar = []
            for satir in gecmis:
                durum = str(satir.get("Durum", "aktif"))
                ad = str(satir.get("AdSoyad") or satir.get("PersonelID", ""))
                vardiya = str(satir.get("VardiyaAdi", ""))
                notlar = str(satir.get("Notlar", "") or "")
                metin = f"- {ad} | {vardiya} | {durum}"
                if notlar:
                    metin += f" | Not: {notlar}"
                satirlar.append(metin)

            bilgi_goster(self, "\n".join(satirlar))
        except Exception as e:
            logger.error(f"revizyon_gecmisi_goster: {e}")
            hata_goster(self, str(e))

    # ── Manuel Panel ──────────────────────────────────────────

    def _manuel_sec_yukle(self):
        self._cmb_mv.clear(); self._cmb_mp.clear()
        if not self._birim_id: return
        try:
            svc = self._svc()
            for v in (svc.get_vardiyalar(self._birim_id).veri or []):
                self._cmb_mv.addItem(
                    f"{v.get('VardiyaAdi','')} ({v.get('BasSaat','')}-{v.get('BitSaat','')})",
                    userData=v.get("VardiyaID",""))
            p_rows = svc._r.get("Personel").get_all() or []
            for p in sorted(p_rows, key=lambda x: x.get("AdSoyad","")):
                if str(p.get("GorevYeri","")).strip() == self._birim_adi:
                    self._cmb_mp.addItem(p.get("AdSoyad",""),
                                        userData=str(p["KimlikNo"]))
        except Exception as e: logger.error(f"manuel_sec_yukle: {e}")

    def _manuel_kaydet(self):
        if not self._secili_gun: return
        vid = self._cmb_mv.currentData(); pid = self._cmb_mp.currentData()
        if not all([self._birim_id, vid, pid]):
            uyari_goster(self, "Vardiya ve personel seçin.")
            return
        try:
            veri = {
                "BirimID": self._birim_id, "BirimAdi": self._birim_adi,
                "VardiyaID": vid, "PersonelID": pid,
                "NobetTarihi": self._secili_gun.isoformat(),
                "NobetTuru": self._cmb_mt.currentText(),
                "Notlar": self._txt_neden.text().strip(),
            }
            s = self._svc().plan_ekle(veri)
            if s.basarili:
                self._txt_neden.clear()
                self._yukle_data()
                return

            hata_msg = str(
                getattr(s, "mesaj", "")
                or getattr(s, "hata", "")
                or "İşlem gerçekleştirilemedi."
            )
            kisit_ihlali = (
                "yasak" in hata_msg.lower()
                or "izinli" in hata_msg.lower()
                or "çakış" in hata_msg.lower()
                or "cakis" in hata_msg.lower()
                or "üst üste" in hata_msg.lower()
                or "çift" in hata_msg.lower()
            )
            if kisit_ihlali:
                if soru_sor(self, f"{hata_msg}\n\nBu kısıtı atlayıp manuel nöbet yazılsın mı?"):
                    veri["KisitAtla"] = True
                    s2 = self._svc().plan_ekle(veri)
                    if s2.basarili:
                        self._txt_neden.clear()
                        self._yukle_data()
                        return
                    msg2 = str(
                        getattr(s2, "mesaj", "")
                        or getattr(s2, "hata", "")
                        or "İşlem gerçekleştirilemedi."
                    )
                    hata_goster(self, msg2)
                    return

            hata_goster(self, hata_msg)
        except Exception as e:
            hata_goster(self, str(e))

    def _nobet_degistir(self):
        if not self._secili_satir:
            uyari_goster(self, "Önce değiştirilecek nöbet kaydını seçin.")
            return
        yeni_pid = self._cmb_mp.currentData()
        if not yeni_pid:
            uyari_goster(self, "Yeni personeli seçin.")
            return
        if str(yeni_pid) == str(self._secili_satir.get("PersonelID", "")):
            uyari_goster(self, "Seçili nöbet zaten bu personele ait.")
            return
        try:
            sonuc = self._svc().plan_degistir(
                satir_id=str(self._secili_satir.get("SatirID", "")),
                yeni_personel_id=str(yeni_pid),
                neden=self._txt_neden.text().strip(),
            )
            if sonuc.basarili:
                self._txt_neden.clear()
                self._yukle_data()
                if self._secili_gun:
                    secili_tarih = self._secili_gun.isoformat()
                    gun_satirlari = [
                        n for n in self._plan_data
                        if str(n.get("NobetTarihi", "")) == secili_tarih
                    ]
                    self._gun_tiklandi(self._secili_gun, gun_satirlari)
                return
            hata_goster(self, str(sonuc.mesaj or sonuc.hata))
        except Exception as e:
            hata_goster(self, str(e))

    def _nobet_sil(self, satir_id: str):
        if not satir_id: return
        try:
            s = self._svc().plan_iptal(satir_id)
            if s.basarili: self._yukle_data()
            else: hata_goster(self, str(s.hata))
        except Exception as e: hata_goster(self, str(e))
