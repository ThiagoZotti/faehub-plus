import sqlite3
import unittest
from unittest.mock import patch
from app import app
import database

class PerformanceTests(unittest.TestCase):
    def test_one_connection_per_request_and_closed_afterwards(self):
        client=app.test_client()
        with client.session_transaction() as s:s.update(username='gilberto',role='admin')
        original=database.sqlite3.connect;opened=[];statements=[]
        def connect(*args,**kwargs):
            conn=original(*args,**kwargs);opened.append(conn);conn.set_trace_callback(statements.append);return conn
        with patch.object(database.sqlite3,'connect',side_effect=connect):
            self.assertEqual(client.get('/configuracoes').status_code,200)
        self.assertEqual(len(opened),1)
        with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')
        self.assertFalse(any('FROM attendance' in sql or 'FROM grades' in sql or 'FROM activity_log' in sql for sql in statements))

    def test_static_cache_and_version(self):
        response=app.test_client().get('/static/performance.css?v=1')
        self.assertEqual(response.status_code,200)
        self.assertIn('max-age=31536000',response.headers['Cache-Control'])
        self.assertIn('immutable',response.headers['Cache-Control'])
        response.close()
        unversioned=app.test_client().get('/static/performance.css')
        self.assertNotIn('immutable',unversioned.headers['Cache-Control'])
        unversioned.close()
        from flask import url_for
        with app.test_request_context():self.assertIn('?v=',url_for('static',filename='performance.css'))

if __name__=='__main__':unittest.main()
