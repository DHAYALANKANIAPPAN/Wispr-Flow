# System Claims & Verification Registry

All claims regarding Adaptive IQ are cataloged below in compliance with Section 14 and Section 15. Every statement is strictly categorized as **[MEASURED]**, **[PLANNED]**, or **[HYPOTHESIS]** and referenced to its machine-generated artifact or implementation source.

---

## 1. Measured Claims ([MEASURED])

| Claim | Measured Value | Benchmark File / Source | Method / Sample |
| :--- | :--- | :--- | :--- |
| **Misconception Classification Agreement** | **90.00%** agreement with human consensus | [`eval/results/reasoning_agreement.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/reasoning_agreement.json) | 40 double-labelled human explanations (`eval/human_labels.jsonl`) |
| **Misconception Cohen's Kappa** | **$\kappa = 0.7835$** (substantial agreement) | [`eval/results/reasoning_agreement.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/reasoning_agreement.json) | 40 double-labelled human explanations |
| **Invalid LLM Output Rate** | **0 invalid outputs** (0%) | [`eval/results/reasoning_agreement.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/reasoning_agreement.json) | Evaluated over 40 structured queries |
| **Reasoning Level Agreement** | **32.50%** ($\kappa = 0.0000$) | [`eval/results/reasoning_agreement.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/reasoning_agreement.json) | Evaluated under fail-closed fallback mode |
| **Learner Mastery Recovery Error** | **$\text{MAE} = 0.1615$** (Mean Absolute Error) | [`eval/results/simulation.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/simulation.json) | 50 synthetic students over 15 adaptive items (`seed=42`) |
| **Weakest Concept Recovery Rate** | **24.00%** (12 of 50 synthetic students) | [`eval/results/simulation.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/simulation.json) | 50 synthetic students over 15 adaptive items |
| **Adaptive Item Budget to Weakest** | **13.40 questions** on average | [`eval/results/policy_compare.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/policy_compare.json) | 50 synthetic students comparing adaptive vs random |
| **Random Item Budget to Weakest** | **11.34 questions** on average | [`eval/results/policy_compare.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/policy_compare.json) | Same 50 synthetic students and seeds |
| **Curriculum Prerequisite Trade-off** | **$-18.17\%$** relative step speed | [`eval/results/policy_compare.json`](file:///home/dustin/Project/Wispr-Flow/eval/results/policy_compare.json) | Random samples locked concepts immediately; Adaptive respects prerequisite unlocks |
| **Backend Test Coverage** | **31 tests passing** (100% pass rate) | Pytest suite: `backend/tests/` | Covers auth, DAG, schema, learner model, decisions, pipeline, adaptive engine, revision |

---

## 2. Architecture & Design Claims ([PLANNED])

| Capability | Status | Implementation File | Verification Target |
| :--- | :--- | :--- | :--- |
| **Atomic 9-Step Pipeline** | Active / Production | [`backend/app/main.py`](file:///home/dustin/Project/Wispr-Flow/backend/app/main.py) | Verified in `backend/tests/test_pipeline.py` |
| **Fail-Closed Misconception Taxonomy** | Active / Production | [`backend/app/misconceptions.py`](file:///home/dustin/Project/Wispr-Flow/backend/app/misconceptions.py) | 5 controlled IDs + `NONE`; unknown IDs coerce to `NONE` |
| **Wispr Flow Voice Input Integration** | Planned (Phase 4) | Frontend textarea | Multi-line textarea keeps raw text and line breaks without clearing on blur |
| **PostgreSQL Deployment DB** | Planned (Deploy) | `backend/app/db.py` | Database URL toggle via `DATABASE_URL` |
| **Next.js & Recharts Dashboard** | Planned (Phase 4) | `frontend/` | Reads from `GET /students/{id}/mastery` and `GET /teachers/{id}/class-summary` |

---

## 3. Unverified Hypotheses ([HYPOTHESIS])

> [!WARNING]
> The following claims are strictly hypotheses. They have not been validated by empirical trials and must NOT be stated as proven in presentations or demos:

1. **Voice Input Efficacy**:
   - *Claim*: Dictating explanations via Wispr Flow improves conceptual recall or student engagement.
   - *Status*: **[HYPOTHESIS]** (Requires randomized control trial comparing dictated explanations vs typed explanations).
2. **Mastery Formula Validity**:
   - *Claim*: The exponential moving update rule ($m_{new} = m_{old} + \alpha(E - m_{old})$) accurately tracks true cognitive knowledge states.
   - *Status*: **[HYPOTHESIS]** (The formula is an engineering prototype, not a validated Bayesian Knowledge Tracing model).
3. **Long-Term Spaced Retention**:
   - *Claim*: The spaced revision scheduling intervals (1, 3, 7, 14 days) produce superior 30-day exam retention.
   - *Status*: **[HYPOTHESIS]** (Requires longitudinal student assessment data).
