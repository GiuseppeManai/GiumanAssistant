from datetime import datetime
from pathlib import Path
import re

from giuman_assistant.llm import ask_llm

WIKI_DIR = Path("wiki")
AINOTE_SECTIONS = [
    "METADATA",
    "ENTITIES",
    "TOPICS",
    "EXACT_TRANSCRIPTION",
    "STRUCTURED_CAPTURE",
    "WIKI_SUMMARY",
    "ACTIONS",
    "UNCERTAIN_TEXT",
]


def safe_wiki_path(wiki_dir, filename):
    root = Path(wiki_dir).resolve()
    path = (root / filename).resolve()

    if path == root or root not in path.parents:
        raise ValueError(f"Unsafe wiki path: {filename}")

    return path


def normalize_wiki_filename(filename):
    filename = filename.replace("wiki/", "").replace("wiki\\", "")
    return filename.strip()


def read_wiki():
    pages = {}

    for path in WIKI_DIR.glob("*.md"):
        pages[path.name] = path.read_text(encoding="utf-8")

    return pages


def write_wiki(updates):
    for filename, content in updates.items():
        filename = normalize_wiki_filename(filename)
        path = safe_wiki_path(WIKI_DIR, filename)
        path.write_text(content, encoding="utf-8")


def parse_llm_output(output):
    files = {}
    current_file = None
    buffer = []

    for line in output.splitlines():
        if line.startswith("===FILE:"):
            if current_file:
                files[current_file] = "\n".join(buffer).strip()
            current_file = line.replace("===FILE:", "").replace("===", "").strip()
            buffer = []
        else:
            buffer.append(line)

    if current_file:
        files[current_file] = "\n".join(buffer).strip()

    return files


def slugify_note_name(value):
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "ainote_import"


def parse_structured_note_sections(text):
    sections = {name: "" for name in AINOTE_SECTIONS}
    current_section = None
    buffer = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if line in AINOTE_SECTIONS:
            if current_section:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = line
            buffer = []
            continue

        if current_section:
            buffer.append(raw_line.rstrip())

    if current_section:
        sections[current_section] = "\n".join(buffer).strip()

    return sections


def parse_metadata_block(text):
    data = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue

        key, _, value = stripped[2:].partition(":")
        if not _:
            continue

        data[key.strip()] = value.strip()

    return data


def first_nonempty_line(text):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def summary_bullets(text):
    bullets = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped)
        elif stripped:
            bullets.append(f"- {stripped}")

    return bullets or ["- Imported AINOTE2 note indexed as a source-specific wiki page."]


def update_index_for_page(page_filename, page_title, summary_text):
    index_path = safe_wiki_path(WIKI_DIR, "index.md")

    if index_path.exists():
        content = index_path.read_text(encoding="utf-8").rstrip()
    else:
        content = "# Wiki Index"

    summary_line = first_nonempty_line(summary_text).replace("\n", " ").strip("- ").strip()
    if not summary_line:
        summary_line = "Imported AINOTE2 note."

    entry = f"- [{page_title}]({page_filename}): {summary_line}"
    if entry not in content:
        content = f"{content}\n{entry}".strip() + "\n"
        index_path.write_text(content, encoding="utf-8")


def append_log_for_page(source_name, page_filename, summary_text, imported_at):
    log_path = safe_wiki_path(WIKI_DIR, "log.md")
    existing = log_path.read_text(encoding="utf-8").rstrip() if log_path.exists() else ""
    date_label = imported_at.split("T", maxsplit=1)[0]
    if source_name in existing and page_filename in existing:
        return
    summary_lines = "\n".join(summary_bullets(summary_text))
    entry = (
        f"## {date_label} - {source_name}\n\n"
        f"- Source: {source_name}\n"
        f"- Summary:\n"
        f"{summary_lines}\n"
        f"- Pages updated:\n"
        f"  - {page_filename}\n"
        f"- Notes:\n"
        f"  - Imported from AINOTE2.\n"
    )

    if existing:
        log_text = f"{existing}\n\n{entry}\n"
    else:
        log_text = f"{entry}\n"

    log_path.write_text(log_text, encoding="utf-8")


def build_ainote_page(
    extracted_text,
    source_file,
    category,
    imported_at,
    raw_txt_path,
    selected_knowledge_type,
):
    sections = parse_structured_note_sections(extracted_text)
    metadata = parse_metadata_block(sections["METADATA"])
    detected_title = metadata.get("detected_title") or Path(source_file).stem.replace("_", " ").strip()
    detected_title = detected_title.strip() or Path(source_file).stem
    wiki_filename = f"{slugify_note_name(detected_title)}.md"
    page_title = detected_title
    note_category = metadata.get("category") or category
    note_knowledge_type = metadata.get("knowledge_type") or selected_knowledge_type
    page_path = f"wiki/{wiki_filename}"

    metadata_lines = [
        f"- original_filename: {source_file}",
        f"- detected_title: {detected_title}",
        f"- wiki_page_filename: {wiki_filename}",
        f"- wiki_page_path: {page_path}",
        f"- category: {note_category}",
        f"- imported_at: {imported_at}",
        f"- selected_knowledge_type: {selected_knowledge_type}",
        f"- detected_knowledge_type: {note_knowledge_type}",
        f"- raw_txt_path: {raw_txt_path}",
    ]

    passthrough_fields = [
        "category_confidence",
        "likely_note_type",
        "date_if_visible",
        "possible_update_of",
        "source_device",
        "source_file",
        "uncertainty_level",
    ]
    for field in passthrough_fields:
        if metadata.get(field):
            metadata_lines.append(f"- {field}: {metadata[field]}")

    page_lines = [f"# {page_title}"]
    ordered_sections = {
        "METADATA": "\n".join(metadata_lines),
        "ENTITIES": sections["ENTITIES"] or "- none",
        "TOPICS": sections["TOPICS"] or "- none",
        "EXACT_TRANSCRIPTION": sections["EXACT_TRANSCRIPTION"] or "No transcription extracted.",
        "STRUCTURED_CAPTURE": sections["STRUCTURED_CAPTURE"] or "No structured capture extracted.",
        "WIKI_SUMMARY": sections["WIKI_SUMMARY"] or "- none",
        "ACTIONS": sections["ACTIONS"] or "- none",
        "UNCERTAIN_TEXT": sections["UNCERTAIN_TEXT"] or "- none",
    }

    for section_name, section_content in ordered_sections.items():
        page_lines.append(f"## {section_name}")
        page_lines.append(section_content.strip())

    page_content = "\n\n".join(page_lines).strip() + "\n"
    return {
        "page_title": page_title,
        "wiki_filename": wiki_filename,
        "page_path": page_path,
        "page_content": page_content,
        "summary_text": sections["WIKI_SUMMARY"],
        "detected_title": detected_title,
        "category": note_category,
        "knowledge_type": note_knowledge_type,
    }


def write_ainote_page(
    extracted_text,
    source_file,
    category,
    imported_at,
    raw_txt_path,
    selected_knowledge_type,
):
    page = build_ainote_page(
        extracted_text=extracted_text,
        source_file=source_file,
        category=category,
        imported_at=imported_at,
        raw_txt_path=raw_txt_path,
        selected_knowledge_type=selected_knowledge_type,
    )
    page_path = safe_wiki_path(WIKI_DIR, page["wiki_filename"])
    page_path.write_text(page["page_content"], encoding="utf-8")
    update_index_for_page(page["wiki_filename"], page["page_title"], page["summary_text"])
    append_log_for_page(source_file, page["wiki_filename"], page["summary_text"], imported_at)
    return {
        **page,
        "updated_files": [
            page["page_path"],
            "wiki/index.md",
            "wiki/log.md",
        ],
    }


def integrate_into_wiki(source_text, source_name, knowledge_type):
    current_date = datetime.now().strftime("%Y-%m-%d")
    wiki_pages = read_wiki()

    combined_wiki = "\n\n".join([f"# FILE: {k}\n{v}" for k, v in wiki_pages.items()])

    prompt = f"""
You maintain a high-quality personal knowledge wiki in markdown.

GOALS:
- Create clean, structured, non-redundant knowledge
- Merge new information into existing pages intelligently
- Avoid repetition across sections

KNOWLEDGE TYPE: {knowledge_type}

You MUST treat the content differently based on type:

- source → summarize and integrate into relevant pages
- idea → store as idea with status=raw, do NOT force into concepts
- concept → create or refine a concept page
- framework → structure as reusable model
- project → create/update project page
- decision → record rationale and outcome
- pattern → extract reusable insight
- profile → update personal_profile.md
- action → create actionable item

Respect the knowledge type strictly.

PAGE STRUCTURE (enforce when relevant):

# Title

## Overview
Short explanation of the concept

## Key Concepts
- bullet points
- definitions
- core ideas
- key messages

## Applications
- real-world use cases

## Architecture / Components (if relevant)
- systems, layers, building blocks

## Challenges / Limitations
- constraints, risks, tradeoffs

## Notes
- additional insights or emerging ideas

RULES:
- Do NOT duplicate content
- Merge with existing sections instead of appending blindly
- Prefer bullets over long paragraphs
- Keep content concise but high signal and high density
- Remove low-value or noisy information
- avoid jargon and use appropriate english
- Do NOT repeat the same idea across sections
- If information already exists, refine or merge it instead of adding new bullets
- Keep each section under 8–10 bullets
- Prefer specific examples over generic statements
- You MUST NOT use markdown code fences (```)
- For type=idea:
    - DO NOT merge into existing pages  
    - Create or update ideas.md 
    - Preserve raw content


 Append a new entry to log.md using THIS EXACT FORMAT:

## {current_date} — {source_name}

- Source: {source_name}
- Summary:
  - bullet point 1
  - bullet point 2 (optional)
- Pages updated:
  - file1.md
  - file2.md
- Notes:
  - optional

STRICT RULES:
- You MUST preserve all existing content exactly
- You MUST append only at the end
- You MUST follow the format EXACTLY
- You MUST include "##" before the date
- You MUST use "-" for all bullet points
- You MUST NOT write paragraphs in Summary
- If format is not followed, the output is INVALID

SOURCE NAME:
{source_name}

SOURCE CONTENT:
{source_text}

CURRENT WIKI:
{combined_wiki}

OUTPUT FORMAT — MANDATORY:

You MUST return one or more complete files using this exact format.

For every file you update, use:

===FILE: wiki/<filename>.md===
<full updated file content>

You MUST include:
===FILE: wiki/index.md===
<full updated index.md content>

You MUST include:
===FILE: wiki/log.md===
<full updated log.md content>

STRICT OUTPUT RULES:
- Do NOT return text outside ===FILE blocks
- Do NOT return only a log entry
- Do NOT skip index.md or log.md
- Do NOT use code fences
- If you do not follow this format, the output is INVALID
"""

    response = ask_llm(prompt, [], [])
    print("\n===== LLM RAW OUTPUT =====\n")
    print(response)
    print("\n==========================\n")
    updates = parse_llm_output(response)

    if not updates:
        print("⚠️ No files parsed from LLM output")

    print("\n===== PARSED FILES =====")
    for k in updates.keys():
        print("->", k)
    print("========================\n")

    write_wiki(updates)

    return list(updates.keys())
