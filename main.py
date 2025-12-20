"""
Tiền xử lý 2 file cố định: data/raw/train.csv và data/raw/test.csv
- Chạy qua master_pipeline (đã tích hợp đủ các step)
- Ghi ra 2 file cùng tên (train.csv, test.csv) vào thư mục data/processed

Cách chạy (từ thư mục gốc dự án):
    python src/pipeline/preprocess_train_test.py

Yêu cầu:
- Các file tồn tại:
    data/raw/train.csv
    data/raw/test.csv
  Trong mỗi file phải có cột 'text' (và thường có 'label')
- Có thư mục từ điển:
    data/dictionaries/ (emoticon_map.yaml, teencode_map.yaml, ...)
"""

import os
import sys
import pandas as pd
from typing import List

# Thử import master_pipeline theo kiểu package; nếu chạy trực tiếp từ root, dùng fallback
try:
    from src.pipeline.master_pipeline import default_config, init_pipeline_handlers, process_text
except Exception:
    try:
        from pipeline.master_pipeline import default_config, init_pipeline_handlers, process_text  
    except Exception as e:
        print(" Không import được master_pipeline")
        raise e

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
DICT_DIR = "data/dictionaries"

TRAIN_IN = os.path.join(RAW_DIR, "train.csv")
TEST_IN = os.path.join(RAW_DIR, "test.csv")

TRAIN_OUT = os.path.join(PROCESSED_DIR, "train.csv")
TEST_OUT = os.path.join(PROCESSED_DIR, "test.csv")

VALID_IN = r"D:\Learn\ky1_nam4\Hoc_sau\hate_speech_detection\data\raw\valid.csv"
VALID_OUT = os.path.join(PROCESSED_DIR, "valid.csv")

LOWERCASE_OUTPUT = True      # Ép chữ thường sau pipeline

def _process_file(in_path: str, out_path: str,
                  cfg: dict, handlers: dict) -> None:
    """
    - Đọc CSV (yêu cầu có cột 'text')
    - Chạy master_pipeline cho từng dòng
    - Ghi CSV mới vào out_path, giữ nguyên cột 'label' nếu có
    """
    if not os.path.exists(in_path):
        print(f" Không tìm thấy file: {in_path}")
        return

    df = pd.read_csv(in_path)
    if "free_text" not in df.columns:
        raise ValueError(f"{in_path} cần có cột 'free_text'.")

    total = len(df)
    print(f"→ Đang xử lý: {in_path} (tổng {total} dòng) ...")

    cleaned_list: List[str] = []
    for i, raw in enumerate(df["free_text"].astype(str).tolist(), start=1):
        res = process_text(raw, handlers, cfg)
        cleaned_list.append(res["cleaned"])
        if i % 1000 == 0 or i == total:
            print(f"  ... {i}/{total}")

    out_df = df.copy()
    out_df["free_text"] = cleaned_list

    # Sắp xếp cột: 'free_text' trước, giữ 'label_id' nếu có
    cols = ["free_text"] + (["label_id"] if "label_id" in out_df.columns else [])
    out_df = out_df[cols]

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    out_df.to_csv(out_path, index=False, encoding="utf-8")
    print(f" Đã lưu: {out_path}\n")


if __name__ == "__main__":
    # Khởi tạo cấu hình và handlers 1 lần dùng cho cả 2 file
    cfg = default_config(dict_dir=DICT_DIR)
    cfg["lowercase"] = LOWERCASE_OUTPUT
    handlers = init_pipeline_handlers(cfg)

    _process_file(TRAIN_IN, TRAIN_OUT, cfg, handlers)
    _process_file(TEST_IN, TEST_OUT, cfg, handlers)
    _process_file(VALID_IN, VALID_OUT, cfg, handlers)

    print(" --> Hoàn tất tiền xử lý train.csv, test.csv và valid.csv.")