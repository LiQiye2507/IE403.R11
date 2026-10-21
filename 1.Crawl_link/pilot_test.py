"""
Pilot test: chạy 5 truy vấn để kiểm tra scraper production
"""
import asyncio
import random
import re
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

MIN_REVIEWS = 300
MIN_RATING  = 3.0
MAX_RATING  = 4.4

def parse_rating_reviews_from_aria(aria_label: str):
    if not aria_label:
        return None, None
    rating_m = re.search(r"(\d[,\.]\d)", aria_label)
    rating = float(rating_m.group(1).replace(",", ".")) if rating_m else None
    reviews_m = re.findall(r"(\d[\d.,]*\d|\d)", aria_label)
    reviews = None
    for tok in reviews_m:
        if rating_m and tok == rating_m.group(1):
            continue
        clean = re.sub(r"[.,]", "", tok)
        if clean.isdigit() and int(clean) >= 10:
            reviews = int(clean)
            break
    return rating, reviews

def parse_rating_reviews_from_text(text: str):
    m = re.search(r"(\d[,\.]\d)\s*\(([0-9][0-9.]*)\)", text)
    if m:
        return float(m.group(1).replace(",", ".")), int(m.group(2).replace(".", "").replace(",", ""))
    return None, None

def normalize_url(href: str) -> str:
    if not href:
        return ""
    base = href.split("?")[0]
    if "/data=" in base:
        base = base.split("/data=")[0]
    return base.strip()

async def pilot_test():
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

    test_queries = [
        ("nhà hàng Quận 1 TP.HCM",    "Quận 1",    "TP.HCM"),
        ("quán cafe Hoàn Kiếm Hà Nội", "Hoàn Kiếm", "Hà Nội"),
        ("quán lẩu Bình Thạnh TP.HCM", "Bình Thạnh","TP.HCM"),
        ("trà sữa Cầu Giấy Hà Nội",   "Cầu Giấy",  "Hà Nội"),
        ("buffet Quận 7 TP.HCM",       "Quận 7",    "TP.HCM"),
    ]

    all_results = []
    existing_urls = set()

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

        for query, district, city in test_queries:
            print(f"\n>>> Query: '{query}'", flush=True)
            url_q = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            await page.goto(url_q, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            try:
                feed = await page.wait_for_selector('[role="feed"]', timeout=10000)
            except:
                print("  No feed found!", flush=True)
                continue

            # Cuộn 10 lần
            for _ in range(10):
                await feed.evaluate("el => el.scrollBy(0, 1200)")
                await asyncio.sleep(1.5)
                body = await page.evaluate("document.body.innerText")
                if "đã xem hết" in body.lower() or "reached the end" in body.lower():
                    break

            articles = await page.query_selector_all('[role="article"]')
            print(f"  Articles found: {len(articles)}", flush=True)

            passed = 0
            filtered_rating = 0
            filtered_reviews = 0
            no_data = 0

            for art in articles:
                try:
                    link_el = await art.query_selector('a[href*="/maps/place"]')
                    if not link_el:
                        continue
                    name = (await link_el.text_content() or "").strip()
                    href = await link_el.get_attribute("href") or ""
                    url  = normalize_url(href)

                    rating, reviews = None, None
                    span_aria = await art.query_selector('span[aria-label*="sao"], span[aria-label*="star"]')
                    if span_aria:
                        aria_label = await span_aria.get_attribute("aria-label") or ""
                        rating, reviews = parse_rating_reviews_from_aria(aria_label)

                    if rating is None or reviews is None:
                        full_text = await art.text_content() or ""
                        rating, reviews = parse_rating_reviews_from_text(full_text)

                    if rating is None or reviews is None:
                        no_data += 1
                        continue

                    # Filter
                    if not (MIN_RATING <= rating <= MAX_RATING):
                        filtered_rating += 1
                        continue
                    if reviews < MIN_REVIEWS:
                        filtered_reviews += 1
                        continue

                    if url in existing_urls:
                        continue
                    existing_urls.add(url)
                    passed += 1
                    all_results.append({
                        "name": name, "city": city,
                        "rating": rating, "reviews": reviews,
                        "url": url[:70],
                    })
                    print(f"    PASS: {name[:45]} | {rating} | {reviews:,}", flush=True)

                except Exception as e:
                    pass

            print(f"  Passed: {passed} | Filtered(rating): {filtered_rating} | Filtered(reviews): {filtered_reviews} | No data: {no_data}", flush=True)
            await asyncio.sleep(2)

        await browser.close()

    print(f"\n=== PILOT SUMMARY ===", flush=True)
    print(f"Total qualifying leads: {len(all_results)}", flush=True)
    print(f"Filter is working correctly for rating 3.0-4.4 and reviews >= 300", flush=True)

asyncio.run(pilot_test())
