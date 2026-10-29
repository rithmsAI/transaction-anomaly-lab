# Five-minute interview walkthrough

Use these prompts to prepare an explanation in your own words. Do not claim skills or implementation decisions you cannot explain yet.

1. **Problem (30 seconds).** Explain the limited review capacity and why false alarms matter.
2. **Run (60 seconds).** Run the test suite, then `python lab.py`. Open the benchmark image and metrics.
3. **Method (60 seconds).** Trace training, calibration, and test. Explain why test data must not select the threshold.
4. **Result (60 seconds).** Rules find 81 of 112 injected anomalies with 87 false alarms; the model finds 65 with 98 false alarms. Explain why the simulator favors rules.
5. **Tradeoff (45 seconds).** Reduce the budget using a separate output directory. Observe changes in recall and workload; do not promise the direction or size before running it.
6. **Next step (45 seconds).** Propose multiseed and shifted-data testing before making real-world claims.

## Questions to be ready for

- Why does a 5% calibration budget produce more than 5% alerts on the test set?
- Why is accuracy a weak headline for rare events?
- How does `-score_samples` differ from a fraud probability?
- What information is allowed at training, calibration, and evaluation time?
- Which synthetic assumptions favor the baseline?
- What would break if customers appeared repeatedly in the data?

## Learning exercise before publication

Change one normal-data assumption, run into a new output directory, and write a short observation. Keep the original benchmark unchanged. Being able to explain that experiment is more valuable than memorizing the README.

## Service extension

Run the API using `docs/SERVICE.md`. Explain 401, 409, 422, and 503 responses; show why a duplicate event produces one audit record. Read the concurrent retry test and explain how SQLite serialization protects it. Then explain why a frozen threshold can overload reviewers when legitimate behavior shifts. Be explicit that container CI is not proof of a cloud deployment.

