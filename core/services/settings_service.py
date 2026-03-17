"""
SettingsService — Sabitler ve Tatiller Yönetimi
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.hata_yonetici import SonucYonetici, logger


class SettingsService:

    def __init__(self, db):
        self._db = db

    # ══════════════════ SABİTLER ══════════════════

    def get_sabitler(self) -> SonucYonetici:
        try:
            cur = self._db.execute(
                "SELECT Rowid, Kod, MenuEleman, Aciklama FROM Sabitler ORDER BY MenuEleman"
            )
            rows = [dict(r) for r in cur.fetchall()] if cur else []
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.get_sabitler")

    def add_sabit(self, kod: str, menu_eleman: str, aciklama: str) -> SonucYonetici:
        try:
            if not kod or not menu_eleman:
                return SonucYonetici.hata(
                    Exception("Kod ve Menü Elemanı zorunludur"),
                    "SettingsService.add_sabit"
                )
            # Rowid: sbt001, sbt002 ... şeklinde üret
            rowid = self._next_sabit_rowid()
            self._db.execute(
                "INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama, sync_status, updated_at) "
                "VALUES (?, ?, ?, ?, 'dirty', ?)",
                (rowid, kod, menu_eleman, aciklama or "", datetime.now().isoformat())
            )
            logger.info(f"Sabit eklendi: {menu_eleman} ({kod})")
            return SonucYonetici.tamam(
                f"Sabit başarıyla eklendi: {menu_eleman}",
                veri={"rowid": rowid}
            )
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.add_sabit")

    def _next_sabit_rowid(self) -> str:
        """sbt001, sbt002 ... formatında bir Rowid üret."""
        try:
            cur = self._db.execute(
                "SELECT Rowid FROM Sabitler WHERE Rowid LIKE 'sbt%' ORDER BY Rowid DESC LIMIT 1"
            )
            row = cur.fetchone() if cur else None
            if row:
                last = str(row[0] if not isinstance(row, dict) else row.get("Rowid", ""))
                num = int(last.replace("sbt", "")) if last.startswith("sbt") else 0
            else:
                num = 0
        except Exception:
            num = 0
        return f"sbt{num + 1:03d}"

    def update_sabit(self, rowid: str, kod: str, menu_eleman: str, aciklama: str) -> SonucYonetici:
        try:
            if not kod or not menu_eleman:
                return SonucYonetici.hata(
                    Exception("Kod ve Menü Elemanı zorunludur"),
                    "SettingsService.update_sabit"
                )
            self._db.execute(
                "UPDATE Sabitler SET Kod=?, MenuEleman=?, Aciklama=?, "
                "sync_status='dirty', updated_at=? WHERE Rowid=?",
                (kod, menu_eleman, aciklama or "", datetime.now().isoformat(), rowid)
            )
            logger.info(f"Sabit güncellendi: {rowid}")
            return SonucYonetici.tamam("Sabit başarıyla güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.update_sabit")

    def delete_sabit(self, rowid: str) -> SonucYonetici:
        try:
            self._db.execute("DELETE FROM Sabitler WHERE Rowid=?", (rowid,))
            logger.info(f"Sabit silindi: {rowid}")
            return SonucYonetici.tamam("Sabit başarıyla silindi.")
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.delete_sabit")

    # ══════════════════ TATİLLER ══════════════════

    def get_tatiller(self) -> SonucYonetici:
        try:
            cur = self._db.execute(
                "SELECT Tarih, ResmiTatil FROM Tatiller ORDER BY Tarih"
            )
            rows = [dict(r) for r in cur.fetchall()] if cur else []
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.get_tatiller")

    def add_tatil(self, tarih: str, resmi_tatil: str) -> SonucYonetici:
        try:
            if not tarih or not resmi_tatil:
                return SonucYonetici.hata(
                    Exception("Tarih ve Tatil Adı zorunludur"),
                    "SettingsService.add_tatil"
                )
            try:
                datetime.strptime(tarih, "%Y-%m-%d")
            except ValueError:
                return SonucYonetici.hata(
                    Exception("Geçersiz tarih formatı (YYYY-MM-DD)"),
                    "SettingsService.add_tatil"
                )
            cur = self._db.execute(
                "SELECT 1 FROM Tatiller WHERE Tarih=?", (tarih,)
            )
            if cur and cur.fetchone():
                return SonucYonetici.hata(
                    Exception(f"Bu tarih zaten tatil olarak kaydedilmiş: {tarih}"),
                    "SettingsService.add_tatil"
                )
            self._db.execute(
                "INSERT INTO Tatiller (Tarih, ResmiTatil, sync_status, updated_at) "
                "VALUES (?, ?, 'dirty', ?)",
                (tarih, resmi_tatil, datetime.now().isoformat())
            )
            logger.info(f"Tatil eklendi: {tarih} ({resmi_tatil})")
            return SonucYonetici.tamam(f"Tatil başarıyla eklendi: {resmi_tatil}")
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.add_tatil")

    def update_tatil(self, tarih: str, resmi_tatil: str) -> SonucYonetici:
        try:
            if not tarih or not resmi_tatil:
                return SonucYonetici.hata(
                    Exception("Tarih ve Tatil Adı zorunludur"),
                    "SettingsService.update_tatil"
                )
            self._db.execute(
                "UPDATE Tatiller SET ResmiTatil=?, sync_status='dirty', updated_at=? "
                "WHERE Tarih=?",
                (resmi_tatil, datetime.now().isoformat(), tarih)
            )
            logger.info(f"Tatil güncellendi: {tarih}")
            return SonucYonetici.tamam("Tatil başarıyla güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.update_tatil")

    def delete_tatil(self, tarih: str) -> SonucYonetici:
        try:
            self._db.execute("DELETE FROM Tatiller WHERE Tarih=?", (tarih,))
            logger.info(f"Tatil silindi: {tarih}")
            return SonucYonetici.tamam("Tatil başarıyla silindi.")
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.delete_tatil")
