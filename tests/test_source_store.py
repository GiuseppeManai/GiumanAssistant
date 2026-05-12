from giuman_assistant.source_store import safe_filename, trim_content


def test_safe_filename_removes_unsafe_characters():
    assert safe_filename("../My Source!!") == "my_source"


def test_safe_filename_has_fallback():
    assert safe_filename("!!!") == "source"


def test_trim_content_limits_size():
    text = "a" * 101
    trimmed = trim_content(text, limit=100)

    assert len(trimmed) > 100
    assert "[TRUNCATED]" in trimmed
