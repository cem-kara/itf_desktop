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
    QHeaderView, QProgressBar, QStyledItemDelegate,
    QAbstractItemView, QStyle, QApplication
)
from PySide6.QtCore import Qt, QRectF, QTimer, QSize
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QBrush, QPen, QPainterPath

from core.logger import logger
from ui.dialogs.mesaj_kutusu import MesajKutusu
from core.di import get_fhsz_service
from core.date_utils import parse_date
from core.hesaplamalar import sua_hak_edis_hesapla, is_gunu_hesapla, tr_upper
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

def _parse_date_as_datetime(val):
    """parse_date() sonucunu datetime'a dönüştür."""
    parsed = parse_date(val)
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
    "Ait Yıl", "Dönem", "Aylık Çalışma Gün Sayısı", "Kullanılan İzin",
    "Fiili Çalışma (Saat)",
]

# Kolon indeksleri
C_KIMLIK, C_AD, C_BIRIM, C_KOSUL = 0, 1, 2, 3
C_YIL, C_DONEM, C_GUN, C_IZIN, C_SAAT = 4, 5, 6, 7, 8


# ═══════════════════════════════════════════════════════════════════
#  DELEGATE: Çalışma Koşulu  (Kolon 3)
#  — Paint: temiz renkli badge + küçük ok ikonu
#  — Edit : tek tıkta büyük, net QComboBox popup
# ═══════════════════════════════════════════════════════════════════

_KOSUL_ITEMS = ["Çalışma Koşulu A", "Çalışma Koşulu B"]

# Renk tanımları
_K_A = {
    "badge_bg":  QColor(30, 90, 40, 200),
    "badge_brd": QColor("#4caf50"),
    "text":      QColor("#c8f7c5"),
    "dot":       QColor("#66bb6a"),
}
_K_B = {
    "badge_bg":  QColor(20, 70, 150, 200),
    "badge_brd": QColor("#42a5f5"),
    "text":      QColor("#bbdefb"),
    "dot":       QColor("#42a5f5"),
}


class KosulDelegate(QStyledItemDelegate):
    """
    Çalışma Koşulu A / B seçici delegate.
    Her satırda badge olarak görünür; tek tıkla büyük açılan combo sunar.
    """
    def paint(self, painter, option, index):
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "Çalışma Koşulu B")
        is_a = "KOŞULU A" in text.upper()
        clr  = _K_A if is_a else _K_B

        # Satır seçili arka plan
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(29, 117, 254, 50))
        else:
            painter.fillRect(option.rect, QColor("transparent"))

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Badge alanı (tüm hücreyi doldurur, kenar boşluklu)
        r = QRectF(option.rect).adjusted(8, 6, -28, -6)   # sağda ok için yer bırak
        path = QPainterPath()
        path.addRoundedRect(r, 6, 6)
        painter.setBrush(QBrush(clr["badge_bg"]))
        painter.setPen(QPen(clr["badge_brd"], 1.5))
        painter.drawPath(path)

        # Badge metni
        painter.setPen(clr["text"])
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        painter.setBrush(QBrush(clr["badge_brd"]))
        painter.restore()

    def createEditor(self, parent, option, index):
        from PySide6.QtWidgets import QListView
        editor = QComboBox(parent)
        editor.addItems(_KOSUL_ITEMS)
        # Büyük popup için özel view
        view = QListView()
        view.setStyleSheet("""
            QListView {{
                background-color: {panel};
                color: {primary};
                border: 1.5px solid {focus};
                font-size: 12px;
                font-weight: 700;
                outline: none;
            }}
            QListView::item {{
                min-height: 54px;
                padding: 0 24px;
                font-size: 12px;
                font-weight: 700;
            }}
            QListView::item:selected {{
                background-color: rgba(29,117,254,0.18);
                color: #fff;
            }}
        """.format(
            panel=DarkTheme.BG_SECONDARY,
            primary=DarkTheme.TEXT_PRIMARY,
            focus=DarkTheme.INPUT_BORDER_FOCUS,
        ))
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setUniformItemSizes(True)
        editor.setView(view)
        editor.setMinimumHeight(48)
        editor.setFixedHeight(54)
        editor.setStyleSheet("""
            QComboBox {{
                background-color: {input_bg};
                color: {primary};
                border: 2px solid {focus};
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 16px;
                font-weight: 700;
            }}
            QComboBox::drop-down {{ border: none; width: 32px; }}
            QComboBox::down-arrow {{
                border-left: 7px solid transparent;
                border-right: 7px solid transparent;
                border-top: 9px solid {focus};
                margin-right: 10px;
            }}
        """.format(
            input_bg=DarkTheme.INPUT_BG,
            primary=DarkTheme.TEXT_PRIMARY,
            focus=DarkTheme.INPUT_BORDER_FOCUS,
        ))
        # Tek tıkta popup açılsın
        QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole) or _KOSUL_ITEMS[1]
        editor.blockSignals(True)
        editor.setCurrentText(text if text in _KOSUL_ITEMS else _KOSUL_ITEMS[1])
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# ═══════════════════════════════════════════════════════════════════
#  DELEGATE: Fiili Çalışma saati sonuç badge  (Kolon 8 — read-only)
# ═══════════════════════════════════════════════════════════════════

class SonucDelegate(QStyledItemDelegate):
    """Hesaplanan fiili çalışma saatini renkli badge olarak gösterir."""
    def paint(self, painter, option, index):
        bg = QColor(29, 117, 254, 55) if option.state & QStyle.StateFlag.State_Selected \
            else QColor("transparent")
        painter.fillRect(option.rect, bg)

        try:
            deger = float(index.data(Qt.ItemDataRole.DisplayRole))
        except (ValueError, TypeError):
            deger = 0

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect).adjusted(10, 6, -10, -6)

        if deger > 0:
            c_bg   = QColor(27, 94, 32, 150)
            c_bord = QColor("#66bb6a")
            c_txt  = QColor("#ffffff")
            label  = f"✓  {deger:.0f} saat"
        else:
            c_bg   = QColor(62, 62, 62, 70)
            c_bord = QColor("#444")
            c_txt  = QColor("muted")
            label  = "— saat"

        path = QPainterPath()
        path.addRoundedRect(rect, 5, 5)
        painter.setBrush(QBrush(c_bg))
        painter.setPen(QPen(c_bord, 1))
        painter.drawPath(path)
        painter.setPen(c_txt)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 38)


# ═══════════════════════════════════════════════
#  FHSZ YÖNETİM SAYFASI
# ═══════════════════════════════════════════════

class FHSZYonetimPage(QWidget):

    def _show_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu, QTableWidgetItem
        idx = self.tablo.indexAt(pos)
        if not idx.isValid() or idx.column() != C_KOSUL:
            return
        menu = QMenu(self)
        action_a = menu.addAction("Çalışma Koşulu A")
        action_b = menu.addAction("Çalışma Koşulu B")
        action = menu.exec(self.tablo.viewport().mapToGlobal(pos))
        if action == action_a:
            self.tablo.setItem(idx.row(), idx.column(), QTableWidgetItem("Çalışma Koşulu A"))
            self._satir_hesapla(idx.row())
        elif action == action_b:
            self.tablo.setItem(idx.row(), idx.column(), QTableWidgetItem("Çalışma Koşulu B"))
            self._satir_hesapla(idx.row())

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db = db
        self._svc = get_fhsz_service(db) if db else None
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
        filter_frame.setProperty("bg-role", "panel")
        fp = QHBoxLayout(filter_frame)
        fp.setContentsMargins(12, 8, 12, 8)
        fp.setSpacing(8)

        # Dönem Seçimi: Ay · Yıl
        fp.addWidget(self._make_label("Dönem:"))
        self.cmb_ay = QComboBox()
        # self.cmb_ay.setStyleSheet kaldırıldı (global QSS yönetir)
        self.cmb_ay.setFixedWidth(140)
        self.cmb_ay.addItems(AY_ISIMLERI)
        self.cmb_ay.setCurrentIndex(max(0, datetime.now().month - 1))
        fp.addWidget(self.cmb_ay)
        
        self.cmb_yil = QComboBox()
        # self.cmb_yil.setStyleSheet kaldırıldı (global QSS yönetir)
        self.cmb_yil.setFixedWidth(100)
        by = datetime.now().year
        for y in range(by - 5, by + 5):
            self.cmb_yil.addItem(str(y))
        self.cmb_yil.setCurrentText(str(by))
        fp.addWidget(self.cmb_yil)

        self._add_sep(fp)

        self.lbl_donem = QLabel("Dönem aralığı: ...")
        self.lbl_donem.setProperty("color-role", "muted")
        self.lbl_donem.setStyleSheet("font-size: 11px;")
        fp.addWidget(self.lbl_donem)

        fp.addStretch()

        self.btn_hesapla = QPushButton("HESAPLA")
        self.btn_hesapla.setProperty("style-role", "action")
        self.btn_hesapla.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_hesapla, "bar_chart", color="primary", size=14)
        fp.addWidget(self.btn_hesapla)

        main.addWidget(filter_frame)

        # -- Bilgi alani: aylik ozet
        info_frame = QFrame()
        info_frame.setProperty("bg-role", "panel")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(24)

        self.lbl_aylik_gun = QLabel("—")
        info_layout.addWidget(self._make_stat_block("Aylık çalışma gün sayısı", self.lbl_aylik_gun))

        self.lbl_aylik_saat = QLabel("—")
        info_layout.addWidget(self._make_stat_block("Aylık çalışma saati", self.lbl_aylik_saat))

        self.lbl_aylik_tatil = QLabel("—")
        info_layout.addWidget(self._make_stat_block("Toplam tatil gün sayısı", self.lbl_aylik_tatil))

        self.lbl_aylik_tatil_is_gunu = QLabel("—")
        info_layout.addWidget(
            self._make_stat_block("İş gününe denk gelen tatil sayısı", self.lbl_aylik_tatil_is_gunu)
        )

        info_layout.addStretch()
        main.addWidget(info_frame)

        # ── TABLO (QTableWidget — orijinaldeki gibi) ──
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(TABLO_KOLONLARI))
        self.tablo.setHorizontalHeaderLabels(TABLO_KOLONLARI)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.verticalHeader().setDefaultSectionSize(40)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # self.tablo.setStyleSheet kaldırıldı (global QSS yönetir)
        self.tablo.setEditTriggers(
            QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.DoubleClicked
        )

        h = self.tablo.horizontalHeader()
        h.setDefaultSectionSize(90)
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(C_KIMLIK, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(C_KOSUL, QHeaderView.ResizeMode.Fixed)
        self.tablo.setColumnWidth(C_KOSUL, 180)
        h.setSectionResizeMode(C_GUN,  QHeaderView.ResizeMode.Fixed)
        self.tablo.setColumnWidth(C_GUN, 160)
        h.setSectionResizeMode(C_IZIN, QHeaderView.ResizeMode.Fixed)
        self.tablo.setColumnWidth(C_IZIN, 110)
        h.setSectionResizeMode(C_SAAT, QHeaderView.ResizeMode.Fixed)
        self.tablo.setColumnWidth(C_SAAT, 150)

        # AitYıl + Dönem gizli
        self.tablo.setColumnHidden(C_YIL, True)
        self.tablo.setColumnHidden(C_DONEM, True)

        # Delegate'ler
        self._kosul_del = KosulDelegate(self.tablo)
        self._saat_del  = SonucDelegate(self.tablo)
        self.tablo.setItemDelegateForColumn(C_KOSUL, self._kosul_del)
        # Sağ tık context menu: Çalışma Koşulu A/B
        self.tablo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tablo.customContextMenuRequested.connect(self._show_context_menu)

        self.tablo.setItemDelegateForColumn(C_SAAT,  self._saat_del)

        # Tabloyu layout'a ekle (görünmesi için şart)
        main.addWidget(self.tablo, 1)

        # ── ALT BAR ──
        bot_frame = QFrame()
        bot_frame.setProperty("bg-role", "panel")
        bf = QHBoxLayout(bot_frame)
        bf.setContentsMargins(12, 8, 12, 8)
        bf.setSpacing(12)

        self.lbl_durum = QLabel("Hazır")
        self.lbl_durum.setProperty("color-role", "muted")
        bf.addWidget(self.lbl_durum)

        bf.addStretch()

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(160)
        self.progress.setFixedHeight(14)
        self.progress.setStyleSheet("""
            QProgressBar {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 3px; font-size: 10px; color: {};
            }}
            QProgressBar::chunk {{
                background-color: rgba(29,117,254,0.5); border-radius: 2px;
            }}
        """.format("muted"))
        bf.addWidget(self.progress)

        self.btn_kaydet = QPushButton("KAYDET / GUNCELLE")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save", color="primary", size=14)
        bf.addWidget(self.btn_kaydet)

        main.addWidget(bot_frame)
        self._donem_guncelle()

    # ─── UI yardımcıları ───

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setProperty("color-role", "muted")
        return lbl

    def _add_sep(self, layout):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setProperty("bg-role", "separator")
        layout.addWidget(sep)

    def _make_stat_block(self, title: str, value_label: QLabel) -> QWidget:
        block = QFrame()
        bl = QVBoxLayout(block)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setProperty("style-role", "stat-label")
        bl.addWidget(lbl_title)

        value_label.setProperty("style-role", "stat-value")
        bl.addWidget(value_label)
        return block

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
        self._update_aylik_bilgi()

    def _update_aylik_bilgi(self):
        donem_bas, donem_bit = self._get_donem_aralik()
        if not donem_bas or not donem_bit:
            self.lbl_aylik_gun.setText("—")
            self.lbl_aylik_saat.setText("—")
            self.lbl_aylik_tatil.setText("—")
            self.lbl_aylik_tatil_is_gunu.setText("—")
            return

        try:
            is_gunu = is_gunu_hesapla(donem_bas, donem_bit, self._tatil_listesi_np)
        except Exception:
            is_gunu = 0

        tatil_sayisi = 0
        tatil_is_gunu = 0
        if self._tatil_listesi_np:
            for d in self._tatil_listesi_np:
                try:
                    dt = datetime.strptime(d, "%Y-%m-%d")
                except Exception:
                    continue
                if donem_bas <= dt <= donem_bit:
                    tatil_sayisi += 1
                    if dt.weekday() < 5:
                        tatil_is_gunu += 1

        self.lbl_aylik_gun.setText(str(is_gunu))
        self.lbl_aylik_saat.setText(str(is_gunu * KOSUL_A_SAAT))
        self.lbl_aylik_tatil.setText(str(tatil_sayisi))
        self.lbl_aylik_tatil_is_gunu.setText(str(tatil_is_gunu))

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
            if not self._svc:
                return

            # 1. Personeller
            self._all_personel = self._svc.get_personel_listesi().veri or []

            # 2. İzinler
            self._all_izin = self._svc.get_izin_listesi().veri or []

            # 3. Tatiller → numpy busday_count formatı
            try:
                tatiller = self._svc.get_tatil_gunleri().veri or []
                self._tatil_listesi_np = []
                for r in tatiller:
                    d = parse_date(r.get("Tarih", ""))
                    if d:
                        self._tatil_listesi_np.append(d.strftime("%Y-%m-%d"))
            except Exception:
                self._tatil_listesi_np = []

            # 4. Sabitler → Kod="Gorev_Yeri"
            #    MenuEleman = birim adı | Aciklama = "Çalışma Koşulu A / B"
            sabitler = self._svc.get_sabitler_listesi().veri or []

            self._birim_kosul_map = {}

            for r in sabitler:
                # Sadece Gorev_Yeri olanlar
                if str(r.get("Kod", "")).strip() != "Gorev_Yeri":
                    continue

                birim = tr_upper(str(r.get("MenuEleman", "")).strip())
                aciklama = tr_upper(str(r.get("Aciklama", "")).strip())

                if not birim:
                    continue

                # KRİTİK DÜZELTME NOKTASI
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
            self._update_aylik_bilgi()


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
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.tablo.setItem(row, col, item)



    def _item_text(self, row, col, default: str = "") -> str:
        item = self.tablo.item(row, col)
        return item.text() if item else default

    def _satir_hesapla(self, row):
        """
        Orijinaldeki _satir_hesapla — Koşul değişince puanı yeniden hesapla.
        Koşul A → (iş_günü - izin) × 7
        Koşul B → 0
        """
        try:
            kosul_item = self.tablo.item(row, C_KOSUL)
            is_gunu_item = self.tablo.item(row, C_GUN)
            izin_item = self.tablo.item(row, C_IZIN)
            if not kosul_item or not is_gunu_item or not izin_item:
                return
            kosul = kosul_item.text()
            is_gunu = int(is_gunu_item.text())
            izin = int(izin_item.text())
            puan = 0
            if "KOŞULU A" in tr_upper(kosul):
                net = max(0, is_gunu - izin)
                puan = net * KOSUL_A_SAAT
            self.tablo.setItem(row, C_SAAT, QTableWidgetItem(str(puan)))
        except Exception:
            pass

    def _hucre_degisti(self, item):
        """Koşul / Gün / İzin değiştiğinde fiili saati yeniden hesapla."""
        if item.column() in (C_KOSUL, C_GUN, C_IZIN):
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

            izin_bas = _parse_date_as_datetime(iz.get("BaslamaTarihi", ""))
            izin_bit = _parse_date_as_datetime(iz.get("BitisTarihi", ""))
            if not izin_bas or not izin_bit:
                continue

            # Kesişim aralığı
            k_bas = max(donem_bas, izin_bas)
            k_bit = min(donem_bit, izin_bit)

            if k_bas <= k_bit:
                toplam += is_gunu_hesapla(k_bas, k_bit, self._tatil_listesi_np)

        return toplam

    def _calc_personel_is_gunu(self, kimlik, donem_bas, donem_bit):
        """Personel için dönem iş günü (gross) hesabı."""
        try:
            kimlik_str = str(kimlik).strip()
            kisi_bit = donem_bit
            durum = ""
            ayrilis = None

            for p in self._all_personel:
                if str(p.get("KimlikNo", "")).strip() == kimlik_str:
                    durum = str(p.get("Durum", "Aktif")).strip()
                    ayrilis = _parse_date_as_datetime(p.get("AyrilisTarihi", ""))
                    break

            if durum == "Pasif" and ayrilis:
                if ayrilis < donem_bas:
                    return 0
                if ayrilis < donem_bit:
                    kisi_bit = ayrilis

            return is_gunu_hesapla(donem_bas, kisi_bit, self._tatil_listesi_np)
        except Exception:
            return 0

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
            MesajKutusu.uyari(self, "26.04.2022 tarihli Resmî Gazete’de yayımlanan Radyoloji Hizmetleri Yönetmeliği gereğince, bu tarihten önceki süreler için fiili hizmet süresi zammı ve şua izni hesaplaması yapılamamaktadır. Lütfen hesaplama başlangıç tarihini kontrol ediniz.")
            return

        self.tablo.setRowCount(0)
        self.btn_hesapla.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_durum.setText("Kayıtlar kontrol ediliyor...")

        yil_str = self.cmb_yil.currentText()
        ay_str = self.cmb_ay.currentText()

        try:
            if not self._svc:
                MesajKutusu.uyari(self, "Veritabanı bağlantısı yok.")
                return

            # Veriler yüklenmediyse otomatik yükle
            if not self._all_personel:
                self.lbl_durum.setText("Veriler yükleniyor...")
                QApplication.processEvents()
                try:
                    self.load_data()
                except Exception as ld_err:
                    logger.error(f"load_data hatası: {ld_err}")
                    self.lbl_durum.setText(f"Veri yükleme hatası: {ld_err}")
                    return

            # Personel yüklendi mi?
            self.lbl_durum.setText(
                f"{len(self._all_personel)} personel, "
                f"{len(self._tatil_listesi_np)} tatil yüklendi. Hesaplanıyor..."
            )
            QApplication.processEvents()

            # Mevcut kayıtları kontrol et
            mevcut = self._svc.get_donem_puantaj_listesi(yil_str, ay_str).veri or []

            if mevcut:
                self._kayitli_veriyi_yukle(mevcut)
            else:
                self._sifirdan_hesapla()

        except Exception as e:
            logger.error(f"FHSZ kontrol hatası: {e}")
            MesajKutusu.hata(self, str(e))
        finally:
            # Her durumda UI'yi sıfırla
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
        donem_bas, donem_bit = self._get_donem_aralik()

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
            item_k.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
            self.tablo.setItem(row_idx, C_KOSUL, item_k)

            self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
            self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())
            izin_gunu = int(str(row_data.get("KullanilanIzin", "0")))
            gross_gun = 0
            if donem_bas and donem_bit:
                gross_gun = self._calc_personel_is_gunu(kimlik, donem_bas, donem_bit)
            self._set_item(row_idx, C_GUN, str(gross_gun))
            self._set_item(row_idx, C_IZIN, str(izin_gunu))
            self._set_item(row_idx, C_SAAT, str(row_data.get("FiiliCalismaSaat", "0")))

        # ── EKSİK PERSONEL SENKRONİZASYONU ──
        try:
            donem_bas, donem_bit = self._get_donem_aralik()
            if not donem_bas or not donem_bit:
                self.tablo.blockSignals(False)
                return
            hesap_bas = donem_bas if donem_bas >= FHSZ_ESIK else FHSZ_ESIK

            yeni_sayi = self._eksik_personel_ekle(
                mevcut_tcler, hesap_bas, donem_bit
            )

            if yeni_sayi > 0:
                MesajKutusu.bilgi(self, f"Listede olmayan {yeni_sayi} yeni personel eklendi.")
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
            if not donem_bas or not donem_bit:
                self.tablo.blockSignals(False)
                return
            if donem_bit < FHSZ_ESIK:
                self.tablo.blockSignals(False)
                return

            hesap_bas = donem_bas if donem_bas >= FHSZ_ESIK else FHSZ_ESIK

            if not self._all_personel:
                self.lbl_durum.setText("Personel listesi boş — önce load_data() çağrılmalı.")
                self.tablo.blockSignals(False)
                return

            sorted_personel = sorted(
                self._all_personel,
                key=lambda p: str(p.get("AdSoyad", ""))
            )

            eklenen = 0
            atlanan_sinif = 0
            for p in sorted_personel:
                kimlik = str(p.get("KimlikNo", "")).strip()
                sinif = str(p.get("HizmetSinifi", "")).strip()
                if sinif not in IZIN_VERILEN_SINIFLAR:
                    atlanan_sinif += 1
                    continue

                ad = p.get("AdSoyad", "")
                birim = str(p.get("GorevYeri", "")).strip()
                durum = str(p.get("Durum", "Aktif")).strip()

                # Pasif personel kontrolü
                kisi_bit = donem_bit
                if durum == "Pasif":
                    ayrilis = _parse_date_as_datetime(p.get("AyrilisTarihi", ""))
                    if ayrilis:
                        if ayrilis < hesap_bas:
                            continue
                        if ayrilis < donem_bit:
                            kisi_bit = ayrilis

                row_idx = self.tablo.rowCount()
                self.tablo.insertRow(row_idx)
                eklenen += 1

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
                item_k.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
                self.tablo.setItem(row_idx, C_KOSUL, item_k)

                self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
                self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())

                # İş günü (numpy busday_count)
                ozel_is_gunu = is_gunu_hesapla(hesap_bas, kisi_bit, self._tatil_listesi_np)
                # İzin kesişim
                izin_gunu = self._kesisim_izin_gunu(kimlik, hesap_bas, kisi_bit)
                self._set_item(row_idx, C_GUN, str(ozel_is_gunu))
                self._set_item(row_idx, C_IZIN, str(izin_gunu))

                # Puan hesapla
                self._satir_hesapla(row_idx)

        except Exception as e:
            logger.error(f"FHSZ sıfırdan hesaplama hatası: {e}")
            MesajKutusu.hata(self, str(e))

        self.tablo.blockSignals(False)
        logger.info(
            f"FHSZ hesaplama: {eklenen} satır eklendi, "
            f"{atlanan_sinif} personel HizmetSınıfı filtresiyle atlandı. "
            f"Filtre: {IZIN_VERILEN_SINIFLAR}"
        )
        if eklenen == 0 and atlanan_sinif > 0:
            self.lbl_durum.setText(
                f"Tablo boş: {len(sorted_personel)} personelden {atlanan_sinif} tanesi "
                f"izin verilen hizmet sınıfında değil. "
                f"({', '.join(IZIN_VERILEN_SINIFLAR)})"
            )
        elif eklenen > 0:
            self.lbl_durum.setText(f"{eklenen} personel hesaplandı.")

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
                ayrilis = _parse_date_as_datetime(p.get("AyrilisTarihi", ""))
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
            item_k.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
            self.tablo.setItem(row_idx, C_KOSUL, item_k)

            self._set_item(row_idx, C_YIL, self.cmb_yil.currentText())
            self._set_item(row_idx, C_DONEM, self.cmb_ay.currentText())

            ozel_is_gunu = is_gunu_hesapla(hesap_bas, kisi_bit, self._tatil_listesi_np)
            izin_gunu = self._kesisim_izin_gunu(kimlik, hesap_bas, kisi_bit)
            self._set_item(row_idx, C_GUN, str(ozel_is_gunu))
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
            if not self._svc:
                return
            mevcut = self._svc.get_donem_puantaj_listesi(yil_str, ay_str).veri or []
            mevcut_sayisi = len(mevcut)

            # Onay
            if mevcut_sayisi > 0:
                cevap = MesajKutusu.soru(
                    self,
                    f"Bu dönem ({ay_str} {yil_str}) için {mevcut_sayisi} kayıt zaten var.\n\n"
                    f"'Evet' derseniz:\n"
                    f"1. Mevcut kayıtlar silinecek.\n"
                    f"2. Tablodaki GÜNCEL veriler kaydedilecek."
                )
                if not cevap:
                    self.lbl_durum.setText("İptal edildi.")
                    return

            self.btn_kaydet.setEnabled(False)
            self.progress.setVisible(True)

            self.lbl_durum.setText("Guncel veriler kaydediliyor...")
            kayitlar = []
            for r in range(self.tablo.rowCount()):
                kayitlar.append({
                    "Personelid": self._item_text(r, C_KIMLIK, ""),
                    "AdSoyad": self._item_text(r, C_AD, ""),
                    "Birim": self._item_text(r, C_BIRIM, ""),
                    "CalismaKosulu": self._item_text(r, C_KOSUL, ""),
                    "AitYil": self._item_text(r, C_YIL, yil_str),
                    "Donem": self._item_text(r, C_DONEM, ay_str),
                    "AylikGun": self._item_text(r, C_GUN, "0"),
                    "KullanilanIzin": self._item_text(r, C_IZIN, "0"),
                    "FiiliCalismaSaat": self._item_text(r, C_SAAT, "0"),
                })

            kaydet_sonuc = self._svc.donem_puantaj_kaydet(yil_str, ay_str, kayitlar)
            if not kaydet_sonuc.basarili:
                raise RuntimeError(kaydet_sonuc.mesaj)
            kayit_sayisi = len(kayitlar)

            self.progress.setVisible(False)
            self.btn_kaydet.setEnabled(True)
            self.lbl_durum.setText(f"{kayit_sayisi} kayit kaydedildi  -  {ay_str} {yil_str}")

            logger.info(f"FHSZ kaydedildi: {ay_str} {yil_str}, {kayit_sayisi} kayıt")
            MesajKutusu.bilgi(self, "Kayıt işlemi tamamlandı.")

        except Exception as e:
            self.lbl_durum.setText(f"Hata: {e}")
            logger.error(f"FHSZ kayıt hatası: {e}")
            MesajKutusu.hata(self, str(e))
        finally:
            self.progress.setVisible(False)
            self.btn_kaydet.setEnabled(True)

    # ═══════════════════════════════════════════
    #  ŞUA BAKİYESİ GÜNCELLE  (Izin_Bilgi → SuaCariYilKazanim)
    # ═══════════════════════════════════════════

    def _sua_bakiye_guncelle(self, repo_puantaj, yil_str):
        try:
            if not self._svc:
                return
            sonuc = self._svc.sua_bakiye_guncelle(yil_str)
            if sonuc.basarili:
                logger.info(f"Şua bakiyesi güncellendi: {sonuc.veri} personel")
            else:
                logger.error(f"Şua bakiye güncelleme hatası: {sonuc.mesaj}")
        except Exception as e:
            logger.error(f"Şua bakiye güncelleme hatası: {e}")
