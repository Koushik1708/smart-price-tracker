import asyncio
from playwright.async_api import async_playwright

async def test():
    print('Starting p')
    async with async_playwright() as p:
        print('Launching browser')
        browser = await p.chromium.launch(headless=True)
        print('Browser launched')
        await browser.close()
        print('Closed')

if __name__ == '__main__':
    asyncio.run(test())
