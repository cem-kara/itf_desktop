# -*- coding: utf-8 -*-
"""
dokuman_listesi.py
──────────────────
Dokumanlar tablosunun tamamını gösteren merkezi arama/listeleme sayfası.

Mevcut altyapıyı (DokumanService, BaseDokumanPanel) bozmadan çalışır.

Kullanım
--------
from ui.pages.dokuman_listesi import DokumanListesiPage
    page = DokumanListesiPage(db=self._db)
"""
from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QThread,QUrl, Signal as _Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableView, QHeaderView, QLineEdit,
    QComboBox, QAbstractItemView, QMessageBox, 
    QDateEdit, QCheckBox,
)
from PySide6.QtCore import QDate

from core.logger import logger
from ui.components.base_table_model import BaseTableModel
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S

# ─────────────────────────────────────────────────────────────
# Sütun tanımları
# ─────────────────────────────────────────────────────────────
COLS = [
    ("EntityType",       "Tür",         80),
    ("EntityId",         "ID / TC",     110),
    ("DisplayName",      "Dosya Adı",   220),
    ("BelgeTuru",        "Belge Türü",  130),
    ("BelgeAciklama",    "Açıklama",    180),
    ("YuklenmeTarihi",   "Yüklenme",     95),
    ("_konum",           "Konum",        65),
]

ENTITY_LABELS = {
    "personel":   "Personel",
    "cihaz":      "Cihaz",
    "rke":        "RKE",
    "satin_alma": "Satın Alma",
    "kurumsal":   "Kurumsal",
}


# ─────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────
class _DokumanModel(BaseTableModel):
    ALIGN_CENTER = frozenset({"EntityType", "YuklenmeTarihi", "_konum"})

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key, "")
        if val is None:
            return ""
        if key == "YuklenmeTarihi":
            try:
                return datetime.fromisoformat(str(val)).strftime("%d.%m.%Y")
            except Exception:
                return str(val)[:10]
        if key == "EntityType":
            return ENTITY_LABELS.get(str(val).lower(), str(val))
        if key == "_konum":
            return "☁ Drive" if row.get("DrivePath") else "💾 Yerel"
        if key == "DisplayName":
            return str(val) or str(row.get("Belge", ""))
        return str(val)

    def _fg(self, key: str, row: dict):
        if key == "_konum":
            return QColor("#60a5fa") if row.get("DrivePath") else QColor("muted")
        if key == "DisplayName":
            return QColor("accent")
        return None


# ─────────────────────────────────────────────────────────────
# Worker
# ─────────────────────────────────────────────────────────────
class _Loader(QThread):
    finished = _Signal(list)
    error    = _Signal(str)

    def __init__(self, db):
        super().__init__()
        self._db = db

    def run(self):
        try:
            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            from core.paths import DB_PATH

            db_path: str = getattr(self._db, "db_path", None) or str(self._db) if self._db else DB_PATH
            db = SQLiteManager(db_path=db_path, check_same_thread=False)
            try:
                repo = get_registry(db).get("Dokumanlar")
                rows = repo.get_all() or []
                # Yükleme tarihi DESC sırala
                rows.sort(
                    key=lambda r: str(r.get("YuklenmeTarihi") or ""),
                    reverse=True,
                )
            except Exception:
                rows = []
            db.close()
            self.finished.emit(rows)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────
# Sayfa
# ─────────────────────────────────────────────────────────────
class DokumanListesiPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db      = db
        self._rows:   list[dict] = []
        self._filter: list[dict] = []
        self._loader: Optional[_Loader] = None
        self._build_ui()
        if db:
            self.load_data()

    # ─── UI ─────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(14)

        # Başlık
        top = QHBoxLayout()
        lbl = QLabel("Doküman Yönetimi")
        lbl.setProperty("color-role", "primary")
        self.btn_yenile = QPushButton("⟳  Yenile")
        self.btn_yenile.setStyleSheet(str(S.get("refresh_btn", "") or ""))
        self.btn_yenile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_yenile.clicked.connect(self.load_data)
        top.addWidget(lbl)
        top.addStretch()
        top.addWidget(self.btn_yenile)
        root.addLayout(top)

        # Özet kartlar
        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        self._s_toplam    = self._stat("Toplam Belge",  "—", "accent")
        self._s_personel  = self._stat("Personel",       "—", "#60a5fa")
        self._s_cihaz     = self._stat("Cihaz",          "—", "#a78bfa")
        self._s_rke       = self._stat("RKE",            "—", "#f472b6")
        self._s_satin     = self._stat("Satın Alma",     "—", "#fb923c")
        self._s_kurumsal  = self._stat("Kurumsal",       "—", "#94a3b8")
        self._s_drive     = self._stat("Drive'da",       "—", "#34d399")
        for w in (self._s_toplam, self._s_personel, self._s_cihaz,
                  self._s_rke, self._s_satin, self._s_kurumsal, self._s_drive):
            stat_row.addWidget(w)
        root.addLayout(stat_row)

        # Filtre çubuğu
        ff = QFrame()
        ff.setStyleSheet(str(S.get("filter_panel", "") or ""))
        fb = QHBoxLayout(ff)
        fb.setContentsMargins(12, 8, 12, 8)
        fb.setSpacing(8)

        self.cmb_tur    = self._cmb("Tür")
        self.cmb_belge  = self._cmb("Belge Türü")
        self.inp_arama  = QLineEdit()
        self.inp_arama.setPlaceholderText("Dosya adı / ID / açıklama ara...")
        self.inp_arama.setStyleSheet(str(S.get("search", "") or ""))
        self.inp_arama.setMinimumWidth(220)

        self.chk_drive = QCheckBox("Sadece Drive")
        self.chk_drive.setProperty("color-role", "primary")

        self.lbl_sonuc = QLabel("— belge")
        self.lbl_sonuc.setProperty("color-role", "primary")

        for lbl_t, w in (("Tür", self.cmb_tur), ("Belge Türü", self.cmb_belge)):
            fb.addWidget(QLabel(lbl_t))
            fb.addWidget(w)
        fb.addWidget(self.inp_arama)
        fb.addWidget(self.chk_drive)
        fb.addStretch()
        fb.addWidget(self.lbl_sonuc)
        root.addWidget(ff)

        # Tablo
        self.table = QTableView()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(str(S.get("table", "") or ""))
        self.table.doubleClicked.connect(self._ac)
        self._model = _DokumanModel(COLS)
        self.table.setModel(self._model)
        self._model.setup_columns(self.table, stretch_keys=["DisplayName", "BelgeAciklama"])
        root.addWidget(self.table, 1)

        # Alt çubuk
        bot = QHBoxLayout()
        self.btn_ac = QPushButton("📂  Dosyayı Aç")
        self.btn_ac.setStyleSheet(str(S.get("btn_default", "") or ""))
        self.btn_ac.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ac.clicked.connect(self._ac_secili)
        self.btn_ac.setEnabled(False)

        self.btn_sil = QPushButton("🗑  Kaydı Sil")
        self.btn_sil.setStyleSheet(str(S.get("close_btn", S.get("btn_danger", "")) or ""))
        self.btn_sil.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sil.clicked.connect(self._sil)
        self.btn_sil.setEnabled(False)

        self.lbl_footer = QLabel("")
        self.lbl_footer.setStyleSheet(str(S.get("footer_label", "") or ""))
        bot.addWidget(self.lbl_footer)
        bot.addStretch()
        bot.addWidget(self.btn_ac)
        bot.addWidget(self.btn_sil)
        root.addLayout(bot)

        # Bağlantılar
        self.cmb_tur.currentIndexChanged.connect(self._apply_filter)
        self.cmb_belge.currentIndexChanged.connect(self._apply_filter)
        self.inp_arama.textChanged.connect(self._apply_filter)
        self.chk_drive.stateChanged.connect(self._apply_filter)
        self.table.selectionModel().selectionChanged.connect(self._on_select)

    def _cmb(self, ph: str) -> QComboBox:
        c = QComboBox()
        c.setStyleSheet(str(S.get("combo_filter", "") or ""))
        c.addItem(f"Tümü ({ph})")
        c.setMinimumWidth(140)
        return c

    def _stat(self, title: str, value: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{background:{"panel"};
                    border:1px solid {"primary"};
                    border-left:3px solid {color};border-radius:6px;}}
        """)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setProperty("color-role", "primary")
        v = QLabel(value)
        v.setProperty("color-role", "primary")
        v.setObjectName("val")
        lay.addWidget(t); lay.addWidget(v)
        return f

    @staticmethod
    def _set_stat(card: QFrame, val: str):
        lbl = card.findChild(QLabel, "val")
        if lbl:
            lbl.setText(val)

    # ─── Veri ───────────────────────────────────────────────
    def load_data(self):
        if self._loader and self._loader.isRunning():
            return
        self.btn_yenile.setEnabled(False)
        self.lbl_footer.setText("Yükleniyor...")
        self._loader = _Loader(self._db)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_finished(self, rows: list):
        self.btn_yenile.setEnabled(True)
        self._rows = rows
        self._fill_combos()
        self._apply_filter()
        self._update_stats()
        self.lbl_footer.setText(f"{len(rows)} belge kaydı yüklendi.")

    def _on_load_error(self, msg: str):
        self.btn_yenile.setEnabled(True)
        logger.error(f"DokumanListesi yükleme hatası: {msg}")
        self.lbl_footer.setText(f"Hata: {msg}")

    def _fill_combos(self):
        def _fill(cmb, key, label, transform=None):
            vals = sorted({
                (transform(str(r.get(key, ""))) if transform else str(r.get(key, "")))
                for r in self._rows if r.get(key)
            })
            cmb.blockSignals(True)
            cur = cmb.currentText()
            cmb.clear()
            cmb.addItem(f"Tümü ({label})")
            for v in vals:
                cmb.addItem(v)
            idx = cmb.findText(cur)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        _fill(self.cmb_tur,   "EntityType", "Tür",
              transform=lambda x: ENTITY_LABELS.get(x.lower(), x))
        _fill(self.cmb_belge, "BelgeTuru",  "Belge Türü")

    def _apply_filter(self):
        tur_sec   = self.cmb_tur.currentText()
        belge_sec = self.cmb_belge.currentText()
        arama     = self.inp_arama.text().strip().lower()
        sadece_drive = self.chk_drive.isChecked()

        def _ok(r):
            if "Tümü" not in tur_sec:
                et = ENTITY_LABELS.get(str(r.get("EntityType", "")).lower(),
                                       str(r.get("EntityType", "")))
                if et != tur_sec:
                    return False
            if "Tümü" not in belge_sec and str(r.get("BelgeTuru", "")) != belge_sec:
                return False
            if sadece_drive and not r.get("DrivePath"):
                return False
            if arama:
                haystack = " ".join([
                    str(r.get("DisplayName", "")),
                    str(r.get("Belge", "")),
                    str(r.get("EntityId", "")),
                    str(r.get("BelgeAciklama", "")),
                ]).lower()
                if arama not in haystack:
                    return False
            return True

        self._filter = [r for r in self._rows if _ok(r)]
        self._model.set_data(self._filter)
        self.lbl_sonuc.setText(f"{len(self._filter)} belge")

    def _update_stats(self):
        rows = self._rows
        et = lambda r, v: r.get("EntityType","").lower() == v
        self._set_stat(self._s_toplam,   str(len(rows)))
        self._set_stat(self._s_personel, str(sum(1 for r in rows if et(r,"personel"))))
        self._set_stat(self._s_cihaz,    str(sum(1 for r in rows if et(r,"cihaz"))))
        self._set_stat(self._s_rke,      str(sum(1 for r in rows if et(r,"rke"))))
        self._set_stat(self._s_satin,    str(sum(1 for r in rows if et(r,"satin_alma"))))
        self._set_stat(self._s_kurumsal, str(sum(1 for r in rows if et(r,"kurumsal"))))
        self._set_stat(self._s_drive,    str(sum(1 for r in rows if r.get("DrivePath"))))

    # ─── Seçim & Aksiyonlar ─────────────────────────────────
    def _on_select(self, *_):
        has = bool(self.table.selectionModel().selectedRows())
        self.btn_ac.setEnabled(has)
        self.btn_sil.setEnabled(has)

    def _secili_row(self) -> Optional[dict]:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return None
        return self._model.get_row(idxs[0].row())

    def _ac(self, index=None):
        """Çift tıklama veya buton ile dosyayı aç."""
        row = self._secili_row()
        if not row:
            return
        drive = str(row.get("DrivePath", "")).strip()
        local = str(row.get("LocalPath", "")).strip()
        try:
            if drive:
                QDesktopServices.openUrl(QUrl(drive))
                return
            if not local or not os.path.exists(local):
                QMessageBox.warning(self, "Bulunamadı",
                    f"Dosya bulunamadı:\n{local}\n\nDosya silinmiş veya taşınmış olabilir.")
                return
            if platform.system() == "Windows":
                os.startfile(local)
            elif platform.system() == "Darwin":
                subprocess.run(["open", local])
            else:
                subprocess.run(["xdg-open", local])
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı:\n{e}")

    def _ac_secili(self):
        self._ac()

    def _sil(self):
        row = self._secili_row()
        if not row:
            return
        dosya = row.get("DisplayName") or row.get("Belge", "")
        cevap = QMessageBox.question(
            self, "Kaydı Sil",
            f"<b>{dosya}</b> belgesinin veritabanı kaydı silinecek.<br><br>"
            f"Dosyanın kendisi silinmez, sadece kayıt kaldırılır.<br>Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("Dokumanlar")
            pk = {
                "EntityType": row.get("EntityType"),
                "EntityId":   row.get("EntityId"),
                "BelgeTuru":  row.get("BelgeTuru"),
                "Belge":      row.get("Belge"),
            }
            repo.delete(pk)
            self.load_data()
            self.lbl_footer.setText(f"'{dosya}' kaydı silindi.")
        except Exception as e:
            logger.error(f"Doküman silme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Silme başarısız:\n{e}")

    def set_db(self, db):
        self._db = db
        self.load_data()
