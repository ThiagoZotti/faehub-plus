import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import academic_core
import database as db


class AcademicIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        database_patch = patch.object(db, "DB_PATH", Path(self.temp.name) / "integrity.db")
        database_patch.start()
        self.addCleanup(database_patch.stop)
        db.init_db()

    def test_restart_preserves_managed_student_and_all_enrollment_end_states(self):
        states = ("completed", "transferred", "withdrawn", "cancelled")
        with db.connection() as conn:
            students = conn.execute("SELECT id FROM students ORDER BY id LIMIT 4").fetchall()
            for row, status in zip(students, states):
                conn.execute("UPDATE enrollments SET status=?,ended_on='2026-09-30' WHERE student_id=?",
                             (status, row["id"]))
                conn.execute("UPDATE students SET full_name='Nome administrado',active=FALSE WHERE id=?",
                             (row["id"],))
            before = [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")]
            conn.execute("INSERT INTO subjects(code,name,active) VALUES('NEW','Nova disciplina',TRUE)")
            grade_count = conn.execute("SELECT COUNT(*) n FROM class_subjects").fetchone()["n"]
        for _ in range(2):
            db.init_db()
        with db.connection() as conn:
            self.assertEqual(before, [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")])
            self.assertEqual(grade_count, conn.execute("SELECT COUNT(*) n FROM class_subjects").fetchone()["n"])
            for row in students:
                student = conn.execute("SELECT full_name,active FROM students WHERE id=?", (row["id"],)).fetchone()
                self.assertEqual(student["full_name"], "Nome administrado")
                self.assertFalse(student["active"])

    def test_upgrade_without_marker_adopts_existing_data_without_reseeding(self):
        with db.connection() as conn:
            conn.execute("DELETE FROM seed_markers WHERE name='academic_core_initial_v1'")
            conn.execute("UPDATE students SET full_name='Nome migrado' WHERE registration='23081'")
            conn.execute("UPDATE enrollments SET status='completed',ended_on='2026-09-30'")
            before = [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")]
        db.init_db()
        with db.connection() as conn:
            self.assertEqual(before, [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")])
            self.assertEqual("Nome migrado", conn.execute("SELECT full_name FROM students WHERE registration='23081'").fetchone()["full_name"])
            self.assertIsNotNone(conn.execute("SELECT 1 FROM seed_markers WHERE name='academic_core_initial_v1'").fetchone())

    def create_next_year(self):
        academic_core.mutate("year_create", {"name": "2027", "starts_on": "2027-02-01", "ends_on": "2027-12-17"}, "gilberto")
        with db.connection() as conn:
            return conn.execute("SELECT id FROM academic_years WHERE name='2027'").fetchone()["id"]

    def test_activation_rejects_open_or_planned_periods_without_partial_changes(self):
        year_id = self.create_next_year()
        for status in ("open", "planning"):
            with self.subTest(status=status):
                with db.connection() as conn:
                    conn.execute("UPDATE academic_periods SET status=? WHERE period_number=3", (status,))
                    before = [dict(row) for row in conn.execute("SELECT * FROM academic_years ORDER BY id")]
                    logs = conn.execute("SELECT COUNT(*) n FROM activity_log").fetchone()["n"]
                with self.assertRaisesRegex(ValueError, "Feche todos os períodos"):
                    academic_core.mutate("year_status", {"year_id": year_id, "status": "active"}, "gilberto")
                with db.connection() as conn:
                    self.assertEqual(before, [dict(row) for row in conn.execute("SELECT * FROM academic_years ORDER BY id")])
                    self.assertEqual(logs, conn.execute("SELECT COUNT(*) n FROM activity_log").fetchone()["n"])

    def test_activation_after_closure_preserves_history_and_audits_transition(self):
        year_id = self.create_next_year()
        with db.connection() as conn:
            conn.execute("UPDATE academic_periods SET status='closed'")
            before = [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")]
        academic_core.mutate("year_status", {"year_id": year_id, "status": "active"}, "gilberto")
        with db.connection() as conn:
            self.assertEqual("closed", conn.execute("SELECT status FROM academic_years WHERE name='2026'").fetchone()["status"])
            self.assertEqual([year_id], [row["id"] for row in conn.execute("SELECT id FROM academic_years WHERE status='active'")])
            self.assertEqual(before, [dict(row) for row in conn.execute("SELECT * FROM enrollments ORDER BY id")])
            self.assertIsNotNone(conn.execute("SELECT 1 FROM activity_log WHERE username='gilberto' AND action='estrutura_year_status'").fetchone())

    def test_invalid_target_and_reactivation_do_not_close_current_year(self):
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            academic_core.mutate("year_status", {"year_id": -1, "status": "active"}, "gilberto")
        with db.connection() as conn:
            current = conn.execute("SELECT id FROM academic_years WHERE name='2026'").fetchone()["id"]
        academic_core.mutate("year_status", {"year_id": current, "status": "active"}, "gilberto")
        with db.connection() as conn:
            self.assertEqual("active", conn.execute("SELECT status FROM academic_years WHERE id=?", (current,)).fetchone()["status"])


if __name__ == "__main__":
    unittest.main()
