"""Tests for KnowledgeGraph DAG and prerequisite unlock policies.

Purpose:
    Validates cycle rejection, prerequisite retrieval, and student concept unlock logic.
"""

import json
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import User, LearnerMastery, Subject, Concept
from backend.app.knowledge_graph import KnowledgeGraph


@pytest.fixture
def sample_graph():
    """Returns the default electricity knowledge graph."""
    return KnowledgeGraph()


@pytest.fixture
def test_db():
    """In-memory SQLite session fixture."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_root_concepts_unlocked_by_default(sample_graph):
    """Root concepts with no prerequisites must be unlocked for any student."""
    assert sample_graph.is_unlocked(student_id="student_1", concept_id="electric_current") is True
    assert sample_graph.is_unlocked(student_id=None, concept_id="potential_difference") is True
    assert sample_graph.is_unlocked(student_id="student_1", concept_id="resistance") is True


def test_dependent_concept_locked_initially(sample_graph):
    """Dependent concept (ohms_law) must be locked when student has no prerequisite mastery."""
    assert sample_graph.is_unlocked(student_id="student_1", concept_id="ohms_law") is False
    assert sample_graph.is_unlocked(student_id="student_1", concept_id="electrical_power") is False


def test_dependent_concept_unlocks_with_prerequisites(sample_graph, test_db):
    """Dependent concept unlocks once all prerequisites achieve threshold mastery."""
    student_id = "student_test_1"

    # ohms_law requires: electric_current, potential_difference, resistance
    # Set mastery below threshold (0.50 < 0.60)
    for cid in ["electric_current", "potential_difference", "resistance"]:
        test_db.add(LearnerMastery(student_id=student_id, concept_id=cid, mastery=0.50))
    test_db.commit()

    assert sample_graph.is_unlocked(student_id=student_id, concept_id="ohms_law", db=test_db) is False

    # Elevate mastery to >= 0.60
    for record in test_db.query(LearnerMastery).filter_by(student_id=student_id).all():
        record.mastery = 0.75
    test_db.commit()

    assert sample_graph.is_unlocked(student_id=student_id, concept_id="ohms_law", db=test_db) is True
    # electrical_power still locked because ohms_law is not mastered yet
    assert sample_graph.is_unlocked(student_id=student_id, concept_id="electrical_power", db=test_db) is False


def test_cycle_rejection():
    """Graph loader must detect and reject circular dependencies at initialization."""
    cyclic_data = {
        "concepts": [
            {"id": "A", "name": "Concept A", "prerequisites": ["B"]},
            {"id": "B", "name": "Concept B", "prerequisites": ["C"]},
            {"id": "C", "name": "Concept C", "prerequisites": ["A"]},
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cyclic_data, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Cycle detected"):
            KnowledgeGraph(concepts_path=temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_unknown_concept_raises(sample_graph):
    """Querying an unknown concept ID must raise KeyError."""
    with pytest.raises(KeyError, match="Unknown concept ID"):
        sample_graph.prerequisites_of("quantum_teleportation")

    with pytest.raises(KeyError, match="Unknown concept ID"):
        sample_graph.is_unlocked(student_id="s1", concept_id="quantum_teleportation")


def test_unknown_prerequisite_reference_raises():
    """Referencing a non-existent prerequisite must raise ValueError at load time."""
    invalid_data = {
        "concepts": [
            {"id": "A", "name": "Concept A", "prerequisites": ["NON_EXISTENT"]},
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(invalid_data, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="unknown prerequisite"):
            KnowledgeGraph(concepts_path=temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)
