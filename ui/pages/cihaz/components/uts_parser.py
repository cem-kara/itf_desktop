# -*- coding: utf-8 -*-
"""
UTS scraping + parsing utilities.
Separated from UI to keep widget code smaller.
"""
from __future__ import annotations

import json
from typing import Dict, Optional, Set

from bs4 import BeautifulSoup

from core.logger import logger
from core.paths import TEMP_DIR
from database.table_config import TABLES


_UTS_URL = "https://utsuygulama.saglik.gov.tr/UTS/vatandas"

_JSON_KEY_TO_DB_FIELD = {
    "markaAdi": "MarkaAdi",
    "versiyonModel": "VersiyonModel",
    "urunTanimi": "UrunTanimi",
    "gmdnTerim.turkceAd": "GmdnTerimTurkceAd",
    "gmdnTerim.turkceAciklama": "GmdnTerimTurkceAciklama",
    "birincilUrunNumarasi": "BirincilUrunNumarasi",
    "durum": "Durum",
    "utsBaslangicTarihi": "UtsBaslangicTarihi",
    "ithalImalBilgisi": "IthalImalBilgisi",
    "menseiUlkeSet": "MenseiUlkeSet",
    "baskaCihazinBilesenAksesuarYedekParcasiMi": "SutEslesmesiSet",
    "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerir",
    "mrgUyumlu": "MrgUyumlu",
    "vucudaImplanteEdilebilirMi": "BaskaImalatciyaUrettirildiMi",
    "tekKullanimlik": "SinirliKullanimSayisiVar",
    "tekHastayaKullanilabilir": "TekHastayaKullanilabilir",
    "kalibrasyonaTabiMi": "KalibrasyonaTabiMi",
    "kalibrasyonPeriyodu": "KalibrasyonPeriyodu",
    "bakimaTabiMi": "BakimaTabiMi",
    "bakimPeriyodu": "BakimPeriyodu",
    "kurum.unvan": "KurumUnvan",
    "kurum.eposta": "KurumEposta",
    "gmdnTerim.kod": "GmdnTerimKod",
    "etiket": "EtiketAdi",
    "siniflandirma": "Sinif",
    "katalogNo": "KatalogNo",
    "temelUdiDi": "TemelUdiDi",
    "aciklama": "Aciklama",
    "kurumGorunenAd": "KurumGorunenAd",
    "kurumNo": "KurumNo",
    "kurumTelefon": "KurumTelefon",
    "cihazKayitTipi": "CihazKayitTipi",
    "urunTipi": "UrunTipi",
    "ithalEdilenUlkeSet": "IthalEdilenUlkeSet",
}


def load_allowed_db_fields(table_name: str = "Cihaz_Teknik") -> Set[str]:
    """Return allowed DB columns for a table from TABLES config."""
    config = TABLES[table_name]
    cols = config.get("columns", [])
    return set(cols)


def filter_allowed_fields(data: Dict[str, str], allowed_fields: Optional[Set[str]] = None) -> Dict[str, str]:
    """Filter parsed data to only known DB columns."""
    if not data:
        return {}
    if allowed_fields is None:
        allowed_fields = load_allowed_db_fields()
    return {k: v for k, v in data.items() if k in allowed_fields}


def _yn(val) -> str:
    """Evet/Hayir donustur."""
    if val is None:
        return ""
    v = str(val).upper().strip()
    if v in ("EVET", "YES", "TRUE", "1"):
        return "Evet"
    if v in ("HAYIR", "NO", "FALSE", "0"):
        return "Hayır"
    return str(val)


async def scrape_uts(urun_no: str) -> Dict[str, str]:  # type: ignore
    """
    Playwright ile ÜTS web sayfasından ürün verisi çeker.
    Network API call'larını intercept ederek JSON response'ı yakalar.
    """
    from playwright.async_api import async_playwright
    import os
    from datetime import datetime

    result = {}
    captured_json = None
    debug_dir = os.path.join(TEMP_DIR, "uts_debug")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True
)
        page = await context.new_page()

        async def handle_response(response):
            nonlocal captured_json
            try:
                if (
                    "detay" in response.url.lower()
                    or "detail" in response.url.lower()
                    or "tibbiCihazSorgula" in response.url
                ):
                    if response.status == 200:
                        logger.debug(f"API Response yakalandi: {response.url}")
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
                            logger.debug(f"Response JSON parse basarisiz: {json_err}")
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            logger.debug(f"UTS sayfasi aciliyor: {_UTS_URL}")
            await page.goto(_UTS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Tüm network işlemlerinin bitmesini bekle (referans veri yükleme için)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                logger.debug("Network işlemleri tamamlandı (networkidle)")
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}, devam ediliyor...")
                await page.wait_for_timeout(3000)

            page_content = await page.content()
            logger.debug(f"Sayfa yüklendi, byte: {len(page_content)}")

            screenshot_path = os.path.join(debug_dir, f"uts_page_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            logger.debug(f"Screenshot kaydedildi: {screenshot_path}")

            all_inputs = await page.query_selector_all("input")
            logger.debug(f"Sayfa uzerinde {len(all_inputs)} adet input bulundu")
            for i, inp in enumerate(all_inputs):
                inp_id = await inp.get_attribute("id")
                inp_name = await inp.get_attribute("name")
                inp_type = await inp.get_attribute("type")
                inp_visible = await inp.is_visible()
                logger.debug(
                    f"  Input {i}: id={inp_id}, name={inp_name}, type={inp_type}, visible={inp_visible}"
                )

            iframes = await page.query_selector_all("iframe")
            logger.debug(f"Sayfa uzerinde {len(iframes)} adet iframe bulundu")
            for i, iframe in enumerate(iframes):
                iframe_id = await iframe.get_attribute("id")
                iframe_name = await iframe.get_attribute("name")
                iframe_src = await iframe.get_attribute("src")
                logger.debug(
                    f"  IFrame {i}: id={iframe_id}, name={iframe_name}, src={iframe_src[:80] if iframe_src else None}"
                )

            search_input = None
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
                            logger.debug(f"Input bulundu (gorunur): {selector}")
                            break
                        try:
                            compute_result = await page.evaluate(
                                f"""
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
                                """
                            )
                            logger.debug(
                                f"Input gizli: {selector} -> CSS: {compute_result}"
                            )
                        except Exception as css_err:
                            logger.debug(
                                f"Input bulundu ama gizli: {selector} (CSS check basarisiz: {css_err})"
                            )
                except Exception as e:
                    logger.debug(f"Selector test basarisiz: {selector} -> {e}")

            if not search_input:
                all_inputs = await page.query_selector_all("input")
                if all_inputs:
                    search_input = all_inputs[0]
                    logger.warning("Visible input bulunamadi, ilk input kullaniliyor")
                else:
                    raise RuntimeError("UTS sayfasinda hic input bulunamadi.")

            try:
                await search_input.fill(urun_no, force=True)
                logger.debug(f"Urun no yazildi (fill): {urun_no}")
            except Exception as e:
                logger.warning(f"fill() basarisiz: {e}")
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
                    logger.debug(f"Urun no yazildi (JS): {urun_no}")
                except Exception as js_err:
                    logger.warning(f"JS setValue basarisiz, type() deneniyor: {js_err}")
                    try:
                        await search_input.type(urun_no, delay=50)
                        logger.debug(f"Urun no yazildi (type): {urun_no}")
                    except Exception as type_err:
                        raise RuntimeError(
                            f"Input doldurma basarisiz (fill, JS, type hepsi denendi): {type_err}"
                        )

            await page.wait_for_timeout(500)

            logger.debug("Submit button araniyor...")

            all_buttons = await page.query_selector_all("button")
            logger.debug(f"Sayfa uzerinde {len(all_buttons)} adet button bulundu")
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
                            logger.debug(f"Button bulundu: {selector}")
                            break
                        logger.debug(
                            f"Button bulundu ama (visible={is_visible}, enabled={is_enabled}): {selector}"
                        )
                except Exception as e:
                    logger.debug(f"Button selector basarisiz: {selector} -> {e}")

            if submit_btn:
                try:
                    await submit_btn.click()
                    logger.debug("Button tiklandi")
                    await page.wait_for_timeout(1000)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(1500)

                    logger.debug(
                        "Sonuc tablosundan ilk urunun barcode'una tiklaniyor..."
                    )

                    rows = await page.query_selector_all(
                        "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
                    )
                    logger.debug(f"Tabloda {len(rows)} satir bulundu")

                    if rows:
                        try:
                            first_row = rows[0]
                            first_cell = await first_row.query_selector(
                                "td:first-child, td:nth-child(1)"
                            )

                            if first_cell:
                                clickable = await first_cell.query_selector(
                                    "a, span[style*='cursor'], [data-id], .barcode, .product-id"
                                )

                                if clickable:
                                    logger.debug(
                                        "Barcode hucrede tiklanabilir element bulundu, tiklaniyor..."
                                    )
                                    await clickable.click()
                                else:
                                    logger.debug("Barcode hucreye tiklaniyor...")
                                    await first_cell.click()
                            else:
                                logger.debug("Satirin kendisine tiklaniyor...")
                                await first_row.click()

                            logger.debug("Popup acilmasi bekleniyor...")
                            await page.wait_for_timeout(500)

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
                                        logger.debug(f"Modal bulundu: {selector}")
                                        modal_found = True
                                        break
                                except Exception:
                                    pass

                            if modal_found:
                                await page.wait_for_timeout(1500)
                                logger.debug("Popup acildi ve yüklendi")
                            else:
                                logger.warning(
                                    "Modal/Popup acilmis gibi gozukmuyor, devam ediliyor..."
                                )
                                await page.wait_for_timeout(1500)

                        except Exception as detail_err:
                            logger.warning(f"Popup acma basarisiz: {detail_err}")
                    else:
                        logger.warning("Sonuc tablosunda satir bulunamadi!")

                except Exception as e:
                    logger.warning(f"Button click basarisiz: {e}")
                    logger.warning("Enter tusu deneniyor...")
                    await search_input.press("Enter")
                    await page.wait_for_timeout(1000)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(1500)

                    rows = await page.query_selector_all(
                        "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
                    )
                    if rows:
                        try:
                            first_row = rows[0]
                            first_cell = await first_row.query_selector(
                                "td:first-child, td:nth-child(1)"
                            )
                            if first_cell:
                                clickable = await first_cell.query_selector(
                                    "a, span[style*='cursor'], [data-id]"
                                )
                                if clickable:
                                    await clickable.click()
                                else:
                                    await first_cell.click()
                            else:
                                await first_row.click()
                            await page.wait_for_timeout(1500)
                        except Exception as retry_err:
                            logger.warning(
                                f"Enter sonrasi popup acma basarisiz: {retry_err}"
                            )
            else:
                logger.warning("Button bulunamadi, Enter tusu kullaniliyor")
                await search_input.press("Enter")
                await page.wait_for_timeout(1000)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1500)

                rows = await page.query_selector_all(
                    "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
                )
                logger.debug(f"Tabloda {len(rows)} satir bulundu (Enter yolu)")

                if rows:
                    try:
                        first_row = rows[0]
                        first_cell = await first_row.query_selector(
                            "td:first-child, td:nth-child(1)"
                        )

                        if first_cell:
                            clickable = await first_cell.query_selector(
                                "a, span[style*='cursor'], [data-id]"
                            )
                            if clickable:
                                logger.debug(
                                    "Barcode hucrede tiklanabilir element bulundu, tiklaniyor..."
                                )
                                await clickable.click()
                            else:
                                logger.debug("Barcode hucreye tiklaniyor...")
                                await first_cell.click()
                        else:
                            logger.debug("Satirin kendisine tiklaniyor...")
                            await first_row.click()

                        await page.wait_for_timeout(1500)
                        logger.debug("Popup acilmis olmali (Enter yolu)")
                    except Exception as detail_err:
                        logger.warning(
                            f"Popup acma basarisiz (Enter yolu): {detail_err}"
                        )

            result_screenshot = os.path.join(debug_dir, f"uts_modal_{timestamp}.png")
            await page.screenshot(path=result_screenshot)
            logger.debug(f"Modal sayfasi screenshot'i: {result_screenshot}")

            detail_html = await page.content()
            detail_soup = BeautifulSoup(detail_html, "html.parser")
            logger.debug(f"Modal HTML parse edildi, byte: {len(detail_html)}")

            html_file = os.path.join(debug_dir, f"uts_modal_{timestamp}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(detail_html)
            logger.debug(f"Modal HTML kaydedildi: {html_file}")

            if captured_json:
                logger.debug("API JSON response'indan veri cekiliyor...")
                result = _parse_uts_api_response(captured_json, urun_no)
                if result and any(result.values()):
                    logger.info(
                        f"API JSON'dan basariyla {len(result)} alan cikartildi"
                    )
                else:
                    logger.warning("API JSON parse edildi ama alan bulunamadi")
            else:
                logger.warning("API JSON yakalanmadi, HTML parse'a geciliyor...")
                result = {}

            if not result or not any(result.values()):
                logger.debug("Fallback: Modal HTML'den veri cekiliyor...")
                result = _parse_uts_modal(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(
                        f"HTML modal'dan basariyla {len(result)} alan cikartildi"
                    )

            if not result or not any(result.values()):
                logger.debug("Fallback: HTML detail'den veri cekiliyor...")
                result = _parse_uts_detail(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(
                        f"HTML detailed'dan basariyla {len(result)} alan cikartildi"
                    )

            if not result or not any(result.values()):
                logger.warning("Fallback: Liste tablosundan cek...")
                result = _parse_uts_html(detail_soup, urun_no)
                if result and any(result.values()):
                    logger.debug(
                        f"HTML list'ten basariyla {len(result)} alan cikartildi"
                    )

            if not result or not any(result.values()):
                logger.warning("Tum parse yontemleri basarisiz")

            if captured_json:
                result["_raw_json"] = json.dumps(captured_json)[:1000]
            else:
                result["_raw_json"] = detail_html[:1000]
            result["_item_count"] = "1"

            logger.debug(f"UTS cekme basarili: {len(result)} alan")

        except Exception as e:
            import traceback

            logger.error(f"UTS scraping hatasi: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"UTS veri cekme hatasi:\n{e}")
        finally:
            await context.close()
            await browser.close()

    return result


async def scrape_uts(urun_no: str) -> Dict[str, str]:
    """
    Wrapper: Playwright ile ÜTS web sayfasından ürün verisi çeker.
    Network API call'larını intercept ederek JSON response'ı yakalar.
    Sonra direkt API çağrısıyla referans verilerini almaya çalışır.
    """
    from playwright.async_api import async_playwright
    import os
    from datetime import datetime

    result = {}
    captured_json = None
    debug_dir = os.path.join(TEMP_DIR, "uts_debug")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True
)
        page = await context.new_page()

        async def handle_response(response):
            nonlocal captured_json
            try:
                if (
                    "detay" in response.url.lower()
                    or "detail" in response.url.lower()
                    or "tibbiCihazSorgula" in response.url
                ):
                    if response.status == 200:
                        logger.debug(f"API Response yakalandi: {response.url}")
                        try:
                            data = await response.json()
                            captured_json = data
                            logger.debug(
                                f"JSON response parse edildi: {len(str(data))} byte"
                            )

                            json_file = os.path.join(
                                debug_dir, f"uts_api_response_{timestamp}.json"
                            )
                            with open(json_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            logger.debug(f"API JSON kaydedildi: {json_file}")
                        except Exception as json_err:
                            logger.debug(f"Response JSON parse basarisiz: {json_err}")
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            logger.debug(f"UTS sayfasi aciliyor: {_UTS_URL}")
            await page.goto(_UTS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)

            # Tüm network işlemlerinin bitmesini bekle (referans veri yükleme için)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                logger.debug("Network işlemleri tamamlandı (networkidle)")
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}, devam ediliyor...")
                await page.wait_for_timeout(3000)

            page_content = await page.content()
            logger.debug(f"Sayfa yüklendi, byte: {len(page_content)}")

            all_inputs = await page.query_selector_all("input")
            logger.debug(f"Sayfa uzerinde {len(all_inputs)} adet input bulundu")

            search_input = None
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
                            logger.debug(f"Input bulundu (gorunur): {selector}")
                            break
                except Exception:
                    pass

            if not search_input:
                all_inputs = await page.query_selector_all("input")
                if all_inputs:
                    search_input = all_inputs[0]
                    logger.warning("Visible input bulunamadi, ilk input kullaniliyor")
                else:
                    raise RuntimeError("UTS sayfasinda hic input bulunamadi.")

            try:
                await search_input.fill(urun_no, force=True)
                logger.debug(f"Urun no yazildi (fill): {urun_no}")
            except Exception:
                try:
                    await page.evaluate(
                        f"""
                        document.querySelectorAll('input').forEach(inp => {{
                            inp.value = '{urun_no}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }});
                        """
                    )
                    logger.debug(f"Urun no yazildi (JS): {urun_no}")
                except Exception:
                    pass

            await page.wait_for_timeout(500)

            all_buttons = await page.query_selector_all("button")
            submit_btn = None

            for elem in all_buttons:
                try:
                    is_visible = await elem.is_visible()
                    is_enabled = await elem.is_enabled()
                    if is_visible and is_enabled:
                        submit_btn = elem
                        break
                except Exception:
                    pass

            if submit_btn:
                try:
                    await submit_btn.click()
                    logger.debug("Button tiklandi")
                    await page.wait_for_timeout(1000)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(1500)

                    rows = await page.query_selector_all(
                        "table tbody tr, table tr[role='row'], tr[data-id], tr.row"
                    )
                    if rows:
                        try:
                            first_row = rows[0]
                            first_cell = await first_row.query_selector(
                                "td:first-child, td:nth-child(1)"
                            )
                            if first_cell:
                                clickable = await first_cell.query_selector(
                                    "a, span[style*='cursor'], [data-id]"
                                )
                                if clickable:
                                    await clickable.click()
                                else:
                                    await first_cell.click()
                            else:
                                await first_row.click()

                            await page.wait_for_timeout(1500)
                        except Exception:
                            pass
                except Exception:
                    try:
                        await search_input.press("Enter")
                        await page.wait_for_timeout(2000)
                    except Exception:
                        pass

            detail_html = await page.content()
            detail_soup = BeautifulSoup(detail_html, "html.parser")

            # Playwright'dan gelen veriler
            if captured_json:
                logger.debug("API JSON response'indan veri cekiliyor...")
                result = _parse_uts_api_response(captured_json, urun_no)
            else:
                result = {}

            if not result or not any(result.values()):
                logger.debug("Fallback: Modal HTML'den veri cekiliyor...")
                result = _parse_uts_modal(detail_soup, urun_no)

            result["_raw_json"] = json.dumps(captured_json)[:1000] if captured_json else detail_html[:1000]
            result["_item_count"] = "1"

        except Exception as e:
            import traceback

            logger.error(f"UTS scraping hatasi: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"UTS veri cekme hatasi:\n{e}")
        finally:
            await context.close()
            await browser.close()

    return result


def _parse_uts_api_response(api_response: dict, urun_no: str) -> Dict[str, str]:
    """
    UTS API JSON response'ini parse et.
    Yeni Cihaz_Teknik şemasına göre alan adları mapping'i yap.
    """
    r: Dict[str, str] = {}

    if not api_response or "data" not in api_response:
        logger.warning("API response yapisi hatali (data array yok)")
        return r

    data_array = api_response.get("data", [])
    if not data_array or not isinstance(data_array, list):
        logger.warning(f"Data array bos veya hatali (tip: {type(data_array)})")
        return r

    item = data_array[0]
    if not isinstance(item, dict):
        logger.warning("Data item dict degil")
        return r

    logger.debug(f"API JSON parse basliyor (item keys: {len(item)})")

    # ── Temel Urun Bilgileri ──────────────────────────────────────────────────
    if "birincilUrunNumarasi" in item and item["birincilUrunNumarasi"]:
        r["BirincilUrunNumarasi"] = str(item["birincilUrunNumarasi"])
        logger.debug(f"BirincilUrunNumarasi: {item['birincilUrunNumarasi']}")

    if "markaAdi" in item and item["markaAdi"]:
        r["MarkaAdi"] = item["markaAdi"].strip()
        logger.debug(f"MarkaAdi: {item['markaAdi']}")

    if "etiketAdi" in item and item["etiketAdi"]:
        r["EtiketAdi"] = item["etiketAdi"].strip()
        logger.debug(f"EtiketAdi: {item['etiketAdi'][:60]}")

    if "urunTanimi" in item and item["urunTanimi"]:
        r["UrunTanimi"] = item["urunTanimi"].strip()
        logger.debug(f"UrunTanimi: {item['urunTanimi'][:60]}")

    if "versiyonModel" in item and item["versiyonModel"]:
        r["VersiyonModel"] = item["versiyonModel"].strip()
        logger.debug(f"VersiyonModel: {item['versiyonModel']}")

    if "katalogNo" in item and item["katalogNo"]:
        r["KatalogNo"] = item["katalogNo"].strip()
        logger.debug(f"KatalogNo: {item['katalogNo']}")

    if "temelUdiDi" in item and item["temelUdiDi"]:
        r["TemelUdiDi"] = item["temelUdiDi"].strip()
        logger.debug(f"TemelUdiDi: {item['temelUdiDi']}")

    if "aciklama" in item and item["aciklama"]:
        r["Aciklama"] = item["aciklama"].strip()
        logger.debug(f"Aciklama: {item['aciklama'][:60]}")

    # ── Kurum Bilgileri ─────────────────────────────────────────────────────────
    if "kurum" in item and isinstance(item["kurum"], dict):
        kurum = item["kurum"]

        if "unvan" in kurum and kurum["unvan"]:
            r["KurumUnvan"] = kurum["unvan"].strip()
            logger.debug(f"KurumUnvan: {kurum['unvan']}")

        if "gorunenAd" in kurum and kurum["gorunenAd"]:
            r["KurumGorunenAd"] = kurum["gorunenAd"].strip()
            logger.debug(f"KurumGorunenAd: {kurum['gorunenAd']}")

        if "kurumNo" in kurum and kurum["kurumNo"]:
            r["KurumNo"] = str(kurum["kurumNo"])
            logger.debug(f"KurumNo: {kurum['kurumNo']}")

        if "telefon" in kurum and kurum["telefon"]:
            r["KurumTelefon"] = kurum["telefon"]
            logger.debug(f"KurumTelefon: {kurum['telefon']}")

        if "eposta" in kurum and kurum["eposta"]:
            r["KurumEposta"] = kurum["eposta"]
            logger.debug(f"KurumEposta: {kurum['eposta']}")

    # ── Durum ve Kayit Bilgileri ────────────────────────────────────────────────
    if "durum" in item and item["durum"]:
        r["Durum"] = item["durum"]
        logger.debug(f"Durum: {item['durum']}")

    if "utsBaslangicTarihi" in item and item["utsBaslangicTarihi"]:
        r["UtsBaslangicTarihi"] = item["utsBaslangicTarihi"]
        logger.debug(f"UtsBaslangicTarihi: {item['utsBaslangicTarihi']}")

    if "kontroleGonderildigiTarih" in item and item["kontroleGonderildigiTarih"]:
        r["KontroleGonderildigiTarih"] = item["kontroleGonderildigiTarih"]
        logger.debug(f"KontroleGonderildigiTarih: {item['kontroleGonderildigiTarih']}")

    if "cihazKayitTipi" in item and item["cihazKayitTipi"]:
        r["CihazKayitTipi"] = item["cihazKayitTipi"]
        logger.debug(f"CihazKayitTipi: {item['cihazKayitTipi']}")

    # ── Urun Tipi ve Siniflandirma ───────────────────────────────────────────────
    if "urunTipi" in item and item["urunTipi"]:
        r["UrunTipi"] = item["urunTipi"]
        logger.debug(f"UrunTipi: {item['urunTipi']}")

    if "sinif" in item and item["sinif"]:
        r["Sinif"] = item["sinif"]
        logger.debug(f"Sinif: {item['sinif']}")

    # ── Ithal/Imal Bilgileri ────────────────────────────────────────────────────
    if "ithalImalBilgisi" in item and item["ithalImalBilgisi"]:
        r["IthalImalBilgisi"] = item["ithalImalBilgisi"]
        logger.debug(f"IthalImalBilgisi: {item['ithalImalBilgisi']}")

    if "menseiUlkeSet" in item and item["menseiUlkeSet"]:
        val = item["menseiUlkeSet"]
        if isinstance(val, list):
            val = ", ".join([str(v) for v in val if v])
        if val:
            r["MenseiUlkeSet"] = str(val)
            logger.debug(f"MenseiUlkeSet: {val}")

    if "ithalEdilenUlkeSet" in item and item["ithalEdilenUlkeSet"]:
        val = item["ithalEdilenUlkeSet"]
        if isinstance(val, list):
            val = ", ".join([str(v) for v in val if v])
        if val:
            r["IthalEdilenUlkeSet"] = str(val)
            logger.debug(f"IthalEdilenUlkeSet: {val}")

    # ── GMDN Terim Bilgileri ────────────────────────────────────────────────────
    if "gmdnTerim" in item and isinstance(item["gmdnTerim"], dict):
        gmdn = item["gmdnTerim"]

        if "kod" in gmdn and gmdn["kod"]:
            r["GmdnTerimKod"] = str(gmdn["kod"])
            logger.debug(f"GmdnTerimKod: {gmdn['kod']}")

        if "turkceAd" in gmdn and gmdn["turkceAd"]:
            r["GmdnTerimTurkceAd"] = gmdn["turkceAd"]
            logger.debug(f"GmdnTerimTurkceAd: {gmdn['turkceAd'][:60]}")

        if "turkceAciklama" in gmdn and gmdn["turkceAciklama"]:
            r["GmdnTerimTurkceAciklama"] = gmdn["turkceAciklama"]
            logger.debug(f"GmdnTerimTurkceAciklama: {gmdn['turkceAciklama'][:60]}")

    # ── Kalibrasyon ve Bakim Bilgileri ───────────────────────────────────────────
    if "kalibrasyonaTabiMi" in item and item["kalibrasyonaTabiMi"]:
        result = _yn(item["kalibrasyonaTabiMi"])
        if result:
            r["KalibrasyonaTabiMi"] = result
            logger.debug(f"KalibrasyonaTabiMi: {result}")

    if "kalibrasyonPeriyodu" in item and item["kalibrasyonPeriyodu"]:
        r["KalibrasyonPeriyodu"] = str(item["kalibrasyonPeriyodu"])
        logger.debug(f"KalibrasyonPeriyodu: {item['kalibrasyonPeriyodu']} ay")

    if "bakimaTabiMi" in item and item["bakimaTabiMi"]:
        result = _yn(item["bakimaTabiMi"])
        if result:
            r["BakimaTabiMi"] = result
            logger.debug(f"BakimaTabiMi: {result}")

    if "bakimPeriyodu" in item and item["bakimPeriyodu"]:
        r["BakimPeriyodu"] = str(item["bakimPeriyodu"])
        logger.debug(f"BakimPeriyodu: {item['bakimPeriyodu']} ay")

    # ── Teknik Ozellikler (Evet/Hayir alanlari) ─────────────────────────────────
    evet_hayir_alanlari = {
        "iyonizeRadyasyonIcerir": "IyonizeRadyasyonIcerir",
        "mrgUyumlu": "MrgUyumlu",
        "tekHastayaKullanilabilir": "TekHastayaKullanilabilir",
        "sinirliKullanimSayisiVar": "SinirliKullanimSayisiVar",
        "baskaImalatciyaUrettirildiMi": "BaskaImalatciyaUrettirildiMi",
    }

    for json_field, db_field in evet_hayir_alanlari.items():
        if json_field in item and item[json_field]:
            result = _yn(item[json_field])
            if result:
                r[db_field] = result
                logger.debug(f"{db_field}: {result}")

    # ── Ek Teknik Bilgiler ───────────────────────────────────────────────────────
    if "sinirliKullanimSayisi" in item and item["sinirliKullanimSayisi"]:
        r["SinirliKullanimSayisi"] = str(item["sinirliKullanimSayisi"])
        logger.debug(f"SinirliKullanimSayisi: {item['sinirliKullanimSayisi']}")

    if "sutEslesmesiSet" in item and item["sutEslesmesiSet"]:
        val = item["sutEslesmesiSet"]
        if isinstance(val, list):
            val = ", ".join([str(v) for v in val if v])
        if val:
            r["SutEslesmesiSet"] = str(val)
            logger.debug(f"SutEslesmesiSet: {val}")

    if "basvuruyaHazirMi" in item and item["basvuruyaHazirMi"] is not None:
        val = "Evet" if item["basvuruyaHazirMi"] else "Hayır"
        r["BasvuruHazir"] = val
        logger.debug(f"BasvuruHazir: {val}")

    if "cihazKayitTipi" in item and item["cihazKayitTipi"]:
        r["KayitTipi"] = item["cihazKayitTipi"]
        logger.debug(f"KayitTipi: {item['cihazKayitTipi']}")

    if "rafOmru" in item and item["rafOmru"]:
        r["RafOmruDegeri"] = str(item["rafOmru"])
        logger.debug(f"RafOmruDegeri: {item['rafOmru']}")

    if "rafOmruVar" in item and item["rafOmruVar"]:
        result = _yn(item["rafOmruVar"])
        if result:
            r["RafOmruVarMi"] = result
            logger.debug(f"RafOmruVarMi: {result}")

    if "kalibrasyonPeriyodu" in item and item["kalibrasyonPeriyodu"]:
        val = item["kalibrasyonPeriyodu"]
        r["KalibrasyonPeriyoduAy"] = str(val)
        logger.debug(f"KalibrasyonPeriyoduAy: {val} ay")

    if "bakimPeriyodu" in item and item["bakimPeriyodu"]:
        val = item["bakimPeriyodu"]
        r["BakimPeriyoduAy"] = str(val)
        logger.debug(f"BakimPeriyoduAy: {val} ay")

    if "mrgUyumlu" in item and item["mrgUyumlu"]:
        val = item["mrgUyumlu"]
        r["MRGGuvenlikBilgisi"] = val
        logger.debug(f"MRGGuvenlikBilgisi: {val}")

    logger.info(f"API JSON parse tamamlandi: {len(r)} alan basariyla eklendi")
    return r


def _parse_uts_modal(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    r: Dict[str, str] = {}

    logger.debug("Modal parsing basliyor...")

    modal = soup.find("div", {"role": "dialog"})
    if not modal:
        modal = soup.find(class_=lambda x: x and "modal" in str(x).lower())  # type: ignore
    if not modal:
        modal = soup

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
                _map_label_to_db(r, label, value_text)
                logger.debug(f"  [div/span] {label} -> {value_text[:50]}")

    dts = modal.find_all("dt")
    for dt in dts:
        label = dt.get_text(strip=True)
        dd = dt.find_next("dd")
        if dd:
            value = dd.get_text(strip=True)
            if label and value:
                _map_label_to_db(r, label, value)
                logger.debug(f"  [dt/dd] {label} -> {value[:50]}")

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
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} -> {value[:50]}")

    text_content = modal.get_text()
    lines = [line.strip() for line in text_content.split("\n") if line.strip()]

    for line in lines:
        if ":" in line and len(line) < 200:
            parts = line.split(":", 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value = parts[1].strip()

                if label and value and not any(
                    x in label.lower() for x in ["bilgiler", "kodlari", "tarihi"]
                ):
                    if 3 < len(label) < 100:
                        _map_label_to_db(r, label, value)

    try:
        strong = modal.find("strong")
        if strong:
            product_name = strong.get_text(strip=True)
            if product_name and len(product_name) > 10:
                r["UrunAdi"] = product_name
                logger.debug(f"Urun Adi bulundu (strong): {product_name}")
    except Exception:
        pass

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


def _parse_uts_detail(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    r: Dict[str, str] = {}

    panels = soup.find_all(
        ["div", "section"],
        class_=[
            "panel",
            "panel-body",
            "modal-body",
            "detail-panel",
            "info-panel",
        ]
)
    if not panels:
        panels = soup.find_all("div")

    logger.debug(f"Panel/div sayisi: {len(panels)}")

    for panel in panels[:20]:
        dts = panel.find_all("dt")
        for dt in dts:
            label = dt.get_text(strip=True)
            dd = dt.find_next("dd")
            if dd:
                value = dd.get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [dt/dd] {label} -> {value[:50]}")

        labels = panel.find_all("div", class_="label")
        for label_div in labels:
            label = label_div.get_text(strip=True)
            next_div = label_div.find_next("div", class_="value")
            if next_div:
                value = next_div.get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [div label/value] {label} -> {value[:50]}")

        rows = panel.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                if label and value:
                    _map_label_to_db(r, label, value)
                    logger.debug(f"  [tr/td] {label} -> {value[:50]}")

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
                        _map_label_to_db(r, label, value)

    try:
        urn_ad_candidates = [
            soup.find("strong"),
            soup.find("h3"),
            soup.find("h2"),
            soup.find(
                ["span", "div"],
                class_=["product-name", "urn-ad", "title", "main-title"]
),
        ]
        for cand in urn_ad_candidates:
            if cand:
                text = cand.get_text(strip=True)
                if text and 10 < len(text) < 200:
                    r["UrunAdi"] = text
                    logger.debug(f"Urun Adi bulundu: {text}")
                    break
    except Exception:
        pass

    if "Firma" not in r:
        firma_text = soup.find(text=lambda t: t and "HEALTHCARE" in str(t).upper())  # type: ignore
        if firma_text:
            parent = firma_text.parent.find_next(["div", "span", "td"])  # type: ignore
            if parent:
                firma = parent.get_text(strip=True)
                r["Firma"] = firma
                logger.debug(f"Firma bulundu: {firma}")

    logger.debug(f"Detay parse sonucu: {len(r)} alan bulundu")
    return r


def _parse_uts_html(soup: BeautifulSoup, urun_no: str) -> Dict[str, str]:
    r: Dict[str, str] = {}

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)

                if value and label:
                    _map_label_to_db(r, label, value)  # type: ignore

    inputs = soup.find_all(["input", "select", "textarea"])
    for inp in inputs:
        name = inp.get("name", "")
        value = inp.get("value", "") or inp.get_text(strip=True)
        if name and value:
            _map_label_to_db(r, name, value)  # type: ignore

    if urun_no:
        r["UrunNo"] = urun_no

    return r


def _map_label_to_db(data: dict, label: str, value: str) -> None:
    label_upper = label.upper().strip()
    value = str(value).strip()

    if not value:
        return

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
