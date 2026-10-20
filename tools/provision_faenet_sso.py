"""One-time bridge key, private files only. Never prints credentials."""
import argparse
import os
from pathlib import Path
import secrets


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];folder=args.output_dir.resolve()
    if folder==root or root in folder.parents or folder.exists():
        raise SystemExit('Escolha uma pasta privada nova, fora do repositório e de pastas compartilhadas.')
    folder.mkdir(parents=True,mode=0o700)
    secret=secrets.token_urlsafe(48)
    values={'faehub.env':'FAEHUB_FAENET_CLIENT_SECRET='+secret+'\n',
            'faenet.env':'FAEHUB_SSO_CLIENT_SECRET='+secret+'\nFAEHUB_LOGIN_REQUIRED=1\n'}
    for name,content in values.items():
        fd=os.open(folder/name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(content)
    print('Configurações privadas criadas. Importar primeiro faehub.env no FaeHub; após Live, faenet.env na FaeNet. Nenhum segredo foi exibido.')


if __name__=='__main__':main()
