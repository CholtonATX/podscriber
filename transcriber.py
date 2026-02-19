from pathlib import Path

from openai import OpenAI

from logger import get_logger

logger = get_logger(__name__)


def transcribe(audio_paths: list[Path], api_key: str) -> str:
    """
    Transcribe one or more audio chunks via OpenAI Whisper API.
    Returns concatenated transcript string.
    """
    client = OpenAI(api_key=api_key)
    transcripts = []

    for i, path in enumerate(audio_paths, start=1):
        logger.info(f"  Transcribing chunk {i}/{len(audio_paths)}: {path.name}")
        with open(path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
            )
        transcripts.append(response)

    return "\n\n---\n\n".join(transcripts)
