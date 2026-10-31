"""Pydantic schemas for request and response validation.

Purpose:
    Enforces strict input validation, serialization, and typing contracts.

Status:
    Active, production-ready.

Fail-Closed Behavior:
    Rejects malformed, incomplete, or out-of-range payloads with HTTP 422 Unprocessable Entity.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# User and Auth Schemas
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    role: Literal["student", "teacher"]


class UserLogin(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    name: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# Concept and Prerequisite Schemas
class ConceptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    name: str
    description: Optional[str] = None
    prerequisites: List[str] = []
    is_unlocked: bool = False
    mastery: Optional[float] = None


# Question Schemas
class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    answer_type: Literal["numeric", "text"]
    tolerance: Optional[float] = 0.0
    difficulty: int
    question_type: Literal["conceptual", "numerical"]
    status: Literal["draft", "approved"]
    concept_ids: List[str] = []


# Attempt and Pipeline Schemas
class SubmitAnswerRequest(BaseModel):
    question_id: str
    student_answer: str = Field(..., min_length=1)
    explanation: str = Field(default="", description="Typed or dictated reasoning")
    session_id: Optional[str] = None


class DecisionTrace(BaseModel):
    rule: str
    concept: Optional[str] = None
    mastery: Optional[float] = None
    detail: Optional[str] = None


class NextQuestionDecision(BaseModel):
    question_id: Optional[str] = None
    concept_id: Optional[str] = None
    reason: Dict[str, Any]


class SubmitAnswerResponse(BaseModel):
    attempt_id: str
    correct: bool
    reasoning: Literal["sound", "weak", "none"]
    misconception_id: Optional[str] = None
    evidence: float
    llm_status: Literal["ok", "unavailable", "invalid_output", "skipped"]
    feedback: str
    concept_mastery_updates: Dict[str, float]
    next_question: NextQuestionDecision


# Revision and Analytics Schemas
class RevisionItemOut(BaseModel):
    concept_id: str
    due_date: datetime
    reason: Dict[str, Any]


class StudentMasterySummary(BaseModel):
    student_id: str
    concepts: Dict[str, Dict[str, Any]]
    weakest_concept: Optional[str] = None
    strongest_concept: Optional[str] = None
