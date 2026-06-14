# ERP tier ingest (prototype)

Meridian's demo graph is tier-1 heavy. This script ingests **BOM / tier-N edges** from CSV to address Flaws #12 and #13.

## CSV format

```csv
parent_supplier_id,child_supplier_id,tier,notes
detroit-motors-supply,acme-electronics-ltd,2,Auto OEM → tier-2 electronics
```

| Column | Description |
|--------|-------------|
| `parent_supplier_id` | Upstream supplier slug or Neo4j `Supplier.id` |
| `child_supplier_id` | Downstream supplier slug or Neo4j `Supplier.id` |
| `tier` | Relationship depth (2 or 3) |
| `notes` | Optional provenance text |

## Usage

```bash
# Preview
python scripts/ingest_erp_csv.py --file data/sample_erp_tiers.csv --dry-run

# Write to Neo4j (requires NEO4J_* env)
python scripts/ingest_erp_csv.py --file data/sample_erp_tiers.csv
```

## Graph model

Creates `(:Supplier)-[:SUPPLIES {tier, source: 'erp_csv'}]->(:Supplier)`.

Missing child nodes are stubbed with `country_iso: 'XX'` so completeness metrics reflect tier coverage.

## Completeness API

`GET /analytics/graph/health` returns:

- `tier2_link_count` — count of `SUPPLIES` edges with `tier >= 2`
- `completeness_score` — weighted blend of geo, events, ports, tier coverage

## Limitations

- Not a full ERP connector — CSV prototype only
- No automatic SAP/Oracle sync
- Tier depth not yet fed into SCRI `dependency_depth` feature (roadmap)

See `docs/LIMITATIONS.md` Layer B.
