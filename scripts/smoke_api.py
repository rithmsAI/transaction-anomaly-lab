"""Exercise a running service over real HTTP; used by container CI."""
import json
import os
import time
import urllib.error
import urllib.request

base = 'http://127.0.0.1:8000'
for attempt in range(30):
    try:
        with urllib.request.urlopen(base + '/readyz', timeout=2) as response:
            if response.status == 200:
                break
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        time.sleep(1)
else:
    raise RuntimeError('Service did not become ready')
headers = {'Content-Type': 'application/json', 'X-API-Key': os.environ['LAB_API_KEY']}
event = {'event_id': 'container-smoke', 'amount_usd': 90.0, 'distance_km': 4.0,
         'transactions_last_hour': 1, 'account_age_days': 500.0}
results = []
for _ in range(2):
    request = urllib.request.Request(base + '/score', data=json.dumps(event).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        results.append(json.load(response))
assert results[0] == results[1], 'Retry changed decision'
with urllib.request.urlopen(urllib.request.Request(base + '/metrics', headers=headers), timeout=5) as response:
    assert json.load(response)['unique_events'] == 1, 'Retry created a duplicate'
print('Container HTTP scoring, authentication, and idempotent retry passed')

