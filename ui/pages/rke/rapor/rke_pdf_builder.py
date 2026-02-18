# -*- coding: utf-8 -*-
"""
RKE PDF Builder

HTML ablonlar ve PDF retim fonksiyonlar.
Qt veya UI'a bamll yoktur  saf i mant katman.

Da ak API:
    html_genel_rapor(veriler, filtre_ozeti) -> str
    html_hurda_rapor(veriler)               -> str
    pdf_olustur(html_content, dosya_yolu)   -> bool
"""
import datetime

from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtCore import QMarginsF

from core.logger import logger


# ===============================================
#  ORTAK CSS
# ===============================================

def _base_css() -> str:
    return """
        body { font-family: 'Times New Roman', serif; font-size: 11pt; color: #000; }
        h1 { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 5px; }
        h2 { font-size: 12pt; font-weight: bold; margin-top: 15px; text-decoration: underline; }
        .center { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10pt; }
        th, td { border: 1px solid #000; padding: 4px; text-align: center; vertical-align: middle; }
        th { background-color: #f0f0f0; font-weight: bold; }
        .left { text-align: left; }
        .sig-table { width: 100%; border: none; margin-top: 40px; }
        .sig-table td { border: none; text-align: center; vertical-align: top; padding: 20px; }
        .line { border-top: 1px solid #000; width: 80%; margin: 30px auto 0; }
        .legal { text-align: justify; margin: 5px 0; line-height: 1.4; }
    """


# ===============================================
#  HTML ABLONLARI
# ===============================================

def html_genel_rapor(veriler: list, filtre_ozeti: str) -> str:
    """Genel kontrol raporu HTML'i retir."""
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows  = "".join(
        f"<tr>"
        f"<td>{r['Cins']}</td>"
        f"<td>{r['EkipmanNo']}</td>"
        f"<td>{r['Pb']}</td>"
        f"<td>{r['Tarih']}<br>{r['Sonuc']}</td>"
        f"<td class='left'>{r['Aciklama']}</td>"
        f"</tr>"
        for r in veriler
    )
    return f"""
    <html><head><style>{_base_css()}</style></head><body>
    <h1>RADYASYON KORUYUCU EKPMAN (RKE) KONTROL RAPORU</h1>
    <div class="center">Filtre: {filtre_ozeti} | Tarih: {tarih}</div>
    <table>
      <thead>
        <tr>
          <th>Koruyucu Cinsi</th><th>Ekipman No</th><th>Pb (mm)</th>
          <th>Kontrol (Tarih  Sonu)</th><th>Aklama</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:9pt; font-style:italic; margin-top:8px;">
      * Bu form toplu kontroller iin retilmitir.
    </p>
    <table class="sig-table">
      <tr>
        <td><b>Kontrol Eden</b><div class="line">mza</div></td>
        <td><b>Birim Sorumlusu</b><div class="line">mza</div></td>
        <td><b>Radyasyon Koruma Sorumlusu</b><div class="line">mza</div></td>
      </tr>
    </table>
    </body></html>
    """


def html_hurda_rapor(veriler: list) -> str:
    """Hurda (HEK) ekipman teknik raporu HTML'i retir."""
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows  = ""
    for i, r in enumerate(veriler, 1):
        sorunlar = []
        if "Deil" in r.get("Sonuc", ""):
            sorunlar.append(f"Muayene: {r['Sonuc']}")
        if r.get("Aciklama"):
            sorunlar.append(r["Aciklama"])
        rows += (
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{r['Cins']}</td>"
            f"<td>{r['EkipmanNo']}</td>"
            f"<td>{r.get('ABD', '')}</td>"
            f"<td>{r['Pb']}</td>"
            f"<td class='left'>{' | '.join(sorunlar)}</td>"
            f"</tr>"
        )
    return f"""
    <html><head><style>{_base_css()}</style></head><body>
    <h1>HURDA (HEK) EKPMAN TEKNK RAPORU</h1>
    <div class="center">Tarih: {tarih}</div>
    <h2>A. mha Edilecek Ekipman Listesi</h2>
    <table>
      <thead>
        <tr>
          <th>Sra</th><th>Cinsi</th><th>Ekipman No</th>
          <th>Blm</th><th>Pb (mm)</th><th>Uygunsuzluk</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <h2>B. Teknik Rapor ve Talep</h2>
    <p class="legal">
      Yukarda bilgileri belirtilen ekipmanlarn fiziksel veya radyolojik btnlklerini
      yitirdikleri tespit edilmitir. Hizmet d braklarak (HEK) demirba kaytlarndan
      dlmesi arz olunur.
    </p>
    <table class="sig-table">
      <tr>
        <td><b>Kontrol Eden</b><div class="line">mza</div></td>
        <td><b>Birim Sorumlusu</b><div class="line">mza</div></td>
        <td><b>RKS</b><div class="line">mza</div></td>
      </tr>
    </table>
    </body></html>
    """


# ===============================================
#  PDF RE
# ===============================================

def pdf_olustur(html_content: str, dosya_yolu: str) -> bool:
    """
    HTML ieriini A4 PDF olarak kaydeder.

    Dn: True  baarl, False  hata olutu.
    """
    try:
        doc = QTextDocument()
        doc.setHtml(html_content)

        writer = QPdfWriter(dosya_yolu)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setResolution(300)

        layout = QPageLayout()
        layout.setPageSize(QPageSize(QPageSize.A4))
        layout.setOrientation(QPageLayout.Portrait)
        layout.setMargins(QMarginsF(15, 15, 15, 15))
        writer.setPageLayout(layout)

        doc.print_(writer)
        return True
    except Exception as e:
        logger.error(f"PDF oluturma hatas: {e}")
        return False
