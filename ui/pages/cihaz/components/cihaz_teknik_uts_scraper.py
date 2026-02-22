# -*- coding: utf-8 -*-
"""
Cihaz Teknik ÜTS Web Sorgulama - Playwright Tabanlı
───────────────────────────────────────────────────
Gerçek tarayıcı ile ÜTS sayfasından veri çeker,
HTML parse ederek veritabanına kaydeder.
"""
from __future__ import annotations
import json
import asyncio
import sys
from typing import Dict, Optional
from bs4 import BeautifulSoup

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QLineEdit,
    QMessageBox, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from core.logger import logger
from database.repository_registry import RepositoryRegistry

C = DarkTheme

_ACCENT    = getattr(C, "ACCENT",         "#4d9de0")
_BORDER    = getattr(C, "BORDER_PRIMARY", "#2d3f55")
_TEXT_PRI  = getattr(C, "TEXT_PRIMARY",   "#dce8f5")
_TEXT_SEC  = getattr(C, "TEXT_SECONDARY", "#7a93ad")
_SUCCESS   = "#4caf6e"
_WARNING   = "#e8a838"
_ERROR     = "#e05c5c"
_BG_SECT   = "rgba(255,255,255,0.03)"
_BG_HDR    = "rgba(77,157,224,0.18)"
_BG_SUBHDR = "rgba(77,157,224,0.09)"
_BG_EVEN   = "transparent"
_BG_ODD    = "rgba(255,255,255,0.04)"
_BC        = f"1px solid {_BORDER}"

_HDR_CSS = (
    f"background:{_BG_HDR};color:{_ACCENT};"
    "font-size:12px;font-weight:700;letter-spacing:.5px;"
    f"border-bottom:{_BC};padding:7px 14px;"
)
_SUBHDR_CSS = (
    f"background:{_BG_SUBHDR};color:{_ACCENT};"
    "font-size:11px;font-weight:600;font-style:italic;"
    f"border-top:{_BC};border-bottom:{_BC};padding:4px 14px;"
)
_LBL_CSS = f"color:{_TEXT_SEC};font-size:11px;font-weight:600;padding:6px 10px 6px 14px;"
_VAL_CSS = f"color:{_TEXT_PRI};font-size:12px;font-weight:400;padding:6px 14px 6px 0px;"
_INP_CSS = (
    f"QLineEdit{{background:rgba(255,255,255,.05);color:{_TEXT_PRI};"
    f"border:{_BC};border-radius:5px;padding:8px 12px;font-size:13px;}}"
    f"QLineEdit:focus{{border-color:{_ACCENT};background:rgba(77,157,224,.07);}}"
)
_BTN_P = (
    f"QPushButton{{background:{_ACCENT};color:#fff;border:none;border-radius:5px;"
    "font-size:12px;font-weight:700;padding:9px 22px;}}"
    "QPushButton:hover{background:#5eaee8;}"
    "QPushButton:disabled{background:#2d3f55;color:#55697a;}"
)
_BTN_S = (
    f"QPushButton{{background:transparent;color:{_TEXT_SEC};"
    f"border:{_BC};border-radius:5px;font-size:12px;font-weight:600;padding:9px 22px;}}"
    f"QPushButton:hover{{background:rgba(255,255,255,.06);color:{_TEXT_PRI};}}"
)

# ══════════════════════════════════════════════════════════════════════════════
#  ALAN FILTRELEME (Cihaz Kimligi.ini)
# ══════════════════════════════════════════════════════════════════════════════

_JSON_KEY_TO_DB_FIELD = {
    "markaAdi": "Marka",
    "versiyonModel": "Model",
    "urunTanimi": "UrunTanimi",
    "gmdnTerim.turkceAd": "GmdnTurkce",
    "gmdnTerim.turkceAciklama": "GmdnAciklama",
    "birincilUrunNumarasi": "UrunNo",
    "durum": "UrunDurum",
    "utsBaslangicTarihi": "UTSBaslangicTarihi",
    "ithalImalBilgisi": "IthalImalBilgisi",
    "menseiUlkeSet": "MenseiUlke",
    "baskaCihazinBilesenAksesuarYedekParcasiMi": "BilesenAksesuarMi",
    "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerirMi",
    "mrgUyumlu": "MRGGuvenlikBilgisi",
    "vucudaImplanteEdilebilirMi": "ImplanteEdilebilirMi",
    "tekKullanimlik": "TekKullanimlikMi",
    "tekHastayaKullanilabilir": "TekHastaKullanimMi",
    "kalibrasyonaTabiMi": "KalibrasyonaTabiMi",
    "kalibrasyonPeriyodu": "KalibrasyonPeriyoduAy",
    "bakimaTabiMi": "BakimaTabiMi",
    "bakimPeriyodu": "BakimPeriyoduAy",
    "kurum.unvan": "Firma",
    "kurum.eposta": "FirmaEmail",
    "belgeSet[0].turkceDokumanDosyaAdi": "UrunBelgeleri",
    "belgeSet[0].guncellemeTarihi": "UrunBelgeleri",
    "urunKunyesiDosyaAdi": "UrunKunye",
}


def _load_allowed_json_keys() -> set:
    import os

    ini_path = os.path.join(os.path.dirname(__file__), "🏷️ Cihaz Kimliği.ini")
    keys = set()
    try:
        with open(ini_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "JSON Karşılığı" in line:
                    continue
                if "\t" not in line:
                    continue
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) < 2:
                    continue
                json_key = parts[-1]
                if json_key:
                    keys.add(json_key)
    except Exception as e:
        logger.warning(f"Cihaz Kimligi ini okunamadi: {e}")
    return keys


def _load_allowed_db_fields() -> set:
    json_keys = _load_allowed_json_keys()
    if not json_keys:
        return set()
    return {db_field for key, db_field in _JSON_KEY_TO_DB_FIELD.items() if key in json_keys}


def _filter_allowed_fields(data: Dict[str, str], allowed: set) -> Dict[str, str]:
    if not allowed:
        return data
    return {k: v for k, v in data.items() if k in allowed}

# ══════════════════════════════════════════════════════════════════════════════
#  PLAYWRIGHT BROWSER SCRAPER
# ══════════════════════════════════════════════════════════════════════════════

_UTS_URL = "https://utsuygulama.saglik.gov.tr/UTS/vatandas"

def _yn(val) -> str:
    """Evet/Hayır dönüştür."""
    if val is None: return ""
    v = str(val).upper().strip()
    if v in ("EVET", "YES", "TRUE", "1"):
        return "Evet"
    elif v in ("HAYIR", "NO", "FALSE", "0"):
        return "Hayır"
    return str(val)


async def scrape_uts(urun_no: str) -> Dict[str, str]:
    """
    Playwright ile ÜTS web sayfasından ürün verisi çeker.
    Network API call'larını intercept ederek JSON response'ı yakalar.
    
    1. Tarayıcı aç
    2. ÜTS sayfasına git
    3. Network response'larını dinle
    4. Ürün numarası gir
    5. Sorgula
    6. API response JSON'ı yakala ve parse et
    """
    from playwright.async_api import async_playwright
    import os
    from datetime import datetime
    from core.paths import TEMP_DIR
    
    result = {}
    captured_json = None  # API response'ını buraya kaydet
    debug_dir = os.path.join(TEMP_DIR, "uts_debug")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        # Headless mode (ui görmez), timeout 60s
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        
        # Network response'larını yakala
        async def handle_response(response):
            nonlocal captured_json
            try:
                # Detay bilgi API call'larını ara
                if "detay" in response.url.lower() or "detail" in response.url.lower() or "tibbiCihazSorgula" in response.url:
                    if response.status == 200:
                        logger.debug(f"API Response yakalalandı: {response.url}")
                        try:
                            data = await response.json()
                            captured_json = data
                            logger.debug(f"JSON response parse edildi: {len(str(data))} byte")
                            
                            # JSON'ı dosyaya kaydet
                            json_file = os.path.join(debug_dir, f"uts_api_response_{timestamp}.json")
                            with open(json_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            logger.debug(f"API JSON kaydedildi: {json_file}")
                        except Exception as json_err:
                            logger.debug(f"Response JSON parse başarısız: {json_err}")
            except Exception as e:
                pass  # Silent fail
        
        page.on("response", handle_response)
        
        try:
            # ÜTS sayfasına git
            logger.debug(f"ÜTS sayfası açılıyor: {_UTS_URL}")
            await page.goto(_UTS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)  # Extra wait for JS rendering
            
            # Debug: Page content'ini logla
            page_content = await page.content()
            logger.debug(f"Sayfa yüklendi, byte: {len(page_content)}")
            
            # Debug: Screenshot al
            screenshot_path = os.path.join(debug_dir, f"uts_page_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            logger.debug(f"Screenshot kaydedildi: {screenshot_path}")
            
            # Debug: Tüm input'ları listele
            all_inputs = await page.query_selector_all("input")
            logger.debug(f"Sayfa üzerinde {len(all_inputs)} adet input bulundu")
            for i, inp in enumerate(all_inputs):
                inp_id = await inp.get_attribute("id")
                inp_name = await inp.get_attribute("name")
                inp_type = await inp.get_attribute("type")
                inp_visible = await inp.is_visible()
                logger.debug(f"  Input {i}: id={inp_id}, name={inp_name}, type={inp_type}, visible={inp_visible}")
            
            # Debug: IFrame'leri kontrol et
            iframes = await page.query_selector_all("iframe")
            logger.debug(f"Sayfa üzerinde {len(iframes)} adet iframe bulundu")
            for i, iframe in enumerate(iframes):
                iframe_id = await iframe.get_attribute("id")
                iframe_name = await iframe.get_attribute("name")
                iframe_src = await iframe.get_attribute("src")
                logger.debug(f"  IFrame {i}: id={iframe_id}, name={iframe_name}, src={iframe_src[:80] if iframe_src else None}")
            
            # Ürün no input'unu bul - daha aggressive approach
            search_input = None
            
            # Farklı selector'ları dene - VISİBLE olanları tercih et
            selectors = [
                "input[placeholder*='Ürün']",
                "input[placeholder*='ürün']",
                "input[id*='urun']",
                "input[id*='Urun']",
                "input[name*='urun']",
                "input[name*='Urun']",
                "input[id='txtUrunNo']",
                "input[id='UrunNo']",
                "input[type='text']:not([type='hidden'])",
                "input:visible",
            ]
            
            for selector in selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            search_input = elem
                            logger.debug(f"✓ Input bulundu (görünür): {selector}")
                            break
                        else:
                            # CSS compute edip neden gizli olduğunu kontrol et
                            try:
                                compute_result = await page.evaluate(f"""
                                    (() => {{
                                        const elem = document.querySelector('{selector}');
                                        if (!elem) return 'element not found';
                                        const style = window.getComputedStyle(elem);
                                        return {{
                                            display: style.display,
                                            visibility: style.visibility,
                                            opacity: style.opacity,
                                            height: style.height,
                                            width: style.width
                                        }};
                                    }})()
                                """)
                                logger.debug(f"✗ Input gizli: {selector} -> CSS: {compute_result}")
                            except Exception as css_err:
                                logger.debug(f"✗ Input bulundu ama gizli: {selector} (CSS check başarısız: {css_err})")
                except Exception as e:
                    logger.debug(f"✗ Selector test başarısız: {selector} -> {e}")
            
            if not search_input:
                # Tüm input'ları ele al, hatta gizlileri de
                all_inputs = await page.query_selector_all("input")
                if all_inputs:
                    search_input = all_inputs[0]
                    logger.warning(f"Visible input bulunamadı, ilk input kullanılıyor")
                else:
                    raise RuntimeError("ÜTS sayfasında hiç input bulunmadı.")
            
            # Input'a ürün no yaz - Visible/Enabled check ile
            try:
                await search_input.fill(urun_no, force=True)
                logger.debug(f"Ürün no yazıldı (fill): {urun_no}")
            except Exception as e:
                logger.warning(f"fill() başarısız: {e}")
                try:
                    # JavaScript ile direkt value set et
                    logger.debug("JavaScript ile input value set ediliyor...")
                    await page.evaluate(f"""
                        document.querySelectorAll('input').forEach(inp => {{
                            inp.value = '{urun_no}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }});
                    """)
                    logger.debug(f"Ürün no yazıldı (JS): {urun_no}")
                except Exception as js_err:
                    logger.warning(f"JS setValue başarısız, type() deneniyor: {js_err}")
                    try:
                        await search_input.type(urun_no, delay=50)
                        logger.debug(f"Ürün no yazıldı (type): {urun_no}")
                    except Exception as type_err:
                        raise RuntimeError(f"Input doldurma başarısız (fill, JS, type hepsi denendi): {type_err}")
            
            await page.wait_for_timeout(500)  # Biraz bekle
            
            # Sorgula butonuna tıkla - detaylı debug ile
            logger.debug("Submit button aranıyor...")
            
            # Debug: Tüm button'ları listele
            all_buttons = await page.query_selector_all("button")
            logger.debug(f"Sayfa üzerinde {len(all_buttons)} adet button bulundu")
            for i, btn in enumerate(all_buttons):
                btn_text = await btn.inner_text()
                btn_visible = await btn.is_visible()
                logger.debug(f"  Button {i}: text='{btn_text}', visible={btn_visible}")
            
            submit_btn = None
            button_selectors = [
                "button:text('Sorgula')",
                "button:text('Ara')",
                "button:text('Search')",
                "button:has-text('Sorgula')",
                "button:has-text('Ara')",
                "button[type='submit']",
            ]
            
            for selector in button_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        is_visible = await elem.is_visible()
                        is_enabled = await elem.is_enabled()
                        if is_visible and is_enabled:
                            submit_btn = elem
                            logger.debug(f"✓ Button bulundu: {selector}")
                            break
                        else:
                            logger.debug(f"✗ Button bulundu ama (visible={is_visible}, enabled={is_enabled}): {selector}")
                except Exception as e:
                    logger.debug(f"✗ Button selector başarısız: {selector} -> {e}")
            
            if submit_btn:
                try:
                    await submit_btn.click()
                    logger.debug("Button tıklandı")
                    # Sonuç sayfasının yüklenmesini bekle
                    await page.wait_for_timeout(1000)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(1500)
                    
                    # Sonuç tablosundan ilk satırın barcode/ID hücresini tıkla (popup açmak için)
                    logger.debug("Sonuç tablosundan ilk ürünün barcode'una tıklanıyor...")
                    
                    # Tablo satırlarını ara
                    rows = await page.query_selector_all("table tbody tr, table tr[role='row'], tr[data-id], tr.row")
                    logger.debug(f"Tabloda {len(rows)} satır bulundu")
                    
                    if rows:
                        try:
                            first_row = rows[0]
                            
                            # İlk satırın ilk hücresini bul (barcode/ID)
                            first_cell = await first_row.query_selector("td:first-child, td:nth-child(1)")
                            
                            if first_cell:
                                # Hücre içinde tıklanabilir element var mı? (link, number vb)
                                clickable = await first_cell.query_selector("a, span[style*='cursor'], [data-id], .barcode, .product-id")
                                
                                if clickable:
                                    logger.debug("Barcode hücresinde tıklanabilir element bulundu, tıklanıyor...")
                                    await clickable.click()
                                else:
                                    # Hücrenin kendisine tıkla
                                    logger.debug("Barcode hücresine tıklanıyor...")
                                    await first_cell.click()
                            else:
                                # Hücre bulamazsan satırın kendisine tıkla
                                logger.debug("Satırın kendisine tıklanıyor...")
                                await first_row.click()
                            
                            # Popup/Modal açılmasını bekle
                            logger.debug("Popup açılması bekleniyor...")
                            await page.wait_for_timeout(500)
                            
                            # Modal açıldı mı kontrol et
                            modal_selectors = [
                                "div[role='dialog']",
                                ".modal",
                                ".panel-modal",
                                "div.modal-dialog",
                                "div[class*='modal']",
                                "div[class*='popup']",
                            ]
                            
                            modal_found = False
                            for selector in modal_selectors:
                                try:
                                    modal = await page.query_selector(selector)
                                    if modal and await modal.is_visible():
                                        logger.debug(f"✓ Modal bulundu: {selector}")
                                        modal_found = True
                                        break
                                except:
                                    pass
                            
                            if modal_found:
                                await page.wait_for_timeout(1500)
                                logger.debug("Popup açıldı ve yüklendi")
                            else:
                                logger.warning("Modal/Popup açılmış gibi gözükmüyor, devam ediliyor...")
                                await page.wait_for_timeout(1500)
                            
                        except Exception as detail_err:
                            logger.warning(f"Popup açma başarısız: {detail_err}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    else:
                        logger.warning("Sonuç tablosunda satır bulunamadı!")
                        
                except Exception as e:
                    logger.warning(f"Button click başarısız: {e}")
                    logger.warning("Enter tuşu deneniyor...")
                    await search_input.press("Enter")
                    await page.wait_for_timeout(1000)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(1500)
                    
                    # Enter sonrası da popup açmayı dene
                    rows = await page.query_selector_all("table tbody tr, table tr[role='row'], tr[data-id], tr.row")
                    if rows:
                        try:
                            first_row = rows[0]
                            first_cell = await first_row.query_selector("td:first-child, td:nth-child(1)")
                            if first_cell:
                                clickable = await first_cell.query_selector("a, span[style*='cursor'], [data-id]")
                                if clickable:
                                    await clickable.click()
                                else:
                                    await first_cell.click()
                            else:
                                await first_row.click()
                            await page.wait_for_timeout(1500)
                        except Exception as retry_err:
                            logger.warning(f"Enter sonrası popup açma başarısız: {retry_err}")
            else:
                # Button yoksa Enter tuşuna bas
                logger.warning("Button bulunamadı, Enter tuşu kullanılıyor")
                await search_input.press("Enter")
                await page.wait_for_timeout(1000)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1500)
                
                # Sonuç tablosundan ilk satırı bul ve tıkla (Enter yolu)
                rows = await page.query_selector_all("table tbody tr, table tr[role='row'], tr[data-id], tr.row")
                logger.debug(f"Tabloda {len(rows)} satır bulundu (Enter yolu)")
                
                if rows:
                    try:
                        first_row = rows[0]
                        first_cell = await first_row.query_selector("td:first-child, td:nth-child(1)")
                        
                        if first_cell:
                            clickable = await first_cell.query_selector("a, span[style*='cursor'], [data-id]")
                            if clickable:
                                logger.debug("Barcode hücresinde tıklanabilir element bulundu, tıklanıyor...")
                                await clickable.click()
                            else:
                                logger.debug("Barcode hücresine tıklanıyor...")
                                await first_cell.click()
                        else:
                            logger.debug("Satırın kendisine tıklanıyor...")
                            await first_row.click()
                        
                        await page.wait_for_timeout(1500)
                        logger.debug("Popup açılmış olmalı (Enter yolu)")
                    except Exception as detail_err:
                        logger.warning(f"Popup açma başarısız (Enter yolu): {detail_err}")
            
            # Debug: Modal/popup sayfasının screenshot'ını al
            result_screenshot = os.path.join(debug_dir, f"uts_modal_{timestamp}.png")
            await page.screenshot(path=result_screenshot)
            logger.debug(f"Modal sayfası screenshot'ı: {result_screenshot}")
            
            # Sayfanın HTML içeriğini al (popup/modal HTML'si)
            detail_html = await page.content()
            detail_soup = BeautifulSoup(detail_html, "html.parser")
            logger.debug(f"Modal HTML parse edildi, byte: {len(detail_html)}")
            
            # HTML'yi her zaman kaydet debug için
            html_file = os.path.join(debug_dir, f"uts_modal_{timestamp}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(detail_html)
            logger.debug(f"Modal HTML kaydedildi: {html_file}")
            
            # ÖNCE API JSON response'dan parse et (en zengin veri kaynağı)
            if captured_json:
                logger.debug(f"🔍 API JSON response'ından veri çekiliyor...")
                result = _parse_uts_api_response(captured_json, urun_no)
                if result and any(result.values()):
                    logger.info(f"✅ API JSON'dan başarıyla {len(result)} alan çıkartıldı")
                else:
                    logger.warning(f"API JSON parse edildi ama alan bulunamadı")
            else:
                logger.warning(f"API JSON yakalanmadı, HTML parse'a geçiliyor...")
                result = {}
            
            # Fallback 1: Modal HTML parse (eğer JSON yoksa veya boşsa)
            if not result or not any(result.values()):
                logger.debug(f"Fallback: Modal HTML'den veri çekiliyor...")
                result = _parse_uts_modal(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"✓ HTML modal'dan başarıyla {len(result)} alan çıkartıldı")
            
            # Fallback 2: Detay HTML parse
            if not result or not any(result.values()):
                logger.debug(f"Fallback: HTML detail'den veri çekiliyor...")
                result = _parse_uts_detail(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"✓ HTML detailed'dan başarıyla {len(result)} alan çıkartıldı")
            
            # Fallback 3: Liste tablosu parse
            if not result or not any(result.values()):
                logger.warning(f"Fallback: Liste tablosundan çek...")
                result = _parse_uts_html(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"✓ HTML list'ten başarıyla {len(result)} alan çıkartıldı")
            
            if not result or not any(result.values()):
                logger.warning(f"❌ Tüm parse yöntemleri başarısız")
            
            # Meta bilgiler ekle
            if captured_json:
                result["_raw_json"] = json.dumps(captured_json)[:1000]
            else:
                result["_raw_json"] = detail_html[:1000]  # HTML'den ilk 1000 char
            result["_item_count"] = "1"
            
            logger.debug(f"ÜTS çekme başarılı: {len(result)} alan")
            
        except Exception as e:
            import traceback
            logger.error(f"ÜTS scraping hatası: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"ÜTS veri çekme hatası:\n{e}")
        finally:
            await context.close()
            await browser.close()
    
    return result


def _parse_uts_api_response(api_response: dict, urun_no: str) -> Dict[str, str]:
    """
    ÜTS API JSON response'ından veri çıkar.
    Doğru field mapping'lerle parse et.
    """
    r: Dict[str, str] = {}
    
    if not api_response or "data" not in api_response:
        logger.warning("API response yapısı hatalı (data array yok)")
        return r
    
    data_array = api_response.get("data", [])
    if not data_array or not isinstance(data_array, list):
        logger.warning(f"Data array boş veya hatalı (tip: {type(data_array)})")
        return r
    
    item = data_array[0]
    if not isinstance(item, dict):
        logger.warning("Data item dict değil")
        return r
    
    logger.debug(f"API JSON parse başlıyor (item keys: {len(item)})")
    
    # === TEMEL ÜRÜN BİLGİLERİ ===
    if "markaAdi" in item:
        val = item["markaAdi"]
        if val and isinstance(val, str):
            r["Marka"] = val.strip()
            logger.debug(f"✓ Marka: {val}")
    
    if "etiketAdi" in item:
        val = item["etiketAdi"]
        if val and isinstance(val, str):
            r["UrunAdi"] = val.strip()
            logger.debug(f"✓ UrunAdi: {val[:60]}")
    
    if "urunTanimi" in item:
        val = item["urunTanimi"]
        if val and isinstance(val, str):
            r["UrunTanimi"] = val.strip()
            logger.debug(f"✓ UrunTanimi: {val[:60]}")
    
    if "versiyonModel" in item:
        val = item["versiyonModel"]
        if val and isinstance(val, str):
            r["Model"] = val.strip()
            logger.debug(f"✓ Model: {val}")
    
    if "urunTipi" in item:
        val = item["urunTipi"]
        if val and isinstance(val, str):
            r["UrunTipi"] = val.strip()
            logger.debug(f"✓ UrunTipi: {val}")
    
    # === FIRMA/KURUM BİLGİLERİ ===
    if "kurum" in item and isinstance(item["kurum"], dict):
        kurum = item["kurum"]
        
        if "unvan" in kurum and kurum["unvan"]:
            r["Firma"] = kurum["unvan"].strip()
            logger.debug(f"✓ Firma: {kurum['unvan']}")
        
        if "kurumNo" in kurum and kurum["kurumNo"]:
            r["FirmaNo"] = str(kurum["kurumNo"])
            logger.debug(f"✓ FirmaNo: {kurum['kurumNo']}")
        
        if "telefon" in kurum and kurum["telefon"]:
            r["FirmaTelefon"] = kurum["telefon"]
            logger.debug(f"✓ FirmaTelefon: {kurum['telefon']}")
        
        if "eposta" in kurum and kurum["eposta"]:
            r["FirmaEmail"] = kurum["eposta"]
            logger.debug(f"✓ FirmaEmail: {kurum['eposta']}")
        
        if "durum" in kurum and kurum["durum"]:
            r["FirmaDurum"] = kurum["durum"]
            logger.debug(f"✓ FirmaDurum: {kurum['durum']}")
    
    # === SINIFLANDIRMA ===
    if "sinif" in item:
        val = item["sinif"]
        if val and isinstance(val, str):
            # SINIF_II_B → Sınıf-IIb (cleaning)
            sinif_clean = val.replace("SINIF_", "Sınıf-").replace("_", "")
            r["Sinif"] = sinif_clean
            logger.debug(f"✓ Sinif: {sinif_clean}")
    
    # === GMDN BİLGİLERİ ===
    if "gmdnTerim" in item and isinstance(item["gmdnTerim"], dict):
        gmdn = item["gmdnTerim"]
        
        if "kod" in gmdn and gmdn["kod"]:
            r["GmdnKod"] = str(gmdn["kod"])
            logger.debug(f"✓ GmdnKod: {gmdn['kod']}")
        
        if "turkceAd" in gmdn and gmdn["turkceAd"]:
            r["GmdnTurkce"] = gmdn["turkceAd"]
            logger.debug(f"✓ GmdnTurkce: {gmdn['turkceAd'][:60]}")

        if "turkceAciklama" in gmdn and gmdn["turkceAciklama"]:
            r["GmdnAciklama"] = gmdn["turkceAciklama"]
            logger.debug(f"✓ GmdnAciklama: {gmdn['turkceAciklama'][:60]}")
        
        if "ingilizceAd" in gmdn and gmdn["ingilizceAd"]:
            r["GmdnIngilizce"] = gmdn["ingilizceAd"]
            logger.debug(f"✓ GmdnIngilizce: {gmdn['ingilizceAd'][:60]}")
    
    # === TEKNİK ÖZELLİKLER (EVET/HAYIR) ===
    yes_no_fields = {
        "kalibrasyonaTabiMi": "KalibrasyonaTabiMi",
        "bakimaTabiMi": "BakimaTabiMi",
        "latexIceriyor": "LateksIceriyorMu",
        "dehpIceriyor": "FtalatDEHPIceriyorMu",
        "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerirMi",
        "nanomateryalIceriyor": "NanomateryalIceriyorMu",
        "sterilPaketlendi": "SterilPaketlendiMi",
        "vucudaImplanteEdilebilirMi": "ImplanteEdilebilirMi",
        "tekKullanimlik": "TekKullanimlikMi",
        "tekHastayaKullanilabilir": "TekHastaKullanimMi",
        "baskaCihazinBilesenAksesuarYedekParcasiMi": "BilesenAksesuarMi",
        "sistemdeTekilUrunuVarMi": "TekilUrunVarMi",
        "saklamaKosuluGerektiriyorMu": "SaklamaKosuluVar",
    }
    
    for json_field, db_field in yes_no_fields.items():
        if json_field in item:
            val = item[json_field]
            if val and isinstance(val, str):
                # EVET → Evet, HAYIR → Hayır
                result = _yn(val)
                if result:
                    r[db_field] = result
                    logger.debug(f"✓ {db_field}: {result}")
    
    # === TARİHLER ===
    # UTSBaslangicTarihi zaten "dd/MM/yyyy" formatında
    if "utsBaslangicTarihi" in item:
        val = item["utsBaslangicTarihi"]
        if val and isinstance(val, str):
            r["UTSBaslangicTarihi"] = val
            logger.debug(f"✓ UTSBaslangicTarihi: {val}")
    
    # DurumTarihi zaten "dd/MM/yyyy" formatında
    if "durumTarihi" in item:
        val = item["durumTarihi"]
        if val and isinstance(val, str):
            r["DurumTarihi"] = val
            logger.debug(f"✓ DurumTarihi: {val}")
    
    if "kontroleGonderildigiTarih" in item:
        val = item["kontroleGonderildigiTarih"]
        if val and isinstance(val, str):
            r["KontrolTarihi"] = val
            logger.debug(f"✓ KontrolTarihi: {val}")
    
    # creationDate ve updateDate (epoch milliseconds → ISO format)
    if "creationDate" in item and item["creationDate"]:
        from datetime import datetime
        try:
            epoch_ms = int(item["creationDate"])
            dt = datetime.fromtimestamp(epoch_ms / 1000.0)
            r["OlusturmaTarihi"] = dt.strftime("%d/%m/%Y")
            logger.debug(f"✓ OlusturmaTarihi: {r['OlusturmaTarihi']}")
        except:
            pass
    
    if "updateDate" in item and item["updateDate"]:
        from datetime import datetime
        try:
            epoch_ms = int(item["updateDate"])
            dt = datetime.fromtimestamp(epoch_ms / 1000.0)
            r["GuncellemeTarihi"] = dt.strftime("%d/%m/%Y")
            logger.debug(f"✓ GuncellemeTarihi: {r['GuncellemeTarihi']}")
        except:
            pass
    
    # === DİĞER ALANLAR ===
    if "ithalImalBilgisi" in item:
        val = item["ithalImalBilgisi"]
        if val and isinstance(val, str):
            r["IthalImalBilgisi"] = val
            logger.debug(f"✓ IthalImalBilgisi: {val}")

    if "menseiUlkeSet" in item and item["menseiUlkeSet"]:
        val = item["menseiUlkeSet"]
        if isinstance(val, list):
            val = ", ".join([str(v) for v in val if v])
        if val:
            r["MenseiUlke"] = str(val)
            logger.debug(f"✓ MenseiUlke: {val}")
    
    if "durum" in item:
        val = item["durum"]
        if val and isinstance(val, str):
            r["UrunDurum"] = val
            logger.debug(f"✓ UrunDurum: {val}")
    
    if "birincilUrunNumarasi" in item:
        val = item["birincilUrunNumarasi"]
        if val:
            r["UrunNo"] = str(val)
            logger.debug(f"✓ UrunNo: {val}")

    if "urunKunyesiDosyaAdi" in item and item["urunKunyesiDosyaAdi"]:
        val = item["urunKunyesiDosyaAdi"]
        r["UrunKunye"] = str(val)
        logger.debug(f"✓ UrunKunye: {val}")

    if "belgeSet" in item and isinstance(item["belgeSet"], list) and item["belgeSet"]:
        doc = item["belgeSet"][0]
        if isinstance(doc, dict):
            doc_name = doc.get("turkceDokumanDosyaAdi")
            doc_date = doc.get("guncellemeTarihi")
            doc_val = ""
            if doc_name:
                doc_val = str(doc_name)
            if doc_date:
                doc_val = f"{doc_val} | Guncelleme: {doc_date}" if doc_val else f"Guncelleme: {doc_date}"
            if doc_val:
                r["UrunBelgeleri"] = doc_val
                logger.debug(f"✓ UrunBelgeleri: {doc_val}")
    
    if "basvuruyaHazirMi" in item and item["basvuruyaHazirMi"] is not None:
        val = "Evet" if item["basvuruyaHazirMi"] else "Hayır"
        r["BasvuruHazir"] = val
        logger.debug(f"✓ BasvuruHazir: {val}")
    
    if "cihazKayitTipi" in item and item["cihazKayitTipi"]:
        r["KayitTipi"] = item["cihazKayitTipi"]
        logger.debug(f"✓ KayitTipi: {item['cihazKayitTipi']}")
    
    if "rafOmru" in item and item["rafOmru"]:
        r["RafOmruDegeri"] = str(item["rafOmru"])
        logger.debug(f"✓ RafOmruDegeri: {item['rafOmru']}")
    
    if "rafOmruVar" in item and item["rafOmruVar"]:
        result = _yn(item["rafOmruVar"])
        if result:
            r["RafOmruVarMi"] = result
            logger.debug(f"✓ RafOmruVarMi: {result}")
    
    # === PERIYODLAR ===
    if "kalibrasyonPeriyodu" in item and item["kalibrasyonPeriyodu"]:
        val = item["kalibrasyonPeriyodu"]
        r["KalibrasyonPeriyoduAy"] = str(val)
        logger.debug(f"✓ KalibrasyonPeriyoduAy: {val} ay")
    
    if "bakimPeriyodu" in item and item["bakimPeriyodu"]:
        val = item["bakimPeriyodu"]
        r["BakimPeriyoduAy"] = str(val)
        logger.debug(f"✓ BakimPeriyoduAy: {val} ay")
    
    # === MRG ===
    if "mrgUyumlu" in item and item["mrgUyumlu"]:
        val = item["mrgUyumlu"]
        r["MRGGuvenlikBilgisi"] = val
        logger.debug(f"✓ MRGGuvenlikBilgisi: {val}")
    
    logger.info(f"✓✓✓ API JSON parse tamamlandı: {len(r)} alan başarıyla eklendi")
    return r



def _parse_uts_modal(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    ÜTS Modal/Popup panelinin HTML'inden veri çıkar.
    
    Struktur:
    - "Tanımlayıcı Bilgiler" (sol panel) + "Durum Bilgileri" (sağ panel)
    - "Sınıflandırma Bilgileri"
    - "İthal/İmal Bilgileri"
    - "SUT Kodları"
    
    Her bölüm altında label: value formatında veya tablosu var.
    """
    r: Dict[str, str] = {}
    
    logger.debug("Modal parsing başlıyor...")
    
    # Modal container'ı bul
    modal = soup.find("div", {"role": "dialog"})
    if not modal:
        modal = soup.find(class_=lambda x: x and "modal" in str(x).lower())
    if not modal:
        modal = soup  # Fallback olarak tüm soup'u kullan
    
    # Başlıklar (Tanımlayıcı Bilgiler, Durum Bilgileri, vb.) tarafından bölümlere ayır
    # Her bölümün altında label-value pair'leri var
    
    # Farklı label-value yapılarını ara
    
    # 1. DIV struktur: <div><span class="label">Label:</span><span class="value">Value</span></div>
    divs = modal.find_all("div")
    for div in divs:
        spans = div.find_all("span", limit=2)
        if len(spans) >= 2:
            label_text = spans[0].get_text(strip=True)
            value_text = spans[1].get_text(strip=True)
            
            # Label'da ":" varsa ayır
            if ":" in label_text:
                label = label_text.rstrip(":")
            else:
                label = label_text
            
            if label and value_text:
                _map_label_to_db(r, label, value_text)
                logger.debug(f"  [div/span] {label} → {value_text[:50]}")
    
    # 2. DL struktur: <dt>Label</dt><dd>Value</dd>
    dts = modal.find_all("dt")
    for dt in dts:
        label = dt.get_text(strip=True)
        dd = dt.find_next("dd")
        if dd:
            value = dd.get_text(strip=True)
            if label and value:
                _map_label_to_db(r, label, value)
                logger.debug(f"  [dt/dd] {label} → {value[:50]}")
    
    # 3. TR yapısı: <tr><td class="label">Label</td><td class="value">Value</td></tr>
    tables = modal.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                
                if label and value:
                    # Label'da ":" varsa kaldır
                    label = label.rstrip(":")
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} → {value[:50]}")
    
    # 4. Basit "Label: Value" text pattern
    text_content = modal.get_text()
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    for line in lines:
        if ':' in line and len(line) < 200:  # Çok uzun satırları atla
            parts = line.split(':', 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value = parts[1].strip()
                
                # Bu şekilde label'lar genellikle iyi belirlenir
                if label and value and not any(x in label.lower() for x in ['bilgiler', 'kodları', 'tarihi']):
                    # Section header'ları skip et ("Tanımlayıcı Bilgileri" gibi)
                    if len(label) > 3 and len(label) < 100:
                        _map_label_to_db(r, label, value)
                        # logger.debug(f"  [text line] {label} → {value[:50]}")
    
    # 5. Ürün Adı - Modal'ın başında bold veya büyük yazı olarak
    try:
        strong = modal.find("strong")
        if strong:
            product_name = strong.get_text(strip=True)
            if product_name and len(product_name) > 10:
                r["UrunAdi"] = product_name
                logger.debug(f"Ürün Adı bulundu (strong): {product_name}")
    except:
        pass
    
    # 6. Firma - "HEALTHCARE" pattern'i ara
    try:
        text = modal.get_text()
        if "SIEMENS HEALTHCARE" in text.upper():
            r["Firma"] = "Siemens Healthcare"
            logger.debug("Firma bulundu: Siemens Healthcare")
        elif "HEALTHCARE" in text.upper():
            # HTML'de "HEALTHCARE SAGLIK A.Ş." pattern'i ara
            import re
            match = re.search(r'(.*?HEALTHCARE.*? A\.?\s*Ş\.?)', text, re.IGNORECASE)
            if match:
                firma = match.group(1).strip()
                r["Firma"] = firma
                logger.debug(f"Firma bulundu (regex): {firma}")
    except:
        pass
    
    logger.debug(f"Modal parse sonucu: {len(r)} alan bulundu")
    return r


def _parse_uts_detail(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    ÜTS detay panelinin HTML'inden veri çıkar.
    
    Modal/Panel içindeki bilgileri parse eder.
    Yapı: Label (Türkçe) → Değer
    """
    r: Dict[str, str] = {}
    
    # Farklı panel/modal selector'ları dene
    panels = soup.find_all(["div", "section"], class_=["panel", "panel-body", "modal-body", "detail-panel", "info-panel"])
    if not panels:
        # Class olmayan div'leri de dene
        panels = soup.find_all("div")
    
    logger.debug(f"Panel/div sayısı: {len(panels)}")
    
    # Tüm text node'ları ve label-value pair'lerini ara
    for panel in panels[:20]:  # İlk 20 paneli kontrol et
        # dt/dd yapısını ara
        dts = panel.find_all("dt")
        for dt in dts:
            label = dt.get_text(strip=True)
            dd = dt.find_next("dd")
            if dd:
                value = dd.get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [dt/dd] {label} → {value[:50]}")
        
        # div.labelproperty yapısını ara (label + değer)
        # Örnek: <div class="label">Ürün Adı</div><div class="value">...</div>
        labels = panel.find_all("div", class_="label")
        for label_div in labels:
            label = label_div.get_text(strip=True)
            # Sonraki value div'ini bul
            next_div = label_div.find_next("div", class_="value")
            if next_div:
                value = next_div.get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [div label/value] {label} → {value[:50]}")
        
        # tr > td yapısını ara (table format)
        rows = panel.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} → {value[:50]}")
        
        # Basit text kır yapısını ara: "Label: Değer"
        text = panel.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    label, value = parts
                    label = label.strip()
                    value = value.strip()
                    if label and value and len(label) < 100:  # Label çok uzun olmasın
                        _map_label_to_db(r, label, value)
    
    # Ürün Adı alanını özel olarak ara
    try:
        # Ürün Adı genellikle kalın veya önemli
        urn_ad_candidates = [
            soup.find("strong"),
            soup.find("h3"),
            soup.find("h2"),
            soup.find(["span", "div"], class_=["product-name", "urn-ad", "title", "main-title"])
        ]
        for cand in urn_ad_candidates:
            if cand:
                text = cand.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 200:
                    r["UrunAdi"] = text
                    logger.debug(f"Ürün Adı bulundu: {text}")
                    break
    except:
        pass
    
    # Firma adı ara
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


def _parse_uts_html(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    """
    ÜTS sonuç sayfasının HTML'inden veri çıkar.
    
    Tipik ÜTS sayfası yapısı:
    - Ana bilgiler tablosu
    - Sınıflandırma
    - İthal/İmal info
    - Teknik özellikler
    - Belgeler vs.
    """
    r: Dict[str, str] = {}
    
    # Tüm tabloları bul
    tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                
                # Boş olmayan değerleri al
                if value and label:
                    # Türkçe etiketi DB schema'sına map et
                    _map_label_to_db(r, label, value)
    
    # Input alanlarından da değer çek (eğer varsa)
    inputs = soup.find_all(["input", "select", "textarea"])
    for inp in inputs:
        name = inp.get("name", "")
        value = inp.get("value", "") or inp.get_text(strip=True)
        if name and value:
            _map_label_to_db(r, name, value)
    
    # Dummy test: urun_no'yu set et
    if urun_no:
        r["UrunNo"] = urun_no
    
    return r


def _map_label_to_db(data: dict, label: str, value: str) -> None:
    """Türkçe etiket → DB şema field mapper."""
    label_upper = label.upper().strip()
    value = str(value).strip()
    
    if not value:
        return
    
    # Eşleştirme tablosu
    mapping = {
        "ÜRÜN ADI": "UrunAdi",
        "MARKA": "Marka",
        "MODEL": "UrunAdi",
        "FIRMA": "Firma",
        "SIRAÇ": "Sinif",
        "SINIF": "Sinif",
        "GMDN KODU": "GmdnKod",
        "GMDN TERİMİ": "GmdnTurkce",
        "İTHAL/İMAL": "IthalImalBilgisi",
        "MENŞEI ÜLKE": "MenseiUlke",
        "STERIL": "SterilPaketlendiMi",
        "TEK KULLANIM": "TekKullanimlikMi",
        "KALİBRASYON": "KalibrasyonaTabiMi",
        "BAKIM": "BakimaTabiMi",
        "LATEKS": "LateksIceriyorMu",
        "FTALAT": "FtalatDEHPIceriyorMu",
        "RADYASYON": "IyonizeRadyasyonIcerirMi",
        "NANOMAT": "NanomateryalIceriyorMu",
        "MRG": "MRGGuvenlikBilgisi",
        "İMPLANT": "ImplanteEdilebilirMi",
    }
    
    for key, db_field in mapping.items():
        if key in label_upper:
            data[db_field] = _yn(value)
            return
    
    # Eşleşme yoksa generic olarak ekle
    # (veya ihtiyaca göre filter et)



# ══════════════════════════════════════════════════════════════════════════════
#  QThread Worker - Async Event Loop entegrasyonu
# ══════════════════════════════════════════════════════════════════════════════

class _Worker(QObject):
    """QThread içinde async Playwright scraper çalıştırır."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, urun_no: str):
        super().__init__()
        self.urun_no = urun_no

    def run(self):
        """Async scraper'ı QThread içinde çalıştır."""
        try:
            # Windows'ta Playwright subprocess desteği için ProactorEventLoop gerekli
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            # Event loop oluştur ve async fonksiyon çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(scrape_uts(self.urun_no))
            loop.close()
            
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Scraper hatası: {e}")
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  UI Yardımcıları
# ══════════════════════════════════════════════════════════════════════════════

def _mk_pair(lbl_txt, val, bg):
    w = QWidget(); w.setStyleSheet(f"background:{bg};")
    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0); h.setSpacing(6)
    l = QLabel(lbl_txt)
    l.setStyleSheet(_LBL_CSS + f"background:{bg};")
    l.setWordWrap(True); l.setMinimumWidth(160)
    l.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
    val.setStyleSheet(val.styleSheet() + f"background:{bg};")
    val.setWordWrap(True)
    h.addWidget(l); h.addWidget(val, stretch=1)
    return w


class _Sec(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._r = 0
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self._frame = QFrame()
        self._frame.setStyleSheet(
            f"QFrame{{border:{_BC};border-radius:4px;background:{_BG_SECT};}}"
        )
        self._vb = QVBoxLayout(self._frame)
        self._vb.setContentsMargins(0,0,0,0); self._vb.setSpacing(0)
        h = QLabel(title); h.setStyleSheet(_HDR_CSS)
        self._vb.addWidget(h); outer.addWidget(self._frame)

    def subhdr(self, t):
        s = QLabel(t); s.setStyleSheet(_SUBHDR_CSS)
        self._vb.addWidget(s); self._r = 0

    def row(self, l1, v1, l2="", v2=None):
        bg = _BG_ODD if self._r % 2 else _BG_EVEN; self._r += 1
        rw = QWidget()
        rw.setStyleSheet(f"background:{bg};border-bottom:{_BC};")
        rw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        rh = QHBoxLayout(rw); rh.setContentsMargins(0,0,0,0); rh.setSpacing(0)
        rh.addWidget(_mk_pair(l1, v1, bg), stretch=1)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine); sep.setFixedWidth(1)
        sep.setStyleSheet(f"background:{_BORDER};border:none;"); rh.addWidget(sep)
        if l2 and v2:
            rh.addWidget(_mk_pair(l2, v2, bg), stretch=1)
        else:
            ph = QWidget(); ph.setStyleSheet(f"background:{bg};")
            ph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            rh.addWidget(ph, stretch=1)
        self._vb.addWidget(rw)


# ══════════════════════════════════════════════════════════════════════════════
#  ANA WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class CihazTeknikUtsScraper(QWidget):
    """
    ÜTS API'dan ürün numarasıyla teknik veri çeken panel.

    Kullanım:
        w = CihazTeknikUtsScraper(cihaz_id="...", db=db, parent=self)
        w.saved.connect(...)
        w.canceled.connect(...)
        w.data_ready.connect(self._populate_form_fields)  # Veriyi form'a yaz
    """
    saved      = Signal()
    canceled   = Signal()
    data_ready = Signal(dict)  # Parsed data emit et (form populate için)

    def __init__(self, cihaz_id="", db=None, parent=None):
        super().__init__(parent)
        self.db       = db
        self.cihaz_id = str(cihaz_id) if cihaz_id else ""
        self._allowed_fields = _load_allowed_db_fields()
        self._parsed: Dict[str, str]    = {}
        self._raw_json: str             = ""
        self._thread: Optional[QThread] = None
        self._build()

    # ── Kurulum ───────────────────────────────────────────────────────────────

    def _build(self):
        main = QVBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet(S.get("scroll",""))
        cnt = QWidget(); cnt.setStyleSheet("background:transparent;")
        root = QVBoxLayout(cnt); root.setContentsMargins(20,20,20,20); root.setSpacing(14)

        root.addWidget(self._search_box())

        self._stat = QLabel(""); self._stat.setAlignment(Qt.AlignCenter)
        self._stat.setStyleSheet(f"color:{_TEXT_SEC};font-size:11px;")
        self._stat.hide(); root.addWidget(self._stat)

        self._prog = QProgressBar(); self._prog.setRange(0,0); self._prog.setFixedHeight(3)
        self._prog.setStyleSheet(
            f"QProgressBar{{background:{_BG_SECT};border:none;border-radius:1px;}}"
            f"QProgressBar::chunk{{background:{_ACCENT};border-radius:1px;}}"
        )
        self._prog.hide(); root.addWidget(self._prog)

        self._prev = QWidget(); self._prev.setStyleSheet("background:transparent;")
        self._pvb  = QVBoxLayout(self._prev)
        self._pvb.setContentsMargins(0,0,0,0); self._pvb.setSpacing(14)
        self._prev.hide(); root.addWidget(self._prev)

        root.addWidget(self._btn_bar())
        root.addStretch()
        scroll.setWidget(cnt); main.addWidget(scroll)

    def _search_box(self):
        box = QFrame()
        box.setStyleSheet(f"QFrame{{border:{_BC};border-radius:8px;background:{_BG_SECT};}}")
        vb = QVBoxLayout(box); vb.setContentsMargins(20,18,20,18); vb.setSpacing(12)

        title = QLabel("🔍  ÜTS Ürün Sorgulama")
        title.setStyleSheet(
            f"color:{_ACCENT};font-size:13px;font-weight:700;border:none;background:transparent;"
        )
        vb.addWidget(title)

        desc = QLabel(
            "Birincil Ürün Numarasını (barkod) girin. ÜTS sistemi sorgulanarak\n"
            "tüm teknik bilgiler otomatik doldurulur."
        )
        desc.setStyleSheet(f"color:{_TEXT_SEC};font-size:11px;border:none;background:transparent;")
        desc.setWordWrap(True); vb.addWidget(desc)

        row = QHBoxLayout(); row.setSpacing(8)
        self._inp = QLineEdit()
        self._inp.setPlaceholderText("Birincil Ürün No  (örn: 04056869003665)")
        self._inp.setStyleSheet(_INP_CSS)
        self._inp.returnPressed.connect(self._start)
        row.addWidget(self._inp, stretch=1)
        btn = QPushButton("Sorgula"); btn.setStyleSheet(_BTN_P)
        btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(self._start)
        row.addWidget(btn); vb.addLayout(row)

        return box

    def _btn_bar(self):
        bar = QWidget(); bar.setStyleSheet("background:transparent;")
        h = QHBoxLayout(bar); h.setContentsMargins(0,0,0,0); h.setSpacing(10)

        self._btn_debug = QPushButton("🛠  Ham JSON")
        self._btn_debug.setStyleSheet(_BTN_S)
        self._btn_debug.setCursor(Qt.PointingHandCursor)
        self._btn_debug.setVisible(False)
        self._btn_debug.clicked.connect(self._show_debug)
        h.addWidget(self._btn_debug)

        h.addStretch()
        b_cancel = QPushButton("İptal"); b_cancel.setStyleSheet(_BTN_S)
        b_cancel.setCursor(Qt.PointingHandCursor)
        b_cancel.clicked.connect(self.canceled.emit); h.addWidget(b_cancel)

        self._b_save = QPushButton("💾  Veritabanına Kaydet")
        self._b_save.setStyleSheet(_BTN_P); self._b_save.setCursor(Qt.PointingHandCursor)
        self._b_save.setEnabled(False); self._b_save.clicked.connect(self._save)
        h.addWidget(self._b_save)
        return bar

    # ── İşlemler ──────────────────────────────────────────────────────────────

    def _start(self):
        urun_no = self._inp.text().strip()
        if not urun_no:
            self._st("Lütfen Birincil Ürün Numarası girin.", _WARNING); return
        if self._thread and self._thread.isRunning(): return

        self._prog.show(); self._b_save.setEnabled(False)
        self._btn_debug.setVisible(False); self._prev.hide()
        self._st(f"ÜTS sorgulanıyor: {urun_no} …", _ACCENT)

        self._thread = QThread()
        self._worker = _Worker(urun_no)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._done)
        self._worker.error.connect(self._err)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _done(self, data: dict):
        self._prog.hide()
        self._raw_json = data.pop("_raw_json", "")
        count = data.pop("_item_count", "?")
        data = _filter_allowed_fields(data, self._allowed_fields)
        self._parsed = data
        
        # DEBUG: Parsed data içeriğini logla
        logger.info(f"📦 Parser çıktısı: {len(self._parsed)} alan")
        logger.debug(f"📋 Alan isimleri: {list(self._parsed.keys())}")
        for key, val in list(self._parsed.items())[:10]:  # İlk 10 alanı göster
            logger.debug(f"  - {key}: {val[:50] if isinstance(val, str) and len(val) > 50 else val}")
        
        self._btn_debug.setVisible(True)
        self._build_preview(data)
        self._b_save.setEnabled(True)
        filled = sum(1 for v in data.values() if v)
        self._st(
            f"✅ {filled} alan çekildi  ({count} ürün bulundu). Kontrol edip kaydedin.",
            _SUCCESS,
        )
        
        # Parsed data'yı parent widget'a emit et (form field populate için)
        self.data_ready.emit(self._parsed)

    def _err(self, msg: str):
        self._prog.hide()
        self._st(f"❌ {msg}", _ERROR)
        logger.error(f"ÜTS: {msg}")
        QMessageBox.warning(self, "Hata", msg)

    def _show_debug(self):
        """Çekilen veriyi JSON olarak göster."""
        if not self._parsed:
            QMessageBox.information(self, "Bilgi", "Henüz bir sonuç yok.")
            return
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Çekilen Ürün Verisi")
        dlg.setText("ÜTS'den çekilen tam teknik bilgiler:")
        dlg.setDetailedText(json.dumps(self._parsed, ensure_ascii=False, indent=2)[:5000])
        dlg.exec()

    # ── Önizleme ──────────────────────────────────────────────────────────────

    def _build_preview(self, data: dict):
        while self._pvb.count():
            it = self._pvb.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        def W(key: str) -> QLabel:
            val = data.get(key) or ""
            lb = QLabel(val if val else "—")
            lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lb.setWordWrap(True)
            lb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            lb.setStyleSheet(_VAL_CSS + (f"color:{_WARNING};" if not val else ""))
            return lb

        # ── 1. Tanimlayici ────────────────────────────────────────────────────
        s1 = _Sec("Tanimlayici Bilgiler")
        s1.row("Urun No",            W("UrunNo"),               "Firma",           W("Firma"))
        s1.row("Marka",              W("Marka"),                "Urun Adi",        W("UrunAdi"))
        s1.row("Model",              W("Model"),                "Urun Tipi",       W("UrunTipi"))
        s1.row("Sinif",              W("Sinif"),                "Referans/Katalog", W("ReferansKatalogNo"))
        s1.row("GMDN Kodu",          W("GmdnKod"),              "GMDN Tanimi",     W("GmdnTurkce"))
        s1.row("Urun Tanimi",        W("UrunTanimi"))
        s1.row("Urun Aciklamasi",    W("UrunAciklamasi"))
        s1.row("Turkce Etiket",      W("TurkceEtiket"),         "Orijinal Etiket", W("OrijinalEtiket"))
        self._pvb.addWidget(s1)

        # ── 1b. Firma Bilgileri ───────────────────────────────────────────────
        s1b = _Sec("Firma/Kurum Bilgileri")
        s1b.row("Firma",         W("Firma"),         "Firma No",      W("FirmaNo"))
        s1b.row("Firma Telefon", W("FirmaTelefon"), "Firma Email",   W("FirmaEmail"))
        s1b.row("Firma Durum",   W("FirmaDurum"),   "Faaliyet Alan", W("FirmaFaaliyetAlan"))
        self._pvb.addWidget(s1b)

        # ── 2. Ithal/Imal ─────────────────────────────────────────────────────
        s2 = _Sec("Ithal/Imal Bilgileri")
        s2.row("Ithal/Imal Bilgisi", W("IthalImalBilgisi"), "Mensei Ulke",      W("MenseiUlke"))
        s2.row("Ithal Edilen Ulke",  W("IthalEdilenUlke"))
        self._pvb.addWidget(s2)

        # ── 3. Ozellikler ─────────────────────────────────────────────────────
        s3 = _Sec("Ozellikler")
        s3.subhdr("Sterilite")
        s3.row("Steril Paketlendi mi",          W("SterilPaketlendiMi"),
               "Kullanim Oncesi Sterilizasyon", W("KullanimOncesiSterilizasyonGerekliMi"))
        s3.subhdr("Kullanimlik")
        s3.row("Tek Kullanimlik mi",             W("TekKullanimlikMi"),
               "Tek Hasta Kullanim mi",          W("TekHastaKullanimMi"))
        s3.row("Sinirli Kullanim Sayisi Var mi", W("SinirliKullanimSayisiVarMi"),
               "Saklama Kosulu Var",             W("SaklamaKosuluVar"))
        s3.row("Tekil Urun Var mi",              W("TekilUrunVarMi"))
        s3.subhdr("Raf Omru")
        s3.row("Raf Omru Var mi", W("RafOmruVarMi"), "Raf Omru Degeri", W("RafOmruDegeri"))
        s3.subhdr("Kalibrasyon / Bakim")
        s3.row("Kalibrasyona Tabi mi",    W("KalibrasyonaTabiMi"),
               "Kalibrasyon Periyodu (ay)", W("KalibrasyonPeriyoduAy"))
        s3.row("Bakima Tabi mi",          W("BakimaTabiMi"),
               "Bakim Periyodu (ay)",      W("BakimPeriyoduAy"))
        s3.subhdr("Diger Ozellikler")
        s3.row("MRG Uyumluluk",                W("MRGGuvenlikBilgisi"),
               "Vucuda Implante Edilebilir mi", W("ImplanteEdilebilirMi"))
        s3.row("Lateks Iceriyor mu",            W("LateksIceriyorMu"),
               "Ftalat/DEHP Iceriyor mu",       W("FtalatDEHPIceriyorMu"))
        s3.row("Iyonize Radyasyon Icerir mi",   W("IyonizeRadyasyonIcerirMi"),
               "Nanomateryal Iceriyor mu",      W("NanomateryalIceriyorMu"))
        s3.row("Bilesen/Aksesuar mi",           W("BilesenAksesuarMi"),
               "Ek-3 Kapsaminda mi",            W("Ek3KapsamindaMi"))
        self._pvb.addWidget(s3)

        # ── 4. Belgeler ───────────────────────────────────────────────────────
        s4 = _Sec("Urun Belgeleri")
        s4.row("Belgeler", W("UrunBelgeleri"))
        self._pvb.addWidget(s4)

        # ── 5. ÜTS Kayıt Bilgileri ────────────────────────────────────────────
        s5 = _Sec("UTS Kayit Bilgisi")
        s5.row("Urun Durumu",          W("UrunDurum"),           "Kayit Tipi",      W("KayitTipi"))
        s5.row("UTS Baslangic Tarihi", W("UTSBaslangicTarihi"),  "Durum Tarihi",    W("DurumTarihi"))
        s5.row("Kontrol Tarihi",       W("KontrolTarihi"),       "Basvuru Hazir",   W("BasvuruHazir"))
        s5.row("Olusturma Tarihi",     W("OlusturmaTarihi"),     "Guncelleme Tarihi", W("GuncellemeTarihi"))
        self._pvb.addWidget(s5)

        self._prev.show()

    # ── Kaydet ────────────────────────────────────────────────────────────────

    def _save(self):
        if not self._parsed: return
        self._parsed["Cihazid"] = self.cihaz_id
        try:
            repo = RepositoryRegistry(self.db).get("Cihaz_Teknik")
            
            # Mevcut kaydı kontrol et
            existing = repo.get_by_cihaz_id(self.cihaz_id)
            if existing:
                repo.update(self.cihaz_id, self._parsed)
            else:
                repo.insert(self._parsed)
            
            filled = sum(1 for v in self._parsed.values() if v)
            self._st("✅ Kaydedildi!", _SUCCESS)
            self._b_save.setEnabled(False)
            QMessageBox.information(self, "Başarılı",
                                    f"Teknik bilgiler kaydedildi. ({filled} alan)")
            
            # Saved signal emit et (parent widget'a bildir)
            self.saved.emit()
            
            # Data'yı tekrar emit et (eğer parent form hala güncel değilse)
            self.data_ready.emit(self._parsed)
        except Exception as e:
            logger.error(f"VT: {e}")
            self._st(f"❌ {e}", _ERROR)
            QMessageBox.critical(self, "Hata", str(e))

    def _st(self, msg, color=""):
        self._stat.setText(msg)
        if color: self._stat.setStyleSheet(f"color:{color};font-size:11px;")
        self._stat.show()
