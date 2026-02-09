# Reports Layout

This folder stores generated outputs.

- `baselines/`: pinned benchmark runs.
- `experiments/`: iterative candidate runs and comparisons.
- `archive/`: older outputs retained for traceability but not active analysis.
- `INDEX.md`: generated report directory index with "latest file" pointers.

Conventions:

- Keep new work under `baselines/`, `experiments/`, or `archive/`, not at `src/reports/` root.
- Name files with UTC-like timestamp suffix `YYYYMMDD_HHMMSS` when possible.
- Keep comparison reports alongside experiment outputs.
- Use stable workflow-first layout:
  - `experiments/tsa_model_compare/runs/<run_id>/`
  - `experiments/tsa_feature_ablation/`
  - `experiments/adhoc_backtests/`
  - `experiments/sanity_checks/`
- Within each `tsa_model_compare` run:
  - `heuristic/` for baseline run artifacts
  - `model/` for candidate run artifacts
  - `comparison.md` for the head-to-head summary

Maintenance:

- Rebuild index after adding/moving reports:
  - `PYTHONPATH=src python3 -m kalshi.build_reports_index`
- Move obsolete root-level reports into `archive/legacy_root_reports/`.
