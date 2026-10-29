from contextlib import closing
import sqlite3,tempfile,unittest
from pathlib import Path
from scripts.query_audit import summarize
class SqlTests(unittest.TestCase):
    def test_read_only_parameterized_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'audit.sqlite'
            with closing(sqlite3.connect(p)) as db, db:
                db.execute('CREATE TABLE decisions(model_version TEXT,rules_alert INTEGER,ml_alert INTEGER)')
                db.executemany('INSERT INTO decisions VALUES(?,?,?)',[('v1',1,0),('v1',0,1),('v2',0,0)])
            self.assertEqual(summarize(p,'v1'),[('v1',2,1,1)])
            self.assertEqual(summarize(p,"v1' OR 1=1 --"),[])
            self.assertFalse((Path(temp)/'missing.sqlite').exists())
            with self.assertRaises(sqlite3.OperationalError): summarize(Path(temp)/'missing.sqlite')
