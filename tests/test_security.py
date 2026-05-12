# tests/test_security.py
import pytest

from giuman_assistant.security import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8501",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "file:///etc/passwd",
        "ftp://example.com",
    ],
)
def test_validate_url_blocks_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_validate_url_allows_public_https():
    validate_url("https://example.com")
