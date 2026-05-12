from giuman_assistant.memory import query_notes


def test_empty_query_returns_no_context():
    docs, sources = query_notes("")

    assert docs == []
    assert sources == []


def test_query_notes_returns_documents_and_metadata():
    docs, sources = query_notes("test query")

    assert isinstance(docs, list)
    assert isinstance(sources, list)


def test_retrieval_returns_source_metadata():
    docs, sources = query_notes("test query")

    if not sources:
        return

    assert "source" in sources[0]
