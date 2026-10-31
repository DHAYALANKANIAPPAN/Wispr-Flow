"""Decision trace logger for explainable AI and algorithmic transparency.

Purpose:
    Persists auditable reason traces for every algorithmic decision:
    - Adaptive next question selection
    - Spaced repetition revision scheduling
    - Misconception classification events
    - Diagnostic progression

Status:
    Active, Phase 2 implementation.

Fail-Closed Behavior:
    - Rejects empty student_id, unknown decision types, or malformed payloads by raising ValueError.
    - Operates within caller's database transaction so logs rollback atomically if any step fails.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models import DecisionLog

VALID_DECISION_TYPES = {
    "next_question",
    "revision_schedule",
    "misconception_flag",
    "diagnostic_start",
    "mastery_update",
}


def log_decision(
    db: Session,
    student_id: str,
    decision_type: str,
    payload: Dict[str, Any],
) -> DecisionLog:
    """Record a structured decision trace in the decision_log table.

    Args:
        db: Active SQLAlchemy database session.
        student_id: Target student identifier.
        decision_type: Category of decision made. Must be in VALID_DECISION_TYPES.
        payload: Full context and reasoning trace dictionary.

    Returns:
        DecisionLog: Staged database record.

    Raises:
        ValueError: If student_id is empty, decision_type is invalid, or payload is not a dict.
    """
    if not student_id or not isinstance(student_id, str):
        raise ValueError("student_id must be a non-empty string")

    if decision_type not in VALID_DECISION_TYPES:
        raise ValueError(
            f"Invalid decision_type '{decision_type}'. Must be one of {sorted(VALID_DECISION_TYPES)}"
        )

    if not isinstance(payload, dict):
        raise ValueError("payload must be a valid dictionary")

    record = DecisionLog(
        student_id=student_id,
        decision_type=decision_type,
        payload_json=payload,
    )
    db.add(record)
    return record


def get_student_decisions(
    db: Session,
    student_id: str,
    decision_type: Optional[str] = None,
    limit: int = 50,
) -> List[DecisionLog]:
    """Retrieve decision history for a student ordered by most recent first.

    Args:
        db: Active SQLAlchemy session.
        student_id: Target student identifier.
        decision_type: Optional filter for a specific decision type.
        limit: Maximum number of rows to return.

    Returns:
        List[DecisionLog]: Matching decision log records.
    """
    query = (
        db.query(DecisionLog)
        .filter(DecisionLog.student_id == student_id)
        .order_by(DecisionLog.created_at.desc())
    )

    if decision_type:
        query = query.filter(DecisionLog.decision_type == decision_type)

    return query.limit(limit).all()
