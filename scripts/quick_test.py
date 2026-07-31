import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.amazon_scraper import AmazonScraper
from scraper.flipkart_scraper import FlipkartScraper

async def test_live():
    print("Testing Amazon Scraper...")
    amazon = AmazonScraper()
    # Live URL for an iPhone 13
    amazon_url = "https://www.amazon.in/Apple-iPhone-13-128GB-Midnight/dp/B09G9HD6PD"
    amz_data = await amazon.fetch_product_data(amazon_url)
    print(f"Amazon Result: {amz_data}")
    
    print("\nTesting Flipkart Scraper...")
    flipkart = FlipkartScraper()
    # Live URL for an iPhone 15
    flipkart_url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"
    fk_data = await flipkart.fetch_product_data(flipkart_url)
    print(f"Flipkart Result: {fk_data}")

if __name__ == "__main__":
    asyncio.run(test_live())
