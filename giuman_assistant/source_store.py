import re
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("raw")
MAX_RAW_CHARS = 100_000


def safe_filename(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9_-]+", "_", name)
    name = name[:80].strip("_")
    return name or "source"


def trim_content(content, limit=MAX_RAW_CHARS):
    if not content:
        return ""

    if len(content) <= limit:
        return content

    return content[:limit] + "\n\n[TRUNCATED]"


def save_raw_source(source_name, content, source_type="text"):
    RAW_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = safe_filename(source_name)
    clean_type = safe_filename(source_type)

    filename = f"{timestamp}_{clean_name}.{clean_type}.txt"
    path = RAW_DIR / filename

    content = trim_content(content)

    path.write_text(
        f"Source: {source_name}\nType: {source_type}\nSaved: {timestamp}\n\n{content}",
        encoding="utf-8",
    )

    return str(path)
