from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from dateutil import parser as date_parser


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(html.unescape(str(value)), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(url: str, base: str | None = None) -> str:
    absolute = urljoin(base or "", url)
    parts = urlsplit(absolute)
    query = "&".join(
        pair for pair in parts.query.split("&")
        if pair and not pair.lower().startswith(("utm_", "source=", "ref="))
    )
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def stable_id(*parts: str) -> str:
    normalized = "|".join(re.sub(r"\W+", " ", p.lower()).strip() for p in parts if p)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:18]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(clean_text(value), fuzzy=True, dayfirst=False)
        if parsed.year < 2000 or parsed.year > date.today().year + 2:
            return None
        return parsed.date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def first_match(patterns: list[str], text: str, flags: int = re.I) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return clean_text(match.group(1))
    return None
