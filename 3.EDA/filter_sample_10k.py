#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter_sample_10k.py
--------------------
Đồ án môn học: Khai thác Dữ liệu Truyền thông Xã hội (IE403)
Nhiệm vụ:
  1. Đọc dữ liệu đánh giá F&B thô từ file cào Google Maps.
  2. Làm sạch dữ liệu (Data Cleaning):
     - Loại bỏ NaN ở `so_sao`, `noi_dung_review`.
     - Xóa các chuỗi dịch tự động của Google: (Dịch bởi Google), (Translated by Google), (Bản gốc), (Original).
     - Chuẩn hóa khoảng trắng.
     - Lọc bình luận quá ngắn (< 4 từ) hoặc không chứa ký tự tiếng Việt / Latin hợp lệ.
     - Khử trùng lặp nội dung review (drop_duplicates).
  3. Ẩn danh dữ liệu (Anonymization):
     - Xóa `ten_reviewer`, `google_maps_url`.
     - Mã hóa `stt_quan` thành `place_id` (P0001, P0002,...).
  4. Lấy mẫu phân tầng (Stratified Sampling) 10.000 dòng cân bằng 3 nhóm sao:
     - Tiêu cực (1.0 & 2.0 sao): 3.333 mẫu
     - Trung tính (3.0 sao): 3.334 mẫu (có cơ chế bù linh hoạt nếu thiếu)
     - Tích cực (4.0 & 5.0 sao): 3.333 mẫu
     - Trộn ngẫu nhiên (random_state=42) và gán `id` từ REV_00001 đến REV_10000.
  5. Xuất file:
     - `3.EDA/dataset_10000_unlabeled.csv` (10.000 dòng cho LLM labeling).
     - `3.EDA/gold_standard_200_template.csv` (200 mẫu ẩn số sao phục vụ gán nhãn thủ công 4 người).
"""

import os
import re
import sys
import pandas as pd
import numpy as np

# Cố định random seed để kết quả tái lập tuyệt đối
RANDOM_STATE = 42
TOTAL_SAMPLE_SIZE = 10000
GOLD_STANDARD_SIZE = 200

# Regex mẫu tiếng Việt và Latin hợp lệ
VIETNAMESE_LATIN_PATTERN = re.compile(
    r'[a-zA-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]'
)

# Regex các cụm từ dịch tự động của Google Maps
GOOGLE_TRANS_PATTERN = re.compile(
    r'\((?:Dịch bởi Google|Translated by Google|Bản gốc|Original)\)',
    re.IGNORECASE
)


def get_file_paths():
    """Xác định đường dẫn tương đối hoặc tuyệt đối linh hoạt."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))

    raw_input_path = os.path.join(project_root, "2.Crawl_data", "fnb_reviews_30_per_place.csv")
    out_10k_path = os.path.join(base_dir, "dataset_10000_unlabeled.csv")
    out_200_path = os.path.join(base_dir, "gold_standard_200_template.csv")

    return raw_input_path, out_10k_path, out_200_path


def clean_review_text(text: str) -> str:
    """Làm sạch văn bản review: xóa tag dịch Google và chuẩn hóa khoảng trắng."""
    if not isinstance(text, str):
        return ""
    text = GOOGLE_TRANS_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_valid_review(text: str, min_words: int = 4) -> bool:
    """Kiểm tra bình luận có hợp lệ: tối thiểu min_words từ và chứa ký tự chữ cái."""
    if not text:
        return False
    if not VIETNAMESE_LATIN_PATTERN.search(text):
        return False
    words = text.split()
    if len(words) < min_words:
        return False
    return True


def run_pipeline():
    print("=" * 70)
    print("🚀 BẮT ĐẦU QUY TRÌNH TIỀN XỬ LÝ & LẤY MẪU PHÂN TẦNG (10.000 MẪU)")
    print("=" * 70)

    raw_input_path, out_10k_path, out_200_path = get_file_paths()

    if not os.path.exists(raw_input_path):
        print(f"❌ LỖI: Không tìm thấy file dữ liệu đầu vào: {raw_input_path}")
        sys.exit(1)

    print(f"📂 Đang đọc dữ liệu từ: {raw_input_path} ...")
    df_raw = pd.read_csv(raw_input_path)
    n_raw = len(df_raw)
    print(f"   -> Tổng số dòng thô ban đầu: {n_raw:,} dòng.")

    # 1. Khử NaN
    print("\n[Bước 1] Khử dữ liệu khuyết thiếu (NaN)...")
    df_step1 = df_raw.dropna(subset=["so_sao", "noi_dung_review"]).copy()
    n_step1 = len(df_step1)
    print(f"   -> Số dòng sau khi loại NaN (so_sao, noi_dung_review): {n_step1:,} dòng (Đã loại {n_raw - n_step1:,} dòng).")

    # 2. Làm sạch text
    print("\n[Bước 2] Làm sạch văn bản và chuẩn hóa khoảng trắng...")
    df_step1["noi_dung_review"] = df_step1["noi_dung_review"].apply(clean_review_text)

    # 3. Lọc bỏ bình luận < 4 từ hoặc không có ký tự chữ cái hợp lệ
    print("\n[Bước 3] Lọc bỏ bình luận < 4 từ và không chứa ký tự chữ cái hợp lệ...")
    valid_mask = df_step1["noi_dung_review"].apply(lambda t: is_valid_review(t, min_words=4))
    df_step2 = df_step1[valid_mask].copy()
    n_step2 = len(df_step2)
    print(f"   -> Số dòng sau khi lọc từ ngắn & ký tự không hợp lệ: {n_step2:,} dòng (Đã loại {n_step1 - n_step2:,} dòng).")

    # 4. Khử trùng lặp nội dung review
    print("\n[Bước 4] Khử trùng lặp nội dung bình luận (drop_duplicates)...")
    df_step3 = df_step2.drop_duplicates(subset=["noi_dung_review"]).copy()
    n_step3 = len(df_step3)
    print(f"   -> Số dòng sau khi khử trùng lặp nội dung: {n_step3:,} dòng (Đã loại {n_step2 - n_step3:,} dòng trùng lặp).")

    # 5. Ẩn danh dữ liệu
    print("\n[Bước 5] Ẩn danh hóa dữ liệu (Anonymization)...")
    # Mã hóa stt_quan thành place_id (P0001, P0002,...)
    df_step3["place_id"] = df_step3["stt_quan"].apply(lambda x: f"P{int(x):04d}")
    print("   -> Đã mã hóa `stt_quan` sang `place_id` dạng P0001 - P1500.")
    print("   -> Đã loại bỏ các cột định danh nhạy cảm: `ten_reviewer`, `google_maps_url`.")

    # 6. Lấy mẫu phân tầng 10.000 dòng theo 3 nhóm sao
    print("\n[Bước 6] Phân nhóm và lấy mẫu phân tầng 10.000 mẫu cân bằng...")
    # Định nghĩa 3 nhóm sao
    df_neg = df_step3[df_step3["so_sao"].isin([1.0, 2.0])].copy()
    df_neu = df_step3[df_step3["so_sao"] == 3.0].copy()
    df_pos = df_step3[df_step3["so_sao"].isin([4.0, 5.0])].copy()

    n_neg_avail = len(df_neg)
    n_neu_avail = len(df_neu)
    n_pos_avail = len(df_pos)

    print(f"   * Số lượng khả dụng sau làm sạch:")
    print(f"     - Nhóm Tiêu cực (1.0 & 2.0 sao) : {n_neg_avail:,} mẫu")
    print(f"     - Nhóm Trung tính (3.0 sao)     : {n_neu_avail:,} mẫu")
    print(f"     - Nhóm Tích cực (4.0 & 5.0 sao) : {n_pos_avail:,} mẫu")

    # Mục tiêu ban đầu
    target_neg = 3333
    target_neu = 3334
    target_pos = 3333

    # Cơ chế bù linh hoạt nếu nhóm 3 sao thiếu
    if n_neu_avail < target_neu:
        actual_neu = n_neu_avail
        deficit = target_neu - actual_neu
        deficit_neg = deficit // 2
        deficit_pos = deficit - deficit_neg
        target_neg += deficit_neg
        target_pos += deficit_pos
        print(f"   ⚠️ Nhóm 3 sao chỉ có {actual_neu} < {target_neu}. Bù {deficit_neg} vào Tiêu cực và {deficit_pos} vào Tích cực.")
    else:
        actual_neu = target_neu

    print(f"   * Kế hoạch lấy mẫu thực tế:")
    print(f"     - Lấy từ Nhóm Tiêu cực : {target_neg:,} mẫu")
    print(f"     - Lấy từ Nhóm Trung tính: {actual_neu:,} mẫu")
    print(f"     - Lấy từ Nhóm Tích cực : {target_pos:,} mẫu")
    print(f"     -> Tổng cộng           : {target_neg + actual_neu + target_pos:,} mẫu")

    sample_neg = df_neg.sample(n=target_neg, random_state=RANDOM_STATE)
    sample_neu = df_neu.sample(n=actual_neu, random_state=RANDOM_STATE)
    sample_pos = df_pos.sample(n=target_pos, random_state=RANDOM_STATE)

    # Gộp 3 nhóm và shuffle toàn bộ
    df_10k = pd.concat([sample_neg, sample_neu, sample_pos], ignore_index=True)
    df_10k = df_10k.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)

    # Sinh cột id định danh: REV_00001 -> REV_10000
    df_10k["id"] = [f"REV_{i+1:05d}" for i in range(len(df_10k))]

    # Chuẩn bị cột cho dataset_10000_unlabeled.csv
    cols_10k = [
        "id", "place_id", "thanh_pho", "quan_huyen", "phan_loai",
        "so_sao", "thoi_gian", "so_luot_thich", "noi_dung_review"
    ]
    df_10k_out = df_10k[cols_10k].copy()

    # 7. Trích xuất phân tầng 200 mẫu cho Gold Standard (Ẩn số sao)
    print("\n[Bước 7] Trích xuất 200 mẫu phân tầng cho Gold Standard (ẩn số sao)...")
    # Phân tầng từ tập 10.000 mẫu: 66 Tiêu cực, 68 Trung tính, 66 Tích cực
    sub_neg = df_10k[df_10k["so_sao"].isin([1.0, 2.0])]
    sub_neu = df_10k[df_10k["so_sao"] == 3.0]
    sub_pos = df_10k[df_10k["so_sao"].isin([4.0, 5.0])]

    sample_200_neg = sub_neg.sample(n=66, random_state=RANDOM_STATE)
    sample_200_neu = sub_neu.sample(n=68, random_state=RANDOM_STATE)
    sample_200_pos = sub_pos.sample(n=66, random_state=RANDOM_STATE)

    df_200 = pd.concat([sample_200_neg, sample_200_neu, sample_200_pos], ignore_index=True)
    # Shuffle lại để các nhóm trộn lẫn ngẫu nhiên
    df_200 = df_200.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)

    # Tạo sẵn các cột trống cho 4 thành viên gán nhãn độc lập
    for i in range(1, 5):
        df_200[f"sentiment_{i}"] = ""
        df_200[f"is_mixed_{i}"] = ""

    # Các cột xuất ra tập 200 mẫu (ẨN CỘT `so_sao` HOÀN TOÀN)
    cols_200 = [
        "id", "place_id", "thanh_pho", "quan_huyen", "phan_loai",
        "thoi_gian", "so_luot_thich", "noi_dung_review",
        "sentiment_1", "is_mixed_1",
        "sentiment_2", "is_mixed_2",
        "sentiment_3", "is_mixed_3",
        "sentiment_4", "is_mixed_4"
    ]
    df_200_out = df_200[cols_200].copy()

    # 8. Xuất file kết quả
    print("\n[Bước 8] Lưu các tập dữ liệu ra file CSV (UTF-8 with BOM)...")
    df_10k_out.to_csv(out_10k_path, index=False, encoding="utf-8-sig")
    print(f"   ✅ Đã lưu tập 10.000 dòng tại: {out_10k_path}")

    df_200_out.to_csv(out_200_path, index=False, encoding="utf-8-sig")
    print(f"   ✅ Đã lưu tập đối chứng 200 mẫu tại: {out_200_path}")

    # In bảng tóm tắt
    print("\n" + "=" * 70)
    print("📊 TỔNG KẾT THỐNG KÊ QUÁ TRÌNH TIỀN XỬ LÝ & LẤY MẪU")
    print("=" * 70)
    print(f"• Tổng số dòng cào thô ban đầu           : {n_raw:,}")
    print(f"• Số dòng sau loại bỏ NaN                : {n_step1:,} (-{n_raw - n_step1:,})")
    print(f"• Số dòng sau lọc độ dài & ký tự Latin   : {n_step2:,} (-{n_step1 - n_step2:,})")
    print(f"• Số dòng sau khử trùng lặp nội dung     : {n_step3:,} (-{n_step2 - n_step3:,})")
    print(f"• Kích thước tập gán nhãn LLM            : {len(df_10k_out):,} dòng (100% cân bằng 3 cực)")
    print(f"• Phân bố số sao tập 10.000:")
    star_summary = df_10k_out["so_sao"].value_counts().sort_index()
    for star, count in star_summary.items():
        pct = count / len(df_10k_out) * 100
        print(f"   - {star:.1f} sao: {count:5,d} mẫu ({pct:5.2f}%)")
    print(f"• Kích thước tập đối chứng Gold Standard : {len(df_200_out):,} mẫu (Ẩn số sao)")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
