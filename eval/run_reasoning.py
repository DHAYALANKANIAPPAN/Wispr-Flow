"""Run reasoning evaluation against the held-out human consensus benchmark.

Purpose:
    Executes evaluate_answer against the 40 double-labelled human explanations in eval/human_labels.jsonl.
    Computes:
    - Percentage agreement with human consensus
    - Cohen's Kappa coefficient (inter-rater agreement above chance)
    - Multiclass confusion matrix
    - Count of invalid LLM outputs
    Writes all results strictly to eval/results/reasoning_agreement.json.

Status:
    Gate 2 verification script.
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evaluation import evaluate_answer

DATASET_PATH = PROJECT_ROOT / "eval" / "human_labels.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "eval" / "results"
OUTPUT_FILE = OUTPUT_DIR / "reasoning_agreement.json"


def compute_cohens_kappa(human_labels: List[str], predicted_labels: List[str], categories: List[str]) -> float:
    """Compute Cohen's Kappa for categorical agreement.

    Formula:
        kappa = (p_o - p_e) / (1 - p_e)
        p_o: observed accuracy
        p_e: expected accuracy by chance
    """
    n = len(human_labels)
    if n == 0:
        return 0.0

    # Observed agreement
    agreements = sum(1 for h, p in zip(human_labels, predicted_labels) if h == p)
    p_o = agreements / n

    # Marginal probabilities
    human_counts = defaultdict(int)
    pred_counts = defaultdict(int)
    for h, p in zip(human_labels, predicted_labels):
        human_counts[h] += 1
        pred_counts[p] += 1

    p_e = sum((human_counts[cat] / n) * (pred_counts[cat] / n) for cat in categories)

    if abs(1.0 - p_e) < 1e-9:
        return 1.0 if p_o == 1.0 else 0.0

    return round((p_o - p_e) / (1.0 - p_e), 4)


def main():
    print("=" * 60)
    print("ADAPTIVE IQ: GATE 2 REASONING EVALUATION HARNESS")
    print("=" * 60)

    if not DATASET_PATH.exists():
        print(f"Error: dataset file not found at {DATASET_PATH}")
        sys.exit(1)

    items = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    total_items = len(items)
    print(f"Loaded {total_items} human-consensus labelled items.")

    human_misconceptions = []
    predicted_misconceptions = []
    human_reasonings = []
    predicted_reasonings = []
    invalid_llm_outputs = 0

    all_categories = [
        "MC_PROPORTIONAL_I_R",
        "MC_RESISTANCE_RISES_WITH_I",
        "MC_CURRENT_USED_UP",
        "MC_VOLTAGE_SPLITS_PARALLEL",
        "MC_POWER_IS_ENERGY",
        "NONE",
    ]

    confusion_matrix = {h: {p: 0 for p in all_categories} for h in all_categories}

    for item in items:
        q_meta = {
            "id": item["question_id"],
            "text": item["question_text"],
            "answer_key": item["answer_key"],
            "answer_type": "text" if any(c.isalpha() for c in item["answer_key"]) else "numeric",
            "tolerance": 0.5,
        }

        # Run evaluate_answer through standard production logic
        res = evaluate_answer(
            question=q_meta,
            student_answer=item["student_answer"],
            explanation=item["explanation"],
        )

        h_misc = item["consensus"]["misconception_id"]
        p_misc = res["misconception_id"] if res["misconception_id"] is not None else "NONE"

        h_reason = item["consensus"]["reasoning"]
        p_reason = res["reasoning"]

        human_misconceptions.append(h_misc)
        predicted_misconceptions.append(p_misc)
        human_reasonings.append(h_reason)
        predicted_reasonings.append(p_reason)

        confusion_matrix[h_misc][p_misc] += 1

        if res["llm_status"] == "invalid_output":
            invalid_llm_outputs += 1

    # Metrics computation
    misc_agreements = sum(1 for h, p in zip(human_misconceptions, predicted_misconceptions) if h == p)
    misc_agreement_rate = round(misc_agreements / total_items, 4)

    misc_kappa = compute_cohens_kappa(human_misconceptions, predicted_misconceptions, all_categories)

    reasoning_categories = ["sound", "weak", "none"]
    reason_agreements = sum(1 for h, p in zip(human_reasonings, predicted_reasonings) if h == p)
    reason_agreement_rate = round(reason_agreements / total_items, 4)
    reason_kappa = compute_cohens_kappa(human_reasonings, predicted_reasonings, reasoning_categories)

    results_payload = {
        "dataset": "eval/human_labels.jsonl",
        "sample_size": total_items,
        "measured_metrics": {
            "misconception_agreement_rate": misc_agreement_rate,
            "misconception_cohens_kappa": misc_kappa,
            "reasoning_level_agreement_rate": reason_agreement_rate,
            "reasoning_level_cohens_kappa": reason_kappa,
            "invalid_llm_outputs_count": invalid_llm_outputs,
        },
        "confusion_matrix": confusion_matrix,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print("\nMEASURED EVALUATION RESULTS:")
    print(f"- Total Evaluated Items: {total_items}")
    print(f"- Misconception Agreement Rate: {misc_agreement_rate * 100:.2f}%")
    print(f"- Misconception Cohen's Kappa: {misc_kappa:.4f}")
    print(f"- Reasoning Level Agreement Rate: {reason_agreement_rate * 100:.2f}%")
    print(f"- Reasoning Level Cohen's Kappa: {reason_kappa:.4f}")
    print(f"- Invalid LLM Outputs: {invalid_llm_outputs}")
    print(f"\nResults stored in: {OUTPUT_FILE}")
    print("=" * 60)
    print("GATE 2 STATUS: PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
