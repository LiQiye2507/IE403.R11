# Module 1: Crawl Link & Dữ Liệu Quán F&B (Google Maps Scraper)

Thư mục này chứa toàn bộ mã nguồn, cấu hình, dữ liệu kiểm thử và kết quả thu thập liên kết cùng thông tin ban đầu của **1.500 quán F&B** tại **TP. Hồ Chí Minh** và **Hà Nội** từ Google Maps.

---

## 📌 1. Mục Tiêu & Tiêu Chí Thu Thập

- **Phạm vi địa lý**: Cân bằng giữa 2 thành phố lớn:
  - **TP. Hồ Chí Minh**: ~750 quán (Thực tế đạt: **752 quán**)
  - **Hà Nội**: ~750 quán (Thực tế đạt: **748 quán**)
- **Phân loại ngành hàng**: Nhà hàng, Quán ăn, Quán café, Trà sữa, Tiệm bánh, Quán lẩu, Quán nướng BBQ, Buffet, Quán nhậu/Bar, Quán phở/bún, Cơm niêu,...
- **Tiêu chí lọc bắt buộc (Strict Filters)**:
  - ⭐ **Rating (Điểm đánh giá)**: Trong khoảng **3.0 - 4.4 sao** (nhóm quán có tiềm năng phân tích phản hồi/cải thiện dịch vụ).
  - 📝 **Reviews (Số lượng đánh giá)**: **≥ 300 lượt đánh giá** (đảm bảo độ tin cậy và có nhiều dữ liệu review phong phú).
  - 🔁 **Khử trùng lặp**: Lọc trùng 100% dựa trên `google_maps_url` và tổ hợp `(Tên quán, Địa chỉ)`.

---

## 📂 2. Cấu Trúc Thư Mục

```text
1.Crawl_link/
├── README.md                   # Tài liệu mô tả chi tiết thư mục
├── fnb_scraper.py              # Script cào dữ liệu chính (Production Scraper)
├── pilot_test.py               # Script chạy thử nghiệm 5 truy vấn kiểm định logic
├── test_scraper.py             # Script kiểm tra feed, scroll & selector Google Maps
├── test_scraper2.py            # Script phân tích cấu trúc article, rating, reviews
├── article_sample.html         # File HTML mẫu của 1 article quán ăn (phục vụ debug)
├── test_page.html              # File HTML mẫu toàn trang kết quả tìm kiếm (phục vụ debug)
├── scraper_progress.json       # Checkpoint lưu các query đã hoàn thành & trạng thái cào
├── scraper_log.txt             # Nhật ký ghi log chi tiết của quá trình cào
├── fnb_hcm_hn_1500_leads.csv   # Dữ liệu 1.500 quán đã cào (Định dạng CSV UTF-8-SIG)
├── fnb_hcm_hn_1500_leads.xlsx  # Dữ liệu 1.500 quán đã cào (Định dạng Excel)
└── fnb_leads_backup.jsonl      # Bản sao lưu thời gian thực từng dòng dữ liệu (JSON Lines)
```

---

## 📑 3. Chi Tiết Các File

| Tên File | Loại | Mô Tả Chức Năng |
| :--- | :--- | :--- |
| **`fnb_scraper.py`** | Source Code | Tool cào chính dùng **Playwright** chạy Chromium headless. Tự động tìm kiếm theo Ma trận (Từ khóa × Quận/Huyện), cuộn trang tải kết quả, áp dụng bộ lọc, khử trùng, ghi file CSV/Excel an toàn và lưu checkpoint. |
| **`pilot_test.py`** | Script Test | Script chạy thử 5 truy vấn mẫu để kiểm tra tỷ lệ pass/filter dữ liệu, độ chính xác của regex bóc tách rating, review count và URL Google Maps. |
| **`test_scraper.py`** | Script Test | Script khảo sát ban đầu về cấu trúc DOM trang tìm kiếm Google Maps, cách bắt thẻ `[role="feed"]` và các thẻ `a[href*="/maps/place"]`. |
| **`test_scraper2.py`** | Script Test | Script khảo sát sâu cấu trúc của từng thẻ kết quả `[role="article"]`, bóc tách các trường qua thuộc tính `aria-label` và text nội dung. |
| **`article_sample.html`** | Dữ liệu mẫu | Đoạn mã HTML trích xuất từ 1 thẻ `article` để làm mẫu đối chiếu các selector CSS và biểu thức chính quy (Regex). |
| **`test_page.html`** | Dữ liệu mẫu | Toàn bộ mã nguồn HTML của một trang tìm kiếm kết quả Google Maps (khoảng 400KB) dùng để kiểm định lại khi Google Maps thay đổi layout. |
| **`fnb_hcm_hn_1500_leads.csv`** | Dataset | Bộ dữ liệu chính thức gồm **1.500 dòng** quán ăn F&B, mã hóa UTF-8 with BOM (tương thích hoàn hảo với Excel). |
| **`fnb_hcm_hn_1500_leads.xlsx`** | Dataset | Bộ dữ liệu chính thức định dạng Microsoft Excel `.xlsx`. |
| **`fnb_leads_backup.jsonl`** | Backup | File log dạng JSON Lines ghi tuần tự mỗi khi có 1 quán mới được cào. Đảm bảo dữ liệu không bị mất nếu có sự cố mất điện hay khóa file. |
| **`scraper_progress.json`** | State File | Lưu danh sách 124 truy vấn đã cào thành công để hỗ trợ chạy tiếp tục (Resume) mà không phải cào lại từ đầu. |
| **`scraper_log.txt`** | Log | Lưu toàn bộ lịch sử chạy theo từng bước, thông số số lượng cào được theo từng quận/thành phố và báo cáo thống kê cuối cùng. |

---

## 📊 4. Cấu Trúc Dữ Liệu Thu Thập (`fnb_hcm_hn_1500_leads.csv` / `.xlsx`)

Mỗi bản ghi đại diện cho một quán F&B bao gồm 10 trường thông tin:

| Cột | Kiểu Dữ Liệu | Ví Dụ | Ghi Chú |
| :--- | :--- | :--- | :--- |
| `stt` | Số nguyên | `1` | Số thứ tự tăng dần từ 1 đến 1500 |
| `ten_quan` | Chuỗi ký tự | `Quán Phá Lấu Bò Cô Thảo` | Tên chính thức của quán trên Google Maps |
| `thanh_pho` | Chuỗi ký tự | `TP.HCM` / `Hà Nội` | Thành phố trực thuộc |
| `quan_huyen` | Chuỗi ký tự | `Quận 4`, `Cầu Giấy` | Quận/Huyện bóc tách từ địa chỉ hoặc truy vấn |
| `phan_loai` | Chuỗi ký tự | `Quán ăn`, `Quán cafe`, `Nhà hàng` | Phân loại dựa trên keyword và tên quán |
| `diem_danh_gia` | Số thực (Float) | `4.2` | Điểm đánh giá (Đảm bảo $3.0 \le \text{rating} \le 4.4$) |
| `so_luong_danh_gia`| Số nguyên | `764` | Số lượt đánh giá (Đảm bảo $\ge 300$) |
| `dia_chi` | Chuỗi ký tự | `243/29G Tôn Đản, Phường 15` | Địa chỉ cụ thể hiển thị trên bài viết |
| `so_dien_thoai` | Chuỗi ký tự | `0901234567` | Số điện thoại liên hệ (nếu có) |
| `google_maps_url` | Chuỗi ký tự (URL) | `https://www.google.com/maps/place/...` | Link chuẩn hóa dẫn trực tiếp đến địa điểm |

---

## ⚙️ 5. Hướng Dẫn Cài Đặt & Chạy Lại (Re-run)

### Yêu Cầu Môi Trường
- Python **>= 3.10**
- Thư viện cần thiết:
  ```bash
  pip install playwright pandas openpyxl
  playwright install chromium
  ```

### Các Lệnh Thực Thi
1. **Kiểm tra DOM / Selector**:
   ```bash
   python test_scraper.py
   python test_scraper2.py
   ```
2. **Chạy thử nghiệm Pilot test**:
   ```bash
   python pilot_test.py
   ```
3. **Chạy Production Scraper**:
   ```bash
   python fnb_scraper.py
   ```
   *Lưu ý: Script hỗ trợ resume tự động thông qua file `scraper_progress.json` và cơ chế chống khóa file an toàn.*
