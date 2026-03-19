# -*- coding: utf-8 -*-
"""
Ana Gösterge Paneli (Dashboard) — v3 Açık Tema
"""
import calendar
from ui.styles.icons import Icons, IconColors
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QCursor, QColor, QFont

from core.logger import logger
from core.date_utils import parse_date, to_db_date
from core.log_manager import LogStatistics
from core.paths import DB_PATH
from ui.theme_manager import ThemeManager
from ui.styles.colors import Colors, DarkTheme
from ui.styles.components import STYLES

S = STYLES

# ─── Renk sabitleri (açık tema) ──────────────────────────────────
BG       = "page"
CARD_BG  = "panel"
BORDER   = "primary"
TXT      = "primary"
TXT2     = DarkTheme.TEXT_SECONDARY
TXT_DIM  = "muted"
ACCENT   = "accent"
SUCCESS  = "ok"
WARN     = "warn"
DANGER   = "err"


# ══════════════════════════════════════════════════════════════
#  WORKER
# ══════════════════════════════════════════════════════════════
class DashboardWorker(QThread):
    data_ready = Signal(dict)

    def __init__(self, db_path):
        super().__init__()
        self._db_path = db_path

    def run(self):
        data = {}
        db = None
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_dashboard_service
            db = SQLiteManager(db_path=self._db_path)
            svc = get_dashboard_service(db)
            data.update(svc.get_dashboard_data())

            log_stats = LogStatistics.get_log_stats()
            data['hata_log_satir'] = log_stats.get('errors.log', {}).get('lines', 0)
            data['toplam_log_boyut_mb'] = LogStatistics.get_total_log_size()

            self.data_ready.emit(data)
        except Exception as e:
            logger.error(f"Dashboard worker hatası: {e}")
            self.data_ready.emit({})
        finally:
            if db:
                db.close()

    # Kod tekrarını önlemek için DashboardService kullanılmaktadır.


# ══════════════════════════════════════════════════════════════
#  STAT CARD — Yeni, temiz açık tema kartı
# ══════════════════════════════════════════════════════════════
class StatCard(QFrame):
    """
    Dashboard için tıklanabilir istatistik kartı — açık tema v3.
    Eski QGroupBox tabanlı StatCard ile tam API uyumluluğu korundu.
    """
    clicked = Signal()

    # Kart vurgu rengi sabitleri (kategori bazlı)
    _ACCENT_COLORS = {
        "blue":   ("#eff6ff", "#2563eb", "#dbeafe"),
        "green":  ("#f0fdf4", "#16a34a", "#dcfce7"),
        "orange": ("#fff7ed", "#ea580c", "#ffedd5"),
        "red":    ("#fef2f2", "#dc2626", "#fee2e2"),
        "purple": ("#faf5ff", "#9333ea", "#f3e8ff"),
        "amber":  ("#fffbeb", "#d97706", "#fef3c7"),
        "slate":  ("#f8fafc", "#475569", "#f1f5f9"),
    }

    def __init__(self, title, icon, parent=None, accent="blue"):
        super().__init__(parent)
        self._title  = title
        self._icon   = icon
        self._accent = accent
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumSize(180, 100)
        self._build_ui()
        self._apply_style(hover=False)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        # Üst satır: ikon + başlık
        top = QHBoxLayout()
        top.setSpacing(8)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(32, 32)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        _icon_map = {
            "alert_triangle": "alert_triangle", "plus_circle": "plus_circle", "wrench": "wrench",
            "crosshair": "crosshair",       "calendar": "calendar",     "file_text": "file_text",
            "user": "user",            "users": "users",         "calendar_check": "calendar_check",
            "hospital": "hospital",        "activity": "activity",      "bar_chart": "bar_chart",
        }
        _, icon_color, _ = self._ACCENT_COLORS.get(self._accent, self._ACCENT_COLORS["blue"])
        _icon_name = _icon_map.get(self._icon, "info")
        try:
            _pm = Icons.pixmap(_icon_name, size=16, color=icon_color)
            self._icon_lbl.setPixmap(_pm)
        except Exception:
            self._icon_lbl.setText(self._icon)

        self._title_lbl = QLabel(self._title)
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {TXT2}; background: transparent;"
        )

        top.addWidget(self._icon_lbl)
        top.addWidget(self._title_lbl, 1)
        lay.addLayout(top)

        # Değer
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(
            f"font-size: 30px; font-weight: 800; color: {TXT}; background: transparent;"
        )
        lay.addWidget(self.value_label)

        # Açıklama
        self.desc_label = QLabel("Yükleniyor...")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
            f"font-size: 11px; color: {TXT_DIM}; background: transparent;"
        )
        lay.addWidget(self.desc_label)

        # Gölge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)

    def _apply_style(self, hover: bool):
        _, icon_color, border_color = self._ACCENT_COLORS.get(
            self._accent, self._ACCENT_COLORS["blue"]
        )
        if hover:
            self.setStyleSheet(
                f"QFrame {{"
                f"  background-color: {CARD_BG};"
                f"  border: 1.5px solid {icon_color};"
                f"  border-radius: 12px;"
                f"}}"
            )
            # İkon arka plan vurgula
            bg_color, _, _ = self._ACCENT_COLORS.get(self._accent, self._ACCENT_COLORS["blue"])
            self._icon_lbl.setStyleSheet(
                f"background-color: {bg_color}; border-radius: 8px;"
            )
        else:
            self.setStyleSheet(
                f"QFrame {{"
                f"  background-color: {CARD_BG};"
                f"  border: 1px solid {BORDER};"
                f"  border-radius: 12px;"
                f"}}"
            )
            bg_color, _, _ = self._ACCENT_COLORS.get(self._accent, self._ACCENT_COLORS["blue"])
            self._icon_lbl.setStyleSheet(
                f"background-color: {bg_color}; border-radius: 8px;"
            )

    def set_data(self, value, description):
        if isinstance(value, int) and value == -1:
            self.value_label.setText("!")
            self.value_label.setStyleSheet(
                f"font-size: 28px; font-weight: 800; color: {DANGER}; background: transparent;"
            )
        else:
            self.value_label.setText(str(value))
            _, icon_color, _ = self._ACCENT_COLORS.get(
                self._accent, self._ACCENT_COLORS["blue"]
            )
            self.value_label.setStyleSheet(
                f"font-size: 30px; font-weight: 800; color: {TXT}; background: transparent;"
            )
        self.desc_label.setText(description)

    def enterEvent(self, event):
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(hover=False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)


# ══════════════════════════════════════════════════════════════
#  BÖLÜM BAŞLIĞI
# ══════════════════════════════════════════════════════════════
def _section_header(title: str, icon: str = "") -> QWidget:
    from PySide6.QtWidgets import QHBoxLayout
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 6, 0, 2)
    row.setSpacing(6)
    if icon:
        from ui.styles.icons import Icons, IconColors
        lbl_icon = QLabel()
        lbl_icon.setPixmap(Icons.pixmap(icon, size=14, color=TXT2))
        lbl_icon.setFixedSize(14, 14)
        row.addWidget(lbl_icon)
    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"font-size: 12px; font-weight: 700; color: {TXT2}; background: transparent;"
        f" text-transform: uppercase;"
    )
    row.addWidget(lbl)
    row.addStretch()
    return container


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: {}; background: {}; max-height: 1px;".format(BORDER, BORDER))
    return line


# ══════════════════════════════════════════════════════════════
#  DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════
class DashboardPage(QWidget):
    """Ana karşılama sayfası — açık tema v3."""
    open_page_requested = Signal(str, str, dict)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db     = db
        self._worker = None
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        self.setObjectName("dashboardPage")
        self.setStyleSheet("QWidget#dashboardPage {{ background-color: {}; }}".format(BG))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 16)
        main_layout.setSpacing(12)

        # ── Başlık Satırı ──────────────────────────────────────
        header = QHBoxLayout()

        greet_col = QVBoxLayout()
        greet_col.setSpacing(2)
        title_lbl = QLabel("Genel Bakış")
        title_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {TXT}; background: transparent;"
        )
        _now = datetime.now()
        today_lbl = QLabel(f"{_now.day} {_now.strftime('%B %Y, %A')}")
        today_lbl.setStyleSheet(
            f"font-size: 12px; color: {TXT_DIM}; background: transparent;"
        )
        greet_col.addWidget(title_lbl)
        greet_col.addWidget(today_lbl)

        self.refresh_button = QPushButton("  Yenile")
        try:
            self.refresh_button.setIcon(Icons.get("refresh", size=14, color=ACCENT))
            self.refresh_button.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self.refresh_button.setFixedHeight(34)
        self.refresh_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_button.setStyleSheet(str(S.get("btn_refresh") or ""))
        self.refresh_button.clicked.connect(self.load_data)

        header.addLayout(greet_col)
        header.addStretch()
        header.addWidget(self.refresh_button)
        main_layout.addLayout(header)

        # ── Scroll Area ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        content = QWidget()
        content.setProperty("bg-role", "panel")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 20)
        content_layout.setSpacing(16)

        # ── FHSZ Uyarı Çerçevesi ──────────────────────────────
        self.fhsz_reminder_frame = self._create_reminder_box(
            "FHSZ Doldurma Hatırlatması",
            "Bugün 15'i! Bu ay FHSZ cetvelini doldurmayı unutmayın."
        )
        content_layout.addWidget(self.fhsz_reminder_frame)

        # ═══ CİHAZ BÖLÜMÜ ════════════════════════════════════
        content_layout.addWidget(_section_header("Cihaz",       "cpu"))

        cihaz_grid = QGridLayout()
        cihaz_grid.setSpacing(12)

        self.card_acik_arizalar = StatCard("Açık Arızalar", "alert_triangle", accent="red")
        self.card_acik_arizalar.clicked.connect(
            lambda: self.open_page_requested.emit("CİHAZ", "Arıza Listesi", {"Filtre": "Açık"}))
        cihaz_grid.addWidget(self.card_acik_arizalar, 0, 0)

        self.card_yeni_arizalar = StatCard("Yeni Arızalar (7 Gün)", "plus_circle", accent="orange")
        self.card_yeni_arizalar.clicked.connect(
            lambda: self.open_page_requested.emit("CİHAZ", "Arıza Listesi", {}))
        cihaz_grid.addWidget(self.card_yeni_arizalar, 0, 1)

        self.card_aylik_bakim = StatCard("Bu Ay Bakım Planı", "wrench", accent="amber")
        self.card_aylik_bakim.clicked.connect(
            lambda: self.open_page_requested.emit("CİHAZ", "Teknik Hizmetler", {}))
        cihaz_grid.addWidget(self.card_aylik_bakim, 0, 2)

        self.card_aylik_kalibrasyon = StatCard("Bu Ay Kalibrasyon", "calendar", accent="blue")
        self.card_aylik_kalibrasyon.clicked.connect(
            lambda: self.open_page_requested.emit("CİHAZ", "Kalibrasyon Takip", {}))
        cihaz_grid.addWidget(self.card_aylik_kalibrasyon, 0, 3)

        self.card_yaklasan_ndk = StatCard("Yaklaşan NDK (6 Ay)", "crosshair", accent="purple")
        self.card_yaklasan_ndk.clicked.connect(
            lambda: self.open_page_requested.emit("CİHAZ", "Cihaz Listesi", {"Filtre": "YaklasanNDK"}))
        cihaz_grid.addWidget(self.card_yaklasan_ndk, 1, 0)

        content_layout.addLayout(cihaz_grid)
        content_layout.addWidget(_divider())

        # ═══ PERSONEL BÖLÜMÜ ══════════════════════════════════
        content_layout.addWidget(_section_header("Personel",    "users"))

        personel_grid = QGridLayout()
        personel_grid.setSpacing(12)

        self.card_aktif_personel = StatCard("Aktif Personel", "users", accent="green")
        self.card_aktif_personel.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "Personel Listesi", {"Filtre": "Aktif"}))
        personel_grid.addWidget(self.card_aktif_personel, 0, 0)

        self.card_aylik_izinli = StatCard("Bu Ay İzinli Personel", "calendar_check", accent="amber")
        self.card_aylik_izinli.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "İzin Takip", {}))
        personel_grid.addWidget(self.card_aylik_izinli, 0, 1)

        content_layout.addLayout(personel_grid)
        content_layout.addWidget(_divider())

        # ═══ SAĞLIK TAKİBİ BÖLÜMÜ ════════════════════════════
        content_layout.addWidget(_section_header("Personel Sağlık Takibi", "activity"))

        saglik_grid = QGridLayout()
        saglik_grid.setSpacing(12)

        self.card_yaklasan_saglik = StatCard("Yaklaşan Muayeneler (90 Gün)", "activity", accent="blue")
        self.card_yaklasan_saglik.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "Sağlık Takip", {"Filtre": "Yaklasan"}))
        saglik_grid.addWidget(self.card_yaklasan_saglik, 0, 0)

        self.card_gecmis_saglik = StatCard("Vadesi Geçmiş Muayeneler", "calendar", accent="red")
        self.card_gecmis_saglik.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "Sağlık Takip", {"Filtre": "Gecmis"}))
        saglik_grid.addWidget(self.card_gecmis_saglik, 0, 1)

        content_layout.addLayout(saglik_grid)
        content_layout.addWidget(_divider())

        # ═══ RKE BÖLÜMÜ ══════════════════════════════════════
        content_layout.addWidget(_section_header("RKE",         "shield"))

        rke_grid = QGridLayout()
        rke_grid.setSpacing(12)

        self.card_yaklasan_rke = StatCard("Yaklaşan RKE Muayeneleri", "clipboard_list", accent="purple")
        self.card_yaklasan_rke.clicked.connect(
            lambda: self.open_page_requested.emit("RKE", "RKE Muayene", {"Filtre": "Yaklasan"}))
        rke_grid.addWidget(self.card_yaklasan_rke, 0, 0)
        rke_grid.addWidget(QWidget(), 0, 1)  # boşluk

        content_layout.addLayout(rke_grid)
        content_layout.addWidget(_divider())

        # ═══ SİSTEM SAĞLIĞI BÖLÜMÜ ═══════════════════════════
        content_layout.addWidget(_section_header("Sistem Sağlığı", "settings"))

        sistem_grid = QGridLayout()
        sistem_grid.setSpacing(12)

        self.card_hata_log = StatCard("Kritik Hata Logları", "file_text", accent="red")
        self.card_hata_log.clicked.connect(
            lambda: self.open_page_requested.emit(
                "YÖNETİCİ İŞLEMLERİ", "Log Görüntüleyici",
                {"Dosya": "errors.log", "Seviye": "ERROR"}))
        sistem_grid.addWidget(self.card_hata_log, 0, 0)

        self.card_log_boyutu = StatCard("Toplam Log Boyutu", "bar_chart", accent="slate")
        self.card_log_boyutu.clicked.connect(
            lambda: self.open_page_requested.emit("YÖNETİCİ İŞLEMLERİ", "Log Görüntüleyici", {}))
        sistem_grid.addWidget(self.card_log_boyutu, 0, 1)

        content_layout.addLayout(sistem_grid)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

    # ── Uyarı Çerçevesi ───────────────────────────────────────
    def _create_reminder_box(self, title: str, text: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {{
                background-color: #fffbeb;
                border: 1.5px solid #fde68a;
                border-radius: 10px;
                padding: 2px;
            }}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        title_lbl = QLabel(f"  {title}")
        title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {WARN}; background: transparent;"
        )
        body_lbl = QLabel(text)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet(
            f"font-size: 12px; color: {TXT2}; background: transparent;"
        )
        lay.addWidget(title_lbl)
        lay.addWidget(body_lbl)
        frame.setVisible(False)
        return frame

    # ── Veri yükle ────────────────────────────────────────────
    def load_data(self):
        if self._worker and self._worker.isRunning():
            return
        logger.info("Dashboard verileri yükleniyor...")
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("  Yükleniyor...")

        db_path = getattr(self._db, "db_path", DB_PATH)
        self._worker = DashboardWorker(db_path)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_data_ready(self, data: dict):
        # FHSZ hatırlatma
        self.fhsz_reminder_frame.setVisible(datetime.now().day == 15)

        # Cihaz
        self.card_acik_arizalar.set_data(
            data.get('acik_arizalar', 0), "Çözülmeyi bekleyen arıza kayıtları")
        self.card_yeni_arizalar.set_data(
            data.get('yeni_arizalar', 0), "Son 7 günde açılan kayıtlar")
        self.card_aylik_bakim.set_data(
            data.get('aylik_bakim', 0), "Bu ay planlanan bakımlar")
        self.card_aylik_kalibrasyon.set_data(
            data.get('aylik_kalibrasyon', 0), "Bu ay tamamlanan kalibrasyonlar")
        self.card_yaklasan_ndk.set_data(
            data.get('yaklasan_ndk', 0), "6 ay içinde dolacak lisanslar")

        # Personel
        self.card_aktif_personel.set_data(
            data.get('aktif_personel', 0), "Sistemde aktif görünen personel")
        yillik = data.get("aylik_izinli_yillik", 0)
        sua    = data.get("aylik_izinli_sua", 0)
        rapor  = data.get("aylik_izinli_rapor", 0)
        diger  = data.get("aylik_izinli_diger", 0)
        izin_desc = f"Yıllık: {yillik}  ·  Şua: {sua}  ·  Rapor: {rapor}  ·  Diğer: {diger}"
        self.card_aylik_izinli.set_data(
            data.get("aylik_izinli_personel_toplam", 0), izin_desc)

        # Sağlık
        self.card_yaklasan_saglik.set_data(
            data.get('yaklasan_saglik', 0), "90 gün içinde kontrolü gelenler")
        gecmis = data.get('gecmis_saglik', 0)
        self.card_gecmis_saglik.set_data(gecmis, "Zamanında yapılmamış muayeneler")

        # RKE
        self.card_yaklasan_rke.set_data(
            data.get('yaklasan_rke', 0), "1 ay içinde muayenesi olanlar")

        # Sistem
        self.card_hata_log.set_data(
            data.get('hata_log_satir', 0), "errors.log dosyasındaki satır sayısı")
        log_boyut = data.get('toplam_log_boyut_mb', 0)
        self.card_log_boyutu.set_data(f"{log_boyut:.2f} MB", "Tüm log dosyalarının toplamı")

    def _on_worker_finished(self):
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("  Yenile")
        logger.info("Dashboard verileri yüklendi.")
