#!/usr/bin/env python3
"""
fix_mojibake.py — Mojibake (karakter kodlama bozulması) düzeltici
Özellikle Türkçe karakterler için optimize edilmiştir.

Kullanım:
    python fix_mojibake.py <dosya>                  # Dosyayı düzelt
    python fix_mojibake.py                          # REPYS kökünde tüm .py dosyalarını tara/düzelt
    python fix_mojibake.py <dosya> -o <çıktı>       # Çıktıyı ayrı dosyaya yaz
    python fix_mojibake.py <dosya> --inplace         # Dosyanın üzerine yaz
    python fix_mojibake.py --text "bozuk metin"     # Doğrudan metin düzelt
    python fix_mojibake.py --detect <dosya>         # Sadece kodlamayı tespit et
"""

import sys
import os
import argparse
import importlib
from pathlib import Path
from typing import Iterable

# ── Opsiyonel bağımlılıklar ──────────────────────────────────────────────────

try:
    chardet = importlib.import_module("chardet")
    HAS_CHARDET = True
except ImportError:
    chardet = None
    HAS_CHARDET = False

try:
    ftfy = importlib.import_module("ftfy")
    HAS_FTFY = True
except ImportError:
    ftfy = None
    HAS_FTFY = False


# ── Yaygın mojibake dönüşüm tabloları ───────────────────────────────────────

# Latin-1 / Windows-1252 → UTF-8 yanlış yorumlanması (en yaygın durum)
LATIN1_TO_UTF8_MAP = {
    # Türkçe karakterler
    "ü": "ü", "ö": "ö", "ç": "ç", "ş": "ş", "ı": "ı",
    "İ": "İ", "Ç": "Ç", "Ö": "Ö", "Ü": "Ü", "Ş": "Ş",
    "Ğ": "Ğ", "ğ": "ğ", "": "",

    # Yaygın işaretler
    "'": "'", "“": "\u201c", "â€\u009d": "\u201d",
    "–": "–", "—": "—", "…": "…",
    "©": "©", "®": "®", "°": "°", "·": "·",
    "€": "€", "£": "£", "¥": "¥",

    # Diğer Avrupa dilleri
    "é": "é", "è": "è", "ê": "ê", "ë": "ë",
    "à": "à", "á": "á", "â": "â", "ã": "ã",
    "ì": "ì", "í": "í", "î": "î", "ï": "ï",
    "ò": "ò", "ó": "ó", "ô": "ô", "õ": "õ",
    "ù": "ù", "ú": "ú", "û": "û",
    "ñ": "ñ", "ÿ": "ÿ", "ı": "ı",
    "À": "À", "Ï": "Á", "": "", "Ï": "Ï",
    "Ä": "Ä", "Å": "Å", "Æ": "Æ", "Ç": "Ç",
    "È": "È", "É": "É", "Ê": "Ê", "Ë": "Ë",
    "Ì": "Ì", "Ï": "Í", "Î": "Î", "Ï": "Ï",
    "Ñ": "Ñ", "Ù": "Ù", "Ú": "Ú", "Û": "Û",
    "ß": "ß",
}

# Windows-1254 (Türkçe) → UTF-8 yanlış yorumlanması
WIN1254_FIXES = {
    "\xfc": "ü", "\xf6": "ö", "\xe7": "ç", "\xfe": "ş",
    "\xfd": "ı", "\xdd": "İ", "\xc7": "Ç", "\xd6": "Ö",
    "\xdc": "Ü", "\xde": "Ş", "\xd0": "Ğ", "\xf0": "ğ",
    "\xd1": "Ñ",
}

# ISO-8859-9 (Türkçe) için alternatif
ISO8859_9_MAP = {
    b"\xfc": "ü", b"\xf6": "ö", b"\xe7": "ç", b"\xfe": "ş",
    b"\xfd": "ı", b"\xdd": "İ", b"\xc7": "Ç", b"\xd6": "Ö",
    b"\xdc": "Ü", b"\xde": "Ş", b"\xd0": "Ğ", b"\xf0": "ğ",
}

# Yaygın yanlış kodlama çiftleri (kaynak → hedef kodlama)
ENCODING_PAIRS = [
    ("utf-8", "latin-1"),
    ("utf-8", "windows-1252"),
    ("utf-8", "windows-1254"),
    ("utf-8", "iso-8859-9"),
    ("utf-8", "iso-8859-1"),
    ("latin-1", "utf-8"),
    ("windows-1252", "utf-8"),
    ("windows-1254", "utf-8"),
    ("iso-8859-9", "utf-8"),
]


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def detect_encoding(raw_bytes: bytes) -> tuple[str, float]:
    """Ham baytların kodlamasını tespit et."""
    if HAS_CHARDET:
        result = chardet.detect(raw_bytes)
        enc = result.get("encoding") or "utf-8"
        confidence = result.get("confidence", 0)
        return enc, confidence
    # chardet yoksa BOM veya UTF-8 geçerliliğine bak
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", 1.0
    if raw_bytes.startswith(b"\xff\xfe"):
        return "utf-16-le", 1.0
    if raw_bytes.startswith(b"\xfe\xff"):
        return "utf-16-be", 1.0
    try:
        raw_bytes.decode("utf-8")
        return "utf-8", 0.9
    except UnicodeDecodeError:
        return "windows-1254", 0.5  # Türkçe için makul varsayılan


def apply_string_map(text: str, mapping: dict) -> str:
    """Sözlük tabanlı karakter eşlemesini uygula (uzun → kısa önceliği)."""
    for wrong, correct in sorted(mapping.items(), key=lambda x: -len(x[0])):
        text = text.replace(wrong, correct)
    return text


def try_encoding_fix(text: str) -> str:
    """Farklı kodlama çiftlerini deneyerek ilk başarılıyı döndür."""
    for enc_wrong, enc_right in ENCODING_PAIRS:
        try:
            fixed = text.encode(enc_wrong).decode(enc_right)
            # Sonuç mantıklı görünüyorsa (bozuk karakter oranı düştüyse) kabul et
            if mojibake_score(fixed) < mojibake_score(text):
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text


def mojibake_score(text: str) -> float:
    """Metindeki bozuk karakter oranını 0-1 arasında döndür."""
    if not text:
        return 0.0
    suspicious = sum(
        1 for ch in text
        if ord(ch) in range(0xC0, 0x100)  # Latin extended A/B bölgesi
        or "\ufffd" == ch                  # Replacement character
    )
    return suspicious / len(text)


def fix_text(text: str, aggressive: bool = False) -> tuple[str, list[str]]:
    """
    Metni düzelt. Uygulanan adımları da döndür.
    aggressive=True: daha fazla dönüşüm dene.
    """
    steps = []
    original_score = mojibake_score(text)

    # 1. ftfy varsa önce onu dene (en kapsamlı çözüm)
    if HAS_FTFY:
        fixed = ftfy.fix_text(text)
        if fixed != text:
            steps.append("ftfy kütüphanesi uygulandı")
            text = fixed

    # 2. String tabanlı eşleme tablosunu uygula
    before = text
    text = apply_string_map(text, LATIN1_TO_UTF8_MAP)
    if text != before:
        steps.append("Latin-1/Windows-1252 → UTF-8 eşlemesi uygulandı")

    # 3. Kodlama çiftlerini deneyerek düzelt
    if aggressive or mojibake_score(text) > 0.05:
        before = text
        text = try_encoding_fix(text)
        if text != before:
            steps.append("Kodlama yeniden yorumlandı")

    # 4. Yaygın Windows-1254 bozukluklarını gider
    before = text
    text = apply_string_map(text, WIN1254_FIXES)
    if text != before:
        steps.append("Windows-1254 Türkçe düzeltmesi uygulandı")

    final_score = mojibake_score(text)
    if original_score > 0 and final_score < original_score:
        steps.append(
            f"Bozukluk oranı: {original_score:.1%} → {final_score:.1%}"
        )

    return text, steps


def fix_file_bytes(raw: bytes) -> tuple[str, list[str]]:
    """Ham baytları okuyup düzeltilmiş metin döndür."""
    steps = []

    # BOM kaldır
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
        steps.append("UTF-8 BOM kaldırıldı")

    # Kodlamayı tespit et
    encoding, confidence = detect_encoding(raw)
    steps.append(f"Tespit edilen kodlama: {encoding} (güven: {confidence:.0%})")

    # Baytları string'e çevir
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        steps.append(f"'{encoding}' ile okunamadı, latin-1 deneniyor")
        text = raw.decode("latin-1")

    # Metin düzeltmesi uygula
    fixed, fix_steps = fix_text(text)
    steps.extend(fix_steps)

    return fixed, steps


TEXT_EXTENSIONS = {
    ".py", ".pyw", ".md", ".txt", ".json", ".qss", ".css", ".csv",
    ".ini", ".cfg", ".toml", ".yaml", ".yml", ".xml", ".sql", ".sh",
    ".ps1", ".bat", ".cmd", ".gitignore", ".gitattributes",
}

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
}


def _decode_bytes(raw: bytes) -> str:
    """Ham baytı en olası kodlamayla metne çevir."""
    encoding, _ = detect_encoding(raw)
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("latin-1", errors="replace")


def _iter_candidate_files(root: Path, py_only: bool = False) -> Iterable[Path]:
    """Klasördeki metin olma ihtimali yüksek dosyaları üret."""
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base = Path(current_root)
        for name in files:
            p = base / name
            if py_only:
                if p.suffix.lower() == ".py":
                    yield p
                continue
            if p.suffix.lower() in TEXT_EXTENSIONS or p.name in TEXT_EXTENSIONS:
                yield p


def fix_directory_inplace(
    root: Path,
    aggressive: bool = False,
    quiet: bool = False,
    py_only: bool = False,
) -> int:
    """Dizindeki dosyaları tarar ve değişenleri UTF-8 olarak yerinde yazar."""
    toplam = 0
    degisen = 0
    hata = 0

    for dosya in _iter_candidate_files(root, py_only=py_only):
        toplam += 1
        try:
            raw = dosya.read_bytes()
            once = _decode_bytes(raw)
            sonra, _ = fix_text(once, aggressive=aggressive)
            if sonra != once:
                dosya.write_text(sonra, encoding="utf-8")
                degisen += 1
                if not quiet:
                    print(f"✓ Düzeltildi: {dosya}", file=sys.stderr)
        except Exception as exc:
            hata += 1
            if not quiet:
                print(f"! Atlandı: {dosya} ({exc})", file=sys.stderr)

    if not quiet:
        print(
            f"Tarama tamamlandı — Toplam: {toplam}, Düzeltilen: {degisen}, Hata: {hata}",
            file=sys.stderr,
        )
    return degisen


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Mojibake (karakter bozulması) düzeltici — Türkçe optimize",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", help="Düzeltilecek dosya veya klasör")
    parser.add_argument("-o", "--output", help="Çıktı dosyası (varsayılan: stdout)")
    parser.add_argument("--inplace", action="store_true",
                        help="Dosyanın üzerine yaz (yedeği .bak uzantısıyla sakla)")
    parser.add_argument("--text", help="Doğrudan metin düzelt")
    parser.add_argument("--detect", action="store_true",
                        help="Sadece kodlamayı tespit et, düzeltme yapma")
    parser.add_argument("--aggressive", action="store_true",
                        help="Daha fazla dönüşüm dene")
    parser.add_argument("--py-only", action="store_true",
                        help="Klasör modunda sadece .py dosyalarını tara")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Adım bilgilerini gösterme")
    return parser.parse_args()


def print_steps(steps: list[str], quiet: bool):
    if not quiet and steps:
        print("── Uygulanan adımlar ──────────────────", file=sys.stderr)
        for s in steps:
            print(f"  ✓ {s}", file=sys.stderr)
        print(file=sys.stderr)


def main():
    args = parse_args()

    # ── Doğrudan metin modu ──
    if args.text:
        fixed, steps = fix_text(args.text, aggressive=args.aggressive)
        print_steps(steps, args.quiet)
        print(fixed)
        return

    # ── Dosya/Klasör modu ──
    if args.file:
        path = Path(args.file)
    else:
        # Parametre verilmezse REPYS kökünü hedefle ve .py dosyaları tara.
        path = Path(__file__).resolve().parents[1]
        args.py_only = True
        if not args.quiet:
            print(
                f"Dosya parametresi verilmedi, varsayılan tarama: {path} (yalnızca .py)",
                file=sys.stderr,
            )

    if not path.exists():
        print(f"Hata: '{path}' bulunamadı.", file=sys.stderr)
        sys.exit(1)

    # ── Klasör modu (REPO tarama) ──
    if path.is_dir():
        fix_directory_inplace(
            path,
            aggressive=args.aggressive,
            quiet=args.quiet,
            py_only=args.py_only,
        )
        return

    raw = path.read_bytes()

    # Sadece tespit modu
    if args.detect:
        encoding, confidence = detect_encoding(raw)
        score = mojibake_score(raw.decode(encoding, errors="replace"))
        print(f"Dosya    : {path}")
        print(f"Kodlama  : {encoding}")
        print(f"Güven    : {confidence:.0%}")
        print(f"Bozukluk : {score:.1%}" + (" (temiz görünüyor)" if score < 0.01 else " ⚠ mojibake tespit edildi"))
        return

    fixed, steps = fix_file_bytes(raw)
    print_steps(steps, args.quiet)

    # Çıktıyı yaz
    if args.inplace:
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_bytes(raw)
        path.write_text(fixed, encoding="utf-8")
        if not args.quiet:
            print(f"✓ Düzeltildi → {path}  (yedek: {backup})", file=sys.stderr)
    elif args.output:
        Path(args.output).write_text(fixed, encoding="utf-8")
        if not args.quiet:
            print(f"✓ Yazıldı → {args.output}", file=sys.stderr)
    else:
        print(fixed)


# ── Modül olarak kullanım için API ───────────────────────────────────────────

def fix(text: str, aggressive: bool = False) -> str:
    """Tek satır API: fix('bozuk metin') → 'düzeltilmiş metin'"""
    result, _ = fix_text(text, aggressive=aggressive)
    return result


def fix_bytes(data: bytes) -> str:
    """Ham bayt dizisinden düzeltilmiş metin döndür."""
    result, _ = fix_file_bytes(data)
    return result


if __name__ == "__main__":
    main()
