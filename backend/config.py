import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = "gpt-4o"

# Not used yet — will activate when YouTube API key is added (Phase 1 later)
YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

REDDIT_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

DATA_DIR: Path = Path("data/runs")
DATA_DIR.mkdir(parents=True, exist_ok=True)
