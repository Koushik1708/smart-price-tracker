import asyncio
from playwright.async_api import async_playwright
import multiprocessing

async def test():
    print('Starting p')
    async with async_playwright() as p:
        print('Launching browser')
        browser = await p.chromium.launch(headless=True)
        print('Browser launched')
        await browser.close()
        print('Closed')

def worker():
    print('Worker started')
    asyncio.run(test())
    print('Worker finished')

if __name__ == '__main__':
    p = multiprocessing.Process(target=worker)
    p.start()
    p.join()
