#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tüm projede import ve from ... import ... satırlarında yanlış girintiyi düzeltir.
Kendi dosyasını ve __init__.py dosyalarını işlemez.
"""

import os
from pathlib import Path
import re

ROOT_DIR = Path(__file__).parent.parent
TARGET_DIR = ROOT_DIR
SCRIPT_NAME = os.path.basename(__file__)

IMPORT_PATTERNS = [
    re.compile(r"^\s+(import\s+.+)$"),
    re.compile(r"^\s+(from\s+.+import.+)$"),
    re.compile(r"^\s+(as\s+.+)$"),
]

def fix_indentation_in_file(file_path):
    if file_path.name == SCRIPT_NAME or file_path.name == "__init__.py":
        return False
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    modified = False
    new_lines = []
    for line in lines:
        fixed = line
        for pat in IMPORT_PATTERNS:
            m = pat.match(line)
            if m:
                fixed = m.group(1) + "\n"
                modified = True
                break
        new_lines.append(fixed)
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return modified

def main():
    py_files = [f for f in TARGET_DIR.rglob("*.py") if f.name != SCRIPT_NAME and f.name != "__init__.py"]
    print(f"🔍 {len(py_files)} .py dosyası taranıyor...")
    count = 0
    for file_path in py_files:
        if fix_indentation_in_file(file_path):
            print(f"✅ {file_path.relative_to(TARGET_DIR)} düzeltildi")
            count += 1
    print(f"\n{'='*60}")
    print(f"📊 {count} dosyada indentation hatası düzeltildi")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
