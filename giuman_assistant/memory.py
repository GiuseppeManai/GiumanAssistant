import hashlib
import re

import chromadb

client = chromadb.PersistentClient(path="./db")
collection = client.get_or_create_collection("notes")
MAX_RETRIEVAL_DISTANCE = 1.30
EXCLUDED_RETRIEVAL_SOURCES = {"log.md", "index.md", "lint_ignore.md", "wiki/log.md", "wiki/index.md"}


def make_id(source, chunk_index):
    raw = f"{source}_{chunk_index}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def infer_knowledge_type(source):
    name = source.lower()

    if "ideas" in name:
        return "idea"
    if "profile" in name:
        return "profile"
    if "project" in name:
        return "project"
    if "framework" in name:
        return "framework"
    if "decision" in name:
        return "decision"

    return "note"


def chunk_text(text, chunk_size=1200, overlap=200):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def delete_source(source):
    existing = collection.get(where={"source": source})
    ids = existing.get("ids", [])
    if ids:
        collection.delete(ids=ids)


def index_note(text, source, knowledge_type=None, metadata=None):
    delete_source(source)

    chunks = chunk_text(text)
    knowledge_type = knowledge_type or infer_knowledge_type(source)
    metadata = metadata or {}

    for i, chunk in enumerate(chunks):
        chunk_metadata = {
            "source": source,
            "source_path": metadata.get("source_path", source),
            "source_filename": metadata.get("source_filename", source),
            "wiki_page_filename": metadata.get("wiki_page_filename", source),
            "chunk": i,
            "chunk_id": make_id(source, i),
            "knowledge_type": knowledge_type,
        }
        optional_fields = [
            "original_filename",
            "detected_title",
            "category",
            "imported_at",
        ]
        for field in optional_fields:
            if metadata.get(field):
                chunk_metadata[field] = metadata[field]

        collection.add(
            documents=[chunk],
            metadatas=[chunk_metadata],
            ids=[make_id(source, i)],
        )


def build_filter(source=None, knowledge_type=None):
    filters = []

    if source:
        filters.append({"source": source})

    if knowledge_type:
        filters.append({"knowledge_type": knowledge_type})

    if not filters:
        return None

    if len(filters) == 1:
        return filters[0]

    return {"$and": filters}


def tokenize_query(text):
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3]


def is_retrieval_source_allowed(metadata):
    source = str(metadata.get("source", ""))
    source_path = str(metadata.get("source_path", ""))
    wiki_page = str(metadata.get("wiki_page_filename", ""))
    candidates = {source, source_path, wiki_page}
    return not any(candidate in EXCLUDED_RETRIEVAL_SOURCES for candidate in candidates)


def lexical_match_score(query, metadata, document):
    haystacks = [
        str(metadata.get("source", "")),
        str(metadata.get("source_path", "")),
        str(metadata.get("source_filename", "")),
        str(metadata.get("wiki_page_filename", "")),
        str(metadata.get("original_filename", "")),
        str(metadata.get("detected_title", "")),
        document or "",
    ]
    combined = "\n".join(haystacks).lower()
    score = 0

    for token in tokenize_query(query):
        if token in combined:
            score += 1

    return score


def find_lexical_candidates(query, limit):
    results = collection.get()
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    candidates = []

    for i, document in enumerate(documents):
        metadata = dict(metadatas[i] or {}) if i < len(metadatas) else {}
        if not is_retrieval_source_allowed(metadata):
            continue
        score = lexical_match_score(query, metadata, document)
        if score <= 0:
            continue

        metadata["lexical_score"] = score
        metadata.setdefault("distance", 0.0)
        candidates.append((document, metadata))

    candidates.sort(
        key=lambda item: (
            -item[1].get("lexical_score", 0),
            item[1].get("distance", 0.0),
        )
    )
    return candidates[:limit]


def query_notes(query, n=5, source=None, knowledge_type=None, max_distance=None):
    if not query or not query.strip():
        return [], []

    where = build_filter(source=source, knowledge_type=knowledge_type)

    kwargs = {
        "query_texts": [query],
        "n_results": max(n * 3, 10),
    }

    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    docs = results.get("documents", [[]])[0]
    sources = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    filtered_docs = []
    filtered_sources = []

    for i, doc in enumerate(docs):
        metadata = sources[i] if i < len(sources) else {}
        distance = distances[i] if i < len(distances) else None

        if not is_retrieval_source_allowed(metadata or {}):
            continue

        if max_distance is not None and distance is not None and distance > max_distance:
            continue

        enriched_metadata = dict(metadata or {})
        if distance is not None:
            enriched_metadata["distance"] = distance
        enriched_metadata["lexical_score"] = lexical_match_score(query, enriched_metadata, doc)

        filtered_docs.append(doc)
        filtered_sources.append(enriched_metadata)

    ranked = list(zip(filtered_docs, filtered_sources))
    ranked.extend(find_lexical_candidates(query, n * 2))

    deduped = []
    seen = set()

    for doc, metadata in ranked:
        key = metadata.get("chunk_id") or f"{metadata.get('source')}::{metadata.get('chunk')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append((doc, metadata))

    ranked.sort(
        key=lambda item: (
            -item[1].get("lexical_score", 0),
            item[1].get("distance", float("inf")),
        )
    )
    deduped.sort(
        key=lambda item: (
            -item[1].get("lexical_score", 0),
            item[1].get("distance", float("inf")),
        )
    )
    deduped = deduped[:n]

    return [doc for doc, _ in deduped], [metadata for _, metadata in deduped]
