#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_excel_annotation.py
--------------------------
Xuất file `3.EDA/gold_standard_200_template.csv` thành:
  1. `3.EDA/gold_standard_200_template.xlsx` (File Excel mẫu chuẩn)
  2. 3 bản sao độc lập cho 3 thành viên gán nhãn trong `3.EDA/annotation_3_members/`:
     - `annotator_1.xlsx`
     - `annotator_2.xlsx`
     - `annotator_3.xlsx`

Tính năng nổi bật trong file Excel:
  - Sheet 1 (`Huong_Dan_Gan_Nhan`): Hướng dẫn chi tiết quy tắc gán nhãn 5 khía cạnh ABSA
    (FOOD, SERVICE, PRICE, AMBIENCE, GENERAL) × 4 trạng thái (POSITIVE, NEGATIVE, NEUTRAL, NONE)
    kèm bảng giải thích trường hợp biên và 5 ví dụ thực tế.
  - Sheet 2 (`Gan_Nhan_200_Mau`):
    + Điền sẵn mặc định `NONE` cho 5 cột khía cạnh để người gán chỉ cần đổi các khía cạnh có xuất hiện
      (tiết kiệm ~70% thao tác click chuột).
    + Tích hợp Dropdown List (Data Validation) chống gõ sai chính tả.
    + Tích hợp Conditional Formatting tự động đổi màu ô theo nhãn:
      * POSITIVE -> Xanh lá
      * NEGATIVE -> Đỏ hồng
      * NEUTRAL  -> Vàng cam
      * NONE     -> Xám nhạt
    + Cố định dòng tiêu đề (Freeze Panes) và tự động xuống dòng (Wrap Text) cột bình luận.
"""

import os
import shutil
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "gold_standard_200_template.csv")
MASTER_XLSX_PATH = os.path.join(BASE_DIR, "gold_standard_200_template.xlsx")
ANNOTATOR_DIR = os.path.join(BASE_DIR, "annotation_3_members")


def style_range(ws, cell_range, font=None, fill=None, alignment=None, border=None):
    for row in ws[cell_range]:
        for cell in row:
            if font:
                cell.font = font
            if fill:
                cell.fill = fill
            if alignment:
                cell.alignment = alignment
            if border:
                cell.border = border


def build_guideline_sheet(ws):
    ws.title = "Huong_Dan_Gan_Nhan"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    title_font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    title_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    sec_font = Font(name="Segoe UI", size=12, bold=True, color="1F4E78")
    sec_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    th_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    th_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")

    body_font = Font(name="Segoe UI", size=10, bold=False, color="000000")
    bold_font = Font(name="Segoe UI", size=10, bold=True, color="000000")

    thin_side = Side(border_style="thin", color="BFBFBF")
    border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    wrap_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Banner tiêu đề
    ws.merge_cells("A1:E1")
    ws["A1"] = "HƯỚNG DẪN GÁN NHÃN ĐA KHÍA CẠNH (ABSA) - ĐÁNH GIÁ F&B GOOGLE MAPS (IE403)"
    ws["A1"].font = title_font
    ws["A1"].fill = title_fill
    ws["A1"].alignment = wrap_center
    ws.row_dimensions[1].height = 36

    # Mục 1: Quy trình nhanh
    ws.merge_cells("A3:E3")
    ws["A3"] = "1. QUY TẮC THAO TÁC NHANH DÀNH CHO 3 NGƯỜI GÁN NHÃN (ANNOTATORS)"
    ws["A3"].font = sec_font
    ws["A3"].fill = sec_fill
    ws["A3"].alignment = wrap_left
    ws.row_dimensions[3].height = 26

    rules = [
        "• Chuyển sang tab 'Gan_Nhan_200_Mau' ở phía dưới để bắt đầu làm việc.",
        "• Mặc định cả 5 cột khía cạnh (FOOD, SERVICE, PRICE, AMBIENCE, GENERAL) đã được điền sẵn là 'NONE' (Không đề cập).",
        "• Khi đọc bình luận ở cột H (noi_dung_review), khía cạnh nào CÓ ĐƯỢC NHẮC TỚI thì bấm mũi tên chọn: POSITIVE (Khen), NEGATIVE (Chê), hoặc NEUTRAL (Trung tính). Khía cạnh không nhắc tới thì giữ nguyên là NONE.",
        "• Làm việc hoàn toàn ĐỘC LẬP trên file cá nhân của mình (annotator_1 / annotator_2 / annotator_3) để tính hệ số đồng thuận chuẩn Cohen's Kappa: κ = (κ12 + κ23 + κ13) / 3 và Fleiss' Kappa."
    ]
    for idx, r_text in enumerate(rules, start=4):
        ws.merge_cells(f"A{idx}:E{idx}")
        ws[f"A{idx}"] = r_text
        ws[f"A{idx}"].font = body_font
        ws[f"A{idx}"].alignment = wrap_left
        ws.row_dimensions[idx].height = 22

    # Mục 2: Bảng định nghĩa 5 khía cạnh
    ws.merge_cells("A9:E9")
    ws["A9"] = "2. BẢNG ĐỊNH NGHĨA CHI TIẾT 5 KHÍA CẠNH (ASPECTS)"
    ws["A9"].font = sec_font
    ws["A9"].fill = sec_fill
    ws["A9"].alignment = wrap_left
    ws.row_dimensions[9].height = 26

    headers_aspect = ["Mã cột", "Tên khía cạnh", "Phạm vi bao hàm trong bình luận", "Từ khóa / Dấu hiệu nhận biết", "Lưu ý xử lý trường hợp biên (Edge Cases)"]
    for col_idx, h in enumerate(headers_aspect, start=1):
        cell = ws.cell(row=10, column=col_idx, value=h)
        cell.font = th_font
        cell.fill = th_fill
        cell.alignment = wrap_center
        cell.border = border_all
    ws.row_dimensions[10].height = 26

    aspects_data = [
        (
            "FOOD",
            "Đồ ăn & Đồ uống",
            "Hương vị (ngon/dở/vừa miệng), độ tươi sống, cách chế biến, khẩu phần (đầy đặn/ít), thực đơn (đa dạng/nghèo nàn), cách bày trí món ăn.",
            "ngon, đậm đà, nhạt, mặn, nguội, tươi, ít thịt, trà thơm, nước dùng, bánh mềm...",
            "Nếu khen/chê 'đồ ăn sạch sẽ' hoặc 'có dị vật (tóc/ruồi) trong bát phở' -> Gán cả FOOD = NEGATIVE và AMBIENCE = NEGATIVE."
        ),
        (
            "SERVICE",
            "Dịch vụ & Nhân viên",
            "Thái độ nhân viên (nv), chủ quán, bảo vệ giữ xe; tốc độ phục vụ/lên món (nhanh/lâu); quy trình order, tính tiền, giao hàng.",
            "nhân viên (nv), chủ quán, bảo vệ, nhiệt tình, thân thiện, thái độ lồi lõm, chờ lâu, quên món...",
            "Khen/chê chú bảo vệ dắt xe nhiệt tình hoặc thái độ kém -> Tính vào SERVICE (không tính vào GENERAL)."
        ),
        (
            "PRICE",
            "Giá cả",
            "Mức giá cụ thể (VD: 50k/tô), đánh giá đắt/rẻ/hợp lý so với chất lượng hoặc mặt bằng chung, thu thêm phụ phí, khuyến mãi.",
            "giá, đắt, mắc, rẻ, bình dân, hợp túi tiền, hạt dẻ, chặt chém, 35k, 100 cành, phí gửi xe...",
            "Nếu chỉ nêu giá tiền khách quan ('Phở bò 45k/tô') mà không khen rẻ hay chê đắt -> Gán PRICE = NEUTRAL."
        ),
        (
            "AMBIENCE",
            "Không gian & Vệ sinh",
            "Không gian quán (rộng/chật, thoáng/bí, mát/nóng, yên tĩnh/ồn ào), trang trí (decor/view), bàn ghế, nhà vệ sinh, VỆ SINH AN TOÀN THỰC PHẨM.",
            "không gian, view đẹp, thoáng, chật, nóng, điều hòa, ồn, sạch sẽ, dơ, bẩn, mùi hôi, ruồi muỗi...",
            "Bao gồm toàn bộ yếu tố vật lý tại quán và vấn đề vệ sinh bàn ghế, bát đũa, môi trường xung quanh."
        ),
        (
            "GENERAL",
            "Đánh giá chung & Vị trí",
            "Nhận xét tổng thể về quán mà không chỉ rõ khía cạnh cụ thể, cảm xúc chung, ý định quay lại/giới thiệu bạn bè, vị trí địa lý/chỗ đậu xe.",
            "quán ruột, tuyệt vời, thất vọng toàn tập, sẽ quay lại, không bao giờ quay lại, dễ tìm, trong hẻm, chỗ để xe...",
            "Nếu câu đã khen cụ thể ('Phở ngon') VÀ chốt thêm câu tổng kết ('Rất đáng ghé lại') -> Gán FOOD = POSITIVE và GENERAL = POSITIVE."
        ),
    ]

    for r_offset, row_vals in enumerate(aspects_data, start=11):
        ws.row_dimensions[r_offset].height = 46
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=r_offset, column=c_idx, value=val)
            c.font = bold_font if c_idx in (1, 2) else body_font
            c.alignment = wrap_center if c_idx == 1 else wrap_left
            c.border = border_all

    # Mục 3: Bảng định nghĩa 4 giá trị nhãn
    ws.merge_cells("A17:E17")
    ws["A17"] = "3. BỘ 4 GIÁ TRỊ NHÃN CẢM XÚC CHO TỪNG KHÍA CẠNH"
    ws["A17"].font = sec_font
    ws["A17"].fill = sec_fill
    ws["A17"].alignment = wrap_left
    ws.row_dimensions[17].height = 26

    headers_label = ["Giá trị chọn", "Ý nghĩa cảm xúc", "Quy tắc áp dụng chi tiết", "Ví dụ minh họa ngắn", "Màu hiển thị tự động"]
    for col_idx, h in enumerate(headers_label, start=1):
        cell = ws.cell(row=18, column=col_idx, value=h)
        cell.font = th_font
        cell.fill = th_fill
        cell.alignment = wrap_center
        cell.border = border_all
    ws.row_dimensions[18].height = 25

    labels_data = [
        ("POSITIVE", "Tích cực (Khen)", "Thể hiện sự hài lòng, khen ngợi, đánh giá tốt hoặc khuyến khích về khía cạnh đó.", "'Đồ ăn cực kỳ cuốn', 'Nhân viên lễ phép', 'Giá siêu hời'", "Xanh lá (Green)"),
        ("NEGATIVE", "Tiêu cực (Chê)", "Thể hiện sự phàn nàn, chê bai, bức xúc, thất vọng (hoặc khen nhẹ nhưng chê nặng).", "'Nước lèo nguội ngắt', 'Đợi 40 phút chưa có đồ', 'Quán nóng như lò bát quái'", "Đỏ hồng (Red)"),
        ("NEUTRAL", "Trung tính", "Có nhắc tới khía cạnh nhưng: (1) Chỉ nêu thông tin khách quan, hoặc (2) Đánh giá ở mức 'tạm ổn / bình thường / 50-50'.", "'Tô đặc biệt giá 65k', 'Đồ ăn ở mức bình thường, không quá đặc sắc'", "Vàng cam (Yellow)"),
        ("NONE", "Không đề cập", "Bình luận hoàn toàn không có thông tin hay ám chỉ gì về khía cạnh này.", "(Giữ nguyên giá trị mặc định NONE)", "Xám nhạt (Gray)"),
    ]

    label_fills = [
        PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
        PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"),
    ]

    for idx, (row_vals, l_fill) in enumerate(zip(labels_data, label_fills), start=19):
        ws.row_dimensions[idx].height = 30
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=idx, column=c_idx, value=val)
            c.font = bold_font if c_idx in (1, 5) else body_font
            c.alignment = wrap_center if c_idx in (1, 5) else wrap_left
            c.border = border_all
            if c_idx in (1, 5):
                c.fill = l_fill

    # Mục 4: Ví dụ thực tế
    ws.merge_cells("A24:E24")
    ws["A24"] = "4. VÍ DỤ MẪU THỰC TẾ (CÁCH GÁN NHÃN CHUẨN)"
    ws["A24"].font = sec_font
    ws["A24"].fill = sec_fill
    ws["A24"].alignment = wrap_left
    ws.row_dimensions[24].height = 26

    ex_headers = ["Câu bình luận mẫu (noi_dung_review)", "FOOD", "SERVICE", "PRICE", "AMBIENCE / GENERAL & Giải thích"]
    for col_idx, h in enumerate(ex_headers, start=1):
        cell = ws.cell(row=25, column=col_idx, value=h)
        cell.font = th_font
        cell.fill = th_fill
        cell.alignment = wrap_center
        cell.border = border_all
    ws.row_dimensions[25].height = 25

    examples = [
        (
            "Phở bò nước dùng ngọt thanh rất ngon, giá 50k một bát nhưng nhân viên mặt nặng mày nhẹ, gọi thêm quẩy mãi không mang ra.",
            "POSITIVE", "NEGATIVE", "NEUTRAL",
            "AMBIENCE = NONE, GENERAL = NONE (Khen phở ngon -> FOOD=POSITIVE; nêu giá 50k khách quan -> PRICE=NEUTRAL; chê nhân viên -> SERVICE=NEGATIVE)."
        ),
        (
            "Quán decor kiểu cổ điển rất ấm cúng, nhạc nhẹ nhàng. Đồ uống thì bình thường, giá hơi chát so với sinh viên.",
            "NEUTRAL", "NONE", "NEGATIVE",
            "AMBIENCE = POSITIVE, GENERAL = NONE (Khen không gian -> AMBIENCE=POSITIVE; đồ uống bình thường -> FOOD=NEUTRAL; giá đắt -> PRICE=NEGATIVE)."
        ),
        (
            "Quán ruột của gia đình mình suốt 5 năm nay, lần nào ghé cũng cực kỳ ưng ý, sẽ ủng hộ dài dài!",
            "NONE", "NONE", "NONE",
            "AMBIENCE = NONE, GENERAL = POSITIVE (Khen tổng thể quán và khẳng định quay lại mà không nêu cụ thể món ăn hay nhân viên -> GENERAL=POSITIVE)."
        ),
        (
            "Bàn ghế dính đầy dầu mỡ chưa lau, dưới sàn toàn giấy ăn. Đồ nướng thì tẩm ướp mặn chát, tệ thật sự.",
            "NEGATIVE", "NONE", "NONE",
            "AMBIENCE = NEGATIVE, GENERAL = NEGATIVE (Chê vệ sinh bẩn -> AMBIENCE=NEGATIVE; đồ nướng mặn -> FOOD=NEGATIVE; chốt 'tệ thật sự' -> GENERAL=NEGATIVE)."
        ),
    ]

    for idx, row_vals in enumerate(examples, start=26):
        ws.row_dimensions[idx].height = 42
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=idx, column=c_idx, value=val)
            c.font = bold_font if c_idx in (2, 3, 4) else body_font
            c.alignment = wrap_center if c_idx in (2, 3, 4) else wrap_left
            c.border = border_all

    # Căn chỉnh độ rộng cột Sheet 1
    col_widths_s1 = [18, 22, 42, 36, 46]
    for i, w in enumerate(col_widths_s1, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_annotation_sheet(ws, df: pd.DataFrame):
    ws.title = "Gan_Nhan_200_Mau"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "id", "place_id", "thanh_pho", "quan_huyen", "phan_loai",
        "thoi_gian", "so_luot_thich", "noi_dung_review",
        "FOOD", "SERVICE", "PRICE", "AMBIENCE", "GENERAL"
    ]

    # Styles
    meta_th_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    aspect_th_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    th_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    meta_font = Font(name="Segoe UI", size=9.5, color="333333")
    review_font = Font(name="Segoe UI", size=10.5, bold=False, color="000000")
    aspect_font = Font(name="Segoe UI", size=10, bold=True, color="595959")

    zebra_fill = PatternFill(start_color="F9FBFD", end_color="F9FBFD", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_side = Side(border_style="thin", color="D9D9D9")
    med_side = Side(border_style="medium", color="1F4E78")
    border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Ghi dòng Header
    ws.row_dimensions[1].height = 30
    for c_idx, col_name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c_idx, value=col_name)
        cell.font = th_font
        cell.fill = aspect_th_fill if c_idx >= 9 else meta_th_fill
        cell.alignment = align_center
        cell.border = Border(left=thin_side, right=thin_side, top=med_side, bottom=med_side)

    # Ghi 200 dòng dữ liệu (điền mặc định NONE cho 5 cột khía cạnh)
    for r_idx, row in df.iterrows():
        excel_row = r_idx + 2
        text_len = len(str(row["noi_dung_review"]))
        # Tự động ước lượng chiều cao dòng theo độ dài câu bình luận
        est_lines = max(2, (text_len // 65) + 1)
        ws.row_dimensions[excel_row].height = min(140, max(28, est_lines * 16))

        row_fill = zebra_fill if r_idx % 2 == 1 else white_fill

        for c_idx, col_name in enumerate(headers, start=1):
            if c_idx >= 9:
                val = "NONE"
            else:
                val = row[col_name]

            cell = ws.cell(row=excel_row, column=c_idx, value=val)
            cell.border = border_cell

            if c_idx == 8:  # noi_dung_review
                cell.font = review_font
                cell.alignment = align_left
                cell.fill = row_fill
            elif c_idx >= 9:  # 5 cột khía cạnh ABSA
                cell.font = aspect_font
                cell.alignment = align_center
            else:
                cell.font = meta_font
                cell.alignment = align_center
                cell.fill = row_fill

    # Thiết lập Data Validation (Dropdown) cho I2:M201
    dv = DataValidation(
        type="list",
        formula1='"POSITIVE,NEGATIVE,NEUTRAL,NONE"',
        allow_blank=False,
        showDropDown=False
    )
    dv.errorTitle = "Giá trị nhãn không hợp lệ"
    dv.error = "Vui lòng chỉ chọn 1 trong 4 nhãn từ danh sách: POSITIVE, NEGATIVE, NEUTRAL, NONE."
    dv.promptTitle = "Chọn nhãn ABSA"
    dv.prompt = "Chọn POSITIVE (Khen), NEGATIVE (Chê), NEUTRAL (Trung tính), hoặc NONE (Không đề cập)"
    ws.add_data_validation(dv)
    dv.add("I2:M201")

    # Thiết lập Conditional Formatting đổi màu tự động cho I2:M201
    pos_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    pos_font = Font(name="Segoe UI", size=10, bold=True, color="006100")

    neg_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    neg_font = Font(name="Segoe UI", size=10, bold=True, color="9C0006")

    neu_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    neu_font = Font(name="Segoe UI", size=10, bold=True, color="9C6500")

    none_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    none_font = Font(name="Segoe UI", size=9.5, bold=False, color="808080")

    ws.conditional_formatting.add("I2:M201", CellIsRule(operator="equal", formula=['"POSITIVE"'], stopIfTrue=True, fill=pos_fill, font=pos_font))
    ws.conditional_formatting.add("I2:M201", CellIsRule(operator="equal", formula=['"NEGATIVE"'], stopIfTrue=True, fill=neg_fill, font=neg_font))
    ws.conditional_formatting.add("I2:M201", CellIsRule(operator="equal", formula=['"NEUTRAL"'], stopIfTrue=True, fill=neu_fill, font=neu_font))
    ws.conditional_formatting.add("I2:M201", CellIsRule(operator="equal", formula=['"NONE"'], stopIfTrue=True, fill=none_fill, font=none_font))

    # Cố định dòng tiêu đề trên cùng
    ws.freeze_panes = "A2"

    # Căn chỉnh độ rộng các cột
    col_widths = {
        "A": 12,  # id
        "B": 10,  # place_id
        "C": 14,  # thanh_pho
        "D": 15,  # quan_huyen
        "E": 18,  # phan_loai
        "F": 14,  # thoi_gian
        "G": 12,  # so_luot_thich
        "H": 68,  # noi_dung_review
        "I": 14,  # FOOD
        "J": 14,  # SERVICE
        "K": 14,  # PRICE
        "L": 14,  # AMBIENCE
        "M": 14,  # GENERAL
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width


def export_excel_files():
    df = pd.read_csv(CSV_PATH)

    wb = Workbook()
    ws_guide = wb.active
    build_guideline_sheet(ws_guide)

    ws_annot = wb.create_sheet(title="Gan_Nhan_200_Mau")
    build_annotation_sheet(ws_annot, df)

    # Đặt sheet Gan_Nhan_200_Mau hoặc Huong_Dan_Gan_Nhan hiển thị thuận tiện
    wb.save(MASTER_XLSX_PATH)
    print(f"✅ Đã xuất file Excel mẫu chuẩn tại: {MASTER_XLSX_PATH}")

    os.makedirs(ANNOTATOR_DIR, exist_ok=True)
    for i in range(1, 4):
        member_path = os.path.join(ANNOTATOR_DIR, f"annotator_{i}.xlsx")
        shutil.copyfile(MASTER_XLSX_PATH, member_path)
        print(f"   -> Đã tạo bản sao độc lập cho Thành viên {i}: {member_path}")


if __name__ == "__main__":
    export_excel_files()

