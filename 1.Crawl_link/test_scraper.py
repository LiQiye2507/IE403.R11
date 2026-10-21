"""Test scraper với 1 truy vấn để kiểm tra selectors"""
import asyncio
import re
import random
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def test_one_query():
    query = "nhà hàng Quận 1 TP.HCM"
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    print(f"Testing: {search_url}")
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--lang=vi-VN"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # Lưu HTML để phân tích
        content = await page.content()
        with open("test_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved HTML: {len(content)} bytes")
        
        # Thử tìm feed
        try:
            feed = await page.wait_for_selector('[role="feed"]', timeout=10000)
            print("Found feed!")
        except:
            print("No feed found - checking page structure...")
            # Thử selector khác
            main = await page.query_selector('div[aria-label*="Kết quả"]')
            if main:
                print("Found aria-label results div")
            all_divs = await page.query_selector_all('[jsaction]')
            print(f"Divs with jsaction: {len(all_divs)}")
            await browser.close()
            return
        
        # Cuộn nhẹ 3 lần
        for i in range(5):
            await feed.evaluate("el => el.scrollBy(0, 800)")
            await asyncio.sleep(1.5)
        
        # Thử các cách lấy items khác nhau
        items_v1 = await page.query_selector_all('[role="feed"] > div[jsaction]')
        items_v2 = await page.query_selector_all('[role="article"]')
        items_v3 = await page.query_selector_all('a[href*="/maps/place"]')
        print(f"Items v1 (div[jsaction]): {len(items_v1)}")
        print(f"Items v2 ([role=article]): {len(items_v2)}")
        print(f"Items v3 (a[href place]): {len(items_v3)}")
        
        # Phân tích item đầu tiên nếu có
        if items_v1:
            item = items_v1[0]
            inner = await item.inner_html()
            print(f"\n--- Item[0] inner HTML (500 chars) ---\n{inner[:500]}")
            
            # Tìm rating
            aria_els = await item.query_selector_all('[aria-label]')
            for el in aria_els[:10]:
                label = await el.get_attribute('aria-label')
                tag = await el.evaluate('el => el.tagName')
                txt = await el.text_content()
                print(f"  aria-label: '{label}' | tag: {tag} | text: '{txt[:30]}'")
        
        # Thử approach khác: tìm tất cả links đến places
        print("\n--- Place links ---")
        links = await page.query_selector_all('a[href*="/maps/place/"]')
        count = 0
        for link in links[:10]:
            href = await link.get_attribute('href')
            txt  = await link.text_content()
            print(f"  [{count}] {txt[:40]!r} -> {href[:80]}")
            count += 1
        print(f"Total place links: {len(links)}")
        
        await browser.close()
    print("Done!")

asyncio.run(test_one_query())
