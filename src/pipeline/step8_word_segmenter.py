"""
BƯỚC 8: TÁCH TỪ TIẾNG VIỆT (WORD SEGMENTATION)
"""

import re
from typing import Tuple, List, Dict

try:
    from pyvi import ViTokenizer
    PYVI_AVAILABLE = True
except ImportError:
    PYVI_AVAILABLE = False
    print("Thư viện 'pyvi' chưa cài")


class WordSegmenter:
    """Lớp tách từ tiếng Việt hỗ trợ xử lý token đặc biệt và từ ghép tùy chỉnh."""

    def __init__(self, tool: str = "pyvi"):
        self.tool = tool
        
        # 1. Regex cho token đặc biệt (giữ nguyên không tách)
        self.SPECIAL_TOKEN_PATTERN = re.compile(
            r"(<[A-Z]+>)|"          # <URL>, <USER>
            r"(:[a-z_]+:)|"         # :angry:
            r"(#[\w_]+)"           
        )

        # 2. Danh sách từ ghép quan trọng (Tự động tạo mapping: "từ ghép" -> "từ_ghép")
        # Thêm các từ lóng, chửi bậy mà PyVi có thể bỏ sót
        raw_phrases = [
            "địt mẹ", "địt con mẹ", "đụ mẹ", "đụ má", "con chó", "con lợn",
            "đồ chó", "đồ ngu", "đồ khốn", "thằng ngu", "con ngu", "thằng chó",
            "thằng khốn", "óc chó", "cái lồn", "con cặc", "vãi lồn", "vãi cả lồn",
            "cút đi", "biến đi", "chết đi", "đi chết đi", "mẹ mày", "bố mày",
            "cha mày", "não phẳng", "ngu như", "ngu vãi"
        ]
        self.phrase_map = {p: p.replace(" ", "_") for p in raw_phrases}
        
        # Tối ưu: Tạo 1 Regex duy nhất để match tất cả từ ghép (Nhanh hơn loop)
        # Sắp xếp theo độ dài giảm dần để ưu tiên cụm dài 
        sorted_phrases = sorted(self.phrase_map.keys(), key=len, reverse=True)
        self.phrase_pattern = re.compile(
            "|".join(map(re.escape, sorted_phrases)), 
            re.IGNORECASE
        )

    def _replace_special_tokens(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Thay thế token đặc biệt bằng placeholder [SPECIAL_i] để bảo vệ khỏi PyVi"""
        special_map = {}
        counter = 0

        def replace_func(match):
            nonlocal counter
            token = match.group(0)
            placeholder = f"[SPECIAL_{counter}]"
            special_map[placeholder] = token
            counter += 1
            return placeholder

        masked_text = self.SPECIAL_TOKEN_PATTERN.sub(replace_func, text)
        return masked_text, special_map

    def _restore_special_tokens(self, text: str, special_map: Dict[str, str]) -> str:
        """Khôi phục token đặc biệt từ placeholder"""
        for placeholder, token in special_map.items():
            # Xử lý trường hợp segmenter dính placeholder vào từ khác (vd: từ_[SPECIAL_0])
            text = text.replace(f"_{placeholder}", f" {token}")
            text = text.replace(f"{placeholder}_", f"{token} ")
            text = text.replace(placeholder, token)
        return text

    def _segment_custom_phrases(self, text: str) -> str:
        """Nối từ ghép tùy chỉnh trước khi đưa vào PyVi"""
        def replace_func(match):
            word = match.group(0)
            # Trả về dạng nối từ (lowercase key để lookup)
            return self.phrase_map.get(word.lower(), word.replace(" ", "_"))
            
        return self.phrase_pattern.sub(replace_func, text)

    def process(self, text: str) -> Tuple[str, dict]:
        """
        Quy trình tách từ đầy đủ:
        1. Ẩn token đặc biệt -> 2. Nối từ ghép tùy chỉnh -> 3. PyVi -> 4. Khôi phục token
        """
        # B1: Ẩn token đặc biệt
        text, special_map = self._replace_special_tokens(text)

        # B2: Xử lý từ ghép tùy chỉnh 
        text = self._segment_custom_phrases(text)

        # B3: Chạy PyVi (nếu có)
        if PYVI_AVAILABLE and self.tool == "pyvi":
            try:
                text = ViTokenizer.tokenize(text)
            except Exception:
                pass # Fallback nếu PyVi lỗi, giữ nguyên kết quả B2

        # B4: Khôi phục token đặc biệt
        text = self._restore_special_tokens(text, special_map)

        # Metadata thống kê
        compounds = re.findall(r"\w+_\w+(?:_\w+)*", text)
        
        return text, {
            "compound_words": compounds,
            "compound_count": len(compounds),
            "tool_used": "pyvi" if PYVI_AVAILABLE else "simple"
        }


# === TEST NHANH ===
if __name__ == "__main__":
    segmenter = WordSegmenter()
    examples = [
        ("<USER> thằng này ngu quá :angry:", "Token đặc biệt"),
        ("học sinh này hư quá", "PyVi chuẩn"),
        ("địt con mẹ mày", "Từ ghép tùy chỉnh"),
        ("Việt Nam vô địch", "Tên riêng"),
        ("thằng ngu_NEG này", "Token NEG")
    ]
    
    print(f"{'INPUT':<30} | {'OUTPUT':<30}")
    print("-" * 65)
    for ex, desc in examples:
        res, _ = segmenter.process(ex)
        print(f"{ex:<30} | {res}")

