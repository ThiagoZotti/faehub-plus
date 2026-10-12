import hashlib
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import academic_core
import account_ownership
import account_enrollment
import database as db
import p1_operations as operations
from app import app
from director import account_access, access_version, init_director


class NavigationOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, 'DB_PATH', Path(cls.temp.name) / 'navigation.db')
        cls.db_patch.start()
        db.init_db()
        init_director()
        db.seed_teacher_assignments()
        academic_core.sync_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def client(self, username='gilberto', role='admin'):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(username=username, role=role, auth_version=access_version(username),
                           profile_photo_revision='', profile_photo_checked=time.time())
            if role == 'aluno':
                session['aluno_id'] = '23081'
        return client

    def trace(self, fn):
        statements = []
        original = sqlite3.connect
        def connect(*args, **kwargs):
            conn = original(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            return conn
        with patch.object(sqlite3, 'connect', side_effect=connect):
            result = fn()
        return result, [s for s in statements if s.lstrip().upper().startswith('SELECT')]

    def test_director_query_budgets_and_no_unneeded_catalog(self):
        client = self.client()
        for route, budget in [('/painel', 8), ('/usuarios', 8), ('/configuracoes', 4), ('/relatorios', 8)]:
            with self.subTest(route=route):
                response, selects = self.trace(lambda: client.get(route))
                self.assertEqual(response.status_code, 200)
                self.assertLessEqual(len(selects), budget)
                self.assertFalse(any('FROM academic_years ORDER' in sql for sql in selects))

    def test_live_revocation_still_applies_on_next_request(self):
        client = self.client('aline', 'professor')
        self.assertEqual(client.get('/painel').status_code, 200)
        with db.connection() as conn:
            conn.execute("UPDATE users SET active=FALSE WHERE username='aline'")
        try:
            self.assertEqual(client.get('/painel').status_code, 302)
            with client.session_transaction() as session:
                self.assertNotIn('role', session)
        finally:
            with db.connection() as conn:
                conn.execute("UPDATE users SET active=TRUE WHERE username='aline'")

    def test_owner_join_matches_authoritative_owner_state(self):
        with db.connection() as conn:
            conn.executemany('INSERT INTO enrollment_settings(key,value) VALUES(?,?)',
                             [('system_owner_username', 'gilberto'), ('system_owner_email', 'owner@example.com')])
            conn.execute("INSERT INTO account_identities VALUES('gilberto','owner@example.com',NULL)")
        try:
            for verified, email, active in [(None, 'owner@example.com', True),
                                             (123, 'owner@example.com', True),
                                             (123, 'wrong@example.com', True),
                                             (123, 'owner@example.com', False),
                                             (0, 'owner@example.com', True)]:
                with db.connection() as conn:
                    conn.execute("UPDATE account_identities SET email=?,verified_at=? WHERE username='gilberto'", (email, verified))
                    conn.execute("UPDATE users SET active=? WHERE username='gilberto'", (active,))
                access, queries = self.trace(lambda: account_access('gilberto'))
                self.assertEqual(access['is_owner'], account_ownership.owner_state()['verified'])
                self.assertEqual(len(queries), 1)
                self.assertFalse(account_access('aline')['is_owner'])
        finally:
            with db.connection() as conn:
                conn.execute("DELETE FROM account_identities WHERE username='gilberto'")
                conn.execute("DELETE FROM enrollment_settings WHERE key IN ('system_owner_username','system_owner_email')")
                conn.execute("UPDATE users SET active=TRUE WHERE username='gilberto'")

    def test_badge_matches_capped_inbox_and_student_message_exclusion(self):
        with db.connection() as conn:
            conn.execute('DELETE FROM notification_reads')
            conn.execute('DELETE FROM notifications')
            conn.executemany('''INSERT INTO notifications(title,body,recipient,role_target,category)
                                VALUES('Fixture','Fixture',?,?,?)''',
                             [('thiago.zotti', None, 'mensagem' if n % 3 == 0 else 'sistema') for n in range(105)] +
                             [(None, 'todos', 'sistema'), (None, 'professor', 'sistema'),
                              ('aline', None, 'mensagem')])
            conn.execute("UPDATE notifications SET expires_at='2000-01-01 00:00:00' WHERE id=(SELECT MAX(id) FROM notifications)")
            conn.execute('INSERT INTO notification_reads(notification_id,username) SELECT MIN(id),? FROM notifications', ('thiago.zotti',))
        for username, role in [('thiago.zotti', 'aluno'), ('aline', 'professor'), ('gilberto', 'admin')]:
            inbox = operations.list_notifications(username, role)
            expected = sum(not n['is_read'] and not (role == 'aluno' and n['category'] == 'mensagem') for n in inbox)
            self.assertEqual(operations.notification_unread_count(username, role), expected)
        with patch.object(operations, 'notification_unread_count', side_effect=AssertionError('Inbox must be reused')):
            self.assertEqual(self.client('thiago.zotti', 'aluno').get('/comunicados').status_code, 200)

    def test_scoped_queries_match_legacy_python_filters(self):
        grades = db.load_grades()
        expected = [g for g in grades if g['student_id'] == '23081']
        self.assertEqual(db.load_grades(student_id='23081'), expected)
        self.assertEqual(db.load_grades(student_ids=[]), [])
        self.assertEqual(db.load_grades(student_ids=['23081'], discipline='Matemática'),
                         [g for g in expected if g['discipline'] == 'Matemática'])
        self.assertEqual(db.get_exercises(teacher='aline'), [e for e in db.get_exercises() if e['teacher'] == 'aline'])
        self.assertEqual(db.get_exercises(class_name='3110'), [e for e in db.get_exercises() if e['class_name'] == '3110'])
        exercises = {e['id']: e for e in db.get_exercises(include_archived=True)}
        self.assertEqual(db.get_submissions(teacher='aline'),
                         [s for s in db.get_submissions() if exercises[s['exercise_id']]['teacher'] == 'aline'])
        expected = [m for m in db.get_messages('thiago.zotti') if m['recipient'] == 'thiago.zotti']
        brief, queries = self.trace(lambda: db.dashboard_message_summary('thiago.zotti'))
        self.assertEqual(len(queries), 1)
        self.assertEqual([(m['id'], m['is_read']) for m in brief['messages']], [(m['id'], m['is_read']) for m in expected[:2]])
        self.assertEqual(brief['message_count'], len(expected))
        self.assertEqual(brief['unread_count'], sum(not m['is_read'] for m in expected))

    def test_message_overview_is_bounded_without_capping_counts(self):
        with db.connection() as conn:
            conn.executemany('''INSERT INTO messages(sender,recipient,subject,body,is_read)
                                VALUES('aline','thiago.zotti','Fixture','Fixture',?)''',
                             [(n % 2 == 0,) for n in range(110)])
        expected = [m for m in db.get_messages('thiago.zotti') if m['recipient'] == 'thiago.zotti']
        brief = db.dashboard_message_summary('thiago.zotti')
        self.assertEqual(len(brief['messages']), 2)
        self.assertEqual(brief['message_count'], len(expected))
        self.assertEqual(brief['unread_count'], sum(not m['is_read'] for m in expected))
        self.assertEqual(db.dashboard_message_summary('unknown'), dict(messages=[], message_count=0, unread_count=0))

    def test_picker_and_metrics_are_equivalent_to_full_loads(self):
        snapshot = academic_core.structure_snapshot()
        expected = [s['code'] for s in snapshot['subjects'] if s['active']]
        self.assertEqual(academic_core.active_subject_codes(), expected)
        all_students = [dict(id=s['registration'], nome=s['full_name']) for s in snapshot['students']]
        self.assertEqual(academic_core.student_directory(), all_students)
        self.assertEqual(academic_core.student_directory([]), [])
        self.assertEqual(academic_core.student_directory(['23081']), [s for s in all_students if s['id'] == '23081'])
        metrics, queries = self.trace(operations.p1_metrics)
        self.assertEqual(len(queries), 1)
        with db.connection() as conn:
            for key, source in [('diaries_pending', "class_diary_entries WHERE status='submitted'"),
                                ('documents_pending', "document_requests WHERE status IN ('requested','processing')"),
                                ('interventions_open', "pedagogical_interventions WHERE status!='closed'"),
                                ('calendar_upcoming', "calendar_events WHERE status='published' AND ends_at>=CURRENT_TIMESTAMP"),
                                ('recovery_pending', "password_recovery_requests WHERE status='requested'")]:
                self.assertEqual(metrics[key], conn.execute('SELECT COUNT(*) FROM ' + source).fetchone()[0])

    def test_content_version_is_stable_and_overrides_manual_staleness(self):
        from flask import url_for
        digest = hashlib.sha256(Path('static/performance.css').read_bytes()).hexdigest()[:16]
        with app.test_request_context():
            self.assertIn('?v=' + digest, url_for('static', filename='performance.css'))
            self.assertIn('?v=1-' + digest, url_for('static', filename='performance.css', v=1))

    def test_demo_reactivation_preserves_owner_personal_accounts_and_passwords(self):
        with db.connection() as conn:
            conn.executemany('INSERT INTO enrollment_settings(key,value) VALUES(?,?)',
                             [('system_owner_username', 'gilberto'), ('system_owner_email', 'owner@example.com'),
                              ('demos_disabled', '1')])
            conn.execute("INSERT INTO account_identities VALUES('gilberto','owner@example.com',123)")
            conn.execute("INSERT INTO account_identities VALUES('thiago.zotti','personal@example.com',123)")
            conn.execute("UPDATE users SET active=FALSE WHERE username IN ('aline','thiago.zotti')")
            original = conn.execute("SELECT password_hash FROM users WHERE username='aline'").fetchone()[0]
        try:
            with self.assertRaises(ValueError):
                account_enrollment.reactivate_demos('aline')
            plan = account_enrollment.reactivate_demos('gilberto')
            self.assertIn('gilberto', plan['preserved'])
            self.assertIn('thiago.zotti', plan['preserved'])
            self.assertIn('aline', plan['eligible'])
            self.assertFalse(account_access('thiago.zotti')['active'])
            self.assertTrue(account_access('aline')['active'])
            with db.connection() as conn:
                self.assertEqual(original, conn.execute("SELECT password_hash FROM users WHERE username='aline'").fetchone()[0])
            # Restart must not inject sample activities after reopening access.
            with db.connection() as conn:
                conn.execute('DELETE FROM submission_reviews')
                conn.execute('DELETE FROM submissions')
                conn.execute('DELETE FROM exercise_states')
                conn.execute('DELETE FROM exercises')
            db.init_db()
            self.assertEqual(db.get_exercises(include_archived=True), [])
        finally:
            with db.connection() as conn:
                conn.execute("DELETE FROM account_identities WHERE username IN ('gilberto','thiago.zotti')")
                conn.execute("DELETE FROM enrollment_settings WHERE key IN ('system_owner_username','system_owner_email','demos_disabled','demos_seed_blocked')")
                conn.execute("UPDATE users SET active=TRUE WHERE username='thiago.zotti'")
            db.init_db()  # Restore this class's fixtures for subsequent equivalence checks.


if __name__ == '__main__':
    unittest.main()
