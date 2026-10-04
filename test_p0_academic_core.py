import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import academic_core
import database as db
from app import app
from director import access_version, init_director


class AcademicCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "p0.db")
        cls.db_patch.start()
        db.init_db(); init_director(); db.seed_teacher_assignments()
        academic_core.sync_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop(); cls.temp.cleanup()

    def setUp(self):
        self.client = app.test_client()

    def login(self, username="gilberto", role="admin", aluno_id=None):
        with self.client.session_transaction() as session:
            session.clear(); session.update(username=username, role=role, display_name="Teste",
                auth_version=access_version(username), p0_token="p0-token")
            if aluno_id: session["aluno_id"] = aluno_id

    def test_structure_pages_are_role_protected(self):
        self.login()
        for view in ("overview", "years", "catalog", "classes", "students", "teachers"):
            self.assertEqual(self.client.get("/estrutura?view=" + view).status_code, 200, view)
        self.login("thiago.zotti", "aluno", "23081")
        self.assertEqual(self.client.get("/estrutura").status_code, 403)

    def test_create_full_academic_chain_and_preserve_enrollment(self):
        self.login()
        def post(action, **values):
            values.update(token="p0-token", action=action, audit_label=action, return_view="overview")
            response = self.client.post("/estrutura", data=values)
            self.assertEqual(response.status_code, 302, response.get_data(as_text=True))
        post("year_create", name="2027", starts_on="2027-02-01", ends_on="2027-12-17")
        snapshot = academic_core.structure_snapshot(); year = next(row for row in snapshot["years"] if row["name"] == "2027")
        post("period_create", year_id=year["id"], name="1º trimestre", period_number="1", starts_on="2027-02-01", ends_on="2027-05-14")
        post("course_create", code="ADM", name="Administração", description="Curso de teste")
        post("subject_create", code="LOG", name="Logística", workload_minutes="1200")
        snapshot = academic_core.structure_snapshot(); course = next(row for row in snapshot["courses"] if row["code"] == "ADM")
        post("class_create", year_id=year["id"], course_id=course["id"], code="1101", grade_label="1º ano", shift="Manhã", room="A1", capacity="30")
        post("student_create", registration="27001", full_name="Estudante Histórico", birth_date="2010-03-04")
        snapshot = academic_core.structure_snapshot(); klass = next(row for row in snapshot["classes"] if row["code"] == "1101"); student = next(row for row in snapshot["students"] if row["registration"] == "27001")
        post("enrollment_create", student_id=student["id"], class_id=klass["id"], enrolled_on="2027-02-01")
        enrollment = next(row for row in academic_core.structure_snapshot()["enrollments"] if row["registration"] == "27001")
        post("enrollment_end", enrollment_id=enrollment["id"], status="completed", ended_on="2027-12-17")
        history = academic_core.student_history("27001")
        self.assertEqual(history[0]["academic_year"], "2027")
        self.assertEqual(history[0]["status"], "completed")

    def test_legacy_grade_is_available_in_normalized_history(self):
        db.save_grade("23081", "LP3", 8.0, 9.0)
        rows = academic_core.student_history("23081")
        scores = [score["score"] for year in rows for score in year["subjects"] if score["code"] == "LP3"]
        self.assertEqual(scores, [8.0, 9.0])

    def test_student_and_guardian_history_scope(self):
        self.login("thiago.zotti", "aluno", "23081")
        self.assertEqual(self.client.get("/historico").status_code, 200)
        self.assertEqual(self.client.get("/historico?matricula=23092").status_code, 403)
        self.login("responsavel.thiago", "responsavel")
        self.assertEqual(self.client.get("/historico?matricula=23081").status_code, 200)
        self.assertEqual(self.client.get("/historico?matricula=23092").status_code, 403)


if __name__ == "__main__":
    unittest.main()
