"""NB_PlanSatir tablosunu tamamen hard delete yapmak için yardımcı script.

Kullanım örnekleri:
    python scripts/hard_delete_nobet_plan.py
    python scripts/hard_delete_nobet_plan.py --dry-run
    python scripts/hard_delete_nobet_plan.py --db /path/to/db.sqlite
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.paths import DB_PATH  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NB_PlanSatir tablosunu tamamen temizle"
    )
    p.add_argument(
        "--db",
        default=DB_PATH,
        help=f"SQLite dosya yolu (varsayılan: {DB_PATH})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Silmeden sadece kaç kayıt olduğunu göster.",
    )
    return p.parse_args()


def _baglan(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _sayac(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM NB_PlanSatir").fetchone()[0]


def _sil(conn: sqlite3.Connection) -> int:
    # PRAGMA transaction dışında uygulanmalı
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.commit()
    try:
        conn.execute("BEGIN")
        silinen = conn.execute("DELETE FROM NB_PlanSatir").rowcount
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return int(silinen)


def main() -> None:
    args = _parse_args()

    db_path = str(Path(args.db))
    if not Path(db_path).exists():
        raise SystemExit(f"Hata: DB bulunamadı: {db_path}")

    conn = _baglan(db_path)
    try:
        satir_say = _sayac(conn)
        print(f"NB_PlanSatir toplam kayıt sayısı: {satir_say}")

        if args.dry_run:
            print("DRY-RUN: Gerçek silme yapılmadı.")
            return

        silinen = _sil(conn)
        print(f"Silme tamamlandı: {silinen} kayıt silindi.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
