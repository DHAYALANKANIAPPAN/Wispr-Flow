# Contributing Guidelines & Git Protocol

Both team members (Dhaya and Agii) must follow these rules strictly with no exceptions.

## 1. Branch Strategy
- `main` is protected. Nobody pushes directly to `main`. It requires PR approval and passing checks.
- `develop` is the active integration branch.
- Every feature or fix begins from a freshly pulled `develop`:
  ```bash
  git checkout develop && git pull
  git checkout -b <prefix>/<area>-<short-name>
  ```

### Allowed Branch Prefixes
- `feat/`: New feature or behavior
- `fix/`: Bug fix
- `test/`: Test additions or test modifications
- `docs/`: Documentation updates
- `data/`: Content, question bank, syllabus, human labels, or configuration updates
- `eval/`: Evaluation harness and benchmarking scripts

Examples:
- `feat/learner-mastery-update`
- `data/electricity-question-bank`
- `eval/reasoning-agreement`

## 2. Commit Standards
All commit messages must begin with a standardized prefix followed by a concise description:
`feat:`, `fix:`, `test:`, `docs:`, `data:`, `eval:`

Example:
`feat: implement update_mastery with clamping and test harness`

## 3. Pull Request (PR) Requirements
- **Size constraint**: Keep PRs focused. Any PR exceeding 400 changed lines requires written rationale in the PR description.
- **Verification evidence**: Every PR must explicitly state whether tests were run and provide the exact test command executed (e.g., `pytest backend/tests/test_learner_model.py -v`). If untested, state `"untested until run"` with an explicit reason.
- **Peer review**: Minimum 1 peer approval is mandatory before merging into `develop`.
  - Dhaya reviews Agii's PRs.
  - Agii reviews Dhaya's PRs.
  - Self-approval is strictly forbidden.
- **No secrets**: Never commit `.env`, API keys, tokens, or SQLite `.db` files.

## 4. Release Process
- On the final release deadline, Dhaya opens a single PR from `develop` into `main`.
- Merge into `main`, tag `v1.0`, and perform a clean-clone verification by following `README.md`.
- Any issues encountered during clean-clone verification are reported transparently in the PR.
