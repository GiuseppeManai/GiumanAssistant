import os
import re
from datetime import datetime

RAW_DIR = "raw"


def safe_filename(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9_-]+", "_", name)
    return name[:80].strip("_")


def save_raw_source(source_name, content, source_type="text"):
    os.makedirs(RAW_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = safe_filename(source_name)

    filename = f"{timestamp}_{clean_name}.{source_type}.txt"
    path = os.path.join(RAW_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Source: {source_name}\n")
        f.write(f"Type: {source_type}\n")
        f.write(f"Saved: {timestamp}\n\n")
        f.write(content)

    return path