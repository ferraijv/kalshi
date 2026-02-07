# AGENTS

Guidance for assistants working in this repo.

- **Project overview**: Kalshi trading framework with scripts under `src/kalshi/` and tests in `test/`.
- **Python version**: 3.9.x (current venv); dependencies in `requirements.txt`. Install with `python3 -m pip install -r requirements.txt`.
- **Tests**: Run from repo root with the source on `PYTHONPATH`: `PYTHONPATH=src python3 -m pytest`. Agents should run pytest after every code change.
- **Key files**: `src/kalshi/shared.py` (core helpers), strategy scripts in `src/kalshi/*.py`, TSA prediction helpers in `src/kalshi/create_next_week_prediction.py`.
- **Type hints/docstrings**: Recent changes added type hints and function-level docstrings; keep new code consistent.
- **Secrets**: `.env` and AWS credentials are sensitive; do not log or commit them.
