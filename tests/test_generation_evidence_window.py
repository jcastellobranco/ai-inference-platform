"""Regression: citations cannot reference evidence omitted from model context."""
import pytest
from app.generation import GroundingError, validate_citations


def test_citation_rejects_out_of_context_index():
    with pytest.raises(GroundingError):
        validate_citations("Claim [6]", 5)


def test_citation_accepts_last_visible_index():
    assert validate_citations("Claim [5]", 5) == [5]
