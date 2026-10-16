"""Generate NEW operator secrets into a private directory, never stdout/Git.

Never use this to rotate keys on an installation with existing encrypted data.
"""
import argparse
import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args()
    folder=args.output_dir.resolve();root=Path(__file__).resolve().parents[1]
    if folder==root or root in folder.parents:
        raise SystemExit('Escolha uma pasta privada fora do repositório e fora de pastas compartilhadas.')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    target=folder/'security.env'
    values=dict(FAEHUB_MFA_ENCRYPTION_KEY=Fernet.generate_key().decode(),
                FAEHUB_BACKUP_KEY=base64.urlsafe_b64encode(os.urandom(32)).decode())
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        stream.write(''.join(name+'='+value+'\n' for name,value in values.items()))
    print('Chaves novas salvas em security.env privado. Não foram exibidas. Preserve cópia externa antes de ativar contas.')


if __name__=='__main__':main()
