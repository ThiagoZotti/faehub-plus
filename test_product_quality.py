import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from app import app
from director import access_version, init_director


class ProductQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "quality.db")
        cls.db_patch.start()
        db.init_db()
        init_director()
        db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def test_security_headers_and_error_page(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        missing = client.get("/nao-existe")
        self.assertEqual(missing.status_code, 404)
        self.assertIn("Caminho não encontrado".encode(), missing.data)

    def test_new_install_leaves_roster_accounts_for_director(self):
        users = db.list_users()
        self.assertFalse(any(user["username"].startswith("aluno3110_") for user in users))
        self.assertEqual(sum(user["role"] == "aluno" for user in users), 4)

    def test_student_frequency_comes_from_saved_attendance(self):
        db.save_attendance("23081", "2026-09-01", "presente")
        db.save_attendance("23081", "2026-09-02", "ausente")
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(
                username="thiago.zotti",
                role="aluno",
                aluno_id="23081",
                display_name="Thiago Zotti",
                auth_version=access_version("thiago.zotti"),
            )
        response = client.get("/frequencia")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"50%", response.data)
        self.assertIn(b"2 chamadas registradas", response.data)

    def test_retry_payloads_are_inert_html_templates(self):
        director_template = Path("templates/director.html").read_text(encoding="utf-8")
        studio_template = Path("templates/professor_studio.html").read_text(encoding="utf-8")
        self.assertIn('<template id="directorRetry">', director_template)
        self.assertIn('<template id="studioFailed">', studio_template)
        self.assertNotIn('type="application/json"', director_template + studio_template)


if __name__ == "__main__":
    unittest.main()
