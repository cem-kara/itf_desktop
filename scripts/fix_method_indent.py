#!/usr/bin/env python3
"""
migrations.py dosyasında _seed_initial_data metodunun geri kalanında indentation düzelt.
"""

import re
from pathlib import Path

def fix_method_body():
    """_seed_initial_data metodunun gövdesindeki indentation'u düzelt."""
    
    migrations_path = Path("database/migrations.py")
    
    # Dosyayı oku
    with open(migrations_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # _seed_initial_data bulun - line number
    start_idx = None
    for i, line in enumerate(lines):
        if "def _seed_initial_data(self, cur):" in line:
            start_idx = i
            break
    
    if start_idx is None:
        print("Hata: _seed_initial_data metodu bulunamadı")
        return False
    
    # Sonuna kadar devam et - bir sonraki def veya comment bulana kadar
    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if re.match(r'^    def ', lines[i]):  # Sonraki method
            end_idx = i
            break
        if re.match(r'^    # ====', lines[i]):  # Section comment
            end_idx = i
            break
    
    if end_idx is None:
        end_idx = len(lines)
    
    print(f"Fixing lines {start_idx+1} to {end_idx}")
    
    # Tüm 12 boşluktan başlayan satırları 8 boşluğa getir
    changed = 0
    for i in range(start_idx + 1, end_idx):
        line = lines[i]
        if line.startswith("            ") and not line.startswith("                "):
            # Remove 4 spaces (from 12 to 8)
            lines[i] = line[4:]
            changed += 1
    
    if changed > 0:
        with open(migrations_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✓ {changed} satır düzeltildi!")
        return True
    else:
        print("Değiştirilecek satır yok")
        return False

if __name__ == "__main__":
    fix_method_body()
