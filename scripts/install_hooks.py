#!/usr/bin/env python3
"""
REPYS — Git Hook Kurulum Scripti
Kullanım: python scripts/install_hooks.py
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOK_SRC = ROOT / "scripts" / "pre-commit.hook"
HOOK_DST = ROOT / ".git" / "hooks" / "pre-commit"


def main():
    # .git klasörü var mı?
    if not (ROOT / ".git").exists():
        print("❌ Bu dizinde git deposu bulunamadı.")
        print(f"   Önce: cd {ROOT} && git init")
        sys.exit(1)

    # hooks klasörü yoksa oluştur
    HOOK_DST.parent.mkdir(parents=True, exist_ok=True)

    # Kopyala
    shutil.copy(HOOK_SRC, HOOK_DST)

    # Çalıştırılabilir yap (Linux/Mac)
    try:
        os.chmod(HOOK_DST, 0o755)
    except Exception:
        pass  # Windows'ta gerekmiyor

    print(f"✅ Pre-commit hook kuruldu: {HOOK_DST}")
    print()
    print("Test etmek için:")
    print("  python scripts/lint_theme.py")
    print()
    print("Artık her 'git commit' öncesi tema kontrolü otomatik çalışacak.")
    print("Acil durumda atlamak için: git commit --no-verify")


if __name__ == "__main__":
    main()
