# -*- coding: utf-8 -*-
"""
UTS Parser - HTML Scraper
==========================
Playwright ile UTS web sayfasından veri çekme.
"""
from typing import Dict, Optional
import os
import json
from datetime import datetime

from core.logger import logger
from core.paths import TEMP_DIR
from .uts_mapper import parse_uts_api_response
from .uts_validator import parse_uts_modal, parse_uts_detail, parse_uts_html


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

UTS_URL = "https://utsuygulama.saglik.gov.tr/UTS/vatandas"


# ─────────────────────────────────────────────────────────────────────────────
# Main Scraper
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_uts(urun_no: str) -> Dict[str, str]:
    """
    Playwright ile ÜTS web sayfasından ürün verisi çek.
    Network API call'larını intercept ederek JSON response'ı yakala.
    
    Args:
        urun_no: Aranan ürün numarası
    
    Returns:
        Çıkartılan field'lar dictionary'si
    
    Raises:
        RuntimeError: Scraping başarısız olursa
    """
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup

    result = {}
    captured_json = None
    
    # Setup debug directory
    debug_dir = os.path.join(TEMP_DIR, "uts_debug")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        async def handle_response(response):
            """API response'larını yakala ve kaydet."""
            nonlocal captured_json
            try:
                if (
                    "detay" in response.url.lower()
                    or "detail" in response.url.lower()
                    or "tibbiCihazSorgula" in response.url
                ):
                    if response.status == 200:
                        logger.debug(f"API Response yakalandı: {response.url}")
                        try:
                            data = await response.json()
                            captured_json = data
                            logger.debug(f"JSON response parse edildi: {len(str(data))} byte")

                            json_file = os.path.join(
                                debug_dir, f"uts_api_response_{timestamp}.json"
                            )
                            with open(json_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            logger.debug(f"API JSON kaydedildi: {json_file}")
                        except Exception as json_err:
                            logger.debug(f"Response JSON parse başarısız: {json_err}")
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            logger.debug(f"UTS sayfası açılıyor: {UTS_URL}")
            await page.goto(UTS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Network işlemlerinin bitmesini bekle
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                logger.debug("Network işlemleri tamamlandı (networkidle)")
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}, devam ediliyor...")
                await page.wait_for_timeout(3000)

            # ── Input alanını bul ve doldur ────────────────────────────────────
            search_input = await _find_search_input(page)
            if not search_input:
                raise RuntimeError("UTS sayfasında hiç input bulunamadı.")

            await _fill_search_input(page, search_input, urun_no)

            # ── Submit button'ı bul ve tıkla ────────────────────────────────────
            await page.wait_for_timeout(500)
            submit_btn = await _find_submit_button(page)
            
            if submit_btn:
                await _click_button(page, search_input, submit_btn)
            else:
                logger.warning("Button bulunamadı, Enter tuşu kullanılıyor")
                await _press_enter_search(page, search_input)

            # ── Modal açılana kadar bekle ──────────────────────────────────────
            detail_html = await page.content()
            detail_soup = BeautifulSoup(detail_html, "html.parser")
            
            if captured_json:
                logger.debug("API JSON response'inden veri çekiliyor...")
                result = parse_uts_api_response(captured_json, urun_no)
                if result and any(result.values()):
                    logger.info(f"API JSON'dan başarıyla {len(result)} alan çıkartıldı")

            # ── Fallback HTML parsing ──────────────────────────────────────────
            if not result or not any(result.values()):
                logger.debug("Fallback: Modal HTML'den veri çekiliyor...")
                result = parse_uts_modal(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"HTML modal'dan başarıyla {len(result)} alan çıkartıldı")

            if not result or not any(result.values()):
                logger.debug("Fallback: HTML detail'den veri çekiliyor...")
                result = parse_uts_detail(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"HTML detail'dan başarıyla {len(result)} alan çıkartıldı")

            if not result or not any(result.values()):
                logger.warning("Fallback: Liste tablosundan çek...")
                result = parse_uts_html(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(f"HTML list'ten başarıyla {len(result)} alan çıkartıldı")

            if not result or not any(result.values()):
                logger.warning("Tüm parse yöntemleri başarısız")

            # ── Raw veriyi sakla ───────────────────────────────────────────────
            result["_raw_json"] = json.dumps(captured_json)[:1000] if captured_json else detail_html[:1000]
            result["_item_count"] = "1"

            logger.debug(f"UTS çekme başarılı: {len(result)} alan")

        except Exception as e:
            import traceback
            logger.error(f"UTS scraping hatası: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"UTS veri çekme hatası:\n{e}")
        finally:
            await context.close()
            await browser.close()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

async def _find_search_input(page):
    """Search input alanını bul."""
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
                    logger.debug(f"Input bulundu (görünür): {selector}")
                    return elem
        except Exception:
            pass

    # Fallback
    all_inputs = await page.query_selector_all("input")
    if all_inputs:
        logger.warning("Visible input bulunamadı, ilk input kullanılıyor")
        return all_inputs[0]

    return None


async def _fill_search_input(page, search_input, urun_no: str):
    """Search input'unu doldur."""
    try:
        await search_input.fill(urun_no, force=True)
        logger.debug(f"Ürün no yazıldı (fill): {urun_no}")
    except Exception:
        try:
            logger.debug("JavaScript ile input value set ediliyor...")
            await page.evaluate(
                f"""
                document.querySelectorAll('input').forEach(inp => {{
                    inp.value = '{urun_no}';
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }});
                """
            )
            logger.debug(f"Ürün no yazıldı (JS): {urun_no}")
        except Exception as js_err:
            logger.warning(f"JS setValue başarısız, type() deneniyor: {js_err}")
            try:
                await search_input.type(urun_no, delay=50)
                logger.debug(f"Ürün no yazıldı (type): {urun_no}")
            except Exception as type_err:
                raise RuntimeError(
                    f"Input doldurma başarısız (fill, JS, type hepsi denendi): {type_err}"
                )


async def _find_submit_button(page):
    """Submit button'ını bul."""
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
                    logger.debug(f"Button bulundu: {selector}")
                    return elem
        except Exception:
            pass

    all_buttons = await page.query_selector_all("button")
    for btn in all_buttons:
        try:
            if await btn.is_visible() and await btn.is_enabled():
                return btn
        except Exception:
            pass

    return None


async def _click_button(page, search_input, submit_btn):
    """Button'ı tıkla ve sonuçları bekle."""
    try:
        await submit_btn.click()
        logger.debug("Button tıklandı")
        await page.wait_for_timeout(1000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)

        rows = await page.query_selector_all(
            "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
        )
        
        if rows:
            await _click_first_row(page, rows[0])
        else:
            logger.warning("Sonuç tablosunda satır bulunamadı!")

    except Exception as e:
        logger.warning(f"Button click başarısız: {e}")
        await _press_enter_search(page, search_input)


async def _click_first_row(page, first_row):
    """Sonuç tablosunun ilk satırına tıkla."""
    try:
        first_cell = await first_row.query_selector("td:first-child, td:nth-child(1)")
        if first_cell:
            clickable = await first_cell.query_selector(
                "a, span[style*='cursor'], [data-id], .barcode, .product-id"
            )
            if clickable:
                logger.debug("Barcode hücrede tiklanabilir element bulundu, tıklanıyor...")
                await clickable.click()
            else:
                logger.debug("Barcode hücreye tıklanıyor...")
                await first_cell.click()
        else:
            logger.debug("Satırın kendisine tıklanıyor...")
            await first_row.click()

        await page.wait_for_timeout(1500)
        logger.debug("Popup açılmış olmalı")
    except Exception as e:
        logger.warning(f"Popup açma başarısız: {e}")


async def _press_enter_search(page, search_input):
    """Enter tuşu ile arama yap."""
    try:
        await search_input.press("Enter")
        logger.debug("Enter tuşu basıldı")
        await page.wait_for_timeout(1000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)

        rows = await page.query_selector_all(
            "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
        )
        
        if rows:
            await _click_first_row(page, rows[0])

    except Exception as e:
        logger.warning(f"Enter search başarısız: {e}")
