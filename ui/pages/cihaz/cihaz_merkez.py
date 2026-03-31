# -*- coding: utf-8 -*-
"""
Cihaz 360° Merkez — v1
───────────────────────────────────────────────
Tüm renkler merkezi ThemeManager / DarkTheme / ComponentStyles üzerinden gelir.
Hardcoded renk yok.
"""
import os
import threading
import asyncio
from pathlib import Path
from typing import cast, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor, QPixmap

from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from core.logger import logger
from core.hata_yonetici import bilgi_goster, hata_goster, uyari_goster
from core.di import get_cihaz_service as _get_cihaz_service
from ui.pages.cihaz.components.uts_parser import scrape_uts
from ui.pages.cihaz.components.ariza_detail_panel import CihazArizaPanel
from ui.pages.cihaz.components.kalibrasyon_detail_panel import KalibrasyonDetailPanel

C = DarkTheme

# Sekme tanımları
TABS = [
    ("GENEL",        "Genel Bakış"),
    ("ÜTS BİLGİLERİ", "ÜTS Bilgileri"),
    ("BELGELER",     "Belgeler"),
    ("ARIZA",        "Arıza Kayıtları"),
    ("BAKIM",        "Bakım İşlemleri"),
    ("KALIBRASYON",  "Kalibrasyon"),
]


class CihazMerkezPage(QWidget):
    kapat_istegi = Signal()

    def __init__(self, db, cihaz_id, sabitler_cache=None, parent=None):
        super().__init__(parent)
        self.db              = db
        self.cihaz_id        = str(cihaz_id)
        self.sabitler_cache  = sabitler_cache
        self._cihaz_svc      = None
        self.cihaz_data      = {}
        self._modules        = {}       # code → widget (lazy cache)
        self._nav_btns       = {}       # code → QPushButton
        self._active_tab     = "GENEL"
        self._initial_load   = False

        self._setup_ui()
        self._load_data()

    # ═══════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setProperty("bg-role", "page")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()
        body.addWidget(self.content_stack, 1)
        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)

    def _build_header(self) -> QFrame:
        """Header (52px) + sekme nav (36px)."""
        outer = QFrame()
        outer.setStyleSheet("""
            QFrame {{
                background-color: {};
                border-bottom: 1px solid {};
            }}
        """.format(C.BG_SECONDARY, C.BORDER_PRIMARY))
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Üst şerit ──
        top = QWidget()
        top.setFixedHeight(52)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(16, 0, 16, 0)
        top_lay.setSpacing(10)

        btn_back = QPushButton(" Listeye")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setProperty("style-role", "secondary")
        IconRenderer.set_button_icon(btn_back, "arrow_left", color=C.TEXT_SECONDARY, size=14)
        btn_back.setIconSize(QSize(14, 14))
        btn_back.clicked.connect(self.kapat_istegi.emit)
        top_lay.addWidget(btn_back)
        top_lay.addWidget(self._sep())

        # Cihaz ikonu (avatar yerine)
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(34, 34)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-radius:8px;"
            f"font-size:13px; font-weight:700; color:{C.TEXT_SECONDARY};"
        )
        self.lbl_avatar.setText("")
        top_lay.addWidget(self.lbl_avatar)

        # Cihaz ID + detay
        info_lay = QVBoxLayout()
        info_lay.setSpacing(1)
        self.lbl_cihaz_id = QLabel("Yükleniyor…")
        self.lbl_cihaz_id.setStyleSheet(
            f"font-size:14px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        self.lbl_detay = QLabel("…")
        self.lbl_detay.setProperty("style-role", "info")
        info_lay.addWidget(self.lbl_cihaz_id)
        info_lay.addWidget(self.lbl_detay)
        top_lay.addLayout(info_lay)

        # Durum badge (dinamik olarak setlenir)
        self.lbl_durum = QLabel("")
        self.lbl_durum.setFixedHeight(22)
        top_lay.addWidget(self.lbl_durum)

        self.lbl_kal_uyari = QLabel("")
        self.lbl_kal_uyari.setVisible(False)
        top_lay.addWidget(self.lbl_kal_uyari)

        top_lay.addStretch()

        # Kapat (X)
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setProperty("bg-role", "panel")
        btn_kapat.clicked.connect(self.kapat_istegi.emit)
        try:
            IconRenderer.set_button_icon(btn_kapat, "x", color=C.TEXT_MUTED, size=14)
        except Exception:
            btn_kapat.setText("✕")
        top_lay.addWidget(btn_kapat)

        lay.addWidget(top)

        # ── Sekme nav ──
        nav = QWidget()
        nav.setFixedHeight(36)
        nav.setProperty("border-role", "top-secondary")
        nav.setProperty("bg-role", "panel")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(16, 0, 16, 0)
        nav_lay.setSpacing(0)

        for code, label in TABS:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(self._tab_btn_qss(active=False))
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            nav_lay.addWidget(btn)
            self._nav_btns[code] = btn

        nav_lay.addStretch()
        lay.addWidget(nav)
        return outer

    # ═══════════════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════════════

    def _load_data(self):
        try:
            svc = self._cihaz_svc or _get_cihaz_service(self.db)
            self._cihaz_svc = svc
            # Cihaz verisini çek
            cihaz = svc.get_cihaz(self.cihaz_id).veri or []
            if not cihaz:
                uyari_goster(self, f"Cihaz bulunamadı: {self.cihaz_id}")
                self.kapat_istegi.emit()
                return

            self.cihaz_data = cihaz
            
            # Header bilgileri
            data = cast(dict, self.cihaz_data) or {}
            cihaz_id = str(data.get("Cihazid", ""))
            marka    = str(data.get("Marka", ""))
            model    = str(data.get("Model", ""))
            seri     = str(data.get("SeriNo", ""))
            birim    = str(data.get("Birim", ""))
            durum    = str(data.get("Durum", ""))
            
            self.lbl_cihaz_id.setText(cihaz_id)
            marka_model = f"{marka} {model}".strip()
            self.lbl_detay.setText(" · ".join(filter(None, [marka_model, seri, birim])))
            
            # Durum badge
            durum_style_map = {
                "Aktif":      "",
                "Arızalı":    "",
                "Bakımda":    "",
                "Devre Dışı": "",
            }
            self.lbl_durum.setText(durum)
            self.lbl_durum.setStyleSheet(
                cast(str, durum_style_map.get(durum, cast(str, "" or "")))
            )
            
            # Cihaz resmi varsa göster
            img_path = str(data.get("Img", "")).strip()
            if img_path and os.path.exists(img_path):
                px = QPixmap(img_path)
                if not px.isNull():
                    self.lbl_avatar.setPixmap(
                        px.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                  Qt.TransformationMode.SmoothTransformation)
                    )
                    self.lbl_avatar.setText("")
            
            # Sekme
            if self._initial_load:
                cur = self.content_stack.currentWidget()
                if cur and hasattr(cur, "load_data"):
                    cast(Any, cur).load_data()
            else:
                self._switch_tab("GENEL")
                self._initial_load = True
                
        except Exception as e:
            logger.error(f"Cihaz merkez veri hatası: {e}")
            hata_goster(self, f"Veri yüklenemedi:\n{e}")

    # ═══════════════════════════════════════════════════
    #  SEKME YÖNETİMİ
    # ═══════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        self._active_tab = code
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_btn_qss(active=(c == code)))

        if code not in self._modules:
            widget = self._create_module(code)
            self._modules[code] = widget
            self.content_stack.addWidget(widget)

        self.content_stack.setCurrentWidget(self._modules[code])

    def _switch_tab_and_open_form(self, code: str):
        """Sekmeye geçip varsa formu otomatik aç."""
        self._switch_tab(code)
        widget = self._modules.get(code)
        if widget is None:
            return
        # Formu otomatik açmak için ilgili metodu çağır
        inner = None
        if hasattr(widget, "ariza_form"):
            inner = widget.ariza_form
        elif hasattr(widget, "bakim_form"):
            inner = widget.bakim_form
        elif hasattr(widget, "kalibrasyon_form"):
            inner = widget.kalibrasyon_form
        # Her formun kendi "yeni kayıt aç" metod adını dene
        for method in ("_open_ariza_form", "_open_bakim_form",
                       "_open_kal_form", "_open_kalibrasyon_form"):
            if inner and hasattr(inner, method):
                getattr(inner, method)()
                break

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "GENEL":
                # Genel bakış paneli
                from ui.pages.cihaz.components.cihaz_overview_panel import CihazOverviewPanel
                w = CihazOverviewPanel(self.cihaz_data, self.db, sabitler_cache=self.sabitler_cache)
                w.saved.connect(self._load_data)  # Kayıt sonrası veriyi yenile
            elif code == "ÜTS BİLGİLERİ":
                # Teknik bilgiler paneli
                from ui.pages.cihaz.components.cihaz_teknik_panel import CihazTeknikPanel
                w = CihazTeknikPanel(self.cihaz_id, self.db)
                w.saved.connect(self._load_data)
                w.searched.connect(self._search_uts)  # UTS sorgulama bağlantısı
                w.search_complete.connect(self._on_search_complete)  # Sonucun UI güncellemesi
            elif code == "BELGELER":
                # Belge yönetim paneli
                from ui.pages.cihaz.components.cihaz_dokuman_panel import CihazDokumanPanel
                w = CihazDokumanPanel(self.cihaz_id, self.db)
                w.saved.connect(self._load_data)
            elif code == "BAKIM":
                # Bakım işlemleri paneli
                from ui.pages.cihaz.components.bakim_detail_panel import BakimDetailPanel
                w = BakimDetailPanel(self.db, cihaz_id=self.cihaz_id)
            elif code == "KALIBRASYON":
                # Kalibrasyon paneli
                w = KalibrasyonDetailPanel(self.db, cihaz_id=self.cihaz_id)
            elif code == "ARIZA":
                # Arıza kayıtları paneli
                w = CihazArizaPanel(self.db, cihaz_id=self.cihaz_id)
                # Arıza → bakım zinciri: arıza formundan bakım sekmesine geç
                if hasattr(w, "ariza_form") and hasattr(w.ariza_form, "bakima_gec"):
                    w.ariza_form.bakima_gec.connect(
                        lambda _: self._switch_tab("BAKIM")
                    )
            else:
                raise ValueError(f"Bilinmeyen sekme: {code}")

            if hasattr(w, "set_embedded_mode"):
                cast(Any, w).set_embedded_mode(True)
            return w

        except Exception as e:
            logger.error(f"Modül yükleme hatası ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("")
            return err

    # ═══════════════════════════════════════════════════
    #  UTS SORGULAMA
    # ═══════════════════════════════════════════════════

    def _search_uts(self, urun_no: str):
        """\u00dcTS'den ürün verisi çek ve panele doldur."""
        if not urun_no.strip():
            uyari_goster(self, "Lütfen ürün numarası girin.")
            return
        
        panel = self._modules.get("ÜTS BİLGİLERİ")
        if not panel:
            return
        
        # Threading ile async işem çalıştır
        def run_search():
            try:
                # Yeni event loop oluşturarak async fonksiyonu çalıştır
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(scrape_uts(urun_no.strip()))
                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass

                if data and isinstance(data, dict):
                    panel.search_complete.emit(data, True, f"Ürün yüklendi: {urun_no}")
                else:
                    panel.search_complete.emit({}, False, f"Ürün bulunamadı: {urun_no}")

            except Exception as e:
                logger.error(f"ÜTS sorgu hatası: {e}")
                panel.search_complete.emit({}, False, f"ÜTS sorgulama başarısız:\n{str(e)[:200]}")
        
        # Thread'de çalıştır
        thread = threading.Thread(target=run_search, daemon=True)
        thread.start()

    def _on_search_complete(self, data: dict, success: bool, message: str):
        """ÜTS sorgusunun tamamlandığını işle (main thread)."""
        panel = self._modules.get("ÜTS BİLGİLERİ")
        if not panel:
            return
        
        if success:
            # Panel'in teknik_data'sını güncelle
            panel.teknik_data.update(data)
            
            # Tüm widget'ları güncelle
            for key, widget in panel._widgets.items():
                raw = panel.teknik_data.get(key, "")
                if key in panel._link_fields and raw:
                    try:
                        uri = Path(raw).expanduser().as_uri()
                        widget.setText(
                            f'<a href="{uri}" style="color:#4d9de0;">{raw}</a>'
                        )
                    except Exception:
                        widget.setText(str(raw))
                else:
                    widget.setText(str(raw) if raw else "—")
            
            bilgi_goster(self, message)
        else:
            uyari_goster(self, message)

    # ═══════════════════════════════════════════════════
    #  YARDIMCI OLUŞTURUCULAR
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setProperty("bg-role", "separator")
        return s

    # ═══════════════════════════════════════════════════
    #  STİL SABİTLERİ (hardcoded renk içermeyen)
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _tab_btn_qss(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{"
                f"background:transparent; border:none;"
                f"border-bottom:2px solid {C.INPUT_BORDER_FOCUS};"
                f"color:{C.TEXT_PRIMARY};"
                f"font-size:13px; font-weight:700; padding:0 14px;"
                f"}}"
            )
        return (
            f"QPushButton{{"
            f"background:transparent; border:none;"
            f"border-bottom:2px solid transparent;"
            f"color:{C.TEXT_SECONDARY};"
            f"font-size:13px; font-weight:600; padding:0 14px;"
            f"}}"
            f"QPushButton:hover{{color:{C.TEXT_PRIMARY};}}"
        )
