#!/usr/bin/env python3
"""
UTF-8 BOM Temizleyici
=====================
Kullanım:
    # Mevcut klasörü tara (varsayılan: .)
    python fix_utf8_bom.py

    # Belirli bir klasörü tara
    python fix_utf8_bom.py --path ./proje/src

    # Belirli uzantıları tara (varsayılan: .py)
    python fix_utf8_bom.py --ext .py .txt .js .ts

    # Önce ne değişeceğini gör, dokunma (dry-run)
    python fix_utf8_bom.py --dry-run

    # Sessiz mod (sadece hata varsa yaz)
    python fix_utf8_bom.py --quiet
"""

import os
import sys
import argparse

UTF8_BOM = b"\xef\xbb\xbf"


def find_bom_files(root: str, extensions: list[str]) -> list[str]:
    """BOM içeren dosyaları bulur."""
    bom_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # __pycache__ ve .git klasörlerini atla
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "node_modules", ".venv", "venv")]
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "rb") as f:
                        if f.read(3) == UTF8_BOM:
                            bom_files.append(filepath)
                except (IOError, PermissionError) as e:
                    print(f"  [UYARI] Okunamadı: {filepath} → {e}", file=sys.stderr)
    return bom_files


def remove_bom(filepath: str) -> bool:
    """Dosyadan BOM'u temizler. Başarılıysa True döner."""
    try:
        with open(filepath, "rb") as f:
            content = f.read()

        if not content.startswith(UTF8_BOM):
            return False  # BOM yok, atla

        with open(filepath, "wb") as f:
            f.write(content[3:])  # İlk 3 byte (BOM) atlanır

        return True
    except (IOError, PermissionError) as e:
        print(f"  [HATA] Yazılamadı: {filepath} → {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Dosyalardaki UTF-8 BOM karakterini toplu temizler.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path", "-p",
        default=".",
        help="Taranacak klasör (varsayılan: mevcut klasör)"
    )
    parser.add_argument(
        "--ext", "-e",
        nargs="+",
        default=[".py"],
        help="İşlenecek uzantılar (varsayılan: .py)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Sadece listele, değiştirme"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Sessiz mod — sadece özet yaz"
    )
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    extensions = [e if e.startswith(".") else f".{e}" for e in args.ext]

    if not os.path.isdir(root):
        print(f"[HATA] Klasör bulunamadı: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Taranan klasör : {root}")
    print(f"Uzantılar       : {', '.join(extensions)}")
    if args.dry_run:
        print("Mod             : DRY-RUN (değişiklik yapılmayacak)")
    print()

    # 1. BOM olan dosyaları bul
    bom_files = find_bom_files(root, extensions)

    if not bom_files:
        print("✓ BOM bulunan dosya yok.")
        return

    print(f"BOM bulunan {len(bom_files)} dosya:\n")
    for f in bom_files:
        rel = os.path.relpath(f, root)
        print(f"  → {rel}")

    if args.dry_run:
        print(f"\n[DRY-RUN] {len(bom_files)} dosya düzeltilecekti. Çıkılıyor.")
        return

    # 2. Temizle
    print()
    fixed = 0
    failed = 0
    for filepath in bom_files:
        rel = os.path.relpath(filepath, root)
        success = remove_bom(filepath)
        if success:
            fixed += 1
            if not args.quiet:
                print(f"  ✓ Düzeltildi: {rel}")
        else:
            failed += 1
            print(f"  ✗ Başarısız : {rel}", file=sys.stderr)

    # 3. Özet
    print(f"\n{'─' * 40}")
    print(f"Toplam   : {len(bom_files)} dosya")
    print(f"Düzeltilen: {fixed} dosya  ✓")
    if failed:
        print(f"Başarısız : {failed} dosya  ✗")
    else:
        print("Hata      : yok  ✓")


if __name__ == "__main__":
    main()
