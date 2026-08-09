from scraper.base import BaseScraper, PriceExtractionError
from typing import Dict, Any
import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

class AmazonScraper(BaseScraper):
    def _fast_http_fetch(self, url: str) -> Dict[str, Any]:
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                title_elem = soup.select_one("#productTitle")
                price_elem = soup.select_one(".a-price-whole")
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price_text = price_elem.get_text(strip=True).replace(",", "").rstrip(".").strip()
                    price = float(price_text)
                    
                    mrp_elem = soup.select_one(".a-text-price .a-offscreen")
                    if mrp_elem:
                        mrp_text = mrp_elem.get_text(strip=True).replace("₹", "").replace(",", "").strip()
                        mrp = float(mrp_text)
                    else:
                        mrp = price
                        
                    asin = url.split("/dp/")[1].split("/")[0].split("?")[0] if "/dp/" in url else "unknown_asin"
                    
                    img_elem = soup.select_one("#landingImage")
                    image_url = img_elem.get("src") if img_elem else None
                    
                    brand_elem = soup.select_one("#bylineInfo")
                    brand = brand_elem.get_text(strip=True) if brand_elem else None
                    if brand and brand.startswith("Brand:"):
                        brand = brand.replace("Brand:", "").strip()
                    elif brand and brand.startswith("Visit the"):
                        brand = brand.replace("Visit the", "").replace("Store", "").strip()

                    cat_elem = soup.select_one("#wayfinding-breadcrumbs_container")
                    category = cat_elem.get_text(separator=" > ", strip=True) if cat_elem else None

                    logging.info(f"Fast HTTP fetch succeeded for {url}")
                    return {
                        "product_id": asin,
                        "current_price": price,
                        "mrp_shown": mrp,
                        "title": title,
                        "platform": "amazon",
                        "image_url": image_url,
                        "brand": brand,
                        "category": category
                    }
        except Exception as e:
            logging.info(f"Fast HTTP fetch skipped for {url}: {e}")
        return None

    async def fetch_product_data(self, url: str) -> Dict[str, Any]:
        # Try fast lightweight HTTP fetch first to save RAM and avoid Chromium OOM
        fast_data = self._fast_http_fetch(url)
        if fast_data:
            return fast_data

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                timeout=30000,
                args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                title_element = await page.query_selector("#productTitle")
                title = await title_element.inner_text() if title_element else "Unknown Title"
                title = title.strip()
                
                price_element = await page.query_selector(".a-price-whole")
                if price_element:
                    price_text = await price_element.inner_text()
                    price = float(price_text.replace(",", "").strip())
                else:
                    raise PriceExtractionError("Could not find price element on Amazon page")
                    
                mrp_element = await page.query_selector(".a-text-price .a-offscreen")
                if mrp_element:
                    mrp_text = await mrp_element.inner_text()
                    mrp = float(mrp_text.replace("₹", "").replace(",", "").strip())
                else:
                    mrp = price
                
                asin = url.split("/dp/")[1].split("/")[0].split("?")[0] if "/dp/" in url else "unknown_asin"
                
                # Image
                image_element = await page.query_selector("#landingImage")
                image_url = await image_element.get_attribute("src") if image_element else None
                
                # Brand
                brand_element = await page.query_selector("#bylineInfo")
                brand = await brand_element.inner_text() if brand_element else None
                if brand and brand.startswith("Brand:"):
                    brand = brand.replace("Brand:", "").strip()
                elif brand and brand.startswith("Visit the"):
                    brand = brand.replace("Visit the", "").replace("Store", "").strip()
                    
                # Category
                category_element = await page.query_selector("#wayfinding-breadcrumbs_container")
                category = await category_element.inner_text() if category_element else None
                if category:
                    category = " > ".join([c.strip() for c in category.split("\n") if c.strip() and c.strip() != "›"])

                return {
                    "product_id": asin,
                    "current_price": price,
                    "mrp_shown": mrp,
                    "title": title,
                    "platform": "amazon",
                    "image_url": image_url,
                    "brand": brand,
                    "category": category
                }
            except PlaywrightTimeoutError as e:
                raise PriceExtractionError(f"Playwright Timeout: {str(e)}")
            except PriceExtractionError as e:
                raise e
            except Exception as e:
                logging.error(f"Error scraping Amazon URL {url}: {e}")
                return None
            finally:
                await browser.close()
