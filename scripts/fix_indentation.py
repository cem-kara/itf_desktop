#!/usr/bin/env python3
"""
migrations.py dosyasında aşırı indentation'u düzelt.
"""

import re
from pathlib import Path

def fix_indentation():
    """migrations.py dosyasında indentation sorunu düzelt."""
    
    migrations_path = Path("database/migrations.py")
    
    # Dosyayı oku
    with open(migrations_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # _seed_initial_data metodu bulunduğu kısım
    # 12 boşluk ile başlayan satırları 4 boşluğa düşür (sadece _seed_initial_data içinde)
    
    # _seed_initial_data ile reset_database arasındaki kısım
    pattern = r'(    def _seed_initial_data\(self, cur\):)'
    match = re.search(pattern, content)
    
    if not match:
        # Yanlış indentation ile dene
        pattern = r'(            def _seed_initial_data\(self, cur\):)'
        match = re.search(pattern, content)
        
        if match:
            print("Found incorrect indentation, fixing...")
            # _seed_initial_data'nın başından "reset_database" başlangıcına kadar
            start = match.start()
            reset_start = content.find("def reset_database", start)
            
            if reset_start > 0:
                # Bu aralığı al
                section = content[start:reset_start]
                
                # 12 boşluktan başlayan satırları 4 boşluğa getir
                fixed_section = re.sub(r'^            ', '    ', section, flags=re.MULTILINE)
                
                # Dosyaya yaz
                new_content = content[:start] + fixed_section + content[reset_start:]
                
                with open(migrations_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                print("✓ Indentation düzeltildi!")
                return True
    else:
        print("Indentation zaten doğru")
        return True
    
    print("Hata: _seed_initial_data metodu bulunamadı")
    return False

if __name__ == "__main__":
    fix_indentation()
