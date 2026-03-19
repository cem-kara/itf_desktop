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


def fix_setstylesheet_and_darktheme(content):
    """setStyleSheet(f...) ve DarkTheme referanslarını setProperty ile değiştir"""
    modified = False
    # setStyleSheet(f...) satırlarını tespit et ve uyarı/otomatik düzeltme uygula
    pattern = r"(\w+)\.setStyleSheet\(f?['\"](.+?)['\"]\)"
    matches = list(re.finditer(pattern, content))
    for m in matches:
        widget, style = m.group(1), m.group(2)
        # Sadece renk veya stil ataması ise setProperty ile değiştir
        if "background" in style or "color" in style:
            # Renk türünü tespit et
            if "background" in style:
                repl = f"{widget}.setProperty(\"bg-role\", \"panel\")"
            elif "color" in style:
                repl = f"{widget}.setProperty(\"color-role\", \"primary\")"
            else:
                repl = f"# YAPILANDIRILAMADI: {widget}.setProperty(...)"
            content = content.replace(m.group(0), repl)
            modified = True
    # DarkTheme.XXX referanslarını rol stringine çevir
    darktheme_map = {
        'DarkTheme.STATUS_SUCCESS': '"ok"',
        'DarkTheme.STATUS_WARNING': '"warn"',
        'DarkTheme.STATUS_ERROR': '"err"',
        'DarkTheme.TEXT_MUTED': '"muted"',
        'DarkTheme.TEXT_PRIMARY': '"primary"',
        'DarkTheme.BG_SECONDARY': '"panel"',
        'DarkTheme.BG_PRIMARY': '"page"',
        'DarkTheme.ACCENT': '"accent"',
        'DarkTheme.BORDER_PRIMARY': '"primary"',
        'DarkTheme.BORDER_SECONDARY': '"secondary"',
        'DarkTheme.ACCENT_SUCCESS': '"success"',
        'DarkTheme.ACCENT_DANGER': '"err"',
        'DarkTheme.ACCENT_WARNING': '"warn"',
    }
    for k, v in darktheme_map.items():
        if k in content:
            content = content.replace(k, v)
            modified = True
    return content, modified

def fix_hardcoded_colors(content):
    """Hardcoded renkleri tema referanslarına çevir"""
    
    replacements = [
        # Uyarı/Hata (Kırmızı)
        (r'"color: {"accent"_DANGER}', r'"color: {"accent"_DANGER}', 'warning red'),
        (r'color: {"accent"_DANGER}', f'color: {{"accent"_DANGER}}', 'warning red'),
        (r'{"accent"_DANGER}', '{"accent"_DANGER}', 'warning red'),
        
        # Info/Mavi
        (r'{"accent"_SUCCESS}', '{"accent"_SUCCESS}', 'info/success'),
        
        # Uyarı/Sarı
        (r'{"accent"_WARNING}', '{"accent"_WARNING}', 'warning yellow'),
        
        # Hata/Kırmızı
        (r'{"accent"_DANGER}', '{"accent"_DANGER}', 'error red'),
        (r'{"accent"_DANGER}', '{"accent"_DANGER}', 'critical red'),
        
        # Gri/Debug
        (r'{"muted"}', '{"muted"}', 'debug gray'),
        
        # Açık gri/Muted
        (r'{DarkTheme.TEXT_SECONDARY}', '{DarkTheme.TEXT_SECONDARY}', 'light gray'),
        
        # Arka plan ışık
        (r'{"panel"}', '{"panel"}', 'light bg'),
        
        # Terminal/Console arka plan
        (r'{"page"}', '{"page"}', 'dark bg'),
        
        # Terminal yazı (yeşil)
        (r'{"accent"_SUCCESS}', '{"accent"_SUCCESS}', 'console green'),
        
        # Microsoft Mavi
        (r'{"accent"}', '{"accent"}', 'ms blue'),
        (r'{"accent"}', '{"accent"}', 'ms blue hover'),
        
        # Microsoft Yeşil
        (r'{"accent"_SUCCESS}', '{"accent"_SUCCESS}', 'ms green'),
        (r'{"accent"_SUCCESS}', '{"accent"_SUCCESS}', 'ms green hover'),
        
        # Koyu Kırmızı
        (r'{"accent"_DANGER}', '{"accent"_DANGER}', 'dark red'),
    ]
    
    modified = False
    for pattern, replacement, note in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
    return content, modified


def process_admin_file(file_path):
    """Admin dosyasını işle"""
    try:
        # Kendi dosyasını asla işleme
        if file_path.name == "fix_admin_theme.py":
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        modified = False

        # 1. Tema import'larını ekle
        new_content, imp_modified = fix_admin_imports(content, file_path.name)
        if imp_modified:
            modified = True
            content = new_content

        # 2. Hardcoded renkleri düzelt
        new_content, color_modified = fix_hardcoded_colors(content)
        if color_modified:
            modified = True
            content = new_content

        # 3. setStyleSheet ve DarkTheme referanslarını düzelt
        new_content, style_modified = fix_setstylesheet_and_darktheme(content)
        if style_modified:
            modified = True
            content = new_content

        # Eğer değişiklik olduysa dosyayı kaydet
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return modified
    except Exception as e:
        print(f"❌ Hata ({file_path.name}): {e}")
        return False


def main():
    root_dir = Path(r'c:\Users\user\Desktop\Python Program\REPYS-main\REPYS')

    if not root_dir.exists():
        print("❌ Proje klasörü bulunamadı!")
        return

    # Tüm .py dosyalarını (alt klasörler dahil) bul
    all_py_files = [f for f in root_dir.rglob('*.py') if f.name != '__init__.py' and f.name != 'fix_admin_theme.py']

    print(f"🔍 Projede {len(all_py_files)} .py dosyası bulundu.")
    print("📝 Tema import ve hardcoded renkler kontrol ediliyor...\n")

    modified_count = 0
    for file_path in all_py_files:
        if process_admin_file(file_path):
            modified_count += 1
            print(f"✅ {file_path.relative_to(root_dir)}")

    print(f"\n{'='*60}")
    print(f"📊 {modified_count} dosya güncellendi (import ve renkler dahil)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
