"""Extend the existing baseline with prevalence and paired uncertainty evidence."""
from pathlib import Path
import json
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from lab import generate,fit_model,model_scores,rule_scores,threshold_for_budget,evaluate

def paired_ap_interval(y,rule,ml,seed=2026,repeats=300):
    # Stratified iid bootstrap, conditional on this test set, fitted model, and class mix.
    rng=np.random.default_rng(seed); groups=[np.flatnonzero(y==k) for k in (0,1)]
    if any(len(g)==0 for g in groups): raise ValueError('Both classes required')
    delta=[]
    for _ in range(repeats):
        idx=np.concatenate([rng.choice(g,len(g),replace=True) for g in groups])
        delta.append(average_precision_score(y[idx],rule[idx])-average_precision_score(y[idx],ml[idx]))
    return [float(v) for v in np.quantile(delta,[.025,.975])]

def run(output=Path('reports/validation_audit.json')):
    rows=[]
    for seed in [42,142,242,342,442]:
        train,_=generate(6000,seed); calibration,_=generate(2000,seed+1); test,y=generate(3000,seed+2)
        model=fit_model(train,seed)
        scorers={'rules':rule_scores,'isolation_forest':lambda x:model_scores(model,x)}
        row={'seed':seed,'split_seeds':[seed,seed+1,seed+2],'prevalence':float(y.mean()),'all_negative_accuracy':float(1-y.mean()),'models':{}}
        scores={}
        for name,scorer in scorers.items():
            threshold=threshold_for_budget(scorer(calibration),.05) # No labels, no test values.
            score=scorer(test); scores[name]=score
            metrics=evaluate(y,score,threshold)
            metrics['roc_auc_secondary']=float(roc_auc_score(y,score))
            metrics['ap_lift_over_prevalence']=metrics['average_precision']/row['prevalence']
            row['models'][name]=metrics
        row['paired_rules_minus_ml_ap_95pct_bootstrap']=paired_ap_interval(y,scores['rules'],scores['isolation_forest'],seed)
        rows.append(row)
    result={'experiment':'synthetic iid validation audit; not real fraud outcomes','bootstrap_scope':'stratified test-row bootstrap conditional on fitted model and observed prevalence; not training uncertainty','runs':rows}
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__': print(json.dumps(run(),indent=2))
