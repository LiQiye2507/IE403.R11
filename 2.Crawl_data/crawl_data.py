"""
CRAWL DATA GOOGLE MAPS REVIEWS (30 REVIEWS / QUÁN) - HỖ TRỢ ĐĂNG NHẬP LƯU PROFILE
Đặc tính nổi bật:
1. Lưu phiên đăng nhập Google vĩnh viễn vào thư mục `./chrome_user_data`.
   - Lần đầu chạy: Nếu chưa đăng nhập, script sẽ tạm dừng để bạn đăng nhập tài khoản Google trên trình duyệt vừa mở, sau đó nhấn Enter để bắt đầu cào.
   - Các lần chạy sau: Tự động nhận diện đã đăng nhập và cào luôn đủ 30 reviews/quán.
2. Bypass lỗi 'Trình duyệt không an toàn' khi đăng nhập Google bằng cách dùng Chrome thực tế + ẩn cờ WebDriver.
3. Checkpoint thông minh: Chỉ tính là hoàn thành quán khi lấy được > 5 reviews (tránh bị kẹt ở mức 5 reviews của Limited View).
"""

import csv
import json
import os
import random
import re
import time
import urllib.parse
from collections import Counter
from playwright.sync_api import sync_playwright

# ==================== CẤU HÌNH ĐƯỜNG DẪN ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CANDIDATE_INPUT_PATHS = [
    os.path.join(BASE_DIR, "..", "1.Crawl_link", "fnb_hcm_hn_1500_leads.csv"),
    os.path.join(BASE_DIR, "1.Crawl_link", "fnb_hcm_hn_1500_leads.csv"),
    os.path.join(BASE_DIR, "fnb_hcm_hn_1500_leads.csv"),
]

INPUT_CSV = None
for path in CANDIDATE_INPUT_PATHS:
    if os.path.exists(path):
        INPUT_CSV = os.path.abspath(path)
        break

if not INPUT_CSV:
    INPUT_CSV = os.path.join(BASE_DIR, "fnb_hcm_hn_1500_leads.csv")

OUTPUT_CSV = os.path.join(BASE_DIR, "fnb_reviews_30_per_place.csv")
PROGRESS_JSON = os.path.join(BASE_DIR, "review_checkpoint.json")
USER_DATA_DIR = os.path.join(BASE_DIR, "chrome_user_data")

TARGET_REVIEWS_PER_PLACE = 30
MIN_VALID_REVIEWS = 6  # Quán nào trước đó chỉ lấy được <= 5 reviews (do chưa login) sẽ được cào lại


def sync_and_clean_csv():
    """
    Kiểm tra file OUTPUT_CSV hiện tại:
    - Những quán đã có >= 6 reviews được tính là hoàn thành hợp lệ.
    - Những quán chỉ có <= 5 reviews (do lần chạy trước chưa đăng nhập) sẽ được lọc bỏ để cào lại đủ 30 reviews.
    """
    if not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0:
        save_checkpoint(set())
        return set()

    rows = []
    url_counts = Counter()
    try:
        with open(OUTPUT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                url = row.get("google_maps_url", "").strip()
                if url:
                    rows.append(row)
                    url_counts[url] += 1

        # Chỉ giữ lại các quán đã lấy được > 5 reviews
        valid_urls = {url for url, count in url_counts.items() if count >= MIN_VALID_REVIEWS}
        cleaned_rows = [r for r in rows if r.get("google_maps_url", "").strip() in valid_urls]

        # Nếu có những dòng <= 5 reviews cũ, ghi lại file sạch
        if len(cleaned_rows) != len(rows) and fieldnames:
            with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cleaned_rows)
            print(f"[*] Đã dọn dẹp các quán bị giới hạn 5 reviews trước đó để cào lại đủ 30 reviews.")

        save_checkpoint(valid_urls)
        return valid_urls
    except Exception as e:
        print(f"[!] Lỗi đồng bộ CSV: {e}")
        return set()


def save_checkpoint(completed_urls):
    """Lưu danh sách URL đã hoàn thành vào file JSON."""
    try:
        temp_file = PROGRESS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"completed_urls": list(completed_urls)}, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, PROGRESS_JSON)
    except Exception as e:
        print(f"[!] Lỗi lưu checkpoint: {e}")


def init_output_csv():
    """Tạo file CSV đầu ra với header chuẩn nếu chưa có."""
    if not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0:
        with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "stt_quan",
                "ten_quan",
                "thanh_pho",
                "quan_huyen",
                "phan_loai",
                "google_maps_url",
                "stt_review",
                "ten_reviewer",
                "so_sao",
                "thoi_gian",
                "noi_dung_review",
                "so_luot_thich",
            ])


def append_reviews_to_csv(reviews_data):
    """Ghi nối tiếp danh sách review của quán vào CSV."""
    if not reviews_data:
        return
    with open(OUTPUT_CSV, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for r in reviews_data:
            writer.writerow([
                r.get("stt_quan", ""),
                r.get("ten_quan", ""),
                r.get("thanh_pho", ""),
                r.get("quan_huyen", ""),
                r.get("phan_loai", ""),
                r.get("google_maps_url", ""),
                r.get("stt_review", ""),
                r.get("ten_reviewer", ""),
                r.get("so_sao", ""),
                r.get("thoi_gian", ""),
                r.get("noi_dung_review", ""),
                r.get("so_luot_thich", "0"),
            ])


def ensure_google_logged_in(page):
    """
    Kiểm tra xem trình duyệt đã đăng nhập tài khoản Google chưa.
    Nếu chưa, mở trang đăng nhập và chờ người dùng đăng nhập thủ công 1 lần duy nhất.
    """
    print("\n[*] Đang kiểm tra trạng thái đăng nhập Google trên trình duyệt...")
    page.goto("https://www.google.com/maps?hl=vi", timeout=40000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Kiểm tra xem có nút "Đăng nhập" (Sign in) ở góc phải trên không
    sign_in_btn = page.locator('a[aria-label*="Đăng nhập"], a[href*="accounts.google.com/ServiceLogin"], button:has-text("Đăng nhập"), a:has-text("Sign in")')

    if sign_in_btn.count() > 0 and sign_in_btn.first.is_visible():
        print("\n" + "!" * 70)
        print(" [CẦN ĐĂNG NHẬP GOOGLE 1 LẦN DUY NHẤT]")
        print(" Hiện tại trình duyệt chưa đăng nhập nên Google Maps sẽ giới hạn chỉ hiện 5 reviews.")
        print(" -> Bước 1: Hãy nhìn vào cửa sổ Chrome vừa bật lên, bấm 'Đăng nhập' và đăng nhập tài khoản Google của bạn.")
        print(" -> Bước 2: Sau khi đăng nhập xong và thấy giao diện bản đồ Google Maps, hãy quay lại cửa sổ Terminal này và nhấn phím [ENTER] để bắt đầu cào tự động!")
        print("!" * 70)
        try:
            sign_in_btn.first.click(timeout=3000)
        except Exception:
            page.goto("https://accounts.google.com/ServiceLogin?hl=vi&continue=https://www.google.com/maps", timeout=40000)

        input("\n>>> Sau khi bạn đã đăng nhập Google xong trên trình duyệt, nhấn [ENTER] tại đây để tiếp tục... ")
        page.goto("https://www.google.com/maps?hl=vi", timeout=40000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        print("[✓] Đã lưu phiên đăng nhập vào thư mục 'chrome_user_data'! Bắt đầu cào dữ liệu...\n")
    else:
        print("[✓] Trình duyệt ĐÃ ĐĂNG NHẬP sẵn tài khoản Google! Chế độ Full Reviews đã kích hoạt.\n")


def open_place_detail_and_reviews_tab(page, place_info):
    """Mở trang chi tiết của quán và bấm vào tab Bài đánh giá."""
    ten_quan = place_info.get("ten_quan", "")
    quan_huyen = place_info.get("quan_huyen", "")
    thanh_pho = place_info.get("thanh_pho", "")
    dia_chi = place_info.get("dia_chi", "").split("Đang mở")[0].split("Đã đóng")[0].split("Mở cả")[0].strip()

    # Tìm kiếm cụ thể Tên quán + Địa chỉ + Quận + TP để vào đúng quán
    search_query = f"{ten_quan} {dia_chi} {quan_huyen} {thanh_pho}".strip()
    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}?hl=vi"

    page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    # Nếu kết quả trả về danh sách nhiều địa điểm -> Click vào địa điểm đầu tiên
    tabs = page.locator('button[role="tab"]')
    if tabs.count() < 2:
        first_card = page.locator('a.hfpxzc').first
        if first_card.count() > 0:
            try:
                first_card.click(timeout=5000)
                page.wait_for_timeout(2500)
            except Exception:
                pass

    # Tìm và click vào tab "Bài đánh giá" / "Reviews"
    tabs = page.locator('button[role="tab"]')
    clicked_tab = False
    for i in range(tabs.count()):
        tab = tabs.nth(i)
        label = (tab.inner_text() or "") + " " + (tab.get_attribute("aria-label") or "")
        if any(k in label.lower() for k in ["đánh giá", "reviews", "review"]):
            try:
                tab.click(timeout=5000)
                clicked_tab = True
                page.wait_for_timeout(2200)
                break
            except Exception:
                pass

    # Dự phòng: nếu chưa bấm được tab thì bấm vào nút tổng số bài đánh giá hoặc "Thêm bài đánh giá"
    if not clicked_tab:
        more_rev_btn = page.locator(
            'button[jsaction*="pane.rating.moreReviews"], '
            'button[aria-label*="bài đánh giá"], '
            'button:has-text("Thêm bài đánh giá"), '
            'button:has-text("More reviews")'
        ).first
        if more_rev_btn.count() > 0:
            try:
                more_rev_btn.click(timeout=4000)
                page.wait_for_timeout(2200)
            except Exception:
                pass


def scroll_reviews_container(page):
    """Cuộn danh sách đánh giá cho đến khi tải đủ tối thiểu 30 bài."""
    for _ in range(8):
        cards = page.locator('div[data-review-id].jftiEf, div.jftiEf')
        if cards.count() >= TARGET_REVIEWS_PER_PLACE:
            break

        # Tự động tìm thẻ cha có thanh cuộn dọc chứa các thẻ review
        scrolled = page.evaluate("""() => {
            const card = document.querySelector('div[data-review-id]') || document.querySelector('div.jftiEf');
            if (card) {
                let el = card.parentElement;
                while (el && el !== document.body) {
                    const style = window.getComputedStyle(el);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
                        el.scrollBy(0, 3500);
                        return true;
                    }
                    el = el.parentElement;
                }
            }
            const containers = document.querySelectorAll('div.m6QErb.DxyBCb, div[role="feed"]');
            for (const c of containers) {
                if (c.scrollHeight > c.clientHeight) {
                    c.scrollBy(0, 3500);
                    return true;
                }
            }
            return false;
        }""")

        if not scrolled:
            page.mouse.wheel(0, 3500)

        page.wait_for_timeout(random.randint(1200, 1800))


def expand_truncated_reviews(page):
    """Bấm mở rộng toàn bộ các nút 'Thêm' / 'Xem thêm' trong các bài đánh giá dài."""
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button.w8nwRe, button[aria-label*="Xem thêm"], button[aria-label*="More"]');
        btns.forEach(b => {
            try { b.click(); } catch (e) {}
        });
    }""")
    page.wait_for_timeout(600)


def parse_reviews_from_dom(page, place_info):
    """Trích xuất tối đa 30 bài đánh giá từ DOM."""
    raw_reviews = page.evaluate("""(maxLimit) => {
        const cards = Array.from(document.querySelectorAll('div[data-review-id].jftiEf, div.jftiEf'));
        const seenIds = new Set();
        const extracted = [];

        for (const card of cards) {
            const revId = card.getAttribute('data-review-id') || card.innerText.slice(0, 60);
            if (seenIds.has(revId)) continue;
            seenIds.add(revId);

            const authorEl = card.querySelector('.d4r55, .WNxFfd');
            const author = authorEl ? authorEl.innerText.trim() : 'Ẩn danh';

            let rating = '';
            const starEl = card.querySelector('span.kvMYJc, span[role="img"][aria-label*="sao"], span[role="img"][aria-label*="star"]');
            if (starEl) {
                const label = starEl.getAttribute('aria-label') || '';
                const m = label.match(/(\\d+([\\.,]\\d+)?)/);
                if (m) rating = m[1].replace(',', '.');
            }

            const timeEl = card.querySelector('.rsqaWe');
            const timeText = timeEl ? timeEl.innerText.trim() : '';

            const textEl = card.querySelector('.wiI7pd');
            const reviewText = textEl ? textEl.innerText.replace(/\\s+/g, ' ').trim() : '';

            let likes = '0';
            const likeEl = card.querySelector('span.pkWtMe');
            if (likeEl && likeEl.innerText.trim()) {
                likes = likeEl.innerText.trim();
            }

            extracted.push({ author, rating, timeText, reviewText, likes });
            if (extracted.length >= maxLimit) break;
        }
        return extracted;
    }""", TARGET_REVIEWS_PER_PLACE)

    results = []
    for idx, item in enumerate(raw_reviews, start=1):
        results.append({
            "stt_quan": place_info.get("stt", ""),
            "ten_quan": place_info.get("ten_quan", ""),
            "thanh_pho": place_info.get("thanh_pho", ""),
            "quan_huyen": place_info.get("quan_huyen", ""),
            "phan_loai": place_info.get("phan_loai", ""),
            "google_maps_url": place_info.get("google_maps_url", ""),
            "stt_review": idx,
            "ten_reviewer": item.get("author", "Ẩn danh"),
            "so_sao": item.get("rating", ""),
            "thoi_gian": item.get("timeText", ""),
            "noi_dung_review": item.get("reviewText", ""),
            "so_luot_thich": item.get("likes", "0"),
        })
    return results


def extract_reviews_for_place(page, place_info):
    """Thực hiện cào review cho 1 quán."""
    place_name = place_info.get("ten_quan", "Quán")
    print(f"\n---> [{place_info.get('stt')}] Đang xử lý: {place_name} ({place_info.get('quan_huyen')}, {place_info.get('thanh_pho')})")

    open_place_detail_and_reviews_tab(page, place_info)
    scroll_reviews_container(page)
    expand_truncated_reviews(page)
    reviews = parse_reviews_from_dom(page, place_info)

    print(f"     Tìm thấy và trích xuất được: {len(reviews)} review.")
    return reviews


def main():
    print("=" * 70)
    print("   CÀO 30 REVIEWS GOOGLE MAPS (CÓ ĐĂNG NHẬP & LƯU PROFILE VĨNH VIỄN)")
    print("=" * 70)

    if not os.path.exists(INPUT_CSV):
        print(f"[!] Không tìm thấy file đầu vào: {INPUT_CSV}")
        return

    init_output_csv()
    completed_urls = sync_and_clean_csv()
    print(f"[*] Checkpoint hợp lệ (>= {MIN_VALID_REVIEWS} reviews/quán): Đã xong {len(completed_urls)} quán.")

    places = []
    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            places.append(row)

    total_places = len(places)
    remaining_places = [p for p in places if p.get("google_maps_url", "").strip() not in completed_urls]
    print(f"[*] Tổng số quán: {total_places} | Cần cào tiếp: {len(remaining_places)}")

    if not remaining_places:
        print("[✓] Đã cào đầy đủ toàn bộ danh sách!")
        return

    with sync_playwright() as p:
        # Sử dụng launch_persistent_context để lưu giữ Cookie đăng nhập Google vào ./chrome_user_data
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="chrome",  # Ưu tiên mở bằng trình duyệt Google Chrome thật trên máy để không bị chặn đăng nhập
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                ignore_default_args=["--enable-automation"],
                locale="vi-VN",
                viewport={"width": 1366, "height": 850},
            )
        except Exception:
            # Dự phòng nếu máy chưa cài Chrome bản chuẩn thì dùng Chromium đi kèm Playwright
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                ignore_default_args=["--enable-automation"],
                locale="vi-VN",
                viewport={"width": 1366, "height": 850},
            )

        page = context.pages[0] if context.pages else context.new_page()
        # Ẩn thuộc tính navigator.webdriver để tránh bị Google phát hiện bot khi login
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Bước kiểm tra và hỗ trợ đăng nhập Google
        ensure_google_logged_in(page)

        try:
            for place in remaining_places:
                url = place.get("google_maps_url", "").strip()
                if not url:
                    continue

                try:
                    reviews = extract_reviews_for_place(page, place)

                    if len(reviews) >= MIN_VALID_REVIEWS:
                        append_reviews_to_csv(reviews)
                        completed_urls.add(url)
                        save_checkpoint(completed_urls)
                        print(f"     [✓] Đã lưu {len(reviews)} review. Tiến độ: {len(completed_urls)}/{total_places} quán.")
                    elif len(reviews) > 0:
                        print(f"     [!] Chỉ lấy được {len(reviews)} review (có thể do chưa đăng nhập hoặc bị giới hạn tạm thời). Chưa đánh dấu hoàn thành để thử lại sau.")
                    else:
                        print(f"     [!] Lấy được 0 review. Bỏ qua tạm thời để thử lại ở lần chạy sau.")

                except Exception as err:
                    print(f"     [X] Lỗi xử lý quán {place.get('ten_quan')}: {err}")

                time.sleep(random.uniform(1.8, 3.0))

        except KeyboardInterrupt:
            print("\n[!] Đã tạm dừng chương trình (Ctrl+C). Phiên đăng nhập và tiến trình đã được lưu an toàn!")
        finally:
            context.close()

    print("\n" + "=" * 70)
    print(f"[✓] Dữ liệu đã lưu tại: {OUTPUT_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    main()