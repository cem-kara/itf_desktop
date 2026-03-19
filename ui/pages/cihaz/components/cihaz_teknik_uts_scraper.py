# -*- coding: utf-8 -*-
"""
Cihaz Teknik ÜTS Web Sorgulama - Playwright Tabanlı
───────────────────────────────────────────────────
Gerçek tarayıcı ile ÜTS sayfasından veri çeker,
HTML parse ederek veritabanına kaydeder.
"""
from __future__ import annotations
import json
import asyncio
import sys
from typing import Dict, Optional, cast
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QLineEdit,
    QMessageBox, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, uyari_goster
from core.di import get_cihaz_service
from database.repository_registry import RepositoryRegistry
from ui.pages.cihaz.components.uts_parser import (
    scrape_uts,
    load_allowed_db_fields,
    filter_allowed_fields,
)

C = DarkTheme

_ACCENT    = getattr(C, "ACCENT",         "#4d9de0")
_BORDER    = getattr(C, "BORDER_PRIMARY", "#2d3f55")
_TEXT_PRI  = getattr(C, "TEXT_PRIMARY",   "#dce8f5")
_TEXT_SEC  = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_SUCCESS   = "#4caf6e"
_WARNING   = "#e8a838"
_ERROR     = "#e05c5c"
_BG_SECT   = "rgba(255,255,255,0.03)"
_BG_HDR    = "rgba(77,157,224,0.18)"
_BG_SUBHDR = "rgba(77,157,224,0.09)"
_BG_EVEN   = "transparent"
_BG_ODD    = "rgba(255,255,255,0.04)"
_BC        = f"1px solid {_BORDER}"

_HDR_CSS = (
    f"background:{_BG_HDR};color:{_ACCENT};"
    "font-size:12px;font-weight:700;letter-spacing:.5px;"
    f"border-bottom:{_BC};padding:7px 14px;"
)
_SUBHDR_CSS = (
    f"background:{_BG_SUBHDR};color:{_ACCENT};"
    "font-size:11px;font-weight:600;font-style:italic;"
    f"border-top:{_BC};border-bottom:{_BC};padding:4px 14px;"
)
_LBL_CSS = f"color:{_TEXT_SEC};font-size:11px;font-weight:600;padding:6px 10px 6px 14px;"
_VAL_CSS = f"color:{_TEXT_PRI};font-size:12px;font-weight:400;padding:6px 14px 6px 0px;"
_INP_CSS = (
    f"QLineEdit{{background:rgba(255,255,255,.05);color:{_TEXT_PRI};"
    f"border:{_BC};border-radius:5px;padding:8px 12px;font-size:13px;}}"
    f"QLineEdit:focus{{border-color:{_ACCENT};background:rgba(77,157,224,.07);}}"
)
_BTN_P = (
    f"QPushButton{{background:{_ACCENT};color:#fff;border:none;border-radius:5px;"
    "font-size:12px;font-weight:700;padding:9px 22px;}}"
    "QPushButton:hover{background:#5eaee8;}"
    "QPushButton:disabled{background:#2d3f55;color:#55697a;}"
)
_BTN_S = (
    f"QPushButton{{background:transparent;color:{_TEXT_SEC};"
    f"border:{_BC};border-radius:5px;font-size:12px;font-weight:600;padding:9px 22px;}}"
    f"QPushButton:hover{{background:rgba(255,255,255,.06);color:{_TEXT_PRI};}}"
)

"""
Parser and scraping logic moved to uts_parser.py to keep UI code smaller.
"""



# ══════════════════════════════════════════════════════════════════════════════
#  QThread Worker - Async Event Loop entegrasyonu
# ══════════════════════════════════════════════════════════════════════════════

class _Worker(QObject):
    """QThread içinde async Playwright scraper çalıştırır."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, urun_no: str):
        super().__init__()
        self.urun_no = urun_no

    def run(self):
        """Async scraper'ı QThread içinde çalıştır."""
        try:
            # Windows'ta Playwright subprocess desteği için ProactorEventLoop gerekli
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(cast(object, asyncio.WindowsProactorEventLoopPolicy()))  # type: ignore
            
            # Event loop oluştur ve async fonksiyon çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(scrape_uts(self.urun_no))
            loop.close()
            
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Scraper hatası: {e}")
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  UI Yardımcıları
# ══════════════════════════════════════════════════════════════════════════════

def _mk_pair(lbl_txt, val, bg):
    w = QWidget(); w.setStyleSheet("background:{};".format(bg))
    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0); h.setSpacing(6)
    l = QLabel(lbl_txt)
    l.setStyleSheet(_LBL_CSS + "background:{};".format(bg))
    l.setWordWrap(True); l.setMinimumWidth(160)
    l.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
    val.setStyleSheet(val.styleSheet() + "background:{};".format(bg))
    val.setWordWrap(True)
    h.addWidget(l); h.addWidget(val, stretch=1)
    return w


class _Sec(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._r = 0
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self._frame = QFrame()
        self._frame.setStyleSheet(
            f"QFrame{{border:{_BC};border-radius:4px;background:{_BG_SECT};}}"
        )
        self._vb = QVBoxLayout(self._frame)
        self._vb.setContentsMargins(0,0,0,0); self._vb.setSpacing(0)
        h = QLabel(title); h.setStyleSheet(_HDR_CSS)
        self._vb.addWidget(h); outer.addWidget(self._frame)

    def subhdr(self, t):
        s = QLabel(t); s.setStyleSheet(_SUBHDR_CSS)
        self._vb.addWidget(s); self._r = 0

    def row(self, l1, v1, l2="", v2=None):
        bg = _BG_ODD if self._r % 2 else _BG_EVEN; self._r += 1
        rw = QWidget()
        rw.setStyleSheet(f"border-bottom: {_BC};")
        rw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        rh = QHBoxLayout(rw); rh.setContentsMargins(0,0,0,0); rh.setSpacing(0)
        rh.addWidget(_mk_pair(l1, v1, bg), stretch=1)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setFixedWidth(1)
        sep.setStyleSheet("background:{};border:none;".format(_BORDER)); rh.addWidget(sep)
        if l2 and v2:
            rh.addWidget(_mk_pair(l2, v2, bg), stretch=1)
        else:
            ph = QWidget(); ph.setStyleSheet("background:{};".format(bg))
            ph.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            rh.addWidget(ph, stretch=1)
        self._vb.addWidget(rw)


# ══════════════════════════════════════════════════════════════════════════════
#  ANA WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class CihazTeknikUtsScraper(QWidget):
    """
    ÜTS API'dan ürün numarasıyla teknik veri çeken panel.

    Kullanım:
        w = CihazTeknikUtsScraper(cihaz_id="...", db=db, parent=self)
        w.saved.connect(...)
        w.canceled.connect(...)
        w.data_ready.connect(self._populate_form_fields)  # Veriyi form'a yaz
    """
    saved      = Signal()
    canceled   = Signal()
    data_ready = Signal(dict)  # Parsed data emit et (form populate için)

    def __init__(self, cihaz_id="", db=None, parent=None):
        super().__init__(parent)
        self.db       = db
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        self._allowed_fields = load_allowed_db_fields()
        self._parsed: Dict[str, str]    = {}
        self._raw_json: str             = ""
        self._thread: Optional[QThread] = None
        self._build()

    # ── Kurulum ───────────────────────────────────────────────────────────────

    def _build(self):
        main = QVBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        cnt = QWidget(); cnt.setStyleSheet("background:transparent;")
        root = QVBoxLayout(cnt); root.setContentsMargins(20,20,20,20); root.setSpacing(14)

        root.addWidget(self._search_box())

        self._stat = QLabel(""); self._stat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stat.setStyleSheet("font-size: 11px;")
        self._stat.hide(); root.addWidget(self._stat)

        self._prog = QProgressBar(); self._prog.setRange(0,0); self._prog.setFixedHeight(3)
        self._prog.setStyleSheet(
            f"QProgressBar{{background:{_BG_SECT};border:none;border-radius:1px;}}"
            f"QProgressBar::chunk{{background:{_ACCENT};border-radius:1px;}}"
        )
        self._prog.hide(); root.addWidget(self._prog)

        self._prev = QWidget(); self._prev.setStyleSheet("background:transparent;")
        self._pvb  = QVBoxLayout(self._prev)
        self._pvb.setContentsMargins(0,0,0,0); self._pvb.setSpacing(14)
        self._prev.hide(); root.addWidget(self._prev)

        root.addWidget(self._btn_bar())
        root.addStretch()
        scroll.setWidget(cnt); main.addWidget(scroll)

    def _search_box(self):
        box = QFrame()
        box.setProperty("border-role", "panel")
        box.style().unpolish(box)
        box.style().polish(box)
        vb = QVBoxLayout(box); vb.setContentsMargins(20,18,20,18); vb.setSpacing(12)

        title = QLabel("ÜTS Ürün Sorgulama")
        title.setStyleSheet(
            f"color:{_ACCENT};font-size:13px;font-weight:700;border:none;background:transparent;"
        )
        vb.addWidget(title)

        desc = QLabel(
            "Birincil Ürün Numarasını (barkod) girin. ÜTS sistemi sorgulanarak\n"
            "tüm teknik bilgiler otomatik doldurulur."
        )
        desc.setStyleSheet("font-size: 11px; border: none; background: transparent;")
        desc.setWordWrap(True); vb.addWidget(desc)

        row = QHBoxLayout(); row.setSpacing(8)
        self._inp = QLineEdit()
        self._inp.setPlaceholderText("Birincil Ürün No  (örn: 04056869003665)")
        self._inp.setStyleSheet(_INP_CSS)
        self._inp.returnPressed.connect(self._start)
        row.addWidget(self._inp, stretch=1)
        btn = QPushButton("Sorgula"); btn.setProperty("style-role", "action")
        btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.clicked.connect(self._start)
        row.addWidget(btn); vb.addLayout(row)

        return box

    def _btn_bar(self):
        bar = QWidget(); bar.setStyleSheet("background:transparent;")
        h = QHBoxLayout(bar); h.setContentsMargins(0,0,0,0); h.setSpacing(10)

        self._btn_debug = QPushButton("Ham JSON")
        self._btn_debug.setProperty("style-role", "secondary")
        self._btn_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_debug.setVisible(False)
        self._btn_debug.clicked.connect(self._show_debug)
        h.addWidget(self._btn_debug)

        h.addStretch()
        b_cancel = QPushButton("İptal"); b_cancel.setProperty("style-role", "secondary")
        b_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        b_cancel.clicked.connect(self.canceled.emit); h.addWidget(b_cancel)

        self._b_save = QPushButton("Veritabanına Kaydet")
        IconRenderer.set_button_icon(self._b_save, "save", color="#00b4d8", size=14)
        self._b_save.setProperty("style-role", "action"); self._b_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._b_save.setEnabled(False); self._b_save.clicked.connect(self._save)
        h.addWidget(self._b_save)
        return bar

    # ── İşlemler ──────────────────────────────────────────────────────────────

    def _start(self):
        urun_no = self._inp.text().strip()
        if not urun_no:
            self._st("Lütfen Birincil Ürün Numarası girin.", _WARNING); return
        if self._thread and self._thread.isRunning(): return

        self._prog.show(); self._b_save.setEnabled(False)
        self._btn_debug.setVisible(False); self._prev.hide()
        self._st(f"ÜTS sorgulanıyor: {urun_no} …", _ACCENT)

        self._thread = QThread()
        self._worker = _Worker(urun_no)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._done)
        self._worker.error.connect(self._err)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _done(self, data: dict):
        self._prog.hide()
        self._raw_json = data.pop("_raw_json", "")
        count = data.pop("_item_count", "?")
        data = filter_allowed_fields(data, self._allowed_fields)
        self._parsed = data
        
        # DEBUG: Parsed data içeriğini logla
        logger.info(f"📦 Parser çıktısı: {len(self._parsed)} alan")
        logger.debug(f"Alan isimleri: {list(self._parsed.keys())}")
        for key, val in list(self._parsed.items())[:10]:  # İlk 10 alanı göster
            logger.debug(f"  - {key}: {val[:50] if isinstance(val, str) and len(val) > 50 else val}")
        
        self._btn_debug.setVisible(True)
        self._build_preview(data)
        self._b_save.setEnabled(True)
        filled = sum(1 for v in data.values() if v)
        self._st(
            f"✅ {filled} alan çekildi  ({count} ürün bulundu). Kontrol edip kaydedin.",
            _SUCCESS,
        )
        
        # Parsed data'yı parent widget'a emit et (form field populate için)
        self.data_ready.emit(self._parsed)

    def _err(self, msg: str):
        self._prog.hide()
        self._st(f"❌ {msg}", _ERROR)
        logger.error(f"ÜTS: {msg}")
        uyari_goster(self, msg)

    def _show_debug(self):
        """Çekilen veriyi JSON olarak göster."""
        if not self._parsed:
            bilgi_goster(self, "Henüz bir sonuç yok.")
            return
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Çekilen Ürün Verisi")
        dlg.setText("ÜTS'den çekilen tam teknik bilgiler:")
        dlg.setDetailedText(json.dumps(self._parsed, ensure_ascii=False, indent=2)[:5000])
        dlg.exec()

    # ── Önizleme ──────────────────────────────────────────────────────────────

    def _build_preview(self, data: dict):
        while self._pvb.count():
            it = self._pvb.takeAt(0)
            if it:
                widget = it.widget()
                if widget:
                    widget.deleteLater()

        def W(key: str) -> QLabel:
            val = data.get(key) or ""
            lb = QLabel(val if val else "—")
            lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lb.setWordWrap(True)
            lb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            lb.setStyleSheet(_VAL_CSS + ("color:{};".format(_WARNING) if not val else ""))
            return lb

         # ── 1. Tanimlayici ────────────────────────────────────────────────────
        s1 = _Sec("Tanimlayici Bilgiler")
        s1.row("Birincil Urun No",   W("BirincilUrunNumarasi"), "Kurum Unvan",  W("KurumUnvan"))
        s1.row("Marka",              W("MarkaAdi"),             "Etiket",       W("EtiketAdi"))
        s1.row("Versiyon/Model",     W("VersiyonModel"),        "Urun Tipi",    W("UrunTipi"))
        s1.row("Sinif",              W("Sinif"),                "Katalog No",  W("KatalogNo"))
        s1.row("GMDN Kodu",          W("GmdnTerimKod"),         "GMDN Tanimi", W("GmdnTerimTurkceAd"))
        s1.row("Temel UDI DI",       W("TemelUdiDi"),           "Urun Tanimi", W("UrunTanimi"))
        s1.row("Aciklama",           W("Aciklama"))
        self._pvb.addWidget(s1)

         # ── 1b. Kurum Bilgileri ───────────────────────────────────────────────
        s1b = _Sec("Kurum/Firma Bilgileri")
        s1b.row("Kurum Gorunen Ad", W("KurumGorunenAd"), "Kurum No",     W("KurumNo"))
        s1b.row("Kurum Telefon",    W("KurumTelefon"),  "Kurum Eposta", W("KurumEposta"))
        self._pvb.addWidget(s1b)

         # ── 2. Ithal/Imal ─────────────────────────────────────────────────────
        s2 = _Sec("Ithal/Imal Bilgileri")
        s2.row("Ithal/Imal Bilgisi", W("IthalImalBilgisi"), "Mensei Ulke", W("MenseiUlkeSet"))
        s2.row("Ithal Edilen Ulke",  W("IthalEdilenUlkeSet"), "SUT Eslesmesi", W("SutEslesmesiSet"))
        self._pvb.addWidget(s2)

         # ── 3. Teknik Ozellikler ─────────────────────────────────────────────
        s3 = _Sec("Teknik Ozellikler")
        s3.subhdr("Durum ve Kayit Bilgisi")
        s3.row("Durum",                     W("Durum"),
             "Cihaz Kayit Tipi",         W("CihazKayitTipi"))
        s3.row("UTS Baslangic Tarihi",     W("UtsBaslangicTarihi"),
             "Kontrol Gonderildigi Tarih", W("KontroleGonderildigiTarih"))
        s3.subhdr("Kalibrasyon / Bakim")
        s3.row("Kalibrasyona Tabi mi",      W("KalibrasyonaTabiMi"),
             "Kalibrasyon Periyodu (ay)", W("KalibrasyonPeriyodu"))
        s3.row("Bakima Tabi mi",            W("BakimaTabiMi"),
             "Bakim Periyodu (ay)",       W("BakimPeriyodu"))
        s3.subhdr("Diger Ozellikler")
        s3.row("MRG Uyumlu",                  W("MrgUyumlu"),
             "Iyonize Radyasyon Icerir mi", W("IyonizeRadyasyonIcerir"))
        s3.row("Tek Hasta Kullanilabilir mi", W("TekHastayaKullanilabilir"),
             "Sinirli Kullanim Sayisi Var", W("SinirliKullanimSayisiVar"))
        s3.row("Sinirli Kullanim Sayisi",     W("SinirliKullanimSayisi"),
             "Baska Imalatciya Urettirildi mi", W("BaskaImalatciyaUrettirildiMi"))
        s3.row("GMDN Aciklama",               W("GmdnTerimTurkceAciklama"))
        self._pvb.addWidget(s3)

        self._prev.show()

    # ── Kaydet ────────────────────────────────────────────────────────────────

    def _save(self):
        if not self._parsed: return
        self._parsed["Cihazid"] = self.cihaz_id
        try:
            svc = get_cihaz_service(self.db)
            
            # Mevcut kaydı kontrol et
            existing = svc.get_cihaz_teknik(self.cihaz_id).veri or []
            if existing:
                svc.update_cihaz_teknik(self.cihaz_id, self._parsed)
            else:
                svc.insert_cihaz_teknik(self._parsed)
            
            filled = sum(1 for v in self._parsed.values() if v)
            self._st("✅ Kaydedildi!", _SUCCESS)
            self._b_save.setEnabled(False)
            bilgi_goster(self, f"Teknik bilgiler kaydedildi. ({filled} alan)")
            
            # Saved signal emit et (parent widget'a bildir)
            self.saved.emit()
            
            # Data'yı tekrar emit et (eğer parent form hala güncel değilse)
            self.data_ready.emit(self._parsed)
        except Exception as e:
            logger.error(f"VT: {e}")
            self._st(f"❌ {e}", _ERROR)
            hata_goster(self, str(e))

    def _st(self, msg, color=""):
        self._stat.setText(msg)
        if color: self._stat.setStyleSheet("color:{};font-size:11px;".format(color))
        self._stat.show()
