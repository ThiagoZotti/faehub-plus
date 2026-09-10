import unittest
from app import app

class InterfaceCopyTests(unittest.TestCase):
    def test_schedule_uses_student_facing_copy(self):
        client=app.test_client()
        with client.session_transaction() as s:s.update(username='thiago.zotti',role='aluno',aluno_id='23081')
        response=client.get('/horario')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('referência enviada'.encode(),response.data)
        self.assertNotIn(b'grade enviada',response.data)
        self.assertNotIn('Grade informada por você'.encode(),response.data)
        self.assertIn('Confirme alterações de aula com a secretaria.'.encode(),response.data)

    def test_entry_remains_explicit(self):
        response=app.test_client().get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'credentialConfirmed',response.data)
        self.assertNotIn('Cenário conceitual'.encode(),response.data)

if __name__=='__main__':unittest.main()
