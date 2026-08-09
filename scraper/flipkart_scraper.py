import json
from scraper.base import BaseScraper, PriceExtractionError
from typing import Dict, Any
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import re

class FlipkartScraper(BaseScraper):
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
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Extract application/ld+json scripts
                scripts = await page.locator('script[type="application/ld+json"]').all_inner_texts()
                
                product_data = None
                for script_text in scripts:
                    try:
                        data = json.loads(script_text)
                        # JSON-LD can be a list or a dict
                        if isinstance(data, list):
                            for item in data:
                                if item.get("@type") == "Product":
                                    product_data = item
                                    break
                        elif isinstance(data, dict):
                            if data.get("@type") == "Product":
                                product_data = data
                        
                        if product_data:
                            break
                    except json.JSONDecodeError:
                        continue
                        
                if not product_data:
                    # Fallback to h1 if JSON-LD fails
                    h1 = await page.query_selector("h1")
                    if not h1:
                        content = await page.content()
                        with open("failed_flipkart.html", "w", encoding="utf-8") as f:
                            f.write(content)
                        raise PriceExtractionError("Could not find product schema or h1 on Flipkart page")
                    title = await h1.inner_text()
                    content = await page.content()
                    with open("failed_flipkart.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    raise PriceExtractionError("Could not find JSON-LD price schema on Flipkart page")
                    
                title = product_data.get("name", "Unknown Title").strip()
                
                offers = product_data.get("offers", {})
                price = offers.get("price")
                if not price:
                    raise PriceExtractionError("Could not find price in JSON-LD schema")
                    
                price = float(price)
                
                # MRP is usually in the description like "Buy X for Rs.249.0 online."
                description = product_data.get("description", "")
                mrp_match = re.search(r"Rs\.([\d,]+(?:\.\d+)?)", description)
                if mrp_match:
                    mrp = float(mrp_match.group(1).replace(",", ""))
                else:
                    mrp = price
                
                # Extract canonical PID from current resolved URL
                current_url = page.url
                match = re.search(r"/p/(itm[a-zA-Z0-9]+)", current_url)
                if match:
                    pid = match.group(1)
                else:
                    pid = "unknown_pid"
                    
                image_url = product_data.get("image")
                if isinstance(image_url, list) and len(image_url) > 0:
                    image_url = image_url[0]
                    
                brand = product_data.get("brand", {}).get("name") if isinstance(product_data.get("brand"), dict) else None
                # Sometimes brand is just a string
                if not brand and isinstance(product_data.get("brand"), str):
                    brand = product_data.get("brand")
                    
                # Category might not be in Product JSON-LD, try to get from BreadcrumbList JSON-LD
                category = None
                for script_text in scripts:
                    try:
                        data = json.loads(script_text)
                        if isinstance(data, list):
                            for item in data:
                                if item.get("@type") == "BreadcrumbList":
                                    items = item.get("itemListElement", [])
                                    category = " > ".join([i.get("item", {}).get("name", "") for i in items if i.get("item", {}).get("name")])
                                    break
                        elif isinstance(data, dict):
                            if data.get("@type") == "BreadcrumbList":
                                items = data.get("itemListElement", [])
                                category = " > ".join([i.get("item", {}).get("name", "") for i in items if i.get("item", {}).get("name")])
                                break
                    except json.JSONDecodeError:
                        continue

                return {
                    "product_id": pid,
                    "current_price": price,
                    "mrp_shown": mrp,
                    "title": title,
                    "platform": "flipkart",
                    "image_url": image_url,
                    "brand": brand,
                    "category": category
                }
            except PlaywrightTimeoutError as e:
                raise PriceExtractionError(f"Playwright Timeout: {str(e)}")
            except PriceExtractionError as e:
                raise e
            except Exception as e:
                logging.error(f"Error scraping Flipkart URL {url}: {e}")
                return None
            finally:
                await browser.close()
