# -*- coding: utf-8 -*-
"""
dozimetre_service.py — Dozimetre Ölçüm Servisi

Sadece toplu kayıt (Excel import) için tasarlanmıştır.
PDF import kendi DB bağlantısını doğrudan kullanmaya devam eder.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Sonuç nesnesi  (SonucYonetici uyumlu)
# ---------------------------------------------------------------------------

@dataclass
class _Sonuc:
    basarili: bool
    mesaj: str = ""


# ---------------------------------------------------------------------------
# Servis
# ---------------------------------------------------------------------------

class DozimetreService:
    """
    Dozimetre_Olcum tablosuna kayıt ekler.

    Excel import alanları → DB sütunları eşlemesi:
        TCKimlikNo   → TCKimlikNo
        AdSoyad      → AdSoyad
        Periyot      → Periyot  (PeriyotAdi boş bırakılır)
        Yil          → Yil
        DerinDoz     → Hp10       (RADAT terminolojisiyle uyumlu)
        YuzeyselDoz  → Hp007
        NeutronDoz   → (yok — tablo şemasında kolonu yoksa atlanır)
        ToplamDoz    → (ayrı kolon yoksa atlanır)
        KumulatifDoz → (ayrı kolon yoksa atlanır)
        DozimetreNo  → DozimetreNo
        OkumaTarihi  → OlusturmaTarihi (yoksa None)
        LaboratuvarAdi → (notlar — tablo şemasında yoksa atlanır)
        Aciklama     → Durum alanına ek olarak yazılır
    """

    # CREATE TABLE — PDF import'ta da aynı şema kullanılıyor.
    _DDL = """
        CREATE TABLE IF NOT EXISTS Dozimetre_Olcum (
            KayitNo          TEXT PRIMARY KEY,
            SiraNo           INTEGER,
            RaporNo          TEXT,
            Periyot          INTEGER,
            PeriyotAdi       TEXT,
            Yil              INTEGER,
            DozimetriTipi    TEXT,
            AdSoyad          TEXT,
            TCKimlikNo       TEXT,
            CalistiBirim     TEXT,
            PersonelID       TEXT,
            DozimetreNo      TEXT,
            VucutBolgesi     TEXT,
            Hp10             REAL,
            Hp007            REAL,
            DozSiniri_Hp10   REAL,
            DozSiniri_Hp007  REAL,
            Durum            TEXT,
            OlusturmaTarihi  TEXT DEFAULT (date('now')),
            UNIQUE(RaporNo, SiraNo)
        )
    """

    def __init__(self, db):
        """
        db: sqlite3 bağlantısı veya db_path string'i.
        Projedeki DB yöneticisiyle uyumlu olması için her iki biçimi de kabul eder.
        """
        self._db = db

    # ------------------------------------------------------------------
    # Yardımcı: bağlantı al
    # ------------------------------------------------------------------

    def _baglanti(self):
        """
        db bir sqlite3.Connection ise doğrudan döner.
        db bir string (yol) ise yeni bağlantı açar.
        db'nin .connection veya .conn attribute'u varsa onu kullanır.
        """
        import sqlite3

        if isinstance(self._db, str):
            conn = sqlite3.connect(self._db)
            conn.row_factory = sqlite3.Row
            return conn, True   # (bağlantı, kapat_mi)

        for attr in ("connection", "conn", "_conn", "_connection"):
            if hasattr(self._db, attr):
                return getattr(self._db, attr), False

        # db'nin kendisi bağlantıysa
        return self._db, False

    # ------------------------------------------------------------------
    # Tablo oluştur (gerekirse)
    # ------------------------------------------------------------------

    def tablo_olustur(self):
        conn, kapat = self._baglanti()
        try:
            conn.execute(self._DDL)
            conn.commit()
        finally:
            if kapat:
                conn.close()

    # ------------------------------------------------------------------
    # Tekil kayıt ekle  ← BaseImportPage motoru bu metodu çağırır
    # ------------------------------------------------------------------

    def olcum_ekle(self, kayit: dict) -> _Sonuc:
        """
        Bir Excel satırını Dozimetre_Olcum tablosuna ekler.
        Eğer TCKimlikNo + Periyot + Yil zaten mevcutsa hata döner
        (pk_cakisma="raporla" ile uyumlu).
        """
        conn, kapat = self._baglanti()
        try:
            # Tablo yoksa oluştur
            conn.execute(self._DDL)

            kayit_no = uuid.uuid4().hex[:12].upper()

            # Excel alan adları → DB kolon adları
            hp10  = self._float(kayit.get("DerinDoz",    kayit.get("Hp10",  "")))
            hp007 = self._float(kayit.get("YuzeyselDoz", kayit.get("Hp007", "")))
            durum = kayit.get("Aciklama") or kayit.get("Durum") or "Excel İçe Aktarma"

            conn.execute(
                """
                INSERT INTO Dozimetre_Olcum
                    (KayitNo, SiraNo, RaporNo, Periyot, PeriyotAdi, Yil,
                     DozimetriTipi, AdSoyad, TCKimlikNo, CalistiBirim,
                     PersonelID, DozimetreNo, VucutBolgesi,
                     Hp10, Hp007, Durum)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    kayit_no,
                    kayit.get("SiraNo") or None,
                    kayit.get("RaporNo", ""),
                    kayit.get("Periyot", ""),
                    kayit.get("PeriyotAdi", ""),
                    self._int(kayit.get("Yil", "")),
                    kayit.get("DozimetriTipi", "Excel"),
                    kayit.get("AdSoyad", ""),
                    kayit.get("TCKimlikNo", ""),
                    kayit.get("CalistiBirim", ""),
                    kayit.get("PersonelID", kayit.get("TCKimlikNo", "")),
                    kayit.get("DozimetreNo", ""),
                    kayit.get("VucutBolgesi", ""),
                    hp10,
                    hp007,
                    durum,
                ),
            )
            conn.commit()
            return _Sonuc(basarili=True)

        except Exception as exc:
            import sqlite3
            if isinstance(exc, sqlite3.IntegrityError):
                return _Sonuc(basarili=False, mesaj="Bu kayıt zaten mevcut (UNIQUE ihlali)")
            return _Sonuc(basarili=False, mesaj=str(exc))
        finally:
            if kapat:
                conn.close()

    # ------------------------------------------------------------------
    # Yardımcı dönüşümler
    # ------------------------------------------------------------------

    @staticmethod
    def _float(val) -> float | None:
        if val is None or str(val).strip() == "":
            return None
        try:
            return float(str(val).replace(",", "."))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _int(val) -> int | None:
        if val is None or str(val).strip() == "":
            return None
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return None
