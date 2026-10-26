"""
Unit tests for search tokenization, matching, and ranking logic.
"""

from __future__ import annotations

from infonet_api.routers.people import _search_matches


def test_token_matching():
    """All tokens must be substrings of the lowercased name."""
    name = "dr. r. sumathi"
    # Exact match
    matches, contiguous = _search_matches(name, "Sumathi")
    assert matches is True
    assert contiguous is True

    # Tokens with punctuation/titles
    matches, contiguous = _search_matches(name, "Dr Sumathi")
    assert matches is True

    # Partial token not in name
    matches, contiguous = _search_matches(name, "Sumathi Ramesh")
    assert matches is False


def test_contiguous_ranking():
    """Contiguous match is flagged so it ranks ahead of separate token matches."""
    name_contiguous = "computer science engineering laboratory"
    name_non_contiguous = "engineering department of computer science"

    m1, c1 = _search_matches(name_contiguous, "computer science")
    assert m1 is True
    assert c1 is True

    m2, c2 = _search_matches(name_non_contiguous, "computer science")
    assert m2 is True
    assert c2 is True  # "computer science" is contiguous here too

    # Now a multi-token query that is non-contiguous in the target
    m3, c3 = _search_matches("computer network laboratory of science", "computer science")
    assert m3 is True
    assert c3 is False  # "computer" and "science" match, but not contiguously "computer science"
