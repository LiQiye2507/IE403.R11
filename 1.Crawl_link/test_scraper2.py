"""Test chi tiết cấu trúc article để lấy rating, reviews, address"""
import asyncio
import re
import sys

async def test_article_structure():
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

    query = "nha hang Quan 1 TP.HCM"
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    print(f"Testing: {search_url}", flush=True)

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

        feed = await page.wait_for_selector('[role="feed"]', timeout=10000)
        print("Feed found!", flush=True)

        # Cuộn nhiều hơn để load thêm results
        for i in range(15):
            await feed.evaluate("el => el.scrollBy(0, 1000)")
            await asyncio.sleep(1.5)
            # Check end marker
            body_text = await page.evaluate("document.body.innerText")
            if "đã xem hết" in body_text.lower() or "reached the end" in body_text.lower():
                print(f"Reached end at scroll {i+1}", flush=True)
                break

        articles = await page.query_selector_all('[role="article"]')
        print(f"Total articles after scroll: {len(articles)}", flush=True)

        # Phân tích article đầu tiên chi tiết
        print("\n=== PHÂN TÍCH ARTICLE ĐẦU TIÊN ===", flush=True)
        if articles:
            art = articles[0]
            html = await art.inner_html()
            # Lưu để xem
            with open("article_sample.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Inner HTML saved ({len(html)} bytes)", flush=True)

            # Text content toàn bộ
            txt = await art.text_content()
            print(f"Full text: {repr(txt[:300])}", flush=True)

            # Tìm aria-labels
            print("\n--- aria-label elements ---", flush=True)
            aria_els = await art.query_selector_all('[aria-label]')
            for el in aria_els:
                label = await el.get_attribute('aria-label')
                tag = await el.evaluate('el => el.tagName')
                text = (await el.text_content() or "")[:40]
                print(f"  [{tag}] aria-label='{label}' | text='{text}'", flush=True)

        # Phân tích tất cả articles
        print("\n=== TẤT CẢ ARTICLES ===", flush=True)
        for i, art in enumerate(articles[:20]):
            try:
                # Tên - thử nhiều cách
                name = ""
                # Cách 1: aria-label trên article
                name_from_aria = await art.get_attribute('aria-label')
                if name_from_aria:
                    name = name_from_aria.strip()

                # Cách 2: link text
                link = await art.query_selector('a[href*="/maps/place"]')
                href = await link.get_attribute('href') if link else ""
                link_text = (await link.text_content() or "").strip() if link else ""

                # Cách 3: heading spans
                heading = await art.query_selector('[class*="fontHeadlineSmall"]')
                heading_text = (await heading.text_content() or "").strip() if heading else ""

                # Text content đầy đủ để tìm rating/reviews
                full_text = await art.text_content()
                full_text = full_text.strip() if full_text else ""

                # Tìm rating pattern "X.X" hoặc "(xxx)"
                rating_match = re.search(r'\b([3-5]\.[0-9])\b', full_text)
                reviews_match = re.search(r'\(([0-9][0-9.,\s]+)\)', full_text)

                rating = float(rating_match.group(1)) if rating_match else None
                reviews_str = reviews_match.group(1).replace(".", "").replace(",", "").strip() if reviews_match else None
                try:
                    reviews = int(reviews_str) if reviews_str else None
                except:
                    reviews = None

                print(f"[{i}] aria='{name[:40]}' | link='{link_text[:30]}' | heading='{heading_text[:30]}'", flush=True)
                print(f"     href='{href[:80]}'", flush=True)
                print(f"     rating={rating} | reviews={reviews}", flush=True)
                print(f"     text='{full_text[:150]}'", flush=True)
                print("", flush=True)

            except Exception as e:
                print(f"[{i}] Error: {e}", flush=True)

        await browser.close()

    print("Done!", flush=True)

asyncio.run(test_article_structure())
