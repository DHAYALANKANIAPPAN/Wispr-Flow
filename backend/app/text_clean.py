"""Speech-to-text explanation cleaner and normalizer.

Purpose:
    Normalizes student explanations captured from speech (e.g. Wispr Flow) or typing.
    Strips verbal filler words ('um', 'uh', 'like', 'so basically', 'you know'),
    collapses excessive whitespace, and calculates word count while preserving raw text,
    line breaks, and physical nomenclature.

Status:
    Active, Phase 2 implementation.

Fail-Closed Behavior:
    - If raw input is None or empty, returns empty clean string and word count 0.
    - Never auto-corrects scientific terminology or mathematical expressions.
    - Preserves input without truncation up to any arbitrary length.
"""

import re
from typing import Dict, Any

# Filler phrases and words to filter from dictated audio
# Matches whole words/phrases case-insensitively with optional trailing comma/period
FILLER_PATTERN = re.compile(
    r"\b(so\s+basically|you\s+know|um+|uh+|like)[,.]?\b",
    flags=re.IGNORECASE,
)


def normalize_explanation(raw: str) -> Dict[str, Any]:
    """Normalize a student explanation by stripping speech fillers and collapsing whitespace.

    Args:
        raw: Raw transcribed or typed explanation string.

    Returns:
        dict:
            - 'raw': Original unedited input string.
            - 'clean': Normalized text with fillers removed and whitespace collapsed.
            - 'word_count': Total word count of the cleaned text.
    """
    if raw is None or not isinstance(raw, str):
        raw = ""

    if not raw.strip():
        return {
            "raw": raw,
            "clean": "",
            "word_count": 0,
        }

    # Process line-by-line to preserve user paragraph structure / line breaks
    cleaned_lines = []
    for line in raw.split("\n"):
        # Strip fillers
        line_no_fillers = FILLER_PATTERN.sub(" ", line)
        # Collapse multiple internal spaces and strip stray leading/trailing punctuation left from fillers
        line_collapsed = re.sub(r"[ \t]+", " ", line_no_fillers).strip()
        line_collapsed = re.sub(r"^[,\s]+", "", line_collapsed).strip()
        cleaned_lines.append(line_collapsed)

    # Reconstruct lines and strip excessive blank leading/trailing lines
    clean_text = "\n".join(cleaned_lines).strip()

    # Calculate word count based on whitespace separation
    words = clean_text.split()
    word_count = len(words)

    return {
        "raw": raw,
        "clean": clean_text,
        "word_count": word_count,
    }
