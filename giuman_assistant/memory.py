import hashlib

import chromadb

client = chromadb.PersistentClient(path="./db")
collection = client.get_or_create_collection("notes")


def make_id(source, chunk_index):
    raw = f"{source}_{chunk_index}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


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


def index_note(text, source):
    delete_source(source)

    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk], metadatas=[{"source": source, "chunk": i}], ids=[make_id(source, i)]
        )


def query_notes(query, n=5):
    if not query or not query.strip():
        return [], []

    results = collection.query(query_texts=[query], n_results=n)
    docs = results.get("documents", [[]])[0]
    sources = results.get("metadatas", [[]])[0]
    return docs, sources
