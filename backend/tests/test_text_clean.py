"""Tests for explanation normalization and speech filler stripping.

Purpose:
    Validates filler removal ('um', 'uh', 'like', 'so basically', 'you know'),
    preservation of raw text, word count calculation, whitespace collapse,
    and handling of extreme lengths and lack of punctuation.
"""

from backend.app.text_clean import normalize_explanation


def test_filler_removal_and_whitespace_collapse():
    """Verify common speech fillers are removed and whitespace collapsed."""
    raw = "Um, so basically the current is uh like 5 Amps because you know V equals IR"
    result = normalize_explanation(raw)

    assert result["raw"] == raw
    assert "um" not in result["clean"].lower()
    assert "so basically" not in result["clean"].lower()
    assert "uh" not in result["clean"].lower()
    assert "you know" not in result["clean"].lower()
    assert result["clean"] == "the current is 5 Amps because V equals IR"
    assert result["word_count"] == 9


def test_empty_and_whitespace_only_string():
    """Empty string or pure whitespace must yield empty clean string and word count 0."""
    empty_res = normalize_explanation("")
    assert empty_res["raw"] == ""
    assert empty_res["clean"] == ""
    assert empty_res["word_count"] == 0

    space_res = normalize_explanation("   \n\t  ")
    assert space_res["clean"] == ""
    assert space_res["word_count"] == 0


def test_long_input_not_truncated():
    """Verify that a 2,000+ character explanation is preserved without truncation."""
    sentence = "Ohm's law relates potential difference and resistance in an electrical circuit. "
    raw = sentence * 30  # ~2400 characters
    assert len(raw) > 2000

    result = normalize_explanation(raw)
    assert result["raw"] == raw
    assert len(result["clean"]) > 2000
    assert result["word_count"] == 30 * 11


def test_no_punctuation_input():
    """Speech transcription without punctuation is handled gracefully."""
    raw = "current and voltage are directly proportional when resistance is kept constant"
    result = normalize_explanation(raw)

    assert result["clean"] == raw
    assert result["word_count"] == 11


def test_preserves_linebreaks():
    """Paragraphs and explicit line breaks must be retained."""
    raw = "First line explaining current.\nSecond line explaining resistance."
    result = normalize_explanation(raw)

    assert "\n" in result["clean"]
    lines = result["clean"].split("\n")
    assert len(lines) == 2
    assert lines[0] == "First line explaining current."
    assert lines[1] == "Second line explaining resistance."
