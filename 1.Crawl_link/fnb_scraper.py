"""
Google Maps F&B Scraper - PRODUCTION RESILIENT VERSION
Thu thập 1.500 quán F&B tại TP.HCM và Hà Nội (khoảng 750 HCM / 750 HN)
Điều kiện: reviews >= 300, rating 3.0–4.4
Chống crash do khóa file, tự động cân bằng giữa 2 thành phố.
"""

import asyncio
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Đảm bảo stdout dùng UTF-8 trên Windows
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ─── CẤU HÌNH ───────────────────────────────────────────────────────────────
OUTPUT_DIR    = Path(__file__).resolve().parent
CSV_FILE      = OUTPUT_DIR / "fnb_hcm_hn_1500_leads.csv"
XLSX_FILE     = OUTPUT_DIR / "fnb_hcm_hn_1500_leads.xlsx"
PROGRESS_FILE = OUTPUT_DIR / "scraper_progress.json"
BACKUP_JSONL  = OUTPUT_DIR / "fnb_leads_backup.jsonl"
LOG_FILE      = OUTPUT_DIR / "scraper_log.txt"

TARGET_TOTAL      = 1500
MIN_REVIEWS       = 300
MIN_RATING        = 3.0
MAX_RATING        = 4.4
SCROLL_DELAY_MIN  = 1.5
SCROLL_DELAY_MAX  = 3.0
QUERY_DELAY_MIN   = 2.0
QUERY_DELAY_MAX   = 4.0

# ─── PHÂN VÙNG & TỪ KHÓA ───────────────────────────────────────────────────
KEYWORDS_FB = [
    "nhà hàng", "quán ăn", "quán nhậu", "quán lẩu", "quán nướng BBQ",
    "buffet", "quán cafe", "trà sữa", "tiệm bánh", "quán phở",
    "quán bún", "cơm niêu",
]

DISTRICTS_HCM = [
    "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", "Quận 7",
    "Quận 8", "Quận 10", "Quận 11", "Quận 12",
    "Bình Thạnh", "Phú Nhuận", "Gò Vấp", "Tân Bình", "Tân Phú", "Bình Tân",
    "TP Thủ Đức", "Thủ Đức", "Quận 2", "Quận 9",
    "Bình Chánh", "Nhà Bè", "Hóc Môn",
]

DISTRICTS_HN = [
    "Hoàn Kiếm", "Ba Đình", "Đống Đa", "Hai Bà Trưng", "Cầu Giấy",
    "Thanh Xuân", "Tây Hồ", "Hoàng Mai", "Long Biên", "Hà Đông",
    "Nam Từ Liêm", "Bắc Từ Liêm",
    "Gia Lâm", "Đông Anh", "Hoài Đức", "Thanh Trì",
]

# ─── LOGGING ────────────────────────────────────────────────────────────────
def log(msg: str):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ─── CHECKPOINT ─────────────────────────────────────────────────────────────
def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ Lỗi đọc progress file: {e}")
    return {"completed_queries": [], "total_collected": 0}

def save_progress(progress: dict):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ Lỗi lưu progress: {e}")

# ─── CSV / XLSX ──────────────────────────────────────────────────────────────
FIELDNAMES = [
    "stt", "ten_quan", "thanh_pho", "quan_huyen", "phan_loai",
    "diem_danh_gia", "so_luong_danh_gia", "dia_chi",
    "so_dien_thoai", "google_maps_url",
]

pending_csv_rows = []

def load_existing_leads() -> tuple[list, set, set]:
    leads, urls, name_addr = [], set(), set()
    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row["stt"] = int(row["stt"])
                    except Exception:
                        pass
                    try:
                        row["diem_danh_gia"] = float(row["diem_danh_gia"])
                    except Exception:
                        pass
                    try:
                        row["so_luong_danh_gia"] = int(float(row["so_luong_danh_gia"]))
                    except Exception:
                        pass

                    leads.append(row)
                    if row.get("google_maps_url"):
                        urls.add(row["google_maps_url"])
                    key = (
                        row.get("ten_quan", "").strip().lower(),
                        row.get("dia_chi",  "").strip().lower()[:30],
                    )
                    name_addr.add(key)
        except Exception as e:
            log(f"⚠️ Lỗi khi đọc file CSV hiện tại: {e}")
    return leads, urls, name_addr

def append_to_csv(rows: list[dict]):
    global pending_csv_rows
    if not rows and not pending_csv_rows:
        return

    # 1. Luôn ghi nối tiếp vào JSONL backup (không bao giờ bị khóa bởi Excel)
    if rows:
        try:
            with open(BACKUP_JSONL, "a", encoding="utf-8") as f_jl:
                for r in rows:
                    f_jl.write(json.dumps(r, ensure_ascii=False) + "\n")
        except Exception as e:
            log(f"  [LỖI GHI JSONL BACKUP] {e}")

    to_write = pending_csv_rows + (rows if rows else [])

    # 2. Thử ghi vào CSV với cơ chế retry và bắt PermissionError
    for attempt in range(4):
        try:
            file_exists = CSV_FILE.exists() and CSV_FILE.stat().st_size > 0
            with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(to_write)
            # Thành công
            pending_csv_rows = []
            return
        except PermissionError:
            log(f"  ⚠️ [KHÓA FILE] CSV đang bị mở (Excel), thử lại sau 2s ({attempt+1}/4)...")
            time.sleep(2)
        except Exception as e:
            log(f"  ⚠️ [LỖI GHI CSV] {e}")
            break

    # Nếu vẫn bị khóa, lưu vào danh sách chờ pending
    pending_csv_rows = to_write
    log(f"  ⚠️ [TẠM LƯU BỘ ĐỆM] Đang giữ {len(pending_csv_rows)} hàng trong bộ nhớ & JSONL backup. Tiếp tục cào bình thường.")

def rewrite_csv_full(leads: list[dict]):
    global pending_csv_rows
    pending_csv_rows = []
    for attempt in range(10):
        try:
            with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(leads)
            log(f"✅ Đã ghi thành công {len(leads)} hàng vào {CSV_FILE.name}")
            return
        except PermissionError:
            log(f"  ⚠️ [KHÓA FILE] Vui lòng đóng Excel nếu đang mở {CSV_FILE.name}. Đợi 3s ({attempt+1}/10)...")
            time.sleep(3)
        except Exception as e:
            log(f"  ❌ Lỗi ghi file CSV: {e}")
            break

    # Fallback nếu vẫn bị khóa
    alt_file = OUTPUT_DIR / "fnb_hcm_hn_1500_leads_final.csv"
    try:
        with open(alt_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(leads)
        log(f"⚠️ Đã lưu bản sao vào {alt_file.name}")
    except Exception as e:
        log(f"  ❌ Lỗi lưu file dự phòng: {e}")

def save_xlsx(leads: list[dict]):
    df = pd.DataFrame(leads, columns=FIELDNAMES)
    for attempt in range(10):
        try:
            df.to_excel(XLSX_FILE, index=False, engine="openpyxl")
            log(f"✅ Đã lưu {len(df)} dòng vào {XLSX_FILE.name}")
            return
        except PermissionError:
            log(f"  ⚠️ Vui lòng đóng Excel nếu đang mở {XLSX_FILE.name}. Đợi 3s ({attempt+1}/10)...")
            time.sleep(3)
        except Exception as e:
            log(f"  ❌ Lỗi lưu Excel: {e}")
            break

    alt_xlsx = OUTPUT_DIR / "fnb_hcm_hn_1500_leads_final.xlsx"
    try:
        df.to_excel(alt_xlsx, index=False, engine="openpyxl")
        log(f"⚠️ Đã lưu bản sao Excel vào {alt_xlsx.name}")
    except Exception as e:
        log(f"  ❌ Lỗi lưu file Excel dự phòng: {e}")

# ─── PARSE HELPERS ───────────────────────────────────────────────────────────
def parse_rating_reviews_from_aria(aria_label: str) -> tuple[float | None, int | None]:
    if not aria_label:
        return None, None

    # Rating: số dạng X,X hoặc X.X
    rating_m = re.search(r"(\d[,\.]\d)", aria_label)
    rating = float(rating_m.group(1).replace(",", ".")) if rating_m else None

    # Reviews: các chữ số liên tiếp
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

def parse_rating_reviews_from_text(text: str) -> tuple[float | None, int | None]:
    m = re.search(r"(\d[,\.]\d)\s*\(([0-9][0-9.]*)\)", text)
    if m:
        rating  = float(m.group(1).replace(",", "."))
        reviews = int(m.group(2).replace(".", "").replace(",", ""))
        return rating, reviews
    return None, None

def extract_category_address(text: str, name: str) -> tuple[str, str, str]:
    """Trả về (category, address, phone)"""
    cleaned = text
    if name and name in cleaned:
        cleaned = cleaned.replace(name, "", 2)

    cleaned = re.sub(r"\d[,\.]\d\s*\([0-9.]+\)", "", cleaned)

    # Tìm số điện thoại nếu có
    phone = ""
    phone_m = re.search(r"(?:\+84|0)(?:[ .\-]?\d){8,10}\b", text)
    if phone_m:
        phone = re.sub(r"[^\d+]", "", phone_m.group(0))

    parts = re.split(r"[·\n]", cleaned)
    parts = [p.strip() for p in parts if p.strip()]

    category = ""
    address  = ""

    if parts:
        cat_part = parts[0]
        if not re.search(r"\d", cat_part) and len(cat_part) > 2:
            category = cat_part
            parts = parts[1:]

        for part in parts:
            if re.search(r"\d", part) and len(part) > 5:
                address = part.strip()
                break

    return category, address, phone

def detect_category(name: str, raw_category: str, keyword: str) -> str:
    src = (name + " " + raw_category + " " + keyword).lower()

    if any(k in src for k in ["cafe", "cà phê", "coffee", "caphe"]):
        return "Quán café"
    if any(k in src for k in ["trà sữa", "milk tea", "boba", "tra sua"]):
        return "Trà sữa"
    if any(k in src for k in ["bánh", "bakery", "cake", "tiem banh"]):
        return "Tiệm bánh"
    if any(k in src for k in ["phở", "pho", "bún", "bun", "hủ tiếu", "mì", "noodle", "bún chả"]):
        return "Quán phở/bún"
    if any(k in src for k in ["lẩu", "hotpot", "lau"]):
        return "Quán lẩu"
    if any(k in src for k in ["nướng", "bbq", "grille", "nuong"]):
        return "Quán nướng/BBQ"
    if any(k in src for k in ["buffet"]):
        return "Buffet"
    if any(k in src for k in ["nhậu", "bia", "pub", "bar"]):
        return "Quán nhậu/Bar"
    if any(k in src for k in ["cơm", "com niêu", "cơm niêu", "rice"]):
        return "Cơm niêu/Quán cơm"
    if "nhà hàng" in src:
        return "Nhà hàng"
    return "Quán ăn"

def extract_district(address: str, district_hint: str, city: str) -> str:
    if not address:
        return district_hint

    hn_districts = [
        "Hoàn Kiếm", "Ba Đình", "Đống Đa", "Hai Bà Trưng", "Cầu Giấy",
        "Thanh Xuân", "Tây Hồ", "Hoàng Mai", "Long Biên", "Hà Đông",
        "Nam Từ Liêm", "Bắc Từ Liêm", "Gia Lâm", "Đông Anh",
        "Hoài Đức", "Thanh Trì",
    ]
    hcm_specials = [
        "Thủ Đức", "Bình Thạnh", "Phú Nhuận", "Gò Vấp", "Tân Bình",
        "Tân Phú", "Bình Tân", "Bình Chánh", "Nhà Bè", "Hóc Môn",
    ]

    m = re.search(r"Qu[aậ]n\s+\d+", address, re.IGNORECASE)
    if m:
        return m.group(0)

    for d in hcm_specials + hn_districts:
        if d.lower() in address.lower():
            return d

    return district_hint

def normalize_url(href: str) -> str:
    if not href:
        return ""
    base = href.split("?")[0]
    if "/data=" in base:
        base = base.split("/data=")[0]
    return base.strip()

# ─── SCRAPE MỘT TRUY VẤN ────────────────────────────────────────────────────
async def scrape_query(
    page,
    query: str,
    district: str,
    city: str,
    keyword: str,
    existing_urls: set,
    existing_name_addr: set,
) -> list[dict]:
    results = []
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(2.5, 3.8))

        try:
            feed = await page.wait_for_selector('[role="feed"]', timeout=12000)
        except PlaywrightTimeoutError:
            log(f"  No feed for: {query}")
            return results

        scroll_count = 0
        max_scrolls  = 25
        while scroll_count < max_scrolls:
            await feed.evaluate("el => el.scrollBy(0, 1200)")
            await asyncio.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))
            scroll_count += 1

            try:
                body = await page.evaluate("document.body.innerText")
                if ("đã xem hết" in body.lower() or
                    "reached the end" in body.lower() or
                    "you've reached" in body.lower()):
                    break
            except Exception:
                pass

        articles = await page.query_selector_all('[role="article"]')

        for art in articles:
            try:
                link_el = await art.query_selector('a[href*="/maps/place"]')
                if not link_el:
                    continue
                name = (await link_el.text_content() or "").strip()
                if not name:
                    continue

                href = await link_el.get_attribute("href") or ""
                url  = normalize_url(href)

                rating, reviews = None, None

                # Cách 1: aria-label SPAN
                span_aria = await art.query_selector(
                    'span[aria-label*="sao"], span[aria-label*="star"]'
                )
                if span_aria:
                    aria_label = await span_aria.get_attribute("aria-label") or ""
                    rating, reviews = parse_rating_reviews_from_aria(aria_label)

                # Cách 2: Text fallback
                if rating is None or reviews is None:
                    full_text = await art.text_content() or ""
                    r2, rv2 = parse_rating_reviews_from_text(full_text)
                    if rating is None:
                        rating = r2
                    if reviews is None:
                        reviews = rv2

                # ── BỘ LỌC BẮT BUỘC (STRICT FILTERS) ──────────────────────────
                if rating is None or reviews is None:
                    continue
                if not (MIN_RATING <= rating <= MAX_RATING):
                    continue
                if reviews < MIN_REVIEWS:
                    continue

                # Parse category, address, phone
                full_text = await art.text_content() or ""
                raw_cat, address, phone = extract_category_address(full_text, name)
                phan_loai = detect_category(name, raw_cat, keyword)
                quan_huyen = extract_district(address, district, city)

                # ── KHỬ TRÙNG LẶP (DEDUPLICATION) ─────────────────────────────
                if url and url in existing_urls:
                    continue
                name_addr_key = (name.lower(), address.lower()[:30])
                if name_addr_key in existing_name_addr:
                    continue

                existing_urls.add(url)
                existing_name_addr.add(name_addr_key)

                results.append({
                    "stt": 0,
                    "ten_quan":          name,
                    "thanh_pho":         city,
                    "quan_huyen":        quan_huyen,
                    "phan_loai":         phan_loai,
                    "diem_danh_gia":     rating,
                    "so_luong_danh_gia": reviews,
                    "dia_chi":           address,
                    "so_dien_thoai":     phone,
                    "google_maps_url":   url,
                })

            except Exception:
                pass

    except Exception as e:
        log(f"  Error query '{query}': {e}")

    return results

# ─── MAIN ───────────────────────────────────────────────────────────────────
async def main():
    log("=" * 60)
    log("SCRAPER F&B GOOGLE MAPS - PRODUCTION RESILIENT")
    log(f"Target: {TARGET_TOTAL} | Rating: {MIN_RATING}-{MAX_RATING} | Reviews >= {MIN_REVIEWS}")
    log("=" * 60)

    progress = load_progress()
    leads, existing_urls, existing_name_addr = load_existing_leads()
    log(f"📂 Đã nạp thành công {len(leads)} quán từ file hiện tại")
    cnt_hcm = sum(1 for x in leads if x.get("thanh_pho") == "TP.HCM")
    cnt_hn  = sum(1 for x in leads if x.get("thanh_pho") == "Hà Nội")
    log(f"   Trong đó: TP.HCM = {cnt_hcm} quán | Hà Nội = {cnt_hn} quán")

    completed_set = set(progress.get("completed_queries", []))

    # Tách truy vấn theo 2 thành phố
    queries_hn = []
    queries_hcm = []
    for kw in KEYWORDS_FB:
        for district in DISTRICTS_HN:
            q = f"{kw} {district} Hà Nội"
            if q not in completed_set:
                queries_hn.append((q, district, "Hà Nội", kw))
        for district in DISTRICTS_HCM:
            q = f"{kw} {district} TP.HCM"
            if q not in completed_set:
                queries_hcm.append((q, district, "TP.HCM", kw))

    random.seed(42)
    random.shuffle(queries_hn)
    random.shuffle(queries_hcm)

    log(f"📋 Truy vấn còn lại: Hà Nội = {len(queries_hn)} | TP.HCM = {len(queries_hcm)}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--lang=vi-VN",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        query_step = 0
        while len(leads) < TARGET_TOTAL and (queries_hn or queries_hcm):
            # Cân bằng thông minh: ưu tiên thành phố đang có ít quán hơn
            cnt_hcm = sum(1 for x in leads if x.get("thanh_pho") == "TP.HCM")
            cnt_hn  = sum(1 for x in leads if x.get("thanh_pho") == "Hà Nội")

            if cnt_hn < cnt_hcm and queries_hn:
                query_tuple = queries_hn.pop(0)
            elif queries_hcm:
                query_tuple = queries_hcm.pop(0)
            elif queries_hn:
                query_tuple = queries_hn.pop(0)
            else:
                break

            q, district, city, keyword = query_tuple
            query_step += 1
            remaining = TARGET_TOTAL - len(leads)
            log(f"\n[Step {query_step}] '{q}' (HCM:{cnt_hcm} | HN:{cnt_hn}) | Còn thiếu: {remaining}")

            new_items = await scrape_query(
                page, q, district, city, keyword,
                existing_urls, existing_name_addr,
            )

            if new_items:
                start_stt = len(leads) + 1
                for i, item in enumerate(new_items):
                    item["stt"] = start_stt + i
                leads.extend(new_items)
                append_to_csv(new_items)
                cnt_hcm_now = sum(1 for x in leads if x.get("thanh_pho") == "TP.HCM")
                cnt_hn_now  = sum(1 for x in leads if x.get("thanh_pho") == "Hà Nội")
                log(f"  ✅ +{len(new_items)} mới | Tổng: {len(leads)}/{TARGET_TOTAL} (HCM:{cnt_hcm_now}, HN:{cnt_hn_now})")
            else:
                log(f"  ➖ 0 quán thỏa điều kiện lọc")

            progress["completed_queries"].append(q)
            progress["total_collected"] = len(leads)
            save_progress(progress)

            # Thử ghi lại pending nếu có
            if pending_csv_rows:
                append_to_csv([])

            # Đổi context định kỳ mỗi 30 queries để giải phóng bộ nhớ
            if query_step % 30 == 0:
                log("🔄 Dọn dẹp bộ nhớ browser context định kỳ...")
                try:
                    await page.close()
                    await context.close()
                    context = await browser.new_context(
                        viewport={"width": 1366, "height": 768},
                        locale="vi-VN",
                        timezone_id="Asia/Ho_Chi_Minh",
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"
                        ),
                    )
                    page = await context.new_page()
                except Exception as e:
                    log(f"  Lỗi làm mới browser context: {e}")

            await asyncio.sleep(random.uniform(QUERY_DELAY_MIN, QUERY_DELAY_MAX))

        await browser.close()

    # ─── HẬU XỬ LÝ & KIỂM TRA CHẤT LƯỢNG (QC) ──────────────────────────────
    log("\n" + "=" * 60)
    log("📊 KIỂM TRA CHẤT LƯỢNG DỮ LIỆU & XUẤT BẢN FILE CHÍNH THỨC")
    log("=" * 60)

    if not leads:
        log("❌ Không có dữ liệu để xử lý!")
        return

    # Nếu nhiều hơn 1500, lấy đúng 1500 dòng đầu tiên hoặc giữ tất cả
    final_leads = leads[:TARGET_TOTAL] if len(leads) >= TARGET_TOTAL else leads

    # Đánh lại STT chuẩn từ 1 đến N
    for i, row in enumerate(final_leads, 1):
        row["stt"] = i

    # Ghi toàn bộ dữ liệu ra CSV và XLSX
    rewrite_csv_full(final_leads)
    save_xlsx(final_leads)

    df = pd.DataFrame(final_leads)
    df["diem_danh_gia"]     = pd.to_numeric(df["diem_danh_gia"],     errors="coerce")
    df["so_luong_danh_gia"] = pd.to_numeric(df["so_luong_danh_gia"], errors="coerce")

    total        = len(df)
    valid_rating = df[(df["diem_danh_gia"] >= MIN_RATING) & (df["diem_danh_gia"] <= MAX_RATING)]
    valid_rev    = df[df["so_luong_danh_gia"] >= MIN_REVIEWS]
    dup_urls     = df[
        df["google_maps_url"].duplicated(keep=False) &
        df["google_maps_url"].notna() &
        (df["google_maps_url"] != "")
    ]
    cnt_hcm = len(df[df["thanh_pho"] == "TP.HCM"])
    cnt_hn  = len(df[df["thanh_pho"] == "Hà Nội"])

    log(f"  📌 Tổng số dòng duy nhất         : {total}")
    log(f"  ⭐ Đạt rating 3.0 đến 4.4        : {len(valid_rating)} / {total} ({len(valid_rating)/total*100:.1f}%)")
    log(f"  📝 Đạt reviews >= 300            : {len(valid_rev)} / {total} ({len(valid_rev)/total*100:.1f}%)")
    log(f"  🔁 Trùng lặp URL Google Maps     : {len(dup_urls)}")
    log(f"  🏙️ TP. Hồ Chí Minh               : {cnt_hcm} quán")
    log(f"  🏛️ Hà Nội                        : {cnt_hn} quán")

    if total >= TARGET_TOTAL and len(valid_rating) == total and len(valid_rev) == total and len(dup_urls) == 0:
        log("\n🎉 HOÀN TẤT XUẤT SẮC! TOÀN BỘ 1.500 QUÁN ĐỀU ĐẠT CHUẨN.")
    else:
        log("\n⚠️ CẦN KIỂM TRA THÊM THEO LOG TRÊN.")

    log(f"\n📁 File CSV : {CSV_FILE}")
    log(f"📁 File XLSX: {XLSX_FILE}")
    log("🏁 CHƯƠNG TRÌNH KẾT THÚC THÀNH CÔNG.")


if __name__ == "__main__":
    asyncio.run(main())
