import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from app import app
from director import access_version, init_director


class NavigationCompactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "navigation.db")
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

    def login(self, username, role, student_id=None):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(
                username=username,
                role=role,
                display_name="Thiago Zotti" if role == "aluno" else "Direção",
                auth_version=access_version(username),
            )
            if student_id:
                session["aluno_id"] = student_id

    def test_student_navigation_uses_three_consolidated_destinations(self):
        self.login("thiago.zotti", "aluno", "23081")
        response = self.client.get("/painel")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/agenda"', response.data)
        self.assertIn(b'href="/comunicados"', response.data)
        self.assertNotIn(b'href="/frequencia"', response.data)
        self.assertNotIn(b'href="/historico"', response.data)

    def test_student_panel_uses_radar_and_has_no_avatar_feature(self):
        self.login("thiago.zotti", "aluno", "23081")
        response = self.client.get("/painel")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Campus em movimento".encode(), response.data)
        self.assertIn("Bem-vindo,".encode(), response.data)
        self.assertIn("Seu próximo movimento".encode(), response.data)
        self.assertIn("Seu ritmo acadêmico".encode(), response.data)
        self.assertIn(b'/exercicios?status=pending', response.data)
        self.assertNotIn("Entregas em foco".encode(), response.data)
        self.assertNotIn("Continue pelo campus".encode(), response.data)
        self.assertNotIn(b'href="/avatar"', response.data)
        self.assertNotIn("Personalizar".encode(), response.data)
        self.assertEqual(self.client.get("/avatar").status_code, 404)

    def test_pending_summary_opens_exercises_with_pending_filter(self):
        self.login("thiago.zotti", "aluno", "23081")
        response = self.client.get("/exercicios?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-initial-exercise-filter="pending"', response.data)
        self.assertIn(b'data-exercise-filter="pending" aria-pressed="true"', response.data)

    def test_agenda_combines_attendance_and_school_events(self):
        self.login("thiago.zotti", "aluno", "23081")
        response = self.client.get("/agenda")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Presenças".encode(), response.data)
        self.assertIn("Eventos escolares".encode(), response.data)

    def test_communications_and_secretary_absorb_old_sections(self):
        self.login("thiago.zotti", "aluno", "23081")
        communications = self.client.get("/comunicados")
        secretary = self.client.get("/secretaria")
        self.assertEqual(communications.status_code, 200)
        self.assertIn("Avisos da turma".encode(), communications.data)
        self.assertIn("Atualizações da conta".encode(), communications.data)
        self.assertEqual(secretary.status_code, 200)
        self.assertIn("Histórico acadêmico".encode(), secretary.data)

    def test_read_notice_can_be_dismissed_and_restored(self):
        self.login("thiago.zotti", "aluno", "23081")
        notice = [{"key": "notice:test", "titulo": "Aviso de teste", "desc": "Conteúdo", "quando": "Hoje"}]
        with patch("app.student_notices", return_value=notice), patch(
            "app.operations.list_notifications", return_value=[]
        ):
            self.client.get("/comunicados")
            with self.client.session_transaction() as session:
                token = session["p1_token"]
            unread_dismiss = self.client.post(
                "/comunicados",
                data={"token": token, "kind": "notice", "item_key": "notice:test", "action": "dismiss"},
            )
            self.assertEqual(unread_dismiss.status_code, 422)
            self.client.post(
                "/comunicados",
                data={"token": token, "kind": "notice", "item_key": "notice:test", "action": "read"},
            )
            self.client.post(
                "/comunicados",
                data={"token": token, "kind": "notice", "item_key": "notice:test", "action": "dismiss"},
            )
            state = db.get_communication_states("thiago.zotti", "notice")["notice:test"]
            self.assertTrue(state["is_read"])
            self.assertIsNotNone(state["dismissed_at"])
            discarded = self.client.get("/comunicados")
            self.assertIn("Descartados".encode(), discarded.data)
            self.client.post(
                "/comunicados",
                data={"token": token, "kind": "notice", "item_key": "notice:test", "action": "restore"},
            )
            restored = db.get_communication_states("thiago.zotti", "notice")["notice:test"]
            self.assertIsNone(restored["dismissed_at"])

    def test_large_role_navigation_uses_shared_more_menu(self):
        self.login("gilberto", "admin")
        response = self.client.get("/painel")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="campus-more"', response.data)
        self.assertIn(b'</nav>\n    <details class="campus-more"', response.data)
        self.assertIn("Configurações".encode(), response.data)


if __name__ == "__main__":
    unittest.main()
