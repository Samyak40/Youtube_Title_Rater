import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

# API configuration
API_KEY = os.getenv("YOUTUBE_API_KEY")

# Directory setup
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Channel discovery configuration
NICHE_KEYWORDS = {
    "tech": ["tech review", "smartphone review", "tech unboxing"],
    "gaming": ["gaming commentary", "let's play", "gaming news"],
    "finance": ["personal finance", "crypto investing", "stock market analysis"]
}

MIN_SUBSCRIBERS = 50_000
MAX_SUBSCRIBERS = 3_000_000
CHANNELS_PER_KEYWORD = 30

# Video collection configuration
MAX_VIDEOS_PER_CHANNEL = 100
