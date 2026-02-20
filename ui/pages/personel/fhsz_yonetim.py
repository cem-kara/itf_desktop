# -*- coding: utf-8 -*-
"""
FHSZ (Fiili Hizmet Süresi Zammı / Şua) Hesaplama ve Düzenleme

Orijinal formdan birebir taşınan çalışma prensibi:
──────────────────────────────────────────────────
• Dönem     : Ayın 15'i → sonraki ayın 14'ü  (relativedelta)
• Eşik      : 26.04.2022 — öncesi hesaplanamaz
• Filtre    : Sadece belirli HizmetSınıfı dahil edilir
• Koşul     : Sabitler → Kod="Gorev_Yeri", Aciklama'da "A" → Koşul A
  - Koşul A : puan = (iş_günü - izin) × 7 saat
  - Koşul B : puan = 0
• İzin      : Dönem aralığıyla kesişim (overlap) iş günü hesabı
• Pasif     : AyrılışTarihi dönem içindeyse, bitiş = ayrılış
• Kayıt     : Eski sil → yeni ekle → şua bakiye güncelle
• Hesap     : hesaplamalar.py → sua_hak_edis_hesapla, is_gunu_hesapla
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QStyledItemDelegate,
    QAbstractItemView, QStyle
)
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QBrush, QPen, QPainterPath

from core.logger import logger
from core.date_utils import parse_date as parse_any_date
from core.hesaplamalar import sua_hak_edis_hesapla, is_gunu_hesapla, tr_upper
from ui.styles import Colors, DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer

def _parse_date(val):
    parsed = parse_any_date(val)
    if not parsed:
        return None
    return datetime.combine(parsed, datetime.min.time())


# ─── Sabitler ───
FHSZ_ESIK = datetime(2022, 4, 26)
KOSUL_A_SAAT = 7

IZIN_VERILEN_SINIFLAR = [
    "Akademik Personel", "Asistan Doktor",
    "Radyasyon Görevlisi", "Hemşire",
]

AY_ISIMLERI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

TABLO_KOLONLARI = [
    "Kimlik No", "Adı Soyadı", "Birim", "Çalışma Koşulu",
    "Ait Yıl", "Dönem", "Aylık Gün", "Kullanılan İzin",
    "Fiili Çalışma (Saat)",
]

# Kolon indeksleri
C_KIMLIK, C_AD, C_BIRIM, C_KOSUL = 0, 1, 2, 3
C_YIL, C_DONEM, C_GUN, C_IZIN, C_SAAT = 4, 5, 6, 7, 8


# ═══════════════════════════════════════════════
#  DELEGATE: Çalışma Koşulu ComboBox  (Kolon 3)
# ═══════════════════════════════════════════════

class KosulDelegate(QStyledItemDelegate):
    """
    Orijinaldeki ComboDelegate'in birebir karşılığı.
    Çalışma Koşulu A / B seçtirip badge olarak gösterir.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = ["Çalışma Koşulu A", "Çalışma Koşulu B"]

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkTheme.INPUT_BG}; color: {DarkTheme.TEXT_PRIMARY};
                border: 2px solid {DarkTheme.INPUT_BORDER_FOCUS}; border-radius: 4px;
                padding: 4px 8px; font-size: 12px; min-height: 24px;
            }}
            QComboBox::drop-down {{ border: none; width: 26px; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {DarkTheme.INPUT_BORDER_FOCUS};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DarkTheme.INPUT_BG}; color: {DarkTheme.TEXT_SECONDARY};
                selection-background-color: rgba(29,117,254,0.4);
                selection-color: {Colors.WHITE}; border: 1px solid {DarkTheme.INPUT_BORDER_FOCUS};
            }}
            QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px; }}
        """)
        # Editor konumlandiktan sonra listeyi ac (tek tikta, flash olmadan)
        QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.EditRole)
        if text in self.items:
            editor.setCurrentText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        """Badge çizimi: Koşul A → yeşil, Koşul B → mavi."""
        bg = QColor(29, 117, 254, 60) if option.state & QStyle.State_Selected \
            else QColor("transparent")
        painter.fillRect(option.rect, bg)

        text = str(index.data(Qt.DisplayRole) or "")
        if "KOŞULU A" in str(text).upper():
            badge_bg = QColor(46, 125, 50, 140)
            border_c = QColor("#66bb6a")
        else:
            badge_bg = QColor(21, 101, 192, 140)
            border_c = QColor("#42a5f5")

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect)
        rect.adjust(5, 4, -5, -4)
        path = QPainterPath()
        path.addRoundedRect(rect, 4, 4)
        painter.setBrush(QBrush(badge_bg))
        painter.setPen(QPen(border_c, 1.5))
        painter.drawPath(path)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.restore()


# ═══════════════════════════════════════════════
#  DELEGATE: Fiili Çalışma sonuç badge  (Kolon 8)
# ═══════════════════════════════════════════════

class SonucDelegate(QStyledItemDelegate):
    """Orijinaldeki SonucDelegate'in birebir karşılığı."""
    def paint(self, painter, option, index):
        bg = QColor(29, 117, 254, 60) if option.state & QStyle.State_Selected \
            else QColor("transparent")
        painter.fillRect(option.rect, bg)

        try:
            deger = float(index.data(Qt.DisplayRole))
        except (ValueError, TypeError):
            deger = 0

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect)
        rect.adjust(8, 5, -8, -5)

        if deger > 0:
            c_bg, c_border, c_text = QColor(27, 94, 32, 140), QColor("#66bb6a"), QColor("#ffffff")
        else:
            c_bg, c_border, c_text = QColor(62, 62, 62, 80), QColor("#555"), QColor("#aaaaaa")

        path = QPainterPath()
        path.addRoundedRect(rect, 4, 4)
        painter.setBrush(QBrush(c_bg))
        painter.setPen(QPen(c_border, 1))
        painter.drawPath(path)
        painter.setPen(c_text)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{deger:.0f}")
        painter.restore()


# ═══════════════════════════════════════════════
#  FHSZ YÖNETİM SAYFASI
# ═══════════════════════════════════════════════

class FHSZYonetimPage(QWidget):

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._all_personel = []
        self._all_izin = []
        self._tatil_listesi_np = []       # ["YYYY-MM-DD", ...] numpy formatı
        self._birim_kosul_map = {}        # {TR_UPPER(birim): "A" | "B"}

        self._setup_ui()
        self._connect_signals()

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(10)

        # ── ÜST BAR: Dönem Seçimi ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fp = QHBoxLayout(filter_frame)
        fp.setContentsMargins(12, 8, 12, 8)
        fp.setSpacing(8)

        lbl_t = QLabel("FHSZ Hesaplama ve Duzenleme")
        lbl_t.setStyleSheet(S.get("section_title", ""))
        fp.addWidget(lbl_t)

        self._add_sep(fp)

        # Yıl
        fp.addWidget(self._make_label("Yıl:"))
        self.cmb_yil = QComboBox()
        self.cmb_yil.setStyleSheet(S["combo"])
        self.cmb_yil.setFixedWidth(80)
        by = datetime.now().year
        for y in range(by - 5, by + 5):
            self.cmb_yil.addItem(str(y))
        self.cmb_yil.setCurrentText(str(by))
        fp.addWidget(self.cmb_yil)

        # Ay
        fp.addWidget(self._make_label("Ay:"))
        self.cmb_ay = QComboBox()
        self.cmb_ay.setStyleSheet(S["combo"])
        self.cmb_ay.setFixedWidth(120)
        self.cmb_ay.addItems(AY_ISIMLERI)
        self.cmb_ay.setCurrentIndex(max(0, datetime.now().month - 1))
        fp.addWidget(self.cmb_ay)

        self._add_sep(fp)

        self.lbl_donem = QLabel("...")
        self.lbl_donem.setStyleSheet(S["donem_label"])
        fp.addWidget(self.lbl_donem)

        fp.addStretch()

        self.btn_hesapla = QPushButton("LISTELE VE HESAPLA")
        self.btn_hesapla.setStyleSheet(S["calc_btn"])
        self.btn_hesapla.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_hesapla, "bar_chart", color=DarkTheme.TEXT_PRIMARY, size=14)
        fp.addWidget(self.btn_hesapla)

        main.addWidget(filter_frame)

        # ── TABLO (QTableWidget — orijinaldeki gibi) ──
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(TABLO_KOLONLARI))
        self.tablo.setHorizontalHeaderLabels(TABLO_KOLONLARI)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setStyleSheet(S["table"])
        self.tablo.setEditTriggers(QAbstractItemView.SelectedClicked | QAbstractItemView.DoubleClicked)

        h = self.tablo.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(C_KIMLIK, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(C_KOSUL, QHeaderView.Fixed)
        self.tablo.setColumnWidth(C_KOSUL, 170)
        h.setSectionResizeMode(C_SAAT, QHeaderView.Fixed)
        self.tablo.setColumnWidth(C_SAAT, 130)

        # AitYıl + Dönem gizli
        self.tablo.setColumnHidden(C_YIL, True)
        self.tablo.setColumnHidden(C_DONEM, True)

        # Delegate'ler
        self.tablo.setItemDelegateForColumn(C_KOSUL, KosulDelegate(self.tablo))
        self.tablo.setItemDelegateForColumn(C_SAAT, SonucDelegate(self.tablo))

        main.addWidget(self.tablo, 1)

        # ── ALT BAR ──
        bot_frame = QFrame()
        bot_frame.setStyleSheet(S["filter_panel"])
        bf = QHBoxLayout(bot_frame)
        bf.setContentsMargins(12, 8, 12, 8)
        bf.setSpacing(12)

        self.lbl_durum = QLabel("Hazır")
        self.lbl_durum.setStyleSheet(S["footer_label"])
        bf.addWidget(self.lbl_durum)

        bf.addStretch()

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(160)
        self.progress.setFixedHeight(14)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 3px; font-size: 10px; color: {DarkTheme.TEXT_MUTED};
            }}
            QProgressBar::chunk {{
                background-color: rgba(29,117,254,0.5); border-radius: 2px;
            }}
        """)
        bf.addWidget(self.progress)


        self.btn_kaydet = QPushButton("KAYDET / GUNCELLE")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        bf.addWidget(self.btn_kaydet)

        main.addWidget(bot_frame)
        self._donem_guncelle()

    # ─── UI yardımcıları ───

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(S["label"])
        return lbl

    def _add_sep(self, layout):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet(f"background-color: {DarkTheme.BORDER_PRIMARY};")
        layout.addWidget(sep)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self.btn_hesapla.clicked.connect(self._baslat_kontrol)
        self.btn_kaydet.clicked.connect(self._kaydet_baslat)
        self.cmb_yil.currentIndexChanged.connect(self._donem_guncelle)
        self.cmb_ay.currentIndexChanged.connect(self._donem_guncelle)
        self.tablo.itemChanged.connect(self._hucre_degisti)

    # ═══════════════════════════════════════════
    #  DÖNEM: 15'i → sonraki ayın 14'ü
    # ═══════════════════════════════════════════

    def _get_donem_aralik(self):
        """Dönem başlangıç/bitiş → (datetime, datetime)"""
        try:
            yil = int(self.cmb_yil.currentText())
            ay_idx = self.cmb_ay.currentIndex() + 1   # 1-12
            donem_bas = datetime(yil, ay_idx, 15)
            donem_bit = donem_bas + relativedelta(months=1) - timedelta(days=1)
            return donem_bas, donem_bit
        except Exception:
            return None, None

    def _donem_guncelle(self):
        donem_bas, donem_bit = self._get_donem_aralik()
        if donem_bas and donem_bit:
            self.lbl_donem.setText(
                f"Dönem: {donem_bas.strftime('%d.%m.%Y')} — {donem_bit.strftime('%d.%m.%Y')}"
            )

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME  (sayfa açılışında)
    # ═══════════════════════════════════════════

    def load_data(self):
        """Personel, izin, tatil, sabitler(Gorev_Yeri) yükle."""
        if not self._db:
            return

        self.lbl_durum.setText("Veriler yükleniyor...")
        self.progress.setVisible(True)

        try:
            from core.di import get_registry
            registry = get_registry(self._db)

            # 1. Personeller
            self._all_personel = registry.get("Personel").get_all()

            # 2. İzinler
            self._all_izin = registry.get("Izin_Giris").get_all()

            # 3. Tatiller → numpy busday_count formatı
            try:
                tatiller = registry.get("Tatiller").get_all()
                self._tatil_listesi_np = []
                for r in tatiller:
                    d = _parse_date(r.get("Tarih", ""))
                    if d:
                        self._tatil_listesi_np.append(d.strftime("%Y-%m-%d"))
            except Exception:
                self._tatil_listesi_np = []

            # 4. Sabitler → Kod="Gorev_Yeri"
            #    MenuEleman = birim adı | Aciklama = "Çalışma Koşulu A / B"
            sabitler = registry.get("Sabitler").get_all()

            self._birim_kosul_map = {}

            for r in sabitler:
                # Sadece Gorev_Yeri olanlar
                if str(r.get("Kod", "")).strip() != "Gorev_Yeri":
                    continue

                birim = tr_upper(str(r.get("MenuEleman", "")).strip())
                aciklama = tr_upper(str(r.get("Aciklama", "")).strip())

                if not birim:
                    continue

                # 🔴 KRİTİK DÜZELTME BURASI
                if "KOŞULU A" in aciklama:
                    self._birim_kosul_map[birim] = "A"
                elif "KOŞULU B" in aciklama:
                    self._birim_kosul_map[birim] = "B"
                else:
                    logger.warning(
                        f"Gorev_Yeri için tanımsız çalışma koşulu: "
                        f"Birim={birim}, Aciklama={aciklama}"
                    )

            self.progress.setVisible(False)
            self.lbl_durum.setText("Veriler yüklendi.")

            logger.info(
                f"FHSZ veri yüklendi: {len(self._all_personel)} personel, "
                f"{len(self._all_izin)} izin, {len(self._tatil_listesi_np)} tatil, "
                f"{len(self._birim_kosul_map)} birim koşul"
            )


        except Exception as e:
            self.progress.setVisible(False)
            self.lbl_durum.setText(f"Veri yükleme hatası: {e}")
            logger.error(f"FHSZ veri yükleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  YARDIMCI: Tablo işlemleri
    # ═══════════════════════════════════════════

    def _set_item(self, row, col, text):
        """Salt-okunur hücre ekle."""
        item = QTableWidgetItem(str(text))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tablo.setItem(row, col, item)

    def _satir_hesapla(self, row):
        """
        Orijinaldeki _satir_hesapla — Koşul değişince puanı yeniden hesapla.
        Koşul A → (is_gunu - izin) × 7
        Koşul B → 0
        """
        try:
            kosul = self.tablo.item(row, C_KOSUL).text()
            is_gunu = int(self.tablo.item(row, C_GUN).text())
            izin = int(self.tablo.item(row, C_IZIN).text())
            puan = 0
            if "KOŞULU A" in tr_upper(kosul):
                net = max(0, is_gunu - izin)
                puan = net * KOSUL_A_SAAT
            self.tablo.setItem(row, C_SAAT, QTableWidgetItem(str(puan)))
        except Exception:
            pass

    def _hucre_degisti(self, item):
        """Koşul kolonu değiştiğinde puanı yeniden hesapla."""
        if item.column() == C_KOSUL:
            self._satir_hesapla(item.row())

    # ═══════════════════════════════════════════
    #  İZİN KESİŞİM HESABI  (orijinal: kesisim_izin_gunu_hesapla)
    # ═══════════════════════════════════════════

    def _kesisim_izin_gunu(self, kimlik, donem_bas, donem_bit):
        """
        Personelin izin kayıtlarıyla dönem aralığının kesişen
        iş günlerini hesaplar (numpy busday_count).
        """
        toplam = 0
        kimlik_str = str(kimlik).strip()

        for iz in self._all_izin:
            if str(iz.get("Personelid", "")).strip() != kimlik_str:
                continue
            if str(iz.get("Durum", "")).strip() == "İptal":
                continue

            izin_bas = _parse_date(iz.get("BaslamaTarihi", ""))
            izin_bit = _parse_date(iz.get("BitisTarihi", ""))
            if not izin_bas or not izin_bit:
                continue

            # Kesişim aralığı
            k_bas = max(donem_bas, izin_bas)
            k_bit = min(donem_bit, izin_bit)

            if k_bas <= k_bit:
                toplam += is_gunu_hesapla(k_bas, k_bit, self._tatil_listesi_np)

        return toplam

    # ═══════════════════════════════════════════
    #  ⚡ LİSTELE VE HESAPLA
    # ═══════════════════════════════════════════

    def _baslat_kontrol(self):
        """
        Orijinaldeki baslat_kontrol:
        1. FHSZ_Puantaj'da mevcut kayıt var mı kontrol et
        2. Varsa → _kayitli_veriyi_yukle + eksik personel ekle
        3. Yoksa → _sifirdan_hesapla
        """
        donem_bas, donem_bit = self._get_donem_aralik()
        if not donem_bas or not donem_bit:
            return

        # 26.04.2022 eşik kontrolü
        if donem_bit < FHSZ_ESIK:
            QMessageBox.warning(self, "Uyarı", "26.04.2022 öncesi hesaplanamaz.")
            return

        self.tablo.setRowCount(0)
        self.btn_hesapla.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_durum.setText("Kayıtlar kontrol ediliyor...")

        yil_str = self.cmb_yil.currentText()
        ay_str = self.cmb_ay.currentText()

        try:
            from core.di import get_registry
            registry = get_registry(self._db)

            # Mevcut kayıtları kontrol et
            tum_puantaj = registry.get("FHSZ_Puantaj").get_all()
            mevcut = [
                r for r in tum_puantaj
                if str(r.get("AitYil", "")).strip() == yil_str
                and str(r.get("Donem", "")).strip() == ay_str
            ]

            if mevcut:
                self._kayitli_veriyi_yukle(mevcut)
            else:
                self._sifirdan_hesapla()

        except Exception as e:
            logger.error(f"FHSZ kontrol hatası: {e}")
            QMessageBox.critical(self, "Hata", str(e))

        self.progress.setVisible(False)
        self.btn_hesapla.setEnabled(True)

    # ───────────────────────────────────────────
    #  Kayıtlı veriyi yükle + eksik personel ekle
    # ───────────────────────────────────────────

    def _kayitli_veriyi_yukle(self, mevcut_rows):
        """Orijinaldeki _kayitli_veriyi_yukle."""
        self.lbl_durum.setText(f"Veritabanından {len(mevcut_rows)} kayıt yüklendi.")
        self.tablo.blockSignals(True)
        self.tablo.setRowCount(0)
        mevcut_tcler = []

        for row_data in mevcut_rows:
            row_idx = self.tablo.rowCount()
            self.tablo.insertRow(row_idx)
            kimlik = str(row_data.get("Personelid", "")).strip()
            mevcut_tcler.append(kimlik)

            self._set_item(row_idx, C_KIMLIK, kimlik)
            self._set_item(row_idx, C_AD, row_data.get("AdSoyad", ""))
            self._set_item(row_idx, C_BIRIM, row_data.get("Birim", ""))

            kosul = row_data.get("CalismaKosulu") or "Çalışma Koşulu B"
            item_k = QTableWidgetItem(str(kosul))
            item_k.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.tablo.setItem(row_idx, C_KOSUL, item_k)

            self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
            self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())
            self._set_item(row_idx, C_GUN, str(row_data.get("AylikGun", "0")))
            self._set_item(row_idx, C_IZIN, str(row_data.get("KullanilanIzin", "0")))
            self._set_item(row_idx, C_SAAT, str(row_data.get("FiiliCalismaSaat", "0")))

        # ── EKSİK PERSONEL SENKRONİZASYONU ──
        try:
            donem_bas, donem_bit = self._get_donem_aralik()
            hesap_bas = donem_bas if donem_bas >= FHSZ_ESIK else FHSZ_ESIK

            yeni_sayi = self._eksik_personel_ekle(
                mevcut_tcler, hesap_bas, donem_bit
            )

            if yeni_sayi > 0:
                QMessageBox.information(
                    self, "Bilgi",
                    f"Listede olmayan {yeni_sayi} yeni personel eklendi."
                )
        except Exception:
            pass

        self.tablo.blockSignals(False)

    # ───────────────────────────────────────────
    #  Sıfırdan hesapla
    # ───────────────────────────────────────────

    def _sifirdan_hesapla(self):
        """Orijinaldeki _sifirdan_hesapla."""
        self.lbl_durum.setText("Yeni hesaplama yapıldı.")
        self.tablo.blockSignals(True)

        try:
            donem_bas, donem_bit = self._get_donem_aralik()
            if donem_bit < FHSZ_ESIK:
                self.tablo.blockSignals(False)
                return

            hesap_bas = donem_bas if donem_bas >= FHSZ_ESIK else FHSZ_ESIK

            if not self._all_personel:
                self.tablo.blockSignals(False)
                return

            sorted_personel = sorted(
                self._all_personel,
                key=lambda p: str(p.get("AdSoyad", ""))
            )

            for p in sorted_personel:
                kimlik = str(p.get("KimlikNo", "")).strip()
                sinif = str(p.get("HizmetSinifi", "")).strip()
                if sinif not in IZIN_VERILEN_SINIFLAR:
                    continue

                ad = p.get("AdSoyad", "")
                birim = str(p.get("GorevYeri", "")).strip()
                durum = str(p.get("Durum", "Aktif")).strip()

                # Pasif personel kontrolü
                kisi_bit = donem_bit
                if durum == "Pasif":
                    ayrilis = _parse_date(p.get("AyrilisTarihi", ""))
                    if ayrilis:
                        if ayrilis < hesap_bas:
                            continue
                        if ayrilis < donem_bit:
                            kisi_bit = ayrilis

                row_idx = self.tablo.rowCount()
                self.tablo.insertRow(row_idx)

                self._set_item(row_idx, C_KIMLIK, kimlik)
                self._set_item(row_idx, C_AD, ad)
                self._set_item(row_idx, C_BIRIM, birim)

                # Çalışma koşulu: birim_kosul_map'ten
                kosul = "Çalışma Koşulu B"
                birim_upper = tr_upper(birim)
                if birim_upper in self._birim_kosul_map \
                   and self._birim_kosul_map[birim_upper] == "A":
                    kosul = "Çalışma Koşulu A"
                item_k = QTableWidgetItem(kosul)
                item_k.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                self.tablo.setItem(row_idx, C_KOSUL, item_k)

                self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
                self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())

                # İş günü (numpy busday_count)
                ozel_is_gunu = is_gunu_hesapla(hesap_bas, kisi_bit, self._tatil_listesi_np)
                self._set_item(row_idx, C_GUN, str(ozel_is_gunu))

                # İzin kesişim
                izin_gunu = self._kesisim_izin_gunu(kimlik, hesap_bas, kisi_bit)
                self._set_item(row_idx, C_IZIN, str(izin_gunu))

                # Puan hesapla
                self._satir_hesapla(row_idx)

        except Exception as e:
            logger.error(f"FHSZ sıfırdan hesaplama hatası: {e}")
            QMessageBox.critical(self, "Hata", str(e))

        self.tablo.blockSignals(False)

    # ───────────────────────────────────────────
    #  Eksik personel ekle  (mevcut kayıtlarda olmayan)
    # ───────────────────────────────────────────

    def _eksik_personel_ekle(self, mevcut_tcler, hesap_bas, donem_bit):
        """Listede olmayan personelleri ekle, yeni eklenen sayısını döndür."""
        yeni_sayi = 0

        if not self._all_personel:
            return 0

        sorted_personel = sorted(
            self._all_personel,
            key=lambda p: str(p.get("AdSoyad", ""))
        )

        for p in sorted_personel:
            kimlik = str(p.get("KimlikNo", "")).strip()
            if kimlik in mevcut_tcler:
                continue

            sinif = str(p.get("HizmetSinifi", "")).strip()
            if sinif not in IZIN_VERILEN_SINIFLAR:
                continue

            durum = str(p.get("Durum", "Aktif")).strip()
            kisi_bit = donem_bit
            if durum == "Pasif":
                ayrilis = _parse_date(p.get("AyrilisTarihi", ""))
                if ayrilis:
                    if ayrilis < hesap_bas:
                        continue
                    if ayrilis < donem_bit:
                        kisi_bit = ayrilis

            row_idx = self.tablo.rowCount()
            self.tablo.insertRow(row_idx)
            yeni_sayi += 1

            self._set_item(row_idx, C_KIMLIK, kimlik)
            self._set_item(row_idx, C_AD, p.get("AdSoyad", ""))
            birim = str(p.get("GorevYeri", "")).strip()
            self._set_item(row_idx, C_BIRIM, birim)

            kosul = "Çalışma Koşulu B"
            birim_upper = tr_upper(birim)
            if birim_upper in self._birim_kosul_map \
               and self._birim_kosul_map[birim_upper] == "A":
                kosul = "Çalışma Koşulu A"
            item_k = QTableWidgetItem(kosul)
            item_k.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.tablo.setItem(row_idx, C_KOSUL, item_k)

            self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
            self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())

            ozel_is_gunu = is_gunu_hesapla(hesap_bas, kisi_bit, self._tatil_listesi_np)
            self._set_item(row_idx, C_GUN, str(ozel_is_gunu))

            izin_gunu = self._kesisim_izin_gunu(kimlik, hesap_bas, kisi_bit)
            self._set_item(row_idx, C_IZIN, str(izin_gunu))

            self._satir_hesapla(row_idx)

            # Yeni personel → sarı arka plan
            for c in range(self.tablo.columnCount()):
                item = self.tablo.item(row_idx, c)
                if item:
                    item.setBackground(QColor(77, 77, 51, 100))

        return yeni_sayi

    # ═══════════════════════════════════════════
    #  💾 KAYDET / GÜNCELLE
    # ═══════════════════════════════════════════

    def _kaydet_baslat(self):
        """
        Orijinaldeki kayıt prensibi:
        1. Tablo boşsa çık
        2. Mevcut dönem kayıtlarını say
        3. Varsa onay al → eski sil → yeni ekle
        4. Yoksa doğrudan ekle
        5. Şua bakiyesi güncelle
        """
        if self.tablo.rowCount() == 0:
            return

        yil_str = self.cmb_yil.currentText()
        ay_str = self.cmb_ay.currentText()

        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("FHSZ_Puantaj")

            # Mevcut kayıt kontrol
            tum = repo.get_all()
            mevcut_sayisi = sum(
                1 for r in tum
                if str(r.get("AitYil", "")).strip() == yil_str
                and str(r.get("Donem", "")).strip() == ay_str
            )

            # Onay
            if mevcut_sayisi > 0:
                cevap = QMessageBox.question(
                    self, "Veri Güncelleme",
                    f"Bu dönem ({ay_str} {yil_str}) için {mevcut_sayisi} kayıt zaten var.\n\n"
                    f"'Evet' derseniz:\n"
                    f"1. Mevcut kayıtlar silinecek.\n"
                    f"2. Tablodaki GÜNCEL veriler kaydedilecek.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if cevap != QMessageBox.Yes:
                    self.lbl_durum.setText("İptal edildi.")
                    return

            self.btn_kaydet.setEnabled(False)
            self.progress.setVisible(True)

            # 1. Eski kayıtları sil
            if mevcut_sayisi > 0:
                self.lbl_durum.setText("Eski kayitlar temizleniyor...")
                for r in tum:
                    if str(r.get("AitYil", "")).strip() == yil_str \
                       and str(r.get("Donem", "")).strip() == ay_str:
                        pk = [
                            str(r.get("Personelid", "")),
                            str(r.get("AitYil", "")),
                            str(r.get("Donem", ""))
                        ]
                        try:
                            repo.delete(pk)
                        except Exception:
                            pass

            # 2. Yeni kaydet (tablodan oku)
            self.lbl_durum.setText("Guncel veriler kaydediliyor...")
            kayit_sayisi = 0
            for r in range(self.tablo.rowCount()):
                data = {
                    "Personelid": self.tablo.item(r, C_KIMLIK).text() if self.tablo.item(r, C_KIMLIK) else "",
                    "AdSoyad": self.tablo.item(r, C_AD).text() if self.tablo.item(r, C_AD) else "",
                    "Birim": self.tablo.item(r, C_BIRIM).text() if self.tablo.item(r, C_BIRIM) else "",
                    "CalismaKosulu": self.tablo.item(r, C_KOSUL).text() if self.tablo.item(r, C_KOSUL) else "",
                    "AitYil": self.tablo.item(r, C_YIL).text() if self.tablo.item(r, C_YIL) else yil_str,
                    "Donem": self.tablo.item(r, C_DONEM).text() if self.tablo.item(r, C_DONEM) else ay_str,
                    "AylikGun": self.tablo.item(r, C_GUN).text() if self.tablo.item(r, C_GUN) else "0",
                    "KullanilanIzin": self.tablo.item(r, C_IZIN).text() if self.tablo.item(r, C_IZIN) else "0",
                    "FiiliCalismaSaat": self.tablo.item(r, C_SAAT).text() if self.tablo.item(r, C_SAAT) else "0",
                }
                repo.insert(data)
                kayit_sayisi += 1

            # 3. Şua bakiyesi güncelle
            self.lbl_durum.setText("Sua hesaplaniyor...")
            self._sua_bakiye_guncelle(repo, yil_str)

            self.progress.setVisible(False)
            self.btn_kaydet.setEnabled(True)
            self.lbl_durum.setText(f"{kayit_sayisi} kayit kaydedildi  -  {ay_str} {yil_str}")

            logger.info(f"FHSZ kaydedildi: {ay_str} {yil_str}, {kayit_sayisi} kayıt")
            QMessageBox.information(self, "Başarılı", "Kayıt işlemi tamamlandı.")

        except Exception as e:
            self.progress.setVisible(False)
            self.btn_kaydet.setEnabled(True)
            self.lbl_durum.setText(f"Hata: {e}")
            logger.error(f"FHSZ kayıt hatası: {e}")
            QMessageBox.critical(self, "Hata", str(e))

    # ═══════════════════════════════════════════
    #  ŞUA BAKİYESİ GÜNCELLE  (Izin_Bilgi → SuaCariYilKazanim)
    # ═══════════════════════════════════════════

    def _sua_bakiye_guncelle(self, repo_puantaj, yil_str):
        """
        Orijinaldeki _sua_bakiye_guncelle:
        1. FHSZ_Puantaj'dan yıla ait tüm kayıtları topla
        2. Personel başına yıllık toplam saat hesapla
        3. sua_hak_edis_hesapla → İzin_Bilgi.SuaCariYilKazanim güncelle
        """
        try:
            from core.di import get_registry
            registry = get_registry(self._db)

            tum = repo_puantaj.get_all()
            personel_toplam = {}
            for r in tum:
                if str(r.get("AitYil", "")).strip() != yil_str:
                    continue
                tc = str(r.get("Personelid", "")).strip()
                try:
                    saat = float(str(r.get("FiiliCalismaSaat", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    saat = 0
                personel_toplam[tc] = personel_toplam.get(tc, 0) + saat

            izin_bilgi = registry.get("Izin_Bilgi")
            for tc, toplam_saat in personel_toplam.items():
                yeni_hak = sua_hak_edis_hesapla(toplam_saat)
                try:
                    mevcut = izin_bilgi.get_by_id(tc)
                    if mevcut:
                        try:
                            eski = float(str(mevcut.get("SuaCariYilKazanim", 0)).replace(",", "."))
                        except (ValueError, TypeError):
                            eski = -1
                        if eski != yeni_hak:
                            izin_bilgi.update(tc, {"SuaCariYilKazanim": yeni_hak})
                except Exception:
                    pass

            logger.info(f"Şua bakiyesi güncellendi: {len(personel_toplam)} personel")

        except Exception as e:
            logger.error(f"Şua bakiye güncelleme hatası: {e}")


