# -*- coding: utf-8 -*-
"""
dozimetre_import.py — RADAT PDF içe aktarma sayfası
Yenilikler: mükerrer önleme (UNIQUE RaporNo+SiraNo) + personel eşleştirme
"""
from __future__ import annotations
import re, sqlite3, uuid
from typing import Optional
import pdfplumber
from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableView, QHeaderView, QFileDialog,
    QMessageBox, QProgressBar, QAbstractItemView,
)
from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S

PREVIEW_COLS = [
    ("AdSoyad",        "Ad Soyad",  200),
    ("PersonelID",     "TC / ID",   130),
    ("CalistiBirim",   "Birim",     140),
    ("DozimetreNo",    "Dzm. No",    80),
    ("Hp10",           "Hp(10)",     70),
    ("Hp007",          "Hp(0,07)",   70),
    ("Durum",          "Durum",     130),
    ("_eslesti_label", "Eşleşme",    90),
]

# ─── Eşleştirme ────────────────────────────────────────────────
def _match_tc(masked: str, real: str) -> bool:
    m = re.match(r"^([0-9]+)(\*+)([0-9]+)$", masked)
    if not m:
        return False
    prefix, stars, suffix = m.group(1), m.group(2), m.group(3)
    expected = len(prefix) + len(stars) + len(suffix)
    return len(real) == expected and real.startswith(prefix) and real.endswith(suffix)


def _name_score(pdf_name: str, real_name: str) -> int:
    """
    PDF'deki kısmi isim ile DB'deki tam isim arasında eşleşme skoru.
    Yıldız-arası TÜM görünür segmentler değerlendirilir.
    Örnek: 'ZEYN**TÜRKDÖNM**' → ['ZEYN','TÜRKDÖNM'] her ikisi de aranır.
    """
    import unicodedata
    def norm(s):
        s = unicodedata.normalize("NFKD", s.upper())
        return s.encode("ascii", "ignore").decode()
    real_parts = [norm(p) for p in real_name.split() if p]
    if not real_parts:
        return 0
    score = 0
    for pp in pdf_name.split():
        segs = [s for s in pp.split("*") if s]
        for seg in segs:
            seg_n = norm(seg)
            if not seg_n:
                continue
            for rp in real_parts:
                if rp.startswith(seg_n):
                    score += len(seg_n)
                    break
    return score


def match_personel(row: dict, personel_list: list[dict]) -> Optional[dict]:
    """
    1. TC maskesiyle DB'de aday bul.
    2. Aday yoksa → None (masked TC kalır).
    3. Adaylar arasında PDF ismiyle skor hesapla:
       - En yüksek skor > 0 → o kişiyi döndür
       - Tüm skorlar 0 → isim örtüşmesi yok, None (masked TC kalır)
       Tek aday olsa bile isim uyuşmuyorsa yanlış eşleşme olmaz.
    """
    tc_masked = row.get("PersonelID", "")
    pdf_name  = row.get("AdSoyad", "")
    candidates = [p for p in personel_list
                  if _match_tc(tc_masked, str(p.get("KimlikNo", "")))]
    if not candidates:
        return None
    en_iyi: Optional[dict] = None
    en_iyi_skor = 0
    for aday in candidates:
        skor = _name_score(pdf_name, str(aday.get("AdSoyad", "")))
        if skor > en_iyi_skor:
            en_iyi_skor = skor
            en_iyi = aday
    return en_iyi if en_iyi_skor > 0 else None

# ─── PDF Parser ─────────────────────────────────────────────────
def _parse_hp(raw) -> Optional[float]:
    if not raw: return None
    s = str(raw).strip()
    if "0,05" in s or "altındadır" in s: return 0.05
    s = s.replace(",", ".")
    try:
        v = float(s)
        return v if 0 <= v <= 500 else None
    except ValueError:
        return None

def _is_tc_masked(s: str) -> bool:
    return bool(re.match(r"^\d+\*+\d+$", str(s).strip()))


def _smart_parse_row(row: list) -> dict:
    birim = vucut = dzm_no = durum = ""
    hp10 = hp007 = None

    # row[1] ve row[2] — TC ile ad pozisyonu otomatik tespit
    r1 = str(row[1] or "").strip().replace("\n", " ")
    r2 = str(row[2] or "").strip().replace("\n", " ")

    if _is_tc_masked(r1.split()[0] if r1.split() else ""):
        tc_raw   = r1.split()[0]
        ad_soyad = r2
    else:
        ad_soyad = r1
        tc_raw   = r2.split()[0] if r2.split() else r2

    for i in range(3, len(row)):
        v = row[i]
        if not v: continue
        s = str(v).strip()
        if "Radyoloji" in s and not birim:
            birim = "Radyoloji A.B.D."
        elif any(k in s for k in ("Vücut","Önlük","Bilek","Yaka")) and not vucut:
            vucut = s.replace("\n"," ")
        elif s.isdigit() and not dzm_no:
            dzm_no = s
        elif "Sınırın" in s or "Aşım" in s:
            durum = s
        elif _parse_hp(s) is not None and dzm_no:
            if hp10 is None: hp10 = _parse_hp(s)
            elif hp007 is None: hp007 = _parse_hp(s)
    return {
        "AdSoyad":      ad_soyad,
        "PersonelID":   tc_raw,   # masked TC → başlangıç değeri, eşleşince gerçek TC yazılır
        "CalistiBirim": birim or "Radyoloji A.B.D.",
        "VucutBolgesi": vucut,
        "DozimetreNo":  dzm_no,
        "Hp10":         hp10,
        "Hp007":        hp007,
        "Durum":        durum or "Sınırın Altında",
    }

def parse_radat_pdf(pdf_path: str) -> tuple[dict, list[dict]]:
    header: dict = {}
    all_rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            if "RaporNo" not in header:
                m = re.search(r"Rapor\s*(?:No|Numaras[ıiIİ])\s*[:\s]+([0-9]{3,12})",
                              text, re.IGNORECASE)
                if m:
                    header["RaporNo"] = m.group(1).strip()
                else:
                    for line in text.splitlines():
                        line = line.strip()
                        if re.fullmatch(r"\d{3,12}", line):
                            header["RaporNo"] = line
                            break

            if "Periyot" not in header:
                m = re.search(
                    r"Periyot\s*/\s*Y[ıi]l\s*[:\s]+(\d+)\s*\(([^)]+)\)\s*/\s*(\d{4})",
                    text, re.IGNORECASE)
                if m:
                    header["Periyot"]    = int(m.group(1))
                    header["PeriyotAdi"] = m.group(2).strip()
                    header["Yil"]        = int(m.group(3))
                else:
                    m = re.search(r"(\d+)[.\s]*\s*Periyot\s*/\s*(\d{4})", text, re.IGNORECASE)
                    if m:
                        header["Periyot"] = int(m.group(1))
                        header["Yil"]     = int(m.group(2))

            if "DozimetriTipi" not in header:
                m = re.search(r"Dozimetr[ei]\s+Tip[i]?\s*[:\s]+(\w+)", text, re.IGNORECASE)
                if m:
                    header["DozimetriTipi"] = m.group(1)

            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0]: continue
                    if not str(row[0]).strip().isdigit(): continue
                    all_rows.append(_smart_parse_row(row))

    return header, all_rows

# ─── Workers ────────────────────────────────────────────────────
class _PdfLoader(QThread):
    finished = _Signal(dict, list, int, int)
    error    = _Signal(str)

    def __init__(self, pdf_path: str, db):
        super().__init__()
        self._path = pdf_path
        self._db   = db

    @staticmethod
    def _db_path(db) -> str:
        if isinstance(db, str):
            return db
        for attr in ("db_path", "_db_path", "path", "_path"):
            val = getattr(db, attr, None)
            if val and isinstance(val, str):
                return val
        return str(db)

    def run(self):
        try:
            header, rows = parse_radat_pdf(self._path)
            personel_list: list[dict] = []
            db_path = self._db_path(self._db)
            if db_path:
                try:
                    conn = sqlite3.connect(db_path, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    personel_list = [dict(r) for r in
                        conn.execute("SELECT KimlikNo, AdSoyad FROM Personel").fetchall()]
                    conn.close()
                except Exception:
                    pass
            eslesen = eslesmez = 0
            for r in rows:
                p = match_personel(r, personel_list)
                if p:
                    r["PersonelID"]     = str(p["KimlikNo"]).strip()
                    r["AdSoyad"]        = str(p["AdSoyad"]).strip()
                    r["_eslesti"]       = True
                    r["_eslesti_label"] = "✔ Eşleşti"
                    eslesen += 1
                else:
                    r["_eslesti"]       = False
                    r["_eslesti_label"] = "? Bulunamadı"
                    eslesmez += 1
            self.finished.emit(header, rows, eslesen, eslesmez)
        except Exception as exc:
            self.error.emit(str(exc))

class _DbSaver(QThread):
    finished = _Signal(int, int)
    error    = _Signal(str)

    def __init__(self, db, header: dict, rows: list[dict]):
        super().__init__()
        self._db = db; self._header = header; self._rows = rows

    @staticmethod
    def _db_path(db) -> str:
        if isinstance(db, str):
            return db
        for attr in ("db_path", "_db_path", "path", "_path"):
            val = getattr(db, attr, None)
            if val and isinstance(val, str):
                return val
        return str(db)

    def run(self):
        try:
            conn = sqlite3.connect(self._db_path(self._db), check_same_thread=False)
            rno = self._header.get("RaporNo", "")
            yeni = atlanan = 0
            for r in self._rows:
                try:
                    conn.execute("""
                        INSERT INTO Dozimetre_Olcum
                            (KayitNo,RaporNo,Periyot,PeriyotAdi,Yil,
                             DozimetriTipi,AdSoyad,PersonelID,CalistiBirim,
                             DozimetreNo,VucutBolgesi,Hp10,Hp007,Durum)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (uuid.uuid4().hex[:12].upper(), rno,
                         self._header.get("Periyot"), self._header.get("PeriyotAdi",""),
                         self._header.get("Yil"), self._header.get("DozimetriTipi",""),
                         r["AdSoyad"], r.get("PersonelID",""), r["CalistiBirim"],
                         r["DozimetreNo"], r["VucutBolgesi"],
                         r["Hp10"], r["Hp007"], r["Durum"]))
                    yeni += 1
                except sqlite3.IntegrityError:
                    atlanan += 1
            conn.commit(); conn.close()
            self.finished.emit(yeni, atlanan)
        except Exception as exc:
            self.error.emit(str(exc))

# ─── Model ──────────────────────────────────────────────────────
class _PreviewModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"Hp10","Hp007","_eslesti_label"})
    def _fg(self, key: str, row: dict):
        if key == "_eslesti_label":
            return QColor("#4ade80") if row.get("_eslesti") else QColor("#facc15")
        if key == "PersonelID":
            pid = str(row.get("PersonelID",""))
            return QColor("#4ade80") if pid.isdigit() else QColor("#facc15")
        if key == "Durum" and "Aşım" in str(row.get("Durum","")):
            return QColor("#f87171")
        return None
    def _display(self, key: str, row: dict) -> str:
        val = row.get(key,"")
        if val is None: return ""
        if key in ("Hp10","Hp007"):
            return f"{val:.3f}" if isinstance(val, float) else str(val)
        return str(val)

# ─── Sayfa ──────────────────────────────────────────────────────
class DozimetreImportPage(QWidget):
    def __init__(self, db: str = "", parent=None):
        super().__init__(parent)
        self._db = db
        self._header: dict = {}
        self._rows:   list[dict] = []
        self._loader: Optional[_PdfLoader] = None
        self._saver:  Optional[_DbSaver]   = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24,20,24,20)
        root.setSpacing(16)

        lbl = QLabel("Dozimetre Raporu İçe Aktar")
        lbl.setStyleSheet(f"font-size:18px;font-weight:700;color:{DarkTheme.TEXT_PRIMARY};")
        root.addWidget(lbl)

        self._info_card = self._make_info_card()
        root.addWidget(self._info_card)

        file_row = QHBoxLayout(); file_row.setSpacing(8)
        self.lbl_path = QLabel("Henüz dosya seçilmedi")
        self.lbl_path.setStyleSheet(f"""
            background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};
            border-radius:6px;padding:6px 12px;color:{DarkTheme.TEXT_MUTED};font-size:12px;""")
        self.lbl_path.setMinimumWidth(300)
        self.btn_sec = QPushButton("📂  PDF Seç")
        self.btn_sec.setStyleSheet(str(S.get("btn_default","") or ""))
        self.btn_sec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sec.clicked.connect(self._pick_file)
        file_row.addWidget(self.lbl_path,1); file_row.addWidget(self.btn_sec)
        root.addLayout(file_row)

        self.progress = QProgressBar()
        self.progress.setRange(0,0); self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar{{background:{DarkTheme.BG_TERTIARY};border-radius:2px;border:none;}}
            QProgressBar::chunk{{background:{DarkTheme.ACCENT};border-radius:2px;}}""")
        self.progress.hide()
        root.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-size:12px;")
        root.addWidget(self.lbl_status)

        self.table = QTableView()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableView{{background:{DarkTheme.BG_SECONDARY};
                alternate-background-color:{DarkTheme.BG_TERTIARY};
                border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:8px;
                gridline-color:{DarkTheme.BORDER_PRIMARY};font-size:12px;color:{DarkTheme.TEXT_PRIMARY};}}
            QTableView::item:selected{{background:{DarkTheme.ACCENT};color:#ffffff;}}
            QHeaderView::section{{background:{DarkTheme.BG_TERTIARY};color:{DarkTheme.TEXT_MUTED};
                font-size:11px;font-weight:600;padding:6px;border:none;
                border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};}}""")
        self._model = _PreviewModel(PREVIEW_COLS)
        self.table.setModel(self._model)
        self._model.setup_columns(self.table, stretch_keys=["AdSoyad"])
        root.addWidget(self.table, 1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8); btn_row.addStretch()
        self.btn_temizle = QPushButton("Temizle")
        self.btn_temizle.setStyleSheet(str(S.get("btn_default","") or ""))
        self.btn_temizle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_temizle.clicked.connect(self._clear)
        self.btn_temizle.setEnabled(False)
        self.btn_kaydet = QPushButton("💾  Veritabanına Kaydet")
        self.btn_kaydet.setStyleSheet(str(S.get("btn_action","") or ""))
        self.btn_kaydet.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kaydet.clicked.connect(self._save)
        self.btn_kaydet.setEnabled(False)
        btn_row.addWidget(self.btn_temizle); btn_row.addWidget(self.btn_kaydet)
        root.addLayout(btn_row)

    def _make_info_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""QFrame{{background:{DarkTheme.BG_SECONDARY};
            border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:8px;}}""")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16,12,16,12); lay.setSpacing(32)
        def _lbl(t):
            w = QLabel(self._rich(t,"—"))
            w.setTextFormat(Qt.TextFormat.RichText)
            return w
        self._i_rapor   = _lbl("Rapor No")
        self._i_periyot = _lbl("Periyot")
        self._i_yil     = _lbl("Yıl")
        self._i_tip     = _lbl("Tip")
        self._i_adet    = _lbl("Toplam")
        self._i_eslesen = _lbl("Eşleşen")
        self._i_eksik   = _lbl("Eşleşmeyen")
        for w in (self._i_rapor,self._i_periyot,self._i_yil,
                  self._i_tip,self._i_adet,self._i_eslesen,self._i_eksik):
            lay.addWidget(w)
        lay.addStretch()
        return card

    def _rich(self, title: str, value: str, color: str = "") -> str:
        c = color or DarkTheme.TEXT_PRIMARY
        return (f"<span style='color:{DarkTheme.TEXT_MUTED};font-size:10px;'>{title}</span><br>"
                f"<span style='color:{c};font-size:13px;font-weight:600;'>{value}</span>")

    def _update_info_card(self, eslesen: int = 0, eslesmez: int = 0):
        h = self._header
        periyot = f"{h.get('Periyot','')} ({h.get('PeriyotAdi','')})" if h.get("Periyot") else "—"
        self._i_rapor.setText(self._rich("Rapor No",   h.get("RaporNo","—")))
        self._i_periyot.setText(self._rich("Periyot",  periyot))
        self._i_yil.setText(self._rich("Yıl",          str(h.get("Yil","—"))))
        self._i_tip.setText(self._rich("Tip",           h.get("DozimetriTipi","—")))
        self._i_adet.setText(self._rich("Toplam",       str(len(self._rows)), DarkTheme.ACCENT))
        self._i_eslesen.setText(self._rich("Eşleşen",   str(eslesen),  "#4ade80"))
        eksik_renk = "#facc15" if eslesmez else "#4ade80"
        self._i_eksik.setText(self._rich("Eşleşmeyen",  str(eslesmez), eksik_renk))

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,"RADAT PDF Seç","","PDF Dosyaları (*.pdf);;Tüm Dosyalar (*)")
        if not path: return
        self.lbl_path.setText(path)
        self._load_pdf(path)

    def _load_pdf(self, path: str):
        if self._loader and self._loader.isRunning(): return
        self.btn_sec.setEnabled(False)
        self.btn_kaydet.setEnabled(False)
        self.btn_temizle.setEnabled(False)
        self.progress.show()
        self.lbl_status.setText("PDF okunuyor ve personel eşleştiriliyor...")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-size:12px;")
        self._loader = _PdfLoader(path, self._db)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, header: dict, rows: list, eslesen: int, eslesmez: int):
        self.progress.hide()
        self.btn_sec.setEnabled(True)
        self.btn_temizle.setEnabled(True)
        self._header = header
        self._rows   = rows
        self._update_info_card(eslesen, eslesmez)
        self._model.set_data(rows)
        self.lbl_status.setText(
            f"✔  {len(rows)} satır okundu — {eslesen} personel eşleşti, {eslesmez} eşleşmedi.")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_SUCCESS};font-size:12px;")
        if rows: self.btn_kaydet.setEnabled(True)

    def _on_load_error(self, msg: str):
        self.progress.hide()
        self.btn_sec.setEnabled(True)
        logger.error(f"Dozimetre PDF okuma hatası: {msg}")
        self.lbl_status.setText(f"✗  Okuma hatası: {msg}")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_ERROR};font-size:12px;")

    def _save(self):
        if not self._rows or not self._db: return
        rapor_no = self._header.get("RaporNo", "")

        mevcut_sayisi: int = 0
        try:
            db_path: str = _DbSaver._db_path(self._db)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM Dozimetre_Olcum WHERE RaporNo=?",
                    (rapor_no,)
                ).fetchone()
                mevcut_sayisi = row[0] if row else 0
            except sqlite3.OperationalError:
                pass
            conn.close()
        except Exception:
            pass

        if mevcut_sayisi > 0:
            if mevcut_sayisi >= len(self._rows):
                QMessageBox.information(
                    self, "Zaten Kayıtlı",
                    f"<b>{rapor_no}</b> raporunun tüm kayıtları "
                    f"zaten veritabanında mevcut.<br>Herhangi bir ekleme yapılmadı."
                )
                return
            cevap = QMessageBox.question(
                self, "Mükerrer Kayıt Uyarısı",
                f"<b>{rapor_no}</b> raporu için:<br><br>"
                f"&nbsp;&nbsp;• <b>{len(self._rows) - mevcut_sayisi}</b> yeni kayıt eklenecek<br>"
                f"&nbsp;&nbsp;• <b>{mevcut_sayisi}</b> kayıt zaten mevcut<br><br>"
                f"Devam edilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
        else:
            cevap = QMessageBox.question(
                self, "Kaydet",
                f"{len(self._rows)} kayıt veritabanına eklenecek. Devam edilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
        if cevap != QMessageBox.StandardButton.Yes: return

        self.btn_kaydet.setEnabled(False)
        self.btn_temizle.setEnabled(False)
        self.btn_sec.setEnabled(False)
        self.progress.show()
        self.lbl_status.setText("Kaydediliyor...")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-size:12px;")
        self._saver = _DbSaver(self._db, self._header, self._rows)
        self._saver.finished.connect(self._on_save_finished)
        self._saver.error.connect(self._on_save_error)
        self._saver.start()

    def _on_save_finished(self, yeni: int, atlanan: int):
        self.progress.hide()
        self.btn_sec.setEnabled(True)
        self.btn_temizle.setEnabled(True)
        msg = f"✅  {yeni} kayıt eklendi."
        if atlanan: msg += f"  {atlanan} mükerrer atlandı."
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_SUCCESS};font-size:12px;")
        detail = f"{yeni} yeni kayıt veritabanına eklendi."
        if atlanan: detail += f"\n{atlanan} kayıt zaten mevcuttu, atlandı."
        QMessageBox.information(self,"Başarılı", detail)

    def _on_save_error(self, msg: str):
        self.progress.hide()
        self.btn_sec.setEnabled(True); self.btn_temizle.setEnabled(True)
        self.btn_kaydet.setEnabled(True)
        logger.error(f"Dozimetre kaydetme hatası: {msg}")
        self.lbl_status.setText(f"✗  Kaydetme hatası: {msg}")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_ERROR};font-size:12px;")
        QMessageBox.critical(self,"Hata",f"Kayıt sırasında hata oluştu:\n{msg}")

    def _clear(self):
        self._header = {}; self._rows = []
        self._model.set_data([])
        self.lbl_path.setText("Henüz dosya seçilmedi")
        self.lbl_status.setText("")
        self.btn_kaydet.setEnabled(False)
        self.btn_temizle.setEnabled(False)
        self._update_info_card()

    def set_db(self, db: str):
        self._db = db
