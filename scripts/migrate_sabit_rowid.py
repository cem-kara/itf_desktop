# -*- coding: utf-8 -*-
"""Sabitler.Rowid alanlarini sbt### formatina cevirir."""

import os
import sys
import sqlite3

# Proje kökünü sys.path'e ekle (script doğrudan çalıştırıldığında)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.paths import DB_PATH



def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        # Her satiri internal _rowid_ ile al (Rowid kolonu NULL olsa da yakalanir)
        cur = conn.execute("SELECT _rowid_, Rowid FROM Sabitler ORDER BY _rowid_")
        rows = cur.fetchall()

        # Yeni id'leri uret
        new_ids = [f"sbt_{i:03d}" for i in range(1, len(rows) + 1)]

        # Geçici tablo ile row bazli eşleme
        conn.execute("CREATE TEMP TABLE _sabit_map (rid INTEGER, new_id TEXT, tmp_id TEXT)")
        conn.executemany(
            "INSERT INTO _sabit_map (rid, new_id, tmp_id) VALUES (?, ?, ?)",
            [(r[0], n, f"tmp_{r[0]}") for r, n in zip(rows, new_ids)],
        )

        # 1) Önce geçici benzersiz Rowid ver (unique çakışmayı engelle)
        conn.execute(
            """
            UPDATE Sabitler
            SET Rowid = (SELECT tmp_id FROM _sabit_map WHERE rid = Sabitler._rowid_)
            """
        )

        # 2) Gerçek sbt### Rowid'lere geçir
        conn.execute(
            """
            UPDATE Sabitler
            SET Rowid = (SELECT new_id FROM _sabit_map WHERE rid = Sabitler._rowid_)
            """
        )

        conn.execute("DROP TABLE _sabit_map")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate(DB_PATH)
    print("Sabitler.Rowid migration tamamlandi.")
