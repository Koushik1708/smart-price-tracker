import asyncio
from scraper.flipkart_scraper import FlipkartScraper

async def main():
    s = FlipkartScraper()
    res = await s.fetch_product_data('https://www.flipkart.com/product/p/itm6ac6485515ae4?pid=itm6ac6485515ae4')
    print("RESULT:", res)

if __name__ == "__main__":
    asyncio.run(main())
