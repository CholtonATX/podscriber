import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("processed_episodes.json")


class StateManager:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self._state: dict = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {}

    def is_processed(self, episode_number: int) -> bool:
        return str(episode_number) in self._state

    def mark_processed(self, episode_number: int, notion_url: str, episode_title: str) -> None:
        self._state[str(episode_number)] = {
            "title": episode_title,
            "notion_url": notion_url,
            "processed_at": datetime.utcnow().isoformat(),
        }
        self._save()

    def _save(self) -> None:
        with open(self.state_file, "w") as f:
            json.dump(self._state, f, indent=2)

    def get_processed_count(self) -> int:
        return len(self._state)
