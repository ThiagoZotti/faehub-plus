import base64
import json
import os
import unittest
from email import message_from_bytes
from unittest.mock import MagicMock, patch
import gmail_mail


class GmailTests(unittest.TestCase):
    def test_refresh_then_multipart_delivery(self):
        auth = MagicMock()
        auth.__enter__.return_value.read.return_value = b'{"access_token":"fake-access"}'
        sent = MagicMock()
        sent.__enter__.return_value.read.return_value = b'{"id":"fake-message"}'
        env = dict(FAEHUB_GMAIL_CLIENT_ID='fake-client', FAEHUB_GMAIL_CLIENT_SECRET='fake-secret',
                   FAEHUB_GMAIL_REFRESH_TOKEN='fake-refresh', FAEHUB_GMAIL_SENDER='sender@gmail.com')
        with patch.dict(os.environ, env, clear=True), patch.object(gmail_mail, 'urlopen', side_effect=[auth, sent]) as transport:
            self.assertTrue(gmail_mail.configured())
            gmail_mail.send('student@example.com', 'Convite', 'Texto', '<b>Convite</b>')
        requests = [call.args[0] for call in transport.call_args_list]
        self.assertEqual(requests[0].full_url, 'https://oauth2.googleapis.com/token')
        self.assertIn(b'grant_type=refresh_token', requests[0].data)
        self.assertEqual(requests[1].full_url, 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')
        message = message_from_bytes(base64.urlsafe_b64decode(json.loads(requests[1].data)['raw']))
        self.assertEqual(message['To'], 'student@example.com')
        self.assertEqual(message.get_content_type(), 'multipart/alternative')
        self.assertEqual(len(message.get_payload()), 2)

    def test_incomplete_config_and_unknown_provider_fail_closed(self):
        import account_enrollment as enrollment
        with patch.dict(os.environ, {'FAEHUB_MAIL_PROVIDER':'gmail', 'FAEHUB_PUBLIC_URL':'https://school.example'}, clear=True):
            self.assertFalse(enrollment.mail_configured())

    def test_invitation_dispatches_to_gmail_with_existing_template(self):
        import account_enrollment as enrollment
        from app import app
        env = dict(FAEHUB_MAIL_PROVIDER='gmail', FAEHUB_PUBLIC_URL='https://school.example',
                   FAEHUB_GMAIL_CLIENT_ID='fake-client', FAEHUB_GMAIL_CLIENT_SECRET='fake-secret',
                   FAEHUB_GMAIL_REFRESH_TOKEN='fake-refresh', FAEHUB_GMAIL_SENDER='sender@gmail.com')
        with app.app_context(), patch.dict(os.environ, env, clear=True), patch.object(gmail_mail, 'send') as send:
            self.assertTrue(enrollment.mail_configured())
            enrollment.send_invitation_email('student@example.com', 'fake-invite-token', 'fake-id')
        self.assertEqual(send.call_args.args[0], 'student@example.com')
        self.assertIn('/ativar#convite=fake-invite-token', send.call_args.args[2])
        self.assertIn('Ativar minha conta', send.call_args.args[3])
        with patch.dict(os.environ, {'FAEHUB_MAIL_PROVIDER':'unknown'}, clear=True):
            self.assertFalse(enrollment.mail_configured())

    def test_failed_refresh_never_attempts_delivery_or_exposes_secret(self):
        with patch.dict(os.environ, {'FAEHUB_GMAIL_CLIENT_ID':'fake', 'FAEHUB_GMAIL_CLIENT_SECRET':'private-test', 'FAEHUB_GMAIL_REFRESH_TOKEN':'fake'}), patch.object(gmail_mail, 'urlopen', side_effect=OSError('private-test')) as transport:
            with self.assertRaises(ValueError) as failure:
                gmail_mail.send('student@example.com', 'Convite', 'Texto', '<b>Convite</b>')
            self.assertNotIn('private-test', str(failure.exception))
            self.assertEqual(transport.call_count, 1)
