# Validation extension: observed results

On seed 42, the existing benchmark reproduces upstream average precision: rules 0.6493, Isolation Forest 0.5234. Rules find 81 of 112 synthetic anomalies, with 87 false positives. Isolation Forest finds 65, with 98 false positives. Thresholds are calibrated independently for an approximate 5% review budget; observed test alert rates are 5.60% and 5.43%. A calibrated budget is not a guarantee on new data.

Five nonoverlapping seed triplets (42/43/44, 142/143/144, 242/243/244, 342/343/344, 442/443/444) test repeatability under independently regenerated data. Rules exceed Isolation Forest AP in all five runs. This descriptive result is specific to the simulator; rules share its anomaly assumptions.

| Base seed | Rules AP | Isolation Forest AP | Paired rules-minus-ML AP 95% interval |
|---|---:|---:|---:|
| 42 | 0.6493 | 0.5234 | 0.0559 to 0.1992 |
| 142 | 0.7011 | 0.5249 | 0.1006 to 0.2424 |
| 242 | 0.6709 | 0.4352 | 0.1532 to 0.3054 |
| 342 | 0.7378 | 0.4969 | 0.1592 to 0.3203 |
| 442 | 0.6877 | 0.5143 | 0.0978 to 0.2455 |

Intervals use 300 paired stratified bootstrap replicates per run. They condition on a fitted model and the observed class mix; they do not capture full training uncertainty or establish real-world fraud performance. The frozen split design and test definitions were selected before reading these results.

An all-normal prediction achieves roughly 96% accuracy here while finding no anomalies. That is why average precision, precision/recall, false alarms, misses and actual review rate carry more meaning than accuracy. Secondary ROC-AUC and AP lift over prevalence are included in validation_audit.json.

The expanded suite passes 24 tests: all 18 original tests plus invalid-metric checks, paired-bootstrap identity, training-only fitting, test-label threshold invariance, read-only SQL filtering, and request connection closure. The last test follows a real Windows failure that exposed unclosed SQLite handles. API code and fixtures now close connections explicitly while preserving transaction commits/rollbacks. No public API or Docker container was deployed or verified in this session.

Next evidence: use an appropriately licensed real or richer sequential dataset; record decision-time features and label-availability time; split chronologically with a maturity gap, then validate entity handling. Current iid synthetic data cannot demonstrate these properties.
