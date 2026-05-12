# GiuMan Assistant

A local-first personal AI assistant for structured knowledge, strategic thinking, and idea development.
Built experimentally with coding agents and iterative refinement.
The system prioritizes explicit retrieval, inspectable memory, and minimal orchestration over autonomous agent complexity.

Inspired by:
- Vivian Balakrishnan's assistant gist
- Andrej Karpathy's note-taking / memory system concepts


References:
- https://gist.github.com/VivianBalakrishnan/a7d4eec3833baee4971a0ee54b08f322
- https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The system combines:
- Streamlit UI
- OpenAI LLM reasoning
- ChromaDB semantic memory
- Markdown wiki as source of truth
- Raspberry Pi deployment support

## Purpose

GiuMan Assistant is designed to act as a personal thinking partner. It helps capture knowledge, retrieve context, structure ideas, and support strategic reasoning.

## Non-Goals

- Autonomous multi-agent orchestration
- Hidden memory systems
- Framework-heavy abstractions
- Cloud-dependent architecture

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
Copy `.env.example` to `.env`
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
python -m scripts.reindex_wiki
streamlit run run.py
```

## Reset Memory Index

```powershell
Remove-Item -Recurse -Force db
python -m scripts.reindex_wiki
```

## Design Principles

- Wiki-first memory
- Retrieval controls truth
- LLM reasons over provided context
- Keep code small, explicit, and hackable
- Prefer practical clarity over framework complexity

## Core Invariants

- Wiki is the source of truth
- Retrieval controls context
- LLMs do not decide retrieval scope
- All memory remains inspectable
- Prompts remain plain text
- No hidden orchestration layers
- Metadata filters retrieval

## Security Model

- Local-first architecture
- URL validation and SSRF protection
- Path traversal protection
- Input size limits
- Explicit retrieval filtering
- Secrets stored only in `.env`
