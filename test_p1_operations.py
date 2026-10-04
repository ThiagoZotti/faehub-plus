import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import p1_operations as operations
from app import app
from director import access_version, init_director


class P1OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "p1.db")
        cls.db_patch.start()
        db.init_db()
        init_director()
        db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.client = app.test_client()

    def login(self, username, role, **extra):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(
                username=username,
                role=role,
                display_name="Teste P1",
                auth_version=access_version(username),
                p1_token="p1-token",
                message_token="message-token",
                exercise_token="exercise-token",
                studio_token="studio-token",
                **extra,
            )

    def test_all_p1_pages_render_for_authorized_roles(self):
        self.login("gilberto", "admin")
        for path in ("secretaria", "coordenacao", "periodos", "calendario", "notificacoes", "diario", "relatorios"):
            self.assertEqual(self.client.get("/" + path).status_code, 200, path)
        self.login("responsavel.thiago", "responsavel")
        for path in ("painel", "secretaria", "calendario", "notificacoes", "mensagens"):
            self.assertEqual(self.client.get("/" + path).status_code, 200, path)

    def test_guardian_authentication_and_empty_document_scope(self):
        account = db.authenticate("responsavel.thiago", "responsavel@123")
        self.assertEqual(account["role"], "responsavel")
        self.assertEqual(operations.list_document_requests(student_ids=[]), [])

    def test_student_cannot_publish_calendar_event(self):
        self.login("thiago.zotti", "aluno", aluno_id="23081")
        self.assertEqual(self.client.post("/calendario", data={"token": "p1-token"}).status_code, 403)

    def test_diary_submission_and_coordination_validation(self):
        self.login("aline", "professor")
        response = self.client.post("/diario", data={
            "token": "p1-token", "class_name": "3110", "discipline": "LP3",
            "lesson_date": date.today().isoformat(), "class_hours": "2",
            "content": "Estruturação de rotas Flask", "objectives": "Construir uma rota segura",
            "methodology": "Laboratório", "resources": "Computadores", "homework": "",
            "observations": "", "status": "submitted",
        })
        self.assertEqual(response.status_code, 302)
        entry = operations.list_diary_entries("aline")[0]
        self.assertEqual(entry["status"], "submitted")
        self.login("gilberto", "admin")
        response = self.client.post("/diario", data={
            "token": "p1-token", "id": entry["id"], "action": "validate", "coordinator_note": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(operations.list_diary_entries("aline")[0]["status"], "validated")

    def test_document_protocol_and_guardian_scope(self):
        self.login("responsavel.thiago", "responsavel")
        response = self.client.post("/secretaria", data={
            "token": "p1-token", "student_id": "23081", "document_type": "frequencia",
            "purpose": "Comprovação para inscrição externa",
        })
        self.assertEqual(response.status_code, 302)
        record = operations.list_document_requests(student_ids=["23081"])[0]
        self.assertTrue(record["protocol"].startswith("FH-"))
        response = self.client.post("/secretaria", data={
            "token": "p1-token", "student_id": "23092", "document_type": "frequencia", "purpose": "Teste",
        })
        self.assertEqual(response.status_code, 422)

    def test_notifications_persist_read_state(self):
        operations.create_notification("Conselho de classe", "Novo horário publicado", role_target="aluno", created_by="gilberto")
        self.login("thiago.zotti", "aluno", aluno_id="23081")
        page = self.client.get("/notificacoes")
        self.assertIn("Conselho de classe".encode(), page.data)
        item = operations.list_notifications("thiago.zotti", "aluno")[0]
        self.client.post("/notificacoes", data={"token": "p1-token", "action": "read", "id": item["id"]})
        self.assertTrue(operations.list_notifications("thiago.zotti", "aluno")[0]["is_read"])

    def test_message_attachment_and_authorized_download(self):
        self.login("thiago.zotti", "aluno", aluno_id="23081")
        response = self.client.post("/mensagens", data={
            "token": "message-token", "recipient": "aline", "subject": "Trabalho",
            "body": "Segue o arquivo.", "attachment": (io.BytesIO(b"conteudo"), "trabalho.txt"),
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        message = db.get_messages("thiago.zotti")[0]
        attachment = operations.list_attachments("message", [message["id"]])[0]
        download = self.client.get(f"/anexos/{attachment['id']}")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.data, b"conteudo")
        self.login("jonathan.samuel", "aluno", aluno_id="23092")
        self.assertNotEqual(self.client.get(f"/anexos/{attachment['id']}").status_code, 200)

    def test_password_recovery_uses_one_time_code(self):
        operations.request_password_recovery("thiago.zotti")
        request_row = operations.list_recovery_requests()[0]
        code = operations.issue_recovery_code(request_row["id"], "gilberto")
        operations.use_recovery_code("thiago.zotti", code, "nova-senha-segura")
        self.assertIsNotNone(db.authenticate("thiago.zotti", "nova-senha-segura"))
        with self.assertRaises(ValueError):
            operations.use_recovery_code("thiago.zotti", code, "outra-senha-segura")


if __name__ == "__main__":
    unittest.main()
