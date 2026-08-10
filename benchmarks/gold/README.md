# Reviewed Gold Set

Create one JSON file per source PDF. The filename must match the benchmark run directory.

```json
{
  "pdf": "source.pdf",
  "run_dir": "source",
  "clauses": [
    {"canonical_id": "1.1", "parent_id": "1", "page_start": 2, "heading_quote": "1.1 Services"}
  ],
  "references": [{"from": "1.1", "to": "2.1"}]
}
```

Review each rendered PDF page and record every explicit clause heading, hierarchy, and cross-reference. Run the evaluator with:

```bash
uv run python scripts/benchmark_contracts.py --runs /tmp/legal-sentinel-improved --output /tmp/legal-sentinel-improved/benchmark.json
```
