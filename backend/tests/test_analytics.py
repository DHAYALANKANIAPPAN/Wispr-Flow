"""Tests for analytics aggregates and dashboard read endpoints.

Purpose:
    Validates that:
    1. student_summary computes accurate mastery, weakest/strongest concepts,
       accuracy percentages, and review dates from seeded database rows.
    2. class_summary computes accurate class averages, most-missed concepts,
       students needing support, and misconception distributions.
    3. Hand-computed expected values match database calculations exactly.
    4. HTTP read endpoints enforce authorization and return correct payloads.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.models import (
    User,
    Subject,
    Concept,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    RevisionSchedule,
    MisconceptionEvent,
    DecisionLog,
)
from backend.app.analytics import student_summary, class_summary
from backend.app.main import app


@pytest.fixture
def analytics_db():
    """In-memory SQLite session with known hand-computed ground truth records."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # 1. Subject & Concepts
    subj = Subject(id="physics_cbse_10", name="Physics")
    c1 = Concept(id="electric_current", subject_id="physics_cbse_10", name="Electric Current")
    c2 = Concept(id="potential_difference", subject_id="physics_cbse_10", name="Potential Difference")
    c3 = Concept(id="resistance", subject_id="physics_cbse_10", name="Resistance")
    session.add_all([subj, c1, c2, c3])

    # 2. Users (1 Teacher, 2 Students)
    teacher = User(id="teacher_01", role="teacher", name="Prof. Turing", email="turing@school.org", password_hash="hash")
    s1 = User(id="student_01", role="student", name="Alice", email="alice@school.org", password_hash="hash")
    s2 = User(id="student_02", role="student", name="Bob", email="bob@school.org", password_hash="hash")
    session.add_all([teacher, s1, s2])

    # 3. Learner Mastery:
    # Alice:
    # electric_current: 0.80, attempts: 2
    # resistance: 0.30, attempts: 2 (Alice weakest: resistance)
    # Bob:
    # electric_current: 0.40, attempts: 1
    # resistance: 0.60, attempts: 1 (Bob weakest: electric_current)
    session.add_all([
        LearnerMastery(student_id="student_01", concept_id="electric_current", mastery=0.80, attempts_count=2),
        LearnerMastery(student_id="student_01", concept_id="resistance", mastery=0.30, attempts_count=2),
        LearnerMastery(student_id="student_02", concept_id="electric_current", mastery=0.40, attempts_count=1),
        LearnerMastery(student_id="student_02", concept_id="resistance", mastery=0.60, attempts_count=1),
    ])

    # 4. Questions
    q1 = Question(id="q1", text="Q1", answer_key="k1", answer_type="text", difficulty=1, question_type="conceptual", status="approved")
    q2 = Question(id="q2", text="Q2", answer_key="k2", answer_type="text", difficulty=2, question_type="conceptual", status="approved")
    session.add_all([q1, q2])

    # 5. Attempts:
    # Alice: 3 attempts (2 correct, 1 incorrect with MC_PROPORTIONAL_I_R)
    # Accuracy: 2/3 = 66.7%
    att1 = Attempt(id="a1", student_id="student_01", question_id="q1", student_answer="k1", correct=True, reasoning="sound", evidence=1.0, llm_status="ok")
    att2 = Attempt(id="a2", student_id="student_01", question_id="q1", student_answer="k1", correct=True, reasoning="none", evidence=0.8, llm_status="ok")
    att3 = Attempt(id="a3", student_id="student_01", question_id="q2", student_answer="bad", correct=False, reasoning="none", misconception_id="MC_PROPORTIONAL_I_R", evidence=0.0, llm_status="ok")

    # Bob: 2 attempts (1 correct, 1 incorrect with MC_CURRENT_USED_UP)
    # Accuracy: 1/2 = 50.0%
    att4 = Attempt(id="a4", student_id="student_02", question_id="q1", student_answer="k1", correct=True, reasoning="sound", evidence=1.0, llm_status="ok")
    att5 = Attempt(id="a5", student_id="student_02", question_id="q2", student_answer="bad", correct=False, reasoning="none", misconception_id="MC_CURRENT_USED_UP", evidence=0.0, llm_status="ok")

    session.add_all([att1, att2, att3, att4, att5])
    session.flush()

    # 6. Misconception events
    session.add(MisconceptionEvent(attempt_id="a3", misconception_id="MC_PROPORTIONAL_I_R", evidence_text="proportional text"))
    session.add(MisconceptionEvent(attempt_id="a5", misconception_id="MC_CURRENT_USED_UP", evidence_text="used up text"))

    # 7. Revision schedule for Alice
    now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    session.add(RevisionSchedule(student_id="student_01", concept_id="resistance", due_date=now + timedelta(days=1), reason_json={"rule": "critical_review_1_day"}))

    # 8. Decision log for Alice
    session.add(DecisionLog(student_id="student_01", decision_type="next_question", payload_json={"rule": "weakest_concept", "concept": "resistance"}))

    session.commit()
    yield session
    session.close()


def test_student_summary_hand_computed_totals(analytics_db):
    """Test student_summary against hand-computed expected metrics for Alice."""
    summary = student_summary(student_id="student_01", db=analytics_db)

    assert summary["student_id"] == "student_01"
    assert summary["total_attempts"] == 3
    assert summary["accuracy_percentage"] == 66.7

    # Weakest is resistance (0.30)
    assert summary["weakest_concept"] == "resistance"
    # Strongest is electric_current (0.80)
    assert summary["strongest_concept"] == "electric_current"

    # Misconceptions list contains MC_PROPORTIONAL_I_R count 1
    assert len(summary["misconceptions_encountered"]) == 1
    assert summary["misconceptions_encountered"][0]["misconception_id"] == "MC_PROPORTIONAL_I_R"
    assert summary["misconceptions_encountered"][0]["count"] == 1

    # Upcoming revision
    assert len(summary["upcoming_revisions"]) == 1
    assert summary["upcoming_revisions"][0]["concept_id"] == "resistance"


def test_class_summary_hand_computed_totals(analytics_db):
    """Test class_summary against hand-computed expected metrics for Teacher 01."""
    summary = class_summary(teacher_id="teacher_01", db=analytics_db)

    assert summary["teacher_id"] == "teacher_01"
    assert summary["total_students"] == 2
    assert summary["total_attempts"] == 5
    # Total correct: 3 out of 5 -> 60.0%
    assert summary["average_class_accuracy"] == 60.0

    # Class concept mastery averages:
    # electric_current: (0.80 + 0.40) / 2 = 0.60
    # resistance: (0.30 + 0.60) / 2 = 0.45
    cm = summary["concept_class_mastery"]
    assert cm["electric_current"]["average_mastery"] == 0.60
    assert cm["resistance"]["average_mastery"] == 0.45

    # Most missed concept: resistance (0.45 < 0.60)
    assert summary["most_missed_concept"] == "resistance"

    # Students needing support:
    # Alice has resistance 0.30 (< 0.40) -> Alice needs support
    # Bob has electric_current 0.40 and avg (0.40+0.60)/2 = 0.50 -> Alice is flagged
    support_ids = [s["student_id"] for s in summary["students_needing_support"]]
    assert "student_01" in support_ids

    # Misconception distribution: 1 MC_PROPORTIONAL_I_R, 1 MC_CURRENT_USED_UP
    dist = summary["misconception_distribution"]
    assert dist["MC_PROPORTIONAL_I_R"] == 1
    assert dist["MC_CURRENT_USED_UP"] == 1


def test_api_read_endpoints_with_auth(analytics_db):
    """Test GET /students/{id}/mastery, GET /students/{id}/decisions, and GET /teachers/{id}/class-summary."""
    from backend.app.auth import create_access_token

    def override_get_db():
        yield analytics_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    alice_token = create_access_token(user_id="student_01", role="student")
    teacher_token = create_access_token(user_id="teacher_01", role="teacher")

    # 1. Alice reads own mastery
    m_res = client.get(
        "/students/student_01/mastery",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert m_res.status_code == 200
    assert m_res.json()["weakest_concept"] == "resistance"

    # 2. Alice reads own decisions
    d_res = client.get(
        "/students/student_01/decisions",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert d_res.status_code == 200
    assert len(d_res.json()) >= 1
    assert d_res.json()[0]["decision_type"] == "next_question"

    # 3. Teacher reads class summary
    c_res = client.get(
        "/teachers/teacher_01/class-summary",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert c_res.status_code == 200
    assert c_res.json()["most_missed_concept"] == "resistance"

    app.dependency_overrides.clear()
