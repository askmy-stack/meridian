# Architecture for contributors

This is the "where is it safe to change things" companion to
[`ARCHITECTURE.md`](../ARCHITECTURE.md).

## Module stability map

| Module | Phase | Stability | Tests |
|--------|-------|-----------|-------|
| `src/producers/` | 1 | 🟢 Stable | Unit (24 tests) |
| `src/schemas.py` | 1 | 🟢 Stable | Unit |
| `src/graph/` | 2 | 🟡 In progress | Partial unit |
| `src/ingestion/` | 2 | 🟡 In progress | Light |
| `src/api/` | 2/5 | 🟡 In progress | Unit + integration (added in Phase 7 audit) |
| `src/api/auth/` | 5 | 🟠 Needs review | Some |
| `src/entity_resolution/` | 2 | 🟠 Needs tests | None yet |
| `src/consumers/` | 2 | 🟠 Needs tests | None yet |
| `src/intelligence/` | 3 | 🔴 Stub-heavy | None |
| `src/simulation/` | 4 | 🔴 Stub-heavy | None |
| `src/alerting/` | 4 | 🟡 Functional | Unit |
| `src/forecasting/` | 4 | 🔴 Pure stub | None |
| `frontend/` | 5 | 🟡 Functional | None (e2e planned) |
| `terraform/` | 6 | 🟢 Reviewed | N/A |

Legend:
* 🟢 Stable — change with care, regression tests required
* 🟡 In progress — actively evolving, expect churn
* 🟠 Needs review — works but is under-tested or has known gaps
* 🔴 Stub / placeholder — most logic is mocked or hardcoded; expect to rewrite

## Where to make your first contribution

**If you want a fast win:**
* Frontend polish (any page in `frontend/src/pages/`)
* Documentation in `docs/` or `README.md`
* Adding test cases to `tests/unit/`

**If you want to learn the system:**
* Wire a new producer (e.g. NOAA weather) following `src/producers/gdelt_producer.py`
* Add a new field to `Supplier` and thread it through the API + graph
* Implement one of the open Tier 2 / Tier 3 audit items in `DECISIONS.md`

**Avoid these for first PRs:**
* `src/intelligence/` — model logic is in flux; coordinate first
* `src/forecasting/tgn_forecaster.py` — needs full reimplementation, not patches
* `terraform/` — operator-level changes; needs maintainer review

## Data flow (mental model)

```text
[GDELT/ACLED/AIS/NOAA] ──► Kafka topics
                              │
                              ▼
                  [src/consumers/entity_resolution]
                              │ (MERGE into Neo4j)
                              ▼
                          [Neo4j]
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    [intelligence/]   [simulation/]      [api/]
    classifier         monte_carlo        endpoints
    risk_scorer        propagation        /alerts /risk
    NER                                   /visualization
            │                 │                 │
            └─────────────────┼─────────────────┘
                              ▼
                        [alerting/slack]
                              │
                              ▼
                        [Slack + frontend]
```

## Key invariants

These hold across every change:

1. **Kafka is the only event bus.** No HTTP between ingestion services.
2. **Neo4j writes use MERGE.** Never plain CREATE for relationships.
3. **Risk scores include a SHAP explanation.** No black-box numbers.
4. **Monte Carlo runs ≥ 1000 iterations.** No point estimates.
5. **All ML experiments are tracked in MLflow.** No untracked runs.
6. **All secrets come from env vars.** No defaults that work in production.

If your change violates any of these, raise it in the PR description.

## Testing strategy

```text
tests/
├── unit/         ← fast, mocked, no Docker (run on every commit)
└── integration/  ← needs `docker compose up -d`, runs in CI
```

Add unit tests in the same module structure as the code they test:
`src/api/routes/alerts.py` ⇒ `tests/unit/test_alerts_route.py`.

Integration tests should be **deterministic** — never depend on live external
APIs. Use VCR cassettes or fixtures.
