"""
Example personnel PDF template generator.

This script reads personnel-related tables and builds a single PDF report that
contains "all available information" for one sample person.

Usage:
    python scripts/generate_personel_pdf_template.py
    python scripts/generate_personel_pdf_template.py --kimlik-no 12345678901
    python scripts/generate_personel_pdf_template.py --output docs/personel_ornek.pdf
"""

from __future__ import annotations

import argparse
import html
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.paths import DB_PATH


PERSONEL_SECTIONS = [
    (
        "Kimlik ve Temel Bilgiler",
        [
            ("KimlikNo", "TC Kimlik No"),
            ("AdSoyad", "Ad Soyad"),
            ("DogumYeri", "Dogum Yeri"),
            ("DogumTarihi", "Dogum Tarihi"),
            ("Durum", "Durum"),
            ("AyrilisTarihi", "Ayrilis Tarihi"),
            ("AyrilmaNedeni", "Ayrilma Nedeni"),
        ],
    ),
    (
        "Kurum ve Gorev Bilgileri",
        [
            ("HizmetSinifi", "Hizmet Sinifi"),
            ("KadroUnvani", "Kadro Unvani"),
            ("GorevYeri", "Gorev Yeri"),
            ("KurumSicilNo", "Kurum Sicil No"),
            ("MemuriyeteBaslamaTarihi", "Memuriyete Baslama Tarihi"),
        ],
    ),
    (
        "Iletisim Bilgileri",
        [
            ("CepTelefonu", "Cep Telefonu"),
            ("Eposta", "E-posta"),
        ],
    ),
    (
        "Egitim Bilgileri",
        [
            ("MezunOlunanOkul", "Okul 1"),
            ("MezunOlunanFakulte", "Fakulte/Bolum 1"),
            ("MezuniyetTarihi", "Mezuniyet Tarihi 1"),
            ("DiplomaNo", "Diploma No 1"),
            ("MezunOlunanOkul2", "Okul 2"),
            ("MezunOlunanFakulte2", "Fakulte/Bolum 2"),
            ("MezuniyetTarihi2", "Mezuniyet Tarihi 2"),
            ("DiplomaNo2", "Diploma No 2"),
        ],
    ),
    (
        "Saglik Ozet Bilgileri",
        [
            ("MuayeneTarihi", "Son Muayene Tarihi"),
            ("Sonuc", "Saglik Sonucu"),
        ],
    ),
    (
        "Dosya Linkleri",
        [
            ("Resim", "Resim"),
            ("Diploma1", "Diploma 1"),
            ("Diploma2", "Diploma 2"),
            ("OzlukDosyasi", "Ozluk Dosyasi"),
        ],
    ),
]


def fmt_date(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    if not text:
        return "-"
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return text


def text(value: Any) -> str:
    if value is None:
        return "-"
    t = str(value).strip()
    return t if t else "-"


def escape(value: Any) -> str:
    return html.escape(text(value))


def fetch_one_person(conn: sqlite3.Connection, kimlik_no: str | None) -> dict[str, Any]:
    cur = conn.cursor()
    if kimlik_no:
        cur.execute("SELECT * FROM Personel WHERE KimlikNo = ? LIMIT 1", (kimlik_no,))
        row = cur.fetchone()
        if row:
            return dict(row)
    cur.execute(
        """
        SELECT * FROM Personel
        ORDER BY
            CASE WHEN Durum = 'Aktif' THEN 0 ELSE 1 END,
            AdSoyad ASC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    return dict(row) if row else {}


def fetch_related(conn: sqlite3.Connection, personel_id: str) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    cur = conn.cursor()

    cur.execute("SELECT * FROM Izin_Bilgi WHERE TCKimlik = ? LIMIT 1", (personel_id,))
    row = cur.fetchone()
    izin_bilgi = dict(row) if row else {}

    cur.execute(
        """
        SELECT IzinTipi, BaslamaTarihi, Gun, BitisTarihi, Durum
        FROM Izin_Giris
        WHERE Personelid = ?
        ORDER BY BaslamaTarihi DESC
        LIMIT 15
        """,
        (personel_id,),
    )
    izin_gecmis = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT AitYil, Donem, Birim, CalismaKosulu, AylikGun, KullanilanIzin, FiiliCalismaSaat
        FROM FHSZ_Puantaj
        WHERE Personelid = ?
        ORDER BY AitYil DESC, Donem DESC
        LIMIT 12
        """,
        (personel_id,),
    )
    puantaj = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT Yil, MuayeneTarihi, SonrakiKontrolTarihi, Sonuc, Durum,
               DermatolojiDurum, DahiliyeDurum, GozDurum, GoruntulemeDurum
        FROM Personel_Saglik_Takip
        WHERE Personelid = ?
        ORDER BY Yil DESC
        LIMIT 10
        """,
        (personel_id,),
    )
    saglik = [dict(r) for r in cur.fetchall()]

    return {
        "izin_bilgi": izin_bilgi,
        "izin_gecmis": izin_gecmis,
        "puantaj": puantaj,
        "saglik": saglik,
    }


def section_table(title: str, rows: list[tuple[str, str]], personel: dict[str, Any]) -> str:
    tr = []
    for key, label in rows:
        value = personel.get(key, "")
        if "Tarih" in key:
            value = fmt_date(value)
        tr.append(
            f"<tr><th>{html.escape(label)}</th><td>{escape(value)}</td></tr>"
        )
    return (
        "<div class='section'>"
        f"<h3>{html.escape(title)}</h3>"
        "<table class='kv'>"
        + "".join(tr)
        + "</table>"
        "</div>"
    )


def list_table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return (
            "<div class='section'>"
            f"<h3>{html.escape(title)}</h3><p class='empty'>Kayit bulunamadi.</p>"
            "</div>"
        )
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(col)}</td>" for col in row) + "</tr>")
    return (
        "<div class='section'>"
        f"<h3>{html.escape(title)}</h3>"
        "<table class='grid'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
        "</div>"
    )


def profile_overview(personel: dict[str, Any]) -> str:
    ad = escape(personel.get("AdSoyad", "-"))
    hizmet = escape(personel.get("HizmetSinifi", "-"))
    kimlik = escape(personel.get("KimlikNo", "-"))
    dogum_yeri = escape(personel.get("DogumYeri", "-"))
    dogum_tarihi = escape(fmt_date(personel.get("DogumTarihi", "")))
    telefon = escape(personel.get("CepTelefonu", "-"))
    eposta = escape(personel.get("Eposta", "-"))
    kadro = escape(personel.get("KadroUnvani", "-"))
    baslama = escape(fmt_date(personel.get("MemuriyeteBaslamaTarihi", "")))
    sicil = escape(personel.get("KurumSicilNo", "-"))
    gorev = escape(personel.get("GorevYeri", "-"))
    okul1 = escape(personel.get("MezunOlunanOkul", "-"))
    fak1 = escape(personel.get("MezunOlunanFakulte", "-"))
    mez1 = escape(fmt_date(personel.get("MezuniyetTarihi", "")))
    dip1 = escape(personel.get("DiplomaNo", "-"))
    okul2 = escape(personel.get("MezunOlunanOkul2", "-"))
    fak2 = escape(personel.get("MezunOlunanFakulte2", "-"))
    mez2 = escape(fmt_date(personel.get("MezuniyetTarihi2", "")))
    dip2 = escape(personel.get("DiplomaNo2", "-"))

    return f"""
    <div class='overview section'>
      <table class='layout'>
        <tr>
          <td class='photo-cell'>
            <div class='photo-box'>{{Resim}}</div>
          </td>
          <td class='gap-cell'></td>
          <td class='hero-cell'>
            <div class='name'>{ad}</div>
            <div class='hizmet'>{hizmet}</div>
          </td>
        </tr>
        <tr>
          <td class='left-cell'>
            <div class='subhead'>Kimlik Bilgileri</div>
            <p><b>T.C. Kimlik No:</b> {kimlik}</p>
            <p><b>Dogum Yeri / Tarihi:</b> {dogum_yeri} / {dogum_tarihi}</p>
            <div class='subhead'>Iletisim</div>
            <p><b>Telefon:</b> {telefon}</p>
            <p><b>E-posta:</b> {eposta}</p>
          </td>
          <td class='gap-cell'></td>
          <td class='right-cell'>
            <div class='subhead'>Kadro ve Kurumsal Bilgiler</div>
            <p><b>Kadro Unvani:</b> {kadro}</p>
            <p><b>Memuriyete Baslama Tarihi:</b> {baslama}</p>
            <p><b>Kurum Sicil No:</b> {sicil}</p>
            <p><b>Gorev Yeri:</b> {gorev}</p>
            <div class='subhead'>Egitim</div>
            <p>{okul1}</p>
            <p>{fak1}</p>
            <p>{mez1} / {dip1}</p>
            <p>{okul2}</p>
            <p>{fak2}</p>
            <p>{mez2} / {dip2}</p>
          </td>
        </tr>
      </table>
    </div>
    """


def build_html(personel: dict[str, Any], related: dict[str, Any]) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    kimlik = text(personel.get("KimlikNo"))
    ad = text(personel.get("AdSoyad"))

    parts: list[str] = [
        "<html><head><meta charset='utf-8'>",
        """
        <style>
        * { box-sizing: border-box; }
        body { font-family: 'Times New Roman', serif; color: #111827; font-size: 10pt; margin: 0; }
        .sheet { border: 1px solid #dbe3ee; border-radius: 6px; overflow: hidden; }
        .header {
            background: #ffffff;
            border-top: 5px solid #548ab7;
            color: #1f2937;
            padding: 12px 18px 8px 18px;
        }
        .header h1 { margin: 0 0 4px 0; font-size: 18pt; font-weight: 700; color: #548ab7; }
        .header .sub { margin: 0; font-size: 10pt; color: #475569; }
        .meta {
            background: #f9fbfd;
            border-top: 1px solid #dbe3ee;
            border-bottom: 1px solid #dbe3ee;
            padding: 8px 18px;
            color: #334155;
            font-size: 9pt;
        }
        .content { padding: 10px 12px 12px 12px; }
        .section { margin: 10px 0; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; }
        h3 {
            margin: 0;
            padding: 7px 10px;
            font-size: 11pt;
            color: #548ab7;
            background: #f6f9fc;
            border-bottom: 1px solid #e2e8f0;
        }
        table { width: 100%; border-collapse: collapse; }
        .kv th { width: 32%; text-align: left; background: #fbfdff; color: #334155; border: 1px solid #e2e8f0; padding: 5px 7px; font-weight: 700; }
        .kv td { border: 1px solid #e2e8f0; padding: 5px 7px; }
        .grid th { background: #f6f9fc; border: 1px solid #d9e4f2; padding: 5px 7px; text-align: left; color: #2f4f6f; font-weight: 700; }
        .grid td { border: 1px solid #e2e8f0; padding: 5px 7px; }
        .grid tbody tr:nth-child(even) td { background: #fcfdff; }
        .empty { color: #64748b; font-style: italic; padding: 8px 10px; margin: 0; }
        .footer {
            margin-top: 12px;
            padding: 8px 10px;
            border: 1px solid #dbe3ee;
            border-radius: 4px;
            background: #f8fafc;
            font-size: 8.8pt;
            color: #475569;
        }
        .overview { border-color: #cfd9e6; }
        .layout td { vertical-align: top; border: 1px solid #dbe3ee; padding: 8px; }
        .layout .gap-cell { width: 6.9%; background: #ffffff; border-left: none; border-right: none; }
        .layout .photo-cell { width: 34.3%; text-align: center; }
        .layout .hero-cell { width: 58.8%; vertical-align: middle; }
        .photo-box {
            border: 1px solid #c7d4e4;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 11pt;
            background: #ffffff;
        }
        .name {
            font-size: 28pt;
            line-height: 1.1;
            color: #548ab7;
            font-weight: 700;
        }
        .hizmet {
            margin-top: 6px;
            font-size: 12pt;
            font-weight: 700;
            color: #374151;
        }
        .subhead {
            margin: 2px 0 6px 0;
            color: #548ab7;
            font-size: 11pt;
            font-weight: 700;
        }
        .left-cell p, .right-cell p {
            margin: 0 0 4px 0;
            font-size: 10pt;
        }
        </style>
        """,
        "</head><body>",
        "<div class='sheet'>",
        "<div class='header'>",
        "<h1>Personel Bilgi Raporu</h1>",
        f"<p class='sub'>{escape(ad)} | TC: {escape(kimlik)}</p>",
        "</div>",
        f"<div class='meta'>Olusturma Zamani: {escape(now)} | Kaynak: ITF Desktop</div>",
        "<div class='content'>",
        profile_overview(personel),
    ]

    for title, rows in PERSONEL_SECTIONS:
        parts.append(section_table(title, rows, personel))

    izin_bilgi = related.get("izin_bilgi", {}) or {}
    parts.append(
        list_table(
            "Izin Bilgi Ozeti",
            [
                "Yillik Devir",
                "Yillik Hakedis",
                "Yillik Toplam Hak",
                "Yillik Kullanilan",
                "Yillik Kalan",
                "SUA Kalan",
                "Rapor/Mazeret Toplam",
            ],
            [
                [
                    izin_bilgi.get("YillikDevir", "-"),
                    izin_bilgi.get("YillikHakedis", "-"),
                    izin_bilgi.get("YillikToplamHak", "-"),
                    izin_bilgi.get("YillikKullanilan", "-"),
                    izin_bilgi.get("YillikKalan", "-"),
                    izin_bilgi.get("SuaKalan", "-"),
                    izin_bilgi.get("RaporMazeretTop", "-"),
                ]
            ]
            if izin_bilgi
            else [],
        )
    )

    izin_rows = []
    for r in related.get("izin_gecmis", []) or []:
        izin_rows.append(
            [
                r.get("IzinTipi", "-"),
                fmt_date(r.get("BaslamaTarihi", "")),
                r.get("Gun", "-"),
                fmt_date(r.get("BitisTarihi", "")),
                r.get("Durum", "-"),
            ]
        )
    parts.append(
        list_table(
            "Izin Gecmisi (Son 15 Kayit)",
            ["Izin Tipi", "Baslama", "Gun", "Bitis", "Durum"],
            izin_rows,
        )
    )

    puantaj_rows = []
    for r in related.get("puantaj", []) or []:
        puantaj_rows.append(
            [
                r.get("AitYil", "-"),
                r.get("Donem", "-"),
                r.get("Birim", "-"),
                r.get("CalismaKosulu", "-"),
                r.get("AylikGun", "-"),
                r.get("KullanilanIzin", "-"),
                r.get("FiiliCalismaSaat", "-"),
            ]
        )
    parts.append(
        list_table(
            "FHSZ Puantaj (Son 12 Donem)",
            ["Yil", "Donem", "Birim", "Calisma Kosulu", "Aylik Gun", "Kullanilan Izin", "Fiili Saat"],
            puantaj_rows,
        )
    )

    saglik_rows = []
    for r in related.get("saglik", []) or []:
        saglik_rows.append(
            [
                r.get("Yil", "-"),
                fmt_date(r.get("MuayeneTarihi", "")),
                fmt_date(r.get("SonrakiKontrolTarihi", "")),
                r.get("Sonuc", "-"),
                r.get("Durum", "-"),
                r.get("DermatolojiDurum", "-"),
                r.get("DahiliyeDurum", "-"),
                r.get("GozDurum", "-"),
                r.get("GoruntulemeDurum", "-"),
            ]
        )
    parts.append(
        list_table(
            "Saglik Takip Detay (Son Kayitlar)",
            [
                "Yil",
                "Muayene",
                "Sonraki Kontrol",
                "Sonuc",
                "Durum",
                "Dermatoloji",
                "Dahiliye",
                "Goz",
                "Goruntuleme",
            ],
            saglik_rows,
        )
    )

    parts.append(
        "<div class='footer'>"
        "Not: Bu dokuman kurum ici raporlama amacli ornek personel sablonudur."
        "</div>"
    )
    parts.append("</div></div></body></html>")
    return "".join(parts)


def write_pdf(html_content: str, output_path: Path) -> None:
    app = QGuiApplication.instance() or QGuiApplication([])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = QTextDocument()
    doc.setHtml(html_content)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(output_path))
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)
    doc.print_(printer)

    # Keep reference to avoid lint/static complaints
    _ = app


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate example personnel PDF template.")
    parser.add_argument("--kimlik-no", help="Specific Personel.KimlikNo to use as sample.")
    parser.add_argument(
        "--output",
        default="docs/ornek_personel_raporu.pdf",
        help="Output PDF path (default: docs/ornek_personel_raporu.pdf)",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        personel = fetch_one_person(conn, args.kimlik_no)
        if not personel:
            raise RuntimeError("Personel tablosunda kayit bulunamadi.")

        personel_id = str(personel.get("KimlikNo", "")).strip()
        related = fetch_related(conn, personel_id)
        html_content = build_html(personel, related)
    finally:
        conn.close()

    output_path = Path(args.output)
    write_pdf(html_content, output_path)
    print(f"PDF olusturuldu: {output_path}")


if __name__ == "__main__":
    main()
