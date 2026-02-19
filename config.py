import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    openai_api_key: str
    anthropic_api_key: str
    notion_api_key: str
    notion_database_id: str
    rss_feed_url: str
    temp_dir: str = field(default="/tmp/podscriber")


def load_config(feed_url_override: str | None = None) -> Config:
    """Load and validate config from .env. Raises ValueError on missing keys."""
    load_dotenv()

    required = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
        "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        "RSS_FEED_URL": os.getenv("RSS_FEED_URL"),
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    temp_dir = os.getenv("TEMP_DIR", "/tmp/podscriber")
    Path(temp_dir).mkdir(parents=True, exist_ok=True)

    return Config(
        openai_api_key=required["OPENAI_API_KEY"],
        anthropic_api_key=required["ANTHROPIC_API_KEY"],
        notion_api_key=required["NOTION_API_KEY"],
        notion_database_id=required["NOTION_DATABASE_ID"],
        rss_feed_url=feed_url_override or required["RSS_FEED_URL"],
        temp_dir=temp_dir,
    )
