# -*- coding: utf-8 -*-
"""Kalibrasyon bileşenleri: giriş formu + performans bölümleri + sparkline."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtGui import QColor, QPainter, QBrush

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer


_FORM_C = {
    "panel": getattr(DarkTheme, "PANEL", "#191d26"),
    "border": getattr(DarkTheme, "BORDER", "#242938"),
    "text": getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5"),
}

_SPARK_C = {
    "red": getattr(DarkTheme, "DANGER", "#f75f5f"),
    "amber": getattr(DarkTheme, "WARNING", "#f5a623"),
    "green": getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
}


class KalibrasyonGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 8)
        root.setSpacing(8)

        hdr = QWidget()
        hdr.setStyleSheet(f"background:{_FORM_C['panel']};border-radius:6px;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 8, 8, 8)
        hdr_l.setSpacing(0)
        lbl_title = QLabel("Yeni Kalibrasyon Kaydı")
        lbl_title.setStyleSheet(
            f"font-size:12px;font-weight:700;color:{_FORM_C['text']};background:transparent;"
        )
        hdr_l.addWidget(lbl_title)
        hdr_l.addStretch()
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{text_sec};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{_FORM_C['border']};color:{_FORM_C['text']};}}"
        )
        btn_kapat.clicked.connect(self._close_self)
        hdr_l.addWidget(btn_kapat)
        root.addWidget(hdr)

        grp = QGroupBox()
        grp.setStyleSheet(S.get("group", ""))
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_firma = QLineEdit()
        self.txt_firma.setStyleSheet(S["input"])
        self.txt_firma.setPlaceholderText("Kalibrasyon firması")
        self._r(grid, 0, "Firma *", self.txt_firma)

        self.txt_sertifika = QLineEdit()
        self.txt_sertifika.setStyleSheet(S["input"])
        self.txt_sertifika.setPlaceholderText("Sertifika numarası")
        self._r(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True)
        self.dt_yapilan.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_yapilan.setStyleSheet(S["date"])
        self._r(grid, 2, "Yapılan Tarih *", self.dt_yapilan)

        self.txt_gecerlilik = QLineEdit()
        self.txt_gecerlilik.setStyleSheet(S["input"])
        self.txt_gecerlilik.setPlaceholderText("Örn: 1 Yıl, 2 Yıl")
        self._r(grid, 3, "Geçerlilik Süresi", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True)
        self.dt_bitis.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_bitis.setStyleSheet(S["date"])
        self._r(grid, 4, "Bitiş Tarihi *", self.dt_bitis)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._r(grid, 5, "Durum", self.cmb_durum)

        self.txt_dosya = QLineEdit()
        self.txt_dosya.setStyleSheet(S["input"])
        self.txt_dosya.setPlaceholderText("Dosya yolu veya link")
        self._r(grid, 6, "Dosya / Link", self.txt_dosya)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(72)
        self.txt_aciklama.setPlaceholderText("Ek açıklama (isteğe bağlı)")
        self._r(grid, 7, "Açıklama", self.txt_aciklama)

        root.addWidget(grp)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S.get("btn_refresh", ""))
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S.get("action_btn", S.get("btn_primary", "")))
        try:
            IconRenderer.set_button_icon(
                btn_kaydet, "save", color=DarkTheme.BTN_PRIMARY_TEXT, size=14
            )
        except Exception:
            pass
        btn_kaydet.clicked.connect(self._save)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(btn_kaydet, "cihaz.write")
        btns.addWidget(btn_kaydet)
        root.addLayout(btns)

    def _r(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _close_self(self):
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, "_close_form"):
                parent._close_form()
                return
            parent = parent.parentWidget()

    def _save(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Kalibrasyon Kaydetme"
        ):
            return
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        if not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return

        firma = self.txt_firma.text().strip()
        if not firma:
            QMessageBox.warning(self, "Uyarı", "Firma adı zorunludur.")
            return

        kalid = f"{self._cihaz_id}-KL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Kalid": kalid,
            "Cihazid": self._cihaz_id,
            "Firma": firma,
            "SertifikaNo": self.txt_sertifika.text().strip(),
            "YapilanTarih": self.dt_yapilan.date().toString("yyyy-MM-dd"),
            "Gecerlilik": self.txt_gecerlilik.text().strip(),
            "BitisTarihi": self.dt_bitis.date().toString("yyyy-MM-dd"),
            "Durum": self.cmb_durum.currentText().strip(),
            "Dosya": self.txt_dosya.text().strip(),
            "Aciklama": self.txt_aciklama.toPlainText().strip(),
        }
        try:
            RepositoryRegistry(self._db).get("Kalibrasyon").insert(data)
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Kalibrasyon kaydı kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _clear(self):
        for w in [self.txt_firma, self.txt_sertifika, self.txt_gecerlilik, self.txt_dosya]:
            w.clear()
        self.txt_aciklama.clear()
        self.dt_yapilan.setDate(QDate.currentDate())
        self.dt_bitis.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)


class KalSparkline(QWidget):
    def __init__(self, values: List[int], parent=None):
        super().__init__(parent)
        self._values = values or [0] * 12
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height, count = self.width(), self.height(), len(self._values)
        if count == 0:
            return
        max_v = max(self._values) if any(self._values) else 1
        bar_w = max(2, (width - (count - 1) * 2) // count)
        for i, value in enumerate(self._values):
            bar_h = max(3, int((value / max_v) * (height - 4))) if max_v else 3
            x = i * (bar_w + 2)
            y = height - bar_h
            color = QColor(_SPARK_C["red"] if value > max_v * 0.7 else _SPARK_C["amber"] if value > max_v * 0.4 else _SPARK_C["green"])
            color.setAlpha(180)
            painter.fillRect(x, y, bar_w, bar_h, QBrush(color))
        painter.end()


def load_cihaz_marka_map(db) -> tuple[Dict[str, str], Dict[str, set]]:
    cihaz_marka_map: Dict[str, str] = {}
    tum_markalar: Dict[str, set] = defaultdict(set)
    if not db:
        return cihaz_marka_map, tum_markalar

    try:
        repo = RepositoryRegistry(db).get("Cihazlar")
        for cihaz in (repo.get_all() or []):
            cihaz_id = str(cihaz.get("Cihazid", "") or "").strip()
            marka = str(cihaz.get("Marka", "") or "").strip()
            if cihaz_id and marka:
                cihaz_marka_map[cihaz_id] = marka
                tum_markalar[marka].add(cihaz_id)
    except Exception as exc:
        logger.error(f"Cihazlar tablosu yüklenemedi: {exc}")
    return cihaz_marka_map, tum_markalar


def compute_marka_stats(rows, cihaz_marka_map, tum_markalar):
    stats: Dict[str, Dict] = {}
    now = datetime.now()
    bugun = now.date()
    limit = bugun + timedelta(days=30)

    for row in rows:
        cihaz_id = str(row.get("Cihazid", "") or "").strip()
        if cihaz_id not in cihaz_marka_map:
            continue

        marka = cihaz_marka_map[cihaz_id]
        if marka not in stats:
            stats[marka] = {
                "marka": marka,
                "cihazlar": set(),
                "toplam": 0,
                "gecerli": 0,
                "gecersiz": 0,
                "yaklasan": 0,
                "ay_trend": defaultdict(int),
            }

        stat = stats[marka]
        stat["cihazlar"].add(cihaz_id)
        stat["toplam"] += 1

        durum = row.get("Durum", "")
        if durum in ("Gecerli", "Geçerli"):
            stat["gecerli"] += 1
        elif durum in ("Gecersiz", "Geçersiz"):
            stat["gecersiz"] += 1

        bitis = row.get("BitisTarihi", "")
        if bitis and len(bitis) >= 10:
            try:
                bitis_tarih = datetime.strptime(bitis[:10], "%Y-%m-%d").date()
                if bugun <= bitis_tarih <= limit:
                    stat["yaklasan"] += 1
            except ValueError:
                pass

        yapilan = row.get("YapilanTarih", "")
        if yapilan and len(yapilan) >= 7:
            try:
                yapilan_ay = datetime.strptime(yapilan[:7], "%Y-%m")
                months_ago = (now.year - yapilan_ay.year) * 12 + (now.month - yapilan_ay.month)
                if 0 <= months_ago <= 11:
                    stat["ay_trend"][11 - months_ago] += 1
            except ValueError:
                pass

    marka_data = []
    for stat in stats.values():
        trend = [stat["ay_trend"].get(i, 0) for i in range(12)]
        oran = round(stat["gecerli"] / stat["toplam"] * 100) if stat["toplam"] else 0
        marka_data.append({
            **stat,
            "cihaz_sayi": len(stat["cihazlar"]),
            "trend": trend,
            "oran": oran,
        })
    marka_data.sort(key=lambda x: x["toplam"], reverse=True)

    planlanan = set(stats.keys())
    kalsiz = [
        {"marka": marka, "cihaz_sayi": len(ids), "cihazlar": sorted(ids)}
        for marka, ids in tum_markalar.items() if marka not in planlanan
    ]
    kalsiz.sort(key=lambda x: x["marka"])

    return marka_data, kalsiz


def build_single_cihaz_stats(rows: List[Dict], colors: Dict[str, str]) -> QWidget:
    gecerli = sum(1 for row in rows if row.get("Durum", "") in ("Gecerli", "Geçerli"))
    gecersiz = sum(1 for row in rows if row.get("Durum", "") in ("Gecersiz", "Geçersiz"))
    toplam = len(rows)

    bugun = datetime.now().date()
    limit = bugun + timedelta(days=30)
    yaklasan = sum(
        1 for row in rows
        if row.get("BitisTarihi", "") and len(row.get("BitisTarihi", "")) >= 10
        and bugun <= datetime.strptime(row["BitisTarihi"][:10], "%Y-%m-%d").date() <= limit
    )
    gecersiz_pct = f"%{round(gecersiz / toplam * 100)}" if toplam else "—"

    container = QWidget()
    container.setStyleSheet("background:transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    for title, value, color in [
        ("Toplam", str(toplam), colors["accent"]),
        ("Geçerli", str(gecerli), colors["green"]),
        ("Geçersiz", str(gecersiz), colors["red"]),
        ("Yaklaşan Bitiş", str(yaklasan), colors["amber"]),
        ("Geçersizlik", gecersiz_pct, colors["red"]),
    ]:
        card = QWidget()
        card.setStyleSheet(
            f"background:{colors['panel']};border:1px solid {colors['border']};border-radius:6px;"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(10, 8, 10, 8)
        card_l.setSpacing(2)

        label = QLabel(title.upper())
        label.setStyleSheet(
            f"font-size:9px;font-weight:600;letter-spacing:0.06em;"
            f"color:{colors['muted']};background:transparent;"
        )
        number = QLabel(value)
        number.setStyleSheet(
            f"font-size:16px;font-weight:700;color:{color};background:transparent;"
        )
        card_l.addWidget(label)
        card_l.addWidget(number)
        layout.addWidget(card, 1)

    return container


def _bar_row(label: str, value: int, pct: int, fill_color: str, colors: Dict[str, str]) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background:transparent;")
    row_l = QHBoxLayout(row)
    row_l.setContentsMargins(0, 0, 0, 0)
    row_l.setSpacing(6)

    lbl = QLabel(label)
    lbl.setFixedWidth(58)
    lbl.setStyleSheet(f"font-size:10px;color:{colors['muted']};background:transparent;")
    row_l.addWidget(lbl)

    bar_bg = QWidget()
    bar_bg.setFixedHeight(6)
    bar_bg.setStyleSheet(f"background:{colors['border']};border-radius:3px;")
    bar_bg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    bar_fill = QWidget(bar_bg)
    bar_fill.setFixedHeight(6)
    bar_fill.setStyleSheet(f"background:{fill_color};border-radius:3px;")
    bar_fill.setFixedWidth(max(4, int(pct * 1.5)))
    row_l.addWidget(bar_bg)

    count = QLabel(str(value))
    count.setFixedWidth(24)
    count.setAlignment(Qt.AlignRight)
    count.setStyleSheet(
        f"font-size:10px;font-weight:600;color:{fill_color};background:transparent;"
    )
    row_l.addWidget(count)

    return row


def build_marka_grid(marka_data: List[Dict], colors: Dict[str, str]) -> QWidget:
    if not marka_data:
        empty = QLabel("Eşleşen marka verisi bulunamadı.")
        empty.setStyleSheet(f"color:{colors['muted']};font-size:12px;padding:12px;")
        return empty

    container = QWidget()
    container.setStyleSheet("background:transparent;")
    grid = QGridLayout(container)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(10)

    max_toplam = max((d["toplam"] for d in marka_data), default=1)
    cols = 3

    for idx, data in enumerate(marka_data):
        row_i, col_i = divmod(idx, cols)

        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{colors['panel']};border:1px solid {colors['border']};border-radius:8px;}}"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(14, 12, 14, 12)
        card_l.setSpacing(8)

        hdr = QHBoxLayout()
        marka_lbl = QLabel(data["marka"])
        marka_lbl.setStyleSheet(
            f"font-size:13px;font-weight:700;color:{colors['text']};background:transparent;"
        )
        hdr.addWidget(marka_lbl)
        hdr.addStretch()

        cihaz_sayi = QLabel(f"{data['cihaz_sayi']} cihaz")
        cihaz_sayi.setStyleSheet(
            f"font-size:10px;color:{colors['muted']};"
            f"background:{colors['border']};border-radius:4px;padding:1px 6px;"
        )
        hdr.addWidget(cihaz_sayi)

        oran_color = colors["green"] if data["oran"] >= 80 else colors["amber"] if data["oran"] >= 50 else colors["red"]
        oran_badge = QLabel(f"%{data['oran']} geçerli")
        oran_badge.setStyleSheet(
            f"font-size:10px;font-weight:600;color:{oran_color};"
            f"background:{oran_color}22;border-radius:4px;padding:1px 6px;"
        )
        hdr.addWidget(oran_badge)

        if data["yaklasan"] > 0:
            yaklasan_badge = QLabel(f"{data['yaklasan']} yaklaşan")
            yaklasan_badge.setStyleSheet(
                f"font-size:10px;font-weight:600;color:{colors['amber']};"
                f"background:{colors['amber']}22;border-radius:4px;padding:1px 6px;"
            )
            hdr.addWidget(yaklasan_badge)

        card_l.addLayout(hdr)

        for label_txt, val, color in [
            ("Toplam", data["toplam"], colors["accent"]),
            ("Geçerli", data["gecerli"], colors["green"]),
            ("Geçersiz", data["gecersiz"], colors["red"]),
        ]:
            bar_pct = int((val / max_toplam) * 100) if max_toplam else 0
            card_l.addWidget(_bar_row(label_txt, val, bar_pct, color, colors))

        spark = KalSparkline(data["trend"], parent=card)
        spark.setFixedHeight(32)
        card_l.addWidget(spark)

        grid.addWidget(card, row_i, col_i)

    remainder = len(marka_data) % cols
    if remainder:
        for c in range(remainder, cols):
            placeholder = QWidget()
            placeholder.setStyleSheet("background:transparent;")
            grid.addWidget(placeholder, len(marka_data) // cols, c)

    return container


def build_no_kal_card(kalsiz: List[Dict], colors: Dict[str, str]) -> QWidget:
    card = QWidget()
    card.setStyleSheet(
        f"background:{colors['panel']};"
        f"border:1px solid {colors['amber']}44;"
        f"border-left:3px solid {colors['amber']};"
        f"border-radius:8px;"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(10)

    hdr = QHBoxLayout()
    title = QLabel("Kalibrasyonu Olmayan Markalar")
    title.setStyleSheet(
        f"font-size:12px;font-weight:700;color:{colors['amber']};background:transparent;"
    )
    hdr.addWidget(title)
    hdr.addStretch()

    count = QLabel(f"{len(kalsiz)} marka")
    count.setStyleSheet(
        f"font-size:11px;font-weight:600;color:{colors['amber']};"
        f"background:{colors['amber']}22;border-radius:4px;padding:2px 8px;"
    )
    hdr.addWidget(count)
    layout.addLayout(hdr)

    wrap = QWidget()
    wrap.setStyleSheet("background:transparent;")
    wrap_l = QHBoxLayout(wrap)
    wrap_l.setContentsMargins(0, 0, 0, 0)
    wrap_l.setSpacing(8)

    for data in kalsiz:
        chip = QWidget()
        chip.setStyleSheet(
            f"background:{colors['surface']};border:1px solid {colors['border']};border-radius:6px;"
        )
        chip_l = QVBoxLayout(chip)
        chip_l.setContentsMargins(10, 6, 10, 6)
        chip_l.setSpacing(2)

        marka = QLabel(data["marka"])
        marka.setStyleSheet(
            f"font-size:12px;font-weight:600;color:{colors['text']};background:transparent;"
        )
        chip_l.addWidget(marka)

        cihaz = QLabel(f"{data['cihaz_sayi']} cihaz")
        cihaz.setStyleSheet(f"font-size:10px;color:{colors['muted']};background:transparent;")
        chip_l.addWidget(cihaz)

        wrap_l.addWidget(chip)

    wrap_l.addStretch()
    layout.addWidget(wrap)
    return card


def build_trend_chart(rows: List[Dict], colors: Dict[str, str]) -> QWidget:
    now = datetime.now()
    ay_sayim: Dict[int, int] = {}
    ay_etiket: Dict[int, str] = {}
    ay_isimleri = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

    for i in range(12):
        ay_idx = (now.month - 1 - i) % 12
        konum = 11 - i
        ay_sayim[konum] = 0
        ay_etiket[konum] = ay_isimleri[ay_idx]

    for row in rows:
        yapilan = row.get("YapilanTarih", "")
        if yapilan and len(yapilan) >= 7:
            try:
                dt = datetime.strptime(yapilan[:7], "%Y-%m")
                months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
                if 0 <= months_ago <= 11:
                    ay_sayim[11 - months_ago] += 1
            except ValueError:
                pass

    degerler = [ay_sayim[i] for i in range(12)]
    etiketler = [ay_etiket[i] for i in range(12)]
    max_val = max(degerler) if any(degerler) else 1

    container = QWidget()
    container.setStyleSheet(
        f"background:{colors['panel']};border:1px solid {colors['border']};border-radius:8px;"
    )
    cl = QVBoxLayout(container)
    cl.setContentsMargins(16, 14, 16, 14)
    cl.setSpacing(6)

    bar_row = QHBoxLayout()
    bar_row.setSpacing(4)
    for val in degerler:
        col = QVBoxLayout()
        col.setSpacing(2)
        col.setAlignment(Qt.AlignBottom)

        val_lbl = QLabel(str(val) if val else "")
        val_lbl.setAlignment(Qt.AlignHCenter)
        val_lbl.setStyleSheet(f"font-size:9px;color:{colors['muted']};background:transparent;")
        col.addWidget(val_lbl)

        bar_color = colors["red"] if val > max_val * 0.7 else colors["amber"] if val > max_val * 0.4 else colors["green"]
        bar_h = max(4, int((val / max_val) * 60)) if max_val else 4
        bar = QWidget()
        bar.setFixedSize(16, bar_h)
        bar.setStyleSheet(f"background:{bar_color};border-radius:3px 3px 0 0;")
        col.addWidget(bar, 0, Qt.AlignHCenter)
        bar_row.addLayout(col)

    cl.addLayout(bar_row)

    lbl_row = QHBoxLayout()
    lbl_row.setSpacing(4)
    for etiket in etiketler:
        lbl = QLabel(etiket)
        lbl.setAlignment(Qt.AlignHCenter)
        lbl.setStyleSheet(f"font-size:9px;color:{colors['muted']};background:transparent;")
        lbl_row.addWidget(lbl)
    cl.addLayout(lbl_row)

    return container


def build_expiry_list(rows: List[Dict], colors: Dict[str, str], bitis_rengi_fn) -> QWidget:
    bugun = datetime.now().date()
    limit = bugun + timedelta(days=90)
    ilgili = []

    for row in rows:
        bitis = row.get("BitisTarihi", "")
        if bitis and len(bitis) >= 10:
            try:
                bitis_tarih = datetime.strptime(bitis[:10], "%Y-%m-%d").date()
                if bitis_tarih <= limit:
                    ilgili.append((bitis_tarih, row))
            except ValueError:
                pass

    ilgili.sort(key=lambda x: x[0])

    container = QWidget()
    container.setStyleSheet("background:transparent;")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    if not ilgili:
        lbl = QLabel("Yaklaşan veya geçmiş bitiş tarihi bulunmuyor.")
        lbl.setStyleSheet(f"color:{colors['muted']};font-size:12px;padding:12px;")
        layout.addWidget(lbl)
        return container

    for bitis_tarih, row in ilgili[:20]:
        bitis_raw = row.get("BitisTarihi", "")
        bitis_c = bitis_rengi_fn(bitis_raw)
        gecti = bitis_tarih < bugun
        kalan = (bitis_tarih - bugun).days

        row_w = QWidget()
        row_w.setStyleSheet(
            f"background:{colors['panel']};border:1px solid {colors['border']};"
            f"border-left:3px solid {bitis_c};border-radius:6px;"
        )
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(12, 8, 12, 8)
        row_l.setSpacing(12)

        chip = QLabel(str(row.get("Cihazid", "")) or "—")
        chip.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{colors['accent']};"
            f"background:{colors['accent']}22;border-radius:4px;padding:2px 8px;"
        )
        chip.setFixedWidth(90)
        row_l.addWidget(chip)

        firma = QLabel(str(row.get("Firma", "")) or "—")
        firma.setStyleSheet(f"font-size:12px;color:{colors['text']};background:transparent;")
        firma.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row_l.addWidget(firma)

        sertifika = QLabel(str(row.get("SertifikaNo", "")) or "—")
        sertifika.setStyleSheet(f"font-size:10px;color:{colors['muted']};background:transparent;")
        sertifika.setFixedWidth(90)
        row_l.addWidget(sertifika)

        zaman_str = (
            f"{to_ui_date(bitis_raw, '—')}  ({abs(kalan)}g geçti)"
            if gecti else
            f"{to_ui_date(bitis_raw, '—')}  ({kalan}g kaldı)"
        )
        zaman_lbl = QLabel(zaman_str)
        zaman_lbl.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{bitis_c};background:transparent;"
        )
        row_l.addWidget(zaman_lbl)
        layout.addWidget(row_w)

    return container
