# Engineering decisions

## Evaluation contract

Three separately seeded streams produce 6,000 training, 2,000 calibration, and 3,000 test events. Labels never enter training, scoring, or threshold calibration. Test labels are used for metrics only. This prevents direct holdout leakage, but does not solve simulator bias: both methods and the generator are designed by the same project.

A quantile of calibration scores defines each alert threshold. All scores greater than or equal to the threshold are alerted. Ties can exceed the budget. If exactly K reviews were required, use a batch ranking policy with a documented deterministic tie breaker; that is a different operational contract from fixed-threshold scoring.

## Features and synthetic labels

Amounts follow a lognormal distribution, distances and account ages follow exponential distributions, and recent counts follow a Poisson distribution. Approximately 4% of events receive synthetic anomaly labels. Half of those have elevated amount/distance; half have burst activity and young accounts. Populations overlap. The label means an event came from an injected pattern, not that a real investigator confirmed fraud.

All features are assumed available at decision time. Real implementation would have to define how distance is computed and ensure the one-hour activity count excludes future events.

## Why the model loses here

Isolation Forest finds statistically unusual feature combinations. The baseline explicitly targets the two injected patterns. Some legitimate tail events look unusual to the model, while some injected events overlap the normal distribution. The benchmark favors the rules' prior knowledge. Report this openly rather than tuning repeatedly on the test set to manufacture an ML win.

## Reproducibility boundary

The generator and model use fixed seeds. Direct dependency versions and Python 3.12 are specified; transitive dependencies are not fully locked. Exact floating-point results can vary by environment. The bundled metrics were generated locally. The original experiment passed GitHub Actions after publication; use the current Actions run to inspect verification of subsequent changes.

## Useful next pull requests

1. Expand the included five-seed evaluation and report uncertainty without selecting favorable seeds.
2. Expand the included legitimate high-value purchase and travel stress test with additional shifts.
3. Compare a supervised model, using labels only in a separate training design.
4. Add customer histories with leakage-safe, past-only features and chronological splits.

## Security and data boundary

No credentials are needed. Inputs are generated arrays rather than uploaded customer data. The repository contains no copied business source or employer information. Never commit real transaction exports or secrets as demo inputs.
