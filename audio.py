import time
from pathlib import Path

import requests

from logger import get_logger

logger = get_logger(__name__)

WHISPER_MAX_BYTES = 24 * 1024 * 1024  # 24 MB — leave margin below Whisper's 25 MB limit
_DOWNLOAD_RETRIES = 3
_RETRY_DELAY = 5  # seconds


def download_audio(url: str, temp_dir: str, episode_number: int) -> Path:
    """Stream-download audio to temp_dir with retries. Returns path to downloaded file."""
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)

    ext = Path(url.split("?")[0]).suffix or ".mp3"
    dest = temp_path / f"episode_{episode_number}{ext}"

    for attempt in range(1, _DOWNLOAD_RETRIES + 1):
        try:
            logger.info(f"Downloading audio to {dest} (attempt {attempt}/{_DOWNLOAD_RETRIES})")
            dest.unlink(missing_ok=True)  # Remove partial file from previous attempt
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded {size_mb:.1f} MB")
            return dest
        except (requests.ConnectionError, requests.ChunkedEncodingError) as e:
            if attempt == _DOWNLOAD_RETRIES:
                raise
            logger.warning(f"Download interrupted ({e}), retrying in {_RETRY_DELAY}s...")
            time.sleep(_RETRY_DELAY)

    raise RuntimeError("Download failed after all retries")  # unreachable, satisfies type checker


def split_audio_if_needed(audio_path: Path) -> list[Path]:
    """
    Return [audio_path] if under limit, otherwise split into ~10-minute chunks.
    Requires ffmpeg on PATH.
    """
    if audio_path.stat().st_size <= WHISPER_MAX_BYTES:
        return [audio_path]

    logger.info(f"File exceeds 24 MB — splitting into chunks")
    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError("pydub is required for audio chunking: pip install pydub")

    audio = AudioSegment.from_file(audio_path)
    chunk_ms = 10 * 60 * 1000  # 10 minutes in milliseconds
    chunks = []

    base = audio_path.with_suffix("")
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = base.parent / f"{base.name}_chunk{i:03d}.mp3"
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)
        logger.info(f"  Chunk {i}: {chunk_path.name} ({chunk_path.stat().st_size / (1024*1024):.1f} MB)")

    # Remove the original after splitting
    audio_path.unlink()
    return chunks


def cleanup_audio(paths: list[Path]) -> None:
    """Delete all audio files."""
    for p in paths:
        p.unlink(missing_ok=True)
