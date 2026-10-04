import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from app import app


class InternshipModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "internships.db")
        cls.db_patch.start()
        db.init_db()
        db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.client = app.test_client()
        self.login("aline", "professor")

    def login(self, username, role):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(
                username=username,
                role=role,
                display_name="Teste",
                aluno_id="23081",
                teacher_token="internship-token",
            )

    def payload(self, **overrides):
        data = {
            "token": "internship-token",
            "action": "create",
            "class_name": "3110",
            "company": "Laboratório Horizonte",
            "title": "Estágio em suporte de TI",
            "description": "Atendimento técnico e apoio à equipe de infraestrutura.",
            "location": "Santa Cruz, Rio de Janeiro",
            "modality": "hibrido",
            "workload": "20h semanais",
            "requirements": "Cursando ensino técnico e boa comunicação.",
            "application_url": "https://example.com/estagio",
            "application_instructions": "Preencha o formulário da organização.",
            "deadline": "2099-12-31",
        }
        data.update(overrides)
        return data

    def test_teacher_create_edit_archive_restore_and_student_visibility(self):
        response = self.client.post("/estagios", data=self.payload())
        self.assertEqual(response.status_code, 302)
        item = next(i for i in db.get_internships() if i["title"] == "Estágio em suporte de TI")

        self.login("thiago.zotti", "aluno")
        page = self.client.get("/estagios")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Laborat", page.data)
        self.assertIn(b'rel="noopener noreferrer nofollow external"', page.data)

        self.login("aline", "professor")
        edited = self.payload(action="edit", id=str(item["id"]), title="Estágio em infraestrutura")
        self.assertEqual(self.client.post("/estagios", data=edited).status_code, 302)
        self.assertEqual(next(i for i in db.get_internships() if i["id"] == item["id"])["title"], "Estágio em infraestrutura")

        self.assertEqual(self.client.post("/estagios", data={"token": "internship-token", "action": "archive", "id": item["id"]}).status_code, 302)
        self.login("thiago.zotti", "aluno")
        self.assertNotIn(b"Est\xc3\xa1gio em infraestrutura", self.client.get("/estagios").data)

        self.login("aline", "professor")
        self.assertEqual(self.client.post("/estagios", data={"token": "internship-token", "action": "restore", "id": item["id"]}).status_code, 302)
        self.assertFalse(next(i for i in db.get_internships(include_archived=True) if i["id"] == item["id"])["archived"])

    def test_validation_csrf_and_role_enforcement(self):
        self.assertEqual(self.client.post("/estagios", data=self.payload(token="bad")).status_code, 400)
        unsafe = self.payload(title="Link inseguro", application_url="javascript:alert(1)")
        response = self.client.post("/estagios", data=unsafe)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("Link inseguro", [item["title"] for item in db.get_internships(include_archived=True)])

        self.login("thiago.zotti", "aluno")
        self.assertEqual(self.client.post("/estagios", data=self.payload()).status_code, 403)
        self.login("gilberto", "admin")
        self.assertEqual(self.client.get("/estagios").status_code, 302)

    def test_teacher_cannot_change_another_teachers_opportunity(self):
        db.create_user("outro_docente_estagio", "test-password", "Outro Docente", "professor")
        db.save_internship("outro_docente_estagio", {
            key: value for key, value in self.payload().items()
            if key in {"company", "title", "description", "location", "modality", "workload", "requirements", "application_url", "application_instructions", "deadline", "class_name"}
        })
        item = next(i for i in db.get_internships(teacher="outro_docente_estagio", include_archived=True))
        response = self.client.post("/estagios", data={
            "token": "internship-token", "action": "archive", "id": item["id"]
        })
        self.assertEqual(response.status_code, 422)
        self.assertFalse(next(i for i in db.get_internships(teacher="outro_docente_estagio", include_archived=True) if i["id"] == item["id"])["archived"])


if __name__ == "__main__":
    unittest.main()
