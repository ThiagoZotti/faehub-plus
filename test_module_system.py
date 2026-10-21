"""Shared module skin is applied to every authorized profile, not dashboards."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import database as db
from app import app
from director import init_director, access_version


class ModuleSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.override=patch.object(db,'DB_PATH',Path(cls.temp.name)/'modules.db')
        cls.override.start()
        db.init_db();init_director();db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.override.stop();cls.temp.cleanup()

    def login(self,username,role):
        client=app.test_client()
        with client.session_transaction() as session:
            session.update(username=username,role=role,auth_version=access_version(username),aluno_id='23081')
        return client

    def test_all_module_groups_share_the_adapter(self):
        profiles=[
            ('thiago.zotti','aluno',('boletim','agenda','horario','exercicios','comunicados','secretaria','estagios','mensagens','frequencia','calendario','historico','conta/seguranca')),
            ('aline','professor',('turmas','notas','chamada','diario','exercicios','mensagens','avisos','estagios','calendario','notificacoes','conta/seguranca')),
            ('gilberto','admin',('usuarios','estrutura','secretaria','coordenacao','relatorios','mensagens','periodos','calendario','notificacoes','configuracoes','diario','historico','conta/seguranca')),
            ('responsavel.thiago','responsavel',('secretaria','calendario','notificacoes','mensagens','historico','conta/seguranca')),
        ]
        for username,role,paths in profiles:
            client=self.login(username,role)
            for path in paths:
                with self.subTest(role=role,path=path):
                    result=client.get('/'+path)
                    self.assertEqual(result.status_code,200)
                    self.assertIn(b'module-system.css',result.data)
                    self.assertIn(b'campus-modules',result.data)
                    self.assertIn(b'campus-electric',result.data)

    def test_approved_dashboards_and_portal_are_not_recomposed(self):
        for username,role in [('thiago.zotti','aluno'),('aline','professor'),('gilberto','admin'),('responsavel.thiago','responsavel')]:
            client=self.login(username,role)
            for path in ('/painel','/faenet'):
                result=client.get(path)
                self.assertEqual(result.status_code,200)
                self.assertNotIn(b'module-system.css',result.data)
                self.assertNotIn(b'campus-modules',result.data)
        self.assertNotIn(b'module-system.css',app.test_client().get('/').data)

    def test_document_status_remains_semantic_and_actions_remain_links_or_buttons(self):
        import p1_operations as operations
        identifier,_=operations.create_document_request('thiago.zotti','23081','matricula','Ensaio isolado')
        operations.update_document_request(identifier,'ready','Pronto para conferência')
        result=self.login('gilberto','admin').get('/secretaria')
        html=result.get_data(as_text=True)
        self.assertIn('>Pronto</span>',html)
        self.assertIn('>Abrir</a>',html)
        self.assertIn('>Atualizar</button>',html)
        self.assertIn('<option value="ready" selected>',html)
        self.assertIn('maxlength="1000">Pronto para conferência</textarea>',html)
        self.assertIn('ops-btn--small',html)


if __name__=='__main__':unittest.main()
