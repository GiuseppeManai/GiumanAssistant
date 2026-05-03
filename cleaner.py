import re

def clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n")

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove repeated spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove common web noise
    noise_patterns = [
        r"(?i)sign in",
        r"(?i)log in",
        r"(?i)subscribe",
        r"(?i)accept cookies",
        r"(?i)cookie policy",
        r"(?i)privacy policy",
        r"(?i)terms of service",
        r"(?i)share this post",
        r"(?i)follow .* on linkedin",
        r"(?i)like comment share",
    ]

    lines = []
    for line in text.split("\n"):
        clean = line.strip()

        if not clean:
            lines.append("")
            continue

        if any(re.search(pattern, clean) for pattern in noise_patterns):
            continue

        # Remove very short junk lines
        if len(clean) <= 2:
            continue

        lines.append(clean)

    text = "\n".join(lines)

    # Remove too many blank lines again
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()