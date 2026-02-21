import sys
from pathlib import Path

import click

from audio import cleanup_audio, download_audio, split_audio_if_needed
from config import load_config
from extractor import extract_insights
from feed import parse_feed
from logger import get_logger
from models import Episode
from notion_writer import create_episode_page
from state import StateManager
from transcriber import transcribe

logger = get_logger("podscriber")


@click.command()
@click.option("--episode", "-e", type=int, default=None, help="Process a specific episode number only")
@click.option("--from", "from_episode", type=int, default=None, help="Start batch from this episode number")
@click.option("--limit", "-n", type=int, default=None, help="Max number of unprocessed episodes to process")
@click.option("--dry-run", is_flag=True, default=False, help="Print what would be processed without calling APIs")
@click.option("--feed-url", default=None, help="Override the RSS feed URL from .env")
@click.option("--database", "database_id", default=None, help="Override the Notion database ID from .env")
def main(episode: int | None, from_episode: int | None, limit: int | None, dry_run: bool, feed_url: str | None, database_id: str | None) -> None:
    """Podscriber: transcribe and extract brewing insights from podcast episodes."""
    try:
        config = load_config(feed_url_override=feed_url, database_id_override=database_id)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    state = StateManager()
    episodes = parse_feed(config.rss_feed_url)

    if not episodes:
        click.echo("No episodes found in feed.")
        return

    # Filter to target episode(s)
    if episode is not None:
        targets = [ep for ep in episodes if ep.number == episode]
        if not targets:
            click.echo(f"Episode {episode} not found. Feed has episodes 1–{len(episodes)}.")
            sys.exit(1)
    else:
        targets = [ep for ep in episodes if not state.is_processed(ep.number)]
        if from_episode is not None:
            targets = [ep for ep in targets if ep.number >= from_episode]
        if limit is not None:
            targets = targets[:limit]

    if not targets:
        click.echo(f"All episodes already processed. ({state.get_processed_count()} total)")
        return

    click.echo(f"Episodes to process: {len(targets)}")
    for ep in targets:
        click.echo(f"  [{ep.number}] {ep.title} ({ep.published.strftime('%Y-%m-%d')})")

    if dry_run:
        click.echo("\nDry run — no API calls made.")
        return

    click.echo("")
    for ep in targets:
        _process_episode(ep, config, state)

    click.echo(f"\nDone. {state.get_processed_count()} episodes processed total.")


def _process_episode(episode: Episode, config, state: StateManager) -> None:
    audio_paths = []
    try:
        logger.info(f"[Ep. {episode.number}] Starting: {episode.title}")

        logger.info(f"[Ep. {episode.number}] Downloading audio...")
        raw_path = download_audio(episode.audio_url, config.temp_dir, episode.number)
        audio_paths = split_audio_if_needed(raw_path)

        logger.info(f"[Ep. {episode.number}] Transcribing ({len(audio_paths)} chunk(s))...")
        transcript = transcribe(audio_paths, config.openai_api_key)
        logger.info(f"[Ep. {episode.number}] Transcript: {len(transcript):,} characters")

        logger.info(f"[Ep. {episode.number}] Extracting brewing insights with Claude...")
        insights = extract_insights(
            transcript=transcript,
            episode_title=episode.title,
            episode_description=episode.description,
            api_key=config.anthropic_api_key,
        )

        logger.info(f"[Ep. {episode.number}] Creating Notion page...")
        notion_url = create_episode_page(
            episode=episode,
            insights=insights,
            database_id=config.notion_database_id,
            api_key=config.notion_api_key,
        )

        state.mark_processed(episode.number, notion_url, episode.title)
        logger.info(f"[Ep. {episode.number}] Done. {notion_url}")

    except Exception as e:
        logger.error(
            f"[Ep. {episode.number}] FAILED: {type(e).__name__}: {e}",
            exc_info=True,
        )

    finally:
        if audio_paths:
            cleanup_audio(audio_paths)
            logger.info(f"[Ep. {episode.number}] Audio cleaned up")


if __name__ == "__main__":
    main()
