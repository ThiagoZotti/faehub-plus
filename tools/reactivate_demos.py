"""Private database-operator command. Dry-run by default; never print credentials."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description='Reabrir demos existentes, preservando contas pessoais e proprietário.')
    parser.add_argument('--apply', action='store_true', help='Gravar a reabertura no Supabase configurado.')
    parser.add_argument('--allow-shared-school-data', action='store_true',
                        help='Reconhecer que as demos terão acesso aos dados do app principal.')
    args = parser.parse_args()
    if args.apply and not args.allow_shared_school_data:
        parser.error('--apply exige --allow-shared-school-data: as demos não são isoladas dos dados reais.')
    import database as db
    import account_enrollment as enrollment
    import account_ownership as ownership
    if not db.using_postgres():
        parser.error('Configure FAEHUB_DATABASE_URL para o Supabase; este comando não usa SQLite.')
    with db.connection() as conn:
        plan = enrollment.demo_reactivation_plan(conn)
        owner = ownership.owner_state(conn)
    print('Elegíveis: ' + (', '.join(plan['eligible']) or 'nenhuma'))
    print('Preservadas/ausentes: ' + (', '.join(plan['preserved']) or 'nenhuma'))
    if args.apply:
        if not owner or not owner['verified']:
            parser.error('O proprietário precisa estar ativo e com o e-mail reservado confirmado.')
        enrollment.reactivate_demos(owner['username'])
        print('Reabertura gravada. Senhas e vínculos não foram alterados.')
    else:
        print('Simulação: nenhuma conta foi alterada.')


if __name__ == '__main__':
    main()
