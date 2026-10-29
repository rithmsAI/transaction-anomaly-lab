"""Local synthetic scoring service with authenticated scoring and SQL audit records."""
from contextlib import closing
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import sklearn

from lab import generate, fit_model, model_scores, rule_scores, threshold_for_budget


class Transaction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    event_id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    amount_usd: float = Field(ge=0, le=1e9)
    distance_km: float = Field(ge=0, le=50000)
    transactions_last_hour: int = Field(ge=0, le=100000)
    account_age_days: float = Field(ge=0, le=50000)

    def features(self):
        return np.array([[self.amount_usd, self.distance_km,
                          self.transactions_last_hour, self.account_age_days]])


class Decision(BaseModel):
    event_id: str
    model_version: str
    rules_score: float
    ml_score: float
    rules_alert: bool
    ml_alert: bool


def create_app(db_path=None, api_key=None):
    db_path = Path(db_path or os.environ.get('AUDIT_DB', 'runtime/audit.sqlite'))
    config_key = api_key if api_key is not None else os.environ.get('LAB_API_KEY', '')

    @asynccontextmanager
    async def lifespan(app):
        if len(config_key) < 16:
            raise RuntimeError('LAB_API_KEY must contain at least 16 characters')
        app.state.ready = False
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS decisions (
                event_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
                model_version TEXT NOT NULL, response_json TEXT NOT NULL,
                rules_alert INTEGER NOT NULL, ml_alert INTEGER NOT NULL,
                created_at TEXT NOT NULL)''')
        train, _ = generate(6000, 42)
        calibration, _ = generate(2000, 43)
        app.state.model = fit_model(train, 42)
        app.state.ml_threshold = threshold_for_budget(model_scores(app.state.model, calibration), .05)
        app.state.rules_threshold = threshold_for_budget(rule_scores(calibration), .05)
        # Cover scoring implementation, API calibration parameters and dependency versions.
        digest = hashlib.sha256(Path(__file__).read_bytes() + Path(__file__).with_name('lab.py').read_bytes()
                                + (sklearn.__version__ + np.__version__).encode()).hexdigest()[:12]
        app.state.version = 'synthetic-iforest-' + digest
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(title='Transaction Anomaly Lab API', version='0.2.0', lifespan=lifespan)

    def authorize(x_api_key: str | None = Header(default=None)):
        if not x_api_key or not hmac.compare_digest(x_api_key.encode(), config_key.encode()):
            raise HTTPException(401, 'Invalid API key')
        if not getattr(app.state, 'ready', False):
            raise HTTPException(503, 'Model is not ready')

    @app.get('/healthz')
    def health():
        return {'status': 'alive'}

    @app.get('/readyz')
    def ready():
        if not getattr(app.state, 'ready', False):
            raise HTTPException(503, 'Model is not ready')
        return {'status': 'ready'}

    @app.post('/score', response_model=Decision, dependencies=[Depends(authorize)])
    def score(transaction: Transaction):
        payload_hash = hashlib.sha256(transaction.model_dump_json().encode()).hexdigest()
        x = transaction.features()
        rules = float(rule_scores(x)[0])
        ml = float(model_scores(app.state.model, x)[0])
        result = Decision(event_id=transaction.event_id, model_version=app.state.version,
                          rules_score=rules, ml_score=ml,
                          rules_alert=rules >= app.state.rules_threshold,
                          ml_alert=ml >= app.state.ml_threshold)
        try:
            with closing(sqlite3.connect(db_path, timeout=5)) as db, db:
                # Serialize read+write so concurrent retries cannot create duplicates.
                db.execute('BEGIN IMMEDIATE')
                existing = db.execute('SELECT payload_hash, response_json FROM decisions WHERE event_id = ?',
                                      (transaction.event_id,)).fetchone()
                if existing:
                    if existing[0] != payload_hash:
                        raise HTTPException(409, 'event_id already used with different features')
                    return Decision.model_validate_json(existing[1])
                db.execute('INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (transaction.event_id, payload_hash, app.state.version, result.model_dump_json(),
                            int(result.rules_alert), int(result.ml_alert), datetime.now(timezone.utc).isoformat()))
            return result
        except sqlite3.Error:
            # Do not claim a decision was recorded when persistence fails.
            raise HTTPException(503, 'Audit storage unavailable') from None

    @app.get('/metrics', dependencies=[Depends(authorize)])
    def metrics():
        try:
            with closing(sqlite3.connect(db_path, timeout=5)) as db, db:
                row = db.execute('SELECT COUNT(*), COALESCE(SUM(rules_alert), 0), COALESCE(SUM(ml_alert), 0) FROM decisions').fetchone()
            return {'unique_events': row[0], 'rules_alerts': row[1], 'ml_alerts': row[2],
                    'active_model_version': app.state.version}
        except sqlite3.Error:
            raise HTTPException(503, 'Audit storage unavailable') from None

    return app


app = create_app()

