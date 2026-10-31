# Adaptive IQ: Live Demo Script

> **Event Demonstration Protocol**
> Scenario: Two-Student Demonstration (Student A: Arun; Student B: Bhavna).
> All numbers shown on screen originate from database queries and `eval/results/`. Zero hardcoded values.

---

## Act 1: Student Profiles & Motivation (1 Minute)

- **Speaker**: "Most exam-prep quizzes only store marks. Adaptive IQ stores knowledge: per-student, per-concept mastery, the reasoning behind mistakes, and the reason for every decision the system makes."
- **Presenting Two Distinct Learners**:
  - **Student A (Arun)**: Conceptually strong in theory, but struggles with multi-step numerical calculations ($V = IR$, $Q = It$, $P = VI$).
  - **Student B (Bhavna)**: High algebraic aptitude in formulas, but harbors fundamental conceptual traps (e.g. believes voltage splits across parallel branches).

---

## Act 2: Login, Knowledge Graph & Gate 1 (1 Minute)

1. **Student Login**:
   - Arun logs in via `POST /auth/login`.
   - Client calls `GET /concepts`.
2. **Explainable Prerequisite DAG**:
   - The UI renders the 7 CBSE Electricity concepts:
     - Root concepts (**Electric Current**, **Potential Difference**, **Resistance**) are **UNLOCKED**.
     - Dependent concepts (**Ohm's Law**, **Series Circuits**, **Parallel Circuits**, **Electrical Power**) are **LOCKED** until prerequisites reach $0.60$ mastery.
   - *Judges' Check*: "Notice how dependent concepts cannot be accessed until prerequisites are confirmed. This is enforced by NetworkX DAG validation."

---

## Act 3: Voice-Enabled Reasoning with Wispr Flow (2 Minutes)

1. **Question Presented**:
   - Question: *"A student claims that doubling resistance at constant voltage will double the current. Is this correct?"* (Trap: `q_ohm_trap`).
2. **Dictating Explanation via Wispr Flow**:
   - Bhavna focuses the multi-line "Explain your reasoning" textarea and speaks into Wispr Flow:
     > *"Um, so basically current increases because you know resistance is higher and more resistance pushes more current through."*
   - Text is transcribed directly by Wispr Flow into the input field.
   - *Auditable Truth*: "Notice the system keeps the raw speech text unchanged while `normalize_explanation()` strips fillers ('um', 'uh', 'so basically') without modifying physics terms."
3. **Submission & The 9-Step Pipeline**:
   - Bhavna submits: Answer = `"correct"`.
   - **Deterministic Check**: Correctness is evaluated deterministically against the answer key (`"incorrect"`). The LLM never decides correctness! Result: `correct = False`.
   - **Misconception Detection**: Reasoning classified into closed vocabulary: `MC_PROPORTIONAL_I_R`.
   - **Evidence Score**: Computed as `0.0` from `config/evaluation.json`.
   - **Mastery Update**: Ohm's Law mastery drops from $0.50 \to 0.40$ ($m_{new} = 0.50 + 0.20 \cdot (0.0 - 0.50)$).
   - **Spaced Revision**: Scheduled for **0 days** (`incorrect_same_session`).

---

## Act 4: Explainability & The Decision Trace ("Why am I seeing this?") (1.5 Minutes)

1. **Next Question Recommendation**:
   - Client queries `GET /questions/next`.
   - System presents targeted remediation on Ohm's Law at difficulty level 1.
2. **The "Why am I seeing this?" Modal**:
   - Clicking the trace icon queries `GET /students/{id}/decisions`.
   - The UI displays the stored trace from `decision_log`:
     ```json
     {
       "rule": "revision_due",
       "concept": "ohms_law",
       "mastery": 0.40,
       "detail": "Immediate same-session revision triggered by incorrect response with misconception MC_PROPORTIONAL_I_R."
     }
     ```
   - *Judges' Check*: "Every question selection has an immutable reason logged in the database. No black boxes."

---

## Act 5: Teacher Dashboard & Analytics (1.5 Minutes)

1. **Teacher Login**:
   - Teacher logs in and views `GET /teachers/{id}/class-summary`.
2. **Actionable Insights from Stored Rows**:
   - **Class Mastery Distribution**: Average mastery per concept across all students.
   - **Most-Missed Concept**: `ohms_law` and `parallel_circuits` flagged automatically.
   - **Students Needing Support**: Flags Arun (needs numerical support) and Bhavna (concept traps).
   - **Misconception Breakdown**: Chart displaying frequencies of `MC_PROPORTIONAL_I_R` vs `MC_VOLTAGE_SPLITS_PARALLEL`.

---

## Act 6: Scientific Evaluation Harness & Verification (2 Minutes)

- **Speaker**: "In hackathons, teams often make unverified claims. We built an empirical evaluation harness with preregistered hypotheses and measured results."
- **Surface the 3 Measured Benchmarks**:
  1. **Measured Reasoning Agreement** (`eval/results/reasoning_agreement.json`):
     - **90.00% agreement** with human consensus across 40 double-labelled explanations.
     - **$\kappa = 0.7835$** (substantial agreement on Cohen's scale).
  2. **Synthetic Learner Recovery Test** (`eval/results/simulation.json`):
     - 50 synthetic students run through the real pipeline.
     - **Mean Absolute Error (MAE): 0.1615** against true latent mastery.
  3. **Policy Comparison** (`eval/results/policy_compare.json`):
     - 50 synthetic students benchmarked on Adaptive vs Random selection.
     - Demonstrates the empirical trade-off between prerequisite-gated curriculum learning ($13.40$ items) vs unconstrained search ($11.34$ items).
- **Conclusion**: "Simple, working, explainable code. No fake data, no unverified claims."
