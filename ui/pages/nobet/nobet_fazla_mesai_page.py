# -*- coding: utf-8 -*-
"""
nobet_fazla_mesai_page.py — Birim Bazlı Fazla Mesai Bildirim Ekranı

Bu ekran ödeme işlemi yapmaz.

Amaç:
  - Seçilen birim için aylık fazla mesai saatlerini özetlemek
  - İdareye verilecek çıktıyı hazırlamak
  - Sonraki nöbet planlarında adil dağılım için referans üretmek

Akış:
  1. Birim seç
  2. Ay seç
  3. Mesai saatlerini hazırla
  4. Sonuçları gözden geçir
  5. PDF / CSV çıktısı al
"""
from __future__ import annotations

import csv
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.di import (
    get_nb_birim_service,
    get_nb_mesai_service,
    get_nb_plan_service,
    get_personel_service,
)
from core.hata_yonetici import bilgi_goster, hata_logla_goster, uyari_goster, soru_sor
from ui.styles.icons import IconColors, IconRenderer

_AY = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

FM_BILDIRIM_ESIK_DK = 7 * 60


def _it(text: str, user_data=None) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def _fmt_dk(dakika: int) -> str:
    if dakika == 0:
        return "0s 00dk"
    isaret = "-" if dakika < 0 else ""
    dakika = abs(dakika)
    return f"{isaret}{dakika // 60}s {dakika % 60:02d}dk"


def _status_bilgisi(toplam_dk: int) -> tuple[str, str]:
    if toplam_dk >= FM_BILDIRIM_ESIK_DK:
        return "Bildirime Hazır", "#f59e0b"
    if toplam_dk > 0:
        return "Takip", "#4d9ee8"
    if toplam_dk <= -FM_BILDIRIM_ESIK_DK:
        return "Eksik", "#e85555"
    return "Dengede", "#2ec98e"


def _bayram_ekstra_dk(calis_dk: int, hedef_dk: int, fazla_dk: int) -> int:
    # FazlaDakika = (CalisDakika - HedefDakika) + BayramDakika
    return max(0, fazla_dk - (calis_dk - hedef_dk))


class NobetFazlaMesaiPage(QWidget):
    """Birim bazlı fazla mesai özet ekranı."""

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._ag = action_guard
        self._yil = date.today().year
        self._ay = date.today().month
        self._birim_id = ""
        self._birim_adi = ""
        self._personel_ad_map: dict[str, str] = {}
        self._satirlar: list[dict] = []

        self._birim_svc = get_nb_birim_service(db) if db else None
        self._plan_svc = get_nb_plan_service(db) if db else None
        self._mesai_svc = get_nb_mesai_service(db) if db else None
        self._personel_svc = get_personel_service(db) if db else None

        self.setProperty("bg-role", "page")
        self._build()
        if db:
            self._personel_map_yukle()
            self._birimleri_yukle()

    def _build(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 16, 16, 16)
        ana.setSpacing(12)

        ana.addWidget(self._build_header())
        ana.addWidget(self._build_toolbar())
        ana.addWidget(self._build_summary_bar())
        ana.addWidget(self._build_info_panel())
        ana.addWidget(self._build_table_panel(), 1)
        ana.addWidget(self._build_detail_panel())

    def _build_header(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        baslik = QLabel("Fazla Mesai Bildirimi")
        baslik.setProperty("style-role", "title")
        layout.addWidget(baslik)

        alt = QLabel(
            "Bu ekran ödeme işlemi yapmaz. Sadece idareye verilecek fazla mesai "
            "çıktısını hazırlar ve sonraki nöbet çizelgeleri için denge verisi üretir."
        )
        alt.setProperty("color-role", "muted")
        layout.addWidget(alt)
        return panel

    def _build_toolbar(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self._btn_ay_geri = QPushButton("")
        self._btn_ay_geri.setProperty("style-role", "secondary")
        self._btn_ay_geri.setFixedSize(28, 28)
        IconRenderer.set_button_icon(
            self._btn_ay_geri, "chevron_left", color=IconColors.MUTED, size=14
        )
        self._btn_ay_geri.clicked.connect(self._ay_geri)
        layout.addWidget(self._btn_ay_geri)

        self._lbl_ay = QLabel("")
        self._lbl_ay.setFixedWidth(120)
        self._lbl_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ay.setProperty("style-role", "section-title")
        layout.addWidget(self._lbl_ay)

        self._btn_ay_ileri = QPushButton("")
        self._btn_ay_ileri.setProperty("style-role", "secondary")
        self._btn_ay_ileri.setFixedSize(28, 28)
        IconRenderer.set_button_icon(
            self._btn_ay_ileri, "chevron_right", color=IconColors.MUTED, size=14
        )
        self._btn_ay_ileri.clicked.connect(self._ay_ileri)
        layout.addWidget(self._btn_ay_ileri)

        layout.addSpacing(12)

        lbl_birim = QLabel("Birim")
        lbl_birim.setProperty("style-role", "form")
        layout.addWidget(lbl_birim)

        self._cmb_birim = QComboBox()
        self._cmb_birim.setMinimumWidth(240)
        self._cmb_birim.currentIndexChanged.connect(self._on_birim_degisti)
        layout.addWidget(self._cmb_birim)

        layout.addStretch()

        self._btn_hazirla = QPushButton("Mesai Saatlerini Hazırla")
        self._btn_hazirla.setProperty("style-role", "action")
        self._btn_hazirla.setFixedHeight(30)
        IconRenderer.set_button_icon(
            self._btn_hazirla, "clipboard_list", color=IconColors.PRIMARY, size=14
        )
        self._btn_hazirla.clicked.connect(self._mesai_hazirla)
        layout.addWidget(self._btn_hazirla)

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setProperty("style-role", "secondary")
        self._btn_yenile.setFixedHeight(30)
        IconRenderer.set_button_icon(
            self._btn_yenile, "refresh", color=IconColors.MUTED, size=14
        )
        self._btn_yenile.clicked.connect(self._sayfa_yenile)
        layout.addWidget(self._btn_yenile)

        self._btn_pdf = QPushButton("PDF")
        self._btn_pdf.setProperty("style-role", "secondary")
        self._btn_pdf.setFixedHeight(30)
        self._btn_pdf.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_pdf, "file_pdf", color=IconColors.MUTED, size=14
        )
        self._btn_pdf.clicked.connect(self._pdf_al)
        layout.addWidget(self._btn_pdf)

        self._btn_csv = QPushButton("CSV")
        self._btn_csv.setProperty("style-role", "secondary")
        self._btn_csv.setFixedHeight(30)
        self._btn_csv.setEnabled(False)
        IconRenderer.set_button_icon(
            self._btn_csv, "download", color=IconColors.MUTED, size=14
        )
        self._btn_csv.clicked.connect(self._csv_al)
        layout.addWidget(self._btn_csv)

        return panel

    def _build_summary_bar(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._kart_personel = self._build_summary_card("Personel", "0")
        self._kart_hazir = self._build_summary_card("Bildirime Hazır", "0")
        self._kart_toplam = self._build_summary_card("Toplam Fazla", "0s 00dk")
        self._kart_eksik = self._build_summary_card("Eksik Bakiye", "0s 00dk")

        for kart in [
            self._kart_personel,
            self._kart_hazir,
            self._kart_toplam,
            self._kart_eksik,
        ]:
            layout.addWidget(kart, 1)

        return panel

    def _build_summary_card(self, baslik: str, deger: str) -> QFrame:
        kart = QFrame()
        kart.setProperty("bg-role", "elevated")
        layout = QVBoxLayout(kart)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        value_lbl = QLabel(deger)
        value_lbl.setProperty("style-role", "stat-value")
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(baslik)
        title_lbl.setProperty("style-role", "stat-label")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(value_lbl)
        layout.addWidget(title_lbl)
        kart._value_label = value_lbl  # type: ignore[attr-defined]
        return kart

    def _build_info_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self._lbl_durum = QLabel("Birim seçerek başlayın.")
        self._lbl_durum.setProperty("style-role", "section-title")
        layout.addWidget(self._lbl_durum)

        self._lbl_aciklama = QLabel(
            "Mesai özeti henüz hazırlanmadı. Seçilen birim ve ay için hesap oluşturulduktan sonra çıktı alınabilir."
        )
        self._lbl_aciklama.setProperty("color-role", "muted")
        self._lbl_aciklama.setWordWrap(True)
        layout.addWidget(self._lbl_aciklama)
        return panel

    def _build_table_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._tbl = QTableWidget(0, 9)
        self._tbl.setHorizontalHeaderLabels([
            "Personel",
            "Çalışılan",
            "Hedef",
            "Bu Ay Fazla",
            "Bayram Ekstra",
            "Önceki Devir",
            "Toplam",
            "Durum",
            "Son Hesap",
        ])
        header = self._tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for kolon in range(1, 9):
            header.setSectionResizeMode(kolon, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.itemSelectionChanged.connect(self._detay_guncelle)
        layout.addWidget(self._tbl, 1)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        baslik = QLabel("Seçili Kayıt")
        baslik.setProperty("style-role", "section-title")
        layout.addWidget(baslik)

        self._lbl_detay = QLabel(
            "Tablodan bir kayıt seçtiğinizde bu personelin mesai dengesi burada özetlenir."
        )
        self._lbl_detay.setWordWrap(True)
        self._lbl_detay.setProperty("color-role", "muted")
        layout.addWidget(self._lbl_detay)
        return panel

    def _personel_map_yukle(self):
        if not self._personel_svc:
            return
        sonuc = self._personel_svc.get_personel_listesi(aktif_only=False)
        if not sonuc.basarili:
            return
        self._personel_ad_map = {
            str(r.get("KimlikNo", "")): str(r.get("AdSoyad", "")).strip()
            for r in (sonuc.veri or [])
            if str(r.get("KimlikNo", "")).strip()
        }

    def _birimleri_yukle(self):
        if not self._birim_svc:
            return
        sonuc = self._birim_svc.get_birimler(sadece_aktif=True)
        if not sonuc.basarili:
            uyari_goster(self, sonuc.mesaj or "Birimler yüklenemedi.")
            return

        self._cmb_birim.blockSignals(True)
        self._cmb_birim.clear()
        self._cmb_birim.addItem("Birim seçin", userData="")
        for birim in (sonuc.veri or []):
            self._cmb_birim.addItem(
                birim.get("BirimAdi", ""),
                userData=birim.get("BirimID", ""),
            )
        self._cmb_birim.blockSignals(False)
        self._sayfa_yenile()

    def _ay_geri(self):
        if self._ay == 1:
            self._ay = 12
            self._yil -= 1
        else:
            self._ay -= 1
        self._sayfa_yenile()

    def _ay_ileri(self):
        if self._ay == 12:
            self._ay = 1
            self._yil += 1
        else:
            self._ay += 1
        self._sayfa_yenile()

    def _on_birim_degisti(self):
        self._birim_id = str(self._cmb_birim.currentData() or "")
        self._birim_adi = self._cmb_birim.currentText() if self._birim_id else ""
        self._sayfa_yenile()

    def _guncel_plan(self) -> dict | None:
        if not self._plan_svc or not self._birim_id:
            return None
        return self._plan_svc.get_plan(self._birim_id, self._yil, self._ay)

    def _mesai_hazirla(self):
        if not self._birim_id:
            uyari_goster(self, "Önce birim seçin.")
            return

        plan = self._guncel_plan()
        if not plan:
            uyari_goster(self, "Seçilen ay için plan bulunamadı.")
            return

        if self._satirlar and not soru_sor(
            self,
            "Bu ay için mevcut mesai özeti yeniden oluşturulacak. Devam etmek istiyor musunuz?",
        ):
            return

        try:
            sonuc = self._mesai_svc.mesai_hesapla(
                self._birim_id,
                str(plan.get("PlanID", "")),
                self._yil,
                self._ay,
            )
            if not sonuc.basarili:
                uyari_goster(self, sonuc.mesaj or "Mesai özeti hazırlanamadı.")
                return
            bilgi_goster(
                self,
                "Mesai saatleri hazırlandı. Artık idare çıktısını alabilirsiniz.",
            )
            self._sayfa_yenile()
        except Exception as exc:
            hata_logla_goster(self, "NobetFazlaMesaiPage._mesai_hazirla", exc)

    def _sayfa_yenile(self):
        self._lbl_ay.setText(f"{_AY[self._ay]} {self._yil}")

        if not self._birim_id:
            self._satirlar = []
            self._tbl.setRowCount(0)
            self._lbl_durum.setText("Birim seçerek başlayın.")
            self._lbl_aciklama.setText(
                "Bu ekran sadece birim bazında çalışır. Önce birim, sonra ay seçin."
            )
            self._btn_pdf.setEnabled(False)
            self._btn_csv.setEnabled(False)
            self._kartlari_guncelle([])
            self._detay_bosalt()
            return

        plan = self._guncel_plan()
        if not plan:
            self._satirlar = []
            self._tbl.setRowCount(0)
            self._lbl_durum.setText(f"{self._birim_adi} için plan bulunamadı")
            self._lbl_aciklama.setText(
                "Seçilen ay için nöbet planı yok. Önce plan oluşturulmalı veya onaylanmış plan açılmalı."
            )
            self._btn_pdf.setEnabled(False)
            self._btn_csv.setEnabled(False)
            self._kartlari_guncelle([])
            self._detay_bosalt()
            return

        self._hesaplari_yukle(plan)

    def _hesaplari_yukle(self, plan: dict):
        try:
            plan_id = str(plan.get("PlanID", ""))
            plan_durum = str(plan.get("Durum", "taslak"))
            sonuc = self._mesai_svc.get_hesaplar(self._birim_id, plan_id, self._yil, self._ay)
            if not sonuc.basarili:
                uyari_goster(self, sonuc.mesaj or "Mesai kayıtları okunamadı.")
                return

            self._satirlar = []
            for kayit in (sonuc.veri or []):
                pid = str(kayit.get("PersonelID", ""))
                calis_dk = int(kayit.get("CalisDakika", 0))
                hedef_dk = int(kayit.get("HedefDakika", 0))
                fazla_dk = int(kayit.get("FazlaDakika", 0))
                toplam_dk = int(kayit.get("ToplamFazlaDakika", 0))
                bayram_ekstra_dk = _bayram_ekstra_dk(calis_dk, hedef_dk, fazla_dk)
                durum, renk = _status_bilgisi(toplam_dk)
                self._satirlar.append({
                    "PersonelID": pid,
                    "AdSoyad": self._personel_ad_map.get(pid, pid),
                    "CalisDakika": calis_dk,
                    "HedefDakika": hedef_dk,
                    "FazlaDakika": fazla_dk,
                    "BayramEkstraDakika": bayram_ekstra_dk,
                    "DevirDakika": int(kayit.get("DevirDakika", 0)),
                    "ToplamFazlaDakika": toplam_dk,
                    "HesapTarihi": str(kayit.get("HesapTarihi", "") or "")[:10],
                    "Durum": durum,
                    "DurumRenk": renk,
                    "PlanDurum": plan_durum,
                })

            self._tbl.setRowCount(0)
            for satir in self._satirlar:
                row = self._tbl.rowCount()
                self._tbl.insertRow(row)

                personel_itm = QTableWidgetItem(satir["AdSoyad"])
                personel_itm.setData(Qt.ItemDataRole.UserRole, satir["PersonelID"])
                self._tbl.setItem(row, 0, personel_itm)
                self._tbl.setItem(row, 1, _it(_fmt_dk(satir["CalisDakika"])))
                self._tbl.setItem(row, 2, _it(_fmt_dk(satir["HedefDakika"])))
                self._tbl.setItem(row, 3, _it(_fmt_dk(satir["FazlaDakika"])))
                self._tbl.setItem(row, 4, _it(_fmt_dk(satir["BayramEkstraDakika"])))
                self._tbl.setItem(row, 5, _it(_fmt_dk(satir["DevirDakika"])))

                toplam_itm = _it(_fmt_dk(satir["ToplamFazlaDakika"]))
                toplam_itm.setForeground(QColor(satir["DurumRenk"]))
                self._tbl.setItem(row, 6, toplam_itm)

                durum_itm = _it(satir["Durum"])
                durum_itm.setForeground(QColor(satir["DurumRenk"]))
                self._tbl.setItem(row, 7, durum_itm)
                self._tbl.setItem(row, 8, _it(satir["HesapTarihi"] or "-"))

            self._lbl_durum.setText(
                f"{self._birim_adi} | {_AY[self._ay]} {self._yil} | Plan durumu: {plan_durum}"
            )
            if self._satirlar:
                self._lbl_aciklama.setText(
                    "Liste hazır. Bu tablo idareye çıktı vermek ve sonraki dönem dağılım kararlarını desteklemek için kullanılır."
                )
            else:
                self._lbl_aciklama.setText(
                    "Bu plan için henüz mesai özeti hazırlanmadı. 'Mesai Saatlerini Hazırla' ile kayıt üretin."
                )

            self._btn_pdf.setEnabled(bool(self._satirlar))
            self._btn_csv.setEnabled(bool(self._satirlar))
            self._kartlari_guncelle(self._satirlar)
            self._detay_bosalt()
        except Exception as exc:
            hata_logla_goster(self, "NobetFazlaMesaiPage._hesaplari_yukle", exc)

    def _kartlari_guncelle(self, satirlar: list[dict]):
        personel_sayi = len(satirlar)
        bildirime_hazir = sum(
            1 for satir in satirlar if satir.get("ToplamFazlaDakika", 0) >= FM_BILDIRIM_ESIK_DK
        )
        toplam_fazla = sum(
            max(0, int(satir.get("ToplamFazlaDakika", 0))) for satir in satirlar
        )
        toplam_eksik = sum(
            abs(min(0, int(satir.get("ToplamFazlaDakika", 0)))) for satir in satirlar
        )

        self._kart_personel._value_label.setText(str(personel_sayi))  # type: ignore[attr-defined]
        self._kart_hazir._value_label.setText(str(bildirime_hazir))  # type: ignore[attr-defined]
        self._kart_toplam._value_label.setText(_fmt_dk(toplam_fazla))  # type: ignore[attr-defined]
        self._kart_eksik._value_label.setText(_fmt_dk(toplam_eksik))  # type: ignore[attr-defined]

    def _detay_bosalt(self):
        self._lbl_detay.setText(
            "Tablodan bir kayıt seçtiğinizde bu personelin mesai dengesi burada özetlenir."
        )

    def _detay_guncelle(self):
        row = self._tbl.currentRow()
        if row < 0 or row >= len(self._satirlar):
            self._detay_bosalt()
            return

        satir = self._satirlar[row]
        self._lbl_detay.setText(
            f"{satir['AdSoyad']} için bu ay çalışılan süre {_fmt_dk(satir['CalisDakika'])}, "
            f"hedef süre {_fmt_dk(satir['HedefDakika'])}. Bu ay farkı {_fmt_dk(satir['FazlaDakika'])}, "
            f"bayram ekstra {_fmt_dk(satir['BayramEkstraDakika'])}, "
            f"önceki devir {_fmt_dk(satir['DevirDakika'])}, toplam denge {_fmt_dk(satir['ToplamFazlaDakika'])}. "
            f"Durum: {satir['Durum']}. Bu bilgi ödeme için değil, idari bildirim ve sonraki dağılım dengesi için referanstır."
        )

    def _rapor_satirlari(self) -> list[list[str]]:
        return [
            [
                satir["AdSoyad"],
                _fmt_dk(satir["CalisDakika"]),
                _fmt_dk(satir["HedefDakika"]),
                _fmt_dk(satir["FazlaDakika"]),
                _fmt_dk(satir["BayramEkstraDakika"]),
                _fmt_dk(satir["DevirDakika"]),
                _fmt_dk(satir["ToplamFazlaDakika"]),
                satir["Durum"],
                satir["HesapTarihi"] or "-",
            ]
            for satir in self._satirlar
        ]

    def _pdf_al(self):
        if not self._satirlar:
            uyari_goster(self, "Önce mesai özeti hazırlayın.")
            return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

            yol, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Kaydet",
                f"FM_Bildirim_{self._birim_adi}_{_AY[self._ay]}_{self._yil}.pdf",
                "PDF (*.pdf)",
            )
            if not yol:
                return

            styles = getSampleStyleSheet()
            baslik_stili = ParagraphStyle(
                "baslik",
                parent=styles["Title"],
                fontSize=13,
                spaceAfter=3,
            )
            alt_stil = ParagraphStyle(
                "alt",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                spaceAfter=6,
            )

            doc = SimpleDocTemplate(
                yol,
                pagesize=landscape(A4),
                leftMargin=1.5 * cm,
                rightMargin=1.5 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
            )

            icerik = []
            icerik.append(
                Paragraph(
                    f"Fazla Mesai Bildirim Özeti - {self._birim_adi} - {_AY[self._ay]} {self._yil}",
                    baslik_stili,
                )
            )
            icerik.append(
                Paragraph(
                    "Bu rapor ödeme belgesi değildir. İdari bilgilendirme ve sonraki nöbet dağılım dengesini desteklemek için hazırlanmıştır.",
                    alt_stil,
                )
            )
            icerik.append(
                Paragraph(
                    f"Rapor tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                    alt_stil,
                )
            )
            icerik.append(Spacer(1, 0.3 * cm))

            veri = [[
                "Personel",
                "Çalışılan",
                "Hedef",
                "Bu Ay Fazla",
                "Bayram Ekstra",
                "Önceki Devir",
                "Toplam",
                "Durum",
                "Son Hesap",
            ]]
            veri.extend(self._rapor_satirlari())

            tablo = Table(
                veri,
                colWidths=[4.2 * cm, 1.9 * cm, 1.9 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.2 * cm, 1.8 * cm],
                repeatRows=1,
            )
            tablo.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            icerik.append(tablo)
            doc.build(icerik)
            bilgi_goster(self, f"PDF kaydedildi: {yol}")
        except Exception as exc:
            hata_logla_goster(self, "NobetFazlaMesaiPage._pdf_al", exc)

    def _csv_al(self):
        if not self._satirlar:
            uyari_goster(self, "Önce mesai özeti hazırlayın.")
            return
        try:
            yol, _ = QFileDialog.getSaveFileName(
                self,
                "CSV Kaydet",
                f"FM_Bildirim_{self._birim_adi}_{_AY[self._ay]}_{self._yil}.csv",
                "CSV (*.csv)",
            )
            if not yol:
                return

            with open(yol, "w", newline="", encoding="utf-8-sig") as dosya:
                yazici = csv.writer(dosya)
                yazici.writerow([
                    "Personel",
                    "Çalışılan",
                    "Hedef",
                    "Bu Ay Fazla",
                    "Bayram Ekstra",
                    "Önceki Devir",
                    "Toplam",
                    "Durum",
                    "Son Hesap",
                ])
                yazici.writerows(self._rapor_satirlari())
            bilgi_goster(self, f"CSV kaydedildi: {yol}")
        except Exception as exc:
            hata_logla_goster(self, "NobetFazlaMesaiPage._csv_al", exc)

    def load_data(self):
        if self._db:
            self._personel_map_yukle()
            self._birimleri_yukle()
