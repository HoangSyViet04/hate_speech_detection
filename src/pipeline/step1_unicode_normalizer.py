"""
Bộ chuẩn hóa Unicode  
Các bước giữ lại:
 1) Chuẩn hoá dạng Unicode (NFKC -> NFC)
 2) Xóa ký tự vô hình / điều hướng (zero-width, BOM, directional marks, soft hyphen ...)
 3) Thay các ký tự "giả mạo" thường gặp (Cyrillic/Greek/full-width) về ký tự Latin tương ứng
 4) Gộp mọi khoảng trắng (tab/newline/multi-space) thành 1 dấu cách và trim đầu/cuối
"""

import re
import unicodedata
from typing import Iterable

# Danh sách ký tự vô hình cần xóa (những ký tự này thường phá tokenization)
INVISIBLES = [
    "\u200B",  # zero-width space (khoảng trắng không hiển thị)
    "\u200C",  # zero-width non-joiner (ngăn chữ dính)
    "\u200D",  # zero-width joiner (ép dính)
    "\u2060",  # word joiner
    "\uFEFF",  # BOM (byte order mark)
    "\u00AD",  # soft hyphen (gạch nối mềm, thường không hiển thị)
    "\u200E", "\u200F",  # left-to-right / right-to-left marks (điều hướng hiển thị)
    # Các isolate và directional formatting có thể xuất hiện khi copy/paste
    "\u2066", "\u2067", "\u2068", "\u2069",
    "\u202A", "\u202B", "\u202C", "\u202D", "\u202E",
]
# Bảng ký tự "giả mạo" thường gặp và ký tự Latin tương ứng
CONFUSABLES = {
    # Cyrillic nhìn giống Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X",
    # Một vài ký tự Greek hay nhầm
    "α": "a", "ο": "o", "ν": "v",
    # Full-width (ký tự rộng kiểu Nhật/Unicode) -> ASCII thường
    "ａ":"a","ｂ":"b","ｃ":"c","ｄ":"d","ｅ":"e","ｆ":"f","ｇ":"g",
    "ｈ":"h","ｉ":"i","ｊ":"j","ｋ":"k","ｌ":"l","ｍ":"m","ｎ":"n",
    "ｏ":"o","ｐ":"p","ｑ":"q","ｒ":"r","ｓ":"s","ｔ":"t","ｕ":"u",
    "ｖ":"v","ｗ":"w","ｘ":"x","ｙ":"y","ｚ":"z",
    "０":"0","１":"1","２":"2","３":"3","４":"4",
    "５":"5","６":"6","７":"7","８":"8","９":"9",
}

# Tạo bảng dịch 1 lần: invisibles -> None (xóa), confusables -> ký tự thay thế
_TRANSLATE = {ord(ch): None for ch in INVISIBLES}
_TRANSLATE.update({ord(k): v for k, v in CONFUSABLES.items()})

_WS_RE = re.compile(r"\s+")


def process(text: str) -> str:
    """
    Chuẩn hoá chuỗi đầu vào, trả về chuỗi đã xử lý.

    Quy trình:
     - Nếu input không phải str, chuyển sang str.
     - Unicode NFKC -> NFC để gộp các dạng tương đương.
     - Xóa ký tự vô hình và map confusables bằng translate (1 lần duy nhất).
     - Gộp mọi whitespace (space/tab/newline) thành 1 space và trim hai đầu.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1) Chuẩn hoá dạng unicode
    text = unicodedata.normalize("NFKC", text)
    text = unicodedata.normalize("NFC", text)

    # 2) Xóa invisibles và map confusables trong một lần duyệt
    text = text.translate(_TRANSLATE)

    # 3) Gộp whitespace thành 1 space và trim hai đầu
    text = _WS_RE.sub(" ", text).strip()

    return text


def process(texts: Iterable[str]):
    """
    Trả về generator các chuỗi đã chuẩn hoá (tiện để dùng trong pipeline).
    """
    for t in texts:
        yield process(t)


if __name__ == "__main__":
    # Ví dụ nhỏ để kiểm tra nhanh
    samples = [
        "g\u200Bi\u200Bế\u200Bt",         # zero-width chèn giữa chữ
        "cоn chо",                       # chữ 'о' Cyrillic để obfuscate
        "ｈｅｌｌｏ   \n world",           # full-width + nhiều whitespace/newline
        "Đầy   \t    khoảng  \n  trắng"  # khoảng trắng hỗn hợp
    ]

    print("Ví dụ chuẩn hoá:")
    for s in samples:
        print("IN :", repr(s))
        print("OUT:", repr(process(s)))
        print("---")
