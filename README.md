# GiuMan Assistant

A local-first personal AI assistant for structured knowledge, strategic thinking, and idea development.

The system combines:
- Streamlit UI
- OpenAI LLM reasoning
- ChromaDB semantic memory
- Markdown wiki as source of truth
- Raspberry Pi deployment support

## Purpose

GiuMan Assistant is designed to act as a personal thinking partner. It helps capture knowledge, retrieve context, structure ideas, and support strategic reasoning.

## Architecture

```text
User
 ↓
Streamlit UI
 ↓
Retrieval / routing
 ↓
ChromaDB + wiki/
 ↓
LLM
 ↓
Styled answer
```

## Folder Model

```text
wiki/         curated knowledge
raw/          raw ingested sources
db/           local ChromaDB index
AGENTS.md     assistant behavior instructions
.env          local secrets, not committed
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
OPENAI_API_KEY=your_key_here
```

## Run

```bash
python reindex_wiki.py
streamlit run app.py
```

## Reset Memory Index

```powershell
Remove-Item -Recurse -Force db
python reindex_wiki.py
```

## Design Principles

- Wiki-first memory
- Retrieval controls truth
- LLM reasons over provided context
- Keep code small, explicit, and hackable
- Prefer practical clarity over framework complexity