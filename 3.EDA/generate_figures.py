#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_figures.py
-------------------
Script vẽ 4 biểu đồ trực quan hóa dữ liệu EDA cho đồ án IE403:
  1. star_distribution_comparison.png : So sánh phân bố số sao (Raw vs Sampled 10k).
  2. word_count_analysis.png          : Phân tích độ dài câu, kiểm chứng ngưỡng 128 từ cho PhoBERT & Boxplot 3 nhóm sao.
  3. teencode_and_emoji_stats.png     : Tỷ lệ sử dụng Emoji và Top 10 từ lóng / Teencode phổ biến.
  4. location_and_category_dist.png   : Phân bố theo thành phố, quận huyện và loại hình kinh doanh F&B.
Lưu toàn bộ hình ảnh độ phân giải cao 300 DPI vào thư mục `3.EDA/figures/`.
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Thiết lập font hiển thị tiếng Việt chuẩn trên Windows
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Calibri', 'Tahoma', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.autolayout'] = True
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
FIG_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

RAW_PATH = os.path.join(PROJECT_ROOT, "2.Crawl_data", "fnb_reviews_30_per_place.csv")
SAMPLED_PATH = os.path.join(BASE_DIR, "dataset_10000_unlabeled.csv")


def load_data():
    print("⏳ Đang tải dữ liệu thô và tập 10k...")
    df_raw = pd.read_csv(RAW_PATH)
    df_10k = pd.read_csv(SAMPLED_PATH)
    return df_raw, df_10k


def plot_figure_1_star_distribution(df_raw, df_10k):
    """Biểu đồ 1: So sánh phân bố số sao trước và sau khi lấy mẫu phân tầng."""
    print("📊 Đang vẽ Biểu đồ 1: star_distribution_comparison.png ...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

    # 1. Phân bố thô (lọc bỏ NaN số sao)
    raw_stars = df_raw['so_sao'].dropna().value_counts().sort_index()
    total_raw = len(df_raw['so_sao'].dropna())
    raw_pct = (raw_stars / total_raw) * 100

    # Bảng màu đại diện: 1-2 sao đỏ/cam, 3 sao vàng, 4-5 sao xanh lá
    palette = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']

    bars1 = axes[0].bar(
        [f"{int(s)} sao" for s in raw_stars.index],
        raw_stars.values,
        color=palette,
        edgecolor='#333333',
        linewidth=1.2,
        alpha=0.88
    )
    axes[0].set_title(
        f"A. Phan Bo So Sao Truoc Lay Mau\n(Tap Tho: N = {total_raw:,} danh gia)",
        fontsize=13, fontweight='bold', pad=12
    )
    axes[0].set_title(
        f"A. Phân Bố Số Sao Trước Lấy Mẫu\n(Tập Thô: N = {total_raw:,} đánh giá)",
        fontsize=13, fontweight='bold', pad=12
    )
    axes[0].set_xlabel("Đánh giá số sao (Rating)", fontsize=11, fontweight='bold')
    axes[0].set_ylabel("Số lượng đánh giá (Tần suất)", fontsize=11, fontweight='bold')
    axes[0].grid(axis='y', linestyle='--', alpha=0.5)

    # Thêm nhãn số lượng và % trên đầu cột
    for bar, count, pct in zip(bars1, raw_stars.values, raw_pct.values):
        height = bar.get_height()
        axes[0].text(
            bar.get_x() + bar.get_width() / 2.,
            height + max(raw_stars.values) * 0.015,
            f"{count:,}\n({pct:.1f}%)",
            ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#2c3e50'
        )
    axes[0].set_ylim(0, max(raw_stars.values) * 1.15)

    # Ghi chú hiện tượng mất cân bằng
    axes[0].text(
        0.05, 0.88,
        "[Canh bao] Lech manh ve 5 sao (51.9%)\nTong 4-5 sao chiem toi 73.3%",
        transform=axes[0].transAxes, fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffeaa7", edgecolor="#fdcb6e", alpha=0.9)
    )

    # 2. Phân bố tập 10.000 mẫu phân tầng
    s_stars = df_10k['so_sao'].value_counts().sort_index()
    total_10k = len(df_10k)
    s_pct = (s_stars / total_10k) * 100

    bars2 = axes[1].bar(
        [f"{int(s)} sao" for s in s_stars.index],
        s_stars.values,
        color=palette,
        edgecolor='#333333',
        linewidth=1.2,
        alpha=0.88
    )
    axes[1].set_title(
        f"B. Phân Bố Số Sao Sau Khi Lấy Mẫu Phân Tầng\n(Tập Chuẩn: N = {total_10k:,} đánh giá)",
        fontsize=13, fontweight='bold', pad=12
    )
    axes[1].set_xlabel("Đánh giá số sao (Rating)", fontsize=11, fontweight='bold')
    axes[1].set_ylabel("Số lượng đánh giá (Tần suất)", fontsize=11, fontweight='bold')
    axes[1].grid(axis='y', linestyle='--', alpha=0.5)

    for bar, count, pct in zip(bars2, s_stars.values, s_pct.values):
        height = bar.get_height()
        axes[1].text(
            bar.get_x() + bar.get_width() / 2.,
            height + max(s_stars.values) * 0.015,
            f"{count:,}\n({pct:.1f}%)",
            ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#2c3e50'
        )
    axes[1].set_ylim(0, max(s_stars.values) * 1.15)

    # Ghi chú phân tầng 3 nhóm cảm xúc cân bằng
    axes[1].text(
        0.05, 0.85,
        "[Toi uu] Can bang hoan hao 3 nhom cam xuc:\n"
        "- Tieu cuc (1-2 sao): 3.333 mau (33.33%)\n"
        "- Trung tinh (3 sao): 3.334 mau (33.34%)\n"
        "- Tich cuc (4-5 sao): 3.333 mau (33.33%)",
        transform=axes[1].transAxes, fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#dff9fb", edgecolor="#55efc4", alpha=0.95)
    )

    out_file = os.path.join(FIG_DIR, "star_distribution_comparison.png")
    fig.tight_layout()
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"   -> Đã lưu: {out_file}")


def plot_figure_2_word_count(df_10k):
    """Biểu đồ 2: Phân tích độ dài câu, kiểm chứng max_length=128 cho PhoBERT & Boxplot 3 nhóm sao."""
    print("📊 Đang vẽ Biểu đồ 2: word_count_analysis.png ...")
    df = df_10k.copy()
    df['word_count'] = df['noi_dung_review'].apply(lambda x: len(str(x).split()))

    # Tính tỷ lệ <= 128 từ
    pct_128 = (df['word_count'] <= 128).mean() * 100
    mean_wc = df['word_count'].mean()
    median_wc = df['word_count'].median()
    p95_wc = np.percentile(df['word_count'], 95)

    # Phân nhóm cảm xúc
    def get_group(star):
        if star in [1.0, 2.0]:
            return "Tiêu cực (1-2 sao)"
        elif star == 3.0:
            return "Trung tính (3 sao)"
        else:
            return "Tích cực (4-5 sao)"

    df['group'] = df['so_sao'].apply(get_group)
    group_order = ["Tiêu cực (1-2 sao)", "Trung tính (3 sao)", "Tích cực (4-5 sao)"]
    group_colors = ['#e74c3c', '#f39c12', '#2ecc71']

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # 1. Histogram & KDE (cắt giới hạn 0 - 250 để hiển thị rõ vùng tập trung)
    wc_filtered = df['word_count'][df['word_count'] <= 250]
    sns.histplot(
        wc_filtered,
        bins=50,
        kde=True,
        ax=axes[0],
        color='#3498db',
        edgecolor='#2980b9',
        alpha=0.6,
        line_kws={'linewidth': 2}
    )

    # Đường vạch đỏ tại ngưỡng 128 từ
    axes[0].axvline(
        128,
        color='#c0392b',
        linestyle='--',
        linewidth=2.2,
        label=f'Ngưỡng PhoBERT max_length = 128 ({pct_128:.1f}% bao phủ)'
    )
    axes[0].axvline(
        median_wc,
        color='#27ae60',
        linestyle=':',
        linewidth=2,
        label=f'Trung vị (Median) = {median_wc:.0f} từ'
    )
    axes[0].axvline(
        mean_wc,
        color='#8e44ad',
        linestyle='-.',
        linewidth=2,
        label=f'Trung bình (Mean) = {mean_wc:.1f} từ'
    )

    axes[0].set_title(
        "A. Phân Bố Độ Dài Bình Luận (Word Count)\n& Kiểm Chứng Ngưỡng Tokenization PhoBERT",
        fontsize=12.5, fontweight='bold', pad=12
    )
    axes[0].set_xlabel("Số lượng từ (Word count)", fontsize=11, fontweight='bold')
    axes[0].set_ylabel("Số lượng bình luận", fontsize=11, fontweight='bold')
    axes[0].set_xlim(0, 250)
    axes[0].legend(loc='upper right', fontsize=9.5, frameon=True)
    axes[0].grid(True, linestyle='--', alpha=0.5)

    # Hộp chú thích luận cứ chọn max_length=128
    axes[0].text(
        0.48, 0.40,
        f"[Thuc nghiem PhoBERT]\n"
        f"- {pct_128:.2f}% binh luan <= 128 tu\n"
        f"- Phan vi 95%: {p95_wc:.0f} tu\n"
        f"- Chon max_length=128 giup toi uu\n"
        f"  chi phi tinh toan & giu tron\n"
        f"  ngu canh quan trong nhat.",
        transform=axes[0].transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ecf0f1", edgecolor="#bdc3c7", alpha=0.95)
    )

    # 2. Boxplot theo 3 nhóm sao
    sns.boxplot(
        x='group',
        y='word_count',
        hue='group',
        legend=False,
        data=df,
        order=group_order,
        palette=group_colors,
        ax=axes[1],
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": 7},
        fliersize=3,
        linewidth=1.3
    )

    axes[1].set_title(
        "B. So Sánh Độ Dài Bình Luận Theo 3 Nhóm Cảm Xúc\n(Hình thoi trắng biểu thị giá trị Trung Bình - Mean)",
        fontsize=12.5, fontweight='bold', pad=12
    )
    axes[1].set_xlabel("Nhóm cảm xúc (Rating Group)", fontsize=11, fontweight='bold')
    axes[1].set_ylabel("Số lượng từ (Word count)", fontsize=11, fontweight='bold')
    axes[1].set_ylim(0, 220)
    axes[1].grid(axis='y', linestyle='--', alpha=0.5)

    # Thống kê chi tiết trên từng nhóm
    grp_stats = df.groupby('group')['word_count'].agg(['mean', 'median']).loc[group_order]
    for idx, (grp, row) in enumerate(grp_stats.iterrows()):
        axes[1].text(
            idx, row['mean'] + 6,
            f"Mean: {row['mean']:.1f}\nMed: {row['median']:.0f}",
            ha='center', va='bottom', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=group_colors[idx], alpha=0.85)
        )

    out_file = os.path.join(FIG_DIR, "word_count_analysis.png")
    fig.tight_layout()
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"   -> Đã lưu: {out_file}")


def plot_figure_3_teencode_and_emoji(df_10k):
    """Biểu đồ 3: Tỷ lệ sử dụng Emoji theo nhóm sao và Top 10 từ lóng / Teencode."""
    print("📊 Đang vẽ Biểu đồ 3: teencode_and_emoji_stats.png ...")
    df = df_10k.copy()

    # 1. Thống kê Emoji
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf]')
    df['has_emoji'] = df['noi_dung_review'].apply(lambda x: bool(emoji_pattern.search(str(x))))

    def get_group(star):
        if star in [1.0, 2.0]:
            return "Tiêu cực\n(1-2 sao)"
        elif star == 3.0:
            return "Trung tính\n(3 sao)"
        else:
            return "Tích cực\n(4-5 sao)"

    df['group'] = df['so_sao'].apply(get_group)
    group_order = ["Tiêu cực\n(1-2 sao)", "Trung tính\n(3 sao)", "Tích cực\n(4-5 sao)"]
    emoji_rates = (df.groupby('group')['has_emoji'].mean() * 100).loc[group_order]

    # 2. Thống kê Teencode Top 10
    teencode_dict = {
        'ko (không)': r'\bko\b',
        'k (không)': r'\bk\b',
        'ok (ổn / đồng ý)': r'\bok\b',
        'đc (được)': r'\bđc\b',
        'nv (nhân viên)': r'\bnv\b',
        'kh (không / khách)': r'\bkh\b',
        'vs (với)': r'\bvs\b',
        'dc (được)': r'\bdc\b',
        'mn (mọi người)': r'\bmn\b',
        'oke (ok / được)': r'\boke\b'
    }

    tc_counts = []
    for label, pat in teencode_dict.items():
        regex = re.compile(pat, re.IGNORECASE)
        occ = df['noi_dung_review'].apply(lambda t: len(regex.findall(str(t)))).sum()
        tc_counts.append({'label': label, 'count': occ})

    df_tc = pd.DataFrame(tc_counts).sort_values(by='count', ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # A. Tỷ lệ % Emoji
    colors_emoji = ['#e74c3c', '#f39c12', '#2ecc71']
    bars_emoji = axes[0].bar(
        emoji_rates.index,
        emoji_rates.values,
        color=colors_emoji,
        edgecolor='#333333',
        linewidth=1.2,
        alpha=0.88,
        width=0.55
    )
    axes[0].set_title(
        "A. Tỷ Lệ Bình Luận Chứa Emoji Theo Cảm Xúc\n(Nghiên cứu hành vi biểu cảm của người dùng)",
        fontsize=12.5, fontweight='bold', pad=12
    )
    axes[0].set_xlabel("Nhóm cảm xúc", fontsize=11, fontweight='bold')
    axes[0].set_ylabel("Tỷ lệ phần trăm (%)", fontsize=11, fontweight='bold')
    axes[0].set_ylim(0, max(emoji_rates.values) * 1.3)
    axes[0].grid(axis='y', linestyle='--', alpha=0.5)

    for bar, val in zip(bars_emoji, emoji_rates.values):
        height = bar.get_height()
        axes[0].text(
            bar.get_x() + bar.get_width() / 2.,
            height + 0.3,
            f"{val:.2f}%",
            ha='center', va='bottom', fontsize=11, fontweight='bold', color='#2c3e50'
        )

    axes[0].text(
        0.05, 0.82,
        "[Nhan xet behavior]:\n"
        "- Nhom Tich cuc dung emoji nhieu nhat (10.0%),\n"
        "  chu yeu bieu dat hai long, yeu thich.\n"
        "- Nhom Tieu cuc (8.2%) dung icon buc xuc.\n"
        "- Can quy tac chuan hoa teencode/emoji o buoc tien xu ly.",
        transform=axes[0].transAxes, fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff9e6", edgecolor="#ffeaa7", alpha=0.95)
    )

    # B. Cột ngang Top 10 Teencode
    bars_tc = axes[1].barh(
        df_tc['label'],
        df_tc['count'],
        color='#9b59b6',
        edgecolor='#2c3e50',
        linewidth=1.1,
        alpha=0.85,
        height=0.65
    )
    axes[1].set_title(
        "B. Top 10 Từ Lóng / Teencode Phổ Biến Nhất\n(Thống kê tổng số lần xuất hiện trong 10.000 đánh giá)",
        fontsize=12.5, fontweight='bold', pad=12
    )
    axes[1].set_xlabel("Số lần xuất hiện (Tần suất)", fontsize=11, fontweight='bold')
    axes[1].set_ylabel("Từ lóng / Teencode", fontsize=11, fontweight='bold')
    axes[1].grid(axis='x', linestyle='--', alpha=0.5)
    axes[1].set_xlim(0, max(df_tc['count']) * 1.18)

    for bar in bars_tc:
        width = bar.get_width()
        axes[1].text(
            width + max(df_tc['count']) * 0.02,
            bar.get_y() + bar.get_height() / 2.,
            f"{int(width):,} lần",
            ha='left', va='center', fontsize=9.5, fontweight='bold', color='#34495e'
        )

    out_file = os.path.join(FIG_DIR, "teencode_and_emoji_stats.png")
    fig.tight_layout()
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"   -> Đã lưu: {out_file}")


def plot_figure_4_location_and_category(df_10k):
    """Biểu đồ 4: Phân bố theo thành phố, top quận huyện và loại hình ẩm thực."""
    print("📊 Đang vẽ Biểu đồ 4: location_and_category_dist.png ...")
    df = df_10k.copy()

    fig = plt.figure(figsize=(16, 7))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1.25, 1.45])

    ax_city = fig.add_subplot(gs[0])
    ax_dist = fig.add_subplot(gs[1])
    ax_cat = fig.add_subplot(gs[2])

    # 1. Phân bố theo thành phố (Donut Chart)
    city_counts = df['thanh_pho'].value_counts()
    city_colors = ['#3498db', '#e67e22']
    wedges, texts, autotexts = ax_city.pie(
        city_counts.values,
        labels=city_counts.index,
        autopct='%1.1f%%',
        startangle=140,
        colors=city_colors,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
        textprops=dict(fontsize=11, fontweight='bold')
    )
    for at in autotexts:
        at.set_color('white')
        at.set_fontsize(11)
        at.set_weight('bold')
    ax_city.set_title(
        f"A. Phân Bố Theo Thành Phố\n(Hà Nội vs TP.HCM)",
        fontsize=12, fontweight='bold', pad=12
    )

    # 2. Top 10 Quận/Huyện
    top_dist = df['quan_huyen'].value_counts().head(10).sort_values(ascending=True)
    bars_dist = ax_dist.barh(
        top_dist.index,
        top_dist.values,
        color='#1abc9c',
        edgecolor='#16a085',
        linewidth=1,
        alpha=0.88,
        height=0.65
    )
    ax_dist.set_title(
        "B. Top 10 Quận / Huyện Đóng Góp\nNhiều Đánh Giá Nhất",
        fontsize=12, fontweight='bold', pad=12
    )
    ax_dist.set_xlabel("Số lượng đánh giá", fontsize=10.5, fontweight='bold')
    ax_dist.grid(axis='x', linestyle='--', alpha=0.5)
    ax_dist.set_xlim(0, max(top_dist.values) * 1.18)

    for bar in bars_dist:
        width = bar.get_width()
        ax_dist.text(
            width + max(top_dist.values) * 0.02,
            bar.get_y() + bar.get_height() / 2.,
            f"{int(width):,}",
            ha='left', va='center', fontsize=9, fontweight='bold', color='#2c3e50'
        )

    # 3. Phân loại loại hình ẩm thực
    top_cat = df['phan_loai'].value_counts().head(10).sort_values(ascending=True)
    bars_cat = ax_cat.barh(
        top_cat.index,
        top_cat.values,
        color='#e74c3c',
        edgecolor='#c0392b',
        linewidth=1,
        alpha=0.85,
        height=0.65
    )
    ax_cat.set_title(
        "C. Top Loại Hình Ẩm Thực (F&B)\nPhổ Biến Trong Tập Dữ Liệu",
        fontsize=12, fontweight='bold', pad=12
    )
    ax_cat.set_xlabel("Số lượng đánh giá", fontsize=10.5, fontweight='bold')
    ax_cat.grid(axis='x', linestyle='--', alpha=0.5)
    ax_cat.set_xlim(0, max(top_cat.values) * 1.18)

    for bar in bars_cat:
        width = bar.get_width()
        pct = (width / len(df)) * 100
        ax_cat.text(
            width + max(top_cat.values) * 0.02,
            bar.get_y() + bar.get_height() / 2.,
            f"{int(width):,} ({pct:.1f}%)",
            ha='left', va='center', fontsize=9, fontweight='bold', color='#2c3e50'
        )

    out_file = os.path.join(FIG_DIR, "location_and_category_dist.png")
    fig.tight_layout()
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"   -> Đã lưu: {out_file}")


def main():
    print("=" * 70)
    print("🎨 TIẾN TRÌNH XUẤT 4 BIỂU ĐỒ EDA ĐỘ PHÂN GIẢI CAO (DPI=300)")
    print("=" * 70)
    df_raw, df_10k = load_data()
    plot_figure_1_star_distribution(df_raw, df_10k)
    plot_figure_2_word_count(df_10k)
    plot_figure_3_teencode_and_emoji(df_10k)
    plot_figure_4_location_and_category(df_10k)
    print("=" * 70)
    print("✅ HOÀN TẤT VẼ VÀ XUẤT TẤT CẢ BIỂU ĐỒ VÀO 3.EDA/figures/!")
    print("=" * 70)


if __name__ == "__main__":
    main()
