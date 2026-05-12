# tests/test_wiki_manager.py
import pytest

from giuman_assistant.wiki_manager import safe_wiki_path


def test_safe_wiki_path_allows_normal_page(tmp_path):
    path = safe_wiki_path(tmp_path, "ideas.md")
    assert path == tmp_path / "ideas.md"


@pytest.mark.parametrize("name", ["../secrets.env", "/tmp/x.md", "a/../../x.md"])
def test_safe_wiki_path_blocks_traversal(tmp_path, name):
    with pytest.raises(ValueError):
        safe_wiki_path(tmp_path, name)
