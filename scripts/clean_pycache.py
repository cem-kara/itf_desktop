#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__pycache__ temizleyici.

Kullanim:
  python scripts/clean_pycache.py
  python scripts/clean_pycache.py --dry-run
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tum __pycache__ klasorlerini sil.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Silmeden sadece bulunanalri listeler.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(".")
    caches = [p for p in root.rglob("__pycache__") if p.is_dir()]
    if not caches:
        print("Bulunmadi: __pycache__")
        return 0

    if args.dry_run:
        for p in caches:
            print(p)
        print(f"Toplam: {len(caches)}")
        return 0

    removed = 0
    for p in caches:
        shutil.rmtree(p, ignore_errors=True)
        removed += 1
    print(f"Silindi: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
