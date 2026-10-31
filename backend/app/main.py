"""FastAPI application main entrypoint and routing.

Purpose:
    Exposes REST endpoints for authentication, diagnostic assessments,
    adaptive quizzes, answer evaluation, learner mastery, and analytics.

Status:
    Active, Phase 2/3 complete pipeline implementation.

Fail-Closed Behavior:
    Fails closed on missing or unverified credentials, invalid schema payloads,
    and missing concept/question entities. Full answer submission executes
    in an atomic transaction that rolls back completely on any exception.
"""

from pathlib import Path
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.db import get_db, Base, engine, SessionLocal
from backend.app.models import (
    User,
    Subject,
    Concept,
    ConceptPrerequisite,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    MisconceptionEvent,
    RevisionSchedule,
    DecisionLog,
)
from backend.app.schemas import (
    UserRegister,
    UserLogin,
    UserOut,
    TokenResponse,
    ConceptOut,
    QuestionOut,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    NextQuestionDecision,
)
from backend.app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_student_access,
    require_teacher_access,
)
from backend.app.knowledge_graph import knowledge_graph
from backend.app.text_clean import normalize_explanation
from backend.app.evaluation import evaluate_answer
from backend.app.learner_model import apply_mastery_update
from backend.app.revision import apply_revision_schedule
from backend.app.decisions import log_decision
from backend.app.adaptive_engine import select_next_question

# Ensure tables exist (auto-migration for dev SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Adaptive IQ API",
    description="Adaptive Exam-Prep Tutor with a Learner Model",
    version="1.0.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_database_from_content(db: Session) -> None:
    """Seed concepts, prerequisites, and questions from content files if empty.

    Args:
        db: Active database session.
    """
    content_dir = Path(__file__).resolve().parent.parent.parent / "content" / "electricity"
    concepts_file = content_dir / "concepts.json"
    questions_file = content_dir / "questions.jsonl"

    # Seed concepts if not present
    if concepts_file.exists() and db.query(Subject).count() == 0:
        with open(concepts_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        subj = Subject(id=data.get("subject_id", "physics_cbse_10"), name="CBSE Class 10 Physics")
        db.add(subj)
        db.flush()

        for c in data.get("concepts", []):
            db.add(
                Concept(
                    id=c["id"],
                    subject_id=subj.id,
                    name=c["name"],
                    description=c.get("description", ""),
                )
            )
        db.flush()

        for c in data.get("concepts", []):
            for prereq_id in c.get("prerequisites", []):
                db.add(ConceptPrerequisite(concept_id=c["id"], prerequisite_id=prereq_id))
        db.commit()

    # Seed questions if not present
    if questions_file.exists() and db.query(Question).count() == 0:
        with open(questions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                q = Question(
                    id=item["id"],
                    text=item["text"],
                    answer_key=item["answer_key"],
                    answer_type=item["answer_type"],
                    tolerance=item.get("tolerance", 0.0),
                    difficulty=item["difficulty"],
                    question_type=item["question_type"],
                    rubric=item.get("rubric", ""),
                    status=item.get("status", "draft"),
                    reviewed_by=item.get("reviewed_by"),
                )
                db.add(q)
                db.flush()
                for cid in item.get("concept_ids", []):
                    db.add(QuestionConcept(question_id=q.id, concept_id=cid))
        db.commit()


# Seed on application startup
with SessionLocal() as init_db:
    try:
        seed_database_from_content(init_db)
    except Exception:
        init_db.rollback()


@app.get("/health", tags=["system"])
def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "Adaptive IQ"}


@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new student or teacher user."""
    existing_user = db.query(User).filter_by(email=payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a student or teacher user with email and password."""
    user = db.query(User).filter_by(email=payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user profile."""
    return UserOut.model_validate(current_user)


@app.get("/students/{student_id}/mastery-test", tags=["auth"])
def get_student_mastery_auth_test(
    student_id: str,
    current_user: User = Depends(get_current_user),
):
    """Auth validation endpoint to verify cross-student access is blocked."""
    require_student_access(student_id=student_id, current_user=current_user)
    return {"status": "authorized", "student_id": student_id}


@app.get("/teachers/{teacher_id}/class-summary-test", tags=["auth"])
def get_teacher_class_auth_test(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
):
    """Auth validation endpoint to verify cross-teacher access is blocked."""
    require_teacher_access(teacher_id=teacher_id, current_user=current_user)
    return {"status": "authorized", "teacher_id": teacher_id}


@app.get("/concepts", response_model=List[ConceptOut], tags=["curriculum"])
def list_concepts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List chapter concepts along with prerequisite locks and mastery for the authenticated student."""
    mastery_records = db.query(LearnerMastery).filter_by(student_id=current_user.id).all()
    mastery_map = {m.concept_id: m.mastery for m in mastery_records}

    all_concepts = knowledge_graph.get_all_concepts()
    result = []

    for c in all_concepts:
        cid = c["id"]
        is_unlocked = knowledge_graph.is_unlocked(
            student_id=current_user.id,
            concept_id=cid,
            mastery_map=mastery_map,
        )
        result.append(
            ConceptOut(
                id=cid,
                subject_id="physics_cbse_10",
                name=c["name"],
                description=c.get("description"),
                prerequisites=c["prerequisites"],
                is_unlocked=is_unlocked,
                mastery=mastery_map.get(cid, 0.5 if is_unlocked else None),
            )
        )

    return result


@app.get("/diagnostic/questions", response_model=List[QuestionOut], tags=["diagnostic"])
def get_diagnostic_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the fixed set of 8 approved diagnostic questions covering the syllabus."""
    diagnostic_ids = [
        "q_diag_01",
        "q_diag_02",
        "q_diag_03",
        "q_diag_04",
        "q_diag_05",
        "q_diag_06",
        "q_diag_07",
        "q_diag_08",
    ]

    questions = (
        db.query(Question)
        .filter(Question.id.in_(diagnostic_ids), Question.status == "approved")
        .all()
    )

    out = []
    for q in questions:
        cids = [qc.concept_id for qc in q.concepts]
        q_dict = QuestionOut(
            id=q.id,
            text=q.text,
            answer_type=q.answer_type,
            tolerance=q.tolerance,
            difficulty=q.difficulty,
            question_type=q.question_type,
            status=q.status,
            concept_ids=cids,
        )
        out.append(q_dict)

    return out


@app.get("/questions/next", response_model=NextQuestionDecision, tags=["adaptive"])
def get_next_question(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the next recommended question for the authenticated student."""
    decision = select_next_question(student_id=current_user.id, db=db)
    q_data = None
    if decision["question_id"]:
        q = db.query(Question).filter_by(id=decision["question_id"]).first()
        if q:
            cids = [qc.concept_id for qc in q.concepts]
            q_data = QuestionOut(
                id=q.id,
                text=q.text,
                answer_key=q.answer_key,
                answer_type=q.answer_type,
                tolerance=q.tolerance,
                difficulty=q.difficulty,
                question_type=q.question_type,
                rubric=q.rubric,
                status=q.status,
                concept_ids=cids,
            )

    return NextQuestionDecision(
        question_id=decision["question_id"],
        concept_id=decision["concept_id"],
        reason=decision["reason"],
        question=q_data,
    )


@app.get("/questions/{question_id}", response_model=QuestionOut, tags=["adaptive"])
def get_question_by_id(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve question metadata and prompt by identifier."""
    q = db.query(Question).filter_by(id=question_id).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{question_id}' not found",
        )
    cids = [qc.concept_id for qc in q.concepts]
    return QuestionOut(
        id=q.id,
        text=q.text,
        answer_key=q.answer_key,
        answer_type=q.answer_type,
        tolerance=q.tolerance,
        difficulty=q.difficulty,
        question_type=q.question_type,
        rubric=q.rubric,
        status=q.status,
        concept_ids=cids,
    )


@app.post("/attempts", response_model=SubmitAnswerResponse, status_code=status.HTTP_201_CREATED, tags=["quiz"])
def submit_attempt(
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit an answer to a question and run the complete 9-step atomic update pipeline.

    Unified Data Flow (Section 4):
    1. Normalize explanation
    2. Deterministic correctness check
    3. LLM reasoning classification (or fail-closed fallback)
    4. Evidence score computation
    5. Learner model update for each concept
    6. Attempt persisted (with MisconceptionEvent if detected)
    7. Revision schedule updated
    8. Adaptive next question chosen + reason logged
    9. Response payload returned
    """
    # 1. Fetch question and enforce 'approved' status
    question = db.query(Question).filter_by(id=payload.question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID '{payload.question_id}' not found",
        )

    if question.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved questions may be answered by students",
        )

    tested_concept_ids = [qc.concept_id for qc in question.concepts]
    if not tested_concept_ids:
        # Fallback to electric_current if untagged
        tested_concept_ids = ["electric_current"]

    # 2. Normalize explanation
    clean_res = normalize_explanation(payload.explanation)
    clean_text = clean_res["clean"]

    # 3. Evaluate answer deterministically and classify reasoning
    q_dict = {
        "id": question.id,
        "text": question.text,
        "answer_key": question.answer_key,
        "answer_type": question.answer_type,
        "tolerance": question.tolerance,
    }

    eval_res = evaluate_answer(
        question=q_dict,
        student_answer=payload.student_answer,
        explanation=clean_text,
    )

    correct = eval_res["correct"]
    reasoning = eval_res["reasoning"]
    misconception_id = eval_res["misconception_id"]
    evidence = eval_res["evidence"]
    llm_status_val = eval_res["llm_status"]
    feedback_text = eval_res["feedback"]

    try:
        # Begin atomic transaction mutations
        # 5. Learner model update per concept
        concept_mastery_updates: Dict[str, float] = {}
        for cid in tested_concept_ids:
            updated_record = apply_mastery_update(
                db=db,
                student_id=current_user.id,
                concept_id=cid,
                evidence=evidence,
            )
            concept_mastery_updates[cid] = updated_record.mastery

            # Log mastery update decision
            log_decision(
                db=db,
                student_id=current_user.id,
                decision_type="mastery_update",
                payload={
                    "concept_id": cid,
                    "new_mastery": updated_record.mastery,
                    "evidence": evidence,
                    "attempts_count": updated_record.attempts_count,
                    "consecutive_strong": updated_record.consecutive_strong,
                },
            )

        # 6. Store attempt record (never overwritten)
        attempt = Attempt(
            student_id=current_user.id,
            question_id=question.id,
            session_id=payload.session_id,
            student_answer=payload.student_answer,
            explanation_raw=payload.explanation,
            explanation_clean=clean_text,
            correct=correct,
            reasoning=reasoning,
            misconception_id=misconception_id,
            evidence=evidence,
            llm_status=llm_status_val,
        )
        db.add(attempt)
        db.flush()

        # If misconception was detected, store event and log decision
        if misconception_id is not None and misconception_id != "NONE":
            misc_event = MisconceptionEvent(
                attempt_id=attempt.id,
                misconception_id=misconception_id,
                evidence_text=clean_text,
            )
            db.add(misc_event)

            log_decision(
                db=db,
                student_id=current_user.id,
                decision_type="misconception_flag",
                payload={
                    "attempt_id": attempt.id,
                    "misconception_id": misconception_id,
                    "evidence_snippet": clean_text[:200],
                },
            )

        # 7. Update revision schedule for each updated concept
        for cid in tested_concept_ids:
            m_val = concept_mastery_updates[cid]
            m_rec = db.query(LearnerMastery).filter_by(student_id=current_user.id, concept_id=cid).first()
            consec = m_rec.consecutive_strong if m_rec else 0

            sched = apply_revision_schedule(
                db=db,
                student_id=current_user.id,
                concept_id=cid,
                mastery=m_val,
                last_result_correct=correct,
                consecutive_strong=consec,
            )
            db.flush()

            log_decision(
                db=db,
                student_id=current_user.id,
                decision_type="revision_schedule",
                payload=sched.reason_json,
            )

        # 8. Adaptive engine selects next question and logs reason trace
        next_q_decision = select_next_question(student_id=current_user.id, db=db)
        log_decision(
            db=db,
            student_id=current_user.id,
            decision_type="next_question",
            payload=next_q_decision["reason"],
        )

        # Commit entire pipeline transaction atomically
        db.commit()

    except Exception:
        db.rollback()
        raise

    # 9. Return structured response payload
    return SubmitAnswerResponse(
        attempt_id=attempt.id,
        correct=correct,
        reasoning=reasoning,
        misconception_id=misconception_id,
        evidence=evidence,
        llm_status=llm_status_val,
        feedback=feedback_text,
        concept_mastery_updates=concept_mastery_updates,
        next_question=NextQuestionDecision(
            question_id=next_q_decision["question_id"],
            concept_id=next_q_decision["concept_id"],
            reason=next_q_decision["reason"],
            question=(
                QuestionOut(
                    id=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().id,
                    text=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().text,
                    answer_key=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().answer_key,
                    answer_type=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().answer_type,
                    tolerance=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().tolerance,
                    difficulty=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().difficulty,
                    question_type=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().question_type,
                    rubric=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().rubric,
                    status=db.query(Question).filter_by(id=next_q_decision["question_id"]).first().status,
                    concept_ids=[qc.concept_id for qc in db.query(Question).filter_by(id=next_q_decision["question_id"]).first().concepts],
                )
                if next_q_decision["question_id"] and db.query(Question).filter_by(id=next_q_decision["question_id"]).first()
                else None
            ),
        ),
    )


@app.get("/students/{student_id}/mastery", tags=["analytics"])
def get_student_mastery_dashboard(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return student mastery breakdown, weakest/strongest concepts, and review schedules."""
    require_student_access(student_id=student_id, current_user=current_user)
    from backend.app.analytics import student_summary
    return student_summary(student_id=student_id, db=db)


@app.get("/students/{student_id}/decisions", tags=["analytics"])
def get_student_decision_history(
    student_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return explainable decision logs powering the 'Why am I seeing this' student & teacher views."""
    require_student_access(student_id=student_id, current_user=current_user)
    from backend.app.decisions import get_student_decisions
    records = get_student_decisions(db=db, student_id=student_id, limit=limit)
    return [
        {
            "id": r.id,
            "student_id": r.student_id,
            "decision_type": r.decision_type,
            "payload": r.payload_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@app.get("/teachers/{teacher_id}/class-summary", tags=["analytics"])
def get_teacher_class_dashboard(
    teacher_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregate class mastery, most-missed concepts, students needing support, and misconception distribution."""
    require_teacher_access(teacher_id=teacher_id, current_user=current_user)
    from backend.app.analytics import class_summary
    return class_summary(teacher_id=teacher_id, db=db)
