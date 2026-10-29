from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api import create_app

TEST_KEY = 'local-test-key-not-a-secret'
EVENT = {'event_id': 'synthetic-001', 'amount_usd': 100.0, 'distance_km': 20.0,
         'transactions_last_hour': 2, 'account_age_days': 600.0}


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp.name) / 'audit.sqlite'
        cls.app = create_app(cls.db_path, TEST_KEY)
        cls.client = TestClient(cls.app)
        cls.client.__enter__()
        cls.headers = {'X-API-Key': TEST_KEY}

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.temp.cleanup()

    def setUp(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute('DELETE FROM decisions')

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get('/healthz').status_code, 200)
        self.assertEqual(self.client.get('/readyz').status_code, 200)
        self.app.state.ready = False
        try:
            self.assertEqual(self.client.get('/readyz').status_code, 503)
            self.assertEqual(self.client.post('/score', json=EVENT, headers=self.headers).status_code, 503)
        finally:
            self.app.state.ready = True

    def test_authentication(self):
        for headers in ({}, {'X-API-Key': 'incorrect'}):
            self.assertEqual(self.client.post('/score', json=EVENT, headers=headers).status_code, 401)
            self.assertEqual(self.client.get('/metrics', headers=headers).status_code, 401)

    def test_request_connections_are_closed(self):
        original_connect = sqlite3.connect
        opened = []
        def tracked(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            opened.append(connection)
            return connection
        with patch('api.sqlite3.connect', side_effect=tracked):
            self.assertEqual(self.client.post('/score', json=EVENT, headers=self.headers).status_code, 200)
            self.assertEqual(self.client.get('/metrics', headers=self.headers).status_code, 200)
        self.assertEqual(len(opened), 2)
        for connection in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')

    def test_invalid_contracts(self):
        for change in ({'amount_usd': -1}, {'transactions_last_hour': 1.2},
                       {'transactions_last_hour': True}, {'amount_usd': '100'},
                       {'unexpected': 1}, {'event_id': "bad'; DROP TABLE decisions;"}):
            with self.subTest(change=change):
                self.assertEqual(self.client.post('/score', json=EVENT | change, headers=self.headers).status_code, 422)

    def test_retries_and_conflicting_ids(self):
        a = self.client.post('/score', json=EVENT, headers=self.headers)
        b = self.client.post('/score', json=EVENT, headers=self.headers)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.json(), b.json())
        conflict = self.client.post('/score', json=EVENT | {'amount_usd': 200.0}, headers=self.headers)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.client.get('/metrics', headers=self.headers).json()['unique_events'], 1)

    def test_concurrent_retries_record_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.client.post('/score', json=EVENT, headers=self.headers), range(4)))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertTrue(all(r.json() == results[0].json() for r in results))
        self.assertEqual(self.client.get('/metrics', headers=self.headers).json()['unique_events'], 1)

    def test_audit_failure_returns_unavailable(self):
        with patch('api.sqlite3.connect', side_effect=sqlite3.OperationalError('failure')):
            self.assertEqual(self.client.post('/score', json=EVENT, headers=self.headers).status_code, 503)
            self.assertEqual(self.client.get('/metrics', headers=self.headers).status_code, 503)

    def test_audit_survives_restart(self):
        first = self.client.post('/score', json=EVENT, headers=self.headers).json()
        with TestClient(create_app(self.db_path, TEST_KEY)) as restarted:
            self.assertEqual(restarted.post('/score', json=EVENT, headers=self.headers).json(), first)
            self.assertEqual(restarted.get('/metrics', headers=self.headers).json()['unique_events'], 1)

    def test_missing_key_fails_startup(self):
        with self.assertRaises(RuntimeError):
            with TestClient(create_app(self.db_path, '')):
                pass

