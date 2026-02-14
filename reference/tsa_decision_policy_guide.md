# TSA Decision Policy Guide

This guide explains what the TSA decision-policy gates do and how to tune them.

## Why This Exists

Model quality alone does not guarantee better trading results.  
Policy gates decide which model signals are allowed to become trades.

## Core Terms

- `prob_yes`: estimated probability that YES settles true.
- `side`: chosen side (`yes` if `prob_yes >= 0.5`, otherwise `no`).
- `side_price`: price paid for the chosen side.
  - if side is `yes`: `side_price = yes_price`
  - if side is `no`: `side_price = no_price = 1 - yes_price`
- `edge`: expected edge on chosen side.
  - `edge = side_probability - side_price`
- `spread`: YES bid/ask spread (`yes_ask - yes_bid`) when available.

## EntryPolicyConfig Fields

Defined in `/Users/jacobferraiolo/kalshi/src/kalshi/decision_policy.py`.

- `min_edge` (optional float)
  - Rejects trades where `edge < min_edge`.
  - `None` disables this gate.
- `no_trade_prob_band` (float, default `0.0`)
  - Blocks low-conviction probabilities around `0.5`.
  - Example: `0.02` blocks `prob_yes` in `[0.48, 0.52]`.
- `max_side_price` (optional float)
  - Rejects expensive entries above this side price.
  - `None` disables.
- `max_spread` (optional float)
  - Rejects trades if spread is wider than threshold.
  - If set and spread is missing, trade is rejected (`missing_spread`).

## Gate Evaluation Order

`evaluate_entry(...)` applies gates in this order:

1. `no_trade_prob_band`
2. `min_edge`
3. `max_side_price`
4. `max_spread` (or `missing_spread`)

The first failing gate becomes `reject_reason`.

## How Backtest Uses Policy

`/Users/jacobferraiolo/kalshi/src/kalshi/backtest_tsa.py`:

1. Builds probability per market (`model` or `heuristic`).
2. Maps to `side` and `side_probability`.
3. Computes `side_price`, `edge`, and `spread`.
4. Applies `EntryPolicyConfig`.
5. Records trade only if allowed.

If `entry_policy=None`, backtest uses permissive defaults (no active filters).

## Sweep Workflow

`/Users/jacobferraiolo/kalshi/src/kalshi/run_tsa_policy_sweep.py`:

1. Runs a no-gate baseline on a fixed window.
2. Runs a grid of policy configs.
3. Computes `pnl_total`, `max_drawdown`, `ece`, `trades`.
4. Marks `passes_gates` using baseline-relative checks:
   - hold/improve `pnl_total` (with `--pnl-tolerance`)
   - reduce/hold `max_drawdown`
   - preserve `ece` (with `--ece-tolerance`)
5. Selects best passing policy by:
   - highest `pnl_total`
   - then lowest `max_drawdown`
   - then lowest `ece`

## Example Commands

Backtest with explicit gates:

```bash
PYTHONPATH=src python3 -m kalshi.backtest_tsa \
  --start 2024-10-27 \
  --end 2026-02-01 \
  --prob-source heuristic \
  --min-edge 0.02 \
  --no-trade-prob-band 0.01 \
  --max-side-price 0.80 \
  --max-spread 0.12
```

Run policy sweep:

```bash
PYTHONPATH=src python3 -m kalshi.run_tsa_policy_sweep \
  --start 2024-10-27 \
  --end 2026-02-01 \
  --prob-source model \
  --min-edge-grid none,0.01,0.02 \
  --no-trade-band-grid 0.0,0.01,0.02 \
  --max-side-price-grid none,0.75,0.80 \
  --max-spread-grid none,0.10,0.15
```

## Practical Starting Ranges

- `min_edge`: `none`, `0.01`, `0.02`
- `no_trade_prob_band`: `0.00`, `0.01`, `0.02`
- `max_side_price`: `none`, `0.75`, `0.80`
- `max_spread`: `none`, `0.10`, `0.15`

Keep grids narrow first; expand only when results are stable across windows.
