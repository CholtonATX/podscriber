from datetime import datetime, timezone

import feedparser

from logger import get_logger
from models import Episode

logger = get_logger(__name__)


def parse_feed(url: str) -> list[Episode]:
    """Parse RSS feed and return episodes sorted oldest-first with stable 1..N numbering."""
    logger.info(f"Fetching feed: {url}")
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        logger.warning(f"Feed parse error: {feed.bozo_exception}")
        return []

    podcast_name = feed.feed.get("title", "Unknown Podcast")
    logger.info(f"Podcast: {podcast_name} — {len(feed.entries)} entries found")

    entries_with_audio = []
    for entry in feed.entries:
        audio_url = _extract_audio_url(entry)
        if audio_url:
            entries_with_audio.append((entry, audio_url))

    # Sort oldest-first for stable episode numbering
    entries_with_audio.sort(key=lambda x: x[0].get("published_parsed") or (0,))

    episodes = []
    for i, (entry, audio_url) in enumerate(entries_with_audio, start=1):
        episodes.append(Episode(
            number=i,
            title=entry.get("title", "Untitled"),
            published=_parse_date(entry.get("published_parsed")),
            audio_url=audio_url,
            description=_strip_html(entry.get("summary", "")),
            podcast_name=podcast_name,
        ))

    return episodes


def _extract_audio_url(entry) -> str | None:
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("audio/"):
            return enc.get("href") or enc.get("url")
    for link in entry.get("links", []):
        if link.get("rel") == "enclosure":
            href = link.get("href")
            if href:
                return href
    return None


def _parse_date(published_parsed) -> datetime:
    if published_parsed:
        return datetime(*published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def _strip_html(text: str) -> str:
    """Remove basic HTML tags from description text."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()
