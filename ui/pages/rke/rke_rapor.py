# -*- coding: utf-8 -*-
"""
RKE Raporlama
═══════════════════════════════════════════════════════════
Mod 1 — Aktif Envanter  : ABD/Birim filtreli, son muayene dahil
Mod 2 — Hurda Listesi   : Durum=UygunDeğil VEYA son muayene başarısız
         + "Bölüm Bazlı Grupla" checkbox → aynı şablonu gruplu çıkarır
"""
import datetime
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QMarginsF, QSortFilterProxyModel
from PySide6.QtGui import QCursor, QTextDocument, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QCheckBox, QTableView, QAbstractItemView, QApplication,
)

from core.logger import logger
from core.di import get_rke_service
from core.hata_yonetici import hata_goster, uyari_goster
from ui.components.base_table_model import BaseTableModel
from ui.styles.icons import IconRenderer, IconColors


# ═══════════════════════════════════════════════════════════
#  HTML / PDF ŞABLONLARI
# ═══════════════════════════════════════════════════════════

def _css() -> str:
    return (
        "body{font-family:'Times New Roman',serif;font-size:11pt;color:#000;}"
        "h1{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:4px;}"
        "h2{font-size:11pt;font-weight:bold;margin-top:14px;margin-bottom:4px;"
        "background:#ddd;padding:3px 6px;}"
        ".c{text-align:center;font-size:10pt;margin-bottom:8px;}"
        "table{width:100%;border-collapse:collapse;margin-top:6px;font-size:9.5pt;}"
        "th,td{border:1px solid #000;padding:3px 5px;vertical-align:middle;}"
        "th{background:#eee;font-weight:bold;text-align:center;}"
        ".l{text-align:left;} .c2{text-align:center;}"
        "tr:nth-child(even){background:#f9f9f9;}"
        ".sig{width:100%;border:none;margin-top:36px;}"
        ".sig td{border:none;text-align:center;vertical-align:top;padding:16px;}"
        ".line{border-top:1px solid #000;width:70%;margin:28px auto 0;}"
        ".legal{text-align:justify;margin:6px 0;line-height:1.5;font-size:10pt;}"
        ".uygun{color:#1a7a1a;font-weight:600;}"
        ".uygun_d{color:#b00000;font-weight:600;}"
    )


def _imza_satiri() -> str:
    return ("<table class='sig'><tr>"
            "<td><b>Kontrol Eden</b><div class='line'></div></td>"
            "<td><b>Birim Sorumlusu</b><div class='line'></div></td>"
            "<td><b>Radyasyon Koruma Sorumlusu</b><div class='line'></div></td>"
            "</tr></table>")


def _envanter_satirlari(veriler: list[dict]) -> str:
    satirlar = []
    for i, r in enumerate(veriler, 1):
        son_t  = r.get("SonMuayeneTarihi", "—")
        son_d  = r.get("SonMuayeneDurum",  "—")
        renk   = "uygun" if "Değil" not in son_d and son_d != "—" else "uygun_d"
        satirlar.append(
            f"<tr>"
            f"<td class='c2'>{i}</td>"
            f"<td class='l'>{r.get('Cins','')}</td>"
            f"<td class='c2'>{r.get('EkipmanNo','')}</td>"
            f"<td class='c2'>{r.get('Pb','')}</td>"
            f"<td class='l'>{r.get('Birim','')}</td>"
            f"<td class='c2'>{r.get('KontrolTarihi','—')}</td>"
            f"<td class='c2'>{son_t}</td>"
            f"<td class='c2 {renk}'>{son_d}</td>"
            f"</tr>"
        )
    return "".join(satirlar)


def _hurda_satirlari(veriler: list[dict]) -> str:
    satirlar = []
    for i, r in enumerate(veriler, 1):
        neden_list = []
        if "Değil" in r.get("EnvanterDurum", ""):
            neden_list.append("Envanter: " + r.get("EnvanterDurum", ""))
        if "Değil" in r.get("SonFiziksel", ""):
            neden_list.append("Fiziksel: " + r.get("SonFiziksel", ""))
        if "Değil" in r.get("SonSkopi", ""):
            neden_list.append("Skopi: " + r.get("SonSkopi", ""))
        neden = " | ".join(neden_list) or r.get("Aciklama", "")
        satirlar.append(
            f"<tr>"
            f"<td class='c2'>{i}</td>"
            f"<td class='l'>{r.get('Cins','')}</td>"
            f"<td class='c2'>{r.get('EkipmanNo','')}</td>"
            f"<td class='c2'>{r.get('Pb','')}</td>"
            f"<td class='l'>{r.get('ABD','')}</td>"
            f"<td class='l'>{r.get('Birim','')}</td>"
            f"<td class='l'>{neden}</td>"
            f"</tr>"
        )
    return "".join(satirlar)


def html_envanter_raporu(veriler: list[dict], filtre: str) -> str:
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    baslik_satirlari = (
        "<tr><th width='4%'>No</th><th width='14%'>Cins</th>"
        "<th width='14%'>Ekipman No</th><th width='7%'>Pb</th>"
        "<th width='14%'>Birim</th><th width='12%'>Kontrol T.</th>"
        "<th width='12%'>Son Muayene</th><th width='23%'>Durum</th></tr>"
    )
    return (
        f"<html><head><meta charset='utf-8'><style>{_css()}</style></head><body>"
        f"<h1>RKE AKTİF ENVANTER RAPORU</h1>"
        f"<div class='c'>{filtre} &nbsp;|&nbsp; Rapor Tarihi: {tarih} &nbsp;|&nbsp; "
        f"Toplam: {len(veriler)} ekipman</div>"
        f"<table><thead>{baslik_satirlari}</thead>"
        f"<tbody>{_envanter_satirlari(veriler)}</tbody></table>"
        f"{_imza_satiri()}</body></html>"
    )


def html_hurda_raporu(veriler: list[dict], filtre: str,
                      gruplu: bool = False) -> str:
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    baslik_satirlari = (
        "<tr><th width='4%'>No</th><th width='13%'>Cins</th>"
        "<th width='14%'>Ekipman No</th><th width='6%'>Pb</th>"
        "<th width='14%'>ABD</th><th width='14%'>Birim</th>"
        "<th width='35%'>Uygunsuzluk</th></tr>"
    )
    if gruplu:
        # ABD → Birim gruplu çıktı
        from itertools import groupby
        sirali = sorted(veriler, key=lambda r: (r.get("ABD",""), r.get("Birim","")))
        icerik = ""
        for abd, abd_grup in groupby(sirali, key=lambda r: r.get("ABD","")):
            abd_listesi = list(abd_grup)
            icerik += f"<h2>{abd}</h2>"
            for birim, b_grup in groupby(abd_listesi, key=lambda r: r.get("Birim","")):
                b_listesi = list(b_grup)
                icerik += (f"<b>Birim: {birim}</b> ({len(b_listesi)} ekipman)"
                           f"<table><thead>{baslik_satirlari}</thead>"
                           f"<tbody>{_hurda_satirlari(b_listesi)}</tbody></table>")
    else:
        icerik = (f"<table><thead>{baslik_satirlari}</thead>"
                  f"<tbody>{_hurda_satirlari(veriler)}</tbody></table>")

    return (
        f"<html><head><meta charset='utf-8'><style>{_css()}</style></head><body>"
        f"<h1>HURDA (HEK) EKİPMAN TEKNİK RAPORU</h1>"
        f"<div class='c'>{filtre} &nbsp;|&nbsp; Tarih: {tarih} &nbsp;|&nbsp; "
        f"Toplam: {len(veriler)} ekipman</div>"
        f"{icerik}"
        f"<div class='legal' style='margin-top:14px;'>"
        f"Yukarıda belirtilen ekipmanların fiziksel veya radyolojik bütünlüklerini "
        f"yitirdikleri ve/veya periyodik muayenede uygunsuz bulundukları tespit "
        f"edilmiştir. HEK kaydına alınması arz olunur.</div>"
        f"{_imza_satiri()}</body></html>"
    )


def pdf_yaz(html: str, kayit: str) -> bool:
    try:
        doc = QTextDocument()
        doc.setHtml(html)
        w = QPdfWriter(kayit)
        w.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        w.setResolution(300)
        lay = QPageLayout()
        lay.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        lay.setOrientation(QPageLayout.Orientation.Portrait)
        lay.setMargins(QMarginsF(15, 15, 15, 15))
        w.setPageLayout(lay)
        doc.print_(w)
        return True
    except Exception as e:
        logger.error(f"PDF yazma: {e}")
        return False


# ═══════════════════════════════════════════════════════════
#  VERİ YÜKLEYİCİ
# ═══════════════════════════════════════════════════════════

class _VeriYukleyici(QThread):
    """
    get_rapor_verisi() → RKE listesi + muayene listesi alır,
    her ekipman için son muayene bilgisini hesaplar, birleşik liste döner.
    """
    veri_hazir  = Signal(list, list, list)   # birlesik, abd_listesi, birim_listesi
    hata_olustu = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db

    def run(self):
        try:
            svc   = get_rke_service(self._db)
            sonuc = svc.get_rapor_verisi()
            if not sonuc.basarili:
                self.hata_olustu.emit(sonuc.mesaj)
                return

            rke_list     = sonuc.veri.get("rke_list", [])
            muayene_list = sonuc.veri.get("muayene_list", [])

            # Ekipman başına son muayeneyi bul
            son_muayene: dict[str, dict] = {}
            for m in muayene_list:
                en  = str(m.get("EkipmanNo", "")).strip()
                tar = str(m.get("FMuayeneTarihi") or "").strip()
                if not en:
                    continue
                mevcut = son_muayene.get(en)
                if not mevcut or tar > mevcut.get("FMuayeneTarihi", ""):
                    son_muayene[en] = m

            abd_s:   set[str] = set()
            birim_s: set[str] = set()
            birlesik: list[dict] = []

            for r in rke_list:
                en  = str(r.get("EkipmanNo", "")).strip()
                abd = str(r.get("AnaBilimDali", "")).strip()
                bir = str(r.get("Birim", "")).strip()
                if abd:   abd_s.add(abd)
                if bir:   birim_s.add(bir)

                m   = son_muayene.get(en, {})
                fiz = str(m.get("FizikselDurum", "")).strip()
                sko = str(m.get("SkopiDurum", "")).strip()

                # Hurda mı?
                env_durum  = str(r.get("Durum", "")).strip()
                muayene_kt = ("Kullanıma Uygun Değil"
                              if ("Değil" in fiz or "Değil" in sko)
                              else ("Kullanıma Uygun" if fiz else ""))
                is_hurda = ("Değil" in env_durum or "Değil" in muayene_kt)

                birlesik.append({
                    # Envanter
                    "EkipmanNo":      en,
                    "Cins":           str(r.get("KoruyucuCinsi", "")).strip(),
                    "Pb":             str(r.get("KursunEsdegeri", "")).strip(),
                    "ABD":            abd,
                    "Birim":          bir,
                    "KontrolTarihi":  str(r.get("KontrolTarihi", "")).strip(),
                    "EnvanterDurum":  env_durum,
                    # Son muayene
                    "SonMuayeneTarihi": str(m.get("FMuayeneTarihi", "")).strip(),
                    "SonFiziksel":      fiz,
                    "SonSkopi":         sko,
                    "SonMuayeneDurum":  muayene_kt,
                    "Aciklama":         str(m.get("Aciklamalar", "")).strip(),
                    # Hesaplanan
                    "IsHurda":          is_hurda,
                })

            self.veri_hazir.emit(
                birlesik,
                sorted(abd_s),
                sorted(birim_s),
            )
        except Exception as e:
            logger.error(f"Rapor veri yükleme: {e}")
            self.hata_olustu.emit(str(e))


# ═══════════════════════════════════════════════════════════
#  PDF WORKER
# ═══════════════════════════════════════════════════════════

class _PdfWorker(QThread):
    log_mesaji  = Signal(str)
    islem_bitti = Signal()

    def __init__(self, mod: int, veriler: list[dict],
                 filtre: str, kayit: str, gruplu: bool = False):
        super().__init__()
        self._mod    = mod
        self._veri   = veriler
        self._filtre = filtre
        self._kayit  = kayit
        self._gruplu = gruplu

    def run(self):
        try:
            from core.rapor_servisi import RaporServisi
            tarih_str = datetime.datetime.now().strftime("%d.%m.%Y")

            if self._mod == 1:
                # Aktif Envanter
                context = {"baslik": "RKE AKTİF ENVANTER RAPORU",
                           "filtre": self._filtre, "tarih": tarih_str}
                yol = RaporServisi.pdf("rke_envanter", context,
                                       self._veri, self._kayit)
                if not yol:
                    yol = self._kayit if pdf_yaz(
                        html_envanter_raporu(self._veri, self._filtre),
                        self._kayit
                    ) else None

            else:
                # Hurda
                context = {"baslik": "HURDA (HEK) EKİPMAN RAPORU",
                           "filtre": self._filtre, "tarih": tarih_str,
                           "gruplu": self._gruplu}
                yol = RaporServisi.pdf("rke_hurda", context,
                                       self._veri, self._kayit)
                if not yol:
                    yol = self._kayit if pdf_yaz(
                        html_hurda_raporu(self._veri, self._filtre,
                                          gruplu=self._gruplu),
                        self._kayit
                    ) else None

            if yol:
                self.log_mesaji.emit(f"✔ Rapor hazır: {yol}")
                RaporServisi.ac(yol)
            else:
                self.log_mesaji.emit("✗ PDF oluşturulamadı.")

        except Exception as e:
            self.log_mesaji.emit(f"✗ Hata: {e}")
        finally:
            self.islem_bitti.emit()


# ═══════════════════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════════════════

_COLS_ENV = [
    ("EkipmanNo",        "Ekipman No",       120),
    ("Cins",             "Cins",             110),
    ("Pb",               "Pb",                50),
    ("ABD",              "Ana Bilim Dalı",   150),
    ("Birim",            "Birim",            130),
    ("KontrolTarihi",    "Kontrol T.",        100),
    ("SonMuayeneTarihi", "Son Muayene",       100),
    ("SonMuayeneDurum",  "Durum",             140),
]

_COLS_HURDA = [
    ("EkipmanNo",     "Ekipman No",   120),
    ("Cins",          "Cins",         110),
    ("Pb",            "Pb",            50),
    ("ABD",           "Ana Bilim D.", 150),
    ("Birim",         "Birim",        130),
    ("EnvanterDurum", "Env. Durum",   130),
    ("SonFiziksel",   "Son Fiziksel", 140),
    ("SonSkopi",      "Son Skopi",    140),
]


class _RaporModel(BaseTableModel):
    def __init__(self, cols, parent=None):
        super().__init__(cols, parent=parent)

    def _display(self, key: str, row: dict) -> str:
        return str(row.get(key, "") or "")

    def _fg(self, key: str, row: dict):
        v = str(row.get(key, ""))
        if "Değil" in v:
            return self.status_fg("Uygun Değil")
        if "Uygun" in v:
            return self.status_fg("Uygun")
        return None

    def _align(self, key: str):
        if key in ("Pb", "KontrolTarihi", "SonMuayeneTarihi"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows):
        self.set_data(rows)


# ═══════════════════════════════════════════════════════════
#  SAYFA
# ═══════════════════════════════════════════════════════════

class RKERaporPenceresi(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db           = db
        self._action_guard = action_guard
        self._ham:          list[dict] = []
        self._filtrelenmis: list[dict] = []
        self._kpi:          dict[str, QLabel] = {}
        self._loader:       Optional[_VeriYukleyici] = None
        self._worker:       Optional[_PdfWorker]     = None

        self._setup_ui()
        self._connect_signals()
        if db:
            self.load_data()

    # ─── UI ──────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_kontrol_paneli())
        root.addWidget(self._build_table(), 1)
        root.addWidget(self._build_footer())

    # ─── KPI ─────────────────────────────────────────────

    def _build_kpi_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setProperty("bg-role", "panel")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        for key, title, role in [
            ("toplam",  "TOPLAM EKİPMAN",  "accent"),
            ("uygun",   "KULLANIMA UYGUN",  "ok"),
            ("uygun_d", "UYGUN DEĞİL",      "err"),
            ("hurda",   "HURDA ADAYI",      "warn"),
            ("muayene", "SON 1 YILDA MUAYENE EDİLEN", "muted"),
        ]:
            lay.addWidget(self._kpi_card(key, title, role), 1)
        return bar

    def _kpi_card(self, key, title, role) -> QWidget:
        w = QWidget(); w.setProperty("bg-role", "page")
        hl = QHBoxLayout(w); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(0)
        bar = QFrame(); bar.setFixedWidth(3); bar.setProperty("bg-role", "separator")
        hl.addWidget(bar)
        c = QWidget(); c.setProperty("bg-role", "page")
        vl = QVBoxLayout(c); vl.setContentsMargins(14, 8, 14, 8); vl.setSpacing(2)
        lt = QLabel(title); lt.setProperty("style-role", "kpi-label"); lt.setProperty("color-role", "disabled")
        lv = QLabel("0");   lv.setProperty("style-role", "kpi-value"); lv.setProperty("color-role", role)
        vl.addWidget(lt); vl.addWidget(lv)
        hl.addWidget(c, 1)
        self._kpi[key] = lv
        return w

    # ─── Toolbar ─────────────────────────────────────────

    def _build_kontrol_paneli(self) -> QFrame:
        """
        3 sütunlu kontrol paneli:
          [1] Rapor Türü     [2] Filtreler     [3] İşlemler
        """
        from PySide6.QtWidgets import QGroupBox, QGridLayout
        outer = QFrame()
        outer.setProperty("bg-role", "panel")
        outer.setFixedHeight(110)
        lay = QHBoxLayout(outer)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(0)

        # ── SÜTUN 1: Rapor Türü ──────────────────────────
        grp_tur = QGroupBox("Rapor Türü")
        grp_tur.setProperty("style-role", "group")
        vt = QVBoxLayout(grp_tur)
        vt.setContentsMargins(10, 4, 10, 4)
        vt.setSpacing(4)

        self._bg = QButtonGroup(self)
        self.rb_envanter = QRadioButton("Aktif Envanter Listesi")
        self.rb_hurda    = QRadioButton("Hurda (HEK) Listesi")
        self.rb_envanter.setChecked(True)
        for rb in (self.rb_envanter, self.rb_hurda):
            rb.setProperty("style-role", "radio")
            self._bg.addButton(rb)
            vt.addWidget(rb)

        self.chk_gruplu = QCheckBox("  Bölüm Bazlı Grupla")
        self.chk_gruplu.setProperty("style-role", "check")
        self.chk_gruplu.setEnabled(False)
        self.chk_gruplu.setToolTip("Hurda raporunu ABD ve Birim bazlı gruplandırır")
        vt.addWidget(self.chk_gruplu)

        lay.addWidget(grp_tur, 2)
        lay.addSpacing(10)

        # ── SÜTUN 2: Filtreler ───────────────────────────
        grp_fil = QGroupBox("Filtreler")
        grp_fil.setProperty("style-role", "group")
        gf = QGridLayout(grp_fil)
        gf.setContentsMargins(10, 4, 10, 4)
        gf.setSpacing(6)

        def _flbl(t):
            l = QLabel(t); l.setProperty("style-role","stat-label")
            l.setProperty("color-role", "muted"); return l

        gf.addWidget(_flbl("Ana Bilim Dalı"), 0, 0)
        self.cmb_abd = QComboBox(); self.cmb_abd.addItem("Tümü")
        gf.addWidget(self.cmb_abd, 1, 0)

        gf.addWidget(_flbl("Birim"), 0, 1)
        self.cmb_birim = QComboBox(); self.cmb_birim.addItem("Tümü")
        gf.addWidget(self.cmb_birim, 1, 1)

        gf.addWidget(_flbl("Muayene Tarihi"), 0, 2)
        self.cmb_tarih = QComboBox(); self.cmb_tarih.addItem("Tüm Tarihler")
        self.cmb_tarih.setToolTip("Seçilen tarihte muayenesi yapılan ekipmanları filtreler")
        gf.addWidget(self.cmb_tarih, 1, 2)

        gf.setColumnStretch(0, 2)
        gf.setColumnStretch(1, 2)
        gf.setColumnStretch(2, 2)

        lay.addWidget(grp_fil, 5)
        lay.addSpacing(10)

        # ── SÜTUN 3: İşlemler ────────────────────────────
        grp_isl = QGroupBox("İşlemler")
        grp_isl.setProperty("style-role", "group")
        vi = QVBoxLayout(grp_isl)
        vi.setContentsMargins(10, 4, 10, 4)
        vi.setSpacing(6)

        self.btn_yenile = QPushButton(" Verileri Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.setFixedHeight(28)
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=IconColors.MUTED, size=14)
        vi.addWidget(self.btn_yenile)

        self.btn_pdf = QPushButton(" PDF Rapor Oluştur")
        self.btn_pdf.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_pdf.setProperty("style-role", "action")
        self.btn_pdf.setFixedHeight(28)
        IconRenderer.set_button_icon(self.btn_pdf, "file_text", color=IconColors.PRIMARY, size=14)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_pdf, "cihaz.write")
        vi.addWidget(self.btn_pdf)

        lay.addWidget(grp_isl, 2)
        return outer

    # ─── Tablo ───────────────────────────────────────────

    def _build_table(self) -> QWidget:
        wrap = QWidget()
        vl   = QVBoxLayout(wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Envanter tablo
        self._model_env   = _RaporModel(_COLS_ENV)
        self._proxy_env   = QSortFilterProxyModel(self)
        self._proxy_env.setSourceModel(self._model_env)

        self.tablo_env = QTableView()
        self.tablo_env.setModel(self._proxy_env)
        self._table_setup(self.tablo_env)
        self._model_env.setup_columns(self.tablo_env, stretch_keys=["SonMuayeneDurum"])
        vl.addWidget(self.tablo_env)

        # Hurda tablo
        self._model_hurda = _RaporModel(_COLS_HURDA)
        self._proxy_hurda = QSortFilterProxyModel(self)
        self._proxy_hurda.setSourceModel(self._model_hurda)

        self.tablo_hurda = QTableView()
        self.tablo_hurda.setModel(self._proxy_hurda)
        self._table_setup(self.tablo_hurda)
        self._model_hurda.setup_columns(self.tablo_hurda, stretch_keys=["SonSkopi"])
        self.tablo_hurda.setVisible(False)
        vl.addWidget(self.tablo_hurda)
        return wrap

    @staticmethod
    def _table_setup(t: QTableView):
        t.setAlternatingRowColors(True)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        t.setSortingEnabled(True)
        t.verticalHeader().setDefaultSectionSize(36)

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setProperty("bg-role", "panel")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        self.lbl_durum = QLabel("")
        self.lbl_durum.setProperty("color-role", "muted")
        lay.addWidget(self.lbl_durum)
        lay.addStretch()
        self.lbl_sayi = QLabel("0 kayıt")
        self.lbl_sayi.setProperty("style-role", "footer")
        lay.addWidget(self.lbl_sayi)
        return frame

    # ─── Sinyaller ───────────────────────────────────────

    def _connect_signals(self):
        self._bg.buttonClicked.connect(self._mod_degisti)
        self.chk_gruplu.stateChanged.connect(lambda _: self._filtrele())
        self.cmb_tarih.currentIndexChanged.connect(lambda _: self._filtrele())
        self.cmb_abd.currentIndexChanged.connect(lambda _: self._filtrele())
        self.cmb_birim.currentIndexChanged.connect(lambda _: self._filtrele())
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_pdf.clicked.connect(self._rapor_baslat)

    def _mod_degisti(self):
        hurda = self.rb_hurda.isChecked()
        self.chk_gruplu.setEnabled(hurda)
        self.tablo_env.setVisible(not hurda)
        self.tablo_hurda.setVisible(hurda)
        self._filtrele()

    # ─── Veri ────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        self.btn_pdf.setEnabled(False)
        self.lbl_durum.setText("Yükleniyor…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self._loader = _VeriYukleyici(self._db)
        self._loader.veri_hazir.connect(self._veri_geldi)
        self._loader.hata_olustu.connect(self._yukleme_hata)
        self._loader.finished.connect(self._yukle_bitti)
        self._loader.start()

    def _veri_geldi(self, data: list, abd_l: list, birim_l: list):
        self._ham = data

        # ABD / Birim combolar
        for cmb, liste in [(self.cmb_abd, abd_l), (self.cmb_birim, birim_l)]:
            cur = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear(); cmb.addItem("Tümü"); cmb.addItems(liste)
            idx = cmb.findText(cur)
            if idx >= 0: cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        # Tarih combo — mevcut muayene tarihlerini dd.MM.yyyy formatında listele
        def _d(s):
            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                try: return datetime.datetime.strptime(s, fmt).date()
                except: pass
            return datetime.date.min

        tarihler = sorted(
            {r.get("SonMuayeneTarihi", "") for r in data if r.get("SonMuayeneTarihi")},
            reverse=True, key=_d
        )
        cur_t = self.cmb_tarih.currentText()
        self.cmb_tarih.blockSignals(True)
        self.cmb_tarih.clear()
        self.cmb_tarih.addItem("Tüm Tarihler")
        for t in tarihler:
            # yyyy-MM-dd → dd.MM.yyyy görünümü
            try:
                d = datetime.datetime.strptime(t, "%Y-%m-%d")
                self.cmb_tarih.addItem(d.strftime("%d.%m.%Y"), userData=t)
            except Exception:
                self.cmb_tarih.addItem(t, userData=t)
        idx = self.cmb_tarih.findText(cur_t)
        if idx >= 0: self.cmb_tarih.setCurrentIndex(idx)
        self.cmb_tarih.blockSignals(False)

        self._filtrele()

    def _yukle_bitti(self):
        QApplication.restoreOverrideCursor()
        self.btn_pdf.setEnabled(True)
        self.lbl_durum.setText("")

    def _yukleme_hata(self, msg: str):
        QApplication.restoreOverrideCursor()
        self.btn_pdf.setEnabled(True)
        self.lbl_durum.setText("")
        hata_goster(self, msg)

    # ─── Filtreleme ──────────────────────────────────────

    def _filtrele(self):
        fa = self.cmb_abd.currentText()
        fb = self.cmb_birim.currentText()
        # userData = "yyyy-MM-dd", "Tüm Tarihler" ise None
        ft_raw = self.cmb_tarih.currentData() or ""
        ft_lbl = self.cmb_tarih.currentText()

        filtered = []
        for r in self._ham:
            if "Tümü" not in fa and r.get("ABD", "") != fa:           continue
            if "Tümü" not in fb and r.get("Birim", "") != fb:         continue
            if ft_raw and r.get("SonMuayeneTarihi", "") != ft_raw:    continue
            filtered.append(r)

        if self.rb_hurda.isChecked():
            filtered = [r for r in filtered if r.get("IsHurda")]
            self._model_hurda.set_rows(filtered)
            self.lbl_sayi.setText(f"{len(filtered)} hurda adayı")
        else:
            self._model_env.set_rows(filtered)
            self.lbl_sayi.setText(f"{len(filtered)} ekipman")

        self._filtrelenmis = filtered
        self._update_kpi(filtered if self.rb_envanter.isChecked() else self._ham)

    # ─── KPI Güncelle ────────────────────────────────────

    def _update_kpi(self, rows: list[dict]):
        toplam  = len(rows)
        uygun   = sum(1 for r in rows if r.get("EnvanterDurum","") == "Uygun"
                      and not r.get("IsHurda"))
        uygun_d = sum(1 for r in rows if "Değil" in r.get("EnvanterDurum",""))
        hurda   = sum(1 for r in rows if r.get("IsHurda"))
        gun_365 = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
        muayene = sum(1 for r in rows
                      if r.get("SonMuayeneTarihi","") >= gun_365)
        for k, v in [("toplam", toplam), ("uygun", uygun),
                     ("uygun_d", uygun_d), ("hurda", hurda), ("muayene", muayene)]:
            if k in self._kpi:
                self._kpi[k].setText(str(v))

    # ─── PDF ─────────────────────────────────────────────

    def _rapor_baslat(self):
        if not self._filtrelenmis:
            uyari_goster(self, "Rapor alınacak veri yok.")
            return

        from core.rapor_servisi import RaporServisi
        now  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mod  = 1 if self.rb_envanter.isChecked() else 2
        isim = f"RKE_Envanter_{now}" if mod == 1 else f"RKE_Hurda_{now}"

        kayit = RaporServisi.kaydet_diyalogu(self, isim, tur="pdf")
        if not kayit:
            return

        fa    = self.cmb_abd.currentText()
        fb    = self.cmb_birim.currentText()
        ft    = self.cmb_tarih.currentText()
        filtre = " | ".join(p for p in [
            fa if "Tümü" not in fa else "",
            fb if "Tümü" not in fb else "",
            ft if "Tüm Tarihler" not in ft else "",
        ] if p) or "Tüm Kayıtlar"

        self.btn_pdf.setEnabled(False)
        self.lbl_durum.setText("PDF oluşturuluyor…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self._worker = _PdfWorker(
            mod, self._filtrelenmis, filtre, kayit,
            gruplu=self.chk_gruplu.isChecked(),
        )
        self._worker.log_mesaji.connect(self.lbl_durum.setText)
        self._worker.islem_bitti.connect(self._rapor_tamam)
        self._worker.start()

    def _rapor_tamam(self):
        QApplication.restoreOverrideCursor()
        self.btn_pdf.setEnabled(True)

    # ─── Yardımcı ────────────────────────────────────────

    @staticmethod
    def _vsep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedHeight(24)
        f.setProperty("bg-role", "separator")
        return f

    def closeEvent(self, event):
        for t in (self._loader, self._worker):
            if t and t.isRunning():
                t.quit(); t.wait(500)
        event.accept()


# Uyumluluk alias
RKERaporPage = RKERaporPenceresi
