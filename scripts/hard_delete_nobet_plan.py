"""NB_PlanSatir ve NB_Plan kayıtlarını hard delete yapmak için yardımcı script.

Kullanım örnekleri:
    python scripts/hard_delete_nobet_plan.py
    python scripts/hard_delete_nobet_plan.py --plan-id PLAN_UUID
    python scripts/hard_delete_nobet_plan.py --birim-id BRM001 --yil 2026 --ay 3
    python scripts/hard_delete_nobet_plan.py --dry-run

Not:
    - Varsayılan davranış direkt silmedir.
    - Sadece önizleme için --dry-run kullanın.
  - FK hatasını önlemek için aynı PlanID'ye bağlı NB_MesaiHesap kayıtları da silinir.
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
        description="NB_PlanSatir + NB_Plan hard delete aracı"
    )
    p.add_argument(
        "--db",
        default=DB_PATH,
        help=f"SQLite dosya yolu (varsayılan: {DB_PATH})",
    )
    p.add_argument(
        "--plan-id",
        action="append",
        dest="plan_ids",
        help="Silinecek PlanID (birden fazla için tekrarlanabilir)",
    )
    p.add_argument("--birim-id", help="BirimID filtresi")
    p.add_argument("--yil", type=int, help="Yıl filtresi")
    p.add_argument("--ay", type=int, help="Ay filtresi (1-12)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Silmeden sadece ne silineceğini göster.",
    )
    return p.parse_args()


def _baglan(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _planlari_bul(conn: sqlite3.Connection, args: argparse.Namespace) -> list[sqlite3.Row]:
    if args.plan_ids:
        plan_ids = sorted({str(pid).strip() for pid in args.plan_ids if str(pid).strip()})
        if not plan_ids:
            return []
        ph = ",".join(["?"] * len(plan_ids))
        return conn.execute(
            f"""
            SELECT PlanID, BirimID, Yil, Ay, Versiyon, Durum
            FROM NB_Plan
            WHERE PlanID IN ({ph})
            ORDER BY Yil, Ay, BirimID, Versiyon
            """,
            plan_ids,
        ).fetchall()

    if args.birim_id and args.yil and args.ay:
        return conn.execute(
            """
            SELECT PlanID, BirimID, Yil, Ay, Versiyon, Durum
            FROM NB_Plan
            WHERE BirimID = ? AND Yil = ? AND Ay = ?
            ORDER BY Versiyon
            """,
            (args.birim_id, args.yil, args.ay),
        ).fetchall()

    if args.birim_id or args.yil or args.ay:
        raise SystemExit(
            "Hata: Dönem filtresi için --birim-id + --yil + --ay birlikte verilmelidir."
        )

    # Filtre yoksa tüm planları seç (tabloyu tamamen boşaltma modu).
    return conn.execute(
        """
        SELECT PlanID, BirimID, Yil, Ay, Versiyon, Durum
        FROM NB_Plan
        ORDER BY Yil, Ay, BirimID, Versiyon
        """
    ).fetchall()


def _sayaclar(conn: sqlite3.Connection, plan_ids: list[str]) -> tuple[int, int, int]:
    if not plan_ids:
        return (0, 0, 0)
    ph = ",".join(["?"] * len(plan_ids))

    satir_say = conn.execute(
        f"SELECT COUNT(*) FROM NB_PlanSatir WHERE PlanID IN ({ph})",
        plan_ids,
    ).fetchone()[0]
    plan_say = conn.execute(
        f"SELECT COUNT(*) FROM NB_Plan WHERE PlanID IN ({ph})",
        plan_ids,
    ).fetchone()[0]
    mesai_say = conn.execute(
        f"SELECT COUNT(*) FROM NB_MesaiHesap WHERE PlanID IN ({ph})",
        plan_ids,
    ).fetchone()[0]
    return (int(satir_say), int(plan_say), int(mesai_say))


def _sil(conn: sqlite3.Connection, plan_ids: list[str]) -> tuple[int, int, int]:
    if not plan_ids:
        return (0, 0, 0)
    ph = ",".join(["?"] * len(plan_ids))

    # Legacy bazı kurulumlarda FK tanımı uyumsuz olabildiği için,
    # bakım amaçlı hard-delete sırasında FK doğrulamasını geçici kapat.
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        with conn:
            mesai = conn.execute(
                f"DELETE FROM NB_MesaiHesap WHERE PlanID IN ({ph})",
                plan_ids,
            ).rowcount
            satir = conn.execute(
                f"DELETE FROM NB_PlanSatir WHERE PlanID IN ({ph})",
                plan_ids,
            ).rowcount
            plan = conn.execute(
                f"DELETE FROM NB_Plan WHERE PlanID IN ({ph})",
                plan_ids,
            ).rowcount
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return (int(satir), int(plan), int(mesai))


def main() -> None:
    args = _parse_args()
    if args.ay is not None and not 1 <= args.ay <= 12:
        raise SystemExit("Hata: --ay 1 ile 12 arasında olmalı.")

    db_path = str(Path(args.db))
    if not Path(db_path).exists():
        raise SystemExit(f"Hata: DB bulunamadı: {db_path}")

    conn = _baglan(db_path)
    try:
        plan_rows = _planlari_bul(conn, args)
        if not plan_rows:
            print("Silinecek plan bulunamadı.")
            return

        plan_ids = [str(r["PlanID"]) for r in plan_rows]
        satir_say, plan_say, mesai_say = _sayaclar(conn, plan_ids)

        print("\nSilinecek planlar:")
        for r in plan_rows:
            print(
                f"- PlanID={r['PlanID']} | Birim={r['BirimID']} | "
                f"Dönem={r['Yil']}/{int(r['Ay']):02d} | "
                f"Versiyon={r['Versiyon']} | Durum={r['Durum']}"
            )

        print("\nEtkilenecek kayıt sayıları:")
        print(f"- NB_PlanSatir : {satir_say}")
        print(f"- NB_MesaiHesap: {mesai_say}")
        print(f"- NB_Plan      : {plan_say}")

        if args.dry_run:
            print("\nDRY-RUN: Gerçek silme yapılmadı.")
            return

        sil_satir, sil_plan, sil_mesai = _sil(conn, plan_ids)
        print("\nSilme tamamlandı:")
        print(f"- Silinen NB_PlanSatir : {sil_satir}")
        print(f"- Silinen NB_MesaiHesap: {sil_mesai}")
        print(f"- Silinen NB_Plan      : {sil_plan}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
