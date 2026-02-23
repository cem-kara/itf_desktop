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
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor, QPixmap

from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles, STYLES
from ui.styles.icons import IconRenderer, Icons
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.pages.cihaz.components.uts_parser import scrape_uts

C = DarkTheme

# Sekme tanımları
TABS = [
    ("GENEL",        "Genel Bakış"),
    ("TEKNIK",       "Teknik Bilgiler"),
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
        self.cihaz_data      = {}
        self._modules        = {}       # code → widget (lazy cache)
        self._nav_btns       = {}       # code → QPushButton
        self._active_tab     = "GENEL"
        self._form_widget    = None
        self._current_form_type = None
        self._initial_load   = False

        self._setup_ui()
        self._load_data()

    # ═══════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setStyleSheet(STYLES["page"])
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()
        body.addWidget(self.content_stack, 1)
        body.addWidget(self._build_right_panel())

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)

    def _build_header(self) -> QFrame:
        """Header (52px) + sekme nav (36px)."""
        outer = QFrame()
        outer.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
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
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setStyleSheet(STYLES["back_btn"])
        IconRenderer.set_button_icon(btn_back, "arrow_left", color=C.TEXT_SECONDARY, size=14)
        btn_back.setIconSize(QSize(14, 14))
        btn_back.clicked.connect(self.kapat_istegi.emit)
        top_lay.addWidget(btn_back)
        top_lay.addWidget(self._sep())

        # Cihaz ikonu (avatar yerine)
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(34, 34)
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        self.lbl_avatar.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-radius:8px;"
            f"font-size:13px; font-weight:700; color:{C.TEXT_SECONDARY};"
        )
        self.lbl_avatar.setText("🔧")
        top_lay.addWidget(self.lbl_avatar)

        # Cihaz ID + detay
        info_lay = QVBoxLayout()
        info_lay.setSpacing(1)
        self.lbl_cihaz_id = QLabel("Yükleniyor…")
        self.lbl_cihaz_id.setStyleSheet(
            f"font-size:14px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        self.lbl_detay = QLabel("…")
        self.lbl_detay.setStyleSheet(STYLES["info_label"])
        info_lay.addWidget(self.lbl_cihaz_id)
        info_lay.addWidget(self.lbl_detay)
        top_lay.addLayout(info_lay)

        # Durum badge (dinamik olarak setlenir)
        self.lbl_durum = QLabel("")
        self.lbl_durum.setFixedHeight(22)
        top_lay.addWidget(self.lbl_durum)

        top_lay.addStretch()

        # Bakım / Arıza header butonları
        self.btn_bakim_ekle = QPushButton(" Bakım Gir")
        self.btn_bakim_ekle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_bakim_ekle.setStyleSheet(STYLES["refresh_btn"])
        IconRenderer.set_button_icon(self.btn_bakim_ekle, "tool", color=C.TEXT_SECONDARY, size=14)
        self.btn_bakim_ekle.setIconSize(QSize(14, 14))
        self.btn_bakim_ekle.clicked.connect(lambda: self._toggle_form("BAKIM"))
        top_lay.addWidget(self.btn_bakim_ekle)

        self.btn_ariza_ekle = QPushButton(" Arıza Kaydet")
        self.btn_ariza_ekle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ariza_ekle.setStyleSheet(STYLES["refresh_btn"])
        IconRenderer.set_button_icon(self.btn_ariza_ekle, "alert_circle", color=C.TEXT_SECONDARY, size=14)
        self.btn_ariza_ekle.setIconSize(QSize(14, 14))
        self.btn_ariza_ekle.clicked.connect(lambda: self._toggle_form("ARIZA"))
        top_lay.addWidget(self.btn_ariza_ekle)

        # Kapat (X)
        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setStyleSheet("background:transparent; border:none;")
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
        nav.setStyleSheet(f"background:transparent; border-top:1px solid {C.BORDER_SECONDARY};")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(16, 0, 16, 0)
        nav_lay.setSpacing(0)

        for code, label in TABS:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self._tab_btn_qss(active=False))
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            nav_lay.addWidget(btn)
            self._nav_btns[code] = btn

        nav_lay.addStretch()
        lay.addWidget(nav)
        return outer

    def _build_right_panel(self) -> QFrame:
        """400px sabit sağ panel."""
        panel = QFrame()
        panel.setFixedWidth(400)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-left: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Form bölgesi (toggle ile açılır) ──
        self.form_container = QFrame()
        self.form_container.setVisible(False)
        self.form_container.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};"
        )
        self.form_lay = QVBoxLayout(self.form_container)
        self.form_lay.setContentsMargins(12, 10, 12, 10)
        self.form_lay.setSpacing(8)

        form_hdr = QHBoxLayout()
        self.lbl_form_title = QLabel("İşlem")
        self.lbl_form_title.setStyleSheet(STYLES["section_label"])
        form_hdr.addWidget(self.lbl_form_title)
        form_hdr.addStretch()
        btn_form_kapat = QPushButton()
        btn_form_kapat.setFixedSize(20, 20)
        btn_form_kapat.setStyleSheet("background:transparent; border:none;")
        btn_form_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_form_kapat.clicked.connect(self._hide_form)
        try:
            IconRenderer.set_button_icon(btn_form_kapat, "x", color=C.TEXT_MUTED, size=11)
        except Exception:
            btn_form_kapat.setText("✕")
        form_hdr.addWidget(btn_form_kapat)
        self.form_lay.addLayout(form_hdr)

        self.form_content_lay = QVBoxLayout()
        self.form_content_lay.setContentsMargins(0, 0, 0, 0)
        self.form_lay.addLayout(self.form_content_lay)
        lay.addWidget(self.form_container)

        # ── Scroll: uyarılar + aksiyonlar ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(STYLES["scroll"])

        info_widget = QWidget()
        info_widget.setStyleSheet("background:transparent;")
        info_lay = QVBoxLayout(info_widget)
        info_lay.setContentsMargins(14, 16, 14, 16)
        info_lay.setSpacing(14)

        # Uyarılar
        info_lay.addWidget(self._section_lbl("DURUM"))
        self.alert_container = QVBoxLayout()
        self.alert_container.setSpacing(5)
        info_lay.addLayout(self.alert_container)

        # Hızlı işlemler
        info_lay.addWidget(self._section_lbl("HIZLI İŞLEMLER"))
        for label, icon, cb in [
            ("Bakım Gir",          "tool",         lambda: self._toggle_form("BAKIM")),
            ("Arıza Kaydet",       "alert_circle", lambda: self._toggle_form("ARIZA")),
            ("Kalibrasyon Kaydet", "check_circle", lambda: self._toggle_form("KALIBRASYON")),
            ("Künye Görüntüle",    "file_text",    None),
            ("Durum Değiştir",     "refresh",      None),
        ]:
            info_lay.addWidget(self._action_btn(label, icon, cb))

        info_lay.addStretch()
        scroll.setWidget(info_widget)
        lay.addWidget(scroll, 1)
        return panel

    # ═══════════════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════════════

    def _load_data(self):
        try:
            registry = RepositoryRegistry(self.db)
            cihaz_repo = registry.get("Cihazlar")
            
            # Cihaz verisini çek
            cihazlar = cihaz_repo.get_by_kod(self.cihaz_id, "Cihazid")
            if not cihazlar:
                QMessageBox.warning(self, "Hata", f"Cihaz bulunamadı: {self.cihaz_id}")
                self.kapat_istegi.emit()
                return
            
            self.cihaz_data = cihazlar[0]
            
            # Header bilgileri
            cihaz_id = str(self.cihaz_data.get("Cihazid", ""))
            marka    = str(self.cihaz_data.get("Marka", ""))
            model    = str(self.cihaz_data.get("Model", ""))
            seri     = str(self.cihaz_data.get("SeriNo", ""))
            birim    = str(self.cihaz_data.get("Birim", ""))
            durum    = str(self.cihaz_data.get("Durum", ""))
            
            self.lbl_cihaz_id.setText(cihaz_id)
            marka_model = f"{marka} {model}".strip()
            self.lbl_detay.setText(" · ".join(filter(None, [marka_model, seri, birim])))
            
            # Durum badge
            durum_style_map = {
                "Aktif":      STYLES["header_durum_aktif"],
                "Arızalı":    STYLES["header_durum_pasif"],
                "Bakımda":    STYLES["header_durum_izinli"],
                "Devre Dışı": STYLES["header_durum_pasif"],
            }
            self.lbl_durum.setText(durum)
            self.lbl_durum.setStyleSheet(
                durum_style_map.get(durum, STYLES.get("info_label", ""))
            )
            
            # Cihaz resmi varsa göster
            img_path = str(self.cihaz_data.get("Img", "")).strip()
            if img_path and os.path.exists(img_path):
                px = QPixmap(img_path)
                if not px.isNull():
                    self.lbl_avatar.setPixmap(
                        px.scaled(34, 34, Qt.KeepAspectRatioByExpanding,
                                  Qt.SmoothTransformation)
                    )
                    self.lbl_avatar.setText("")
            
            # Uyarıları yükle
            self._load_alerts()
            
            # Sekme
            if self._initial_load:
                cur = self.content_stack.currentWidget()
                if cur and hasattr(cur, "load_data"):
                    cur.load_data()
            else:
                self._switch_tab("GENEL")
                self._initial_load = True
                
        except Exception as e:
            logger.error(f"Cihaz merkez veri hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenemedi:\n{e}")

    def _load_alerts(self):
        """Cihaz için kritik durumları yükle."""
        while self.alert_container.count():
            item = self.alert_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        alerts = []
        
        # Garanti kontrolü
        garanti_durum = str(self.cihaz_data.get("GarantiDurumu", ""))
        if garanti_durum == "Sona Erdi":
            alerts.append("Garanti süresi sona ermiş")
        
        # Kalibrasyon kontrolü
        kalibrasyon = str(self.cihaz_data.get("KalibrasyonGereklimi", ""))
        if kalibrasyon == "Gerekli":
            alerts.append("Kalibrasyon gerekli")
        
        # Bakım kontrolü
        bakim_durum = str(self.cihaz_data.get("BakimDurum", ""))
        if bakim_durum == "Gecikmiş":
            alerts.append("Periyodik bakım gecikmiş")
        
        # Durum kontrolü
        durum = str(self.cihaz_data.get("Durum", ""))
        if durum == "Arızalı":
            alerts.append("Cihaz arızalı durumda")
        
        if not alerts:
            # İkon + metin widget'ı
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(16, 16)
            icon_lbl.setPixmap(Icons.pixmap("check_circle", size=16, 
                                            color=ComponentStyles.get_status_text_color('Aktif')))
            h.addWidget(icon_lbl)
            
            lbl = QLabel("Kritik durum yok")
            lbl.setStyleSheet(
                f"color:{ComponentStyles.get_status_text_color('Aktif')};"
                "background:transparent; font-size:12px;"
            )
            h.addWidget(lbl)
            h.addStretch()
            self.alert_container.addWidget(container)
        else:
            for msg in alerts:
                # İkon + metin widget'ı
                container = QWidget()
                h = QHBoxLayout(container)
                h.setContentsMargins(6, 6, 6, 6)
                h.setSpacing(8)
                container.setStyleSheet(
                    f"background:{C.BG_TERTIARY};"
                    f"border:1px solid {C.BORDER_PRIMARY};"
                    "border-radius:5px;"
                )
                
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(16, 16)
                icon_lbl.setPixmap(Icons.pixmap("alert_triangle", size=16,
                                                color=ComponentStyles.get_status_text_color('İzinli')))
                h.addWidget(icon_lbl)
                
                lbl = QLabel(msg)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color:{ComponentStyles.get_status_text_color('İzinli')};"
                    "background:transparent; font-size:12px;"
                )
                h.addWidget(lbl, 1)
                self.alert_container.addWidget(container)

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

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "GENEL":
                # Genel bakış paneli
                from ui.pages.cihaz.components.cihaz_overview_panel import CihazOverviewPanel
                w = CihazOverviewPanel(self.cihaz_data, self.db, sabitler_cache=self.sabitler_cache)
                w.saved.connect(self._load_data)  # Kayıt sonrası veriyi yenile
            elif code == "TEKNIK":
                # Teknik bilgiler paneli
                from ui.pages.cihaz.components.cihaz_teknik_panel import CihazTeknikPanel
                w = CihazTeknikPanel(self.cihaz_id, self.db)
                w.saved.connect(self._load_data)
                w.searched.connect(self._search_uts)  # UTS sorgulama bağlantısı
                w.search_complete.connect(self._on_search_complete)  # Sonucun UI güncellemesi
            elif code == "BAKIM":
                # Bakım işlemleri paneli
                from ui.pages.cihaz.components.bakim_kayit import BakimKayitPenceresi
                w = BakimKayitPenceresi(self.db, cihaz_id=self.cihaz_id)
            elif code == "KALIBRASYON":
                # Kalibrasyon paneli
                from ui.pages.cihaz.components.kalibrasyon_kayit import KalibrasyonKayitPenceresi
                w = KalibrasyonKayitPenceresi(self.db, cihaz_id=self.cihaz_id)
            elif code == "ARIZA":
                # Arıza kayıtları paneli
                from ui.pages.cihaz.ariza_kayit import ArizaKayitPenceresi
                w = ArizaKayitPenceresi(self.db, cihaz_id=self.cihaz_id)
            else:
                raise ValueError(f"Bilinmeyen sekme: {code}")

            if hasattr(w, "set_embedded_mode"):
                w.set_embedded_mode(True)
            return w

        except Exception as e:
            logger.error(f"Modül yükleme hatası ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(STYLES.get("stat_red", f"color:{C.STATUS_ERROR};"))
            return err

    # ═══════════════════════════════════════════════════
    #  FORM YÖNETİMİ (inline, popup yok)
    # ═══════════════════════════════════════════════════

    def _toggle_form(self, form_type: str):
        if (self.form_container.isVisible()
                and self._current_form_type == form_type):
            self._hide_form()
            return
        self._show_form(form_type)

    def _show_form(self, form_type: str):
        if not self.cihaz_data:
            QMessageBox.warning(self, "Hata", "Cihaz verisi henüz yüklenmedi.")
            return

        # Önceki formu temizle
        while self.form_content_lay.count():
            item = self.form_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._form_widget = None

        try:
            if form_type == "BAKIM":
                self.lbl_form_title.setText("BAKIM GİRİŞİ")
                from ui.pages.cihaz.bakim_kalibrasyon_form import BakimKayitForm
                form = BakimKayitForm(self.db, cihaz_id=self.cihaz_id)
                form.saved.connect(self._on_form_saved)
                self.form_content_lay.addWidget(form)
            elif form_type == "ARIZA":
                self.lbl_form_title.setText("ARIZA KAYIT")
                from ui.pages.cihaz.ariza_kayit import ArizaKayitForm
                form = ArizaKayitForm(self.db, cihaz_id=self.cihaz_id)
                form.saved.connect(self._on_form_saved)
                self.form_content_lay.addWidget(form)
            elif form_type == "KALIBRASYON":
                self.lbl_form_title.setText("KALİBRASYON KAYIT")
                from ui.pages.cihaz.bakim_kalibrasyon_form import KalibrasyonKayitForm
                form = KalibrasyonKayitForm(self.db, cihaz_id=self.cihaz_id)
                form.saved.connect(self._on_form_saved)
                self.form_content_lay.addWidget(form)
            else:
                return

            self._current_form_type = form_type
            self.form_container.setVisible(True)

        except Exception as e:
            logger.error(f"Form yükleme ({form_type}): {e}")
            QMessageBox.critical(self, "Hata", f"Form yüklenemedi:\n{e}")

    def _hide_form(self):
        self.form_container.setVisible(False)
        while self.form_content_lay.count():
            item = self.form_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._form_widget       = None
        self._current_form_type = None

    def _on_form_saved(self):
        self._hide_form()
        self._load_data()
        ariza = self._modules.get("ARIZA")
        if ariza and hasattr(ariza, "load_data"):
            ariza.load_data()
        bakim = self._modules.get("BAKIM")
        if bakim and hasattr(bakim, "load_data"):
            bakim.load_data()
        kalibrasyon = self._modules.get("KALIBRASYON")
        if kalibrasyon and hasattr(kalibrasyon, "load_data"):
            kalibrasyon.load_data()

    # ═══════════════════════════════════════════════════
    #  UTS SORGULAMA
    # ═══════════════════════════════════════════════════

    def _search_uts(self, urun_no: str):
        """\u00dcTS'den ürün verisi çek ve panele doldur."""
        if not urun_no.strip():
            QMessageBox.warning(self, "Hata", "Lütfen ürün numarası girin.")
            return
        
        panel = self._modules.get("TEKNIK")
        if not panel:
            return
        
        # Threading ile async işem çalıştır
        def run_search():
            try:
                # uts_parser verisiyle asyncio.run() çalıştır
                data = asyncio.run(scrape_uts(urun_no.strip()))
                
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
        panel = self._modules.get("TEKNIK")
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
            
            QMessageBox.information(self, "Başarılı", message)
        else:
            QMessageBox.warning(self, "Hata", message)

    # ═══════════════════════════════════════════════════
    #  YARDIMCI OLUŞTURUCULAR
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setStyleSheet(f"background: {C.BORDER_PRIMARY};")
        return s

    @staticmethod
    def _section_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(STYLES["section_label"])
        return lbl

    @staticmethod
    def _action_btn(label: str, icon: str, callback) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedHeight(34)
        btn.setStyleSheet(STYLES["action_btn"])
        try:
            IconRenderer.set_button_icon(btn, icon, color=C.TEXT_SECONDARY, size=13)
        except Exception:
            pass
        if callback:
            btn.clicked.connect(callback)
        else:
            btn.setEnabled(False)
        return btn

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
