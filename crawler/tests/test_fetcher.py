from __future__ import annotations

import io
import urllib.request

from crawler.spiders.fetcher import HttpFetcher


class _MockResponse:
    def __init__(self, body: str, code: int = 200) -> None:
        self._buf = io.BytesIO(body.encode("utf-8"))
        self._code = code

    def read(self) -> bytes:
        return self._buf.read()

    def getcode(self) -> int:
        return self._code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_http_fetcher_success(monkeypatch) -> None:
    def _fake_urlopen(req, timeout=0):
        return _MockResponse("<html>ok</html>", 200)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    fetcher = HttpFetcher(retries=1)
    result = fetcher.fetch("https://s.hqew.com/product/ABC123")
    assert result.status_code == 200
    assert "ok" in result.body
