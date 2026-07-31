import asyncio
from scraper.amazon_scraper import AmazonScraper

async def main():
    s = AmazonScraper()
    res = await s.fetch_product_data('https://www.amazon.in/dp/B0CHX1W1XY')
    print("RESULT:", res)

if __name__ == "__main__":
    asyncio.run(main())
