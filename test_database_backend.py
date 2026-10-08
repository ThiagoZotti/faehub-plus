import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, g
from datetime import date, datetime
from decimal import Decimal

import database


class DatabaseBackendTests(unittest.TestCase):
    def test_pool_checks_connections_before_lending_them(self):
        import psycopg_pool
        with patch.object(database, '_postgres_pool', None), patch.object(database, 'DATABASE_URL', 'postgresql://invalid.example/test'), patch.object(psycopg_pool, 'ConnectionPool') as pool:
            database._pool()
            self.assertIs(pool.call_args.kwargs['check'], pool.check_connection)
            self.assertEqual(pool.call_args.kwargs['timeout'], 10)
            self.assertEqual(pool.call_args.kwargs['kwargs']['connect_timeout'], 10)
            self.assertEqual(pool.call_args.kwargs['kwargs']['sslmode'], 'require')

    def test_disconnect_preserves_original_error_and_returns_lease(self):
        raw=MagicMock();raw.rollback.side_effect=RuntimeError('connection is lost')
        root=RuntimeError('original query failure')
        lease=MagicMock();lease.__enter__.return_value=raw
        with patch.object(database, 'using_postgres', return_value=True), patch.object(database, '_pool') as pool:
            pool.return_value.connection.return_value=lease
            with self.assertRaises(RuntimeError) as raised:
                with database.connection():
                    raise root
        self.assertIs(raised.exception, root)
        raw.close.assert_called_once()
        self.assertIs(lease.__exit__.call_args.args[1], root)
        raw.commit.assert_not_called()

    def test_teardown_returns_broken_request_connection_without_masking_error(self):
        raw=MagicMock();raw.rollback.side_effect=RuntimeError('connection is lost')
        lease=MagicMock()
        with Flask(__name__).app_context():
            g.faehub_connection=database.PostgresConnection(raw)
            g.faehub_connection_lease=lease
            database.close_request_connection(RuntimeError('original query failure'))
            self.assertNotIn('faehub_connection', g)
            self.assertNotIn('faehub_connection_lease', g)
        raw.close.assert_called_once();lease.__exit__.assert_called_once()
        raw.commit.assert_not_called()

    def test_teardown_commit_failure_is_not_reported_as_success(self):
        raw=MagicMock();root=RuntimeError('commit failed')
        raw.commit.side_effect=root;raw.rollback.side_effect=RuntimeError('connection is lost')
        lease=MagicMock()
        with Flask(__name__).app_context():
            g.faehub_connection=database.PostgresConnection(raw)
            g.faehub_connection_lease=lease
            with self.assertRaises(RuntimeError) as raised:
                database.close_request_connection()
        self.assertIs(raised.exception, root)
        raw.close.assert_called_once();lease.__exit__.assert_called_once()
        self.assertIs(lease.__exit__.call_args.args[1], root)

    def test_translates_sqlite_parameters_for_postgres(self):
        translated = database._postgres_sql(
            "INSERT OR IGNORE INTO example(value) VALUES(?)"
        )
        self.assertEqual(
            translated,
            "INSERT INTO example(value) VALUES(%s) ON CONFLICT DO NOTHING",
        )

    def test_translates_sqlite_clock_expression(self):
        translated = database._postgres_sql(
            "UPDATE example SET updated_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE id=?"
        )
        self.assertIn("clock_timestamp()", translated)
        self.assertTrue(translated.endswith("id=%s"))

    def test_compat_row_supports_names_and_positions(self):
        row = database.CompatRow(name="Thiago", role="aluno")
        self.assertEqual(row[0], "Thiago")
        self.assertEqual(row["role"], "aluno")

    def test_postgres_values_are_template_safe(self):
        row = database._portable_row(
            {
                "day": date(2026, 9, 25),
                "moment": datetime(2026, 9, 25, 14, 30),
                "score": Decimal("8.50"),
            }
        )
        self.assertEqual(row["day"], "2026-09-25")
        self.assertEqual(row["moment"], "2026-09-25T14:30:00")
        self.assertEqual(row["score"], 8.5)


if __name__ == "__main__":
    unittest.main()
