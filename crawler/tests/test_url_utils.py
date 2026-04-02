from crawler.spiders.url_utils import fingerprint_url, normalize_url


def test_normalize_url_removes_tracking_query_and_sorts() -> None:
    normalized = normalize_url("https://s.hqew.com/a/b/?utm_source=x&b=2&a=1")
    assert normalized == "https://s.hqew.com/a/b?a=1&b=2"


def test_fingerprint_is_stable() -> None:
    a = fingerprint_url("https://s.hqew.com/a?b=2&a=1")
    b = fingerprint_url("https://s.hqew.com/a?a=1&b=2")
    assert a == b
