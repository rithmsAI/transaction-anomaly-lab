"""Build a standalone explorer from real, reproducible synthetic evaluations."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import generate, fit_model, model_scores, rule_scores, threshold_for_budget, evaluate
ROOT = Path(__file__).resolve().parents[1]

def build():
    train, _ = generate(6000, 42)
    calibration, _ = generate(2000, 43)
    test, labels = generate(3000, 44)
    model = fit_model(train, 42)
    results = {}
    for name, scorer in [('Rules baseline', rule_scores), ('Isolation Forest', lambda x: model_scores(model, x))]:
        cal, scores = scorer(calibration), scorer(test)
        results[name] = {str(b): evaluate(labels, scores, threshold_for_budget(cal, b / 100)) for b in [1, 2, 5, 10, 20]}
    template = (ROOT / 'demo/template.html').read_text()
    (ROOT / 'demo/index.html').write_text(template.replace('__RESULTS__', json.dumps(results)))
    return results

if __name__ == '__main__':
    build()
    print('Built demo/index.html from seed-42 training, seed-43 calibration, seed-44 test.')

