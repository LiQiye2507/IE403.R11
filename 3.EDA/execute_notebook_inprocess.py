#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
execute_notebook_inprocess.py
-----------------------------
Thực thi các cell code của notebook trong cùng một Python process,
bắt toàn bộ stdout và các đồ thị Matplotlib (lưu dưới dạng base64 png),
sau đó ghi đè outputs chuẩn chỉ vào `eda_raw_and_sampled.ipynb`.
"""

import os
import sys
import io
import base64
import contextlib
import nbformat as nbf
import matplotlib.pyplot as plt
from IPython.display import display

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK_PATH = os.path.join(BASE_DIR, "eda_raw_and_sampled.ipynb")


def execute_notebook():
    print(f"📖 Đang đọc notebook: {NOTEBOOK_PATH} ...")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = nbf.read(f, as_version=4)

    orig_cwd = os.getcwd()
    os.chdir(BASE_DIR)

    # Global scope dùng chung giữa các cell
    exec_globals = {
        '__name__': '__main__',
        '__file__': NOTEBOOK_PATH,
        'display': print  # In dataframe ra dạng text trong stdout
    }

    execution_count = 1

    try:
        for idx, cell in enumerate(nb.cells):
            if cell.cell_type != 'code':
                continue

            print(f"⚙️ Đang thực thi Cell [{execution_count}] (vị trí {idx + 1}/{len(nb.cells)})...")
            code_source = cell.source

            # Hook matplotlib figure capture
            plt.close('all')
            # Override plt.show để figure không bị đóng ngay
            original_show = plt.show
            plt.show = lambda *args, **kwargs: None

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stdout_capture):
                try:
                    exec(code_source, exec_globals)
                except Exception as e:
                    print(f"❌ LỖI KHI CHẠY CELL {idx + 1}: {e}", file=sys.stderr)
                    raise e
                finally:
                    plt.show = original_show

            stdout_text = stdout_capture.getvalue()
            cell.outputs = []
            cell.execution_count = execution_count

            # 1. Thêm stdout stream nếu có text
            if stdout_text.strip():
                cell.outputs.append(nbf.v4.new_output(
                    output_type='stream',
                    name='stdout',
                    text=stdout_text
                ))

            # 2. Bắt các matplotlib figure đang mở
            fig_nums = plt.get_fignums()
            for fig_num in fig_nums:
                fig = plt.figure(fig_num)
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
                img_buf.seek(0)
                img_b64 = base64.b64encode(img_buf.read()).decode('utf-8')
                plt.close(fig)

                # Gắn output dạng image/png
                cell.outputs.append(nbf.v4.new_output(
                    output_type='display_data',
                    data={
                        'image/png': img_b64,
                        'text/plain': '<Figure size ...>'
                    },
                    metadata={}
                ))

            execution_count += 1

    finally:
        os.chdir(orig_cwd)

    # Ghi lại notebook đã có outputs
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        nbf.write(nb, f)

    print(f"🎉 Đã thực thi thành công {execution_count - 1} code cells và lưu outputs vào: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    execute_notebook()
