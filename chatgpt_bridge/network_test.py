import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        print("测试访问 https://www.baidu.com ...")
        browser = await p.chromium.launch(channel="msedge", headless=False)
        page = await browser.new_page()
        try:
            await page.goto("https://www.baidu.com", timeout=30000)
            print("百度访问成功:", await page.title())
        except Exception as e:
            print("百度访问失败:", e)
        finally:
            await browser.close()

        print("\n测试访问 https://chatgpt.com ...")
        browser2 = await p.chromium.launch(channel="msedge", headless=False)
        page2 = await browser2.new_page()
        try:
            await page2.goto("https://chatgpt.com", timeout=30000)
            print("ChatGPT 访问成功:", await page2.title())
        except Exception as e:
            print("ChatGPT 访问失败:", e)
        finally:
            await browser2.close()

asyncio.run(test())
