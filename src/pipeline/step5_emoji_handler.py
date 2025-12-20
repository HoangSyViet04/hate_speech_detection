"""
BƯỚC 5: XỬ LÝ EMOJI VÀ EMOTICON ASCII
============================================================
Mục tiêu:
- Chuyển emoticon ASCII (ví dụ :)) , =)) , :v ) thành token 
- Chuyển emoji thành chữ (demojize) 
- Trả về text đã chuẩn hoá và metadata cơ bản (số emoji, danh sách emoticon tìm thấy)
"""

import re
import yaml
from typing import Tuple, Dict, List

try:
    import emoji
    EMOJI_AVAILABLE = True
except Exception:
    EMOJI_AVAILABLE = False

# Biểu thức chính quy dự phòng để phát hiện emoticon ASCII nếu không có bản đồ
FALLBACK_EMOTICON_RE = re.compile(r"[:=;][\)\(DpPoOvV]+|<3|:\'[\(c]|:v", re.IGNORECASE)

def load_emoticon_map(path: str) -> Dict[str, str]:
    """
    Tải bản đồ biểu tượng cảm xúc từ tệp YAML.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        return {}

def _sorted_emoticons_by_length(emoticon_map: Dict[str, str]) -> List[str]:
    """Trả về các phím biểu tượng cảm xúc được sắp xếp theo độ dài mô tả để các phím dài hơn khớp trước"""
    return sorted(emoticon_map.keys(), key=len, reverse=True)

def replace_ascii_emoticons(text: str, emoticon_map: Dict[str, str]) -> Tuple[str, List[str]]:
    """
    Thay thế biểu tượng cảm xúc ASCII theo emoticon_map.
    """
    found = []
    if not emoticon_map:
        matches = FALLBACK_EMOTICON_RE.findall(text)
        return text, matches

    for emo in _sorted_emoticons_by_length(emoticon_map):
        if emo in text:
            token = emoticon_map[emo]
            count = text.count(emo)
            found.extend([emo] * count)
            text = text.replace(emo, f" {token} ")
    text = re.sub(r"\s+", " ", text).strip()
    return text, found

def demojize_text(text: str) -> Tuple[str, List[str]]:
    """
    Chuyển đổi ký tự biểu tượng cảm xúc thành mã thông báo văn bản bằng emoji.demojize 
    """
    if not EMOJI_AVAILABLE:
        return text, []
    emojis_found = [c for c in text if emoji.is_emoji(c)]
    demoj = emoji.demojize(text, language="en")
    demoj = re.sub(r"\s+", " ", demoj).strip()
    return demoj, emojis_found

def extract_basic_emoji_features(emojis_found: List[str]) -> Dict[str, int]:
    return {
        "emoji_count": len(emojis_found),
    }

def process(text: str, emoticon_map_path: str = "data/dictionaries/emoticon_map.yaml") -> Tuple[str, Dict]:
    metadata = {
        "emoticons_found": [],
        "emojis_found": [],
        "emoji_features": {},
    }

    # 1) chuyển emoji thành chữ (demojize)
    text, emojis = demojize_text(text)
    metadata["emojis_found"] = emojis
    metadata["emoji_features"] = extract_basic_emoji_features(emojis)

    # 2) thay thế emoticon ASCII
    emoticon_map = load_emoticon_map(emoticon_map_path)
    text, emoticons = replace_ascii_emoticons(text, emoticon_map)
    metadata["emoticons_found"] = emoticons
    # 3) dọn dẹp khoảng trắng thừa
    text = re.sub(r"\s+", " ", text).strip()
    return text, metadata


if __name__ == "__main__":
    samples = [
        "hay quá :)) =)))",
        "tức quá 😡🖕",
        "buồn ghê :(( T_T huhu",
        ":v cái này hài vl",
        "haha lol 😂🤣",
        "thằng 🤡 này",
        "bình thường",
        "<3 yêu quá <33",
    ]

    print("=" * 60)
    print("TEST BƯỚC 5: EMOJI & EMOTICON ")
    print("=" * 60)

    for s in samples:
        cleaned, meta = process(s, emoticon_map_path="data/dictionaries/emoticon_map.yaml")
        print(f"\nInput:  {repr(s)}")
        print(f"Output: {repr(cleaned)}")
        # print(f"Meta:   {meta}")s