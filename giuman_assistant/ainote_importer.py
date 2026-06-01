import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

INBOX = Path("AINOTE2_inbox")
RAW = INBOX / "raw"
FAILED = INBOX / "failed"
MANIFEST = INBOX / "manifest.json"

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_PDF_PAGES = 5


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def ensure_folders():
    RAW.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)


def file_fingerprint(path):
    stat = path.stat()
    return {
        "source_file": path.name,
        "sha256": file_hash(path),
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


def load_manifest():
    if not MANIFEST.exists():
        return []

    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(items):
    MANIFEST.write_text(json.dumps(items, indent=2), encoding="utf-8")


def manifest_hashes(manifest):
    return {item.get("sha256") for item in manifest if item.get("sha256")}


def already_processed(path, manifest):
    return file_hash(path) in manifest_hashes(manifest)


def mark_processed(
    path,
    raw_path,
    category="unknown",
    duplicate_status="new",
    imported_at=None,
    detected_title=None,
    wiki_page_filename=None,
):
    manifest = load_manifest()
    fingerprint = file_fingerprint(path)
    imported_at = imported_at or datetime.now().isoformat(timespec="seconds")

    fingerprint.update(
        {
            "imported_at": imported_at,
            "raw_txt_path": raw_path,
            "suggested_category": category,
            "duplicate_status": duplicate_status,
            "detected_title": detected_title,
            "wiki_page_filename": wiki_page_filename,
        }
    )

    manifest.append(fingerprint)
    save_manifest(manifest)


def classify_file(path, processed_hashes):
    suffix = path.suffix.lower()
    info = {
        "name": path.name,
        "path": str(path),
        "suffix": suffix,
        "size": path.stat().st_size,
        "sha256": file_hash(path),
    }

    if suffix not in SUPPORTED:
        return "unsupported", info

    if info["sha256"] in processed_hashes:
        return "already_imported", info

    return "new", info


def validate_inbox():
    result = {
        "new": [],
        "already_imported": [],
        "unsupported": [],
        "message": "",
    }

    manifest = load_manifest()
    processed_hashes = manifest_hashes(manifest)

    if not RAW.exists():
        result["message"] = f"Inbox folder not found: {RAW}"
        return result

    files = sorted((path for path in RAW.iterdir() if path.is_file()), key=lambda p: p.name.lower())

    for path in files:
        status, info = classify_file(path, processed_hashes)
        result[status].append(info)

    result["message"] = (
        f"Found {len(result['new'])} new, "
        f"{len(result['already_imported'])} already imported, "
        f"{len(result['unsupported'])} unsupported file(s)."
    )
    return result


def render_pdf_pages(path):
    import fitz

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
    from giuman_assistant.llm import extract_note_from_image

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        page_images = render_pdf_pages(path)
        descriptions = []

        for i, image_bytes in enumerate(page_images, start=1):
            description = extract_note_from_image(image_bytes, f"{path.name} page {i}")
            descriptions.append(f"## Page {i}\n{description}")

        return "\n\n".join(descriptions)

    if suffix in {".png", ".jpg", ".jpeg"}:
        return extract_note_from_image(read_image(path), path.name)

    raise ValueError(f"Unsupported file type: {suffix}")


def reindex_imported_note(page_path, metadata, knowledge_type):
    from giuman_assistant.memory import index_note

    path = Path(page_path)
    if not path.exists():
        return

    source = metadata.get("source_path", str(path).replace("\\", "/"))
    index_note(
        path.read_text(encoding="utf-8"),
        source,
        knowledge_type=knowledge_type,
        metadata=metadata,
    )


def import_file(path, category, knowledge_type):
    from giuman_assistant.source_store import save_raw_source
    from giuman_assistant.wiki_manager import write_ainote_page

    extracted = describe_file(path)

    if not extracted.strip():
        raise ValueError("No content extracted")

    raw_path = save_raw_source(path.stem, extracted, "ainote_pdf")
    imported_at = datetime.now().isoformat(timespec="seconds")
    page = write_ainote_page(
        extracted_text=extracted,
        source_file=path.name,
        category=category,
        imported_at=imported_at,
        raw_txt_path=raw_path,
        selected_knowledge_type=knowledge_type,
    )
    metadata = {
        "source_path": page["page_path"],
        "source_filename": page["wiki_filename"],
        "wiki_page_filename": page["wiki_filename"],
        "original_filename": path.name,
        "detected_title": page["detected_title"],
        "category": page["category"],
        "imported_at": imported_at,
    }
    reindex_imported_note(page["page_path"], metadata, page["knowledge_type"])
    mark_processed(
        path,
        raw_path,
        category=page["category"],
        imported_at=imported_at,
        detected_title=page["detected_title"],
        wiki_page_filename=page["wiki_filename"],
    )

    return {
        "file": path.name,
        "raw_txt_path": raw_path,
        "updated_files": page["updated_files"],
        "wiki_page": page["page_path"],
        "detected_title": page["detected_title"],
    }


def move_to_failed(path):
    FAILED.mkdir(parents=True, exist_ok=True)
    destination = FAILED / path.name

    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = FAILED / f"{path.stem}_{timestamp}{path.suffix}"

    shutil.move(str(path), str(destination))
    return str(destination)


def import_new_notes(category="professional", knowledge_type="Source only"):
    ensure_folders()

    result = {
        "processed": [],
        "skipped": [],
        "failed": [],
        "message": "",
    }

    validation = validate_inbox()

    for item in validation["already_imported"]:
        result["skipped"].append({**item, "reason": "already_imported"})

    for item in validation["unsupported"]:
        result["skipped"].append({**item, "reason": "unsupported"})

    for item in validation["new"]:
        path = Path(item["path"])

        try:
            result["processed"].append(import_file(path, category, knowledge_type))
        except Exception as exc:
            failed_path = move_to_failed(path)
            result["failed"].append(
                {
                    "file": path.name,
                    "path": str(path),
                    "failed_path": failed_path,
                    "error": str(exc),
                }
            )

    result["message"] = (
        f"Processed {len(result['processed'])}, "
        f"skipped {len(result['skipped'])}, "
        f"failed {len(result['failed'])} file(s)."
    )
    return result


def migrate_legacy_imports():
    from giuman_assistant.wiki_manager import write_ainote_page

    manifest = load_manifest()
    migrated = []

    for item in manifest:
        raw_txt_path = item.get("raw_txt_path")
        source_file = item.get("source_file")
        imported_at = item.get("imported_at")
        category = item.get("suggested_category", "professional")
        wiki_page_filename = item.get("wiki_page_filename")

        if not raw_txt_path or not source_file or not imported_at:
            continue

        raw_path = Path(raw_txt_path)
        if not raw_path.exists():
            continue

        if wiki_page_filename:
            wiki_path = Path("wiki") / wiki_page_filename
            if wiki_path.exists():
                continue

        extracted = raw_path.read_text(encoding="utf-8")
        page = write_ainote_page(
            extracted_text=extracted,
            source_file=source_file,
            category=category,
            imported_at=imported_at,
            raw_txt_path=raw_txt_path,
            selected_knowledge_type="Source only",
        )
        metadata = {
            "source_path": page["page_path"],
            "source_filename": page["wiki_filename"],
            "wiki_page_filename": page["wiki_filename"],
            "original_filename": source_file,
            "detected_title": page["detected_title"],
            "category": page["category"],
            "imported_at": imported_at,
        }
        reindex_imported_note(page["page_path"], metadata, page["knowledge_type"])
        item["wiki_page_filename"] = page["wiki_filename"]
        item["detected_title"] = page["detected_title"]
        migrated.append(page["page_path"])

    if migrated:
        save_manifest(manifest)

    return migrated
