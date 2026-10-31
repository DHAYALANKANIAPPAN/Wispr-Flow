"""SQLAlchemy ORM models for Adaptive IQ.

Purpose:
    Defines the database schema across SQLite (development) and PostgreSQL (production).
    Enforces relational integrity, audit tracking, decision logging, and learner mastery state.

Status:
    Active, strict schema definition matching Section 6 of specification.

Fail-Closed Behavior:
    Enforces foreign key relationships, non-nullable required constraints,
    and type validations at the database and ORM layers.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.db import Base


def _generate_uuid() -> str:
    """Generate a random UUID string for primary keys."""
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    """Return the current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account model for students and teachers."""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=_generate_uuid)
    role = Column(String(16), nullable=False)  # 'student' | 'teacher'
    name = Column(String(128), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    attempts = relationship("Attempt", back_populates="student")
    mastery_records = relationship("LearnerMastery", back_populates="student")
    revision_schedules = relationship("RevisionSchedule", back_populates="student")
    decision_logs = relationship("DecisionLog", back_populates="student")


class Subject(Base):
    """Academic subject container."""
    __tablename__ = "subjects"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)

    concepts = relationship("Concept", back_populates="subject")


class Concept(Base):
    """Target knowledge concept node within a subject."""
    __tablename__ = "concepts"

    id = Column(String(64), primary_key=True)
    subject_id = Column(String(64), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    subject = relationship("Subject", back_populates="concepts")
    questions = relationship("QuestionConcept", back_populates="concept")
    mastery_records = relationship("LearnerMastery", back_populates="concept")


class ConceptPrerequisite(Base):
    """Prerequisite relationship between concepts."""
    __tablename__ = "concept_prerequisites"

    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    prerequisite_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("concept_id", "prerequisite_id"),
    )


class Question(Base):
    """Question item in the question bank."""
    __tablename__ = "questions"

    id = Column(String(64), primary_key=True)
    text = Column(Text, nullable=False)
    answer_key = Column(String(255), nullable=False)
    answer_type = Column(String(16), nullable=False)  # 'numeric' | 'text'
    tolerance = Column(Float, nullable=True, default=0.0)
    difficulty = Column(Integer, nullable=False)  # 1 | 2 | 3
    question_type = Column(String(16), nullable=False)  # 'conceptual' | 'numerical'
    rubric = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="draft")  # 'draft' | 'approved'
    reviewed_by = Column(String(128), nullable=True)

    concepts = relationship("QuestionConcept", back_populates="question")
    attempts = relationship("Attempt", back_populates="question")


class QuestionConcept(Base):
    """Join table associating questions with tested concepts."""
    __tablename__ = "question_concepts"

    question_id = Column(String(64), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("question_id", "concept_id"),
    )

    question = relationship("Question", back_populates="concepts")
    concept = relationship("Concept", back_populates="questions")


class Attempt(Base):
    """Immutable log of student question attempts."""
    __tablename__ = "attempts"

    id = Column(String(64), primary_key=True, default=_generate_uuid)
    student_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(64), nullable=True)
    student_answer = Column(Text, nullable=False)
    explanation_raw = Column(Text, nullable=True)
    explanation_clean = Column(Text, nullable=True)
    correct = Column(Boolean, nullable=False)
    reasoning = Column(String(16), nullable=False)  # 'sound' | 'weak' | 'none'
    misconception_id = Column(String(64), nullable=True)
    evidence = Column(Float, nullable=False)
    llm_status = Column(String(32), nullable=False)  # 'ok' | 'unavailable' | 'invalid_output' | 'skipped'
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")
    misconception_event = relationship("MisconceptionEvent", back_populates="attempt", uselist=False)


class LearnerMastery(Base):
    """Tracks per-student, per-concept mastery state."""
    __tablename__ = "learner_mastery"

    student_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    mastery = Column(Float, nullable=False, default=0.5)
    consecutive_strong = Column(Integer, nullable=False, default=0)
    attempts_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("student_id", "concept_id"),
    )

    student = relationship("User", back_populates="mastery_records")
    concept = relationship("Concept", back_populates="mastery_records")


class MisconceptionEvent(Base):
    """Stores detailed evidence whenever a misconception is identified."""
    __tablename__ = "misconceptions"

    id = Column(String(64), primary_key=True, default=_generate_uuid)
    attempt_id = Column(String(64), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, unique=True)
    misconception_id = Column(String(64), nullable=False)
    evidence_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    attempt = relationship("Attempt", back_populates="misconception_event")


class RevisionSchedule(Base):
    """Tracks scheduled revision review dates for concepts per student."""
    __tablename__ = "revision_schedule"

    student_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(64), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    reason_json = Column(JSON, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("student_id", "concept_id"),
    )

    student = relationship("User", back_populates="revision_schedules")


class DecisionLog(Base):
    """Audit log of all system decisions for explainability."""
    __tablename__ = "decision_log"

    id = Column(String(64), primary_key=True, default=_generate_uuid)
    student_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_type = Column(String(64), nullable=False)  # 'next_question' | 'revision_schedule' | 'misconception'
    payload_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student = relationship("User", back_populates="decision_logs")
