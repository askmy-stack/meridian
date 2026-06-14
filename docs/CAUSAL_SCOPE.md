# Causal Inference Scope (D-005)

> **Policy:** Correlation ≠ causation in Meridian. User-facing **causal** language requires DoWhy verification.

**Decision record:** [D-005](../DECISIONS.md) · **Metrics:** [METRICS.md](./METRICS.md) · **Engine:** `src/causal/dowhy_engine.py`

## When we use each method

| Method | `causal_method` value | When it applies | User-facing label |
|--------|----------------------|-----------------|-------------------|
| Insufficient data | `insufficient_data` | Fewer than 5 paired Event→Supplier observations | No causal or correlation claim |
| Association only | `association_only` | 5–29 pairs, or DoWhy not installed, or &lt; `min_samples` | “Association only — not verified causation” + bootstrap CI |
| DoWhy verified | `dowhy_backdoor` | ≥30 pairs, DoWhy installed, refutation passes, \|effect\| &gt; 0.05 | “Causal link verified (DoWhy)” |
| Pipeline error | `dowhy_error` | DoWhy raised during estimation | Disclaimer only, no causal claim |

## Sample thresholds

Pipeline alerts use **graph-wide** Event→Supplier pairs from Neo4j:

```cypher
MATCH (e:Event)-[:AFFECTS]->(s:Supplier)
WHERE e.severity IS NOT NULL AND s.risk_score IS NOT NULL
RETURN e.severity, s.risk_score
ORDER BY e.ingested_at DESC
LIMIT $limit
```

| Setting | Default | Env override |
|---------|---------|--------------|
| Pair fetch limit | **100** | `CAUSAL_PAIR_LIMIT` |
| DoWhy minimum samples | **30** | `min_samples` in `assess_event_supplier_link()` |
| Minimum for any correlation | **5** | Hard-coded |

**`causal_sample_count`** on alert payloads reflects the number of pairs actually used in the assessment (after fetch, before truncation to paired length).

## Bootstrap confidence intervals (n &lt; 30)

When paired sample count is below the DoWhy threshold (`min_samples=30`), `assess_event_supplier_link()` computes a **Pearson correlation** plus a **bootstrap 95% percentile CI** (1000 resamples, fixed seed for reproducibility).

| Field | When present |
|-------|----------------|
| `causal_effect_size` | Point estimate correlation |
| `causal_correlation_ci_lower` | 2.5th percentile of bootstrap distribution |
| `causal_correlation_ci_upper` | 97.5th percentile |

Implementation: `bootstrap_correlation_ci()` in `src/causal/dowhy_engine.py`. Wired through `pipeline_alerts.causal_fields_for_alert()`.

**Export for offline analysis:**

```bash
make collect-causal-pairs
# → data/causal/event_supplier_pairs.csv
```

## What we never do

- Assert “X **causes** Y” from Pearson correlation alone.
- Show a green “verified causal” badge without DoWhy refutation.
- Use Granger causality or raw co-occurrence as a substitute for D-005.

## Scaling causal coverage

1. Increase `CAUSAL_PAIR_LIMIT` (default 100) as the graph grows — more pairs improve correlation stability and reach the DoWhy threshold faster.
2. Run `pipeline_refresh.py` regularly so `:AFFECTS` edges accumulate.
3. Install `dowhy` in production images when ready for verified claims (`requirements.txt` optional extra).

## Alert wire format

```json
{
  "causal_claim_allowed": false,
  "causal_method": "association_only",
  "causal_effect_size": 0.82,
  "causal_correlation_ci_lower": 0.61,
  "causal_correlation_ci_upper": 0.93,
  "causal_sample_count": 47,
  "causal_disclaimer": "Correlation observed — not a verified causal claim (D-005). ..."
}
```

Frontend: `AlertsView` badges map `causal_method` to tooltips referencing this doc and D-005.
