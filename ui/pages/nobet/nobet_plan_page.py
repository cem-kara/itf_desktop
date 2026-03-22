# -*- coding: utf-8 -*-
"""
Nöbet Plan Sayfası — Takvim görünümü + otomatik planlama.
Sol: filtreler + otomatik plan butonu
Orta: aylık takvim grid
Sağ: seçili güne atama paneli
"""
from __future__ import annotations
import calendar
from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, QDate, Signal, QTimer
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QScrollArea, QGridLayout,
    QGroupBox, QSpinBox, QProgressBar, QSizePolicy,
    QTextEdit,
)

from core.di import get_nobet_service
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor
from ui.styles.icons import IconRenderer, IconColors

_GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
_AY_ADLARI  = ["", "Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
               "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]


class _GunHucresi(QFrame):
    """Takvim gün hücresi — üstüne tıklayınca sinyal emit eder."""
    tiklandi = Signal(date, list)  # tarih, o güne atanan nöbetler

    def __init__(self, gun: Optional[date] = None, parent=None):
        super().__init__(parent)
        self._gun     = gun
        self._nobetler: list[dict] = []
        self.setFixedHeight(80)
        self.setProperty("bg-role", "page")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        self.lbl_gun = QLabel("")
        self.lbl_gun.setProperty("style-role", "stat-label")
        lay.addWidget(self.lbl_gun)

        self.lbl_icerik = QLabel("")
        self.lbl_icerik.setWordWrap(True)
        self.lbl_icerik.setProperty("color-role", "muted")
        self.lbl_icerik.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.lbl_icerik, 1)

        if gun:
            self.lbl_gun.setText(str(gun.day))
            if gun.weekday() >= 5:
                self.lbl_gun.setProperty("color-role", "warn")
            else:
                self.lbl_gun.setProperty("color-role", "primary")
        else:
            self.setProperty("bg-role", "elevated")

    def set_nobetler(self, nobetler: list[dict], personel_map: dict):
        self._nobetler = nobetler
        if not nobetler:
            self.lbl_icerik.setText("")
            return
        satirlar = []
        for n in nobetler[:3]:
            pid = n.get("PersonelID", "")
            ad  = personel_map.get(pid, pid)
            # Ad soyadın kısaltması
            parcalar = ad.split()
            kisa = (parcalar[0] + " " + parcalar[-1][0] + "."
                    if len(parcalar) > 1 else ad)
            satirlar.append(kisa)
        if len(nobetler) > 3:
            satirlar.append(f"+{len(nobetler)-3} daha")
        self.lbl_icerik.setText("\n".join(satirlar))

    def set_secili(self, secili: bool):
        self.setProperty("bg-role", "elevated" if secili else "page")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if self._gun:
            self.tiklandi.emit(self._gun, self._nobetler)
        super().mousePressEvent(event)


class NobetPlanPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db           = db
        self._action_guard = action_guard
        self._yil          = date.today().year
        self._ay           = date.today().month
        self._secili_gun:  Optional[date] = None
        self._plan_data:   list[dict] = []
        self._personel_map: dict[str, str] = {}  # id → AdSoyad
        self._hucreler:    dict[date, _GunHucresi] = {}
        self._setup_ui()
        if db:
            self.load_data()

    # ─── UI ──────────────────────────────────────────────

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sol_panel(), 0)
        root.addWidget(self._build_takvim_alani(), 1)
        # Sağdan açılan manuel nöbet paneli
        self._manuel_panel = self._build_manuel_panel()
        root.addWidget(self._manuel_panel, 0)

    # ── Sol Panel (kontroller) ──

    def _build_sol_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(220)
        panel.setProperty("bg-role", "panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(12)

        # Ay/Yıl navigasyonu
        grp_nav = QGroupBox("Dönem")
        grp_nav.setProperty("style-role", "group")
        nl = QVBoxLayout(grp_nav)
        nl.setContentsMargins(8, 6, 8, 10)
        nl.setSpacing(6)

        nav_row = QHBoxLayout()
        self.btn_prev = QPushButton("‹")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_prev.setProperty("style-role", "secondary")
        self.btn_prev.clicked.connect(self._prev_ay)
        nav_row.addWidget(self.btn_prev)

        self.lbl_ay = QLabel()
        self.lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ay.setProperty("style-role", "section-title")
        self.lbl_ay.setProperty("color-role", "primary")
        nav_row.addWidget(self.lbl_ay, 1)

        self.btn_next = QPushButton("›")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_next.setProperty("style-role", "secondary")
        self.btn_next.clicked.connect(self._next_ay)
        nav_row.addWidget(self.btn_next)
        nl.addLayout(nav_row)
        lay.addWidget(grp_nav)

        # Birim filtresi
        grp_birim = QGroupBox("Birim")
        grp_birim.setProperty("style-role", "group")
        bl = QVBoxLayout(grp_birim)
        bl.setContentsMargins(8, 6, 8, 10)
        bl.setSpacing(6)
        self.cmb_birim = QComboBox()
        self.cmb_birim.addItem("Tüm Birimler", userData=None)
        self.cmb_birim.currentIndexChanged.connect(self._filtrele_ve_goster)
        bl.addWidget(self.cmb_birim)
        lay.addWidget(grp_birim)

        # Otomatik planlama
        grp_oto = QGroupBox("Otomatik Planlama")
        grp_oto.setProperty("style-role", "group")
        ol = QVBoxLayout(grp_oto)
        ol.setContentsMargins(8, 6, 8, 10)
        ol.setSpacing(6)

        lbl_saat = QLabel("Aylık max saat:")
        lbl_saat.setProperty("color-role", "muted")
        ol.addWidget(lbl_saat)

        self.spn_max_saat = QSpinBox()
        self.spn_max_saat.setRange(50, 400)
        self.spn_max_saat.setValue(225)
        self.spn_max_saat.setSuffix(" saat")
        self.spn_max_saat.setToolTip(
            "Aylık iş günü × 7.5 saat olarak otomatik hesaplanır.\n"
            "İstersen elle de değiştirebilirsin."
        )
        ol.addWidget(self.spn_max_saat)

        self.lbl_is_gunu = QLabel("")
        self.lbl_is_gunu.setProperty("color-role", "muted")
        self.lbl_is_gunu.setProperty("style-role", "stat-label")
        ol.addWidget(self.lbl_is_gunu)

        self.btn_taslak_temizle = QPushButton("Taslakları Temizle")
        self.btn_taslak_temizle.setProperty("style-role", "danger")
        self.btn_taslak_temizle.setFixedHeight(28)
        self.btn_taslak_temizle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_taslak_temizle.clicked.connect(self._taslak_temizle)
        ol.addWidget(self.btn_taslak_temizle)

        self.btn_oto_plan = QPushButton(" Taslak Oluştur")
        self.btn_oto_plan.setProperty("style-role", "action")
        self.btn_oto_plan.setFixedHeight(32)
        self.btn_oto_plan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_oto_plan, "magic",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_oto_plan.clicked.connect(self._oto_plan_olustur)
        ol.addWidget(self.btn_oto_plan)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(3)
        self.pbar.setVisible(False)
        self.pbar.setRange(0, 0)
        ol.addWidget(self.pbar)
        lay.addWidget(grp_oto)

        # Onay
        grp_onay = QGroupBox("Onay")
        grp_onay.setProperty("style-role", "group")
        oy = QVBoxLayout(grp_onay)
        oy.setContentsMargins(8, 6, 8, 10)
        oy.setSpacing(6)
        self.lbl_onay_durum = QLabel("—")
        self.lbl_onay_durum.setProperty("color-role", "muted")
        oy.addWidget(self.lbl_onay_durum)
        self.btn_onayla = QPushButton(" Planı Onayla")
        self.btn_onayla.setProperty("style-role", "action")
        self.btn_onayla.setFixedHeight(28)
        self.btn_onayla.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_onayla, "check",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_onayla.clicked.connect(self._onayla)
        oy.addWidget(self.btn_onayla)
        lay.addWidget(grp_onay)

        lay.addStretch()

        # Seçili güne manuel nöbet ekle
        grp_manuel = QGroupBox("Manuel Nöbet")
        grp_manuel.setProperty("style-role", "group")
        ml = QVBoxLayout(grp_manuel)
        ml.setContentsMargins(8, 6, 8, 10)
        ml.setSpacing(4)
        self.lbl_secili_gun = QLabel("Takvimden gün seçin")
        self.lbl_secili_gun.setProperty("color-role", "muted")
        self.lbl_secili_gun.setProperty("style-role", "stat-label")
        self.lbl_secili_gun.setWordWrap(True)
        ml.addWidget(self.lbl_secili_gun)
        self.btn_manuel_ekle = QPushButton(" Nöbet Ekle")
        self.btn_manuel_ekle.setProperty("style-role", "secondary")
        self.btn_manuel_ekle.setFixedHeight(28)
        self.btn_manuel_ekle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_manuel_ekle.setEnabled(False)
        IconRenderer.set_button_icon(self.btn_manuel_ekle, "plus",
                                     color=IconColors.MUTED, size=13)
        self.btn_manuel_ekle.clicked.connect(self._manuel_panel_ac)
        ml.addWidget(self.btn_manuel_ekle)
        lay.addWidget(grp_manuel)

        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("color-role", "muted")
        self.lbl_durum.setWordWrap(True)
        lay.addWidget(self.lbl_durum)
        return panel

    # ── Takvim ──

    def _build_takvim_alani(self) -> QWidget:
        wrap = QWidget()
        wl   = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)

        # Gün başlıkları
        hdr = QFrame()
        hdr.setFixedHeight(30)
        hdr.setProperty("bg-role", "elevated")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(4, 0, 4, 0)
        hl.setSpacing(2)
        for gn in _GUN_ADLARI:
            l = QLabel(gn)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setProperty("style-role", "stat-label")
            l.setProperty("color-role",
                          "warn" if gn in ("Cmt","Paz") else "muted")
            hl.addWidget(l, 1)
        wl.addWidget(hdr)

        # Grid scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._takvim_widget = QWidget()
        self._takvim_grid   = QGridLayout(self._takvim_widget)
        self._takvim_grid.setSpacing(2)
        self._takvim_grid.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._takvim_widget)
        wl.addWidget(scroll, 1)
        return wrap

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        self._personel_yukle()
        self._birim_combo_doldur()
        self._max_saat_guncelle()
        self._plan_yukle()

    def _personel_yukle(self):
        try:
            from database.repository_registry import RepositoryRegistry
            svc = get_nobet_service(self._db)
            p_rows = svc._r.get("Personel").get_all() or []
            self._personel_map = {
                str(p["KimlikNo"]): p.get("AdSoyad", "") for p in p_rows
            }
        except Exception as e:
            logger.error(f"Personel yükleme: {e}")

    def _birim_combo_doldur(self):
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.get_birimler()
            cur   = self.cmb_birim.currentData()
            self.cmb_birim.blockSignals(True)
            self.cmb_birim.clear()
            self.cmb_birim.addItem("Tüm Birimler", userData=None)
            for b in (sonuc.veri or []):
                self.cmb_birim.addItem(b, userData=b)
            # Önceki seçimi koru
            for i in range(self.cmb_birim.count()):
                if self.cmb_birim.itemData(i) == cur:
                    self.cmb_birim.setCurrentIndex(i)
                    break
            self.cmb_birim.blockSignals(False)
        except Exception as e:
            logger.error(f"Birim combo: {e}")

    def _plan_yukle(self):
        if not self._db:
            return
        try:
            svc   = get_nobet_service(self._db)
            birim_adi = self.cmb_birim.currentData()
            sonuc = svc.get_plan(self._yil, self._ay, birim_adi)
            self._plan_data = sonuc.veri or [] if sonuc.basarili else []
            self._takvim_goster()
            self._onay_durum_goster()
        except Exception as e:
            logger.error(f"Plan yükleme: {e}")

    def _filtrele_ve_goster(self):
        self._plan_yukle()

    # ─── Takvim ──────────────────────────────────────────

    def _takvim_goster(self):
        self._hucreler.clear()
        # Grid temizle
        while self._takvim_grid.count():
            item = self._takvim_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_ay.setText(f"{_AY_ADLARI[self._ay]} {self._yil}")

        # Ayın ilk gününün haftadaki yeri (0=Pzt)
        ilk_gun = date(self._yil, self._ay, 1)
        bos_adet = ilk_gun.weekday()

        # Plan → gün → nöbet listesi haritası
        gun_plan: dict[date, list[dict]] = {}
        for n in self._plan_data:
            try:
                t = date.fromisoformat(str(n.get("NobetTarihi","")))
                gun_plan.setdefault(t, []).append(n)
            except Exception:
                pass

        ay_gun_sayisi = calendar.monthrange(self._yil, self._ay)[1]
        sutun = 0
        satir = 0

        # Boş hücreler (önceki ay)
        for _ in range(bos_adet):
            bos = _GunHucresi()
            self._takvim_grid.addWidget(bos, satir, sutun)
            sutun += 1

        # Ayın günleri
        for gun_no in range(1, ay_gun_sayisi + 1):
            g    = date(self._yil, self._ay, gun_no)
            hucre = _GunHucresi(g)
            nobetler = gun_plan.get(g, [])
            hucre.set_nobetler(nobetler, self._personel_map)
            hucre.tiklandi.connect(self._on_gun_tiklandi)
            self._takvim_grid.addWidget(hucre, satir, sutun)
            self._hucreler[g] = hucre
            sutun += 1
            if sutun == 7:
                sutun = 0
                satir += 1

        # Sütun stretch
        for i in range(7):
            self._takvim_grid.setColumnStretch(i, 1)

    def _on_gun_tiklandi(self, gun: date, nobetler: list):
        if self._secili_gun and self._secili_gun in self._hucreler:
            self._hucreler[self._secili_gun].set_secili(False)
        self._secili_gun = gun
        self._hucreler[gun].set_secili(True)
        self.btn_manuel_ekle.setEnabled(True)
        self.lbl_secili_gun.setText(gun.strftime("%d.%m.%Y"))

        if nobetler:
            satirlar = [
                f"• {self._personel_map.get(n.get('PersonelID',''), n.get('PersonelID',''))}"
                for n in nobetler
            ]
            self.lbl_durum.setText(
                f"{gun.strftime('%d.%m.%Y')} nöbetleri:\n"
                + "\n".join(satirlar)
            )
        else:
            self.lbl_durum.setText(f"{gun.strftime('%d.%m.%Y')} — Nöbet yok")

    # ─── Navigasyon ──────────────────────────────────────

    # ── Manuel Nöbet Paneli ──

    def _build_manuel_panel(self) -> QFrame:
        from PySide6.QtWidgets import QScrollArea, QFormLayout, QTextEdit
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)
        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setProperty("bg-role", "elevated")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 8, 0)
        self.lbl_manuel_baslik = QLabel("Nöbet Ekle")
        self.lbl_manuel_baslik.setProperty("style-role", "section-title")
        self.lbl_manuel_baslik.setProperty("color-role", "primary")
        hl.addWidget(self.lbl_manuel_baslik)
        hl.addStretch()
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setProperty("style-role", "close")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kapat, "x",
                                     color=IconColors.MUTED, size=14)
        btn_kapat.clicked.connect(self._manuel_panel_kapat)
        hl.addWidget(btn_kapat)
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        icerik = QWidget()
        form = QFormLayout(icerik)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)

        def _lbl(t, z=False):
            l = QLabel(("★ " if z else "") + t)
            l.setProperty("color-role", "muted")
            return l

        self.lbl_manuel_tarih = QLabel("")
        self.lbl_manuel_tarih.setProperty("style-role", "section-title")
        form.addRow(_lbl("Tarih"), self.lbl_manuel_tarih)

        self.cmb_manuel_vardiya = QComboBox()
        form.addRow(_lbl("Vardiya", True), self.cmb_manuel_vardiya)

        self.cmb_manuel_personel = QComboBox()
        self.cmb_manuel_personel.setEditable(True)
        self.cmb_manuel_personel.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert)
        form.addRow(_lbl("Personel", True), self.cmb_manuel_personel)

        self.cmb_manuel_tur = QComboBox()
        self.cmb_manuel_tur.addItem("Normal",      userData="normal")
        self.cmb_manuel_tur.addItem("Fazla Mesai", userData="fazla_mesai")
        self.cmb_manuel_tur.setCurrentIndex(0)
        form.addRow(_lbl("Nöbet Türü"), self.cmb_manuel_tur)

        self.inp_manuel_not = QTextEdit()
        self.inp_manuel_not.setFixedHeight(60)
        self.inp_manuel_not.setPlaceholderText("Acil durum, hastalık notu…")
        form.addRow(_lbl("Not"), self.inp_manuel_not)

        scroll.setWidget(icerik)
        root.addWidget(scroll, 1)

        alt = QFrame()
        alt.setFixedHeight(56)
        alt.setProperty("bg-role", "elevated")
        al = QHBoxLayout(alt)
        al.setContentsMargins(16, 8, 16, 8)
        al.setSpacing(8)
        al.addStretch()
        btn_kaydet = QPushButton(" Ekle")
        btn_kaydet.setProperty("style-role", "action")
        btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kaydet, "plus",
                                     color=IconColors.PRIMARY, size=14)
        btn_kaydet.clicked.connect(self._manuel_nobet_ekle)
        al.addWidget(btn_kaydet)
        root.addWidget(alt)
        return panel

    def _manuel_panel_ac(self):
        if not self._secili_gun:
            return
        self.lbl_manuel_baslik.setText(
            f"Nöbet Ekle — {self._secili_gun.strftime('%d.%m.%Y')}")
        self.lbl_manuel_tarih.setText(
            self._secili_gun.strftime("%d.%m.%Y"))
        self._manuel_vardiya_doldur()
        self._manuel_personel_doldur()
        self._animate_manuel(300)

    def _manuel_panel_kapat(self):
        self._animate_manuel(0)

    def _animate_manuel(self, hedef: int):
        if not hasattr(self, "_manuel_anim"):
            self._manuel_anim = []
        self._manuel_anim.clear()
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        cur = self._manuel_panel.width()
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self._manuel_panel, prop)
            a.setDuration(220)
            a.setStartValue(cur)
            a.setEndValue(hedef)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start()
            self._manuel_anim.append(a)

    def _manuel_vardiya_doldur(self):
        self.cmb_manuel_vardiya.clear()
        birim_adi = self.cmb_birim.currentText().strip()
        if not birim_adi or birim_adi == "Tüm Birimler":
            return
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.get_vardiyalar(birim_adi)
            for v in (sonuc.veri or []):
                lbl = (f"{v.get('VardiyaAdi','')} "
                       f"({v.get('BasSaat','')}-{v.get('BitSaat','')})")
                self.cmb_manuel_vardiya.addItem(lbl, userData=v["VardiyaID"])
        except Exception as e:
            logger.error(f"Manuel vardiya doldur: {e}")

    def _manuel_personel_doldur(self):
        self.cmb_manuel_personel.clear()
        try:
            svc = get_nobet_service(self._db)
            p_rows = svc._r.get("Personel").get_all() or []
            tercih_map = svc._tercih_map_getir(self._yil, self._ay)
            for p in sorted(p_rows, key=lambda x: x.get("AdSoyad","")):
                pid = str(p["KimlikNo"])
                ad  = p.get("AdSoyad","")
                if not ad:
                    continue
                tercih = tercih_map.get(pid, "zorunlu")
                # Tüm personeli göster — gönüllü dışı olanları işaretle
                if tercih == "gonullu_disi":
                    etiket = f"⚠ {ad}"
                elif tercih == "nobet_yok":
                    etiket = f"✘ {ad}"
                else:
                    etiket = ad
                self.cmb_manuel_personel.addItem(etiket, userData=pid)
        except Exception as e:
            logger.error(f"Manuel personel doldur: {e}")

    def _manuel_nobet_ekle(self):
        if not self._secili_gun:
            hata_goster(self, "Önce takvimden bir gün seçin.")
            return
        v_id = self.cmb_manuel_vardiya.currentData()
        pid  = self.cmb_manuel_personel.currentData()
        tur  = self.cmb_manuel_tur.currentData()
        if not v_id or not pid:
            hata_goster(self, "Vardiya ve personel seçimi zorunludur.")
            return
        try:
            svc   = get_nobet_service(self._db)
            birim = self.cmb_birim.currentText().strip()
            not_t = self.inp_manuel_not.toPlainText().strip()
            veri  = {
                "PersonelID":  pid,
                "BirimAdi":    birim if birim != "Tüm Birimler" else "",
                "VardiyaID":   v_id,
                "NobetTarihi": self._secili_gun.isoformat(),
                "NobetTuru":   tur,
                # Fazla mesai → direkt onaylı; diğerleri → taslak
                "Durum":       "onaylandi" if tur == "fazla_mesai" else "taslak",
                "Notlar":      not_t,
            }
            sonuc = svc.plan_ekle(veri)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._manuel_panel_kapat()
                self._plan_yukle()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    def _prev_ay(self):
        if self._ay == 1:
            self._ay  = 12
            self._yil -= 1
        else:
            self._ay -= 1
        self._max_saat_guncelle()
        self._plan_yukle()

    def _next_ay(self):
        if self._ay == 12:
            self._ay  = 1
            self._yil += 1
        else:
            self._ay += 1
        self._max_saat_guncelle()
        self._plan_yukle()

    def _max_saat_guncelle(self):
        """Ay değişince iş günü × 7.5 saati spn_max_saat'e yazar."""
        try:
            from core.hesaplamalar import ay_is_gunu
            tatiller = []
            if self._db:
                try:
                    svc = get_nobet_service(self._db)
                    tatiller = svc._tatil_listesi_getir(self._yil, self._ay)
                except Exception:
                    pass
            is_gunu  = ay_is_gunu(self._yil, self._ay, tatil_listesi=tatiller)
            max_saat = round(is_gunu * 7)
            self.spn_max_saat.setValue(max_saat)
            self.lbl_is_gunu.setText(
                f"{is_gunu} iş günü × 7 saat = {max_saat} saat"
            )
        except Exception as e:
            logger.debug(f"Max saat hesap: {e}")

    # ─── Otomatik Plan ───────────────────────────────────

    def _oto_plan_olustur(self):
        birim_adi = self.cmb_birim.currentText().strip()
        if not birim_adi or birim_adi == "Tüm Birimler":
            hata_goster(self, "Otomatik planlama için bir birim seçin.")
            return

        try:
            svc = get_nobet_service(self._db)

            # Onaylanmış plan var mı kontrol et
            onay = svc.onay_getir(self._yil, self._ay, birim_adi)
            onay_rows = onay.veri or []
            zaten_onaylandi = any(
                r.get("Durum") == "onaylandi" for r in onay_rows
            )
            if zaten_onaylandi:
                hata_goster(self,
                    f"<b>{birim_adi}</b> için {_AY_ADLARI[self._ay]} {self._yil} "
                    f"planı zaten onaylanmış.\nYeni taslak oluşturmak için önce onayı geri alın.")
                return

            # Mevcut taslak sayısı
            mevcut = svc.get_plan(self._yil, self._ay, birim_adi)
            mevcut_sayi = len([r for r in (mevcut.veri or [])
                                if r.get("Durum") == "taslak"])

            onay_metni = (f"<b>{birim_adi}</b> için "
                          f"<b>{_AY_ADLARI[self._ay]} {self._yil}</b> "
                          f"nöbet taslağı oluşturulsun mu?")
            if mevcut_sayi > 0:
                onay_metni += (f"<br><br>⚠ Mevcut <b>{mevcut_sayi} taslak</b> "
                               f"silinecek.")

            if not soru_sor(self, onay_metni):
                return

            # Sadece taslakları temizle (onaylananlar korunur)
            svc.taslak_temizle(self._yil, self._ay, birim_adi)
            self.pbar.setVisible(True)
            self.btn_oto_plan.setEnabled(False)
            self.lbl_durum.setText("Taslak oluşturuluyor…")

            sonuc = svc.otomatik_plan_olustur(
                self._yil, self._ay, birim_adi,
                max_aylik_saat=float(self.spn_max_saat.value()),
            )
            self.pbar.setVisible(False)
            self.btn_oto_plan.setEnabled(True)

            if sonuc.basarili:
                uyarilar = (sonuc.veri or {}).get("uyarilar", [])
                mesaj = sonuc.mesaj
                if uyarilar:
                    mesaj += "\n\nUyarılar:\n" + "\n".join(uyarilar[:5])
                bilgi_goster(self, mesaj)
                self.lbl_durum.setText(sonuc.mesaj)
                self._plan_yukle()
            else:
                hata_goster(self, sonuc.mesaj)
                self.lbl_durum.setText("")
        except Exception as e:
            self.pbar.setVisible(False)
            self.btn_oto_plan.setEnabled(True)
            hata_goster(self, str(e))

    def _taslak_temizle(self):
        birim_adi = self.cmb_birim.currentText().strip()
        birim_goster = birim_adi if birim_adi and birim_adi != "Tüm Birimler" else "tüm birimler"
        if not soru_sor(self,
            f"<b>{_AY_ADLARI[self._ay]} {self._yil}</b> — "
            f"<b>{birim_goster}</b> taslak nöbetleri silinsin mi?\n"
            f"(Onaylanmış planlar korunur)"):
            return
        try:
            svc = get_nobet_service(self._db)
            birim_filtre = birim_adi if birim_adi and birim_adi != "Tüm Birimler" else None
            sonuc = svc.taslak_temizle(self._yil, self._ay, birim_filtre)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._plan_yukle()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    # ─── Onay ────────────────────────────────────────────

    def _onay_durum_goster(self):
        birim_adi = self.cmb_birim.currentData()
        if not birim_adi or not self._db:
            self.lbl_onay_durum.setText("—")
            return
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.onay_getir(self._yil, self._ay, birim_adi)
            rows  = sonuc.veri or []
            if rows:
                durum = rows[0].get("Durum", "taslak")
                renk  = "ok" if durum == "onaylandi" else "warn"
                self.lbl_onay_durum.setProperty("color-role", renk)
                self.lbl_onay_durum.setText(durum.capitalize())
            else:
                self.lbl_onay_durum.setText("Taslak")
            self.lbl_onay_durum.style().unpolish(self.lbl_onay_durum)
            self.lbl_onay_durum.style().polish(self.lbl_onay_durum)
        except Exception as e:
            logger.error(f"Onay durum: {e}")

    def _onayla(self):
        birim_adi = self.cmb_birim.currentText().strip()
        if not birim_adi or birim_adi == "Tüm Birimler":
            hata_goster(self, "Onaylamak için bir birim seçin.")
            return
        if not soru_sor(self,
            f"<b>{_AY_ADLARI[self._ay]} {self._yil}</b> nöbet planı onaylansın mı?"):
            return
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.onayla(self._yil, self._ay, birim_adi,
                               onaylayan_id="current_user")
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._onay_durum_goster()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))
