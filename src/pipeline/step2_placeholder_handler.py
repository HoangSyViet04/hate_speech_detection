
"""
BƯỚC 2: PLACEHOLDER (NHÃN GIỮ CHỖ) 
Mục đích:
 - Thay URL/Email/Mention bằng nhãn chung (<URL>, <EMAIL>, <USER>)
"""




import re
from typing import Tuple, List, Dict

#  Biểu thức chính quy để nhận diện 
URL_PATTERN = re.compile(
    r"(https?://[^\s<>\"\'\)\]]+|www\.[^\s<>\"\'\)\]]+)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
MENTION_PATTERN = re.compile(
    r"(?<!\w)@[\w._-]+",  # @username, không có chữ phía trước
    re.UNICODE,
)


#  Các hàm xử lý  


def replace_urls(text: str) -> Tuple[str, List[str]]:
    """
    Thay tất cả URL bằng "<URL>".
    Trả về (văn bản đã thay, list các URL tìm được).
    """
    found = URL_PATTERN.findall(text)
    # Thay trực tiếp bằng <URL>
    new_text = URL_PATTERN.sub("<URL>", text)
    return new_text, found


def replace_emails(text: str) -> Tuple[str, List[str]]:
    """
    Thay tất cả email bằng "<EMAIL>".
    Trả về (văn bản đã thay, list các email tìm được).
    """
    found = EMAIL_PATTERN.findall(text)
    new_text = EMAIL_PATTERN.sub("<EMAIL>", text)
    return new_text, found


def replace_mentions(text: str) -> Tuple[str, List[str]]:
    """
    Thay tất cả @mention bằng "<USER>".
    Trả về (văn bản đã thay, list các mention tìm được).
    """
    found = MENTION_PATTERN.findall(text)
    new_text = MENTION_PATTERN.sub("<USER>", text)
    return new_text, found


def process(text: str) -> Tuple[str, Dict]:
    """
    Xử lý văn bản để thay thế:
      1) Thay URL -> <URL>
      2) Thay Email -> <EMAIL>
      3) Thay Mention -> <USER>

    Trả về:
      - text đã xử lý
      - metadata: dict chứa lists và counts cho urls, emails, mentions
    """
    if text is None:
        text = ""

    metadata = {
        "urls": [],
        "emails": [],
        "mentions": [],
        "url_count": 0,
        "email_count": 0,
        "mention_count": 0,
    }

    # 1) URL
    text, urls = replace_urls(text)
    metadata["urls"] = urls
    metadata["url_count"] = len(urls)

    # 2) Email
    text, emails = replace_emails(text)
    metadata["emails"] = emails
    metadata["email_count"] = len(emails)

    # 3) Mentions
    text, mentions = replace_mentions(text)
    metadata["mentions"] = mentions
    metadata["mention_count"] = len(mentions)

    return text, metadata


#  test nhanh 
if __name__ == "__main__":
    samples = [
        "@nguyen_van_a mày xem cái này đi https://example.com/video",
        "Liên hệ email: contact@company.vn hoặc support@abc.com",
        "Không có gì đặc biệt cả",
        "www.google.com và http://facebook.com/user/post/123, kết thúc.",
    ]


    print("TEST BƯỚC 2: PLACEHOLDER")
    for text in samples:
        out_text, meta = process(text)
        print("\nIN  :", text)
        print("OUT :", out_text)
        print("URLs   :", meta["urls"])
        print("Emails :", meta["emails"])
        print("Mentions:", meta["mentions"])
        print("Counts: urls={}, emails={}, mentions={}".format(
            meta["url_count"], meta["email_count"], meta["mention_count"]
        ))