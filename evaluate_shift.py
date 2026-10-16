"""Repeat paired evaluations across seeds and stress-test frozen thresholds."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp
from lab import (FEATURES, generate, fit_model, model_scores, rule_scores,
                 threshold_for_budget, evaluate, validate)


def shift_legitimate(x, y):
    shifted = validate(x).copy()
    # Simulate more legitimate high-value purchases and travel, not more fraud.
    normal = y == 0
    shifted[normal, 0] *= 3
    shifted[normal, 1] += 100
    return shifted


def drift_report(reference, current):
    reference, current = validate(reference), validate(current)
    report = {}
    for i, name in enumerate(FEATURES):
        stat = float(ks_2samp(reference[:, i], current[:, i]).statistic)
        report[name] = {'ks_statistic': stat, 'review_shift': stat > .1}
    return report


def experiment(seeds):
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or any(s < 0 for s in seeds):
        raise ValueError('Provide at least two distinct nonnegative seeds')
    rows = []
    drift = []
    for seed in seeds:
        # SeedSequence isolates every split even when experiment seeds are consecutive.
        split_seeds = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(seed).spawn(3)]
        train, _ = generate(6000, split_seeds[0])
        calibration, _ = generate(2000, split_seeds[1])
        test, y = generate(3000, split_seeds[2])
        shifted = shift_legitimate(test, y)
        model = fit_model(train, seed)
        for name, scorer in [('rules', rule_scores), ('isolation_forest', lambda x: model_scores(model, x))]:
            threshold = threshold_for_budget(scorer(calibration), .05)
            for scenario, data in [('original', test), ('legitimate_behavior_shift', shifted)]:
                rows.append({'seed': seed, 'method': name, 'scenario': scenario,
                             **evaluate(y, scorer(data), threshold)})
        drift.append({'seed': seed, 'original': drift_report(calibration, test),
                      'shifted': drift_report(calibration, shifted)})
    summary = []
    for method in ('rules', 'isolation_forest'):
        for scenario in ('original', 'legitimate_behavior_shift'):
            group = [r for r in rows if r['method'] == method and r['scenario'] == scenario]
            summary.append({'method': method, 'scenario': scenario, **{
                metric: {'mean': float(np.mean([r[metric] for r in group])),
                         'sample_std': float(np.std([r[metric] for r in group], ddof=1))}
                for metric in ('average_precision', 'precision', 'recall', 'alert_rate', 'false_positives')}})
    return {'seeds': seeds, 'review_budget': .05, 'summary': summary, 'runs': rows,
            'drift': drift, 'note': 'Descriptive variability across synthetic seeds, not a confidence interval or real-world validation. KS > 0.1 is a heuristic effect-size flag, not a calibrated alarm.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, nargs='+', default=[101, 202, 303, 404, 505])
    parser.add_argument('--output', type=Path, default=Path('reports/shift_evaluation.json'))
    args = parser.parse_args()
    report = experiment(args.seeds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))
