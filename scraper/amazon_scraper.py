from scraper.base import BaseScraper, PriceExtractionError
from typing import Dict, Any
import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

class AmazonScraper(BaseScraper):
    async def fetch_product_data(self, url: str) -> Dict[str, Any]:
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
