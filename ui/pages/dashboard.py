# -*- coding: utf-8 -*-
"""
Ana GÃ¶sterge Paneli (Dashboard)
"""
import calendar
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QLabel, QPushButton, QGroupBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import parse_date, to_db_date
from core.log_manager import LogStatistics
from core.paths import DB_PATH
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()

class DashboardWorker(QThread):
    """Arka planda dashboard verilerini toplayan worker."""
    data_ready = Signal(dict)

    def __init__(self, db_path):
        super().__init__()
        self._db_path = db_path

    def run(self):
        data = {}
        db = None
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            db = SQLiteManager(db_path=self._db_path)
            registry = get_registry(db)
            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')

            # --- CÄ°HAZ ---
            six_months_later = (today + timedelta(days=180)).strftime('%Y-%m-%d')
            data['yaklasan_ndk'] = self._get_count(registry, "Cihazlar", f"BitisTarihi BETWEEN '{today_str}' AND '{six_months_later}'")
            
            month_start = today.replace(day=1).strftime('%Y-%m-%d')
            _, last_day = calendar.monthrange(today.year, today.month)
            month_end = today.replace(day=last_day).strftime('%Y-%m-%d')
            data['aylik_bakim'] = self._get_count(registry, "Periyodik_Bakim", f"PlanlananTarih BETWEEN '{month_start}' AND '{month_end}' AND Durum = 'PlanlandÄ±'")

            data['aylik_kalibrasyon'] = self._get_count(registry, "Kalibrasyon", f"BitisTarihi BETWEEN '{month_start}' AND '{month_end}' AND Durum = 'TamamlandÄ±'")

            one_week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            data['yeni_arizalar'] = self._get_count(registry, "Cihaz_Ariza", f"BaslangicTarihi >= '{one_week_ago}' AND Durum <> 'KapatÄ±ldÄ±'")

            # --- PERSONEL ---
            data['aktif_personel'] = self._get_count(registry, "Personel", "Durum = 'Aktif'")
            data.update(self._get_monthly_leave_stats(registry))

            # --- RKE ---
            one_month_later = (today + timedelta(days=30)).strftime('%Y-%m-%d')
            data['yaklasan_rke'] = self._get_count(
                registry,
                "RKE_List",
                f"KontrolTarihi BETWEEN '{today_str}' AND '{one_month_later}' AND Durum = 'PlanlandÄ±'"
            )

            # --- SAÄLIK ---
            three_months_later = (today + timedelta(days=90)).strftime('%Y-%m-%d')
            data['yaklasan_saglik'] = self._get_count(
                registry,
                "Personel_Saglik_Takip",
                f"SonrakiKontrolTarihi BETWEEN '{today_str}' AND '{three_months_later}' AND Durum != 'Pasif'"
            )
            data['gecmis_saglik'] = self._get_count(
                registry,
                "Personel_Saglik_Takip",
                f"SonrakiKontrolTarihi < '{today_str}' AND SonrakiKontrolTarihi != '' AND Durum != 'Pasif'"
            )

            # --- MEVCUT SORGULAR ---
            data['acik_arizalar'] = self._get_count(registry, "Cihaz_Ariza", "Durum = 'AÃ§Ä±k'")
            data['gecmis_kalibrasyon'] = self._get_count(registry, "Kalibrasyon", f"BitisTarihi < '{today_str}' AND BitisTarihi != '' AND Durum = 'TamamlandÄ±'")

            log_stats = LogStatistics.get_log_stats()
            data['hata_log_satir'] = log_stats.get('errors.log', {}).get('lines', 0)
            data['toplam_log_boyut_mb'] = LogStatistics.get_total_log_size()

            self.data_ready.emit(data)
        except Exception as e:
            logger.error(f"Dashboard worker hatasÄ±: {e}")
            self.data_ready.emit({})  # Emit empty on error
        finally:
            if db:
                db.close()

    def _get_count(self, registry, table_name, where_clause, distinct_col=None):
        try:
            repo = registry.get(table_name)
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            cursor = repo.db.execute(query)
            return cursor.fetchone()[0]
        except Exception as e:
            logger.warning(f"Dashboard sayÄ±m hatasÄ± ({table_name}): {e}")
            return -1 # Indicate error

    def _parse_date(self, value):
        if parse_date(value) is None:
            return ""
        return to_db_date(value)

    def _classify_leave_type(self, leave_type):
        leave_type = str(leave_type).strip().lower()
        if "yÄ±llÄ±k" in leave_type or "yillik" in leave_type:
            return "yillik"
        if "ÅŸua" in leave_type or "sua" in leave_type:
            return "sua"
        if "rapor" in leave_type or "saÄŸlÄ±k" in leave_type or "saglik" in leave_type:
            return "rapor"
        return "diger"

    def _get_monthly_leave_stats(self, registry):
        stats = {
            "aylik_izinli_personel_toplam": 0,
            "aylik_izinli_yillik": 0,
            "aylik_izinli_sua": 0,
            "aylik_izinli_rapor": 0,
            "aylik_izinli_diger": 0,
        }
        try:
            today = datetime.now()
            month_start = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                month_end = datetime(today.year + 1, 1, 1).strftime("%Y-%m-%d")
            else:
                month_end = datetime(today.year, today.month + 1, 1).strftime("%Y-%m-%d")

            records = registry.get("Izin_Giris").get_all()
            by_type = {"yillik": set(), "sua": set(), "rapor": set(), "diger": set()}
            all_personnel = set()

            for row in records:
                status = str(row.get("Durum", "")).strip().lower()
                if status == "iptal":
                    continue

                personel_id = str(row.get("Personelid", "")).strip()
                start_date = self._parse_date(row.get("BaslamaTarihi", ""))
                end_date = self._parse_date(row.get("BitisTarihi", "")) or start_date
                if not personel_id or not start_date:
                    continue

                if start_date < month_end and end_date >= month_start:
                    leave_type = self._classify_leave_type(row.get("IzinTipi", ""))
                    by_type[leave_type].add(personel_id)
                    all_personnel.add(personel_id)

            stats["aylik_izinli_personel_toplam"] = len(all_personnel)
            stats["aylik_izinli_yillik"] = len(by_type["yillik"])
            stats["aylik_izinli_sua"] = len(by_type["sua"])
            stats["aylik_izinli_rapor"] = len(by_type["rapor"])
            stats["aylik_izinli_diger"] = len(by_type["diger"])
        except Exception as e:
            logger.warning(f"AylÄ±k izinli personel hesaplama hatasÄ±: {e}")
        return stats

class StatCard(QGroupBox):
    """Dashboard iÃ§in tÄ±klanabilir bir istatistik kartÄ±."""
    clicked = Signal()

    def __init__(self, title, icon, parent=None):
        super().__init__(title, parent)
        self.setObjectName("statCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(
            f"""
            QGroupBox#statCard {{
                font-size: 13px;
                font-weight: 700;
                color: #c9d1d9;
                border: 1px solid {ThemeManager.get_dark_theme_color("BORDER_PRIMARY")};
                border-radius: 14px;
                margin-top: 11px;
                background-color: #151b24;
            }}
            QGroupBox#statCard:hover {{
                border: 1px solid #3f8cff;
                background-color: #192233;
            }}
            QGroupBox#statCard::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 10px;
                color: #dce7ff;
            }}
        """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(15)

        self.icon_label = QLabel(icon)
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet(
            "font-size: 24px; "
            "background-color: rgba(74, 144, 255, 0.18); "
            "color: #9ec5ff; "
            "border: 1px solid rgba(74, 144, 255, 0.35); "
            "border-radius: 24px;"
        )
        layout.addWidget(self.icon_label)

        v_layout = QVBoxLayout()
        v_layout.setSpacing(0)
        
        self.value_label = QLabel("...")
        self.value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e0e2ea; border: none; background: transparent;")
        v_layout.addWidget(self.value_label)

        self.desc_label = QLabel("YÃ¼kleniyor")
        self.desc_label.setStyleSheet("font-size: 12px; color: #8b949e; border: none; background: transparent;")
        v_layout.addWidget(self.desc_label)
        
        layout.addLayout(v_layout)
        layout.addStretch()

    def set_data(self, value, description):
        if isinstance(value, int) and value == -1:
            self.value_label.setText("Hata")
            self.value_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #f85149; border: none; background: transparent;")
        else:
            self.value_label.setText(str(value))
            self.value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e0e2ea; border: none; background: transparent;")
        self.desc_label.setText(description)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)


class DashboardPage(QWidget):
    """Ana karÅŸÄ±lama sayfasÄ±, genel durumu gÃ¶sterir."""
    open_page_requested = Signal(str, str, dict)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._worker = None
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        self.setObjectName("dashboardPage")
        self._apply_visual_styles()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 15)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Genel BakÄ±ÅŸ")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0e2ea;")
        
        self.refresh_button = QPushButton("â†» Yenile")
        self.refresh_button.setFixedSize(100, 36)
        self.refresh_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.refresh_button.setStyleSheet(S.get("refresh_btn", ""))
        self.refresh_button.clicked.connect(self.load_data)

        self.btn_kapat = QPushButton("âœ• Kapat")
        self.btn_kapat.setFixedSize(90, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.btn_kapat)
        main_layout.addLayout(header_layout)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(158, 197, 255, 0.28);
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(158, 197, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 10, 0, 10)
        content_layout.setSpacing(20)

        # --- HatÄ±rlatmalar ---
        self.fhsz_reminder_frame = self._create_reminder_box(
            "Fiili Hizmet ZammÄ± HatÄ±rlatmasÄ±",
            "Her ayÄ±n 15'inde FHSZ hesaplamalarÄ±nÄ± kontrol etmeyi unutmayÄ±n."
        )
        content_layout.addWidget(self.fhsz_reminder_frame)

        # --- Cihaz Grubu ---
        cihaz_group = QGroupBox("ğŸ”¬ Cihaz YÃ¶netimi")
        cihaz_group.setStyleSheet(self._group_style())
        cihaz_grid = QGridLayout(cihaz_group)
        cihaz_grid.setSpacing(20)
        
        self.card_acik_arizalar = StatCard("AÃ§Ä±k ArÄ±za KayÄ±tlarÄ±", "âš ï¸")
        self.card_acik_arizalar.clicked.connect(
            lambda: self.open_page_requested.emit("CÄ°HAZ", "ArÄ±za Listesi", {"Durum": "AÃ§Ä±k"})
        )
        cihaz_grid.addWidget(self.card_acik_arizalar, 0, 0)

        self.card_yeni_arizalar = StatCard("Yeni ArÄ±zalar (1 Hafta)", "ğŸ†•")
        self.card_yeni_arizalar.clicked.connect(lambda: self.open_page_requested.emit("CÄ°HAZ", "ArÄ±za Listesi", {"Filtre": "Yeni"}))
        cihaz_grid.addWidget(self.card_yeni_arizalar, 0, 1)

        self.card_aylik_bakim = StatCard("Bu Ayki BakÄ±mlar", "ğŸ› ï¸")
        self.card_aylik_bakim.clicked.connect(lambda: self.open_page_requested.emit("CÄ°HAZ", "Periyodik BakÄ±m", {"Filtre": "BuAy"}))
        cihaz_grid.addWidget(self.card_aylik_bakim, 0, 2)

        self.card_gecmis_kalibrasyon = StatCard("Vadesi GeÃ§miÅŸ Kalibrasyonlar", "ğŸ“")
        self.card_gecmis_kalibrasyon.clicked.connect(
            lambda: self.open_page_requested.emit("CÄ°HAZ", "Kalibrasyon Takip", {"Filtre": "Gecmis"})
        )
        cihaz_grid.addWidget(self.card_gecmis_kalibrasyon, 1, 0)

        self.card_aylik_kalibrasyon = StatCard("Bu Ayki Kalibrasyonlar", "ğŸ“…")
        self.card_aylik_kalibrasyon.clicked.connect(lambda: self.open_page_requested.emit("CÄ°HAZ", "Kalibrasyon Takip", {"Filtre": "BuAy"}))
        cihaz_grid.addWidget(self.card_aylik_kalibrasyon, 1, 1)

        self.card_yaklasan_ndk = StatCard("YaklaÅŸan NDK LisanslarÄ±", "ğŸ“œ")
        self.card_yaklasan_ndk.clicked.connect(lambda: self.open_page_requested.emit("CÄ°HAZ", "Cihaz Listesi", {"Filtre": "YaklasanNDK"}))
        cihaz_grid.addWidget(self.card_yaklasan_ndk, 1, 2)
        content_layout.addWidget(cihaz_group)

        # --- Personel Grubu ---
        personel_group = QGroupBox("ğŸ‘¤ Personel")
        personel_group.setStyleSheet(self._group_style())
        personel_grid = QGridLayout(personel_group)
        personel_grid.setSpacing(20)

        self.card_aktif_personel = StatCard("Aktif Personel", "ğŸ‘¥")
        self.card_aktif_personel.clicked.connect(lambda: self.open_page_requested.emit("PERSONEL", "Personel Listesi", {"Filtre": "Aktif"}))
        personel_grid.addWidget(self.card_aktif_personel, 0, 0)

        self.card_aylik_izinli = StatCard("Bu Ay Ä°zinli Personel", "ğŸ—“ï¸")
        self.card_aylik_izinli.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "Personel Listesi", {"Filtre": "Ä°zinli"})
        )
        personel_grid.addWidget(self.card_aylik_izinli, 0, 1)
        content_layout.addWidget(personel_group)

        # --- SaÄŸlÄ±k Takibi Grubu ---
        saglik_group = QGroupBox("ğŸ¥ Personel SaÄŸlÄ±k Takibi")
        saglik_group.setStyleSheet(self._group_style())
        saglik_grid = QGridLayout(saglik_group)
        saglik_grid.setSpacing(20)

        self.card_yaklasan_saglik = StatCard("YaklaÅŸan Muayeneler (90 GÃ¼n)", "ğŸ©º")
        self.card_yaklasan_saglik.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "SaÄŸlÄ±k Takip", {"Filtre": "Yaklasan"})
        )
        saglik_grid.addWidget(self.card_yaklasan_saglik, 0, 0)

        self.card_gecmis_saglik = StatCard("Vadesi GeÃ§miÅŸ Muayeneler", "â°")
        self.card_gecmis_saglik.clicked.connect(
            lambda: self.open_page_requested.emit("PERSONEL", "SaÄŸlÄ±k Takip", {"Filtre": "Gecmis"})
        )
        saglik_grid.addWidget(self.card_gecmis_saglik, 0, 1)
        content_layout.addWidget(saglik_group)

        # --- RKE Grubu ---
        rke_group = QGroupBox("ğŸ›¡ï¸ RKE")
        rke_group.setStyleSheet(self._group_style())
        rke_grid = QGridLayout(rke_group)
        rke_grid.setSpacing(20)
        self.card_yaklasan_rke = StatCard("YaklaÅŸan RKE Muayeneleri", "ğŸ›¡ï¸")
        self.card_yaklasan_rke.clicked.connect(lambda: self.open_page_requested.emit("RKE", "RKE Muayene", {"Filtre": "Yaklasan"}))
        rke_grid.addWidget(self.card_yaklasan_rke, 0, 0)
        content_layout.addWidget(rke_group)

        # --- Sistem Grubu ---
        sistem_group = QGroupBox("âš™ï¸ Sistem SaÄŸlÄ±ÄŸÄ±")
        sistem_group.setStyleSheet(self._group_style())
        sistem_grid = QGridLayout(sistem_group)
        sistem_grid.setSpacing(20)

        
        self.card_hata_log = StatCard("Kritik Hata LoglarÄ±", "ğŸ“„")
        self.card_hata_log.clicked.connect(
            lambda: self.open_page_requested.emit("YÃ–NETÄ°CÄ° Ä°ÅLEMLERÄ°", "Log GÃ¶rÃ¼ntÃ¼leyici", {"Dosya": "errors.log", "Seviye": "ERROR"})
        )
        sistem_grid.addWidget(self.card_hata_log, 0, 0)

        self.card_log_boyutu = StatCard("Toplam Log Boyutu", "ğŸ—„ï¸")
        self.card_log_boyutu.clicked.connect(
            lambda: self.open_page_requested.emit("YÃ–NETÄ°CÄ° Ä°ÅLEMLERÄ°", "Log GÃ¶rÃ¼ntÃ¼leyici", {})
        )
        sistem_grid.addWidget(self.card_log_boyutu, 0, 1)
        content_layout.addWidget(sistem_group)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)

    def _create_reminder_box(self, title, text):
        frame = QGroupBox(f"ğŸ”” {title}")
        frame.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e3b341;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #e3b341;
                background-color: rgba(227, 179, 65, 0.08);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        layout = QVBoxLayout(frame)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-weight: normal; color: #c9d1d9; border: none; background: transparent;")
        layout.addWidget(label)
        frame.setVisible(False)
        return frame

    def _apply_visual_styles(self):
        self.setStyleSheet(
            S.get("page", "")
            + """
            QWidget#dashboardPage {
                background-color: #0f141d;
            }
            QLabel {
                color: #d8e1f0;
            }
            QPushButton {
                border-radius: 8px;
            }
            """
        )

    def _group_style(self):
        return """
            QGroupBox {
                border: 1px solid rgba(116, 139, 173, 0.35);
                border-radius: 14px;
                margin-top: 14px;
                padding-top: 10px;
                font-size: 14px;
                font-weight: 700;
                color: #dce7ff;
                background-color: rgba(23, 31, 44, 0.75);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 1px 10px;
                background-color: #101926;
                border-radius: 8px;
                color: #bfd7ff;
            }
        """

    def load_data(self):
        if self._worker and self._worker.isRunning():
            return # Zaten Ã§alÄ±ÅŸÄ±yor
        
        logger.info("Dashboard verileri yÃ¼kleniyor...")
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("YÃ¼kleniyor...")
        
        db_path = getattr(self._db, "db_path", DB_PATH)
        self._worker = DashboardWorker(db_path)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_data_ready(self, data):
        # FHSZ HatÄ±rlatma
        if datetime.now().day == 15:
            self.fhsz_reminder_frame.setVisible(True)
        else:
            self.fhsz_reminder_frame.setVisible(False)

        # Cihaz
        self.card_acik_arizalar.set_data(data.get('acik_arizalar', 0), "Ã‡Ã¶zÃ¼lmeyi bekleyen arÄ±za kayÄ±tlarÄ±")
        self.card_yeni_arizalar.set_data(data.get('yeni_arizalar', 0), "Son 7 gÃ¼nde aÃ§Ä±lan kayÄ±tlar")
        self.card_aylik_bakim.set_data(data.get('aylik_bakim', 0), "Bu ay planlanan bakÄ±mlar")
        self.card_gecmis_kalibrasyon.set_data(data.get('gecmis_kalibrasyon', 0), "SÃ¼resi geÃ§miÅŸ cihazlar")
        self.card_aylik_kalibrasyon.set_data(data.get('aylik_kalibrasyon', 0), "Bu ay geÃ§erlilik sÃ¼resi dolacaklar")
        self.card_yaklasan_ndk.set_data(data.get('yaklasan_ndk', 0), "6 ay iÃ§inde dolacak lisanslar")

        # Personel
        self.card_aktif_personel.set_data(data.get('aktif_personel', 0), "Sistemde aktif gÃ¶rÃ¼nen personel")
        yillik = data.get("aylik_izinli_yillik", 0)
        sua = data.get("aylik_izinli_sua", 0)
        rapor = data.get("aylik_izinli_rapor", 0)
        diger = data.get("aylik_izinli_diger", 0)
        izin_desc = f"YÄ±llÄ±k:{yillik} â€¢ Åua:{sua} â€¢ Rapor:{rapor} â€¢ DiÄŸer:{diger}"
        self.card_aylik_izinli.set_data(data.get("aylik_izinli_personel_toplam", 0), izin_desc)

        # RKE
        self.card_yaklasan_rke.set_data(data.get('yaklasan_rke', 0), "1 ay iÃ§inde muayenesi olanlar")

        # SaÄŸlÄ±k Takibi
        self.card_yaklasan_saglik.set_data(data.get('yaklasan_saglik', 0), "90 gÃ¼n iÃ§inde kontrolÃ¼ gelenler")
        gecmis = data.get('gecmis_saglik', 0)
        self.card_gecmis_saglik.set_data(gecmis, "ZamanÄ±nda yapÄ±lmamÄ±ÅŸ muayeneler")
        if isinstance(gecmis, int) and gecmis > 0:
            self.card_gecmis_saglik.value_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; color: #f85149; border: none; background: transparent;"
            )

        # Sistem
        self.card_hata_log.set_data(data.get('hata_log_satir', 0), "errors.log dosyasÄ±ndaki satÄ±r sayÄ±sÄ±")
        log_boyut = data.get('toplam_log_boyut_mb', 0)
        self.card_log_boyutu.set_data(f"{log_boyut:.2f} MB", "TÃ¼m log dosyalarÄ±nÄ±n toplamÄ±")

    def _on_worker_finished(self):
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("â†» Yenile")
        logger.info("Dashboard verileri yÃ¼klendi.")


