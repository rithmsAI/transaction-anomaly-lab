"""Reproducible synthetic transaction anomaly experiment. No customer data."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, confusion_matrix

FEATURES = ('amount_usd', 'distance_km', 'transactions_last_hour', 'account_age_days')


def generate(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Independent fictional events, with overlapping normal/anomaly populations."""
    if n < 100:
        raise ValueError('At least 100 events are required')
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < .04).astype(int)
    x = np.column_stack((rng.lognormal(3.7, 1.1, n), rng.exponential(30, n),
                         rng.poisson(2, n), rng.exponential(600, n)))
    rows = np.flatnonzero(y)
    # Two anomaly patterns; neither is a guaranteed fraud label in real life.
    large = rows[:len(rows) // 2]
    burst = rows[len(rows) // 2:]
    x[large, 0] *= rng.uniform(3, 12, len(large))
    x[large, 1] += rng.exponential(350, len(large))
    x[burst, 2] += rng.poisson(7, len(burst))
    x[burst, 3] *= .08
    return x, y


def validate(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or len(x) == 0:
        raise ValueError('Expected a nonempty matrix with four feature columns')
    if not np.isfinite(x).all() or (x < 0).any():
        raise ValueError('Features must be finite and nonnegative')
    if not np.equal(x[:, 2], np.floor(x[:, 2])).all():
        raise ValueError('Transaction count must be an integer')
    return x


def rule_scores(x: np.ndarray) -> np.ndarray:
    x = validate(x)
    # Continuous severity permits threshold selection at a review budget.
    return np.maximum(x[:, 0] / 700 + x[:, 1] / 500,
                      x[:, 2] / 10 + 30 / (x[:, 3] + 30))


def fit_model(x: np.ndarray, seed: int) -> IsolationForest:
    # Log features compress heavy tails; no fitted preprocessing sees test data.
    return IsolationForest(n_estimators=200, random_state=seed, n_jobs=1).fit(
        np.log1p(validate(x)))


def model_scores(model: IsolationForest, x: np.ndarray) -> np.ndarray:
    # sklearn returns lower scores for anomalies; negate for ranking.
    return -model.score_samples(np.log1p(validate(x)))


def threshold_for_budget(scores: np.ndarray, budget: float) -> float:
    scores = np.asarray(scores, dtype=float)
    if not 0 < budget < 1:
        raise ValueError('Review budget must be between zero and one')
    if scores.ndim != 1 or len(scores) == 0 or not np.isfinite(scores).all():
        raise ValueError('Expected finite, nonempty scores')
    return float(np.quantile(scores, 1 - budget))


def evaluate(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    pred = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {'average_precision': float(average_precision_score(y, scores)),
            'precision': float(tp / max(tp + fp, 1)),
            'recall': float(tp / max(tp + fn, 1)),
            'alert_rate': float(np.mean(pred)),
            'true_positives': int(tp), 'false_positives': int(fp),
            'false_negatives': int(fn), 'true_negatives': int(tn),
            'threshold': threshold}


def run(output: Path, seed: int = 42, budget: float = .05) -> dict:
    # Separate random streams: model training, threshold calibration, final test.
    train, _ = generate(6000, seed)
    calibration, _ = generate(2000, seed + 1)
    test, labels = generate(3000, seed + 2)
    model = fit_model(train, seed)
    results = {'seed': seed, 'review_budget': budget,
               'split_sizes': {'train': 6000, 'calibration': 2000, 'test': 3000},
               'test_prevalence': float(labels.mean()), 'models': {}}
    scorers = {'Rules baseline': rule_scores,
               'Isolation Forest': lambda x: model_scores(model, x)}
    output.mkdir(parents=True, exist_ok=True)
    all_scores = {}
    for name, scorer in scorers.items():
        threshold = threshold_for_budget(scorer(calibration), budget)
        scores = scorer(test)
        all_scores[name] = scores
        results['models'][name] = evaluate(labels, scores, threshold)
    (output / 'metrics.json').write_text(json.dumps(results, indent=2) + '\n')
    with (output / 'sample_transactions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow((*FEATURES, 'synthetic_anomaly_label', 'rules_score', 'ml_score'))
        for i in range(30):
            writer.writerow((*test[i], labels[i], *(s[i] for s in all_scores.values())))
    plot_results(labels, all_scores, results, output)
    return results


def plot_results(labels, scores, results, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor='#f4f6f8')
    colors = ['#67758a', '#00847d']
    for (name, values), color in zip(scores.items(), colors):
        precision, recall, _ = precision_recall_curve(labels, values)
        axes[0].plot(recall, precision, label=name, color=color, linewidth=2)
    axes[0].axhline(labels.mean(), color='#bb653d', linestyle=':', label='Random ranking')
    axes[0].set(xlabel='Recall', ylabel='Precision', title='Ranking quality on held-out events')
    axes[0].legend(fontsize=9)
    names = list(results['models'])
    tp = [results['models'][n]['true_positives'] for n in names]
    fp = [results['models'][n]['false_positives'] for n in names]
    axes[1].bar(names, tp, color='#00847d', label='Synthetic anomalies found')
    axes[1].bar(names, fp, bottom=tp, color='#dcb18c', label='False alarms')
    axes[1].set(ylabel='Flagged events', title='Workload at calibrated 5% budget' if results['review_budget'] == .05 else 'Workload at calibrated review budget')
    axes[1].legend(fontsize=9)
    fig.suptitle('TRANSACTION ANOMALY LAB  /  synthetic benchmark', fontsize=16, fontweight='bold')
    fig.tight_layout()
    fig.savefig(output / 'benchmark.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports'))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--budget', type=float, default=.05)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error('seed must be nonnegative')
    if not 0 < args.budget < 1:
        parser.error('budget must be between zero and one')
    print(json.dumps(run(args.output, args.seed, args.budget), indent=2))
