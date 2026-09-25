import unittest
from datetime import date, datetime
from decimal import Decimal

import database


class DatabaseBackendTests(unittest.TestCase):
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
