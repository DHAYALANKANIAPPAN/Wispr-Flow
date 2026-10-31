"""Learner model and mastery update engine.

Purpose:
    Tracks and updates per-student, per-concept knowledge mastery.
    Implements the core update_mastery update rule, clamps values to [0.0, 1.0],
    tracks consecutive strong performances, and persists updates atomically.

Status:
    Active, Phase 2 implementation.

Fail-Closed Behavior:
    - Rejects non-numeric, None, or NaN values by raising TypeError or ValueError.
    - Clamps out-of-bound evidence scores to [0.0, 1.0].
    - Initial mastery for unseen concepts defaults to config/mastery.json (0.50).
"""

import os
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models import LearnerMastery

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "mastery.json"


def load_mastery_config() -> Dict[str, Any]:
    """Load mastery hyperparameters from config/mastery.json.

    Returns:
        dict: Configuration dictionary with 'alpha' and 'initial_mastery'.
    """
    if not CONFIG_PATH.exists():
        return {"alpha": 0.20, "initial_mastery": 0.50}

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_CONFIG = load_mastery_config()
DEFAULT_ALPHA: float = float(_CONFIG.get("alpha", 0.20))
INITIAL_MASTERY: float = float(_CONFIG.get("initial_mastery", 0.50))


def update_mastery(m_old: float, evidence: float, alpha: float) -> float:
    """Compute updated knowledge mastery using exponential moving evidence weighting.

    Formula:
        m_new = m_old + alpha * (clamped_evidence - m_old)
        Result is strictly clamped to [0.0, 1.0].

    Note:
        This is a prototype formula per system specification, not a validated
        Bayesian Knowledge Tracing (BKT) or Item Response Theory (IRT) estimate.

    Args:
        m_old: Current concept mastery in [0.0, 1.0].
        evidence: Evidence score derived from student answer and reasoning.
        alpha: Learning rate / update weight.

    Returns:
        float: Updated mastery score clamped to [0.0, 1.0].

    Raises:
        TypeError: If any argument is non-numeric.
        ValueError: If any argument is NaN.
    """
    if not isinstance(m_old, (int, float)) or not isinstance(evidence, (int, float)) or not isinstance(alpha, (int, float)):
        raise TypeError("Mastery, evidence, and alpha must be numeric numbers")

    if math.isnan(m_old) or math.isnan(evidence) or math.isnan(alpha):
        raise ValueError("Mastery, evidence, and alpha cannot be NaN")

    # Clamp inputs safely
    clamped_m_old = max(0.0, min(1.0, float(m_old)))
    clamped_evidence = max(0.0, min(1.0, float(evidence)))
    clamped_alpha = max(0.0, min(1.0, float(alpha)))

    if clamped_alpha == 0.0:
        return clamped_m_old

    m_new = clamped_m_old + clamped_alpha * (clamped_evidence - clamped_m_old)
    # Clamp and round to 4 decimal places for numerical stability
    return round(max(0.0, min(1.0, m_new)), 4)


def get_or_create_mastery(
    db: Session,
    student_id: str,
    concept_id: str,
    initial_mastery: float = INITIAL_MASTERY,
) -> LearnerMastery:
    """Retrieve existing learner mastery or initialize record for unseen concept.

    Args:
        db: Database session.
        student_id: Student identifier.
        concept_id: Concept identifier.
        initial_mastery: Default starting mastery score.

    Returns:
        LearnerMastery: Existing or newly staged database model.
    """
    record = (
        db.query(LearnerMastery)
        .filter_by(student_id=student_id, concept_id=concept_id)
        .first()
    )
    if not record:
        record = LearnerMastery(
            student_id=student_id,
            concept_id=concept_id,
            mastery=initial_mastery,
            consecutive_strong=0,
            attempts_count=0,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(record)
    return record


def apply_mastery_update(
    db: Session,
    student_id: str,
    concept_id: str,
    evidence: float,
    alpha: Optional[float] = None,
) -> LearnerMastery:
    """Update learner mastery and consecutive strong count based on new attempt evidence.

    Args:
        db: Database session.
        student_id: Target student identifier.
        concept_id: Concept being evaluated.
        evidence: Evidence score for the attempt.
        alpha: Optional override for update weight.

    Returns:
        LearnerMastery: Updated record.
    """
    effective_alpha = DEFAULT_ALPHA if alpha is None else alpha
    record = get_or_create_mastery(db, student_id, concept_id)

    new_mastery = update_mastery(
        m_old=record.mastery,
        evidence=evidence,
        alpha=effective_alpha,
    )

    record.mastery = new_mastery
    record.attempts_count += 1

    # Update consecutive strong streak
    if evidence >= 0.90:
        record.consecutive_strong += 1
    else:
        record.consecutive_strong = 0

    record.updated_at = datetime.now(timezone.utc)
    return record
