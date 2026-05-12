import os

from giuman_assistant.memory import index_note

WIKI_DIR = "wiki"

SKIP_FILES = {
    "index.md",
    "log.md",
    "lint_ignore.md",
}

for filename in os.listdir(WIKI_DIR):
    if filename.endswith(".md") and filename not in SKIP_FILES:
        path = os.path.join(WIKI_DIR, filename)

        with open(path, encoding="utf-8") as f:
            content = f.read()

        index_note(content, filename)
        print(f"Indexed: {filename}")

print("Wiki re-index complete.")
