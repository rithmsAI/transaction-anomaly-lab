"""Read-only SQL demonstration: summarize decisions without opening a public service."""
from contextlib import closing
import argparse,json,sqlite3
from pathlib import Path
def summarize(path,model_version=None):
    uri=Path(path).resolve().as_uri()+'?mode=ro'
    with closing(sqlite3.connect(uri,uri=True)) as db:
        return db.execute("SELECT model_version, COUNT(*), SUM(rules_alert), SUM(ml_alert) FROM decisions WHERE (? IS NULL OR model_version = ?) GROUP BY model_version",(model_version,model_version)).fetchall()
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('database'); parser.add_argument('--model-version')
    args=parser.parse_args(); print(json.dumps(summarize(args.database,args.model_version),indent=2))
