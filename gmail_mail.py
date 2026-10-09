"""Server-only Gmail transport. Credentials never enter routes or logs."""
import base64
import json
import os
from email.message import EmailMessage
from email.policy import SMTP
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError


def configured():
    return all(os.getenv(key, '').strip() for key in (
        'FAEHUB_GMAIL_CLIENT_ID', 'FAEHUB_GMAIL_CLIENT_SECRET',
        'FAEHUB_GMAIL_REFRESH_TOKEN', 'FAEHUB_GMAIL_SENDER'))


def send(email, subject, text, html):
    """Refresh authorization, then send once. Never blindly retry delivery."""
    try:
        body = urlencode({
            'client_id': os.environ['FAEHUB_GMAIL_CLIENT_ID'],
            'client_secret': os.environ['FAEHUB_GMAIL_CLIENT_SECRET'],
            'refresh_token': os.environ['FAEHUB_GMAIL_REFRESH_TOKEN'],
            'grant_type': 'refresh_token',
        }).encode('ascii')
        request = Request('https://oauth2.googleapis.com/token', data=body,
                          headers={'Content-Type': 'application/x-www-form-urlencoded'},
                          method='POST')
        with urlopen(request, timeout=10) as response:
            authorization = json.loads(response.read(16384))
        access = authorization.get('access_token') if isinstance(authorization, dict) else None
        if not isinstance(access, str) or not access or '\r' in access or '\n' in access:
            raise ValueError('A autorização do Gmail precisa ser revisada pelo proprietário.')
        message = EmailMessage(policy=SMTP)
        message['From'] = 'FaeHub+ <' + os.environ['FAEHUB_GMAIL_SENDER'].strip() + '>'
        message['To'] = email
        message['Subject'] = subject
        message.set_content(text)
        message.add_alternative(html, subtype='html')
        payload = json.dumps({'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}).encode('utf-8')
        request = Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                          data=payload, method='POST', headers={
                              'Authorization': 'Bearer ' + access,
                              'Content-Type': 'application/json',
                          })
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read(16384))
        if not isinstance(result, dict) or not isinstance(result.get('id'), str) or not result['id']:
            raise ValueError('O Gmail não confirmou o envio. O link não foi liberado.')
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError):
        raise ValueError('O Gmail não confirmou o envio. Confira a autorização e tente novamente mais tarde.') from None
