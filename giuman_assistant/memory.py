import hashlib

import chromadb

client = chromadb.PersistentClient(path="./db")
collection = client.get_or_create_collection("notes")


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


def index_note(text, source, knowledge_type=None):
    delete_source(source)

    chunks = chunk_text(text)
    knowledge_type = knowledge_type or infer_knowledge_type(source)

    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            metadatas=[
                {
                    "source": source,
                    "chunk": i,
                    "knowledge_type": knowledge_type,
                }
            ],
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


def query_notes(query, n=5, source=None, knowledge_type=None):
    if not query or not query.strip():
        return [], []

    where = build_filter(source=source, knowledge_type=knowledge_type)

    kwargs = {
        "query_texts": [query],
        "n_results": n,
    }

    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    docs = results.get("documents", [[]])[0]
    sources = results.get("metadatas", [[]])[0]

    return docs, sources
