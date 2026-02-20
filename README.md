# podscriber

Transcribes and extracts structured brewing insights from podcast RSS feeds, then publishes each episode as a page in a Notion database.

**Pipeline:** RSS feed → OpenAI Whisper (transcription) → Claude (extraction) → Notion

## Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) — required for splitting large audio files
  ```
  brew install ffmpeg
  ```
- API keys for OpenAI, Anthropic, and Notion

## Notion Setup

Before running, create a Notion database with these properties:

| Property | Type |
|---|---|
| Name | Title (auto-created) |
| Episode Number | Number |
| Published Date | Date |
| Podcast Name | Rich Text |
| Audio URL | URL |
| Processed At | Date |

Then:
1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) and create an integration
2. Copy the **Internal Integration Token** — this is your `NOTION_API_KEY`
3. Open your database in Notion → click `...` → **Add connections** → select your integration
4. Copy the database ID from the URL: `notion.so/<workspace>/<DATABASE_ID>?v=...`

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

## Usage

```bash
# Process all new episodes in the feed
python main.py

# Process a specific episode by number
python main.py --episode 5

# Preview what would be processed (no API calls)
python main.py --dry-run

# Override the feed URL
python main.py --feed-url https://other-feed.com/rss
```

## What Gets Extracted

Each Notion page includes:

- **Episode Summary** — 2-3 sentence overview
- **Brewing Techniques** — specific methods, processes, and tips
- **Recipes** — grain bill, hop schedule, yeast, OG/FG, process notes
- **Ingredients & Products Mentioned** — hops, malts, yeasts, adjuncts, equipment brands
- **Business & Marketing Insights** — taproom strategy, branding, distribution, pricing
- **Key Takeaways** — memorable insights and notable quotes

## State Tracking

Processed episodes are recorded in `processed_episodes.json` in the project directory. Re-running is safe — already-processed episodes are skipped. To reprocess an episode, remove its entry from the JSON file.
