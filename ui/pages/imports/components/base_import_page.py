"""
BaseImportPage — 4 Adımlı Excel Import Sihirbazı
=================================================

Kalıtım için:
    class PersonelImportPage(BaseImportPage):
        def _konfig(self) -> ImportKonfig:
            return KONFIG

Adımlar:
    1 → Dosya Seç
    2 → Sütun Eşleştir
    3 → Önizle (duplicate kontrolü dahil)
    4 → Sonuç + Hata Düzeltme
"""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import pandas as pd

from core.services.excel_import_service import (
    ExcelImportService,
    ImportKonfig,
    ImportSonucu,
    SatirSonucu,
    alanlar_tam_listesi,
)

# ---------------------------------------------------------------------------
# Renk sabitleri
# ---------------------------------------------------------------------------
RENK_KIRMIZI = QColor("#6E6CC9")   # pk_duplicate
RENK_SARI    = QColor("#F8E21D")   # yumusak_duplicate
RENK_GRI     = QColor("#F35050A9")   # zorunlu_eksik
RENK_YESIL   = QColor("#04D304")   # basarili
RENK_TURUNCU = QColor("#FC4902")   # hatali


# ---------------------------------------------------------------------------
# Arka plan iş parçacığı
# ---------------------------------------------------------------------------

from PySide6.QtCore import QThread

class _ImportThread(QThread):
    bitti = Signal(object)   # ImportSonucu veya Exception

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.bitti.emit(self._fn())
        except Exception as exc:
            self.bitti.emit(exc)


# ---------------------------------------------------------------------------
# Hata Düzeltme Dialog
# ---------------------------------------------------------------------------

class HataDuzeltmeWidget(QDialog):
    """
    Sadece hatalı / zorunlu_eksik satırları gösterir.
    Kullanıcı hücreleri düzenleyip [Seçilenleri Tekrar Dene] diyebilir.
    """

    yeniden_dene = Signal(list)   # list[SatirSonucu]

    def __init__(self, satirlar: list[SatirSonucu], alan_adlari: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hata Düzeltme")
        self.setMinimumSize(900, 500)
        self._satirlar = list(satirlar)
        self._alan_adlari = alan_adlari
        self._kur()

    # ------------------------------------------------------------------
    def _kur(self):
        ana = QVBoxLayout(self)
        ana.setSpacing(10)

        baslik = QLabel(f"<b>Düzeltilecek Satırlar</b> — {len(self._satirlar)} kayıt")
        baslik.setStyleSheet("font-size:13px; padding:4px;")
        ana.addWidget(baslik)

        # Tablo
        sutun_sayisi = len(self._alan_adlari) + 1  # +1 hata mesajı sütunu
        self._tablo = QTableWidget(len(self._satirlar), sutun_sayisi)
        self._tablo.setHorizontalHeaderLabels(self._alan_adlari + ["Hata Mesajı"])
        self._tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tablo.setAlternatingRowColors(True)
        ana.addWidget(self._tablo)

        self._tabloyu_doldur()

        # Butonlar
        btn_kutu = QHBoxLayout()
        btn_dene          = QPushButton("✔  Seçilenleri Tekrar Dene")
        btn_yoksay_secili = QPushButton("Seçilenleri Yoksay")
        btn_yoksay_hepsi  = QPushButton("Tümünü Yoksay")
        btn_kapat         = QPushButton("Kapat")

        btn_dene.setStyleSheet("background:#4CAF50; color:white; padding:6px 14px;")
        btn_kapat.setStyleSheet("padding:6px 14px;")

        btn_dene.clicked.connect(self._secilenler_dene)
        btn_yoksay_secili.clicked.connect(self._secilenler_yoksay)
        btn_yoksay_hepsi.clicked.connect(self.reject)
        btn_kapat.clicked.connect(self.accept)

        btn_kutu.addWidget(btn_dene)
        btn_kutu.addWidget(btn_yoksay_secili)
        btn_kutu.addStretch()
        btn_kutu.addWidget(btn_yoksay_hepsi)
        btn_kutu.addWidget(btn_kapat)
        ana.addLayout(btn_kutu)

    def _tabloyu_doldur(self):
        for r, satir in enumerate(self._satirlar):
            for c, alan in enumerate(self._alan_adlari):
                self._tablo.setItem(r, c, QTableWidgetItem(str(satir.veri.get(alan, ""))))
            # Hata mesajı — salt okunur
            hata_item = QTableWidgetItem(satir.hata_mesaji)
            hata_item.setFlags(hata_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            hata_item.setBackground(RENK_TURUNCU)
            self._tablo.setItem(r, len(self._alan_adlari), hata_item)

    def _secilenler_dene(self):
        secili_satirlar = {idx.row() for idx in self._tablo.selectedIndexes()}
        if not secili_satirlar:
            QMessageBox.information(self, "Bilgi", "Lütfen önce satır seçin.")
            return

        secili_liste: list[SatirSonucu] = []
        for r in secili_satirlar:
            if r >= len(self._satirlar):
                continue
            satir = self._satirlar[r]
            # Düzeltilmiş veriyi oku
            yeni_veri = dict(satir.veri)
            for c, alan in enumerate(self._alan_adlari):
                item = self._tablo.item(r, c)
                if item:
                    yeni_veri[alan] = item.text().strip()
            satir.duzeltilmis_veri = yeni_veri
            secili_liste.append(satir)

        self.yeniden_dene.emit(secili_liste)
        self.accept()

    def _secilenler_yoksay(self):
        idxler = sorted(
            {idx.row() for idx in self._tablo.selectedIndexes()},
            reverse=True,
        )
        for i in idxler:
            if i < len(self._satirlar):
                self._satirlar.pop(i)
                self._tablo.removeRow(i)


# ---------------------------------------------------------------------------
# BaseImportPage
# ---------------------------------------------------------------------------

class BaseImportPage(QWidget):
    """
    4 adımlı import sihirbazının ortak UI'ı.
    Alt sınıflar yalnızca _konfig() metodunu override eder.
    """

    def __init__(self, db, kaydeden: str = "", parent=None):
        super().__init__(parent)
        self._db         = db
        self._kaydeden   = kaydeden
        self._svc        = ExcelImportService()
        self._konfig_obj = self._konfig()

        # Durum değişkenleri
        self._df: Optional[pd.DataFrame]       = None
        self._harita: dict[str, str]            = {}
        self._manuel: dict[str, str]            = {}    # db_alan → elle girilen değer
        self._satirlar: list[SatirSonucu]       = []
        self._sonuc: Optional[ImportSonucu]     = None
        self._combo_map: dict[str, QComboBox]   = {}    # db_alan → QComboBox
        self._lineedit_map: dict[str, Any]      = {}    # db_alan → QLineEdit

        self._kur_ui()

    # ------------------------------------------------------------------
    # Alt sınıf arayüzü
    # ------------------------------------------------------------------

    def _konfig(self) -> ImportKonfig:
        raise NotImplementedError("Alt sınıf _konfig() metodunu implement etmeli.")

    # ------------------------------------------------------------------
    # Ana UI kurulumu
    # ------------------------------------------------------------------

    def _kur_ui(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 16, 16, 16)
        ana.setSpacing(12)

        # Başlık
        self._baslik_label = QLabel(self._konfig_obj.baslik)
        self._baslik_label.setStyleSheet("font-size:16px; font-weight:bold; padding:4px 0;")
        ana.addWidget(self._baslik_label)

        # Adım göstergesi
        self._adim_widget = self._adim_gostergesi_olustur()
        ana.addWidget(self._adim_widget)

        # İçerik alanı
        self._stack = QStackedWidget()
        self._stack.addWidget(self._adim1_olustur())   # 0
        self._stack.addWidget(self._adim2_olustur())   # 1
        self._stack.addWidget(self._adim3_olustur())   # 2
        self._stack.addWidget(self._adim4_olustur())   # 3
        ana.addWidget(self._stack, stretch=1)

        # Navigasyon butonları
        nav = QHBoxLayout()
        self._btn_geri  = QPushButton("◀  Geri")
        self._btn_ileri = QPushButton("İleri  ▶")
        self._btn_geri.setStyleSheet("padding:6px 18px;")
        self._btn_ileri.setStyleSheet("padding:6px 18px; background:#1565C0; color:white;")
        self._btn_geri.clicked.connect(self._geri)
        self._btn_ileri.clicked.connect(self._ileri)
        nav.addWidget(self._btn_geri)
        nav.addStretch()
        nav.addWidget(self._btn_ileri)
        ana.addLayout(nav)

        self._adima_git(0)

    # ------------------------------------------------------------------
    # Adım göstergesi
    # ------------------------------------------------------------------

    def _adim_gostergesi_olustur(self) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)
        kutu = QHBoxLayout(frame)
        kutu.setContentsMargins(0, 0, 0, 0)
        kutu.setSpacing(4)

        self._adim_labels: list[QLabel] = []
        adimlar = ["1 — Dosya Seç", "2 — Sütun Eşleştir", "3 — Önizle", "4 — Sonuç"]
        for i, metin in enumerate(adimlar):
            lbl = QLabel(metin)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(28)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            lbl.setStyleSheet("background:#E0E0E0; border-radius:4px; padding:2px 8px; color:#555;")
            kutu.addWidget(lbl)
            self._adim_labels.append(lbl)
            if i < len(adimlar) - 1:
                kutu.addWidget(QLabel("→"))

        return frame

    def _adim_gostergesi_guncelle(self, aktif: int):
        for i, lbl in enumerate(self._adim_labels):
            if i < aktif:
                lbl.setStyleSheet(
                    "background:#A5D6A7; border-radius:4px; padding:2px 8px; color:#1B5E20;"
                )
            elif i == aktif:
                lbl.setStyleSheet(
                    "background:#1565C0; border-radius:4px; padding:2px 8px; "
                    "color:white; font-weight:bold;"
                )
            else:
                lbl.setStyleSheet(
                    "background:#E0E0E0; border-radius:4px; padding:2px 8px; color:#555;"
                )

    # ------------------------------------------------------------------
    # Adım 1 — Dosya Seç
    # ------------------------------------------------------------------

    def _adim1_olustur(self) -> QWidget:
        w = QWidget()
        kutu = QVBoxLayout(w)
        kutu.setAlignment(Qt.AlignmentFlag.AlignTop)
        kutu.setSpacing(14)

        aciklama = QLabel(
            "Yüklemek istediğiniz Excel (.xlsx / .xls) dosyasını seçin.\n"
            "Dosyanın ilk satırı sütun başlığı olmalıdır."
        )
        aciklama.setWordWrap(True)
        kutu.addWidget(aciklama)

        btn_sec = QPushButton("📂  Dosya Seç…")
        btn_sec.setFixedHeight(40)
        btn_sec.setStyleSheet("font-size:13px; padding:0 20px;")
        btn_sec.clicked.connect(self._dosya_sec)
        kutu.addWidget(btn_sec, alignment=Qt.AlignmentFlag.AlignLeft)

        self._dosya_bilgi = QLabel("")
        self._dosya_bilgi.setStyleSheet("color:#1565C0; font-weight:bold;")
        kutu.addWidget(self._dosya_bilgi)

        return w

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "",
            "Excel Dosyaları (*.xlsx *.xls);;Tüm Dosyalar (*)"
        )
        if not yol:
            return
        try:
            self._df = self._svc.excel_oku(yol)
            satir = len(self._df)
            sutun = len(self._df.columns)
            self._dosya_bilgi.setText(
                f"✔  {yol.split('/')[-1]}  —  {satir} satır, {sutun} sütun"
            )
            self._btn_ileri.setEnabled(True)
        except ValueError as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            self._df = None
            self._dosya_bilgi.setText("")

    # ------------------------------------------------------------------
    # Adım 2 — Sütun Eşleştir (DB alanı → Excel sütunu / Elle Gir)
    # ------------------------------------------------------------------

    _ELLE_GIR = "__elle_gir__"   # ComboBox sentinel değeri

    def _adim2_olustur(self) -> QWidget:
        w = QWidget()
        ana = QVBoxLayout(w)
        ana.setSpacing(6)

        # Başlık satırı
        baslik_kutu = QHBoxLayout()
        for metin, genislik in [("DB Alanı", 200), ("Excel Sütunu / Değer", 0)]:
            lbl = QLabel(f"<b>{metin}</b>")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            if genislik:
                lbl.setFixedWidth(genislik)
            baslik_kutu.addWidget(lbl, 0 if genislik else 1)
        ana.addLayout(baslik_kutu)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        ic_widget = QWidget()
        self._eslestir_kutu = QVBoxLayout(ic_widget)
        self._eslestir_kutu.setSpacing(3)
        scroll.setWidget(ic_widget)
        ana.addWidget(scroll, stretch=1)

        btn_oto = QPushButton("⚡  Otomatik Eşleştir")
        btn_oto.clicked.connect(self._otomatik_eslestir)
        ana.addWidget(btn_oto, alignment=Qt.AlignmentFlag.AlignRight)

        return w

    def _adim2_doldur(self):
        """DataFrame yüklenince Adım 2 içeriğini DB alanları üzerinden inşa eder."""
        if self._df is None:
            return

        # Önceki içeriği temizle
        while self._eslestir_kutu.count():
            item = self._eslestir_kutu.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._combo_map.clear()
        self._lineedit_map.clear()

        # table_config ile birleştirilmiş TAM alan listesi
        tam_alanlar = alanlar_tam_listesi(self._konfig_obj)

        # Excel sütun seçenekleri (tüm combolar için ortak liste)
        excel_secenekleri = [("", "— Eşleştirme Yok —")]
        excel_secenekleri += [(s, s) for s in self._df.columns]
        excel_secenekleri.append((self._ELLE_GIR, "✏  Elle Gir"))

        for at in tam_alanlar:
            satir_widget = QWidget()
            satir_layout = QHBoxLayout(satir_widget)
            satir_layout.setContentsMargins(2, 1, 2, 1)
            satir_layout.setSpacing(6)

            # Sol: DB alan etiketi
            zorunlu_isaret = " <span style='color:red'>★</span>" if at.zorunlu else ""
            lbl = QLabel(f"{at.goruntu}{zorunlu_isaret}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setFixedWidth(200)
            lbl.setToolTip(f"DB kolon: {at.alan}  |  Tip: {at.tip}")
            satir_layout.addWidget(lbl)

            # Orta: Excel sütun seçici ComboBox
            combo = QComboBox()
            for deger, goruntu in excel_secenekleri:
                # elle_girilebilir=False olan alanlarda "Elle Gir" seçeneği gizlenir
                if deger == self._ELLE_GIR and not at.elle_girilebilir:
                    continue
                combo.addItem(goruntu, deger)
            combo.setMinimumWidth(200)
            satir_layout.addWidget(combo, stretch=1)

            # Sağ: Elle giriş alanı (başta gizli)
            from PySide6.QtWidgets import QLineEdit
            lineedit = QLineEdit()
            lineedit.setPlaceholderText(
                at.varsayilan if at.varsayilan else f"{at.goruntu} değeri girin…"
            )
            if at.varsayilan:
                lineedit.setText(at.varsayilan)
            lineedit.setFixedWidth(180)
            lineedit.setVisible(False)
            satir_layout.addWidget(lineedit)

            # "Elle Gir" seçilince lineedit'i göster/gizle
            def _on_combo_changed(idx, _combo=combo, _edit=lineedit):
                is_elle = _combo.currentData() == self._ELLE_GIR
                _edit.setVisible(is_elle)
                self._eslesme_degisti()

            combo.currentIndexChanged.connect(_on_combo_changed)

            self._eslestir_kutu.addWidget(satir_widget)
            self._combo_map[at.alan] = combo       # db_alan → combo
            self._lineedit_map[at.alan] = lineedit # db_alan → lineedit

        self._eslestir_kutu.addStretch()
        self._otomatik_eslestir()

    def _otomatik_eslestir(self):
        """Motor otomatik eşleştirme önerisini yeni ters yapıda uygular."""
        if self._df is None:
            return
        # Motor hâlâ excel→db haritası döndürüyor, tersini al: db→excel
        harita_excel_db = self._svc.otomatik_eslestir(
            self._df.columns.tolist(), self._konfig_obj
        )
        harita_db_excel = {v: k for k, v in harita_excel_db.items()}

        for db_alan, combo in self._combo_map.items():
            excel_sutun = harita_db_excel.get(db_alan, "")
            for i in range(combo.count()):
                if combo.itemData(i) == excel_sutun:
                    combo.setCurrentIndex(i)
                    break
        self._eslesme_degisti()

    def _eslesme_degisti(self):
        """Aynı Excel sütununa iki DB alanı eşlenirse kırmızı uyarı."""
        secilen_excel: dict[str, str] = {}  # excel_sutun → ilk eşleyen db_alan
        for db_alan, combo in self._combo_map.items():
            deger = combo.currentData()
            if not deger or deger == self._ELLE_GIR:
                combo.setStyleSheet("")
                continue
            if deger in secilen_excel:
                combo.setStyleSheet("background:#FFCCCC;")
            else:
                secilen_excel[deger] = db_alan
                at = next(
                    (a for a in self._konfig_obj.alanlar if a.alan == db_alan), None
                )
                combo.setStyleSheet("background:#E8F5E9;" if (at and at.zorunlu) else "")

    def _haritayi_oku(self) -> dict[str, str]:
        """Combo seçimlerinden {excel_sutun: db_alan} haritası döndürür."""
        harita: dict[str, str] = {}
        secilen_excel: set[str] = set()
        for db_alan, combo in self._combo_map.items():
            deger = combo.currentData()
            if deger and deger != self._ELLE_GIR and deger not in secilen_excel:
                harita[deger] = db_alan   # excel_sutun → db_alan
                secilen_excel.add(deger)
        return harita

    def _manuel_degerleri_oku(self) -> dict[str, str]:
        """'Elle Gir' seçili alanların metin değerlerini döndürür."""
        manuel: dict[str, str] = {}
        for db_alan, combo in self._combo_map.items():
            if combo.currentData() == self._ELLE_GIR:
                lineedit = self._lineedit_map.get(db_alan)
                if lineedit:
                    deger = lineedit.text().strip()
                    if deger:
                        manuel[db_alan] = deger
        return manuel

    def _zorunlu_alanlar_eslestirildi_mi(self) -> bool:
        """Zorunlu alanların Excel'e veya elle girişe bağlı olup olmadığını kontrol eder."""
        eksik = []
        for at in self._konfig_obj.alanlar:
            if not at.zorunlu:
                continue
            combo = self._combo_map.get(at.alan)
            if not combo:
                continue
            deger = combo.currentData()
            if not deger:
                eksik.append(at.goruntu)
                continue
            if deger == self._ELLE_GIR:
                lineedit = self._lineedit_map.get(at.alan)
                if not lineedit or not lineedit.text().strip():
                    eksik.append(f"{at.goruntu} (elle giriş boş)")

        if eksik:
            QMessageBox.warning(
                self, "Zorunlu Alan Eksik",
                "Şu zorunlu alanlar eşleştirilmedi veya boş bırakıldı:\n• "
                + "\n• ".join(eksik)
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Adım 3 — Önizle
    # ------------------------------------------------------------------

    def _adim3_olustur(self) -> QWidget:
        w = QWidget()
        ana = QVBoxLayout(w)

        self._onizle_bilgi = QLabel("")
        self._onizle_bilgi.setWordWrap(True)
        ana.addWidget(self._onizle_bilgi)

        # Renk açıklaması
        aciklama_kutu = QHBoxLayout()
        for renk, metin in [
            (RENK_KIRMIZI, "PK Duplicate"),
            (RENK_SARI,    "Yumuşak Çakışma"),
            (RENK_GRI,     "Zorunlu Eksik"),
        ]:
            kare = QLabel("  ")
            kare.setFixedSize(16, 16)
            kare.setStyleSheet(
                f"background:{renk.name()}; border:1px solid #aaa; border-radius:2px;"
            )
            aciklama_kutu.addWidget(kare)
            aciklama_kutu.addWidget(QLabel(metin))
            aciklama_kutu.addSpacing(12)
        aciklama_kutu.addStretch()
        ana.addLayout(aciklama_kutu)

        self._onizle_tablo = QTableWidget()
        self._onizle_tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._onizle_tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._onizle_tablo.setAlternatingRowColors(True)
        self._onizle_tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ana.addWidget(self._onizle_tablo, stretch=1)

        return w

    def _adim3_doldur(self):
        alan_adlari = [at.alan for at in self._konfig_obj.alanlar]
        sutunlar    = alan_adlari + ["Durum", "Hata"]

        self._onizle_tablo.setColumnCount(len(sutunlar))
        self._onizle_tablo.setRowCount(len(self._satirlar))
        self._onizle_tablo.setHorizontalHeaderLabels(sutunlar)

        durum_renk = {
            "pk_duplicate":      RENK_KIRMIZI,
            "yumusak_duplicate": RENK_SARI,
            "zorunlu_eksik":     RENK_GRI,
        }

        for r, satir in enumerate(self._satirlar):
            renk = durum_renk.get(satir.durum)
            for c, alan in enumerate(alan_adlari):
                item = QTableWidgetItem(str(satir.veri.get(alan, "")))
                if renk:
                    item.setBackground(renk)
                self._onizle_tablo.setItem(r, c, item)

            durum_item = QTableWidgetItem(satir.durum or "✔")
            if renk:
                durum_item.setBackground(renk)
            self._onizle_tablo.setItem(r, len(alan_adlari), durum_item)

            hata_item = QTableWidgetItem(satir.hata_mesaji)
            if renk:
                hata_item.setBackground(renk)
            self._onizle_tablo.setItem(r, len(alan_adlari) + 1, hata_item)

        toplam = len(self._satirlar)
        temiz  = sum(1 for s in self._satirlar if s.durum == "")
        self._onizle_bilgi.setText(
            f"<b>{toplam}</b> satır hazırlandı — "
            f"<span style='color:green'><b>{temiz}</b> temiz</span> | "
            f"<span style='color:red'><b>{toplam - temiz}</b> sorunlu</span>"
        )

    # ------------------------------------------------------------------
    # Adım 4 — Sonuç
    # ------------------------------------------------------------------

    def _adim4_olustur(self) -> QWidget:
        w = QWidget()
        ana = QVBoxLayout(w)
        ana.setAlignment(Qt.AlignmentFlag.AlignTop)
        ana.setSpacing(16)

        self._sonuc_baslik = QLabel("")
        self._sonuc_baslik.setStyleSheet("font-size:14px; font-weight:bold;")
        ana.addWidget(self._sonuc_baslik)

        self._kart_kutu = QHBoxLayout()
        ana.addLayout(self._kart_kutu)

        btn_kutu = QHBoxLayout()
        self._btn_duzenle = QPushButton("✏  Hatalıları Düzenle")
        self._btn_yeni    = QPushButton("🔄  Yeni Import")
        self._btn_kapat   = QPushButton("✔  Kapat")

        self._btn_duzenle.setStyleSheet("background:#F57C00; color:white; padding:6px 14px;")
        self._btn_yeni.setStyleSheet("padding:6px 14px;")
        self._btn_kapat.setStyleSheet("background:#2E7D32; color:white; padding:6px 14px;")

        self._btn_duzenle.clicked.connect(self._hata_duzeltme_ac)
        self._btn_yeni.clicked.connect(self._sifirla)
        self._btn_kapat.clicked.connect(self._kapat)

        btn_kutu.addWidget(self._btn_duzenle)
        btn_kutu.addWidget(self._btn_yeni)
        btn_kutu.addStretch()
        btn_kutu.addWidget(self._btn_kapat)
        ana.addLayout(btn_kutu)

        return w

    def _adim4_guncelle(self):
        if not self._sonuc:
            return
        s = self._sonuc

        self._sonuc_baslik.setText(
            f"İçe aktarma tamamlandı — {s.toplam} satır işlendi"
        )

        # Kartları yenile
        while self._kart_kutu.count():
            item = self._kart_kutu.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for sayi, etiket, on_renk, arka_renk in [
            (s.basarili,          "✓ Eklendi",     "#2E7D32", "#E8F5E9"),
            (s.hatali,            "✗ Hatalı",       "#C62828", "#FFEBEE"),
            (s.pk_duplicate,      "⊘ PK Duplicate", "#6A1B9A", "#F3E5F5"),
            (s.yumusak_duplicate, "⚠ Çakışma",      "#E65100", "#FFF3E0"),
            (s.zorunlu_eksik,     "⚫ Eksik Alan",   "#424242", "#FAFAFA"),
        ]:
            self._kart_kutu.addWidget(
                self._kart_olustur(sayi, etiket, on_renk, arka_renk)
            )

        self._btn_duzenle.setVisible(bool(s.duzeltilecekler))

    def _kart_olustur(self, sayi: int, etiket: str, on_renk: str, arka_renk: str) -> QFrame:
        kart = QFrame()
        kart.setFrameShape(QFrame.Shape.StyledPanel)
        kart.setStyleSheet(
            f"background:{arka_renk}; border:1px solid {on_renk}; "
            f"border-radius:8px; padding:8px; min-width:110px;"
        )
        kutu = QVBoxLayout(kart)
        kutu.setSpacing(2)

        sayi_lbl = QLabel(str(sayi))
        sayi_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setPointSize(22)
        f.setBold(True)
        sayi_lbl.setFont(f)
        sayi_lbl.setStyleSheet(f"color:{on_renk};")

        etiket_lbl = QLabel(etiket)
        etiket_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiket_lbl.setStyleSheet(f"color:{on_renk}; font-size:11px;")

        kutu.addWidget(sayi_lbl)
        kutu.addWidget(etiket_lbl)
        return kart

    # ------------------------------------------------------------------
    # Hata düzeltme
    # ------------------------------------------------------------------

    def _hata_duzeltme_ac(self):
        if not self._sonuc:
            return
        alan_adlari = [at.alan for at in self._konfig_obj.alanlar]
        dlg = HataDuzeltmeWidget(
            self._sonuc.duzeltilecekler, alan_adlari, parent=self
        )
        dlg.yeniden_dene.connect(self._yeniden_dene)
        dlg.exec()

    def _yeniden_dene(self, satirlar: list[SatirSonucu]):
        self._svc.yeniden_yukle(
            satirlar, self._konfig_obj, self._db, self._kaydeden
        )
        # Özetin sayaçlarını satır durumlarından yeniden hesapla
        if self._sonuc:
            svc = self._svc
            self._sonuc.basarili      = sum(1 for s in self._sonuc.satirlar if s.durum == "basarili")
            self._sonuc.hatali        = sum(1 for s in self._sonuc.satirlar if s.durum == "hatali")
            self._sonuc.zorunlu_eksik = sum(1 for s in self._sonuc.satirlar if s.durum == "zorunlu_eksik")
        self._adim4_guncelle()

    # ------------------------------------------------------------------
    # Navigasyon
    # ------------------------------------------------------------------

    def _adima_git(self, adim: int):
        self._stack.setCurrentIndex(adim)
        self._adim_gostergesi_guncelle(adim)

        son_adim = adim == 3
        self._btn_geri.setVisible(0 < adim < 3)
        self._btn_ileri.setVisible(not son_adim)

        if adim == 0:
            self._btn_ileri.setEnabled(self._df is not None)
            self._btn_ileri.setText("İleri  ▶")
        elif adim == 1:
            self._btn_ileri.setEnabled(True)
            self._btn_ileri.setText("Önizle  ▶")
        elif adim == 2:
            self._btn_ileri.setEnabled(True)
            self._btn_ileri.setText("İçe Aktar  ▶")

    def _geri(self):
        mevcut = self._stack.currentIndex()
        if mevcut > 0:
            self._adima_git(mevcut - 1)

    def _ileri(self):
        mevcut = self._stack.currentIndex()

        if mevcut == 0:
            if self._df is None:
                QMessageBox.warning(self, "Uyarı", "Lütfen önce bir dosya seçin.")
                return
            self._adim2_doldur()
            self._adima_git(1)

        elif mevcut == 1:
            if not self._zorunlu_alanlar_eslestirildi_mi():
                return
            self._harita        = self._haritayi_oku()
            self._manuel        = self._manuel_degerleri_oku()
            self._satirlar = self._svc.donustur(
                self._df, self._harita, self._konfig_obj, self._manuel
            )
            self._satirlar = self._svc.duplicate_kontrol(
                self._satirlar, self._konfig_obj, self._db
            )
            self._adim3_doldur()
            self._adima_git(2)

        elif mevcut == 2:
            self._btn_ileri.setEnabled(False)
            self._btn_geri.setEnabled(False)
            self._yukle_baslat()

    def _yukle_baslat(self):
        def is_fn():
            return self._svc.yukle(
                self._satirlar, self._konfig_obj, self._db, self._kaydeden
            )
        self._thread = _ImportThread(is_fn, parent=self)
        self._thread.bitti.connect(self._yukle_bitti)
        self._thread.start()

    def _yukle_bitti(self, sonuc):
        self._btn_ileri.setEnabled(True)
        self._btn_geri.setEnabled(True)
        if isinstance(sonuc, Exception):
            QMessageBox.critical(self, "Import Hatası", f"Beklenmeyen hata:\n{sonuc}")
            return
        self._sonuc = sonuc
        self._adim4_guncelle()
        self._adima_git(3)

    # ------------------------------------------------------------------
    # Sıfırla / Kapat
    # ------------------------------------------------------------------

    def _sifirla(self):
        self._df            = None
        self._harita        = {}
        self._manuel        = {}
        self._satirlar      = []
        self._sonuc         = None
        self._combo_map.clear()
        self._lineedit_map.clear()
        self._dosya_bilgi.setText("")
        self._adima_git(0)

    def _kapat(self):
        """Ebeveyn pencereye bırakılır; gerekirse override edilebilir."""
        pass
