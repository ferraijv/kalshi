# TSA Flow Diagrams

These diagrams explain the end-to-end TSA workflow at a glance.

## 1) High-Level TSA System Flow

```mermaid
flowchart LR
  A["TSA Raw Data (tsa_data.csv)"] --> B["Forecast Model\ncreate_next_week_prediction.py"]
  B --> C["Prediction Payload\n(prediction, trends, yoy)"]
  C --> D["Contract Feature Builder\ncontract_probability_model.py"]
  D --> E{"prob_source"}
  E -->|model| F["Logistic Model Inference\nP(YES wins)"]
  E -->|heuristic| G["Empirical Error CDF\nheuristic likelihood"]
  F --> H["Side Mapping\nmap_yes_probability_to_side"]
  G --> H
  H --> I["Order/Backtest Decision Layer"]
```

## 2) Model Training + Promotion Flow

```mermaid
flowchart TD
  A["Build Contract Dataset\nbuild_tsa_contract_dataset.py"] --> B["Train Logistic Model\ntrain_tsa_probability_model.py"]
  B --> C["Artifacts\n.joblib + .schema.json + .metadata.json"]
  C --> D["Ablation / Evaluation\nrun_tsa_feature_ablation.py"]
  D --> E["Backtest A/B\nheuristic vs model"]
  E --> F{"Promotion Gate"}
  F -->|pass| G["Update MODEL_REGISTRY.md"]
  F -->|pass| H["ACTIVE model artifact in src/data/models"]
  F -->|fail| I["Keep model as experiment"]
```

## 3) Strict Model-Mode Runtime Behavior

```mermaid
flowchart TD
  A["prob_source=model"] --> B["Load bundle + schema"]
  B --> C["Build runtime feature row"]
  C --> D{"Inference successful?"}
  D -->|yes| E["Use P(YES)"]
  D -->|no| F["Raise RuntimeError\n(no fallback)"]
```

## 4) Backtest Execution Flow

```mermaid
flowchart TD
  A["Date window"] --> B["Build weekly event tickers"]
  B --> C["For each event\ncompute run_date = event_date - 7d"]
  C --> D["Forecast as-of run_date"]
  D --> E["Fetch event markets + candles"]
  E --> F["Compute fill_price + realized outcome"]
  F --> G["Get probability\n(model or heuristic)"]
  G --> H["Map side + compute edge, pnl, brier, logloss"]
  H --> I["Write CSV + markdown report"]
```

## 5) Live TSA Trading Bot Flow

```mermaid
flowchart TD
  A["fetch_all_tsa_data"] --> B["create_next_week_prediction"]
  B --> C["get_likelihoods_of_each_contract\n(prob_source)"]
  C --> D{"Is Monday?"}
  D -->|yes| E["create_limit_orders_for_all_contracts"]
  D -->|no| F["Skip orders"]
  E --> G["Email run summary"]
  F --> G
```
