"""
BƯỚC 7: XỬ LÝ PHỦ ĐỊNH (NEGATION)
- Mục tiêu: Đánh dấu các từ nằm trong phạm vi phủ định bằng hậu tố _NEG.
"""

import re
from typing import Tuple, List, Dict, Set

# ---- Cấu hình mặc định ----
NEGATORS: Set[str] = {
    "không", "chẳng", "chả", "chớ", "đừng", "chưa",
    "đéo", "đếch", "éo", "méo", "ko", "k", "hông", "hok", "hem",
    "khỏi"
}

SCOPE_BREAKERS: Set[str] = {
    ".", ",", "!", "?", ";", ":",
    "nhưng", "mà", "tuy", "song", "dù", "và", "hoặc", "hay"
}

class NegationHandler:
    """Lớp xử lý phủ định trong văn bản."""

    def __init__(self, window_size: int = 4, neg_suffix: str = "_NEG"):
        self.window_size = window_size
        self.neg_suffix = neg_suffix
        
        # Regex nhận diện token đặc biệt (<URL>, :angry:)
        self.special_token_pattern = re.compile(r"^(<.+>|:.+:)$")
        
        # Regex nhận diện dấu câu tách rời
        self.punctuation_pattern = re.compile(r"^[^\w]+|[^\w]+$")

    def _is_special_token(self, token: str) -> bool:
        """Kiểm tra token đặc biệt (không nên đánh dấu _NEG)."""
        return bool(self.special_token_pattern.match(token))

    def _is_scope_breaker(self, token: str) -> bool:
        """Kiểm tra token có phá vỡ phạm vi phủ định không."""
        token_lower = token.lower()
        if token_lower in SCOPE_BREAKERS:
            return True
        
        # Loại bỏ dấu câu bao quanh để kiểm tra từ gốc (vd: "nhưng," -> "nhưng")
        clean_token = self.punctuation_pattern.sub("", token_lower)
        return clean_token in SCOPE_BREAKERS

    def process(self, text: str) -> Tuple[str, Dict]:
        """
        Đánh dấu phủ định trong văn bản.
        
        Args:
            text: Văn bản đầu vào (đã tách từ sơ bộ bằng khoảng trắng).
            
        Returns: (Văn bản đã đánh dấu, Metadata thống kê)
        """
        tokens = text.split()
        result_tokens = []
        scopes = []
        
        i = 0
        n = len(tokens)
        
        while i < n:
            token = tokens[i]
            token_lower = token.lower()
            
            # Nếu không phải từ phủ định -> giữ nguyên
            if token_lower not in NEGATORS:
                result_tokens.append(token)
                i += 1
                continue
            
            # Nếu là từ phủ định -> Bắt đầu phạm vi phủ định
            result_tokens.append(token) # Giữ nguyên từ phủ định
            
            current_scope = {
                "negator": token,
                "position": i,
                "marked_words": []
            }
            
            i += 1 # Chuyển sang từ tiếp theo
            marked_count = 0
            
            # Duyệt các từ trong window_size
            while i < n and marked_count < self.window_size:
                next_token = tokens[i]
                
                # Gặp từ ngắt câu -> Dừng phạm vi
                if self._is_scope_breaker(next_token):
                    result_tokens.append(next_token)
                    i += 1
                    break
                
                # Token đặc biệt -> Không đánh dấu nhưng vẫn nằm trong window
                if self._is_special_token(next_token):
                    result_tokens.append(next_token)
                else:
                    # Đánh dấu _NEG
                    result_tokens.append(f"{next_token}{self.neg_suffix}")
                    current_scope["marked_words"].append(next_token)
                    marked_count += 1
                
                i += 1
            
            scopes.append(current_scope)
            
        marked_text = " ".join(result_tokens)
        
        metadata = {
            "negation_scopes": scopes,
            "negation_count": len(scopes),
            "words_marked": sum(len(s["marked_words"]) for s in scopes)
        }
        
        return marked_text, metadata


# Hàm wrapper để tương thích với pipeline cũ 
def process(text: str, window_size: int = 4, neg_suffix: str = "_NEG") -> Tuple[str, Dict]:
    handler = NegationHandler(window_size, neg_suffix)
    return handler.process(text)



if __name__ == "__main__":
    tests = [
        "tao không thích mày",
        "đéo quan tâm mày nói gì",
        "chẳng tôn trọng ai cả",
        "không có gì, nhưng tao ghét mày",
        "em chưa làm bài tập",
        "k hiểu j luôn",
        "đừng nói nữa, tao mệt rồi",
        "tao thích mày",
        "<USER> không thích :angry: chuyện này",
        "ko biết gì cả",
    ]


    print("TEST BƯỚC 7: NEGATION (OPTIMIZED)")

    handler = NegationHandler()
    for s in tests:
        out, meta = handler.process(s)
        print(f"\nInput : {repr(s)}")
        print(f"Output: {repr(out)}")
        print(f"Meta: negation_count={meta['negation_count']}, words_marked={meta['words_marked']}")