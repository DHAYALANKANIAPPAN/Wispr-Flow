"""Analytics and aggregation services for student and teacher dashboards.

Purpose:
    Computes performance aggregates, class summaries, spaced review timelines,
    and misconception distributions strictly from persisted relational database records.

Status:
    Active, Phase 4 implementation.

Fail-Closed Behavior:
    - Never injects synthetic or hard-coded student data into production analytics.
    - If no attempts or mastery records exist, returns deterministic empty/zero structures.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models import (
    User,
    Concept,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    RevisionSchedule,
    MisconceptionEvent,
)
from backend.app.knowledge_graph import knowledge_graph


def student_summary(student_id: str, db: Session) -> Dict[str, Any]:
    """Compute detailed analytics for a single student strictly from DB records.

    Args:
        student_id: Target student identifier.
        db: Active database session.

    Returns:
        dict:
            - 'student_id': str
            - 'concept_mastery': dict of concept_id -> {name, mastery, percentage, attempts_count}
            - 'weakest_concept': Optional[str]
            - 'strongest_concept': Optional[str]
            - 'total_attempts': int
            - 'accuracy_percentage': float
            - 'upcoming_revisions': list of {concept_id, concept_name, due_date, rule}
            - 'misconceptions_encountered': list of {misconception_id, count}
    """
    all_concepts = knowledge_graph.get_all_concepts()
    concept_names = {c["id"]: c["name"] for c in all_concepts}

    mastery_records = (
        db.query(LearnerMastery)
        .filter(LearnerMastery.student_id == student_id)
        .all()
    )
    mastery_dict = {r.concept_id: r for r in mastery_records}

    concept_mastery_out = {}
    for cid, name in concept_names.items():
        rec = mastery_dict.get(cid)
        m_val = rec.mastery if rec else 0.50
        attempts = rec.attempts_count if rec else 0
        concept_mastery_out[cid] = {
            "name": name,
            "mastery": m_val,
            "percentage": round(m_val * 100, 1),
            "attempts_count": attempts,
        }

    # Weakest and strongest among concepts with attempts
    concepts_with_attempts = [
        (cid, data["mastery"])
        for cid, data in concept_mastery_out.items()
        if data["attempts_count"] > 0
    ]

    weakest_cid = min(concepts_with_attempts, key=lambda x: x[1])[0] if concepts_with_attempts else None
    strongest_cid = max(concepts_with_attempts, key=lambda x: x[1])[0] if concepts_with_attempts else None

    # Overall attempt counts and accuracy
    attempts = db.query(Attempt).filter(Attempt.student_id == student_id).all()
    total_attempts = len(attempts)
    correct_attempts = sum(1 for a in attempts if a.correct)
    accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # Upcoming revisions
    schedules = (
        db.query(RevisionSchedule)
        .filter(RevisionSchedule.student_id == student_id)
        .order_by(RevisionSchedule.due_date.asc())
        .all()
    )
    upcoming_revisions = [
        {
            "concept_id": s.concept_id,
            "concept_name": concept_names.get(s.concept_id, s.concept_id),
            "due_date": s.due_date.isoformat(),
            "rule": s.reason_json.get("rule", "standard_review"),
        }
        for s in schedules
    ]

    # Misconceptions encountered
    misc_events = (
        db.query(MisconceptionEvent)
        .join(Attempt, MisconceptionEvent.attempt_id == Attempt.id)
        .filter(Attempt.student_id == student_id)
        .all()
    )
    misc_counts = defaultdict(int)
    for m in misc_events:
        misc_counts[m.misconception_id] += 1

    misconceptions_list = [
        {"misconception_id": mid, "count": count}
        for mid, count in sorted(misc_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "student_id": student_id,
        "concept_mastery": concept_mastery_out,
        "weakest_concept": weakest_cid,
        "strongest_concept": strongest_cid,
        "total_attempts": total_attempts,
        "accuracy_percentage": accuracy,
        "upcoming_revisions": upcoming_revisions,
        "misconceptions_encountered": misconceptions_list,
    }


def class_summary(teacher_id: str, db: Session) -> Dict[str, Any]:
    """Compute aggregate class mastery and diagnostics strictly from database records.

    Args:
        teacher_id: Target teacher identifier.
        db: Active database session.

    Returns:
        dict:
            - 'teacher_id': str
            - 'total_students': int
            - 'total_attempts': int
            - 'average_class_accuracy': float
            - 'concept_class_mastery': dict of concept_id -> {name, average_mastery, average_percentage}
            - 'most_missed_concept': Optional[str]
            - 'students_needing_support': list of {student_id, student_name, average_mastery, weakest_concept}
            - 'misconception_distribution': dict of misconception_id -> count
    """
    all_concepts = knowledge_graph.get_all_concepts()
    concept_names = {c["id"]: c["name"] for c in all_concepts}

    students = db.query(User).filter(User.role == "student").all()
    total_students = len(students)

    all_attempts = db.query(Attempt).all()
    total_attempts = len(all_attempts)
    correct_attempts = sum(1 for a in all_attempts if a.correct)
    class_accuracy = round((correct_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # Class mastery per concept
    concept_sums = defaultdict(float)
    concept_counts = defaultdict(int)

    all_mastery_records = db.query(LearnerMastery).all()
    for m in all_mastery_records:
        concept_sums[m.concept_id] += m.mastery
        concept_counts[m.concept_id] += 1

    concept_class_mastery = {}
    for cid, name in concept_names.items():
        count = concept_counts[cid]
        avg_m = round(concept_sums[cid] / count, 3) if count > 0 else 0.50
        concept_class_mastery[cid] = {
            "name": name,
            "average_mastery": avg_m,
            "average_percentage": round(avg_m * 100, 1),
            "students_assessed": count,
        }

    # Most missed concept: concept with lowest average mastery among evaluated
    assessed_concepts = [
        (cid, data["average_mastery"])
        for cid, data in concept_class_mastery.items()
        if data["students_assessed"] > 0
    ]
    most_missed_cid = min(assessed_concepts, key=lambda x: x[1])[0] if assessed_concepts else None

    # Students needing support: average mastery < 0.50 or any concept < 0.40
    students_needing_support = []
    for s in students:
        s_mastery = db.query(LearnerMastery).filter(LearnerMastery.student_id == s.id).all()
        if not s_mastery:
            continue

        scores = [m.mastery for m in s_mastery]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)

        if avg_score < 0.50 or min_score < 0.40:
            weakest_c = min(s_mastery, key=lambda x: x.mastery).concept_id
            students_needing_support.append({
                "student_id": s.id,
                "student_name": s.name,
                "average_mastery": round(avg_score, 2),
                "weakest_concept": concept_names.get(weakest_c, weakest_c),
            })

    # Misconception distribution across the entire class
    misc_counts = (
        db.query(MisconceptionEvent.misconception_id, func.count(MisconceptionEvent.id))
        .group_by(MisconceptionEvent.misconception_id)
        .all()
    )
    misconception_distribution = {mid: count for mid, count in misc_counts}

    return {
        "teacher_id": teacher_id,
        "total_students": total_students,
        "total_attempts": total_attempts,
        "average_class_accuracy": class_accuracy,
        "concept_class_mastery": concept_class_mastery,
        "most_missed_concept": most_missed_cid,
        "students_needing_support": students_needing_support,
        "misconception_distribution": misconception_distribution,
    }
