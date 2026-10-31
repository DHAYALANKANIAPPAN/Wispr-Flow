"""Synthetic student simulation harness for learner model recovery testing.

Purpose:
    Simulates 50 synthetic students with known ground-truth concept masteries.
    Generates answers probabilistically based on true mastery (with noise).
    Runs student interactions through the full adaptive pipeline.
    Measures:
    1. Mean Absolute Error (MAE) between estimated and true mastery.
    2. Weakest concept recovery rate (percentage where estimated weakest equals true weakest).
    Outputs results strictly to eval/results/simulation.json.

Note:
    All simulated data is strictly labelled 'synthetic' in accordance with Section 7.
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.models import (
    User,
    Subject,
    Concept,
    ConceptPrerequisite,
    Question,
    QuestionConcept,
    Attempt,
    LearnerMastery,
    RevisionSchedule,
    DecisionLog,
)
from backend.app.main import seed_database_from_content
from backend.app.adaptive_engine import select_next_question
from backend.app.learner_model import apply_mastery_update
from backend.app.revision import apply_revision_schedule
from backend.app.evaluation import evaluate_answer

OUTPUT_DIR = PROJECT_ROOT / "eval" / "results"
OUTPUT_FILE = OUTPUT_DIR / "simulation.json"

NUM_STUDENTS = 50
QUESTIONS_PER_STUDENT = 15
RANDOM_SEED = 42


def setup_simulation_db():
    """Create in-memory database and seed with electricity content."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    seed_database_from_content(session)
    return session


def simulate_answer(true_mastery: float, question: Question) -> tuple[str, str]:
    """Generate probabilistic answer and explanation based on synthetic student's true mastery."""
    # Probability of correct answer is proportional to true mastery with noise
    prob_correct = max(0.05, min(0.95, true_mastery + random.gauss(0, 0.08)))
    is_correct = random.random() < prob_correct

    if is_correct:
        ans = question.answer_key
        explanation = f"Because the physical relationship indicates that the value is {ans} according to the governing formula."
    else:
        # Generate plausible wrong answer
        if question.answer_type == "numeric":
            try:
                val = float(question.answer_key)
                ans = str(val * 2 if val != 0 else 5.0)
            except ValueError:
                ans = "999"
        else:
            ans = "opposite"
        explanation = "Current increases because resistance is higher and more charge is pushed through the wire."

    return ans, explanation


def main():
    print("=" * 60)
    print("ADAPTIVE IQ: RECOVERY TEST (SYNTHETIC SIMULATION)")
    print("=" * 60)

    random.seed(RANDOM_SEED)
    session = setup_simulation_db()

    # Get target concepts
    concepts = [c.id for c in session.query(Concept).all()]
    print(f"Curriculum concepts ({len(concepts)}): {concepts}")
    print(f"Simulating {NUM_STUDENTS} synthetic students for {QUESTIONS_PER_STUDENT} questions each...")

    students_data = []
    total_absolute_error = 0.0
    total_estimates_count = 0
    weakest_matches_count = 0

    for i in range(1, NUM_STUDENTS + 1):
        s_id = f"synthetic_student_{i:03d}"
        # Assign ground-truth masteries drawn uniformly with fixed seed
        true_masteries: Dict[str, float] = {}
        for c in concepts:
            true_masteries[c] = round(random.uniform(0.15, 0.90), 2)

        true_weakest = min(true_masteries.items(), key=lambda x: x[1])[0]

        # Register synthetic student in DB
        db_student = User(
            id=s_id,
            role="student",
            name=f"Synthetic Student {i}",
            email=f"synthetic_{i}@simulation.local",
            password_hash="synthetic_hash",
        )
        session.add(db_student)
        session.commit()

        # Step through adaptive loop
        for step in range(QUESTIONS_PER_STUDENT):
            decision = select_next_question(student_id=s_id, db=session)
            qid = decision["question_id"]
            if not qid:
                break

            q = session.query(Question).filter_by(id=qid).first()
            if not q:
                break

            # Primary tested concept
            tested_cids = [qc.concept_id for qc in q.concepts]
            primary_cid = tested_cids[0] if tested_cids else "electric_current"
            c_true_m = true_masteries.get(primary_cid, 0.50)

            # Generate student answer
            s_ans, s_exp = simulate_answer(c_true_m, q)

            # Evaluate answer
            q_dict = {
                "id": q.id,
                "text": q.text,
                "answer_key": q.answer_key,
                "answer_type": q.answer_type,
                "tolerance": q.tolerance,
            }
            eval_res = evaluate_answer(q_dict, s_ans, s_exp)

            # Update learner mastery & revision schedule
            for cid in tested_cids:
                apply_mastery_update(
                    db=session,
                    student_id=s_id,
                    concept_id=cid,
                    evidence=eval_res["evidence"],
                )
                apply_revision_schedule(
                    db=session,
                    student_id=s_id,
                    concept_id=cid,
                    mastery=eval_res["evidence"],
                    last_result_correct=eval_res["correct"],
                )

            # Log attempt
            att = Attempt(
                student_id=s_id,
                question_id=q.id,
                student_answer=s_ans,
                explanation_raw=s_exp,
                explanation_clean=s_exp,
                correct=eval_res["correct"],
                reasoning=eval_res["reasoning"],
                misconception_id=eval_res["misconception_id"],
                evidence=eval_res["evidence"],
                llm_status=eval_res["llm_status"],
            )
            session.add(att)
            session.commit()

        # Compare estimated mastery against true ground truth
        estimated_records = (
            session.query(LearnerMastery)
            .filter(LearnerMastery.student_id == s_id)
            .all()
        )
        estimated_masteries = {r.concept_id: r.mastery for r in estimated_records}

        student_error = 0.0
        for c in concepts:
            est_m = estimated_masteries.get(c, 0.50)
            err = abs(est_m - true_masteries[c])
            student_error += err
            total_absolute_error += err
            total_estimates_count += 1

        student_mae = round(student_error / len(concepts), 4)

        # Evaluate weakest concept recovery
        estimated_weakest = min(
            ((c, estimated_masteries.get(c, 0.50)) for c in concepts),
            key=lambda x: x[1],
        )[0]

        is_weakest_recovered = (estimated_weakest == true_weakest)
        if is_weakest_recovered:
            weakest_matches_count += 1

        students_data.append({
            "student_id": s_id,
            "type": "synthetic",
            "true_masteries": true_masteries,
            "estimated_masteries": estimated_masteries,
            "true_weakest": true_weakest,
            "estimated_weakest": estimated_weakest,
            "weakest_recovered": is_weakest_recovered,
            "mae": student_mae,
        })

    overall_mae = round(total_absolute_error / total_estimates_count, 4)
    weakest_recovery_rate = round(weakest_matches_count / NUM_STUDENTS, 4)

    simulation_results = {
        "status": "synthetic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "sample_size": NUM_STUDENTS,
        "questions_per_student": QUESTIONS_PER_STUDENT,
        "measured_metrics": {
            "mean_absolute_error_mae": overall_mae,
            "weakest_concept_recovery_rate": weakest_recovery_rate,
            "weakest_matches": weakest_matches_count,
            "total_students": NUM_STUDENTS,
        },
        "sample_synthetic_students": students_data[:5],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(simulation_results, f, indent=2)

    print("\nMEASURED SIMULATION RESULTS (SYNTHETIC):")
    print(f"- Total Simulated Students: {NUM_STUDENTS}")
    print(f"- Questions Completed Per Student: {QUESTIONS_PER_STUDENT}")
    print(f"- Overall Mean Absolute Error (MAE): {overall_mae:.4f}")
    print(f"- Weakest Concept Recovery Rate: {weakest_recovery_rate * 100:.2f}% ({weakest_matches_count}/{NUM_STUDENTS})")
    print(f"\nResults stored in: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
