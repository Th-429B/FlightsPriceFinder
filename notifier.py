import os
from pathlib import Path

import requests


def _load_dotenv():
    """Load key=value pairs from a .env file next to this script, if present.

    Real environment variables take precedence over .env values.
    """
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _credentials():
    _load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set "
            "(as environment variables or in a .env file)"
        )
    return token, chat_id


def send_telegram(message: str):
    """Send a Markdown-formatted message to the configured Telegram chat."""
    token, chat_id = _credentials()
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        },
        timeout=30,
    )
    response.raise_for_status()


def send_photo(photo_path: str, caption: str = ""):
    """Send a photo to the configured Telegram chat."""
    token, chat_id = _credentials()
    with open(photo_path, "rb") as photo:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": photo},
            timeout=60,
        )
    response.raise_for_status()
