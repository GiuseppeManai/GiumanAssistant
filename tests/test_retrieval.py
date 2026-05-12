from giuman_assistant.memory import build_filter, infer_knowledge_type, query_notes


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


def test_infer_knowledge_type_from_source():
    assert infer_knowledge_type("ideas.md") == "idea"
    assert infer_knowledge_type("personal_profile.md") == "profile"
    assert infer_knowledge_type("client_project.md") == "project"
    assert infer_knowledge_type("ai_framework.md") == "framework"
    assert infer_knowledge_type("random.md") == "note"


def test_build_filter_source_only():
    assert build_filter(source="ideas.md") == {"source": "ideas.md"}


def test_build_filter_knowledge_type_only():
    assert build_filter(knowledge_type="idea") == {"knowledge_type": "idea"}


def test_build_filter_source_and_knowledge_type():
    assert build_filter(source="ideas.md", knowledge_type="idea") == {
        "$and": [{"source": "ideas.md"}, {"knowledge_type": "idea"}]
    }
