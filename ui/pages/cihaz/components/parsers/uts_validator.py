# -*- coding: utf-8 -*-
"""
UTS Parser - HTML Validation & Parsing
=======================================
HTML sayfalarından veri çıkarma ve validasyon.
"""
from typing import Dict
from bs4 import BeautifulSoup

from core.logger import logger
from .uts_mapper import map_label_to_db


# ─────────────────────────────────────────────────────────────────────────────
# Modal HTML Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_uts_modal(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    Popup modal HTML'den veri çıkart.
    
    Args:
        soup: BeautifulSoup HTML object
        urun_no: Ürün numarası
    
    Returns:
        Çıkartılan field'lar
    """
    r: Dict[str, str] = {}

    logger.debug("Modal parsing başlıyor...")

    modal = soup.find("div", {"role": "dialog"})
    if not modal:
        modal = soup.find(class_=lambda x: x and "modal" in str(x).lower())
    if not modal:
        modal = soup

    # ── Div/Span yapısından çıkart ──────────────────────────────────────────────
    divs = modal.find_all("div")
    for div in divs:
        spans = div.find_all("span", limit=2)
        if len(spans) >= 2:
            label_text = spans[0].get_text(strip=True)
            value_text = spans[1].get_text(strip=True)

            if ":" in label_text:
                label = label_text.rstrip(":")
            else:
                label = label_text

            if label and value_text:
                map_label_to_db(r, label, value_text)
                logger.debug(f"  [div/span] {label} -> {value_text[:50]}")

    # ── DL/DT/DD yapısından çıkart ─────────────────────────────────────────────
    dts = modal.find_all("dt")
    for dt in dts:
        label = dt.get_text(strip=True)
        dd = dt.find_next("dd")
        if dd:
            value = dd.get_text(strip=True)
            if label and value:
                map_label_to_db(r, label, value)
                logger.debug(f"  [dt/dd] {label} -> {value[:50]}")

    # ── Tablo satırlarından çıkart ──────────────────────────────────────────────
    tables = modal.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)

                if label and value:
                    label = label.rstrip(":")
                    map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} -> {value[:50]}")

    # ── Metin satırlarından çıkart ──────────────────────────────────────────────
    text_content = modal.get_text()
    lines = [line.strip() for line in text_content.split("\n") if line.strip()]

    for line in lines:
        if ":" in line and len(line) < 200:
            parts = line.split(":", 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value = parts[1].strip()

                if (label and value and 
                    not any(x in label.lower() for x in ["bilgiler", "kodlari", "tarihi"])):
                    if 3 < len(label) < 100:
                        map_label_to_db(r, label, value)

    # ── Ürün adı (strong tag'den) ──────────────────────────────────────────────
    try:
        strong = modal.find("strong")
        if strong:
            product_name = strong.get_text(strip=True)
            if product_name and len(product_name) > 10:
                r["UrunAdi"] = product_name
                logger.debug(f"Ürün Adı bulundu (strong): {product_name}")
    except Exception:
        pass

    # ── Firma bilgisi (HEALTHCARE regex'i) ──────────────────────────────────────
    try:
        text = modal.get_text()
        if "SIEMENS HEALTHCARE" in text.upper():
            r["Firma"] = "Siemens Healthcare"
            logger.debug("Firma bulundu: Siemens Healthcare")
        elif "HEALTHCARE" in text.upper():
            import re
            match = re.search(r"(.*?HEALTHCARE.*? A\.?\s*Ş\.?)", text, re.IGNORECASE)
            if match:
                firma = match.group(1).strip()
                r["Firma"] = firma
                logger.debug(f"Firma bulundu (regex): {firma}")
    except Exception:
        pass

    logger.debug(f"Modal parse sonucu: {len(r)} alan bulundu")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Detail Panel Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_uts_detail(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    Detay paneli HTML'den veri çıkart.
    
    Args:
        soup: BeautifulSoup HTML object
        urun_no: Ürün numarası
    
    Returns:
        Çıkartılan field'lar
    """
    r: Dict[str, str] = {}

    panels = soup.find_all(
        ["div", "section"],
        class_=[
            "panel",
            "panel-body",
            "modal-body",
            "detail-panel",
            "info-panel",
        ],
    )
    if not panels:
        panels = soup.find_all("div")

    logger.debug(f"Panel/div sayısı: {len(panels)}")

    for panel in panels[:20]:
        # ── DT/DD'den çıkart ────────────────────────────────────────────────────
        dts = panel.find_all("dt")
        for dt in dts:
            label = dt.get_text(strip=True)
            dd = dt.find_next("dd")
            if dd:
                value = dd.get_text(strip=True)
                if label and value:
                    map_label_to_db(r, label, value)
                    logger.debug(f"  [dt/dd] {label} -> {value[:50]}")

        # ── label/value div'lerinden çıkart ────────────────────────────────────
        labels = panel.find_all("div", class_="label")
        for label_div in labels:
            label = label_div.get_text(strip=True)
            next_div = label_div.find_next("div", class_="value")
            if next_div:
                value = next_div.get_text(strip=True)
                if label and value:
                    map_label_to_db(r, label, value)
                    logger.debug(f"  [div label/value] {label} -> {value[:50]}")

        # ── Tablo satırlarından çıkart ─────────────────────────────────────────
        rows = panel.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                if label and value:
                    map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} -> {value[:50]}")

        # ── Metin satırlarından çıkart ─────────────────────────────────────────
        text = panel.get_text()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    label, value = parts
                    label = label.strip()
                    value = value.strip()
                    if label and value and len(label) < 100:
                        map_label_to_db(r, label, value)

    # ── Ürün adı arayış ────────────────────────────────────────────────────────
    urn_ad_candidates = [
        soup.find("strong"),
        soup.find("h3"),
        soup.find("h2"),
        soup.find(
            ["span", "div"],
            class_=["product-name", "urn-ad", "title", "main-title"],
        ),
    ]
    for cand in urn_ad_candidates:
        if cand:
            text = cand.get_text(strip=True)
            if text and 10 < len(text) < 200:
                r["UrunAdi"] = text
                logger.debug(f"Ürün Adı bulundu: {text}")
                break

    # ── Firma araması ────────────────────────────────────────────────────────────
    if "Firma" not in r:
        firma_text = soup.find(text=lambda t: t and "HEALTHCARE" in str(t).upper())
        if firma_text:
            parent = firma_text.parent.find_next(["div", "span", "td"])
            if parent:
                firma = parent.get_text(strip=True)
                r["Firma"] = firma
                logger.debug(f"Firma bulundu: {firma}")

    logger.debug(f"Detay parse sonucu: {len(r)} alan bulundu")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# HTML List Parsing (Fallback)
# ─────────────────────────────────────────────────────────────────────────────

def parse_uts_html(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    Liste tablosu HTML'den veri çıkart (fallback yöntemi).
    
    Args:
        soup: BeautifulSoup HTML object
        urun_no: Ürün numarası
    
    Returns:
        Çıkartılan field'lar
    """
    r: Dict[str, str] = {}

    logger.debug("HTML list parsing başlıyor (fallback)...")

    # ── Tablo satırlarından çıkart ─────────────────────────────────────────────
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)

                if value and label:
                    map_label_to_db(r, label, value)

    # ── Input/Select/Textarea'lardan çıkart ────────────────────────────────────
    inputs = soup.find_all(["input", "select", "textarea"])
    for inp in inputs:
        name = inp.get("name", "")
        value = inp.get("value", "") or inp.get_text(strip=True)
        if name and value:
            map_label_to_db(r, name, value)

    # ── Ürün numarası ekle (varsa) ──────────────────────────────────────────────
    if urun_no:
        r["UrunNo"] = urun_no

    logger.debug(f"HTML list parse sonucu: {len(r)} alan bulundu")
    return r
