"""
BƯỚC 6: XỬ LÝ TEENCODE VÀ SLANG 
- KHÔNG xử lý biến thể kéo dài (ví dụ "kkkk" -> "không") — đã xử lý ở bước 4
"""

import re
import yaml
from typing import Tuple, List, Dict


def load_teencode_map(path: str = "data/dictionaries/teencode_map.yaml") -> Dict[str, str]:
    """Load teencode map từ YAML, trả về dict rỗng nếu lỗi."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            # keys/values đảm bảo là str và lower-key để so khớp không phân biệt hoa thường
            return {str(k).lower(): str(v) for k, v in data.items()}
    except Exception:
        return {}


def _should_replace_short_token(token: str, prev_tok: str, next_tok: str) -> bool:
    """
    Quy tắc đơn giản với token ngắn (ví dụ 'm', 't'):
    - Nếu trước hoặc sau là số thì KHÔNG thay (ví dụ '100 m' không nên thành '100 mày')
    - Nếu không có số kề bên thì thay
    """
    if prev_tok and prev_tok.isdigit():
        return False
    if next_tok and next_tok.isdigit():
        return False
    return True


def replace_teencode(text: str, teencode_map: Dict[str, str]) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Thay các token theo teencode_map.
    - Tokenize đơn giản: giữ các dấu câu (regex: \w+ | [^\w\s])
    - Khi token có trong map (so sánh lowercase) và thỏa ngữ cảnh → thay
    """
    if not teencode_map:
        return text, []

    # tách token giữ dấu câu
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    out_tokens = []
    replacements = []

    for i, tok in enumerate(tokens):
        prev_tok = tokens[i - 1] if i > 0 else None
        next_tok = tokens[i + 1] if i < len(tokens) - 1 else None

        tok_lower = tok.lower()
        if tok_lower in teencode_map:
            # một số token rất ngắn cần kiểm tra ngữ cảnh
            if len(tok) <= 2:
                if _should_replace_short_token(tok, prev_tok, next_tok):
                    new = teencode_map[tok_lower]
                    replacements.append((tok, new))
                    out_tokens.append(new)
                else:
                    out_tokens.append(tok)
            else:
                new = teencode_map[tok_lower]
                replacements.append((tok, new))
                out_tokens.append(new)
        else:
            out_tokens.append(tok)

    # nối lại câu: thêm space trước token nếu token hiện tại và token trước không phải dấu câu
    result = ""
    for i, tok in enumerate(out_tokens):
        if i > 0 and not re.match(r"[^\w\s]", tok):
            result += " "
        result += tok

    return result.strip(), replacements


def get_unknown_words(text: str, teencode_map: Dict[str, str]) -> List[str]:
    """
    Tìm các từ OOV (không nằm trong teencode_map và không phải số, token ngắn).
    Trả về danh sách unique (lowercase).
    """
    tokens = re.findall(r"\w+", text.lower(), re.UNICODE)
    common_words = {
        # danh sách rất ngắn các từ phổ biến để bỏ qua 
        "tôi", "mình", "bạn", "anh", "chị", "em", "họ", "tao", "mày",
        "là", "có", "và", "với", "trong", "cho", "này", "đó", "gì", "sao",
        "không", "rất", "quá", "lắm", "cái", "có", "đi", "đến", "về",
    }
    unknown = set()
    for tok in tokens:
        if tok.isdigit():
            continue
        if tok in common_words:
            continue
        if tok in teencode_map:
            continue
        if len(tok) < 2:
            continue
        unknown.add(tok)
    return sorted(list(unknown))


def process(text: str, teencode_path: str = "data/dictionaries/teencode_map.yaml") -> Tuple[str, Dict]:
    """
    Hàm chính:
      - load teencode map từ file (nếu có)
      - replace_teencode trên text
      - get_unknown_words để log/update từ điển
    Trả về (clean_text, metadata)
    metadata: { "replacements": [(orig,new),...], "replacement_count": n, "unknown_words": [...] }
    """
    teencode_map = load_teencode_map(teencode_path)
    cleaned, replacements = replace_teencode(text, teencode_map)
    unknowns = get_unknown_words(cleaned, teencode_map)
    metadata = {
        "replacements": replacements,
        "replacement_count": len(replacements),
        "unknown_words": unknowns
    }
    return cleaned, metadata


# ----- Test nhanh: danh sách câu (chỉ in kết quả) -----
if __name__ == "__main__":
    tests = [
        "m nói j vậy",
        "k bt sao nữa",
        "100 m chạy",
        "t thích m",
        "wtf mày toxic quá",
        "oke bt thôi",
        "vcl thằng noob",
        "mày k biết à?",
        "k 100 m",
    ]
    print("TEST BƯỚC 6: TEENCODE (danh sách câu, đơn giản)")

    for s in tests:
        out, meta = process(s, teencode_path="data/dictionaries/teencode_map.yaml")
        print(f"\nInput : {repr(s)}")
        print(f"Output: {repr(out)}")
        # print(f"Meta: replacements={meta['replacements']}, unknowns={meta['unknown_words']}")s