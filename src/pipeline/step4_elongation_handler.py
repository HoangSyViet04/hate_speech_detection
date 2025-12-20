# -*- coding: utf-8 -*-
"""
BƯỚC 4: XỬ LÝ KÉO DÀI KÝ TỰ (ELONGATION) — PHONG CÁCH THỦ TỤC 
================================================================================
Mục tiêu:
- Co cụm ký tự lặp nhưng giữ lại tín hiệu cường độ cơ bản.
Xử lý:
1) collapse_repeated_chars(text, max_repeat): co cụm chữ lặp (ví dụ "nguuuuuuuuuuuuu" -> "nguu" nếu max_repeat=2)
2) collapse_punctuation(text): co cụm "!!!" -> "!!", "???" -> "??" và trả thông tin số cụm
3) extract_intensity_features(text): trích các feature cơ bản (max_char_repeat, caps_ratio, exclaim_count, question_count, text_length)
4) process(text, max_repeat=2, extract_features=True): chạy đầy đủ bước, trả về (cleaned_text, metadata)
"""


import re
from typing import Tuple, Dict

# Regex cho chữ cái lặp (bao gồm tiếng Việt có dấu)
LETTER_REPEAT_RE = re.compile(r"([A-Za-zÀ-ỹđĐ])\1{2,}", re.UNICODE)

# Regex cho dấu câu lặp
EXCLAMATION_REPEAT_RE = re.compile(r"!{2,}")
QUESTION_REPEAT_RE = re.compile(r"\?{2,}")


def collapse_repeated_chars(text: str, max_repeat: int = 2) -> Tuple[str, int]:
    """
    Co cụm các ký tự lặp liên tiếp.
    - Ví dụ: "nguuuuuu" với max_repeat=2 -> "nguu"
    """
    if max_repeat < 1:
        raise ValueError("max_repeat phải >= 1")

    collapse_count = 0

    def _repl(m):
        nonlocal collapse_count
        collapse_count += 1
        ch = m.group(1)
        # Trả về ch lặp max_repeat lần (giữ 1 chút cường độ nếu max_repeat>1)
        return ch * max_repeat

    new_text = LETTER_REPEAT_RE.sub(_repl, text)
    return new_text, collapse_count


def collapse_punctuation(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Co cụm các dấu chấm than/dấu hỏi lặp:
    - "!!!!" -> "!!"
    - "???"  -> "??"
    Trả về (text_sau, {"exclaim_sequences": n, "question_sequences": m})
    """
    # Thay và đếm số cụm
    ex_count = len(EXCLAMATION_REPEAT_RE.findall(text))
    text = EXCLAMATION_REPEAT_RE.sub("!!", text)

    q_count = len(QUESTION_REPEAT_RE.findall(text))
    text = QUESTION_REPEAT_RE.sub("??", text)

    stats = {
        "exclaim_sequences": ex_count,
        "question_sequences": q_count,
    }
    return text, stats


def extract_intensity_features(text: str) -> Dict[str, float]:
    """
    Trích xuất đặc trưng cường độ.
    Trả về dict gồm:
      - max_char_repeat: chuỗi lặp dài nhất (số ký tự trong chuỗi lặp gốc)
      - caps_ratio: tỉ lệ chữ IN HOA trên tổng chữ
      - exclaim_count: số ký tự "!"
      - question_count: số ký tự "?"
      - text_length: độ dài text
    """
    features = {}

    # max_char_repeat: tìm tất cả các match của LETTER_REPEAT_RE, lấy độ dài lớn nhất của nhóm match
    matches = list(LETTER_REPEAT_RE.finditer(text))
    if matches:
        max_len = max(len(m.group(0)) for m in matches)
        features["max_char_repeat"] = max_len
    else:
        features["max_char_repeat"] = 0

    # caps_ratio: tỉ lệ chữ hoa trên tổng chữ (nếu không có chữ thì 0)
    letters = [c for c in text if c.isalpha()]
    if letters:
        upper_count = sum(1 for c in letters if c.isupper())
        features["caps_ratio"] = round(upper_count / len(letters), 3)
    else:
        features["caps_ratio"] = 0.0

    # Đếm dấu chấm than và dấu hỏi
    features["exclaim_count"] = text.count("!")
    features["question_count"] = text.count("?")

    # Độ dài text
    features["text_length"] = len(text)

    return features


def process(text: str, max_repeat: int = 2, extract_features: bool = True) -> Tuple[str, Dict]:
    """
    Chạy toàn bộ bước xử lý elongation:
      1) trích features gốc sau khi co 
      2) collapse_repeated_chars
      3) collapse_punctuation

    """
    metadata = {
        "chars_collapsed": 0,
        "punct_stats": {},
        "intensity_features": {},
    }

    # (1) Co cụm ký tự lặp
    text_after_chars, chars_collapsed = collapse_repeated_chars(text, max_repeat=max_repeat)
    metadata["chars_collapsed"] = chars_collapsed

    # (2) Co cụm dấu câu
    text_after_punct, punct_stats = collapse_punctuation(text_after_chars)
    metadata["punct_stats"] = punct_stats

    # (3) Trích features (từ text sau xử lý punctuation)
    if extract_features:
        metadata["intensity_features"] = extract_intensity_features(text_after_punct)

    # Trả kết quả
    cleaned = text_after_punct
    return cleaned, metadata


# ---------- Quick tests / CLI ----------
if __name__ == "__main__":
    tests = [
        ("hayyyyyyy quáááááá", "Kéo dài chữ"),
        ("THẰNG NGU!!!!!", "IN HOA + nhiều dấu !"),
        ("yeuuuuu quáaaaaaaaa???? ", "Lặp + dấu ?"),
        ("bình thường", "Không có gì đặc biệt"),

    ]

    print("TEST BƯỚC 4: ELONGATION ")
    for text, desc in tests:
        cleaned, meta = process(text, max_repeat=2, extract_features=True)
        print(f"\n trường hợp: {desc}")
        print(" Input: ", repr(text))
        print(" Output:", repr(cleaned))
        # print(" Meta:  ", meta)