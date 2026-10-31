# Adaptive IQ (Wispr Flow)

> **Adaptive Exam-Prep Tutor with a Learner Model**
> CBSE Class 10 Physics: Chapter *Electricity*

Adaptive IQ stores knowledge rather than raw marks: per-student, per-concept mastery, the reasoning behind mistakes, and the reason for every decision the system makes.

---

## Clean-Clone Setup Instructions

### 1. Requirements
- Python 3.11+
- Git

### 2. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables
Create a local `.env` file (do NOT commit this file):
```bash
DATABASE_URL=sqlite:///./adaptive_iq.db
LLM_API_KEY=your_key_here
SECRET_KEY=dev_secret_key_change_in_production
```

### 4. Running Backend Tests
Execute pytest:
```bash
pytest backend/tests/ -v
```

### 5. Running the API Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```

---

## Project Structure
```
backend/
  app/           FastAPI app, routes, models, learner model, adaptive engine
  config/        mastery.json, evaluation.json, scheduling.json
  tests/         pytest test suite
content/
  electricity/   concepts.json, questions.jsonl, misconceptions.json
eval/
  human_labels.jsonl
  run_reasoning.py
  simulate_students.py
  policy_compare.py
  results/       script outputs
docs/
  ARCHITECTURE.md
  PREREGISTRATION.md
  DEMO_SCRIPT.md
  CLAIMS.md
```

## Team Protocols
Refer to [CONTRIBUTING.md](file:///home/dustin/Project/Wispr-Flow/CONTRIBUTING.md) for branch strategy, PR size limits, review policies, and commit prefixes.