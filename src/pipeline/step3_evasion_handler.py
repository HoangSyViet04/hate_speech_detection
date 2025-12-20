
"""
BƯỚC 3: GỠ "LÁCH LUẬT" (EVASION HANDLER)
========================================
Mục tiêu:
- Xử lý các từ bị cố tình viết sai để lách luật (evasion).
- Các dạng evasion:
  1. Chèn ký tự rác vào giữa từ: "g.i.ế.t", "c.h.ế.t"
  2. Tách từ thành nhiều phần: "t. ox. ic", "n g u"
  3. Dùng số/ký tự đặc biệt thay chữ (Leetspeak) - (Có thể xử lý ở đây hoặc bước riêng)

Cải tiến:
- Sử dụng Dictionary để kiểm tra việc ghép từ có tạo ra từ có nghĩa (hoặc từ nhạy cảm) hay không.
- Tránh ghép nhầm các từ bình thường (vd: "câu. Sang" -> không ghép).
"""

import re
import os
import yaml
from typing import Set, Tuple, List
from pathlib import Path

class EvasionHandler:
    def __init__(self, dictionary_path: str = None):
        """
        Khởi tạo EvasionHandler.
        :param dictionary_path: Đường dẫn đến file YAML chứa danh sách từ nhạy cảm (profanity).
        """
        self.profanity_set = set()
        
        # 1. Load từ điển nếu có
        if dictionary_path:
            self.profanity_set = self._load_dictionary(dictionary_path)
        
        # 2. Thêm danh sách từ evasion phổ biến (hardcoded fallback)
        # Đây là các từ thường xuyên bị evasion mà ta muốn bắt buộc xử lý
        self.profanity_set.update({
            "toxic", "chết", "giết", "ngu", "địt", "lồn", "cặc", "đéo", "chó", 
            "đĩ", "phò", "cút", "biến", "súc vật", "óc chó", "ngáo", "điên"
        })

        # 3. Regex Patterns
        
        # Pattern 1: Ký tự rác NẰM TRONG token (không chứa khoảng trắng)
        # Ví dụ: "g.i.ế.t", "c-h-ế-t", "đ.ị.t"
        # Match: (chữ cái) + (ký tự rác liên tiếp) + (chữ cái)
        self.INTRA_JUNK_PATTERN = re.compile(
            r"(\w)[\._\-\=\+\*\~\,\;\:\'\"\`\!\?\@\#\$\%\^\&]+(\w)", 
            re.UNICODE
        )

        # Pattern 2a: Chuỗi từ bị tách bởi KÝ TỰ RÁC (có thể kèm space)
        # Bắt buộc phải có ký tự rác để tránh match nhầm câu bình thường
        # Regex: Word + (Junk_Sep + Word) + ...
        # Junk_Sep: \s* [junk] \s*
        self.JUNK_BROKEN_PATTERN = re.compile(
            r"\b\w+(?:\s*[\._\-\=\+\*]+\s*\w+)+\b", 
            re.UNICODE
        )

        # Pattern 2b: Chuỗi KÝ TỰ ĐƠN bị tách bởi KHOẢNG TRẮNG (không có junk)
        # VD: "n g u", "c h ế t"
        # Regex: SingleChar + (Space + SingleChar) + ...
        self.SPACE_SINGLE_CHAR_PATTERN = re.compile(
            r"\b\w(?:\s+\w)+\b", 
            re.UNICODE
        )

    def _load_dictionary(self, path: str) -> Set[str]:
        """Load danh sách từ nhạy cảm từ file YAML."""
        words = set()
        try:
            if not os.path.exists(path):
                # Thử tìm tương đối so với file này
                base_dir = Path(__file__).resolve().parent.parent.parent
                # Dự đoán path: data/dictionaries/profanity_words.yaml
                alt_path = base_dir / "data" / "dictionaries" / "profanity_words.yaml"
                if alt_path.exists():
                    path = str(alt_path)
                else:
                    # print(f" EvasionHandler: Không tìm thấy từ điển tại {path}")
                    return words

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and 'single_words' in data:
                    words.update(w.lower() for w in data['single_words'])
        except Exception as e:
            print(f" EvasionHandler: Lỗi load từ điển {e}")
        return words

    def _normalize_intra_token(self, text: str) -> str:
        """
        Xử lý rác trong token đơn (không có space).
        VD: "g.i.ế.t" -> "giết"
        """
        # Lặp vài lần để xử lý rác lồng nhau hoặc nhiều lớp
        for _ in range(3):
            new_text, count = self.INTRA_JUNK_PATTERN.subn(r"\1\2", text)
            if count == 0:
                break
            text = new_text
        return text

    def _join_junk_broken_words(self, text: str) -> str:
        """
        Nối các từ bị tách bởi ký tự rác (Pattern 2a).
        VD: "t. ox. ic" -> "toxic"
        """
        def replace_func(match):
            original = match.group(0)
            cleaned = re.sub(r"[^\w]", "", original)
            
            # 1. Check Dictionary
            if cleaned.lower() in self.profanity_set:
                return cleaned
            
            # 2. Heuristic: Sentence Boundary Check
            # Nếu pattern giống "câu. Sang" (Lower. Upper) -> Không nối
            # Nếu pattern là "t. ox. ic" (Lower. Lower) -> Nối
            # Lấy các phần tử từ
            words = re.findall(r"\w+", original)
            if len(words) < 2: return original
            
            # Kiểm tra case transition
            has_sentence_boundary = False
            for i in range(len(words) - 1):
                w1, w2 = words[i], words[i+1]
                if w1.islower() and w2[0].isupper():
                    has_sentence_boundary = True
                    break
            
            if has_sentence_boundary:
                return original # Giữ nguyên nếu giống ngắt câu
            
            # Nếu không phải ngắt câu -> Nối (vì đã match pattern chứa junk)
            return cleaned

        return self.JUNK_BROKEN_PATTERN.sub(replace_func, text)

    def _join_space_single_chars(self, text: str) -> str:
        """
        Nối các ký tự đơn bị tách bởi space (Pattern 2b).
        VD: "n g u" -> "ngu"
        """
        def replace_func(match):
            original = match.group(0)
            cleaned = re.sub(r"\s+", "", original)
            # Với ký tự đơn, ta luôn nối vì ít khi có ngữ cảnh "a b c" có nghĩa khác trong hate speech
            return cleaned

        return self.SPACE_SINGLE_CHAR_PATTERN.sub(replace_func, text)

    def process(self, text: str) -> Tuple[str, dict]:
        """Quy trình xử lý chính."""
        if not text:
            return "", {}
            
        original_text = text
        
        # B1: Xử lý rác nội bộ (g.i.ế.t -> giết)
        text = self._normalize_intra_token(text)
        
        # B2: Xử lý từ bị tách bởi rác (t. ox. ic -> toxic)
        text = self._join_junk_broken_words(text)
        
        # B3: Xử lý ký tự đơn (n g u -> ngu)
        text = self._join_space_single_chars(text)
        
        meta = {
            "changed": text != original_text
        }
        return text, meta

# === TEST NHANH ===
if __name__ == "__main__":
    handler = EvasionHandler("data/dictionaries/profanity_words.yaml")
    
    examples = [
        ("thằng này t. ox. ic thật", "Evasion dấu chấm + space"),
        ("thằng này n g u quá", "Evasion space ký tự đơn"),
        ("giết c.h.ế.t mày", "Evasion dấu chấm nội bộ"),
        ("câu. Sang câu mới", "Không phải evasion (không nối)"),
        ("đ.ị.t mẹ mày", "Evasion dấu chấm nội bộ"),
        ("thằng này t.ox.ic vãi", "Evasion dấu chấm không space")
    ]
    print(f"{'INPUT':<30} | {'OUTPUT':<30}")
    print("-" * 65)
    for ex, desc in examples:
        res, _ = handler.process(ex)
        print(f"{ex:<30} | {res}")
    