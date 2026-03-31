# -*- coding: utf-8 -*-
"""
nobet_merkez_page.py — Nöbet Merkezi (Entegre Tasarım)

Yapı:
  ┌─────────────────────────────────────────────────┐
  │  Toolbar: ‹ Ay › | Birim ▼ | PDF | Yenile       │
  │  Kapasite Bar: 9 kart (her zaman görünür)        │
  ├─────────────────────────────────────────────────┤
  │  ① Ön Hazırlık  ──→  ② Nöbet Planı             │
  │  [TAB İÇERİĞİ]                                   │
  ├─────────────────────────────────────────────────┤
  │  Alt Aksiyonlar (sekmeye göre değişir)           │
  └─────────────────────────────────────────────────┘

Akış:
    Hazırlık sekmesi → kontrol → "Hazırlığı Onayla"
    → Plan sekmesi aktif → "Otomatik Plan" → "Onayla"
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QStackedWidget, QProgressBar,
    QMessageBox,
)

from core.di import get_registry
from core.logger import logger
from ui.styles.icons import IconRenderer, IconColors

_AY = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

ONAY_DURUMLAR = {"Onaylandı","onaylandi","onaylı","approved"}


def _networkdays(bas: date, bit: date, tatiller: set) -> int:
    if bas > bit: return 0
    n, g = 0, bas
    while g <= bit:
        if g.weekday() < 5 and g.isoformat() not in tatiller: n += 1
        g += timedelta(days=1)
    return n


def _tatil_set(yil, ay, reg, tur=None) -> set:
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


# ══════════════════════════════════════════════════════════════
#  Otomatik Plan Thread (Plan sayfasından taşındı)
# ══════════════════════════════════════════════════════════════

class _OtoPlanThread(QThread):
    bitti  = Signal(object)
    hata   = Signal(str)

    def __init__(self, db, birim_id, yil, ay):
        super().__init__()
        self._db = db
        self._birim_id = birim_id
        self._yil = yil
        self._ay  = ay

    def run(self):
        try:
            from core.di import get_nobet_service
            svc   = get_nobet_service(self._db)
            sonuc = svc.otomatik_plan_olustur(
                self._yil, self._ay, self._birim_id)
            self.bitti.emit(sonuc)
        except Exception as e:
            self.hata.emit(str(e))


# ══════════════════════════════════════════════════════════════
#  Ana Merkez Sayfası
# ══════════════════════════════════════════════════════════════

class NobetMerkezPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._ag  = action_guard
        self._yil = date.today().year
        self._ay  = date.today().month
        self._birim_id  = ""
        self._birim_adi = ""
        self._hazirlik_onaylandi = False
        self._plan_onay_durumu   = "yok"   # taslak / onaylandi / yururlukte
        self.setProperty("bg-role","page")
        self._build()
        if db:
            self._birimleri_doldur()

    def _reg(self):
        return get_registry(self._db)

    # ──────────────────────────────────────────────────────────
    #  UI İnşası
    # ──────────────────────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        lay.addWidget(self._build_toolbar())
        lay.addWidget(self._build_kapasite_bar())
        lay.addWidget(self._build_adim_bar())

        # Tab içerikleri
        self._stack = QStackedWidget()
        from ui.pages.nobet.nobet_hazirlik_page import NobetHazirlikPage
        from ui.pages.nobet.nobet_plan_page      import NobetPlanPage

        self._hazirlik = NobetHazirlikPage(
            db=self._db, action_guard=self._ag, parent=self)

        self._plan = NobetPlanPage(
            db=self._db, action_guard=self._ag, parent=self)

        self._stack.addWidget(self._hazirlik)
        self._stack.addWidget(self._plan)
        lay.addWidget(self._stack, 1)

        lay.addWidget(self._build_alt_bar())

        # Bağlantılar
        # Hazırlık onay callback'i — sadece merkez yönetiyor
        # (alt sayfalar standalone API'leri olmadığı için bağlantı yok)

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
        self._lbl_ay.setFixedWidth(110)
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role","section-title")
        h.addWidget(self._lbl_ay)

        btn_i = QPushButton("›")
        btn_i.setFixedSize(28,28)
        btn_i.setProperty("style-role","secondary")
        btn_i.clicked.connect(self._ay_ileri)
        h.addWidget(btn_i)

        h.addSpacing(12)
        lbl_b = QLabel("Birim:")
        lbl_b.setProperty("color-role","muted")
        h.addWidget(lbl_b)

        self._cmb_birim = QComboBox()
        self._cmb_birim.setMinimumWidth(200)
        self._cmb_birim.currentIndexChanged.connect(self._on_birim)
        h.addWidget(self._cmb_birim)

        h.addStretch()

        self._btn_pdf = QPushButton("PDF")
        self._btn_pdf.setProperty("style-role","secondary")
        self._btn_pdf.setFixedHeight(28)
        IconRenderer.set_button_icon(
            self._btn_pdf, "file_pdf", color=IconColors.MUTED, size=14)
        self._btn_pdf.clicked.connect(self._pdf_al)
        h.addWidget(self._btn_pdf)

        btn_yenile = QPushButton("")
        btn_yenile.setFixedSize(28,28)
        btn_yenile.setProperty("style-role","secondary")
        IconRenderer.set_button_icon(
            btn_yenile, "refresh", color=IconColors.MUTED, size=14)
        btn_yenile.clicked.connect(self._yukle)
        h.addWidget(btn_yenile)
        return bar

    def _build_kapasite_bar(self) -> QFrame:
        """9 kartlık özet — her iki sekmede de görünür."""
        bar = QFrame()
        bar.setProperty("bg-role","panel")
        bar.setFixedHeight(74)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16,6,16,6)
        h.setSpacing(0)

        self._kartlar: dict[str,QLabel] = {}
        bilgiler = [
            ("toplam_gun",  "Toplam Gün",     "#4d9ee8"),
            ("is_gunu",     "İş Günü",         "#4d9ee8"),
            ("resmi_tatil", "Resmi Tatil",      "#6b7280"),
            ("dini_bayram", "Dini Bayram",      "#6b7280"),
            ("toplam_nobet","Toplam Nöbet",     "#2ec98e"),
            ("hedef_mesai", "Kişi Baş Hedef",  "#f59e0b"),
            ("izinli_kisi", "İzinli Personel", "#f59e0b"),
            ("fm_gonullu",  "FM Gönüllü",      "#4d9ee8"),
            ("uyari",       "Uyarı",            "#e85555"),
        ]
        for key, baslik, renk in bilgiler:
            f = QFrame()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(8,4,8,4)
            fl.setSpacing(1)
            v = QLabel("—")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(
                f"font-size:18px;font-weight:bold;color:{renk};")
            b = QLabel(baslik)
            b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setStyleSheet("font-size:9px;color:#6b7280;")
            fl.addWidget(v)
            fl.addWidget(b)
            self._kartlar[key] = v
            h.addWidget(f, 1)
            if key != "uyari":
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet("color:#2a3a4a;")
                h.addWidget(sep)
        return bar

    def _build_adim_bar(self) -> QFrame:
        """Workflow adım göstergesi + sekme navigasyonu."""
        bar = QFrame()
        bar.setProperty("bg-role","page")
        bar.setFixedHeight(38)
        h = QHBoxLayout(bar)
        h.setContentsMargins(0,0,0,0)
        h.setSpacing(0)

        self._btn_adim_hazirlik = QPushButton("  Ön Hazırlık  ")
        self._btn_adim_hazirlik.setCheckable(True)
        self._btn_adim_hazirlik.setChecked(True)
        self._btn_adim_hazirlik.setProperty("style-role","tab-active")
        self._btn_adim_hazirlik.setFixedHeight(38)
        IconRenderer.set_button_icon(
            self._btn_adim_hazirlik, "clipboard_list",
            color=IconColors.PRIMARY, size=14)
        self._btn_adim_hazirlik.clicked.connect(lambda: self._sekme_gec(0))
        h.addWidget(self._btn_adim_hazirlik)

        self._lbl_ok = QLabel("  →  ")
        self._lbl_ok.setStyleSheet("color:#3a5a7a;font-size:16px;")
        self._lbl_ok.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self._lbl_ok)

        self._btn_adim_plan = QPushButton("  Nöbet Planı  ")
        self._btn_adim_plan.setCheckable(True)
        self._btn_adim_plan.setChecked(False)
        self._btn_adim_plan.setProperty("style-role","tab")
        self._btn_adim_plan.setFixedHeight(38)
        IconRenderer.set_button_icon(
            self._btn_adim_plan, "calendar",
            color=IconColors.MUTED, size=14)
        self._btn_adim_plan.clicked.connect(lambda: self._sekme_gec(1))
        h.addWidget(self._btn_adim_plan)

        h.addStretch()

        # Hazırlık onay durumu göstergesi
        self._lbl_hazirlik_durum = QLabel("Hazırlık onaylanmadı")
        self._lbl_hazirlik_durum.setStyleSheet(
            "font-size:11px;color:#e85555;padding:0 16px;")
        h.addWidget(self._lbl_hazirlik_durum)

        # Plan onay durumu göstergesi
        self._lbl_plan_durum = QLabel("")
        self._lbl_plan_durum.setStyleSheet(
            "font-size:11px;color:#6b7280;padding:0 8px;")
        h.addWidget(self._lbl_plan_durum)
        return bar

    def _build_alt_bar(self) -> QFrame:
        """Alt aksiyonlar — aktif sekmeye göre butonlar değişir."""
        bar = QFrame()
        bar.setProperty("bg-role","panel")
        bar.setFixedHeight(44)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16,0,16,0)
        h.setSpacing(8)

        # ── Hazırlık aksiyonları ──
        self._frm_hazirlik_aks = QFrame()
        hh = QHBoxLayout(self._frm_hazirlik_aks)
        hh.setContentsMargins(0,0,0,0)
        hh.setSpacing(8)

        self._btn_hazirlik_onayla = QPushButton("Hazırlığı Onayla")
        self._btn_hazirlik_onayla.setProperty("style-role","action")
        self._btn_hazirlik_onayla.setFixedHeight(32)
        self._btn_hazirlik_onayla.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_hazirlik_onayla, "check_circle",
            color=IconColors.PRIMARY, size=14)
        self._btn_hazirlik_onayla.clicked.connect(self._hazirlik_onayla)
        hh.addWidget(self._btn_hazirlik_onayla)

        self._btn_hazirlik_iptal = QPushButton("Onayı Geri Al")
        self._btn_hazirlik_iptal.setProperty("style-role","danger")
        self._btn_hazirlik_iptal.setFixedHeight(32)
        self._btn_hazirlik_iptal.setVisible(False)
        self._btn_hazirlik_iptal.clicked.connect(self._hazirlik_iptal)
        hh.addWidget(self._btn_hazirlik_iptal)

        h.addWidget(self._frm_hazirlik_aks)

        # ── Plan aksiyonları ──
        self._frm_plan_aks = QFrame()
        ph = QHBoxLayout(self._frm_plan_aks)
        ph.setContentsMargins(0,0,0,0)
        ph.setSpacing(8)

        self._btn_oto = QPushButton("Otomatik Plan")
        self._btn_oto.setProperty("style-role","action")
        self._btn_oto.setFixedHeight(32)
        self._btn_oto.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_oto, "bolt", color=IconColors.PRIMARY, size=14)
        self._btn_oto.setToolTip("Önce 'Ön Hazırlık' onaylanmalıdır")
        self._btn_oto.clicked.connect(self._oto_plan)
        ph.addWidget(self._btn_oto)

        self._btn_temizle = QPushButton("Taslağı Temizle")
        self._btn_temizle.setProperty("style-role","danger")
        self._btn_temizle.setFixedHeight(32)
        self._btn_temizle.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_temizle, "x", color=IconColors.DANGER, size=14)
        self._btn_temizle.clicked.connect(self._taslak_temizle)
        ph.addWidget(self._btn_temizle)

        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setRange(0,0)
        self._pbar.setVisible(False)
        ph.addWidget(self._pbar)

        self._btn_onayla = QPushButton("Onayla")
        self._btn_onayla.setProperty("style-role","action")
        self._btn_onayla.setFixedHeight(32)
        self._btn_onayla.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_onayla, "check", color=IconColors.PRIMARY, size=14)
        self._btn_onayla.clicked.connect(self._plan_onayla)
        ph.addWidget(self._btn_onayla)

        self._btn_ogeri = QPushButton("Onayı Geri Al")
        self._btn_ogeri.setProperty("style-role","secondary")
        self._btn_ogeri.setFixedHeight(32)
        self._btn_ogeri.setVisible(False)
        self._btn_ogeri.clicked.connect(self._plan_onay_geri)
        ph.addWidget(self._btn_ogeri)

        h.addWidget(self._frm_plan_aks)
        self._frm_plan_aks.setVisible(False)

        h.addStretch()

        return bar

    # ──────────────────────────────────────────────────────────
    #  Navigasyon
    # ──────────────────────────────────────────────────────────

    def _ay_geri(self):
        if self._ay == 1: self._ay, self._yil = 12, self._yil-1
        else: self._ay -= 1
        self._sync_donem()

    def _ay_ileri(self):
        if self._ay == 12: self._ay, self._yil = 1, self._yil+1
        else: self._ay += 1
        self._sync_donem()

    def _on_birim(self):
        self._birim_id  = self._cmb_birim.currentData() or ""
        self._birim_adi = self._cmb_birim.currentText() or ""
        self._sync_donem()

    def _sekme_gec(self, idx: int):
        self._stack.setCurrentIndex(idx)
        aktif0 = idx == 0
        self._btn_adim_hazirlik.setChecked(aktif0)
        self._btn_adim_plan.setChecked(not aktif0)
        self._frm_hazirlik_aks.setVisible(aktif0)
        self._frm_plan_aks.setVisible(not aktif0)
        self._btn_pdf.setVisible(aktif0)

    # ──────────────────────────────────────────────────────────
    #  Veri Senkronizasyonu
    # ──────────────────────────────────────────────────────────

    def _birimleri_doldur(self):
        try:
            rows = sorted(
                self._reg().get("NB_Birim").get_all() or [],
                key=lambda r: r.get("BirimAdi",""))
            self._cmb_birim.blockSignals(True)
            self._cmb_birim.clear()
            for r in rows:
                self._cmb_birim.addItem(r.get("BirimAdi",""),
                                        userData=r["BirimID"])
            self._cmb_birim.blockSignals(False)
            if self._cmb_birim.count() > 0:
                self._cmb_birim.setCurrentIndex(0)
                self._on_birim()
        except Exception as e:
            logger.error(f"birimleri_doldur: {e}")

    def _sync_donem(self):
        """Birim/ay değişince tüm alt bileşenleri güncelle."""
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")

        # Hazırlık sayfası — merkez modu olduğu için combobox yok,
        # state'i doğrudan ata
        self._hazirlik._birim_id  = self._birim_id
        self._hazirlik._birim_adi = self._birim_adi
        self._hazirlik._yil       = self._yil
        self._hazirlik._ay        = self._ay

        # Plan sayfası — merkez modu olduğu için sol panel/cmb yok
        self._plan._birim_id  = self._birim_id
        self._plan._birim_adi = self._birim_adi
        self._plan._yil       = self._yil
        self._plan._ay        = self._ay

        self._yukle()

    def _yukle(self):
        if not self._birim_id:
            return
        try:
            self._yukle_kapasite()
        except Exception as e:
            logger.error(f"_yukle_kapasite: {e}")
        try:
            self._hazirlik.yukle(
                self._birim_id, self._birim_adi, self._yil, self._ay)
        except Exception as e:
            logger.error(f"hazirlik.yukle: {e}")
        try:
            self._plan.yukle(
                self._birim_id, self._birim_adi, self._yil, self._ay)
        except Exception as e:
            logger.error(f"plan._yukle: {e}")
        try:
            self._hazirlik_durum_guncelle()
        except Exception as e:
            logger.error(f"_hazirlik_durum_guncelle: {e}")
        try:
            self._plan_durum_guncelle()
        except Exception as e:
            logger.error(f"_plan_durum_guncelle: {e}")

    def _yukle_kapasite(self):
        """Kapasite barını DB'den hesapla ve güncelle."""
        try:
            reg    = self._reg()
            tatil  = _tatil_set(self._yil, self._ay, reg)
            resmi  = _tatil_set(self._yil, self._ay, reg, "Resmi")
            dini   = _tatil_set(self._yil, self._ay, reg, "DiniBayram")
            ay_son = monthrange(self._yil, self._ay)[1]
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay, ay_son)
            is_gun = _networkdays(ay_bas, ay_bit, tatil)

            # Slot ve vardiya
            slot, ana_v = 4, 2
            a_rows = reg.get("NB_BirimAyar").get_all() or []
            ayar   = next((r for r in a_rows
                           if str(r.get("BirimID",""))==self._birim_id), {})
            slot   = int(ayar.get("GunlukSlotSayisi", 4))
            g_rows = reg.get("NB_VardiyaGrubu").get_all() or []
            v_rows = reg.get("NB_Vardiya").get_all() or []
            gids   = {str(g["GrupID"]) for g in g_rows
                      if str(g.get("BirimID","")) == self._birim_id
                      and int(g.get("Aktif",1))}
            v_count = sum(1 for v in v_rows
                          if str(v.get("GrupID","")) in gids
                          and str(v.get("Rol","ana")) == "ana"
                          and int(v.get("Aktif",1)))
            if v_count > 0: ana_v = v_count

            aktif_gun    = ay_son - len(dini)
            toplam_nobet = aktif_gun * slot * ana_v
            is_gun_hedef = is_gun * 7

            # Personel
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            pids  = [str(r.get("PersonelID","")) for r in bp
                     if str(r.get("BirimID","")) == self._birim_id
                     and int(r.get("Aktif",1))]
            iz_rows = reg.get("Izin_Giris").get_all() or []
            izinli  = sum(1 for pid in pids
                          if any(str(r.get("Personelid","")).strip()==pid
                                 and str(r.get("Durum","")).strip() in ONAY_DURUMLAR
                                 and self._ayda_izinli(r)
                                 for r in iz_rows))
            t_rows  = reg.get("NB_PersonelTercih").get_all() or []
            fm_sayi = sum(1 for pid in pids
                          if any(str(r.get("PersonelID",""))==pid
                                 and str(r.get("BirimID",""))==self._birim_id
                                 and int(r.get("Yil",0))==self._yil
                                 and int(r.get("Ay",0))==self._ay
                                 and str(r.get("NobetTercihi",""))=="fazla_mesai_gonullu"
                                 for r in t_rows))

            self._kartlar["toplam_gun"].setText(str(ay_son))
            self._kartlar["is_gunu"].setText(str(is_gun))
            self._kartlar["resmi_tatil"].setText(str(len(resmi)))
            self._kartlar["dini_bayram"].setText(str(len(dini)))
            self._kartlar["toplam_nobet"].setText(str(toplam_nobet))
            self._kartlar["hedef_mesai"].setText(f"{is_gun_hedef:.0f} s")
            self._kartlar["izinli_kisi"].setText(str(izinli))
            self._kartlar["izinli_kisi"].setStyleSheet(
                f"font-size:18px;font-weight:bold;"
                f"color:{'#f59e0b' if izinli > 0 else '#6b7280'};")
            self._kartlar["fm_gonullu"].setText(str(fm_sayi))
        except Exception as e:
            logger.error(f"_yukle_kapasite: {e}")

    def _ayda_izinli(self, izin_row: dict) -> bool:
        try:
            ay_bas = date(self._yil, self._ay, 1)
            ay_bit = date(self._yil, self._ay,
                          monthrange(self._yil, self._ay)[1])
            bas = date.fromisoformat(str(izin_row.get("BaslamaTarihi","")))
            bit = date.fromisoformat(str(izin_row.get("BitisTarihi","")))
            return max(bas, ay_bas) <= min(bit, ay_bit)
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────
    #  Durum Göstergeleri
    # ──────────────────────────────────────────────────────────

    def _hazirlik_durum_guncelle(self):
        try:
            reg   = self._reg()
            rows  = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay), None)
            onaylandi = bool(kayit)
            self._hazirlik_onaylandi = onaylandi

            if onaylandi:
                tarih = str(kayit.get("OnayTarihi",""))[:10]
                self._lbl_hazirlik_durum.setText(f"Hazırlık onaylandı ({tarih})")
                self._lbl_hazirlik_durum.setStyleSheet(
                    "font-size:11px;color:#2ec98e;padding:0 16px;")
                self._btn_adim_plan.setText("  Nöbet Planı  ")
                IconRenderer.set_button_icon(
                    self._btn_adim_plan, "calendar",
                    color=IconColors.MUTED, size=14)
                self._btn_hazirlik_onayla.setEnabled(False)
                self._btn_hazirlik_onayla.setText("Onaylandı")
                self._btn_hazirlik_iptal.setVisible(True)
            else:
                self._lbl_hazirlik_durum.setText("Hazırlık onaylanmadı")
                self._lbl_hazirlik_durum.setStyleSheet(
                    "font-size:11px;color:#e85555;padding:0 16px;")
                self._btn_adim_plan.setText("  Nöbet Planı  ")
                IconRenderer.set_button_icon(
                    self._btn_adim_plan, "lock",
                    color=IconColors.MUTED, size=14)
                self._btn_hazirlik_onayla.setEnabled(bool(self._birim_id))
                self._btn_hazirlik_onayla.setText("Hazırlığı Onayla")
                self._btn_hazirlik_iptal.setVisible(False)

        except Exception as e:
            logger.error(f"_hazirlik_durum_guncelle: {e}")
            # Tablo yoksa (migration bekliyor) → butonu yine de aktif et
            self._hazirlik_onaylandi = False
            self._lbl_hazirlik_durum.setText("Hazırlık onaylanmadı")
            self._lbl_hazirlik_durum.setStyleSheet(
                "font-size:11px;color:#e85555;padding:0 16px;")
            self._btn_adim_plan.setText("  Nöbet Planı  ")
            IconRenderer.set_button_icon(
                self._btn_adim_plan, "lock",
                color=IconColors.MUTED, size=14)
            self._btn_hazirlik_onayla.setEnabled(bool(self._birim_id))
            self._btn_hazirlik_onayla.setText("Hazırlığı Onayla")
            self._btn_hazirlik_iptal.setVisible(False)

        self._oto_durum_guncelle()

    def _plan_durum_guncelle(self):
        try:
            self._plan_onay_durumu = self._plan.get_onay_durumu()
        except Exception:
            self._plan_onay_durumu = "yok"

        revizyon_modu = self._plan_revizyonda_mi()

        d = {
            "yok":        ("",              ""),
            "taslak":     ("Taslak",        "#f59e0b"),
            "onaylandi":  ("Plan Onaylı",   "#2ec98e"),
            "yururlukte": ("Yürürlükte",    "#2ec98e"),
        }
        metin, renk = d.get(self._plan_onay_durumu, ("",""))
        if revizyon_modu:
            metin, renk = ("Revizyon Modu", "#f59e0b")
        self._lbl_plan_durum.setText(metin)
        self._lbl_plan_durum.setStyleSheet(
            f"font-size:11px;color:{renk};padding:0 8px;" if renk else "")

        durum_norm = str(self._plan_onay_durumu or "").strip().lower()
        onaylanmis = durum_norm in ("onaylandi", "onaylandı", "onaylı", "yururlukte", "yürürlükte")
        plan_var   = bool(self._plan.get_plan_data())
        taslak_var = (durum_norm == "taslak") or (plan_var and not onaylanmis)
        self._btn_onayla.setEnabled(
            taslak_var and plan_var)
        self._btn_ogeri.setVisible(onaylanmis)
        self._btn_temizle.setEnabled(
            taslak_var and not revizyon_modu)
        self._btn_temizle.setToolTip(
            ""
            if self._btn_temizle.isEnabled()
            else ("Revizyon modunda taslak temizleme kapalı"
                  if revizyon_modu
                  else "Temizlenecek taslak plan bulunamadı")
        )
        self._oto_durum_guncelle()

    def _oto_durum_guncelle(self):
        durum_norm = str(self._plan_onay_durumu or "").strip().lower()
        onaylanmis = durum_norm in ("onaylandi", "onaylandı", "onaylı", "yururlukte", "yürürlükte")
        revizyon_modu = self._plan_revizyonda_mi()
        aktif = self._hazirlik_onaylandi and not onaylanmis and not revizyon_modu
        self._btn_oto.setEnabled(aktif)
        self._btn_oto.setToolTip(
            "" if aktif
            else ("Revizyon modunda otomatik plan kapalı"
                  if revizyon_modu
                  else "Önce 'Ön Hazırlık' onaylanmalıdır"
                  if not self._hazirlik_onaylandi
                  else "Plan onaylı, değiştirilemez"))
        # Uyarı kartı güncelle
        uyari = 0
        if not self._hazirlik_onaylandi and self._birim_id:
            uyari += 1
        self._kartlar["uyari"].setText(str(uyari) if uyari else "0")
        self._kartlar["uyari"].setStyleSheet(
            f"font-size:18px;font-weight:bold;"
            f"color:{'#e85555' if uyari > 0 else '#2ec98e'};")

    def _plan_revizyonda_mi(self) -> bool:
        if not self._birim_id:
            return False
        try:
            svc = self._plan._svc()
            plan = svc.plan.get_plan(self._birim_id, self._yil, self._ay)
            if not plan:
                return False
            notlar = str(plan.get("Notlar", "") or "")
            return (
                str(plan.get("Durum", "")) == "taslak"
                and "[REVIZYON_MODU]" in notlar
            )
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────
    #  Hazırlık Onay Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _hazirlik_onay_degisti(self, birim_id, yil, ay, onaylandi):
        """Dahili kullanım — onayla/iptal metodlarından çağrılır."""
        if birim_id == self._birim_id and yil == self._yil and ay == self._ay:
            self._hazirlik_onaylandi = onaylandi
            self._plan.hazirlik_onay_degisti(onaylandi)
            self._hazirlik_durum_guncelle()
            if onaylandi:
                self._sekme_gec(1)

    def _hazirlik_onayla(self):
        if not self._birim_id:
            return
        try:
            reg   = self._reg()
            simdi = datetime.now().isoformat(sep=" ", timespec="seconds")

            # NB_HazirlikOnay tablosu kontrolü (migration ana girişte yapılır)
            rows = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay), None)
            if kayit:
                reg.get("NB_HazirlikOnay").update(
                    kayit["OnayID"],
                    {"Durum":"onaylandi","OnayTarihi":simdi})
            else:
                reg.get("NB_HazirlikOnay").insert({
                    "OnayID":     str(uuid.uuid4()),
                    "BirimID":    self._birim_id,
                    "Yil":        self._yil,
                    "Ay":         self._ay,
                    "Durum":      "onaylandi",
                    "OnayTarihi": simdi,
                    "created_at": simdi,
                })
            self._hazirlik_onaylandi = True
            self._plan.hazirlik_onay_degisti(True)
            self._hazirlik_durum_guncelle()
            self._sekme_gec(1)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _hazirlik_iptal(self):
        cevap = QMessageBox.question(
            self, "Hazırlık Onayı Geri Al",
            "Hazırlık onayı geri alınacak.\n"
            "Otomatik Plan butonu kilitlenecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes:
            return
        try:
            reg  = self._reg()
            rows = reg.get("NB_HazirlikOnay").get_all() or []
            kayit = next(
                (r for r in rows
                 if str(r.get("BirimID","")) == self._birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay), None)
            if kayit:
                reg.get("NB_HazirlikOnay").delete(kayit["OnayID"])
            self._hazirlik_onaylandi = False
            self._plan.hazirlik_onay_degisti(False)
            self._hazirlik_durum_guncelle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  Plan Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _oto_plan(self):
        if not self._hazirlik_onaylandi:
            QMessageBox.warning(self, "Uyarı",
                "Önce 'Ön Hazırlık' onaylanmalıdır.")
            self._sekme_gec(0)
            return
        cevap = QMessageBox.question(
            self, "Otomatik Plan",
            f"{_AY[self._ay]} {self._yil} için otomatik plan oluşturulacak.\n"
            "Mevcut taslak silinecek. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes:
            return
        self._btn_oto.setEnabled(False)
        self._pbar.setVisible(True)
        self._thread = _OtoPlanThread(
            self._db, self._birim_id, self._yil, self._ay)
        self._thread.bitti.connect(self._oto_plan_bitti)
        self._thread.hata.connect(self._oto_plan_hata)
        self._thread.start()

    def _oto_plan_bitti(self, sonuc):
        self._pbar.setVisible(False)
        if sonuc.basarili:
            self._yukle()
        else:
            QMessageBox.critical(self, "Hata", sonuc.mesaj)
            self._oto_durum_guncelle()

    def _oto_plan_hata(self, msg: str):
        self._pbar.setVisible(False)
        QMessageBox.critical(self, "Hata", msg)
        self._oto_durum_guncelle()

    def _taslak_temizle(self):
        if QMessageBox.question(
            self, "Taslağı Temizle",
            "Tüm taslak satırlar silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            svc   = self._plan._svc()
            sonuc = svc.plan.taslak_temizle(
                self._birim_id, self._yil, self._ay)
            if sonuc.basarili:
                self._yukle()
                QMessageBox.information(self, "Bilgi", sonuc.mesaj or "Taslak temizleme tamamlandı.")
            else:
                QMessageBox.critical(self, "Hata", sonuc.mesaj)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _plan_onayla(self):
        try:
            svc   = self._plan._svc()
            sonuc = svc.plan.onayla(
                self._birim_id, self._yil, self._ay,
                onaylayan_id="")
            if sonuc.basarili:
                self._yukle()
                QMessageBox.information(self, "Onaylandı", sonuc.mesaj)
            else:
                QMessageBox.critical(self, "Hata", sonuc.mesaj)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _plan_onay_geri(self):
        if QMessageBox.question(
            self, "Onayı Geri Al",
            "Plan taslak durumuna alınacak, mevcut nöbet satırları korunacak.\n"
            "Bu mod sadece manuel revizyon içindir; otomatik plan ve taslak temizleme kapatılacak.\n"
            "Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            svc   = self._plan._svc()
            sonuc = svc.plan.onay_geri_al(
                self._birim_id, self._yil, self._ay)
            if sonuc.basarili:
                self._yukle()
                QMessageBox.information(self, "Revizyon Modu", sonuc.mesaj)
            else:
                QMessageBox.critical(self, "Hata", sonuc.mesaj)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  PDF
    # ──────────────────────────────────────────────────────────

    def _pdf_al(self):
        self._hazirlik._pdf_al()

    # ──────────────────────────────────────────────────────────
    #  Dış Çağrı
    # ──────────────────────────────────────────────────────────

    def load_data(self):
        if self._db:
            self._birimleri_doldur()
