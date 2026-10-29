# SIS310 validation extension: additions to the existing anomaly lab

## What was already present

Reviewed upstream main commit 374788e42276dce534b07a81d6db73e4a7721f75 on 2026-10-29: lab.py, api.py, evaluate_shift.py, README, modeling/API/shift tests, and service docs. The portfolio's index.html contained broad FinTech/API and ML entries, not these two named projects. This local working package reuses the lab rather than making a second detector. Upstream text/code has no chosen open-source license; this is an owner-requested working copy, not a relicensing.

## New evidence

1. `lab.evaluate` now rejects misaligned vectors, nonbinary labels, nonfinite scores/thresholds, and one-class evaluation sets. A deceptively valid-looking metric is worse than a clear failure.
2. `validation_audit.py` runs five separated seed triplets (no shared random stream between runs), adds the all-negative accuracy reference, AP lift over positive prevalence, secondary ROC-AUC, and a paired stratified bootstrap of rules-minus-ML AP.
3. New tests check the input contract, identical-ranking bootstrap, training-only fitting, and threshold invariance when test labels change. This last test is evidence against test-label leakage, not proof against every possible leakage route.
4. `scripts/query_audit.py` opens existing SQLite storage read-only, groups by model version, and binds filter values. Tests show injection-like input remains a literal filter and a missing file is not silently created.
5. An executed notebook exposes distributions, imbalance, benchmark output, and audit findings for coursework. Install `requirements-notebooks.txt` for notebook dependencies; `requirements-lock.txt` records the full verified environment.
6. Windows verification exposed open SQLite connections: a connection's transaction context manager does not close it. The API, SQL helper and fixtures now explicitly close connections; a new request-lifecycle test verifies closure. This fixes a resource leak without changing scoring or retry behavior.

Run `python -m unittest discover -s tests -v`, `python lab.py`, and `python validation_audit.py`. Inspect reports/validation_audit.json and reports/extension_findings.md. Keep the existing API rather than creating an additional service. Original tests cover validation, authentication, persistence, concurrent retries and storage failure; see SERVICE.md for local setup. Bind any manual demo to 127.0.0.1. Generate a fresh local API key; never put it in a notebook, commit, screenshot, or URL. Scores are anomaly rankings, not fraud probabilities. No real financial transactions are accepted in this exercise.

## Validation decisions step by step

Training fits Isolation Forest without labels. Calibration chooses an approximate review-capacity threshold without labels. Held-out test labels measure ranking and review outcomes once. Thresholds remain fixed for final evaluation. Average precision emphasizes rare positive ranking; precision/recall and confusion counts explain analyst workload. Accuracy alone can reward predicting every transaction as normal. ROC-AUC is secondary because it can conceal an impractical false-alarm burden.

Current fictional events have no account ID or timestamp, so temporal or customer-disjoint performance cannot honestly be claimed. Independent random splits match the simulator only. A licensed real dataset would require chronological train/calibration/test windows, a gap for label maturity, exclusion of post-event fields, and either entity-disjoint holdouts for new-account claims or strict as-of histories for returning-account claims. Do not randomly split repeated account histories or oversample before splitting. Add sampling or class weights inside training only if a future supervised approach requires it.

Bootstrap intervals condition on each fitted model and the observed test class mix. They describe synthetic test-row uncertainty, not population guarantees, business impact, or total training variability. Five-seed results are descriptive robustness evidence. Rules are advantaged by generator assumptions. Unusual does not mean fraudulent.

This extension is part of the public portfolio release. The repository retains its original benchmark and adds validation evidence and an explicit SQLite connection-closure fix. TEST_RESULTS.txt records 24 passing local tests: all 18 original tests and 6 added tests. GitHub Actions also exercises the container; inspect its current status before describing container verification as passing. No public scoring API is deployed. The browser case study is static and uses precomputed fictional-data results.
