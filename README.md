# Dự Án Thu Thập & Xử Lý Dữ Liệu F&B (IE403)

Dự án thu thập, tiền xử lý, gán nhãn và phân tích cảm xúc đa khía cạnh (Aspect-Based Sentiment Analysis - ABSA) đối với ngành hàng F&B (Food & Beverage) tại hai trung tâm kinh tế lớn: **TP. Hồ Chí Minh** và **Hà Nội**.

---

## 📁 Cấu Trúc Dự Án

```text
IE403.R11/
│
├── 1.Crawl_link/                   # Giai đoạn 1: Thu thập liên kết và thông tin sơ bộ các quán F&B
│   ├── README.md                   # Tài liệu chi tiết hướng dẫn & mô tả dữ liệu Giai đoạn 1
│   ├── fnb_scraper.py              # Crawler Playwright tự động cào 1.500 quán từ Google Maps
│   ├── pilot_test.py               # Script kiểm thử pilot 5 truy vấn
│   ├── test_scraper.py             # Script test selector DOM Google Maps
│   ├── test_scraper2.py            # Script test trích xuất chi tiết thẻ article
│   ├── fnb_hcm_hn_1500_leads.csv   # Dữ liệu chính thức (1.500 dòng CSV UTF-8)
│   ├── fnb_hcm_hn_1500_leads.xlsx  # Dữ liệu chính thức định dạng Excel
│   ├── fnb_leads_backup.jsonl      # File backup realtime JSON Lines
│   ├── scraper_progress.json       # Checkpoint tiến trình cào
│   └── scraper_log.txt             # Lịch sử ghi log quá trình cào
│
├── 2.Crawl_data/                   # Giai đoạn 2: Thu thập dữ liệu đánh giá chi tiết
│   ├── crawl_data.py               # Crawler thu thập 30 đánh giá chi tiết cho mỗi quán
│   ├── fnb_reviews_30_per_place.csv# Tập dữ liệu 42.273 đánh giá thô trên Google Maps
│   └── review_checkpoint.json      # Checkpoint lưu tiến trình thu thập đánh giá
│
├── 3.EDA/                          # Giai đoạn 3: Khám phá dữ liệu, làm sạch & lấy mẫu phân tầng
│   ├── README.md                   # Báo cáo phân tích EDA chuyên sâu & thống kê số liệu thực tế
│   ├── filter_sample_10k.py        # Script lọc sạch, khử trùng lặp, ẩn danh và lấy mẫu phân tầng 10k
│   ├── generate_figures.py         # Script vẽ & xuất 4 biểu đồ EDA độ nét cao (DPI=300)
│   ├── execute_notebook_inprocess.py # Script thực thi tự động toàn bộ cells của Notebook
│   ├── eda_raw_and_sampled.ipynb   # Jupyter Notebook hoàn chỉnh có sẵn outputs và lý giải học thuật
│   ├── dataset_10000_unlabeled.csv # Tập 10.000 đánh giá cân bằng 3 cực sẵn sàng cho LLM Labeling
│   ├── gold_standard_200_template.csv # Template 200 mẫu ẩn số sao phục vụ gán nhãn 4 người độc lập
│   └── figures/                    # Thư mục lưu trữ biểu đồ trực quan hóa (DPI=300)
│       ├── star_distribution_comparison.png # So sánh phân bố số sao trước vs sau lấy mẫu
│       ├── word_count_analysis.png          # Độ dài từ, kiểm chứng max_length=128 cho PhoBERT & Boxplot
│       ├── teencode_and_emoji_stats.png     # Tỷ lệ sử dụng Emoji & Top 10 Teencode tiếng Việt
│       └── location_and_category_dist.png   # Phân bố địa lý (Hà Nội vs TP.HCM) và loại hình ẩm thực
│
└── README.md                       # Tài liệu tổng quan dự án (file này)
```

---

## 🚀 Các Giai Đoạn Dự Án

1. **[1.Crawl_link](file:///c:/Users/ZiLing05/Desktop/IE403.R11/1.Crawl_link/README.md)**: 
   - Thu thập thành công **1.500 quán F&B** (752 tại TP.HCM, 748 tại Hà Nội).
   - Bộ lọc chất lượng: Đánh giá từ **3.0 - 4.4 sao**, số lượt reviews **≥ 300**.
   - Cung cấp file CSV, Excel và JSONL backup.

2. **2.Crawl_data**:
   - Thu thập chi tiết **42.273 đánh giá** từ Google Maps tương ứng với danh sách 1.500 quán.
   - Trích xuất 12 trường thông tin: Tên quán, số sao, nội dung review, lượt thích, thời gian, phân loại, quận huyện, thành phố...

3. **[3.EDA](file:///c:/Users/ZiLing05/Desktop/IE403.R11/3.EDA/README.md)**:
   - **Làm sạch & Ẩn danh**: Khử khuyết thiếu NaN (loại 265 dòng), xóa nhãn dịch tự động Google, lọc bỏ bình luận rác/ngắn < 4 từ (loại 78 dòng), khử trùng lặp hoàn toàn nội dung (loại 278 dòng). Ẩn danh hóa người dùng và mã hóa quán thành `place_id` (P0001 -> P1500).
   - **Lấy mẫu phân tầng 10.000 mẫu**: Tái cân bằng hoàn hảo 3 nhóm cảm xúc (*Tiêu cực: 3.333 mẫu, Trung tính: 3.334 mẫu, Tích cực: 3.333 mẫu*), xóa bỏ hoàn toàn hiện tượng lệch về 5 sao của tập thô.
   - **Xây dựng Gold Standard 200 mẫu**: Ẩn số sao, cung cấp cấu trúc cột cho 4 thành viên gán nhãn độc lập để đo lường độ đồng thuận Fleiss' Kappa và đối chứng với LLM.
   - **Khám phá đặc trưng NLP**:
     - Độ dài bình luận: Trung bình 61.23 từ; chứng minh ngưỡng **`max_length = 128`** cho PhoBERT bao phủ tới **90.51%** dữ liệu.
     - Tâm lý người dùng: Đánh giá tiêu cực dài hơn rõ rệt (mean 71.59 từ) so với đánh giá tích cực (mean 49.30 từ).
     - Ngôn ngữ mạng: Thống kê tỷ lệ Emoji (8.89% tổng thể, nhóm tích cực đạt 9.99%) và danh mục Top 10 Teencode (`ko`, `k`, `ok`, `đc`, `nv`, `vs`, `dc`...).
