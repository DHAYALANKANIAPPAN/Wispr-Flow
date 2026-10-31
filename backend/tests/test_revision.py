"""Tests for revision scheduler spaced repetition logic.

Purpose:
    Validates all scheduling threshold contracts from Section 5 of specification,
    including exact boundary handling (0.70 falls in 7-day rule) and database persistence.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import User, Concept, Subject, RevisionSchedule
from backend.app.revision import schedule_revision, apply_revision_schedule


@pytest.fixture
def test_db():
    """In-memory SQLite database session fixture."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    student = User(id="s_rev_test", role="student", name="Rev Student", email="rev@test.com", password_hash="dummy")
    subject = Subject(id="subj_rev", name="Physics")
    concept = Concept(id="conc_rev", subject_id="subj_rev", name="Electric Current")
    session.add_all([student, subject, concept])
    session.commit()

    yield session
    session.close()


def test_incorrect_answer_schedules_immediate_review():
    """Any incorrect answer must return 0 days for immediate review in the same session."""
    res = schedule_revision(mastery=0.95, last_result_correct=False, consecutive_strong=5)
    assert res["days_until_review"] == 0
    assert res["rule"] == "incorrect_same_session"


def test_mastery_below_0_40():
    """Mastery below 0.40 with correct answer returns 1 day (critical review)."""
    res = schedule_revision(mastery=0.35, last_result_correct=True, consecutive_strong=0)
    assert res["days_until_review"] == 1
    assert res["rule"] == "critical_review_1_day"


def test_mastery_0_40_to_0_70():
    """Mastery in [0.40, 0.70) returns 3 days (reinforce review)."""
    res_min = schedule_revision(mastery=0.40, last_result_correct=True, consecutive_strong=1)
    assert res_min["days_until_review"] == 3
    assert res_min["rule"] == "reinforce_review_3_days"

    res_mid = schedule_revision(mastery=0.69, last_result_correct=True, consecutive_strong=1)
    assert res_mid["days_until_review"] == 3
    assert res_mid["rule"] == "reinforce_review_3_days"


def test_boundary_value_0_70_falls_in_7_day_rule():
    """Boundary value requirement: 0.70 exactly falls in the 7-day rule (consolidation)."""
    res = schedule_revision(mastery=0.70, last_result_correct=True, consecutive_strong=1)
    assert res["days_until_review"] == 7
    assert res["rule"] == "consolidation_review_7_days"


def test_mastery_above_0_90_without_and_with_streak():
    """Mastery >= 0.90 requires consecutive_strong >= 3 to achieve 14-day interval; otherwise 7 days."""
    # Mastery 0.92, streak 2 -> 7 days
    res_no_streak = schedule_revision(mastery=0.92, last_result_correct=True, consecutive_strong=2)
    assert res_no_streak["days_until_review"] == 7
    assert res_no_streak["rule"] == "consolidation_review_7_days"

    # Mastery 0.92, streak 3 -> 14 days
    res_streak = schedule_revision(mastery=0.92, last_result_correct=True, consecutive_strong=3)
    assert res_streak["days_until_review"] == 14
    assert res_streak["rule"] == "mastered_review_14_days"


def test_apply_revision_schedule_persistence(test_db):
    """Test saving revision schedule to the database."""
    now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    rec = apply_revision_schedule(
        db=test_db,
        student_id="s_rev_test",
        concept_id="conc_rev",
        mastery=0.55,
        last_result_correct=True,
        consecutive_strong=1,
        now=now,
    )
    test_db.commit()

    expected_due = (now + timedelta(days=3)).replace(tzinfo=None)
    actual_due = rec.due_date.replace(tzinfo=None) if rec.due_date.tzinfo else rec.due_date
    assert actual_due == expected_due
    assert rec.reason_json["rule"] == "reinforce_review_3_days"

    # Read back from database
    stored = (
        test_db.query(RevisionSchedule)
        .filter_by(student_id="s_rev_test", concept_id="conc_rev")
        .first()
    )
    assert stored is not None
    stored_due = stored.due_date.replace(tzinfo=None) if stored.due_date.tzinfo else stored.due_date
    assert stored_due == expected_due
