from pathlib import Path

import fitz

from giuman_assistant.llm import describe_image, summarize_for_wiki
from giuman_assistant.memory import index_note
from giuman_assistant.source_store import save_raw_source
from giuman_assistant.wiki_manager import integrate_into_wiki

INBOX = Path.home() / "OneDrive" / "Giuman_Assistant_Inbox_AINOTE2"
RAW = INBOX / "raw"
PROCESSED = INBOX / "processed"
FAILED = INBOX / "failed"

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_PDF_PAGES = 5


def ensure_folders():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)


def render_pdf_pages(path):
    doc = fitz.open(path)
    images = []

    for page_index in range(min(len(doc), MAX_PDF_PAGES)):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        images.append(pix.tobytes("png"))

    return images


def read_image(path):
    return path.read_bytes()


def describe_file(path):
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        page_images = render_pdf_pages(path)
        descriptions = []

        for i, image_bytes in enumerate(page_images, start=1):
            description = describe_image(image_bytes, f"{path.name} page {i}")
            descriptions.append(f"## Page {i}\n{description}")

        return "\n\n".join(descriptions)

    if suffix in {".png", ".jpg", ".jpeg"}:
        return describe_image(read_image(path), path.name)

    raise ValueError(f"Unsupported file type: {suffix}")


def reindex_updated_files(updated_files):
    for filename in updated_files:
        clean_name = filename.replace("wiki/", "").replace("wiki\\", "")
        path = Path("wiki") / clean_name

        if path.exists():
            index_note(path.read_text(encoding="utf-8"), clean_name)


def import_file(path, category, knowledge_type):
    print(f"\nImporting: {path.name}")

    extracted = describe_file(path)

    if not extracted.strip():
        raise ValueError("No content extracted")

    raw_path = save_raw_source(path.stem, extracted, "ainote_pdf")

    summary = summarize_for_wiki(extracted)

    header = f"""
---
category: {category}
source_device: iflytek_ainote
source_file: {path.name}
source_type: handwritten_pdf
---

{summary}
"""

    updated_files = integrate_into_wiki(header, path.stem, knowledge_type)
    reindex_updated_files(updated_files)

    target = PROCESSED / path.name
    path.replace(target)

    print(f"Saved raw source: {raw_path}")
    print(f"Updated wiki files: {updated_files}")
    print(f"Moved to: {target}")


def choose_category():
    categories = [
        "personal",
        "family",
        "professional",
        "confidential",
        "health",
        "finance",
        "learning",
        "ideas",
    ]

    print("\nCategory:")
    for i, category in enumerate(categories, start=1):
        print(f"{i}. {category}")

    choice = input("Choose category [default professional]: ").strip()

    if not choice:
        return "professional"

    return categories[int(choice) - 1]


def choose_knowledge_type():
    types = [
        "Source only",
        "Idea",
        "Concept",
        "Framework",
        "Project",
        "Client",
        "Decision",
        "Pattern",
        "Profile",
        "Action",
    ]

    print("\nKnowledge type:")
    for i, item in enumerate(types, start=1):
        print(f"{i}. {item}")

    choice = input("Choose type [default Source only]: ").strip()

    if not choice:
        return "Source only"

    return types[int(choice) - 1]


def main():
    ensure_folders()

    files = [
        path
        for path in RAW.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED
    ]

    if not files:
        print(f"No supported files found in {RAW}")
        return

    print("\nFound files:")
    for i, path in enumerate(files, start=1):
        print(f"{i}. {path.name}")

    selected = input("\nImport all files? [y/N]: ").strip().lower()

    if selected != "y":
        print("Cancelled.")
        return

    category = choose_category()
    knowledge_type = choose_knowledge_type()

    for path in files:
        try:
            import_file(path, category, knowledge_type)
        except Exception as e:
            print(f"Failed to import {path.name}: {e}")
            path.replace(FAILED / path.name)


if __name__ == "__main__":
    main()

import fitz

from giuman_assistant.llm import describe_image, summarize_for_wiki
from giuman_assistant.memory import index_note
from giuman_assistant.source_store import save_raw_source
from giuman_assistant.wiki_manager import integrate_into_wiki

INBOX = Path.home() / "OneDrive" / "Giuman_Assistant_Inbox_AINOTE2"
RAW = INBOX / "raw"
PROCESSED = INBOX / "processed"
FAILED = INBOX / "failed"

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_PDF_PAGES = 5


def ensure_folders():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)


def render_pdf_pages(path):
    doc = fitz.open(path)
    images = []

    for page_index in range(min(len(doc), MAX_PDF_PAGES)):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        images.append(pix.tobytes("png"))

    return images


def read_image(path):
    return path.read_bytes()


def describe_file(path):
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        page_images = render_pdf_pages(path)
        descriptions = []

        for i, image_bytes in enumerate(page_images, start=1):
            description = describe_image(image_bytes, f"{path.name} page {i}")
            descriptions.append(f"## Page {i}\n{description}")

        return "\n\n".join(descriptions)

    if suffix in {".png", ".jpg", ".jpeg"}:
        return describe_image(read_image(path), path.name)

    raise ValueError(f"Unsupported file type: {suffix}")


def reindex_updated_files(updated_files):
    for filename in updated_files:
        clean_name = filename.replace("wiki/", "").replace("wiki\\", "")
        path = Path("wiki") / clean_name

        if path.exists():
            index_note(path.read_text(encoding="utf-8"), clean_name)


def import_file(path, category, knowledge_type):
    print(f"\nImporting: {path.name}")

    extracted = describe_file(path)

    if not extracted.strip():
        raise ValueError("No content extracted")

    raw_path = save_raw_source(path.stem, extracted, "ainote_pdf")

    summary = summarize_for_wiki(extracted)

    header = f"""
---
category: {category}
source_device: iflytek_ainote
source_file: {path.name}
source_type: handwritten_pdf
---

{summary}
"""

    updated_files = integrate_into_wiki(header, path.stem, knowledge_type)
    reindex_updated_files(updated_files)

    target = PROCESSED / path.name
    path.replace(target)

    print(f"Saved raw source: {raw_path}")
    print(f"Updated wiki files: {updated_files}")
    print(f"Moved to: {target}")


def choose_category():
    categories = [
        "personal",
        "family",
        "professional",
        "confidential",
        "health",
        "finance",
        "learning",
        "ideas",
    ]

    print("\nCategory:")
    for i, category in enumerate(categories, start=1):
        print(f"{i}. {category}")

    choice = input("Choose category [default professional]: ").strip()

    if not choice:
        return "professional"

    return categories[int(choice) - 1]


def choose_knowledge_type():
    types = [
        "Source only",
        "Idea",
        "Concept",
        "Framework",
        "Project",
        "Client",
        "Decision",
        "Pattern",
        "Profile",
        "Action",
    ]

    print("\nKnowledge type:")
    for i, item in enumerate(types, start=1):
        print(f"{i}. {item}")

    choice = input("Choose type [default Source only]: ").strip()

    if not choice:
        return "Source only"

    return types[int(choice) - 1]


def main():
    ensure_folders()

    files = [
        path
        for path in RAW.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED
    ]

    if not files:
        print(f"No supported files found in {RAW}")
        return

    print("\nFound files:")
    for i, path in enumerate(files, start=1):
        print(f"{i}. {path.name}")

    selected = input("\nImport all files? [y/N]: ").strip().lower()

    if selected != "y":
        print("Cancelled.")
        return

    category = choose_category()
    knowledge_type = choose_knowledge_type()

    for path in files:
        try:
            import_file(path, category, knowledge_type)
        except Exception as e:
            print(f"Failed to import {path.name}: {e}")
            path.replace(FAILED / path.name)


if __name__ == "__main__":
    main()