# -*- coding: utf-8 -*-
"""RKE Raporlama — PDF Şablonları ve Yardımcılar."""
import datetime
from typing import List, Dict
from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize, QPageLayout, QMarginsF
from core.logger import logger


# ════════════════════════════════════════════════════════════════════
#  PDF ŞABLONLARI
# ════════════════════════════════════════════════════════════════════
def _css():
    """PDF CSS stil tanımlaması."""
    return ("body{font-family:'Times New Roman',serif;font-size:11pt;color:#000;}"
            "h1{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:5px;}"
            "h2{font-size:12pt;font-weight:bold;margin-top:15px;margin-bottom:5px;text-decoration:underline;}"
            ".c{text-align:center;}"
            "table{width:100%;border-collapse:collapse;margin-top:10px;font-size:10pt;}"
            "th,td{border:1px solid #000;padding:4px;text-align:center;vertical-align:middle;}"
            "th{background:#f0f0f0;font-weight:bold;}.l{text-align:left;}"
            ".sig{width:100%;border:none;margin-top:40px;}"
            ".sig td{border:none;text-align:center;vertical-align:top;padding:20px;}"
            ".line{border-top:1px solid #000;width:80%;margin:30px auto 0;}"
            ".legal{text-align:justify;margin:5px 0;line-height:1.4;}")


def html_genel_rapor(veriler: List[Dict], filtre_ozeti: str) -> str:
    """Genel RKE Kontrol Raporu HTML şablonu."""
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows = "".join(
        f"<tr><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td><td>{r['Pb']}</td>"
        f"<td>{r['Tarih']}<br>{r['Fiziksel']}</td><td>{r['Tarih']}<br>{r['Skopi']}</td>"
        f"<td class='l'>{r['Aciklama']}</td></tr>"
        for r in veriler
    )
    return (f"<html><head><style>{_css()}</style></head><body>"
            f"<h1>RADYASYON KORUYUCU EKİPMAN (RKE) KONTROL RAPORU</h1>"
            f"<div class='c'>Filtre: {filtre_ozeti} | Rapor Tarihi: {tarih}</div>"
            f"<table><thead><tr>"
            f"<th width='15%'>Koruyucu Cinsi</th><th width='15%'>Koruyucu No</th>"
            f"<th width='10%'>Pb (mm)</th><th width='20%'>Fiziksel Kontrol</th>"
            f"<th width='20%'>Skopi Kontrol</th><th width='20%'>Açıklama</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"<table class='sig'><tr>"
            f"<td><b>Kontrol Eden</b><div class='line'>İmza</div></td>"
            f"<td><b>Birim Sorumlusu</b><div class='line'>İmza</div></td>"
            f"<td><b>RKS</b><div class='line'>İmza</div></td>"
            f"</tr></table></body></html>")


def html_hurda_rapor(veriler: List[Dict], filtre_ozeti: str) -> str:
    """Hurda (HEK) Ekipman Teknik Raporu HTML şablonu."""
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows = "".join(
        f"<tr><td>{i}</td><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td>"
        f"<td>{r['Birim']}</td><td>{r['Pb']}</td>"
        f"<td class='l'>{' | '.join(filter(None, ['Fiziksel: ' + r['Fiziksel'] if 'Değil' in r['Fiziksel'] else '', ' Skopi: ' + r['Skopi'] if 'Değil' in r['Skopi'] else '', r['Aciklama']]))}</td></tr>"
        for i, r in enumerate(veriler, 1)
    )
    return (f"<html><head><style>{_css()}</style></head><body>"
            f"<h1>HURDA (HEK) EKİPMAN TEKNİK RAPORU</h1>"
            f"<div class='c'>Tarih: {tarih}</div>"
            f"<h2>A. İMHA EDİLECEK EKİPMAN LİSTESİ</h2>"
            f"<table><thead><tr>"
            f"<th width='5%'>Sıra</th><th width='20%'>Malzeme Adı</th>"
            f"<th width='15%'>Barkod/Demirbaş</th><th width='15%'>Bölüm</th>"
            f"<th width='10%'>Pb (mm)</th><th width='35%'>Uygunsuzluk</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"<h2>B. TEKNİK RAPOR</h2>"
            f"<div class='legal'>Yukarıdaki ekipmanların fiziksel veya radyolojik bütünlüklerini "
            f"yitirdikleri tespit edilmiştir. HEK kaydına alınması arz olunur.</div>"
            f"<table class='sig'><tr>"
            f"<td><b>Kontrol Eden</b><div class='line'>İmza</div></td>"
            f"<td><b>Birim Sorumlusu</b><div class='line'>İmza</div></td>"
            f"<td><b>RKS</b><div class='line'>İmza</div></td>"
            f"</tr></table></body></html>")


def pdf_olustur(html: str, dosya: str) -> bool:
    """HTML'den PDF dosyası oluştur."""
    try:
        doc = QTextDocument()
        doc.setHtml(html)
        w = QPdfWriter(dosya)
        w.setPageSize(QPageSize(QPageSize.A4))
        w.setResolution(300)
        lay = QPageLayout()
        lay.setPageSize(QPageSize(QPageSize.A4))
        lay.setOrientation(QPageLayout.Portrait)
        lay.setMargins(QMarginsF(15, 15, 15, 15))
        w.setPageLayout(lay)
        doc.print_(w)
        return True
    except Exception as e:
        logger.error(f"PDF oluşturma hatası: {e}")
        return False
