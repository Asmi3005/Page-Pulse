import re
from html import unescape
from urllib.parse import urlparse


def is_https(url: str) -> bool:
    return urlparse(url).scheme.lower() == "https"


def extract_title(html: str) -> str | None:
    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    title = unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    return title or None


def extract_meta_description(html: str) -> str | None:
    patterns = (
        r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\'][^>]*/?>',
        r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\'][^>]*/?>',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            description = unescape(re.sub(r"\s+", " ", match.group(1))).strip()
            return description or None
    return None
