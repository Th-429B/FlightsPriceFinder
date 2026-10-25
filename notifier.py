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
    """Return (token, chat_ids); TELEGRAM_CHAT_ID may be comma-separated."""
    _load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids = [
        c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()
    ]
    if not token or not chat_ids:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set "
            "(as environment variables or in a .env file); "
            "TELEGRAM_CHAT_ID can list several chats separated by commas"
        )
    return token, chat_ids


def _for_each_chat(chat_ids, send):
    """Run send(chat_id) for every chat; one bad chat must not block the rest.

    Raises after the loop if any chat failed."""
    failed = []
    for chat_id in chat_ids:
        try:
            send(chat_id)
        except requests.RequestException as e:
            failed.append(f"{chat_id}: {e}")
    if failed:
        raise RuntimeError("Telegram send failed for " + "; ".join(failed))


def send_telegram(message: str):
    """Send a Markdown-formatted message to every configured Telegram chat."""
    token, chat_ids = _credentials()

    def send(chat_id):
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

    _for_each_chat(chat_ids, send)


def send_photo(photo_path: str, caption: str = ""):
    """Send a photo to every configured Telegram chat."""
    token, chat_ids = _credentials()

    def send(chat_id):
        with open(photo_path, "rb") as photo:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": photo},
                timeout=60,
            )
        response.raise_for_status()

    _for_each_chat(chat_ids, send)
