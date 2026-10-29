# Scoring service and operational behavior

The API is a local demonstration built around synthetic data. It is not a deployed financial system and its scores are not fraud probabilities.

## Start locally

Install all dependencies with `python -m pip install -r requirements-api.txt`.

Windows PowerShell:

```powershell
$env:LAB_API_KEY = python -c "import secrets; print(secrets.token_hex(24))"
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
export LAB_API_KEY="$(python -c 'import secrets; print(secrets.token_hex(24))')"
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Keep the key out of commits. Startup refuses missing or short keys. The service fits its small deterministic synthetic model once at startup; no untrusted serialized model is loaded. Readiness becomes available after model fitting and database initialization. Swagger documentation is at `http://127.0.0.1:8000/docs`; use the X-API-Key field on authenticated endpoints.

## API contract

| Endpoint | Authentication | Behavior |
|---|---|---|
| `GET /healthz` | None | Process liveness |
| `GET /readyz` | None | 200 when initialization is complete, otherwise 503 |
| `POST /score` | `X-API-Key` | Return both scores, alert decisions, and model version |
| `GET /metrics` | `X-API-Key` | SQL-derived counts of unique events and alerts |

Example JSON input:

```json
{"event_id":"synthetic-001","amount_usd":100.0,"distance_km":20.0,"transactions_last_hour":2,"account_age_days":600.0}
```

Inputs use strict types, bounds, and forbidden extra fields. Missing/wrong credentials return 401; invalid data returns 422. Scores are ranking signals. Alerts are determined using frozen thresholds from the seed-43 calibration dataset at a 5% target budget.

## Idempotency and SQL

An event ID identifies one scoring request. Repeating the same validated payload returns its original stored decision, including its original model version. Reusing that ID with different features returns 409. A SQLite primary key and `BEGIN IMMEDIATE` transaction serialize concurrent retries. Identical events still compute scores before the lookup; a future optimization could avoid that repeated compute.

The audit table stores an event ID, a payload hash, the decision, model version, and timestamp. It does not store raw feature values. IDs must be synthetic; hashes are not a guarantee of anonymization. Persistence failure returns 503 rather than pretending the audit succeeded.

`/metrics` reports all stored decisions, which can span model versions; it separately identifies the currently active version. It is an aggregate endpoint, not Prometheus monitoring. A useful SQL investigation is:

```sql
SELECT model_version, COUNT(*) AS events,
       AVG(rules_alert) AS rules_alert_rate,
       AVG(ml_alert) AS ml_alert_rate
FROM decisions
GROUP BY model_version;
```

## Container

```bash
docker build -t anomaly-lab .
docker run --rm -p 127.0.0.1:8000:8000 -e LAB_API_KEY -v anomaly-data:/data anomaly-lab
```

Set `LAB_API_KEY` in the host environment first. The image runs as UID 10001 and has a readiness health check. The named volume retains the audit database between restarts. CI builds the image, starts it, makes real HTTP scoring requests, and checks retry deduplication.

## Operational boundaries

This is a single-node demo using one shared API key and SQLite. It has no per-user authorization, key rotation service, TLS termination, rate limiting, request-body size cap, distributed model registry, or cloud deployment. Local binding is intentional. Before exposing it publicly, add these controls and select a concurrency/persistence design appropriate for the workload. Model fitting during startup is suitable only for this small simulator.

The model-version fingerprint covers API/scoring source and NumPy/scikit-learn versions; it is an audit aid, not a signed supply-chain artifact. Direct dependencies are pinned, but transitive packages and the container base image are not fully locked.

