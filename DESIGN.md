# Design Notes

## Philosophy

GiuMan Assistant is designed as a small, local-first reasoning system.

The system prioritizes:
- curated knowledge over raw retrieval
- explicit control over hidden abstractions
- simple operational flows
- human-readable memory

The architecture intentionally avoids large agent frameworks and unnecessary orchestration layers.

## Core Principle

Retrieval controls truth.

The LLM should reason over selected context, not decide truth autonomously.

## Knowledge Model

The system uses a wiki-first model:

```text
wiki/ = curated memory
raw/  = source ingestion
db/   = semantic retrieval index
```

The markdown wiki acts as the long-term source of truth.

## System Components

### Streamlit
UI and orchestration layer.

### ChromaDB
Semantic retrieval memory.

### OpenAI LLM
Reasoning and synthesis engine.

### AGENTS.md
Behavioral and architectural instructions for the assistant.

## Retrieval Strategy

The application layer decides:
- what knowledge is retrieved
- which sources are filtered
- how context is assembled

The LLM receives controlled context.

## Why Markdown

Markdown provides:
- portability
- inspectability
- versionability
- low operational complexity

The knowledge base should remain understandable without specialized tooling.

## Non-Goals

The system intentionally avoids:
- opaque autonomous agents
- excessive framework abstractions
- hidden workflows
- uncontrolled self-modification

## Future Directions

Potential future improvements:
- metadata-driven retrieval
- local embeddings
- local models
- knowledge evolution tracking
- graph relationships
- reasoning memory