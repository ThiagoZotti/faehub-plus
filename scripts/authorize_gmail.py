"""One-time, local OAuth consent for the institutional sender (standard library).

No secret, authorization code or token is printed. The caller opens authorize.url
in a browser; the mailbox owner personally signs in and approves gmail.send.
"""
import argparse
import base64
import hashlib
import hmac
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

SCOPE = 'https://www.googleapis.com/auth/gmail.send'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    client = json.loads(args.client.read_text(encoding='utf-8-sig')).get('installed', {})
    if not client.get('client_id') or not client.get('client_secret'):
        raise SystemExit('Selecione um JSON de cliente OAuth para computador.')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'render.env').exists():
        raise SystemExit('Escolha uma pasta privada nova; nenhuma credencial será sobrescrita.')
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')
    outcome = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Callback URLs contain private authorization codes.

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            valid = url.path == '/callback' and hmac.compare_digest(query.get('state', [''])[0], state)
            if not valid:
                self.send_error(400, 'Invalid authorization response')
                return
            if 'error' in query:
                outcome['error'] = True
            else:
                code = query.get('code', [''])[0]
                if not code or outcome:
                    self.send_error(400, 'Invalid authorization response')
                    return
                try:
                    data = urlencode({
                        'client_id': client['client_id'], 'client_secret': client['client_secret'],
                        'code': code, 'code_verifier': verifier,
                        'redirect_uri': redirect, 'grant_type': 'authorization_code',
                    }).encode('ascii')
                    request = Request('https://oauth2.googleapis.com/token', data=data,
                                      headers={'Content-Type':'application/x-www-form-urlencoded'}, method='POST')
                    with urlopen(request, timeout=15) as response:
                        token = json.loads(response.read(16384))
                    if (not isinstance(token.get('refresh_token'), str) or not token['refresh_token']
                            or set(token.get('scope', '').split()) != {SCOPE}):
                        raise ValueError('Incomplete or excessive authorization')
                    values = {
                        'FAEHUB_MAIL_PROVIDER':'gmail',
                        'FAEHUB_GMAIL_SENDER':'faetech.sc@gmail.com',
                        'FAEHUB_GMAIL_CLIENT_ID':client['client_id'],
                        'FAEHUB_GMAIL_CLIENT_SECRET':client['client_secret'],
                        'FAEHUB_GMAIL_REFRESH_TOKEN':token['refresh_token'],
                    }
                    if any('\n' in value or '\r' in value for value in values.values()):
                        raise ValueError('Invalid configuration')
                    with (output / 'render.env').open('x', encoding='utf-8') as saved:
                        saved.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
                    outcome['success'] = True
                except Exception:
                    outcome['error'] = True  # Never expose provider responses or credentials.
            text = ('Autorização recebida. Pode fechar esta aba. A configuração foi salva em arquivo privado.'
                    if outcome.get('success') else 'Autorização não concluída. Volte ao Codex para revisar a configuração.')
            body = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>FaeHub — Gmail</title>'
                    '<h1>FaeHub+</h1><p>' + text + '</p></html>').encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(('127.0.0.1', 0), Callback)
    server.timeout = 1
    redirect = 'http://127.0.0.1:' + str(server.server_port) + '/callback'
    authorization = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id':client['client_id'], 'redirect_uri':redirect, 'response_type':'code',
        'scope':SCOPE, 'state':state, 'code_challenge':challenge,
        'code_challenge_method':'S256', 'access_type':'offline',
        'prompt':'consent select_account', 'login_hint':'faetech.sc@gmail.com',
        'include_granted_scopes':'false',
    })
    (output / 'authorize.url').write_text(authorization, encoding='utf-8')
    print('Aguardando autorização pessoal no Google (até 15 minutos).', flush=True)
    deadline = time.monotonic() + 900
    try:
        while not outcome and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
        (output / 'authorize.url').unlink(missing_ok=True)
    print('Autorização concluída; configuração privada salva.' if outcome.get('success')
          else 'Autorização pendente ou recusada; nenhum segredo foi exibido.', flush=True)


if __name__ == '__main__':
    main()
