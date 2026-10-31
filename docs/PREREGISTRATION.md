# Preregistration: Evaluation Hypotheses & Metric Specifications

> **Notice**: This document was formally recorded before the final benchmark and simulation runs to guarantee scientific integrity and prevent post-hoc hypothesis generation.

---

## 1. Study Scope & Target Objectives
Adaptive IQ models student mastery and misconception profiles within CBSE Class 10 Physics (Chapter: *Electricity*). The evaluation harness validates whether:
1. LLM reasoning classifications agree with human consensus on held-out authentic explanations.
2. The learner model recovers latent student mastery and weakest concepts under simulated stochastic response models.
3. The adaptive item selection policy provides targeted diagnostics compared to random item selection.

---

## 2. Preregistered Hypotheses

### Hypothesis 1: Misconception Classification Agreement
- **Hypothesis**: The system's misconception detector (combining fail-closed LLM reasoning with deterministic closed-vocabulary validation) will achieve an inter-rater agreement with human consensus of $\kappa \ge 0.60$ (substantial agreement on Landis & Koch scale).
- **Target Metric**: Cohen's Kappa ($\kappa$) and Percentage Agreement on `eval/human_labels.jsonl` ($N = 40$).
- **Held-out Distribution**: Exactly 40 double-labelled student explanations including at least 8 tricky "correct answer + weak explanation" cases and 8 "apparent trap but actually NONE" cases.

### Hypothesis 2: Learner Model Mastery Recovery
- **Hypothesis**: On a cohort of $N = 50$ synthetic students with uniformly distributed ground-truth concept masteries ($m^* \in [0.15, 0.90]$), the system's estimated mastery $\hat{m}$ will achieve a Mean Absolute Error (MAE) $\le 0.20$ after 15 adaptive responses.
- **Target Metric**:
  $$\text{MAE} = \frac{1}{N \cdot |C|} \sum_{s=1}^N \sum_{c \in C} |\hat{m}_{s,c} - m^*_{s,c}|$$
- **Seed**: Fixed seed (`42`) across all 50 synthetic students.

### Hypothesis 3: Policy Comparison (Adaptive vs Random)
- **Hypothesis**: The adaptive policy (prioritizing prerequisite DAG unlocks, overdue revisions, and weakest concept targeting) will demonstrate structured diagnostics compared to unconstrained random selection.
- **Trade-off Investigation**: Unconstrained random selection can sample locked concepts immediately, whereas adaptive curriculum learning adheres to prerequisite gates. The test measures the exact number of items needed to confirm the true weakest concept.

---

## 3. Protocol for Negative or Neutral Findings
In accordance with BASE CONTEXT Section 14:
- All reported numbers must originate from executable scripts outputting to `eval/results/`.
- No metric will be smoothed, adjusted, or post-hoc calibrated to fit the hypothesis.
- If agreement is low or random selection is faster, the result is reported as an empirical finding.
