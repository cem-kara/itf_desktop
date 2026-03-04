#!/usr/bin/env python3
"""
REPYS — Tema Lint Scripti
=========================
Yasak inline renk pattern'lerini tarar ve raporlar.

Kullanım:
    python scripts/lint_theme.py              # Tüm ui/ tarar
    python scripts/lint_theme.py --fix        # (gelecek) otomatik düzelt
    python scripts/lint_theme.py ui/pages/personel/personel_ekle.py  # tek dosya

Çıkış kodu:
    0 → temiz
    1 → ihlal bulundu (pre-commit hook için)
"""

import os
import re
import sys
from pathlib import Path

# ── Proje kökü ────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
UI_DIR = ROOT / "ui"

# ── Yasak pattern'ler ─────────────────────────────────────────
# (regex, açıklama, öneri)
RULES = [
    (
        r'setStyleSheet\s*\(\s*f["\'].*?(?:DarkTheme|get_current_theme\(\)|_get_C\(\)|C)\.',
        "f-string içinde tema token'ı",
        "setProperty('color-role', '...') veya setProperty('bg-role', '...') kullanın",
    ),
    (
        r'setStyleSheet\s*\(\s*f["\'].*?_C\[',
        "_C dict'i f-string içinde",
        "setProperty('color-role', '...') kullanın",
    ),
    (
        r'setStyleSheet\s*\([^)]*"[^"]*#[0-9a-fA-F]{3,6}',
        "Hardcoded hex renk",
        "DarkTheme token'ı kullanın (C.TEXT_PRIMARY vb.)",
    ),
    (
        r'setStyleSheet\s*\(\s*f["\'].*?(?:BG_|TEXT_|ACCENT|BORDER_|INPUT_|STATUS_|BTN_)',
        "Doğrudan token ismi f-string içinde",
        "setProperty + rol sistemi kullanın",
    ),
]

# ── Yorum / docstring satırları atla ─────────────────────────
def is_comment_or_docstring(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("#")
        or stripped.startswith('"""')
        or stripped.startswith("'''")
        or stripped.startswith("*")
    )


def scan_file(fpath: Path) -> list[tuple[int, str, str, str]]:
    """
    Dosyayı tara. İhlalleri (satır_no, satır, açıklama, öneri) listesi olarak döndür.
    """
    results = []
    try:
        lines = fpath.read_text(encoding="utf-8").splitlines()
    except Exception:
        return results

    for i, line in enumerate(lines, 1):
        if is_comment_or_docstring(line):
            continue
        for pattern, desc, suggestion in RULES:
            if re.search(pattern, line):
                results.append((i, line.rstrip(), desc, suggestion))
                break  # Aynı satırda birden fazla kural eşleşse de bir kez raporla

    return results


def scan_directory(directory: Path) -> dict[Path, list]:
    """Dizini recursive tara, sonuçları {dosya: ihlal_listesi} olarak döndür."""
    findings = {}
    for fpath in sorted(directory.rglob("*.py")):
        if "__pycache__" in str(fpath):
            continue
        issues = scan_file(fpath)
        if issues:
            findings[fpath] = issues
    return findings


def format_report(findings: dict, root: Path) -> str:
    lines = []
    total = sum(len(v) for v in findings.values())

    if not findings:
        lines.append("✅  Yasak pattern bulunamadı — temiz!")
        return "\n".join(lines)

    lines.append(f"❌  {total} ihlal, {len(findings)} dosyada:\n")

    for fpath, issues in findings.items():
        rel = fpath.relative_to(root)
        lines.append(f"  📄  {rel}")
        for lineno, code, desc, suggestion in issues:
            lines.append(f"      satır {lineno}: {desc}")
            lines.append(f"        KOD : {code.strip()[:100]}")
            lines.append(f"        ÖNERİ: {suggestion}")
        lines.append("")

    lines.append(f"Toplam: {total} ihlal")
    lines.append("Düzeltme rehberi: GELISTIRICI_REHBERI.md — Bölüm 5a")

    return "\n".join(lines)


def main():
    # Hedefi belirle
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        target = Path(sys.argv[1])
        if target.is_file():
            findings = {target: scan_file(target)} if scan_file(target) else {}
        elif target.is_dir():
            findings = scan_directory(target)
        else:
            print(f"Hata: {target} bulunamadı", file=sys.stderr)
            sys.exit(2)
    else:
        findings = scan_directory(UI_DIR)

    report = format_report(findings, ROOT)
    print(report)

    # Pre-commit hook için: ihlal varsa 1 döndür
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
