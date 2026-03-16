from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def save_raw_page(base_dir: str, site: str, url_fingerprint: str, body: str, when: datetime | None = None) -> Path:
    when = when or datetime.now(timezone.utc)
    dt = when.strftime("%Y-%m-%d")
    out_dir = Path(base_dir) / f"dt={dt}" / f"site={site}" / "type=detail"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{url_fingerprint}.html"
    output.write_text(body, encoding="utf-8")
    return output
