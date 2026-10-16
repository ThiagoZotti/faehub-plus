"""Private health check. --send-self sends only to the configured sender."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gmail_mail


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--env-file',required=True,type=Path)
    parser.add_argument('--send-self',action='store_true')
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.env_file,override=False)
    try:
        if not gmail_mail.configured():
            raise ValueError()
        if args.send_self:
            gmail_mail.send(os.environ['FAEHUB_GMAIL_SENDER'],'FaeHub+ — teste do envio institucional',
                'Este é um teste controlado do envio institucional do FaeHub+. Nenhum convite ou senha foi alterado.',
                '<h1>FaeHub+</h1><p>Teste controlado do envio institucional. Nenhum convite ou senha foi alterado.</p>')
            print('Gmail confirmou a aceitação do teste enviado à própria caixa institucional. Confira recebimento e spam.')
        else:
            gmail_mail.access_token()
            print('Autorização do Gmail confirmada; nenhum e-mail foi enviado.')
    except Exception:
        print('Gmail não confirmado. Revise as variáveis privadas e a autorização da conta; nenhum segredo foi exibido.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
