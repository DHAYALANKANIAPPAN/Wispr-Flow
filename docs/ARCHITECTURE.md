# Adaptive IQ: Architecture & System Design

Adaptive IQ is an intelligent learning system that evolves with every student answer. Unlike conventional quiz systems that merely store raw marks, Adaptive IQ stores knowledge: per-student, per-concept mastery, the reasoning behind mistakes, and the reason for every decision the system makes.

---

## 1. Scope & Syllabus Confirmation
- **Target Grade/Subject**: Class 10 Physics, CBSE Syllabus.
- **Chapter**: Electricity.
- **Target Concepts (7)**:
  1. `electric_current`: Electric Current ($I = Q/t$)
  2. `potential_difference`: Potential Difference ($V = W/Q$)
  3. `resistance`: Resistance & Factors Affecting Resistance ($R = \rho L / A$)
  4. `ohms_law`: Ohm's Law ($V = IR$)
  5. `series_circuits`: Resistors in Series ($R_{eq} = \sum R_i$)
  6. `parallel_circuits`: Resistors in Parallel ($1/R_{eq} = \sum 1/R_i$)
  7. `electrical_power`: Electrical Power and Heating Effect ($P = VI = I^2 R = V^2/R$)
- **Portability Contract**: The engine is content-agnostic. Adapting to another syllabus (e.g., Tamil Nadu State Board) requires updating content JSON files only; the backend code remains unchanged.

---

## 2. Core Pillars & Verification Standards
Every claim must pass one of the following validation gates:
1. **Explainable**: Every question presented, revision date scheduled, or misconception detected has an auditable trace in `decision_log`.
2. **Measured Reasoning**: LLM misconception and reasoning classifications are evaluated against a held-out, human-labelled consensus dataset (`eval/human_labels.jsonl`). Agreement is reported via Cohen's Kappa and percentage agreement.
3. **Recovery Test**: Synthetic learners with fixed ground-truth mastery are evaluated through the pipeline (`eval/simulate_students.py`). Mean absolute error (MAE) and weakest-concept recovery are measured.
4. **Policy Test**: Adaptive question selection is benchmarked against random question selection under identical synthetic student conditions (`eval/policy_compare.py`).

---

## 3. The Seven System Modules
1. **Diagnostic Engine**: Entry-point assessment; answers feed directly into the learner model via the standard pipeline.
2. **Knowledge Graph (NetworkX)**: Directed acyclic graph (DAG) of concepts and prerequisite relationships. Enforces prerequisite unlocks and rejects cycles at initialization.
3. **Learner Model**: Tracks per-student, per-concept mastery score in $[0.0, 1.0]$. Clamped updates via exponential moving average with evidence weighting.
4. **Adaptive Engine**: Selects the optimal next question based on review urgency, mastery gaps, difficulty stepping, and repetition suppression. Emits structured reason traces.
5. **Misconception Detector**: Classifies student verbal/textual explanations against a controlled, closed taxonomy of misconceptions or `NONE`. Fails closed if the LLM is unavailable or outputs malformed data.
6. **Revision Scheduler**: Implements spaced repetition intervals based on current mastery and correctness history.
7. **Analytics**: Computes student and class aggregates strictly from stored relational records without on-the-fly mutations or mocks.

---

## 4. The Unified Answer Pipeline Data Flow
Every answer submission follows a strictly atomic, 9-step transaction:

```
[Student Submission: Answer + Explanation (Typed/Wispr Flow Voice)]
                           │
                           ▼
 1. Normalize Explanation (strip fillers, whitespace normalization, preserve raw text)
                           │
                           ▼
 2. Deterministic Correctness Check (Tolerance-based numeric or normalized text match; NEVER LLM)
                           │
                           ▼
 3. LLM Reasoning Classification (Sound / Weak / None + Controlled Misconception ID or NONE)
    * If explanation < 5 words -> reasoning='none', misconception_id=None
    * If LLM fails/malformed -> fail closed (reasoning='none', misconception_id=None, status='unavailable'|'invalid_output')
                           │
                           ▼
 4. Evidence Score Computation (Lookup from config/evaluation.json based on correct + reasoning)
                           │
                           ▼
 5. Learner Model Update (update_mastery per concept tested by the question)
                           │
                           ▼
 6. Attempt Record Persisted (Full trace: answers, clean/raw explanation, reasoning, misconception, status)
                           │
                           ▼
 7. Revision Schedule Updated (Next review date computed and persisted per updated concept)
                           │
                           ▼
 8. Adaptive Next Question Selected (Reason trace logged to decision_log)
                           │
                           ▼
 9. Return Response Payload (Correctness, student-facing feedback, misconception ID, next question, reason trace)
```

If any database persistence operation fails, the transaction rolls back completely to prevent state drift.

---

## 5. Fixed Contracts & Controlled Misconceptions

### Mastery Update Formula
```python
def update_mastery(m_old: float, evidence: float, alpha: float) -> float:
    # Prototype formula. Not a validated Bayesian estimate.
    m_new = m_old + alpha * (evidence - m_old)
    return max(0.0, min(1.0, m_new))
```
- Initial unseen concept mastery: `0.50` (read from `backend/config/mastery.json`).
- Default `alpha`: `0.20`.

### Controlled Misconception List
The LLM can only select from this controlled list:
- `MC_PROPORTIONAL_I_R`: Believes current and resistance are directly proportional ($I \propto R$).
- `MC_RESISTANCE_RISES_WITH_I`: Believes resistance increases when current increases at constant $V$.
- `MC_CURRENT_USED_UP`: Believes electric current is consumed or used up by circuit components.
- `MC_VOLTAGE_SPLITS_PARALLEL`: Believes voltage divides across parallel branches.
- `MC_POWER_IS_ENERGY`: Confuses electrical power (Watts) with electrical energy (Joules).
- `NONE`: No misconception detected (sound, incomplete, or ambiguous reasoning).

---

## 6. Database Schema Design (SQLAlchemy)
The system uses relational tables supporting SQLite (development) and PostgreSQL (production):
- `users`: ID, role (`student` | `teacher`), name, email, password_hash, created_at.
- `subjects`: ID, name.
- `concepts`: ID, subject_id, name, description.
- `concept_prerequisites`: concept_id, prerequisite_id.
- `questions`: ID, text, answer_key, answer_type (`numeric` | `text`), tolerance, difficulty (`1` | `2` | `3`), question_type (`conceptual` | `numerical`), rubric, status (`draft` | `approved`), reviewed_by.
- `question_concepts`: question_id, concept_id.
- `attempts`: ID, student_id, question_id, session_id, student_answer, explanation_raw, explanation_clean, correct, reasoning, misconception_id, evidence, llm_status, created_at.
- `learner_mastery`: student_id, concept_id, mastery, consecutive_strong, attempts_count, updated_at.
- `misconceptions`: ID, attempt_id, misconception_id, evidence_text, created_at.
- `revision_schedule`: student_id, concept_id, due_date, reason_json.
- `decision_log`: ID, student_id, decision_type, payload_json, created_at.

---

## 7. Decision Trace Catalog
All algorithmic decisions are logged into `decision_log` with one of the following structured schemas:
- `next_question`: `{"rule": "revision_due" | "weakest_concept" | "no_eligible_question", "concept": str, "mastery": float, "detail": str}`
- `revision_schedule`: `{"rule": str, "days_until_review": int, "mastery": float, "last_result_correct": bool}`
- `misconception_flag`: `{"misconception_id": str, "evidence_text": str, "attempt_id": str}`
