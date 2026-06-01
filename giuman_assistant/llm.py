import base64
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_PROMPT_CHARS = 60_000
MAX_IMAGE_BYTES = 5_000_000
RETRIES = 2
TIMEOUT = 30

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=TIMEOUT)


def load_agent_instructions():
    try:
        with open("AGENTS.md", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def trim_text(text, limit):
    if not text:
        return ""

    if len(text) <= limit:
        return text

    return text[:limit] + "\n\n[TRUNCATED]"


def call_openai(messages):
    last_error = None

    for attempt in range(RETRIES + 1):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
            return res.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < RETRIES:
                time.sleep(1 + attempt)

    return f"OpenAI request failed: {last_error}"


def build_context(docs, sources):
    parts = []

    for i, doc in enumerate(docs):
        if not sources or i >= len(sources):
            continue

        source = sources[i] or {}
        filename = source.get("source")

        if filename:
            parts.append(f"Source: {filename}\n{doc}")

    return "\n\n".join(parts)


def build_personal_context(docs, sources):
    parts = []

    for i, doc in enumerate(docs):
        if not sources or i >= len(sources):
            continue

        source = sources[i] or {}
        filename = source.get("source", "")

        if "personal_profile.md" in filename:
            parts.append(doc)

    return "\n\n".join(parts)


def ask_llm(question, docs, sources):
    agent_instructions = load_agent_instructions()
    personal_context = build_personal_context(docs, sources)
    context = build_context(docs, sources)

    prompt = f"""
{agent_instructions}

You are Giuseppe's twin assistant.

PERSONAL CONTEXT:
{personal_context}

INSTRUCTIONS:
- Think and reason using Giuseppe's decision model and thinking style
- Apply his filters: client relevance, impact, feasibility
- Use challenge mode when solutioning
- Be structured, concise, and practical

SPECIAL RULE:
If the question is about ideas:
- ONLY use ideas.md content
- DO NOT infer or generate ideas from profile, concepts, or strategy pages

---

Context:
{context}

---

Question:
{question}
"""

    prompt = trim_text(prompt, MAX_PROMPT_CHARS)

    return call_openai([{"role": "user", "content": prompt}])


def describe_image(image_bytes, filename):
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return "Image is too large to process."

    encoded = base64.b64encode(image_bytes).decode("utf-8")

    text = f"""
Describe this image for a personal knowledge base.

Include:
- what is visible
- important text
- diagrams or objects
- why useful later

Filename: {filename}
"""

    return call_openai(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                ],
            }
        ]
    )


def extract_note_from_image(image_bytes, filename):
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    text = f"""
    You are extracting knowledge from a handwritten note captured from iFLYTEK AINOTE.

    TASK:
    Convert the note image into a structured raw text artifact for a personal and professional second brain.

    CRITICAL RULES:
    - Do NOT describe the image.
    - Do NOT say "visible elements" or "description of image".
    - Do NOT summarize before transcribing.
    - Preserve the original handwriting content as much as possible.
    - Preserve headings, bullets, names, subjects, arrows, and grouping.
    - If a word is unclear, write [?] next to it.
    - Do not invent missing content.

    CATEGORY RULES:
    - family = spouse, children, school, home, parenting, relatives
    - professional = work, clients, strategy, meetings, delivery, leadership
    - learning = user's own study notes, courses, books, concepts
    - ideas = raw ideas, startup ideas, product ideas, experiments
    - finance = money, investment, budgeting, expenses
    - health = health, food, training, medical, sleep
    - personal = personal reflections, habits, values, identity
    - admin = logistics, errands, accounts, subscriptions, planning

    FILE:
    {filename}

    OUTPUT FORMAT:

    METADATA
    - detected_title:
    - category: family | professional | learning | ideas | finance | health | personal | admin
    - category_confidence: low | medium | high
    - knowledge_type: meeting | idea | decision | project | profile | framework | concept | action | reference | other
    - likely_note_type:
    - date_if_visible:
    - possible_update_of:
    - source_device: iflytek_ainote
    - source_file: {filename}
    - uncertainty_level: low | medium | high

    ENTITIES
    - people:
    - organizations:
    - places:
    - clients:
    - projects:
    - other:

    TOPICS
    - <short snake_case topics, e.g. school_performance, physical_ai, airport_operations>

    EXACT_TRANSCRIPTION
    <transcribe the note as accurately as possible>

    STRUCTURED_CAPTURE
    <organize the content into sections, but do not add new ideas>

    WIKI_SUMMARY
    <specific distilled summary suitable for later integration into the wiki.
    Include the main insight, recurring pattern, and concrete actions if present.
    Avoid generic phrases.>

    ACTIONS
    - <explicit actions only>
    - if none, write: none

    UNCERTAIN_TEXT
    - <only actually uncertain words or phrases>
    - if none, write: none
    """

    return call_openai(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                ],
            }
        ]
    )


def summarize_for_wiki(text):
    agent_instructions = load_agent_instructions()

    prompt = f"""
{agent_instructions}

You are preparing clean input for a knowledge wiki.

TASK:
- Extract only high-value information
- Remove noise (navigation, ads, repetition)
- Convert into structured bullet points

OUTPUT FORMAT:

## Key Points
- ...

## Concepts
- ...

## Applications (if any)
- ...

## Notes
- ...

CONTENT:
{trim_text(text, MAX_PROMPT_CHARS)}
"""

    prompt = trim_text(prompt, MAX_PROMPT_CHARS)

    return call_openai([{"role": "user", "content": prompt}])
