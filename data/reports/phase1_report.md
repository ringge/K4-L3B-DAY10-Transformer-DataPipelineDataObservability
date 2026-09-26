# Phase 1 Baseline Report

## Run Summary

| Item | Value |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-03-30,has-abstract:true |
| Records loaded | 24 |
| Records cleaned | 24 |
| Run time (UTC) | 2026-09-26T03:48:18.825622+00:00 |

## Baseline Evaluation

| Metric | Value |
| --- | ---: |
| Samples | 10 |
| Retrieval hit rate | 100.0% |
| Mean token F1 | 1.000 |
| Judge accuracy | 100.0% |
| Mean judge score | 5.000 / 5 |

## Data Quality and Freshness

- Quality gate: **PASS**
- GX expectations passed: 7/7
- Freshness SLA: **PASS**
- Latest published: 2026-07-22
- Oldest published: 2026-03-28
- Stale records: 1/24 (4.2%)

## Artifacts

- `data/clean/papers_clean.csv` and `data/clean/papers_clean.json`
- `data/chroma/` baseline vector collection
- `data/eval/test_set.json`
- `data/results/baseline_metrics.json` and `data/results/baseline_answers.json`
- `data/quality/baseline_quality_report.json` and `data/quality/freshness_report.json`

Ragas: Set RUN_RAGAS=1 to enable the slower Ragas pass.
