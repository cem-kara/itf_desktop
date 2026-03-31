# ui/pages/fhsz/dis_alan_donem_gecmisi_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Dönem Geçmişi Ekranı

Tüm birimler için hangi dönemler kapatılmış (RKS onaylı),
hangileri hâlâ açık, tek bakışta gösterir.

Her satır bir birim × dönem kombinasyonu:
  - Birim / Ay / Yıl
  - Import sayısı (kaç farklı Excel yüklendi)
  - Kişi sayısı
  - Toplam saat
  - Onay durumu (Açık / Kısmi / Kapalı)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QFont

from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from core.di import get_dis_alan_service
from core.logger import logger

AY_ADLARI = ["", "Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
              "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

def _int(v):
    try: return int(v)
    except: return 0

def _float(v):
    try: return float(str(v).replace(",", "."))
    except: return 0.0


class DisAlanDonemGecmisiPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db  = db
        self._svc = get_dis_alan_service(db) if db else None
        self._setup_ui()
        self._connect_signals()

    # ── UI ─────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 15)
        root.setSpacing(10)

        # Filtre
        top = QFrame()
        top.setStyleSheet(S["filter_panel"])
        top.setMaximumHeight(56)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 6, 12, 6); tl.setSpacing(10)

        lbl = QLabel("Dönem Geçmişi")
        lbl.setProperty("color-role", "primary")
        tl.addWidget(lbl); tl.addStretch()

        tl.addWidget(QLabel("Anabilim Dalı:"))
        self.cmb_ana = QComboBox(); self.cmb_ana.setFixedWidth(190)
        tl.addWidget(self.cmb_ana)

        tl.addWidget(QLabel("Yıl:"))
        self.cmb_yil = QComboBox()
        self.cmb_yil.addItem("Tümü")
        self.cmb_yil.addItems([
            str(y) for y in range(
                QDate.currentDate().year() - 2,
                QDate.currentDate().year() + 2
            )
        ])
        self.cmb_yil.setCurrentText(str(QDate.currentDate().year()))
        self.cmb_yil.setFixedWidth(90)
        tl.addWidget(self.cmb_yil)

        tl.addWidget(QLabel("Durum:"))
        self.cmb_durum = QComboBox()
        self.cmb_durum.addItems(["Tümü", "Açık", "Kısmi", "Kapalı"])
        self.cmb_durum.setFixedWidth(90)
        tl.addWidget(self.cmb_durum)

        self.btn_yukle = QPushButton("Yükle")
        self.btn_yukle.setStyleSheet(S["save_btn"])
        self.btn_yukle.setFixedHeight(36)
        self.btn_yukle.setFixedWidth(80)
        IconRenderer.set_button_icon(self.btn_yukle, "search", color="#FFFFFF")
        tl.addWidget(self.btn_yukle)

        root.addWidget(top)

        # Özet kartlar
        kl = QHBoxLayout(); kl.setSpacing(8)
        self.k_toplam  = self._kart("Toplam Dönem",  "—", "#457B9D")
        self.k_kapali  = self._kart("Kapalı",        "—", "#1B5E20")
        self.k_kismi   = self._kart("Kısmi Onaylı",  "—", "#E65100")
        self.k_acik    = self._kart("Açık",          "—", "#B71C1C")
        self.k_import  = self._kart("Toplam Import", "—", "#457B9D")
        self.k_kisi    = self._kart("Toplam Kişi",   "—", "#457B9D")
        for k in [self.k_toplam, self.k_kapali, self.k_kismi,
                  self.k_acik, self.k_import, self.k_kisi]:
            kl.addWidget(k)
        root.addLayout(kl)

        # Tablo
        kolonlar = [
            ("Anabilim Dalı", 180), ("Birim",      150),
            ("Yıl",            55), ("Ay",           80),
            ("Import",         65), ("Kişi",         55),
            ("Toplam Saat",    95), ("Onaylı",        65),
            ("Durum",          90),
        ]
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(kolonlar))
        self.tablo.setHorizontalHeaderLabels([c[0] for c in kolonlar])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setStyleSheet(S["table"])
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tablo.setAlternatingRowColors(False)
        hdr = self.tablo.horizontalHeader()
        for i, (_, w) in enumerate(kolonlar):
            if kolonlar[i][0] == "Anabilim Dalı":
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.tablo.setColumnWidth(i, w)

        root.addWidget(self.tablo)

        # Alt durum çubuğu
        bot = QFrame()
        bot.setStyleSheet(S.get("filter_panel", ""))
        bot.setMaximumHeight(40)
        bl = QHBoxLayout(bot)
        bl.setContentsMargins(12, 4, 12, 4)
        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("color-role", "primary")
        bl.addWidget(self.lbl_durum)
        bl.addStretch()
        root.addWidget(bot)

    def _kart(self, baslik, val, renk="#457B9D"):
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background:#1A2535; border-radius:8px; "
            f"border-left:3px solid {renk}; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(10, 6, 10, 6); lay.setSpacing(2)
        lb = QLabel(baslik)
        lb.setProperty("color-role", "primary")
        lv = QLabel(str(val))
        lv.setStyleSheet(
            f"font-size:18px; font-weight:bold; color:{renk}; border:none;"
        )
        lay.addWidget(lb); lay.addWidget(lv)
        setattr(f, "_lv", lv)
        return f

    def _kset(self, k, v):
        lv = getattr(k, "_lv", None)
        if lv: lv.setText(str(v))

    # ── Sinyaller ──────────────────────────────────────────────

    def _connect_signals(self):
        self.btn_yukle.clicked.connect(self._yukle)

    # ── Veri ───────────────────────────────────────────────────

    def _yukle(self):
        if not self._db:
            self.lbl_durum.setText("Veritabanı bağlantısı yok")
            return

        try:
            from core.di import get_registry
            reg = get_registry(self._db)
            calisma_rows  = reg.get("Dis_Alan_Calisma").get_all()  or []
            ozet_rows     = reg.get("Dis_Alan_Izin_Ozet").get_all() or []
        except Exception as e:
            logger.error(f"DonemGecmisi._yukle: {e}")
            self.lbl_durum.setText(f"Hata: {e}")
            return

        filtre_ana  = self.cmb_ana.currentText()
        filtre_yil  = self.cmb_yil.currentText()
        filtre_dur  = self.cmb_durum.currentText()

        # Anabilim Dalı combo'yu doldur (ilk çalıştırmada)
        if self.cmb_ana.count() == 0:
            anabilimler = sorted({
                str(r.get("AnaBilimDali","")).strip()
                for r in calisma_rows if r.get("AnaBilimDali")
            })
            self.cmb_ana.addItem("Tümü")
            self.cmb_ana.addItems(anabilimler)

        # Çalışma kayıtlarını dönem × birim grupla
        gruplar: dict[tuple, dict] = {}
        # key: (ana, birim, yil, ay)

        for r in calisma_rows:
            ana   = str(r.get("AnaBilimDali","")).strip()
            birim = str(r.get("Birim","")).strip()
            ay    = _int(r.get("DonemAy"))
            yil   = _int(r.get("DonemYil"))
            tn    = str(r.get("TutanakNo","")).strip()
            tc    = str(r.get("TCKimlik","")).strip() or str(r.get("AdSoyad","")).strip()

            if not (ana and birim and ay and yil):
                continue

            k = (ana, birim, yil, ay)
            if k not in gruplar:
                gruplar[k] = {
                    "ana": ana, "birim": birim, "yil": yil, "ay": ay,
                    "tutanaklar": set(), "kisiler": set(),
                    "toplam_saat": 0.0,
                    "onaylanan": 0, "toplam_kisi": 0,
                }
            gruplar[k]["tutanaklar"].add(tn)
            gruplar[k]["kisiler"].add(tc)
            gruplar[k]["toplam_saat"] += _float(r.get("HesaplananSaat", 0))

        # Onay bilgisini ekle
        onay_set: set[tuple] = set()   # (tc_veya_ad, ay, yil) → onaylı
        for o in ozet_rows:
            if _int(o.get("RksOnay", 0)) == 1:
                tc  = str(o.get("TCKimlik","")).strip() or str(o.get("AdSoyad","")).strip()
                ay  = _int(o.get("DonemAy"))
                yil = _int(o.get("DonemYil"))
                onay_set.add((tc, ay, yil))

        for k, g in gruplar.items():
            ana_, birim_, yil_, ay_ = k
            onaylanan = sum(
                1 for tc in g["kisiler"]
                if (tc, ay_, yil_) in onay_set
            )
            g["onaylanan"]    = onaylanan
            g["toplam_kisi"]  = len(g["kisiler"])
            g["toplam_saat"]  = round(g["toplam_saat"], 2)
            if onaylanan == 0:
                g["durum"] = "Açık"
            elif onaylanan < g["toplam_kisi"]:
                g["durum"] = "Kısmi"
            else:
                g["durum"] = "Kapalı"

        # Filtrele
        sonuclar = list(gruplar.values())
        if filtre_ana != "Tümü":
            sonuclar = [g for g in sonuclar if g["ana"] == filtre_ana]
        if filtre_yil != "Tümü":
            sonuclar = [g for g in sonuclar if str(g["yil"]) == filtre_yil]
        if filtre_dur != "Tümü":
            sonuclar = [g for g in sonuclar if g["durum"] == filtre_dur]

        # Sırala: Açık → Kısmi → Kapalı, sonra birim → yıl → ay
        sira = {"Açık": 0, "Kısmi": 1, "Kapalı": 2}
        sonuclar.sort(key=lambda g: (
            sira.get(g["durum"], 9), g["ana"], g["birim"], g["yil"], g["ay"]
        ))

        self._fill_table(sonuclar)
        self._update_kartlar(sonuclar)

        self.lbl_durum.setText(
            f"{len(sonuclar)} dönem gösteriliyor  |  "
            f"Son güncelleme: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}"
        )

    # ── Tablo ──────────────────────────────────────────────────

    def _fill_table(self, sonuclar):
        self.tablo.setRowCount(0)
        self.tablo.setRowCount(len(sonuclar))

        renkler = {
            "Açık":    (QColor("#3A0A0A"), QColor("#EF9A9A")),
            "Kısmi":   (QColor("#3A2A00"), QColor("#FFE082")),
            "Kapalı":  (QColor("#0A2A0A"), QColor("#A5D6A7")),
        }

        for i, g in enumerate(sonuclar):
            self.tablo.setRowHeight(i, 24)
            bg, fg = renkler.get(g["durum"], (None, QColor("#E0E0E0")))

            def _it(text, center=False, bold=False, _bg=bg, _fg=fg):
                it = QTableWidgetItem(str(text) if text is not None else "")
                if _bg:
                    it.setBackground(QBrush(_bg))
                it.setForeground(QBrush(_fg))
                if center:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bold:
                    f = QFont(); f.setBold(True); it.setFont(f)
                return it

            self.tablo.setItem(i, 0, _it(g["ana"]))
            self.tablo.setItem(i, 1, _it(g["birim"]))
            self.tablo.setItem(i, 2, _it(g["yil"],    center=True))
            ay_ad = AY_ADLARI[g["ay"]] if 1 <= g["ay"] <= 12 else str(g["ay"])
            self.tablo.setItem(i, 3, _it(ay_ad,        center=True))
            self.tablo.setItem(i, 4, _it(len(g["tutanaklar"]), center=True))
            self.tablo.setItem(i, 5, _it(g["toplam_kisi"],     center=True))
            self.tablo.setItem(i, 6, _it(f"{g['toplam_saat']:.1f}", center=True))
            self.tablo.setItem(i, 7, _it(
                f"{g['onaylanan']}/{g['toplam_kisi']}", center=True
            ))

            durum_ikon = {
                "Açık":   "◌  Açık",
                "Kısmi":  "◑  Kısmi",
                "Kapalı": "●  Kapalı",
            }
            self.tablo.setItem(i, 8, _it(
                durum_ikon.get(g["durum"], g["durum"]),
                center=True, bold=True
            ))

    # ── Kartlar ────────────────────────────────────────────────

    def _update_kartlar(self, sonuclar):
        if not sonuclar:
            for k in [self.k_toplam, self.k_kapali, self.k_kismi,
                      self.k_acik, self.k_import, self.k_kisi]:
                self._kset(k, "—")
            return

        self._kset(self.k_toplam,  len(sonuclar))
        self._kset(self.k_kapali,  sum(1 for g in sonuclar if g["durum"] == "Kapalı"))
        self._kset(self.k_kismi,   sum(1 for g in sonuclar if g["durum"] == "Kısmi"))
        self._kset(self.k_acik,    sum(1 for g in sonuclar if g["durum"] == "Açık"))
        self._kset(self.k_import,  sum(len(g["tutanaklar"]) for g in sonuclar))
        self._kset(self.k_kisi,    sum(g["toplam_kisi"] for g in sonuclar))
