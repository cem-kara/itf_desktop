from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Script doğrudan scripts/ altından çalıştırıldığında proje kökünü path'e ekle.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.date_utils import looks_like_date_column, parse_date, to_db_date
from core.logger import logger
from core.paths import DB_PATH
from database.table_config import TABLES


def _pk_columns(cfg):
    pk = cfg.get("pk")
    if isinstance(pk, list):
        return pk
    if pk:
        return [pk]
    return []


def _make_backup(db_path: str) -> str:
    src = Path(db_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = src.with_suffix(src.suffix + f".bak_{stamp}")
    shutil.copy2(src, backup_path)
    logger.info(f"DB yedeği oluşturuldu: {backup_path}")
    return str(backup_path)


def normalize_all_dates(db_path: str, dry_run: bool = False, backup: bool = True):
    if backup and not dry_run:
        _make_backup(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_updates = 0
    total_unparsed = 0
    table_summaries = []

    try:
        for table_name, cfg in TABLES.items():
            columns = cfg.get("columns", [])
            date_fields = cfg.get("date_fields") or [c for c in columns if looks_like_date_column(c)]
            if not date_fields:
                continue
            is_syncable = (
                cfg.get("sync", True)
                and cfg.get("pk") is not None
                and cfg.get("sync_mode") != "pull_only"
            )

            pk_cols = _pk_columns(cfg)
            select_cols = list(columns)
            where_mode = "pk"
            if not pk_cols:
                # PK yoksa rowid kullanarak güvenli güncelle.
                where_mode = "rowid"
                select_cols = ["rowid"] + select_cols

            select_sql = f"SELECT {', '.join(select_cols)} FROM {table_name}"
            rows = cur.execute(select_sql).fetchall()
            table_columns = {
                r["name"] for r in cur.execute(f"PRAGMA table_info({table_name})").fetchall()
            }

            table_updates = 0
            table_unparsed = 0

            for row in rows:
                row_dict = dict(row)
                update_data = {}

                for field in date_fields:
                    raw = row_dict.get(field)
                    norm = to_db_date(raw)
                    if raw != norm:
                        update_data[field] = norm
                    elif raw not in (None, "") and parse_date(raw) is None:
                        table_unparsed += 1

                if not update_data:
                    continue

                # Sync uyumlu tablolar için değişiklikleri push edebilmek adına dirty işaretle.
                if is_syncable and "sync_status" in table_columns:
                    update_data["sync_status"] = "dirty"
                if is_syncable and "updated_at" in table_columns:
                    update_data["updated_at"] = datetime.now().isoformat()

                set_clause = ", ".join(f"{k}=?" for k in update_data.keys())
                params = list(update_data.values())

                if where_mode == "pk":
                    where_clause = " AND ".join(f"{k}=?" for k in pk_cols)
                    params += [row_dict.get(k) for k in pk_cols]
                else:
                    where_clause = "rowid=?"
                    params.append(row_dict["rowid"])

                sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
                if not dry_run:
                    cur.execute(sql, params)
                table_updates += 1

            total_updates += table_updates
            total_unparsed += table_unparsed
            table_summaries.append((table_name, table_updates, table_unparsed))

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

        logger.info("Date normalization complete")
        logger.info(f"Updated rows: {total_updates}")
        logger.info(f"Unparsed date values: {total_unparsed}")
        for table_name, upd, bad in table_summaries:
            if upd or bad:
                logger.info(f"  - {table_name}: updated={upd}, unparsed={bad}")
    finally:
        conn.close()


def _build_parser():
    p = argparse.ArgumentParser(
        description=(
            "Normalize all date-like columns in local SQLite DB to YYYY-MM-DD. "
            "Changed rows in syncable tables are marked dirty for next Google Sheets push."
        )
    )
    p.add_argument("--db-path", default=DB_PATH, help="Path to SQLite database file")
    p.add_argument("--dry-run", action="store_true", help="Report only, do not write changes")
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation before applying updates",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    normalize_all_dates(
        db_path=args.db_path,
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )
