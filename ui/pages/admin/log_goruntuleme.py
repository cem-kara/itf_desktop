# -*- coding: utf-8 -*-
"""
Log Görüntüleyici Sayfası
══════════════════════════════════════════════════════════════
• 3 log dosyası: app.log / sync.log / errors.log
• Rotated dosyalar: app.log.1 ... app.log.5
• Seviye filtresi: TÜMÜ / INFO / WARNING / ERROR / DEBUG
• Metin arama (anlık)
• Canlı takip: 5 saniyede bir dosya değişimi kontrolü
• Renk kodlaması: seviyeye göre
• Dosya bilgisi: boyut, satır sayısı, son güncelleme
• Klasörü aç butonu

Mimari: ThemeManager + core.paths.LOG_DIR + core.logger
"""
import os
import re
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit,
    QLabel, QComboBox, QLineEdit,
    QFrame, QCheckBox, QButtonGroup,
    QSizePolicy, QToolButton,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import (
    QTextCharFormat, QColor, QFont,
    QTextCursor, QSyntaxHighlighter,
    QTextDocument, QCursor,
)

from core.paths import LOG_DIR
from core.logger import logger
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()

# ─── Log dosya tanımları ──────────────────────────────────────
LOG_DOSYALARI = [
    ("app.log",    "Uygulama Logu"),
    ("sync.log",   "Senkronizasyon Logu"),
    ("errors.log", "Hata Logu"),
]
MAX_BACKUP = 5   # RotatingFileHandler backupCount

# ─── Renk paleti ─────────────────────────────────────────────
RENKLER = {
    "ERROR":    "#f85149",
    "CRITICAL": "#ff6e6e",
    "WARNING":  "#e3b341",
    "INFO":     "#e6edf3",
    "DEBUG":    "#8b949e",
    "DEFAULT":  "#8b949e",
    "TARIH":    "#555f6b",
    "SYNC":     "#79c0ff",
}

SEVIYELER = ["TÜMÜ", "DEBUG", "INFO", "WARNING", "ERROR"]


# ══════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTER
# ══════════════════════════════════════════════════════════════
class LogHighlighter(QSyntaxHighlighter):
    """
    Log satırlarını seviyeye ve bölgeye göre renklendirir.
    Format: 2025-01-01 12:00:00,000 - LEVEL - message
    """

    def __init__(self, doc: QTextDocument):
        super().__init__(doc)
        self._filtre   = "TÜMÜ"
        self._arama    = ""
        self._sarı_fmt = self._fmt("#ffea00", bold=False)

    @staticmethod
    def _fmt(renk: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(renk))
        if bold:
            f.setFontWeight(QFont.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def set_filtre(self, seviye: str):
        self._filtre = seviye
        self.rehighlight()

    def set_arama(self, metin: str):
        self._arama = metin.lower()
        self.rehighlight()

    def highlightBlock(self, metin: str):
        if not metin.strip():
            return

        # Seviye tespiti
        seviye = "DEFAULT"
        for s in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            if f" - {s} - " in metin or f" - {s}:" in metin:
                seviye = s
                break

        # Satır geneli renk
        ana_renk = RENKLER.get(seviye, RENKLER["DEFAULT"])

        # sync içerikli INFO satırları mavi
        if seviye == "INFO" and "sync" in metin.lower():
            ana_renk = RENKLER["SYNC"]

        ana_fmt = self._fmt(ana_renk)
        self.setFormat(0, len(metin), ana_fmt)

        # Tarih kısmını soluk göster
        m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\d]*)", metin)
        if m:
            self.setFormat(0, m.end(), self._fmt(RENKLER["TARIH"]))

        # Seviye etiketini kalın göster
        for s in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            pattern = f" - {s} - "
            idx = metin.find(pattern)
            if idx != -1:
                start = idx + 3
                self.setFormat(start, len(s), self._fmt(RENKLER.get(s, ana_renk), bold=True))
                break

        # Arama terimi vurgula
        if self._arama:
            idx = 0
            lower = metin.lower()
            while True:
                idx = lower.find(self._arama, idx)
                if idx == -1:
                    break
                self.setFormat(idx, len(self._arama), self._sarı_fmt)
                idx += len(self._arama)


# ══════════════════════════════════════════════════════════════
#  LOG OKUYUCU THREAD
# ══════════════════════════════════════════════════════════════
class LogOkuyucuThread(QThread):
    """Dosyayı arka planda okur (büyük dosyalar için)."""
    veri_hazir  = Signal(str, dict)   # (içerik, meta)
    hata_olustu = Signal(str)

    def __init__(self, dosya_yolu: str, max_satir: int = 2000):
        super().__init__()
        self._dosya   = dosya_yolu
        self._max     = max_satir

    def run(self):
        try:
            if not os.path.exists(self._dosya):
                self.veri_hazir.emit("", {"boyut": 0, "satirlar": 0, "son_guncelleme": "-"})
                return

            boyut  = os.path.getsize(self._dosya)
            mtime  = os.path.getmtime(self._dosya)
            son_g  = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M:%S")

            with open(self._dosya, encoding="utf-8", errors="replace") as f:
                satirlar = f.readlines()

            toplam = len(satirlar)
            # Çok büyük dosya → son N satır
            if toplam > self._max:
                satirlar = satirlar[-self._max:]

            icerik = "".join(satirlar)

            # Boyutu okunabilir hale getir
            if boyut < 1024:
                boyut_str = f"{boyut} B"
            elif boyut < 1024 * 1024:
                boyut_str = f"{boyut / 1024:.1f} KB"
            else:
                boyut_str = f"{boyut / 1024 / 1024:.1f} MB"

            meta = {
                "boyut":          boyut_str,
                "satirlar":       toplam,
                "gosterilen":     len(satirlar),
                "son_guncelleme": son_g,
                "mtime":          mtime,
            }
            self.veri_hazir.emit(icerik, meta)

        except Exception as exc:
            logger.error(f"LogOkuyucu: {exc}")
            self.hata_olustu.emit(str(exc))


# ══════════════════════════════════════════════════════════════
#  SAYFA
# ══════════════════════════════════════════════════════════════
class LogGoruntuleme(QWidget):
    """
    Log görüntüleyici sayfası.
    db parametresi mimari uyumluluk için kabul edilir.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db          = db
        self._worker      = None
        self._timer       = QTimer(self)
        self._son_mtime   = 0.0
        self._seviye      = "TÜMÜ"
        self._tum_satirlar: list[str] = []

        self._setup_ui()
        self._connect_signals()
        self._dosya_listesini_doldur()
        # İlk yükleme
        self._yenile()

    # ----------------------------------------------------------
    #  UI Kurulum
    # ----------------------------------------------------------
    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(10)

        # ── Üst Araç Çubuğu ───────────────────────────────
        main.addLayout(self._build_toolbar())

        # ── Seviye Filtre Butonları ────────────────────────
        main.addLayout(self._build_level_bar())

        # ── Log Metin Alanı ────────────────────────────────
        self._txt = QPlainTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._txt.setFont(QFont("Consolas, 'IBM Plex Mono', monospace", 11))
        self._txt.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #0d1117;"
            "  color: #e6edf3;"
            "  border: 1px solid #30363d;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "  selection-background-color: #264f78;"
            "}"
            "QScrollBar:vertical {"
            "  background: #161b22; width: 10px; border-radius: 5px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: #30363d; border-radius: 5px;"
            "}"
        )
        self._txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Syntax highlighter bağla
        self._highlighter = LogHighlighter(self._txt.document())

        main.addWidget(self._txt, 1)

        # ── Alt Durum Çubuğu ──────────────────────────────
        main.addWidget(self._build_status_bar())

    def _build_toolbar(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(8)

        # Dosya seçici
        lbl = QLabel("Dosya:")
        lbl.setStyleSheet(S.get("label", "color:#8b8fa3;") + " font-size:12px;")
        h.addWidget(lbl)

        self._cmb_dosya = QComboBox()
        self._cmb_dosya.setFixedWidth(260)
        self._cmb_dosya.setStyleSheet(S.get("combo", ""))
        h.addWidget(self._cmb_dosya)

        sep1 = self._separator()
        h.addWidget(sep1)

        # Arama
        self._txt_arama = QLineEdit()
        self._txt_arama.setPlaceholderText("🔍  Ara...")
        self._txt_arama.setFixedWidth(200)
        self._txt_arama.setStyleSheet(S.get("input", ""))
        self._txt_arama.setClearButtonEnabled(True)
        h.addWidget(self._txt_arama)

        h.addStretch(1)

        # Canlı takip
        self._chk_canli = QCheckBox("Canlı Takip")
        self._chk_canli.setChecked(True)
        self._chk_canli.setStyleSheet(
            "QCheckBox { color: #3fb950; font-size: 12px; font-weight: bold; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        h.addWidget(self._chk_canli)

        # Yenile
        self._btn_yenile = QPushButton("↻  Yenile")
        self._btn_yenile.setFixedSize(90, 32)
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_yenile.setStyleSheet(
            "QPushButton { background-color: #21262d; color: #58a6ff; "
            "border: 1px solid #30363d; border-radius: 5px; font-size: 12px; }"
            "QPushButton:hover { background-color: #30363d; }"
        )
        h.addWidget(self._btn_yenile)

        # Sona git
        self._btn_sona = QPushButton("↓ Sona Git")
        self._btn_sona.setFixedSize(90, 32)
        self._btn_sona.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_sona.setStyleSheet(
            "QPushButton { background-color: #21262d; color: #8b949e; "
            "border: 1px solid #30363d; border-radius: 5px; font-size: 12px; }"
            "QPushButton:hover { background-color: #30363d; }"
        )
        h.addWidget(self._btn_sona)

        # Klasörü aç
        self._btn_klasor = QPushButton("📁  Klasörü Aç")
        self._btn_klasor.setFixedSize(110, 32)
        self._btn_klasor.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_klasor.setStyleSheet(
            "QPushButton { background-color: #21262d; color: #8b949e; "
            "border: 1px solid #30363d; border-radius: 5px; font-size: 12px; }"
            "QPushButton:hover { background-color: #30363d; }"
        )
        h.addWidget(self._btn_klasor)

        return h

    def _build_level_bar(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(5)

        lbl = QLabel("Seviye:")
        lbl.setStyleSheet(S.get("label", "color:#8b8fa3;") + " font-size:12px;")
        h.addWidget(lbl)

        self._seviye_butonlari: dict[str, QPushButton] = {}
        renkler = {
            "TÜMÜ":    ("#58a6ff", "#0d2137"),
            "DEBUG":   ("#8b949e", "#1a1f26"),
            "INFO":    ("#e6edf3", "#1e2630"),
            "WARNING": ("#e3b341", "#2a2010"),
            "ERROR":   ("#f85149", "#2d1210"),
        }

        for seviye in SEVIYELER:
            fg, bg = renkler[seviye]
            btn = QPushButton(seviye)
            btn.setFixedSize(80, 28)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setCheckable(True)
            btn.setChecked(seviye == "TÜMÜ")
            btn.setProperty("seviye", seviye)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: #21262d; color: #8b949e; "
                f"border: 1px solid #30363d; border-radius: 4px; font-size: 11px; font-weight: bold; }}"
                f"QPushButton:checked {{ background-color: {bg}; color: {fg}; "
                f"border: 1px solid {fg}; }}"
                f"QPushButton:hover {{ background-color: #30363d; }}"
            )
            self._seviye_butonlari[seviye] = btn
            h.addWidget(btn)

        h.addSpacing(16)

        # Satır sayacı
        self._lbl_filtre = QLabel("0 / 0 satır")
        self._lbl_filtre.setStyleSheet("color: #555f6b; font-size: 11px; font-family: 'Consolas';")
        h.addWidget(self._lbl_filtre)

        h.addStretch(1)
        return h

    def _build_status_bar(self) -> QWidget:
        frame = QFrame()
        frame.setFixedHeight(28)
        frame.setStyleSheet(
            "QFrame { background-color: #161b22; border: 1px solid #30363d; border-radius: 4px; }"
        )
        h = QHBoxLayout(frame)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(20)

        def _lbl(txt=""):
            l = QLabel(txt)
            l.setStyleSheet("color: #555f6b; font-size: 11px; font-family: 'Consolas'; border: none;")
            return l

        self._lbl_dosya_adi  = _lbl("—")
        self._lbl_boyut      = _lbl("0 B")
        self._lbl_satirsayisi = _lbl("0 satır")
        self._lbl_son_gunc   = _lbl("—")
        self._lbl_durum      = _lbl("Hazır")

        h.addWidget(QLabel("📄", styleSheet="border:none; font-size:11px;"))
        h.addWidget(self._lbl_dosya_adi)
        self._add_divider(h)
        h.addWidget(QLabel("📦", styleSheet="border:none; font-size:11px;"))
        h.addWidget(self._lbl_boyut)
        self._add_divider(h)
        h.addWidget(QLabel("≡", styleSheet="border:none; font-size:11px; color:#555f6b;"))
        h.addWidget(self._lbl_satirsayisi)
        self._add_divider(h)
        h.addWidget(QLabel("🕐", styleSheet="border:none; font-size:11px;"))
        h.addWidget(self._lbl_son_gunc)
        h.addStretch(1)
        self._lbl_durum.setAlignment(Qt.AlignRight)
        h.addWidget(self._lbl_durum)

        return frame

    @staticmethod
    def _add_divider(layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedHeight(14)
        sep.setStyleSheet("color: #30363d; border: none; background-color: #30363d; width: 1px;")
        layout.addWidget(sep)

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setFixedHeight(20)
        f.setStyleSheet("color: #30363d; background-color: #30363d; width: 1px;")
        return f

    # ----------------------------------------------------------
    #  Sinyal Bağlantıları
    # ----------------------------------------------------------
    def _connect_signals(self):
        self._cmb_dosya.currentIndexChanged.connect(self._yenile)
        self._txt_arama.textChanged.connect(self._arama_degisti)
        self._btn_yenile.clicked.connect(self._yenile)
        self._btn_sona.clicked.connect(self._sona_git)
        self._btn_klasor.clicked.connect(self._klasoru_ac)
        self._chk_canli.stateChanged.connect(self._canli_takip_degisti)

        for seviye, btn in self._seviye_butonlari.items():
            btn.clicked.connect(lambda checked, s=seviye: self._seviye_sec(s))

        self._timer.timeout.connect(self._canli_kontrol)
        self._timer.start(5000)   # 5 saniyede bir kontrol

    # ----------------------------------------------------------
    #  Dosya Listesi
    # ----------------------------------------------------------
    def _dosya_listesini_doldur(self):
        self._cmb_dosya.blockSignals(True)
        self._cmb_dosya.clear()

        for dosya, aciklama in LOG_DOSYALARI:
            yol = os.path.join(LOG_DIR, dosya)
            if os.path.exists(yol):
                self._cmb_dosya.addItem(f"{aciklama}  ({dosya})", yol)

            # Rotated backups
            for i in range(1, MAX_BACKUP + 1):
                rotated = yol + f".{i}"
                if os.path.exists(rotated):
                    self._cmb_dosya.addItem(
                        f"  ↳ {dosya}.{i}  (Yedek {i})", rotated
                    )

        if self._cmb_dosya.count() == 0:
            self._cmb_dosya.addItem("Log dosyası bulunamadı", "")

        self._cmb_dosya.blockSignals(False)

    def _secili_dosya(self) -> str:
        return self._cmb_dosya.currentData() or ""

    # ----------------------------------------------------------
    #  Yükleme
    # ----------------------------------------------------------
    def _yenile(self):
        dosya = self._secili_dosya()
        if not dosya:
            self._txt.setPlainText("Log dosyası bulunamadı.")
            return

        self._lbl_durum.setText("Yükleniyor...")

        # Önceki worker'ı bekle
        if self._worker and self._worker.isRunning():
            return

        self._worker = LogOkuyucuThread(dosya)
        self._worker.veri_hazir.connect(self._veri_geldi)
        self._worker.hata_olustu.connect(self._hata_geldi)
        self._worker.start()

    def _veri_geldi(self, icerik: str, meta: dict):
        self._son_mtime        = meta.get("mtime", 0.0)
        self._tum_satirlar     = icerik.splitlines(keepends=True)

        # Meta bilgileri güncelle
        dosya_adi = os.path.basename(self._secili_dosya())
        self._lbl_dosya_adi.setText(dosya_adi)
        self._lbl_boyut.setText(meta.get("boyut", "—"))
        self._lbl_son_gunc.setText(meta.get("son_guncelleme", "—"))

        toplam = meta.get("satirlar", len(self._tum_satirlar))
        if meta.get("gosterilen", toplam) < toplam:
            self._lbl_durum.setText(f"Son {meta['gosterilen']:,} satır gösteriliyor")
        else:
            self._lbl_durum.setText("Hazır")

        self._filtreyi_uygula()

    def _hata_geldi(self, mesaj: str):
        self._txt.setPlainText(f"Dosya okunurken hata oluştu:\n{mesaj}")
        self._lbl_durum.setText("Hata")

    # ----------------------------------------------------------
    #  Filtre & Arama
    # ----------------------------------------------------------
    def _filtreyi_uygula(self):
        arama   = self._txt_arama.text().lower()
        seviye  = self._seviye

        filtrelenmis = []
        for satir in self._tum_satirlar:
            # Seviye filtresi
            if seviye != "TÜMÜ":
                if f" - {seviye} - " not in satir and f" - {seviye}:" not in satir:
                    continue
            # Arama filtresi
            if arama and arama not in satir.lower():
                continue
            filtrelenmis.append(satir)

        icerik = "".join(filtrelenmis)

        # Scroll pozisyonunu koru
        sb        = self._txt.verticalScrollBar()
        en_altta  = sb.value() == sb.maximum()
        self._txt.setPlainText(icerik)

        if en_altta:
            self._sona_git()

        # Sayaç güncelle
        self._lbl_filtre.setText(
            f"{len(filtrelenmis):,} / {len(self._tum_satirlar):,} satır"
        )
        self._lbl_satirsayisi.setText(f"{len(self._tum_satirlar):,} satır")

        # Highlighter güncelle
        self._highlighter.set_filtre(seviye)
        self._highlighter.set_arama(arama)

    def _seviye_sec(self, seviye: str):
        self._seviye = seviye
        # Diğer butonların checked durumunu kapat
        for s, btn in self._seviye_butonlari.items():
            btn.setChecked(s == seviye)
        self._filtreyi_uygula()

    def _arama_degisti(self, metin: str):
        self._filtreyi_uygula()

    # ----------------------------------------------------------
    #  Canlı Takip
    # ----------------------------------------------------------
    def _canli_takip_degisti(self):
        if self._chk_canli.isChecked():
            self._timer.start(5000)
        else:
            self._timer.stop()

    def _canli_kontrol(self):
        """Dosya değiştiyse otomatik yenile."""
        dosya = self._secili_dosya()
        if not dosya or not os.path.exists(dosya):
            return
        try:
            mtime = os.path.getmtime(dosya)
            if mtime != self._son_mtime:
                self._yenile()
        except Exception:
            pass

    # ----------------------------------------------------------
    #  Navigasyon & Yardımcılar
    # ----------------------------------------------------------
    def _sona_git(self):
        self._txt.moveCursor(QTextCursor.End)
        self._txt.ensureCursorVisible()

    def _basa_git(self):
        self._txt.moveCursor(QTextCursor.Start)
        self._txt.ensureCursorVisible()

    def _klasoru_ac(self):
        import subprocess, sys
        try:
            if sys.platform == "win32":
                os.startfile(LOG_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", LOG_DIR])
            else:
                subprocess.Popen(["xdg-open", LOG_DIR])
        except Exception as exc:
            logger.warning(f"Klasör açılamadı: {exc}")
