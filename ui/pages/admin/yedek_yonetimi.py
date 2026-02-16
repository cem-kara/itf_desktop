# -*- coding: utf-8 -*-
"""
Yedek Yönetimi
═══════════════════════════════════════════════════════════════
Mevcut yedekleri listeler; manuel yedek alma, geri yükleme
ve silme işlemlerini sağlar.

Altyapı:
  • database/migrations.py → MigrationManager.backup_database()
    Yedek dizini: data/backups/db_backup_YYYYMMDD_HHMMSS.db
  • Geri yükleme: shutil.copy2(yedek → data/local.db) + uygulama yeniden başlatma

Mimari:
  • Worker yok — tüm dosya işlemleri ana thread'de (hızlı, IO-bound değil)
  • Stiller: ThemeManager.get_all_component_styles()
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QMessageBox, QAbstractItemView,
    QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QColor

from core.logger import logger
from core.paths import DB_PATH
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()

# Yedek dizini migrations.py ile aynı konvansiyonu kullanır
BACKUP_DIR = Path(DB_PATH).parent / "backups"
MAX_YEDEK  = 10          # otomatik temizleme eşiği (migrations ile aynı)


class YedekYonetimiPage(QWidget):
    """Yedekleme yönetim ekranı."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._setup_ui()
        self.load_data()

    # ── UI kurulum ───────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setObjectName("yedekYonetimiPage")
        self.setStyleSheet(S.get("page", ""))

        ana = QVBoxLayout(self)
        ana.setContentsMargins(24, 20, 24, 20)
        ana.setSpacing(16)

        # ── Başlık + butonlar ────────────────────────────────────────────────
        baslik_satir = QHBoxLayout()

        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setFixedSize(90, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))

        baslik_satir.addStretch()
        baslik_satir.addWidget(self.btn_kapat)
        ana.addLayout(baslik_satir)

        # ── Bilgi kartları ───────────────────────────────────────────────────
        kart_satir = QHBoxLayout()
        kart_satir.setSpacing(12)

        self.lbl_adet     = self._bilgi_karti("Yedek Sayısı",   "—",  "📦")
        self.lbl_boyut    = self._bilgi_karti("Toplam Boyut",   "—",  "🗄️")
        self.lbl_son_yedek = self._bilgi_karti("Son Yedek",     "—",  "🕐")

        kart_satir.addWidget(self.lbl_adet[0])
        kart_satir.addWidget(self.lbl_boyut[0])
        kart_satir.addWidget(self.lbl_son_yedek[0])
        kart_satir.addStretch()
        ana.addLayout(kart_satir)

        # ── İşlem butonları ──────────────────────────────────────────────────
        btn_satir = QHBoxLayout()
        btn_satir.setSpacing(10)

        self.btn_yedek_al = QPushButton("💾  Manuel Yedek Al")
        self.btn_yedek_al.setFixedHeight(36)
        self.btn_yedek_al.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yedek_al.setStyleSheet(S.get("save_btn", ""))
        self.btn_yedek_al.clicked.connect(self._manuel_yedek_al)

        self.btn_geri_yukle = QPushButton("♻️  Geri Yükle")
        self.btn_geri_yukle.setFixedHeight(36)
        self.btn_geri_yukle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_geri_yukle.setStyleSheet(S.get("edit_btn", ""))
        self.btn_geri_yukle.setEnabled(False)
        self.btn_geri_yukle.clicked.connect(self._geri_yukle)

        self.btn_sil = QPushButton("🗑  Sil")
        self.btn_sil.setFixedHeight(36)
        self.btn_sil.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sil.setStyleSheet(S.get("danger_btn", ""))
        self.btn_sil.setEnabled(False)
        self.btn_sil.clicked.connect(self._yedek_sil)

        self.btn_yenile = QPushButton("↻ Yenile")
        self.btn_yenile.setFixedHeight(36)
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self.btn_yenile.clicked.connect(self.load_data)

        btn_satir.addWidget(self.btn_yedek_al)
        btn_satir.addWidget(self.btn_geri_yukle)
        btn_satir.addWidget(self.btn_sil)
        btn_satir.addStretch()
        btn_satir.addWidget(self.btn_yenile)
        ana.addLayout(btn_satir)

        # ── Tablo ────────────────────────────────────────────────────────────
        tablo_group = QGroupBox("Mevcut Yedekler")
        tablo_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(116,139,173,0.30);
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 8px;
                font-size: 13px;
                font-weight: 700;
                color: #bfd7ff;
                background: rgba(15, 20, 29, 0.6);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                background: #0f141d;
                border-radius: 6px;
            }
        """)
        tablo_layout = QVBoxLayout(tablo_group)
        tablo_layout.setContentsMargins(12, 12, 12, 12)

        self.tablo = QTableWidget()
        self.tablo.setColumnCount(4)
        self.tablo.setHorizontalHeaderLabels(["Dosya Adı", "Tarih", "Boyut", "Yol"])
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setShowGrid(False)
        self.tablo.setColumnHidden(3, True)   # yol gizli

        hdr = self.tablo.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.tablo.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                alternate-background-color: #111827;
                color: #c9d1d9;
                border: none;
                gridline-color: transparent;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: rgba(63,140,255,0.20);
                color: #e0e2ea;
            }
            QHeaderView::section {
                background-color: #161b26;
                color: #8b949e;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid rgba(116,139,173,0.20);
                padding: 6px 10px;
            }
        """)
        self.tablo.selectionModel().selectionChanged.connect(self._secim_degisti)
        tablo_layout.addWidget(self.tablo)

        # Uyarı notu
        self.lbl_not = QLabel(
            "⚠️  Geri yükleme işlemi mevcut veritabanının üzerine yazar. "
            "İşlem öncesinde otomatik yedek alınır."
        )
        self.lbl_not.setWordWrap(True)
        self.lbl_not.setStyleSheet(
            "color: #e3b341; font-size: 12px; "
            "background: rgba(227,179,65,0.07); "
            "border: 1px solid rgba(227,179,65,0.25); "
            "border-radius: 6px; padding: 8px 12px;"
        )
        tablo_layout.addWidget(self.lbl_not)

        ana.addWidget(tablo_group, 1)

    def _bilgi_karti(self, baslik: str, deger: str, ikon: str):
        """Küçük istatistik kartı; (frame, value_label) döndürür."""
        frame = QFrame()
        frame.setFixedHeight(72)
        frame.setMinimumWidth(160)
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        frame.setStyleSheet("""
            QFrame {
                background: #151b24;
                border: 1px solid rgba(116,139,173,0.25);
                border-radius: 10px;
            }
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(10)

        lbl_ikon = QLabel(ikon)
        lbl_ikon.setFixedSize(34, 34)
        lbl_ikon.setAlignment(Qt.AlignCenter)
        lbl_ikon.setStyleSheet(
            "font-size: 18px; background: rgba(74,144,255,0.15); "
            "border: 1px solid rgba(74,144,255,0.30); border-radius: 17px;"
        )

        v = QVBoxLayout()
        v.setSpacing(0)
        lbl_deger = QLabel(deger)
        lbl_deger.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e2ea; border: none; background: transparent;")
        lbl_baslik = QLabel(baslik)
        lbl_baslik.setStyleSheet("font-size: 11px; color: #8b949e; border: none; background: transparent;")
        v.addWidget(lbl_deger)
        v.addWidget(lbl_baslik)

        lay.addWidget(lbl_ikon)
        lay.addLayout(v)
        return frame, lbl_deger

    # ── Veri yükleme ─────────────────────────────────────────────────────────

    def load_data(self):
        """Yedek dizinini okuyup tabloyu doldurur."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        yedekler = sorted(
            BACKUP_DIR.glob("db_backup_*.db"),
            reverse=True   # en yeni en üstte
        )

        self.tablo.setRowCount(0)
        toplam_boyut = 0

        for yol in yedekler:
            boyut = yol.stat().st_size
            toplam_boyut += boyut

            # Dosya adından tarih parse et: db_backup_YYYYMMDD_HHMMSS.db
            tarih_str = self._dosyadan_tarih(yol.name)

            satir = self.tablo.rowCount()
            self.tablo.insertRow(satir)

            self.tablo.setItem(satir, 0, QTableWidgetItem(yol.name))
            self.tablo.setItem(satir, 1, QTableWidgetItem(tarih_str))
            self.tablo.setItem(satir, 2, QTableWidgetItem(self._boyut_fmt(boyut)))
            self.tablo.setItem(satir, 3, QTableWidgetItem(str(yol)))  # gizli

        # Kart güncelle
        adet = len(yedekler)
        self.lbl_adet[1].setText(str(adet))
        self.lbl_boyut[1].setText(self._boyut_fmt(toplam_boyut))
        son = self._dosyadan_tarih(yedekler[0].name) if yedekler else "—"
        self.lbl_son_yedek[1].setText(son)

        # MAX_YEDEK uyarısı
        if adet >= MAX_YEDEK:
            self.lbl_adet[1].setStyleSheet(
                "font-size: 18px; font-weight: bold; color: #e3b341; border: none; background: transparent;"
            )
        else:
            self.lbl_adet[1].setStyleSheet(
                "font-size: 18px; font-weight: bold; color: #e0e2ea; border: none; background: transparent;"
            )

        self._secim_degisti()
        logger.info(f"Yedek listesi yüklendi: {adet} dosya, {self._boyut_fmt(toplam_boyut)}")

    # ── İşlemler ─────────────────────────────────────────────────────────────

    def _manuel_yedek_al(self):
        """MigrationManager aracılığıyla yeni yedek oluşturur."""
        try:
            from database.migrations import MigrationManager
            mgr = MigrationManager(DB_PATH)
            yol = mgr.backup_database()
            if yol:
                self.load_data()
                QMessageBox.information(
                    self, "Yedek Alındı",
                    f"Yedek başarıyla oluşturuldu:\n{Path(yol).name}"
                )
            else:
                QMessageBox.warning(self, "Uyarı", "Yedekleme başarısız oldu.")
        except Exception as e:
            logger.error(f"Manuel yedek hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedekleme sırasında hata:\n{e}")

    def _geri_yukle(self):
        """Seçili yedeği mevcut veritabanının üzerine yazar."""
        yol = self._secili_yol()
        if not yol:
            return

        onay = QMessageBox.question(
            self,
            "Geri Yükleme Onayı",
            f"<b>{Path(yol).name}</b> yedeği geri yüklenecek.<br><br>"
            "İşlem öncesinde mevcut veritabanı otomatik olarak yedeklenecektir.<br>"
            "Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if onay != QMessageBox.Yes:
            return

        try:
            # 1) Mevcut DB'yi yedekle
            from database.migrations import MigrationManager
            mgr = MigrationManager(DB_PATH)
            onceki_yedek = mgr.backup_database()
            logger.info(f"Geri yükleme öncesi yedek: {onceki_yedek}")

            # 2) Seçili yedeği üzerine kopyala
            shutil.copy2(yol, DB_PATH)
            logger.info(f"Geri yükleme tamamlandı: {yol} → {DB_PATH}")

            self.load_data()

            QMessageBox.information(
                self, "Geri Yükleme Tamamlandı",
                "Veritabanı başarıyla geri yüklendi.\n\n"
                "Değişikliklerin geçerli olması için uygulamayı yeniden başlatın."
            )
        except Exception as e:
            logger.error(f"Geri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Geri yükleme sırasında hata:\n{e}")

    def _yedek_sil(self):
        """Seçili yedeği kalıcı olarak siler."""
        yol = self._secili_yol()
        if not yol:
            return

        onay = QMessageBox.question(
            self,
            "Silme Onayı",
            f"<b>{Path(yol).name}</b> kalıcı olarak silinecek.\n"
            "Bu işlem geri alınamaz. Devam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if onay != QMessageBox.Yes:
            return

        try:
            Path(yol).unlink()
            logger.info(f"Yedek silindi: {yol}")
            self.load_data()
        except Exception as e:
            logger.error(f"Yedek silme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Silme sırasında hata:\n{e}")

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def _secim_degisti(self):
        var = bool(self.tablo.selectedItems())
        self.btn_geri_yukle.setEnabled(var)
        self.btn_sil.setEnabled(var)

    def _secili_yol(self) -> str | None:
        row = self.tablo.currentRow()
        if row < 0:
            return None
        item = self.tablo.item(row, 3)
        return item.text() if item else None

    @staticmethod
    def _dosyadan_tarih(dosya_adi: str) -> str:
        """db_backup_20260216_143022.db → 16.02.2026 14:30:22"""
        try:
            ksm = dosya_adi.replace("db_backup_", "").replace(".db", "")
            dt  = datetime.strptime(ksm, "%Y%m%d_%H%M%S")
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return dosya_adi

    @staticmethod
    def _boyut_fmt(bayt: int) -> str:
        if bayt >= 1_048_576:
            return f"{bayt / 1_048_576:.2f} MB"
        if bayt >= 1_024:
            return f"{bayt / 1_024:.1f} KB"
        return f"{bayt} B"
