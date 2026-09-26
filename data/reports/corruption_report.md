# Corruption and Idempotent Repair Report

## Source and method

- Repair source: `data/raw/crossref_records.json`
- Repaired records were rebuilt from the saved raw snapshot with the normal cleaning pipeline; corrupted records were not used as repair input.
- All three evaluations use the saved baseline test set and separate vector collections.

## Baseline vs Corrupted vs Repaired

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Records | 24 | 23 | 24 |
| Evaluation questions | 10 | 10 | 10 |
| Retrieval hit rate | 100.0% | 60.0% | 100.0% |
| Mean token F1 | 1.000 | 0.579 | 1.000 |
| Judge accuracy | 100.0% | 50.0% | 100.0% |
| Mean judge score / 5 | 5.000 | 3.200 | 5.000 |
| Quality gate | PASS | FAIL | PASS |
| GX checks passed | 7/7 | 5/7 | 7/7 |
| Freshness SLA | PASS | FAIL | PASS |
| Stale rows | 1/24 | 9/23 | 1/24 |
| Stale ratio | 4.2% | 39.1% | 4.2% |

## Injected failures

| Scenario | Affected rows |
| --- | ---: |
| `drop_latest_records` | 5 |
| `blank_summary` | 2 |
| `inject_noise` | 3 |
| `truncate_title` | 3 |
| `stale_date` | 7 |
| `duplicate_rows` | 4 |

## Question-level impact

| Question | Type | Baseline hit | Corrupted hit | Repaired hit | Baseline F1 | Corrupted F1 | Repaired F1 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| test-01 | summary | Yes | Yes | Yes | 1.000 | 0.000 | 1.000 |
| test-02 | summary | Yes | No | Yes | 1.000 | 0.788 | 1.000 |
| test-03 | summary | Yes | Yes | Yes | 1.000 | 0.000 | 1.000 |
| test-04 | authors | Yes | No | Yes | 1.000 | 1.000 | 1.000 |
| test-05 | authors | Yes | Yes | Yes | 1.000 | 1.000 | 1.000 |
| test-06 | authors | Yes | Yes | Yes | 1.000 | 1.000 | 1.000 |
| test-07 | date | Yes | No | Yes | 1.000 | 0.000 | 1.000 |
| test-08 | date | Yes | No | Yes | 1.000 | 0.000 | 1.000 |
| test-09 | categories | Yes | Yes | Yes | 1.000 | 1.000 | 1.000 |
| test-10 | categories | Yes | Yes | Yes | 1.000 | 1.000 | 1.000 |

## Interpretation

- Retrieval hit rate: 100.0% → 60.0% → 100.0%.
- Mean token F1: 1.000 → 0.579 → 1.000.
- Quality gate: PASS → FAIL → PASS.
