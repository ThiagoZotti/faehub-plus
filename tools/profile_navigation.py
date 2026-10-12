"""Reproducible, disposable navigation baseline; never opens the school database."""
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root), str(root / '.test_dependencies')]
    os.environ.update(FAEHUB_DATABASE_URL='', DATABASE_URL='', RENDER='',
                      FAEHUB_SECRET_KEY='disposable-navigation-profile')
    with tempfile.TemporaryDirectory(prefix='faehub-navigation-') as directory:
        os.environ['FAEHUB_DATABASE'] = str(Path(directory) / 'test.db')
        from app import app
        from director import access_version
        original = sqlite3.connect
        cases = [('admin', 'gilberto', None, ['/painel', '/usuarios', '/configuracoes', '/relatorios']),
                 ('professor', 'aline', None, ['/painel', '/turmas', '/notas']),
                 ('aluno', 'thiago.zotti', '23081', ['/painel', '/boletim', '/horario'])]
        results = []
        for role, username, student_id, routes in cases:
            client = app.test_client()
            with client.session_transaction() as session:
                session.update(role=role, username=username, auth_version=access_version(username),
                               profile_photo_revision='', profile_photo_checked=time.time())
                if student_id:
                    session['aluno_id'] = student_id
            for route in routes:
                # Warm the Jinja cache before measuring runtime work.
                client.get(route)
                statements = []
                def connect(*args, **kwargs):
                    conn = original(*args, **kwargs)
                    conn.set_trace_callback(statements.append)
                    return conn
                start = time.perf_counter()
                with patch.object(sqlite3, 'connect', side_effect=connect):
                    response = client.get(route)
                results.append(dict(role=role, route=route, status=response.status_code,
                                    selects=sum(s.lstrip().upper().startswith('SELECT') for s in statements),
                                    milliseconds=round((time.perf_counter() - start) * 1000, 2)))
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
