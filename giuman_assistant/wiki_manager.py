import os
from datetime import datetime

from giuman_assistant.llm import ask_llm

WIKI_DIR = "wiki"


def read_wiki():
    pages = {}
    for filename in os.listdir(WIKI_DIR):
        if filename.endswith(".md"):
            path = os.path.join(WIKI_DIR, filename)
            with open(path, encoding="utf-8") as f:
                pages[filename] = f.read()
    return pages


def write_wiki(updates):
    for filename, content in updates.items():
        # FIX: remove leading "wiki/" if present
        filename = filename.replace("wiki/", "").replace("wiki\\", "")

        path = os.path.join(WIKI_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


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
