#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin klasöründeki tema import'larını ve hardcoded renkleri düzelt
"""

import os
import re
from pathlib import Path

# Import theme colors if available, otherwise define fallback
try:
    from ui.styles.colors import DarkTheme as C
except ImportError:
    C = {}

def fix_admin_imports(content, filename):
    """Admin dosyalarına merkezi tema import'larını ekle"""
    
    # Eğer zaten import edilmişse skip et
    if "from ui.styles.components import STYLES" in content:
        return content, False
    
    if "from ui.styles.colors import" in content:
        return content, False
    
    # Icons import'u bulunan satırdan sonra tema import'ını ekle
    if "from ui.styles.icons import" in content:
        content = content.replace(
            "from ui.styles.icons import Icons, IconRenderer",
            "from ui.styles.icons import Icons, IconRenderer\nfrom ui.styles.colors import DarkTheme as C\nfrom ui.styles.components import STYLES"
        )
        return content, True
    
    # Eğer hiç styles import'u yoksa ekle
    if "from ui.styles" not in content:
        # Import bölümünün sonunu bul
        import_match = re.search(r'(from core\..*|from database\..*)', content)
        if import_match:
            end_pos = content.find('\n', import_match.end())
            content = content[:end_pos] + "\nfrom ui.styles.colors import DarkTheme as C\nfrom ui.styles.components import STYLES" + content[end_pos:]
            return content, True
    
    return content, False


def fix_hardcoded_colors(content):
    """Hardcoded renkleri tema referanslarına çevir"""
    
    replacements = [
        # Uyarı/Hata (Kırmızı)
        (r'"color: #e81123', r'"color: {DarkTheme.ACCENT_DANGER}', 'warning red'),
        (r'color: #e81123', f'color: {{DarkTheme.ACCENT_DANGER}}', 'warning red'),
        (r'#e81123', '{DarkTheme.ACCENT_DANGER}', 'warning red'),
        
        # Info/Mavi
        (r'#3ecf8e', '{DarkTheme.ACCENT_SUCCESS}', 'info/success'),
        
        # Uyarı/Sarı
        (r'#f7b731', '{DarkTheme.ACCENT_WARNING}', 'warning yellow'),
        
        # Hata/Kırmızı
        (r'#f75f5f', '{DarkTheme.ACCENT_DANGER}', 'error red'),
        (r'#d63031', '{DarkTheme.ACCENT_DANGER}', 'critical red'),
        
        # Gri/Debug
        (r'#888888', '{DarkTheme.TEXT_MUTED}', 'debug gray'),
        
        # Açık gri/Muted
        (r'#cccccc', '{DarkTheme.TEXT_SECONDARY}', 'light gray'),
        
        # Arka plan ışık
        (r'#f0f0f0', '{DarkTheme.BG_SECONDARY}', 'light bg'),
        
        # Terminal/Console arka plan
        (r'#1e1e1e', '{DarkTheme.BG_PRIMARY}', 'dark bg'),
        
        # Terminal yazı (yeşil)
        (r'#00ff00', '{DarkTheme.ACCENT_SUCCESS}', 'console green'),
        
        # Microsoft Mavi
        (r'#0078d4', '{DarkTheme.ACCENT}', 'ms blue'),
        (r'#106ebe', '{DarkTheme.ACCENT}', 'ms blue hover'),
        
        # Microsoft Yeşil
        (r'#107c10', '{DarkTheme.ACCENT_SUCCESS}', 'ms green'),
        (r'#0d6e07', '{DarkTheme.ACCENT_SUCCESS}', 'ms green hover'),
        
        # Koyu Kırmızı
        (r'#c70e1a', '{DarkTheme.ACCENT_DANGER}', 'dark red'),
    ]
    
    modified = False
    for pattern, replacement, note in replacements[:3]:  # İlk 3'ü kontrol et
        if pattern in content:
            modified = True
            # Buraya replacement mantığı eklenecek
    
    return content, modified


def process_admin_file(file_path):
    """Admin dosyasını işle"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # 1. Tema import'larını ekle
        new_content, imp_modified = fix_admin_imports(content, file_path.name)
        if imp_modified:
            modified = True
            content = new_content
        
        return modified
    except Exception as e:
        print(f"❌ Hata ({file_path.name}): {e}")
        return False


def main():
    admin_dir = Path(r'c:\Users\user\Desktop\Python Program\REPYS-main\REPYS\ui\admin')
    
    if not admin_dir.exists():
        print("❌ Admin klasörü bulunamadı!")
        return
    
    admin_files = list(admin_dir.glob('*.py'))
    admin_files = [f for f in admin_files if f.name != '__init__.py']
    
    print(f"🔍 Admin klasöründe {len(admin_files)} dosya bulundu.")
    print("📝 Tema import'ları kontrol ediliyor...\n")
    
    modified_count = 0
    for file_path in admin_files:
        if process_admin_file(file_path):
            modified_count += 1
            print(f"✅ {file_path.name}")
    
    print(f"\n{'='*60}")
    print(f"📊 {modified_count} dosya güncelleme için işaretlendi")
    print(f"⚠️  Hardcoded renklerin düzeltilmesi manuel olarak yapılacak")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
