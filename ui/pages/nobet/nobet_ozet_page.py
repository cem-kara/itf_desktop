# -*- coding: utf-8 -*-
"""
Nöbet Özet Sayfası
  Sekme 1 — Nöbet Özeti   : kim kaç nöbet tuttu, dağılım dengesi
  Sekme 2 — Mesai & Hedef : kişi bazlı hedef saat, fazla mesai hesap
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDoubleSpinBox, QGroupBox,
    QStackedWidget, QScrollArea, QFormLayout, QLineEdit,
    QButtonGroup, QRadioButton,
)

from core.di import get_nobet_service
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, soru_sor
from ui.styles.icons import IconRenderer, IconColors

_AY_ADLARI = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

_HEDEF_TIPLER = [
    ("normal",   "Normal"),
    ("sua",      "Şua İzni (0 saat)"),
    ("yillik",   "Yıllık İzin"),
    ("rapor",    "Raporlu"),
    ("emzirme",  "Emzirme"),
    ("idari",    "İdari İzin"),
]

_PANEL_W = 320


class NobetOzetPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db    = db
        self._ag    = action_guard
        self._yil   = date.today().year
        self._ay    = date.today().month
        self._secili_pid:  Optional[str] = None
        self._panel_mod:   str           = "hedef"   # "hedef" | "odenen"
        self._toplam_fazla: float        = 0.0
        self._anim: list = []
        self._setup_ui()
        if db:
            self.load_data()

    # ─── UI kurulum ──────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sol: sekme içerikleri
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_nobet_ozeti())   # 0
        self._stack.addWidget(self._build_mesai_hedef())   # 1
        body.addWidget(self._stack, 1)

        # Sağ: Hedef düzenleme paneli (animasyonlu)
        self._hedef_panel = self._build_hedef_panel()
        body.addWidget(self._hedef_panel)

        wrap = QWidget()
        wrap.setLayout(body)
        root.addWidget(wrap, 1)
        root.addWidget(self._build_footer())

    # ─── Toolbar ─────────────────────────────────────────

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(52)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        # Ay navigasyonu
        self.btn_prev = QPushButton("‹")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setProperty("style-role", "secondary")
        self.btn_prev.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_prev.clicked.connect(self._prev_ay)
        lay.addWidget(self.btn_prev)

        self.lbl_ay = QLabel()
        self.lbl_ay.setProperty("style-role", "title")
        self.lbl_ay.setProperty("color-role", "primary")
        lay.addWidget(self.lbl_ay)

        self.btn_next = QPushButton("›")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setProperty("style-role", "secondary")
        self.btn_next.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_next.clicked.connect(self._next_ay)
        lay.addWidget(self.btn_next)

        lay.addSpacing(12)

        lbl_b = QLabel("Birim:")
        lbl_b.setProperty("color-role", "disabled")
        lay.addWidget(lbl_b)
        self.cmb_birim = QComboBox()
        self.cmb_birim.addItem("Tüm Birimler", userData=None)
        self.cmb_birim.setFixedWidth(160)
        self.cmb_birim.currentIndexChanged.connect(self._yukle_veri)
        lay.addWidget(self.cmb_birim)

        lay.addSpacing(8)

        # Sekme butonları
        self._tab_bg = QButtonGroup(self)
        for i, (lbl_t) in enumerate(["Nöbet Özeti", "Mesai & Hedef"]):
            btn = QRadioButton(lbl_t)
            btn.setProperty("style-role", "radio")
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            self._tab_bg.addButton(btn, i)
            lay.addWidget(btn)

        lay.addStretch()

        self.btn_yenile = QPushButton()
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_yenile, "refresh",
                                     color=IconColors.MUTED, size=16)
        self.btn_yenile.clicked.connect(self.load_data)
        lay.addWidget(self.btn_yenile)
        return frame

    # ─── Sekme 0: Nöbet Özeti ────────────────────────────

    def _build_nobet_ozeti(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        self.tbl_ozet = QTableWidget(0, 6)
        self.tbl_ozet.setHorizontalHeaderLabels([
            "Ad Soyad", "Nöbet Sayısı", "Çalışılan Saat",
            "Hedef Saat", "Fazla Mesai", "Dağılım"
        ])
        self.tbl_ozet.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_ozet.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_ozet.setAlternatingRowColors(True)
        self.tbl_ozet.verticalHeader().setVisible(False)
        self.tbl_ozet.setShowGrid(False)
        self.tbl_ozet.setSortingEnabled(True)
        hdr = self.tbl_ozet.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3, 4, 5):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        vl.addWidget(self.tbl_ozet, 1)
        return w

    # ─── Sekme 1: Mesai & Hedef ──────────────────────────

    def _build_mesai_hedef(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Aksiyon toolbar
        act = QFrame()
        act.setFixedHeight(44)
        act.setProperty("bg-role", "elevated")
        al = QHBoxLayout(act)
        al.setContentsMargins(12, 0, 12, 0)
        al.setSpacing(8)

        lbl_info = QLabel("Personele tıklayarak aylık hedef saat tanımlayın")
        lbl_info.setProperty("color-role", "muted")
        al.addWidget(lbl_info)
        al.addStretch()

        self.btn_fazla_hesap = QPushButton(" Fazla Mesai Hesapla")
        self.btn_fazla_hesap.setProperty("style-role", "action")
        self.btn_fazla_hesap.setFixedHeight(30)
        self.btn_fazla_hesap.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_fazla_hesap, "calculator",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_fazla_hesap.clicked.connect(self._fazla_mesai_hesapla)
        al.addWidget(self.btn_fazla_hesap)
        vl.addWidget(act)

        # Tablo
        self.tbl_hedef = QTableWidget(0, 8)
        self.tbl_hedef.setHorizontalHeaderLabels([
            "Ad Soyad", "Hedef Tipi", "Hedef Saat",
            "Çalışılan", "Bu Ay Fazla", "Önceki Devir",
            "Ödenen ✎", "Devire Giden"
        ])
        tip = ("Çift tıklayarak hedef saat tanımlayın.\n"
               "'Ödenen ✎' sütununa çift tıklayarak ödenen saati girin.")

        self.tbl_hedef.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_hedef.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_hedef.setAlternatingRowColors(True)
        self.tbl_hedef.verticalHeader().setVisible(False)
        self.tbl_hedef.setShowGrid(False)
        self.tbl_hedef.setSortingEnabled(True)
        hdr = self.tbl_hedef.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_hedef.doubleClicked.connect(self._on_hedef_tablo_tiklandi)
        vl.addWidget(self.tbl_hedef, 1)
        return w

    # ─── Sağ Panel: Hedef Düzenleme ──────────────────────

    def _build_hedef_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)
        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık
        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setProperty("bg-role", "elevated")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 8, 0)
        self.lbl_panel_baslik = QLabel("Hedef Saat Tanımla")
        self.lbl_panel_baslik.setProperty("style-role", "section-title")
        self.lbl_panel_baslik.setProperty("color-role", "primary")
        hl.addWidget(self.lbl_panel_baslik)
        hl.addStretch()
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setProperty("style-role", "close")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kapat, "x", color=IconColors.MUTED, size=14)
        btn_kapat.clicked.connect(self._panel_kapat)
        hl.addWidget(btn_kapat)
        root.addWidget(hdr)

        # Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        icerik = QWidget()
        form = QFormLayout(icerik)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)

        def _lbl(t):
            l = QLabel(t)
            l.setProperty("color-role", "muted")
            return l

        self.lbl_panel_personel = QLabel("")
        self.lbl_panel_personel.setProperty("style-role", "section-title")
        form.addRow(_lbl("Personel"), self.lbl_panel_personel)

        self.lbl_panel_donem = QLabel("")
        self.lbl_panel_donem.setProperty("color-role", "muted")
        form.addRow(_lbl("Dönem"), self.lbl_panel_donem)

        # Hedef tipi
        self.cmb_hedef_tipi = QComboBox()
        for val, lbl_t in _HEDEF_TIPLER:
            self.cmb_hedef_tipi.addItem(lbl_t, userData=val)
        self.cmb_hedef_tipi.currentIndexChanged.connect(self._on_hedef_tipi_degisti)
        form.addRow(_lbl("Hedef Tipi"), self.cmb_hedef_tipi)

        self.spn_hedef_saat = QDoubleSpinBox()
        self.spn_hedef_saat.setRange(0.0, 400.0)
        self.spn_hedef_saat.setSingleStep(7.0)
        self.spn_hedef_saat.setValue(119.0)
        self.spn_hedef_saat.setSuffix(" saat")
        form.addRow(_lbl("Hedef Saat"), self.spn_hedef_saat)

        self.inp_aciklama = QLineEdit()
        self.inp_aciklama.setPlaceholderText("Opsiyonel not…")
        form.addRow(_lbl("Açıklama"), self.inp_aciklama)

        # Nöbet tercihi
        self.cmb_nobet_tercihi = QComboBox()
        self.cmb_nobet_tercihi.addItem("Zorunlu (algoritma atar)",     userData="zorunlu")
        self.cmb_nobet_tercihi.addItem("Gönüllü dışı (acil hariç)",   userData="gonullu_disi")
        self.cmb_nobet_tercihi.addItem("Nöbet yok (hiç atanmaz)",      userData="nobet_yok")
        self.cmb_nobet_tercihi.setToolTip(
            "Zorunlu: Algoritma bu kişiyi normale atar.\n"
            "Gönüllü dışı: Algoritma atlamaz, acil/hastalık\n"
            "  durumunda 'Fazla Mesai' olarak manuel eklenebilir.\n"
            "Nöbet yok: Hiçbir şekilde atanamaz."
        )
        form.addRow(_lbl("Nöbet Tercihi"), self.cmb_nobet_tercihi)

        # Ödenen saat alanı (mod=odenen iken görünür)
        self.lbl_toplam_bilgi = QLabel("")
        self.lbl_toplam_bilgi.setProperty("color-role", "muted")
        self.lbl_toplam_bilgi.setWordWrap(True)
        form.addRow(_lbl("Toplam Fazla"), self.lbl_toplam_bilgi)

        self.spn_odenen = QDoubleSpinBox()
        self.spn_odenen.setRange(0.0, 999.0)
        self.spn_odenen.setSingleStep(7.0)
        self.spn_odenen.setValue(0.0)
        self.spn_odenen.setSuffix(" saat")
        self.spn_odenen.setVisible(False)
        form.addRow(_lbl("Ödenen Saat"), self.spn_odenen)

        self.lbl_devire_onizleme = QLabel("")
        self.lbl_devire_onizleme.setProperty("color-role", "muted")
        self.lbl_devire_onizleme.setVisible(False)
        form.addRow(_lbl("Devire Giden"), self.lbl_devire_onizleme)
        self.spn_odenen.valueChanged.connect(self._odenen_onizle)

        # Bilgi etiketi
        self.lbl_hesap_bilgi = QLabel("")
        self.lbl_hesap_bilgi.setProperty("color-role", "muted")
        self.lbl_hesap_bilgi.setWordWrap(True)
        form.addRow("", self.lbl_hesap_bilgi)

        scroll.setWidget(icerik)
        root.addWidget(scroll, 1)

        # Alt buton
        alt = QFrame()
        alt.setFixedHeight(56)
        alt.setProperty("bg-role", "elevated")
        al = QHBoxLayout(alt)
        al.setContentsMargins(16, 8, 16, 8)
        al.setSpacing(8)
        al.addStretch()
        btn_kaydet = QPushButton(" Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_kaydet, "save",
                                     color=IconColors.PRIMARY, size=14)
        btn_kaydet.clicked.connect(self._hedef_kaydet)
        al.addWidget(btn_kaydet)
        root.addWidget(alt)
        return panel

    # ─── Footer ──────────────────────────────────────────

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        self.lbl_ozet = QLabel("")
        self.lbl_ozet.setProperty("style-role", "footer")
        lay.addWidget(self.lbl_ozet)
        lay.addStretch()
        self.lbl_sayi = QLabel("0 personel")
        self.lbl_sayi.setProperty("style-role", "footer")
        lay.addWidget(self.lbl_sayi)
        return frame

    # ─── Animasyon ───────────────────────────────────────

    def _panel_ac(self):
        self._animate(_PANEL_W)

    def _panel_kapat(self):
        self._animate(0)
        self._secili_pid = None

    def _animate(self, hedef: int):
        self._anim.clear()
        cur = self._hedef_panel.width()
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self._hedef_panel, prop)
            a.setDuration(220)
            a.setStartValue(cur)
            a.setEndValue(hedef)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start()
            self._anim.append(a)

    # ─── Sekme geçişi ────────────────────────────────────

    def _switch_tab(self, idx: int):
        self._panel_kapat()
        self._stack.setCurrentIndex(idx)

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        self._birim_combo_doldur()
        self._yukle_veri()

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
            for i in range(self.cmb_birim.count()):
                if self.cmb_birim.itemData(i) == cur:
                    self.cmb_birim.setCurrentIndex(i)
                    break
            self.cmb_birim.blockSignals(False)
        except Exception as e:
            logger.error(f"Birim combo özet: {e}")

    def _yukle_veri(self):
        if not self._db:
            return
        self.lbl_ay.setText(f"{_AY_ADLARI[self._ay]} {self._yil}")
        birim_adi = self.cmb_birim.currentText().strip()
        birim_filtre = birim_adi if birim_adi != "Tüm Birimler" else None

        try:
            svc = get_nobet_service(self._db)
            self._yukle_nobet_ozeti(svc, birim_filtre)
            self._yukle_mesai_hedef(svc, birim_filtre)
        except Exception as e:
            logger.error(f"Özet veri yükleme: {e}")

    # ─── Sekme 0 verisi ──────────────────────────────────

    def _yukle_nobet_ozeti(self, svc, birim_filtre):
        try:
            from core.services.nobet_service import GUNLUK_HEDEF_SAAT
            sonuc = svc.personel_nobet_ozeti(self._yil, self._ay, birim_filtre)
            rows  = sonuc.veri or [] if sonuc.basarili else []

            # Personel adları — servis AdSoyad doldursa da güvenlik için tekrar al
            try:
                p_rows = svc._r.get("Personel").get_all() or []
                p_ad   = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_rows}
            except Exception:
                p_ad = {}

            # Hedef saat haritası
            hedef_sonuc = svc.mesai_hedef_getir(self._yil, self._ay, birim_filtre)
            hedef_map: dict[str, float] = {
                str(r.get("PersonelID","")): float(r.get("HedefSaat", 0.0))
                for r in (hedef_sonuc.veri or [])
            }

            # İş günü — varsayılan hedef
            try:
                from core.hesaplamalar import ay_is_gunu
                tatiller = svc._tatil_listesi_getir(self._yil, self._ay)
                is_gunu  = ay_is_gunu(self._yil, self._ay, tatil_listesi=tatiller)
                varsayilan_hedef = is_gunu * GUNLUK_HEDEF_SAAT
            except Exception:
                varsayilan_hedef = 119.0

            ortalama = sum(r.get("NobetSayisi",0) for r in rows) / max(len(rows), 1)

            self.tbl_ozet.setSortingEnabled(False)
            self.tbl_ozet.setRowCount(0)

            for r in rows:
                ri      = self.tbl_ozet.rowCount()
                self.tbl_ozet.insertRow(ri)
                pid     = str(r.get("PersonelID",""))
                ad      = p_ad.get(pid) or str(r.get("AdSoyad", pid))
                calisan = float(r.get("ToplamSaat", 0.0))

                # Önce tablodaki kayıt, yoksa izin düşülmüş otomatik hesap
                hedef_tab = hedef_map.get(pid)
                if hedef_tab is not None:
                    hedef = hedef_tab
                else:
                    try:
                        h = svc._kisi_hedef_saat(pid, self._yil, self._ay,
                                                  otomatik=True)
                        hedef = h if h is not None else varsayilan_hedef
                    except Exception:
                        hedef = varsayilan_hedef
                fazla   = calisan - hedef
                sayi    = int(r.get("NobetSayisi", 0))

                if sayi > ortalama * 1.3:
                    dagil, dagil_renk = "↑ Yüksek",  QColor("#e8a030")
                elif sayi < ortalama * 0.7:
                    dagil, dagil_renk = "↓ Düşük",   QColor("#4d6070")
                else:
                    dagil, dagil_renk = "✔ Dengeli", QColor("#2ec98e")

                vals = [
                    (ad,                                          None),
                    (str(sayi),                                   None),
                    (f"{calisan:.0f} saat",                       None),
                    (f"{hedef:.0f} saat",                         None),
                    (f"{fazla:+.0f} saat" if calisan > 0 else "—",
                     QColor("#e8a030") if fazla > 0 else
                     QColor("#e85555") if fazla < 0 else None),
                    (dagil,                                       dagil_renk),
                ]
                for col, (txt, renk) in enumerate(vals):
                    item = QTableWidgetItem(txt)
                    item.setData(Qt.ItemDataRole.UserRole, pid)   # her hücreye pid
                    if renk:
                        item.setForeground(renk)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter |
                        (Qt.AlignmentFlag.AlignLeft if col == 0
                         else Qt.AlignmentFlag.AlignCenter)
                    )
                    self.tbl_ozet.setItem(ri, col, item)

            self.tbl_ozet.setSortingEnabled(True)
            toplam = sum(r.get("NobetSayisi",0) for r in rows)
            self.lbl_sayi.setText(f"{len(rows)} personel")
            self.lbl_ozet.setText(
                f"Toplam {toplam} nöbet | Ortalama {ortalama:.1f}/kişi"
            )
        except Exception as e:
            logger.error(f"Nöbet özeti: {e}")

    # ─── Sekme 1 verisi ──────────────────────────────────

    def _yukle_mesai_hedef(self, svc, birim_filtre):
        try:
            from core.services.nobet_service import GUNLUK_HEDEF_SAAT

            # Personel özeti (çalışılan saat için)
            ozet_sonuc = svc.personel_nobet_ozeti(self._yil, self._ay, birim_filtre)
            ozet_map: dict[str, dict] = {
                str(r.get("PersonelID","")): r
                for r in (ozet_sonuc.veri or [])
            }

            # Hedef kayıtları
            hedef_sonuc = svc.mesai_hedef_getir(self._yil, self._ay, birim_filtre)
            hedef_map: dict[str, dict] = {
                str(r.get("PersonelID","")): r
                for r in (hedef_sonuc.veri or [])
            }

            # Fazla mesai hesaplanmış sonuçlar
            fazla_sonuc = svc.fazla_mesai_getir(self._yil, self._ay, birim_filtre)
            fazla_map: dict[str, dict] = {
                str(r.get("PersonelID","")): r
                for r in (fazla_sonuc.veri or [])
            }

            # İş günü varsayılan
            try:
                from core.hesaplamalar import ay_is_gunu
                tatiller = svc._tatil_listesi_getir(self._yil, self._ay)
                is_gunu  = ay_is_gunu(self._yil, self._ay, tatil_listesi=tatiller)
                varsayilan_hedef = is_gunu * GUNLUK_HEDEF_SAAT
            except Exception:
                varsayilan_hedef = 119.0

            # Personel listesi — ozet + hedef tablosundaki herkes
            tum_pid = set(ozet_map.keys()) | set(hedef_map.keys())
            # Personel adları
            try:
                p_rows = svc._r.get("Personel").get_all() or []
                p_ad   = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_rows}
            except Exception:
                p_ad = {}

            # Sadece bu birime ait personeller
            if birim_filtre:
                tum_pid = {
                    pid for pid in tum_pid
                    if pid in ozet_map or
                    (hedef_map.get(pid, {}).get("BirimAdi") == birim_filtre)
                }

            self.tbl_hedef.setSortingEnabled(False)
            self.tbl_hedef.setRowCount(0)
            tipler_map = dict(_HEDEF_TIPLER)

            for pid in sorted(tum_pid, key=lambda p: p_ad.get(p, p)):
                hedef_r = hedef_map.get(pid, {})
                fazla_r = fazla_map.get(pid, {})
                ozet_r  = ozet_map.get(pid, {})

                h_tipi   = hedef_r.get("HedefTipi", "normal")
                h_saat   = float(hedef_r.get("HedefSaat", varsayilan_hedef)) \
                           if hedef_r else varsayilan_hedef
                calisan  = float(ozet_r.get("ToplamSaat", 0.0))
                bu_ay_f  = float(fazla_r.get("FazlaMesaiSaat", calisan - h_saat))
                devir    = float(fazla_r.get("DevirSaat", 0.0))
                odenen   = float(fazla_r.get("OdenenSaat", 0.0))
                devire_g = float(fazla_r.get("DevireGiden", 0.0))
            tipler_map = dict(_HEDEF_TIPLER)

            for pid in sorted(tum_pid, key=lambda p: p_ad.get(p, p)):
                hedef_r  = hedef_map.get(pid, {})
                fazla_r  = fazla_map.get(pid, {})
                ozet_r   = ozet_map.get(pid, {})
                ad       = p_ad.get(pid) or pid

                h_tipi  = hedef_r.get("HedefTipi", "normal")
                if hedef_r:
                    h_saat = float(hedef_r.get("HedefSaat", varsayilan_hedef))
                else:
                    try:
                        h = svc._kisi_hedef_saat(pid, self._yil, self._ay,
                                                  otomatik=True)
                        h_saat = h if h is not None else varsayilan_hedef
                    except Exception:
                        h_saat = varsayilan_hedef
                calisan  = float(ozet_r.get("ToplamSaat", 0.0))
                bu_ay_f  = float(fazla_r.get("FazlaMesaiSaat", calisan - h_saat))
                devir    = float(fazla_r.get("DevirSaat", 0.0))
                odenen   = float(fazla_r.get("OdenenSaat", 0.0))
                devire_g = float(fazla_r.get("DevireGiden", 0.0))
                self.tbl_hedef.insertRow(ri)

                def _renk_fazla(v):
                    if v > 0: return QColor("#e8a030")
                    if v < 0: return QColor("#e85555")
                    return None

                tercih       = str(hedef_r.get("NobetTercihi", "zorunlu"))
                tercih_etiket = {
                    "gonullu_disi": " ⚠ Gönüllü Dışı",
                    "nobet_yok":    " ✘ Nöbet Yok",
                }
                tercih_txt  = tercih_etiket.get(tercih, "")
                tercih_renk = (QColor("#e8a030") if tercih == "gonullu_disi"
                               else QColor("#e85555") if tercih == "nobet_yok"
                               else None)

                vals = [
                    (ad + tercih_txt,                 tercih_renk),
                    (tipler_map.get(h_tipi, h_tipi),  None),
                    (f"{h_saat:.0f} saat",            None),
                    (f"{calisan:.0f} saat",           None),
                    (f"{bu_ay_f:+.1f}",               _renk_fazla(bu_ay_f)),
                    (f"{devir:+.1f}" if devir != 0 else "—",
                     QColor("#4d9ee8") if devir != 0 else None),
                    (f"{odenen:.0f} saat" if odenen > 0 else "—",
                     QColor("#2ec98e") if odenen > 0 else None),
                    (f"{devire_g:+.1f}" if devire_g != 0 else "—",
                     _renk_fazla(devire_g)),
                ]
                for col, (txt, renk) in enumerate(vals):
                    item = QTableWidgetItem(txt)
                    item.setData(Qt.ItemDataRole.UserRole, pid)   # pid her hücrede
                    if renk:
                        item.setForeground(renk)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter |
                        (Qt.AlignmentFlag.AlignLeft if col == 0
                         else Qt.AlignmentFlag.AlignCenter)
                    )
                    self.tbl_hedef.setItem(ri, col, item)

            self.tbl_hedef.setSortingEnabled(True)

        except Exception as e:
            logger.error(f"Mesai hedef yükleme: {e}")

    # ─── Hedef panel işlemleri ───────────────────────────

    def _on_hedef_tablo_tiklandi(self, idx):
        """Sütun 6 (Ödenen ✎) → ödenen panel, diğerleri → hedef panel."""
        if idx.column() == 6:
            self._on_odenen_sec(idx)
        else:
            self._on_hedef_sec(idx)

    def _on_hedef_sec(self, idx):
        pid = self.tbl_hedef.item(idx.row(), 0)
        if not pid:
            return
        pid = pid.data(Qt.ItemDataRole.UserRole)
        if not pid:
            return
        self._secili_pid = pid
        self._panel_mod  = "hedef"
        ad = self.tbl_hedef.item(idx.row(), 0).text()

        self.spn_hedef_saat.setVisible(True)
        self.cmb_hedef_tipi.setVisible(True)
        self.inp_aciklama.setVisible(True)
        self.lbl_hesap_bilgi.setVisible(True)
        self.spn_odenen.setVisible(False)
        self.lbl_devire_onizleme.setVisible(False)
        self.lbl_toplam_bilgi.setVisible(False)

        self.lbl_panel_baslik.setText("Hedef Saat Tanımla")
        self.lbl_panel_personel.setText(ad)
        self.lbl_panel_donem.setText(f"{_AY_ADLARI[self._ay]} {self._yil}")

        # Mevcut hedef tipini bul
        tipi_txt = self.tbl_hedef.item(idx.row(), 1)
        tipi_txt = tipi_txt.text() if tipi_txt else ""
        tipler_ters = {v: k for k, v in _HEDEF_TIPLER}
        tipi = tipler_ters.get(tipi_txt, "normal")
        for i in range(self.cmb_hedef_tipi.count()):
            if self.cmb_hedef_tipi.itemData(i) == tipi:
                self.cmb_hedef_tipi.setCurrentIndex(i)
                break

        # Mevcut hedef saatini al
        saat_item = self.tbl_hedef.item(idx.row(), 2)
        if saat_item:
            try:
                self.spn_hedef_saat.setValue(
                    float(saat_item.text().replace(" saat","").strip()))
            except Exception:
                pass
        self.inp_aciklama.clear()
        self._on_hedef_tipi_degisti()

        # Mevcut NobetTercihi — servis kaydından al
        try:
            svc = get_nobet_service(self._db)
            tercih_map = svc._tercih_map_getir(self._yil, self._ay)
            tercih = tercih_map.get(pid, "zorunlu")
            for i in range(self.cmb_nobet_tercihi.count()):
                if self.cmb_nobet_tercihi.itemData(i) == tercih:
                    self.cmb_nobet_tercihi.setCurrentIndex(i)
                    break
        except Exception:
            self.cmb_nobet_tercihi.setCurrentIndex(0)

        self._panel_ac()

    def _on_odenen_sec(self, idx):
        pid = self.tbl_hedef.item(idx.row(), 0)
        if not pid:
            return
        pid = pid.data(Qt.ItemDataRole.UserRole)
        if not pid:
            return
        self._secili_pid = pid
        self._panel_mod  = "odenen"
        ad = self.tbl_hedef.item(idx.row(), 0).text()

        # Toplam fazla = Bu Ay + Devir
        def _f(col):
            item = self.tbl_hedef.item(idx.row(), col)
            if not item: return 0.0
            try: return float(item.text().replace(" saat","").replace("+","").strip())
            except: return 0.0

        bu_ay   = _f(4)
        devir   = _f(5)
        toplam  = bu_ay + devir
        self._toplam_fazla = toplam

        self.spn_hedef_saat.setVisible(False)
        self.cmb_hedef_tipi.setVisible(False)
        self.inp_aciklama.setVisible(False)
        self.lbl_hesap_bilgi.setVisible(False)
        self.spn_odenen.setVisible(True)
        self.lbl_devire_onizleme.setVisible(True)
        self.lbl_toplam_bilgi.setVisible(True)

        self.lbl_panel_baslik.setText("Ödenen Saat Gir")
        self.lbl_panel_personel.setText(ad)
        self.lbl_panel_donem.setText(f"{_AY_ADLARI[self._ay]} {self._yil}")
        self.lbl_toplam_bilgi.setText(
            f"Toplam: {toplam:+.1f} saat  "
            f"({'alacaklı' if toplam >= 0 else 'verecekli'})"
        )
        self.spn_odenen.setValue(_f(6))
        self._odenen_onizle()
        self._panel_ac()

    def _odenen_onizle(self):
        devire = self._toplam_fazla - self.spn_odenen.value()
        renk   = "color:#e8a030" if devire > 0 else ("color:#e85555" if devire < 0 else "")
        self.lbl_devire_onizleme.setText(f"{devire:+.1f} saat")
        if renk:
            self.lbl_devire_onizleme.setStyleSheet(renk)

    def _on_hedef_tipi_degisti(self):
        tipi = self.cmb_hedef_tipi.currentData()
        bilgi = {
            "normal":  "Standart: iş günü × 7 saat",
            "sua":     "Şua iznindeyken hedef saat = 0",
            "yillik":  "Yıllık izin kullanılan günler düşülür",
            "rapor":   "Raporlu gün sayısı × 7 saat düşülür",
            "emzirme": "Emzirme izni: günde 1.5 saat eksik × gün sayısı",
            "idari":   "İdari izin günleri iş günü sayılmaz",
        }
        self.lbl_hesap_bilgi.setText(bilgi.get(tipi, ""))

        # Tipi seçince otomatik saat önerisi
        try:
            svc = get_nobet_service(self._db)
            from core.hesaplamalar import ay_is_gunu
            tatiller = svc._tatil_listesi_getir(self._yil, self._ay)
            is_gunu  = ay_is_gunu(self._yil, self._ay, tatil_listesi=tatiller)
            from core.services.nobet_service import GUNLUK_HEDEF_SAAT
            if tipi == "sua":
                self.spn_hedef_saat.setValue(0.0)
            elif tipi == "normal":
                self.spn_hedef_saat.setValue(is_gunu * GUNLUK_HEDEF_SAAT)
        except Exception:
            pass

    def _hedef_kaydet(self):
        if not self._secili_pid:
            return
        try:
            svc = get_nobet_service(self._db)
            if self._panel_mod == "odenen":
                sonuc = svc.odenen_guncelle(
                    self._secili_pid, self._yil, self._ay,
                    self.spn_odenen.value()
                )
            else:
                tipi  = self.cmb_hedef_tipi.currentData()
                saat  = self.spn_hedef_saat.value()
                acik  = self.inp_aciklama.text().strip()
                birim = self.cmb_birim.currentText().strip()
                birim = birim if birim != "Tüm Birimler" else ""
                sonuc = svc.mesai_hedef_kaydet(
                    self._secili_pid, self._yil, self._ay,
                    saat, tipi, birim, acik,
                    nobet_tercihi=self.cmb_nobet_tercihi.currentData()
                )
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._panel_kapat()
                self._yukle_veri()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    def _fazla_mesai_hesapla(self):
        birim = self.cmb_birim.currentText().strip()
        birim_filtre = birim if birim != "Tüm Birimler" else None
        if not soru_sor(self,
            f"<b>{_AY_ADLARI[self._ay]} {self._yil}</b> fazla mesai "
            f"hesaplansın mı?\n\nOnaylanmış plan verileri kullanılır."):
            return
        try:
            svc   = get_nobet_service(self._db)
            sonuc = svc.fazla_mesai_hesapla(self._yil, self._ay, birim_filtre)
            if sonuc.basarili:
                bilgi_goster(self, sonuc.mesaj)
                self._yukle_veri()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))

    # ─── Navigasyon ──────────────────────────────────────

    def _prev_ay(self):
        if self._ay == 1:
            self._ay = 12; self._yil -= 1
        else:
            self._ay -= 1
        self._panel_kapat()
        self._yukle_veri()

    def _next_ay(self):
        if self._ay == 12:
            self._ay = 1; self._yil += 1
        else:
            self._ay += 1
        self._panel_kapat()
        self._yukle_veri()
