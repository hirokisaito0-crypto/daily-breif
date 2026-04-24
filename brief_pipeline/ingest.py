from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx
import yaml

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedItem:
    feed_id: str
    feed_title: str
    title: str
    link: str
    summary: str
    published: datetime | None
    item_id: str

    def as_llm_dict(self) -> dict[str, Any]:
        pub = self.published.isoformat() if self.published else ""
        return {
            "item_id": self.item_id,
            "feed_id": self.feed_id,
            "feed_title": self.feed_title,
            "title": self.title,
            "link": self.link,
            "summary": (self.summary or "")[:800],
            "published": pub,
        }


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    import time as time_mod

    for key in ("published", "updated"):
        tp = entry.get(f"{key}_parsed")
        if tp:
            try:
                return datetime.fromtimestamp(
                    time_mod.mktime(tp), tz=timezone.utc
                )
            except Exception:
                pass
        raw = entry.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _strip_html(s: str) -> str:
    import re

    t = re.sub(r"<[^>]+>", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _item_id(link: str, title: str) -> str:
    h = hashlib.sha256(f"{link}\n{title}".encode("utf-8")).hexdigest()[:16]
    return h


def load_feed_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_feed_items(
    config_path: Path,
    *,
    client: httpx.Client | None = None,
) -> list[FeedItem]:
    cfg = load_feed_config(config_path)
    feeds = cfg.get("feeds") or []
    ingest = cfg.get("ingest") or {}
    max_age_h = float(ingest.get("max_item_age_hours", 72))
    timeout = float(ingest.get("request_timeout_seconds", 25))
    max_per = int(ingest.get("max_entries_per_feed", 30))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_h)

    own_client = client is None
    if own_client:
        client = httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "DailyBriefBot/1.0 (RSS ingest; contact: local run)"
            },
        )

    assert client is not None
    out: list[FeedItem] = []
    try:
        for feed in feeds:
            fid = str(feed.get("id") or "")
            ftitle = str(feed.get("title") or fid)
            url = str(feed.get("url") or "").strip()
            if not url:
                continue
            try:
                r = client.get(url)
                r.raise_for_status()
            except Exception as e:
                log.warning("feed fetch failed %s: %s", url, e)
                continue
            parsed = feedparser.parse(r.content)
            for i, entry in enumerate(parsed.entries or []):
                if i >= max_per:
                    break
                title = _strip_html(str(entry.get("title") or "")).strip() or "(無題)"
                link = str(entry.get("link") or entry.get("id") or "").strip()
                if not link:
                    continue
                summary_raw = entry.get("summary") or entry.get("description") or ""
                summary = _strip_html(str(summary_raw))[:1200]
                published = _parse_published(entry)
                if published and published < cutoff:
                    continue
                host = urlparse(link).netloc or fid
                out.append(
                    FeedItem(
                        feed_id=fid or host,
                        feed_title=ftitle,
                        title=title,
                        link=link,
                        summary=summary,
                        published=published,
                        item_id=_item_id(link, title),
                    )
                )
    finally:
        if own_client:
            client.close()

    # 新しい順に並べ、同一リンクは先勝ち
    seen: set[str] = set()
    deduped: list[FeedItem] = []
    out.sort(
        key=lambda x: (x.published or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    for it in out:
        if it.link in seen:
            continue
        seen.add(it.link)
        deduped.append(it)
    return deduped
