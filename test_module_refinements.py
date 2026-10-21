"""Published times and account-scoped bulk reading, using a disposable DB."""
from pathlib import Path
from contextlib import contextmanager
import tempfile
import unittest
from unittest.mock import patch

import database as db
import p1_operations as operations
import school_timetable as timetable
from app import app
from director import init_director, access_version


class WeeklyPresentationTests(unittest.TestCase):
    def test_gaps_and_actual_times_are_not_shifted(self):
        rows = [dict(weekday=1, starts_at='07:00', ends_at='08:40', subject_name='Física'),
                dict(weekday=1, starts_at='10:40', ends_at='12:20', subject_name='Biologia'),
                dict(weekday=0, starts_at='09:00', ends_at='10:40', subject_name='Matemática')]
        view = timetable.week_view(rows)
        self.assertEqual([d['weekday'] for d in view['days']], list(range(5)))
        tuesday = view['days'][1]['segments']
        self.assertEqual([(s['kind'], s['starts_at'], s['ends_at']) for s in tuesday],
                         [('lesson','07:00','08:40'), ('free','08:40','10:40'), ('lesson','10:40','12:20')])
        self.assertEqual(tuesday[1]['minutes'], 120)
        self.assertEqual(tuesday[2]['row'], view['days'][0]['segments'][-1]['row'])
        self.assertEqual(rows[0]['ends_at'], '08:40')

    def test_sunday_only_appears_with_a_published_sunday_lesson(self):
        row = dict(weekday=6, starts_at='14:00', ends_at='15:00', subject_name='Aula publicada')
        view = timetable.week_view([row])
        self.assertEqual(view['days'][-1]['name'], 'Domingo')
        self.assertNotIn(5, [day['weekday'] for day in view['days']])
        self.assertEqual(len(timetable.grid([row])['dias']), 7)
        self.assertEqual(timetable.week_view([])['count'], 0)


class InboxReadAllTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.override = patch.object(db, 'DB_PATH', Path(cls.temp.name)/'inbox.db')
        cls.override.start()
        db.init_db(); init_director(); db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.override.stop(); cls.temp.cleanup()

    def setUp(self):
        with db.connection() as conn:
            conn.execute('DELETE FROM notification_reads')
            conn.execute('DELETE FROM notifications')
            conn.execute('DELETE FROM communication_states')
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session.update(username='thiago.zotti', role='aluno', aluno_id='23081',
                           auth_version=access_version('thiago.zotti'), p1_token='inbox-test')
        for title, kwargs in [
            ('Meu documento', dict(recipient='thiago.zotti')),
            ('Para alunos', dict(role_target='aluno')),
            ('Conversa', dict(recipient='thiago.zotti', category='mensagem')),
            ('Outro usuário', dict(recipient='pablo.sousa')),
            ('Só direção', dict(role_target='admin')),
            ('Descartado', dict(recipient='thiago.zotti')),
        ]:
            operations.create_notification(title, 'Texto de teste', **kwargs)
        self.ids = {n['title']: n['id'] for n in operations.list_notifications('thiago.zotti','aluno')}
        operations.mark_notification(self.ids['Descartado'], 'thiago.zotti', True, 'aluno')
        db.set_communication_read('thiago.zotti','notification',str(self.ids['Descartado']),True)
        db.dismiss_communication('thiago.zotti','notification',str(self.ids['Descartado']))
        self.notices = [dict(key='authorized', titulo='Aviso da turma', desc='Texto', quando='Hoje')]

    def test_bulk_is_persistent_idempotent_and_scoped(self):
        with patch('app.student_notices', return_value=self.notices):
            page = self.client.get('/comunicados')
            self.assertIn(b'Marcar tudo como lido', page.data)
            response = self.client.post('/comunicados', data=dict(token='inbox-test', action='read_all', id='999', item_key='injected'))
            self.assertEqual(response.status_code, 302)
            response = self.client.post('/comunicados', data=dict(token='inbox-test', action='read_all'), follow_redirects=True)
        self.assertIn('já estão lidos'.encode(), response.data)
        read = {n['title']: bool(n['is_read']) for n in operations.list_notifications('thiago.zotti','aluno')}
        self.assertTrue(read['Meu documento']); self.assertTrue(read['Para alunos'])
        self.assertFalse(read['Conversa'])
        self.assertTrue(db.get_communication_states('thiago.zotti','notice')['authorized']['is_read'])
        self.assertNotIn('injected', db.get_communication_states('thiago.zotti','notice'))
        self.assertFalse(any(n['is_read'] for n in operations.list_notifications('pablo.sousa','aluno')))
        self.assertFalse(any(n['is_read'] for n in operations.list_notifications('gilberto','admin')))
        self.assertTrue(db.get_communication_states('thiago.zotti','notification')[str(self.ids['Descartado'])]['dismissed_at'])

    def test_missing_csrf_never_writes(self):
        result = self.client.post('/comunicados', data=dict(action='read_all'))
        self.assertEqual(result.status_code,400)
        self.assertFalse(next(n for n in operations.list_notifications('thiago.zotti','aluno') if n['title']=='Meu documento')['is_read'])

    def test_staff_has_the_same_explicit_action(self):
        with self.client.session_transaction() as session:
            session.update(username='gilberto', role='admin', auth_version=access_version('gilberto'))
        self.assertIn(b'Marcar tudo como lido', self.client.get('/notificacoes').data)
        self.assertEqual(self.client.post('/notificacoes', data=dict(token='inbox-test',action='read_all')).status_code,302)
        self.assertTrue(next(n for n in operations.list_notifications('gilberto','admin') if n['title']=='Só direção')['is_read'])

    def test_write_failure_rolls_back_both_read_stores(self):
        original_connection = db.connection
        class FailingWrites:
            def __init__(self, conn): self.conn = conn
            def execute(self, *args): return self.conn.execute(*args)
            def executemany(self, sql, params):
                if 'INSERT INTO notification_reads' in sql:
                    raise RuntimeError('simulated write failure')
                return self.conn.executemany(sql, params)
        @contextmanager
        def failing_connection():
            with original_connection() as conn:
                yield FailingWrites(conn)
        with patch.object(db, 'connection', failing_connection):
            with self.assertRaisesRegex(RuntimeError, 'simulated'):
                operations.mark_inbox_read('thiago.zotti','aluno',notice_keys=['authorized'],exclude_messages=True)
        self.assertNotIn('authorized', db.get_communication_states('thiago.zotti','notice'))
        self.assertFalse(next(n for n in operations.list_notifications('thiago.zotti','aluno') if n['title']=='Meu documento')['is_read'])


if __name__ == '__main__':
    unittest.main()
