"""Tests for learner model and mastery update mathematical contracts.

Purpose:
    Validates the update_mastery formula, clamping behavior, type rejection,
    consecutive_strong streak updating, and database persistence.
"""

import math
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import LearnerMastery, User, Concept, Subject
from backend.app.learner_model import (
    update_mastery,
    get_or_create_mastery,
    apply_mastery_update,
)


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
    yield session
    session.close()


def test_update_mastery_normal():
    """Test normal textbook case: m_old=0.40, evidence=1.00, alpha=0.20 -> 0.52."""
    result = update_mastery(m_old=0.40, evidence=1.00, alpha=0.20)
    assert result == pytest.approx(0.52, abs=1e-4)


def test_update_mastery_ambiguous():
    """Test ambiguous case: evidence 0.5 moves mastery toward 0.5."""
    # From higher mastery (0.80) -> decreases toward 0.5
    res_high = update_mastery(m_old=0.80, evidence=0.50, alpha=0.20)
    assert res_high < 0.80
    assert res_high == pytest.approx(0.74, abs=1e-4)

    # From lower mastery (0.20) -> increases toward 0.5
    res_low = update_mastery(m_old=0.20, evidence=0.50, alpha=0.20)
    assert res_low > 0.20
    assert res_low == pytest.approx(0.26, abs=1e-4)


def test_update_mastery_alpha_zero_leaves_unchanged():
    """Test that alpha=0.0 leaves mastery score unchanged."""
    result = update_mastery(m_old=0.45, evidence=1.00, alpha=0.0)
    assert result == 0.45


def test_update_mastery_out_of_bounds_clamping():
    """Evidence scores and mastery outside [0, 1] must be clamped strictly to [0, 1]."""
    # Evidence > 1.0 clamped to 1.0
    res_over = update_mastery(m_old=0.90, evidence=2.5, alpha=0.5)
    assert res_over <= 1.0
    assert res_over == pytest.approx(0.95, abs=1e-4)

    # Evidence < 0.0 clamped to 0.0
    res_under = update_mastery(m_old=0.10, evidence=-1.0, alpha=0.5)
    assert res_under >= 0.0
    assert res_under == pytest.approx(0.05, abs=1e-4)


def test_update_mastery_invalid_types_raise():
    """Non-numeric inputs must raise TypeError."""
    with pytest.raises(TypeError):
        update_mastery("0.5", 1.0, 0.2)  # type: ignore

    with pytest.raises(TypeError):
        update_mastery(0.5, None, 0.2)  # type: ignore

    with pytest.raises(TypeError):
        update_mastery(0.5, 1.0, "alpha")  # type: ignore


def test_update_mastery_nan_raises():
    """NaN values must be rejected with ValueError."""
    with pytest.raises(ValueError):
        update_mastery(float("nan"), 1.0, 0.2)

    with pytest.raises(ValueError):
        update_mastery(0.5, float("nan"), 0.2)

    with pytest.raises(ValueError):
        update_mastery(0.5, 1.0, float("nan"))


def test_database_persistence_and_streaks(test_db):
    """Test DB integration: initial mastery, attempts counting, consecutive strong streak."""
    # Seed student and concept
    student = User(id="s_test", role="student", name="Test Student", email="s@test.com", password_hash="dummy")
    subject = Subject(id="subj_test", name="Physics")
    concept = Concept(id="res_test", subject_id="subj_test", name="Resistance")
    test_db.add_all([student, subject, concept])
    test_db.commit()

    # 1. Unseen concept initialized to 0.50
    rec = get_or_create_mastery(test_db, "s_test", "res_test")
    test_db.commit()
    assert rec.mastery == 0.50
    assert rec.attempts_count == 0
    assert rec.consecutive_strong == 0

    # 2. First attempt with evidence 1.0 -> mastery = 0.5 + 0.2*(1 - 0.5) = 0.60
    # consecutive_strong -> 1
    rec = apply_mastery_update(test_db, "s_test", "res_test", evidence=1.0)
    test_db.commit()
    assert rec.mastery == 0.60
    assert rec.attempts_count == 1
    assert rec.consecutive_strong == 1

    # 3. Second strong attempt -> consecutive_strong -> 2
    rec = apply_mastery_update(test_db, "s_test", "res_test", evidence=0.95)
    test_db.commit()
    assert rec.attempts_count == 2
    assert rec.consecutive_strong == 2

    # 4. Weak attempt (evidence < 0.90) -> resets consecutive_strong to 0
    rec = apply_mastery_update(test_db, "s_test", "res_test", evidence=0.30)
    test_db.commit()
    assert rec.attempts_count == 3
    assert rec.consecutive_strong == 0
