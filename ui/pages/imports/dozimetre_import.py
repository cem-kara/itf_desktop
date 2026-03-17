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
from ui.styles.icons import Icons

PREVIEW_COLS = [
    ("SiraNo",         "No",         48),
    ("AdSoyad",        "Ad Soyad",  200),
    ("TCKimlikNo",     "TC Kimlik", 120),
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

def _match_name(pdf_name: str, real_name: str) -> bool:
    pdf_parts  = pdf_name.upper().split()
    real_parts = real_name.upper().split()
    if not pdf_parts or not real_parts:
        return False
    matched = 0
    for pp in pdf_parts:
        visible = pp.rstrip("*")
        if not visible:
            continue
        for rp in real_parts:
            if rp.startswith(visible):
                matched += 1
                break
    return matched >= max(1, len(pdf_parts) - 1)

def match_personel(row: dict, personel_list: list[dict]) -> Optional[dict]:
    tc_masked = row.get("TCKimlikNo", "")
    pdf_name  = row.get("AdSoyad", "")
    candidates = [p for p in personel_list
                  if _match_tc(tc_masked, str(p.get("KimlikNo", "")))]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    name_ok = [p for p in candidates if _match_name(pdf_name, str(p.get("AdSoyad", "")))]
    return name_ok[0] if name_ok else candidates[0]

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

def _smart_parse_row(row: list) -> dict:
    birim = vucut = dzm_no = durum = ""
    hp10 = hp007 = None
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
        "SiraNo":       int(str(row[0]).strip()),
        "AdSoyad":      str(row[1] or "").strip().replace("\n"," "),
        "TCKimlikNo":   str(row[2] or "").strip(),
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
            if idx == 0:
                m = re.search(r"\b(\d{9})\b", text)
                if m: header["RaporNo"] = m.group(1)
                m = re.search(r"Periyot\s*/\s*Yıl\s*[:\s]+(\d+)\s*\(([^)]+)\)\s*/\s*(\d{4})", text)
                if m:
                    header["Periyot"] = int(m.group(1))
                    header["PeriyotAdi"] = m.group(2).strip()
                    header["Yil"] = int(m.group(3))
                m = re.search(r"Dozimetre\s+Tipi\s*[:\s]+(\w+)", text)
                if m: header["DozimetriTipi"] = m.group(1)
            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0]: continue
                    if not str(row[0]).strip().isdigit(): continue
                    all_rows.append(_smart_parse_row(row))
    seen: set[int] = set()
    unique: list[dict] = []
    for r in sorted(all_rows, key=lambda x: x["SiraNo"]):
        if r["SiraNo"] not in seen:
            seen.add(r["SiraNo"])
            unique.append(r)
    return header, unique

# ─── Workers ────────────────────────────────────────────────────
class _PdfLoader(QThread):
    finished = _Signal(dict, list, int, int)
    error    = _Signal(str)
    def __init__(self, pdf_path: str, db: str):
        super().__init__()
        self._path = pdf_path
        self._db   = db
    def run(self):
        try:
            header, rows = parse_radat_pdf(self._path)
            personel_list: list[dict] = []
            if self._db:
                try:
                    conn = sqlite3.connect(self._db)
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
                    r["TCKimlikNo"]     = str(p["KimlikNo"]).strip()
                    r["_eslesti"]       = True
                    r["_eslesti_label"] = "[icon:check] Eşleşti"
                    eslesen += 1
                else:
                    r["PersonelID"]     = ""
                    r["_eslesti"]       = False
                    r["_eslesti_label"] = "? Bulunamadı"
                    eslesmez += 1
            self.finished.emit(header, rows, eslesen, eslesmez)
        except Exception as exc:
            self.error.emit(str(exc))

class _DbSaver(QThread):
    finished = _Signal(int, int)   # yeni, atlanan
    error    = _Signal(str)
    def __init__(self, db: str, header: dict, rows: list[dict]):
        super().__init__()
        self._db = db; self._header = header; self._rows = rows
    def run(self):
        try:
            conn = sqlite3.connect(self._db)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
                    KayitNo TEXT PRIMARY KEY, SiraNo INTEGER,
                    RaporNo TEXT, Periyot INTEGER, PeriyotAdi TEXT,
                    Yil INTEGER, DozimetriTipi TEXT,
                    AdSoyad TEXT, TCKimlikNo TEXT, CalistiBirim TEXT,
                    PersonelID TEXT, DozimetreNo TEXT, VucutBolgesi TEXT,
                    Hp10 REAL, Hp007 REAL,
                    DozSiniri_Hp10 REAL, DozSiniri_Hp007 REAL,
                    Durum TEXT,
                    OlusturmaTarihi TEXT DEFAULT (date('now')),
                    UNIQUE(RaporNo, SiraNo)
                )""")
            conn.commit()
            rno = self._header.get("RaporNo", "")
            yeni = atlanan = 0
            for r in self._rows:
                try:
                    conn.execute("""
                        INSERT INTO Dozimetre_Olcum
                            (KayitNo,SiraNo,RaporNo,Periyot,PeriyotAdi,Yil,
                             DozimetriTipi,AdSoyad,TCKimlikNo,CalistiBirim,
                             PersonelID,DozimetreNo,VucutBolgesi,Hp10,Hp007,Durum)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (uuid.uuid4().hex[:12].upper(), r["SiraNo"], rno,
                         self._header.get("Periyot"), self._header.get("PeriyotAdi",""),
                         self._header.get("Yil"), self._header.get("DozimetriTipi",""),
                         r["AdSoyad"], r["TCKimlikNo"], r["CalistiBirim"],
                         r.get("PersonelID",""), r["DozimetreNo"], r["VucutBolgesi"],
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
    ALIGN_CENTER = frozenset({"SiraNo","Hp10","Hp007","_eslesti_label"})
    def _fg(self, key: str, row: dict):
        if key == "_eslesti_label":
            return QColor("#4ade80") if row.get("_eslesti") else QColor("#facc15")
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
        icon = Icons.pixmap("check_circle", size=16, color=DarkTheme.STATUS_SUCCESS)
        self.lbl_status.setPixmap(icon)
        self.lbl_status.setText(
            f" {len(rows)} satır okundu — {eslesen} personel eşleşti, {eslesmez} eşleşmedi.")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_SUCCESS};font-size:12px;")
        if rows: self.btn_kaydet.setEnabled(True)

    def _on_load_error(self, msg: str):
        self.progress.hide()
        self.btn_sec.setEnabled(True)
        logger.error(f"Dozimetre PDF okuma hatası: {msg}")
        icon = Icons.pixmap("x_circle", size=16, color=DarkTheme.STATUS_ERROR)
        self.lbl_status.setPixmap(icon)
        self.lbl_status.setText(f" Okuma hatası: {msg}")
        self.lbl_status.setStyleSheet(f"color:{DarkTheme.STATUS_ERROR};font-size:12px;")

    def _save(self):
        if not self._rows or not self._db: return
        rapor_no = self._header.get("RaporNo", "")

        # Tam SiraNo karşılaştırması — COUNT(*) yeterli değil,
        # hangi SiraNo'ların zaten kayıtlı olduğunu buluyoruz.
        mevcut_siralar: set = set()
        try:
            db_path: str = getattr(self._db, "db_path", None) or str(self._db)
            conn = sqlite3.connect(db_path)
            try:
                rows_db = conn.execute(
                    "SELECT SiraNo FROM Dozimetre_Olcum WHERE RaporNo=?",
                    (rapor_no,)
                ).fetchall()
                mevcut_siralar = {r[0] for r in rows_db}
            except sqlite3.OperationalError:
                pass
            conn.close()
        except Exception:
            pass

        pdf_siralar   = {r["SiraNo"] for r in self._rows}
        gercek_yeni   = pdf_siralar - mevcut_siralar
        gercek_mevcut = pdf_siralar & mevcut_siralar

        if gercek_mevcut:
            if not gercek_yeni:
                QMessageBox.information(
                    self, "Zaten Kayıtlı",
                    f"<b>{rapor_no}</b> raporunun tüm {len(gercek_mevcut)} kaydı "
                    f"zaten veritabanında mevcut.<br>Herhangi bir ekleme yapılmadı."
                )
                return
            cevap = QMessageBox.question(
                self, "Mükerrer Kayıt Uyarısı",
                f"<b>{rapor_no}</b> raporu için:<br><br>"
                f"&nbsp;&nbsp;• <b>{len(gercek_yeni)}</b> yeni kayıt eklenecek<br>"
                f"&nbsp;&nbsp;• <b>{len(gercek_mevcut)}</b> kayıt zaten mevcut, atlanacak<br><br>"
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
        icon = Icons.pixmap("x_circle", size=16, color=DarkTheme.STATUS_ERROR)
        self.lbl_status.setPixmap(icon)
        self.lbl_status.setText(f" Kaydetme hatası: {msg}")
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
