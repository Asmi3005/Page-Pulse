from app.utils import extract_meta_description, extract_title, is_https


def test_extract_title() -> None:
    html = "<html><head><title>  Hello &amp; World  </title></head></html>"
    assert extract_title(html) == "Hello & World"


def test_extract_meta_description_name_first() -> None:
    html = '<meta name="description" content="Short summary">'
    assert extract_meta_description(html) == "Short summary"


def test_extract_meta_description_content_first() -> None:
    html = '<meta content="Other order" name="description">'
    assert extract_meta_description(html) == "Other order"


def test_is_https() -> None:
    assert is_https("https://example.com") is True
    assert is_https("http://example.com") is False
