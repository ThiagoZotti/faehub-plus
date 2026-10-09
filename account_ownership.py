"""Privately provisioned system ownership; never editable through school roles.

The underlying director role keeps the academic shell compatible. Ownership is
an additional authority, effective only after the pinned mailbox is verified.
"""
import database as db


def owner_state(conn=None):
    if conn is None:
        with db.connection() as connection:
            return owner_state(connection)
    row = conn.execute('''SELECT s.value username,e.value email,u.active,
                          COALESCE(ar.role,u.role) role,ai.email identity_email,ai.verified_at
                          FROM enrollment_settings s
                          LEFT JOIN enrollment_settings e ON e.key='system_owner_email'
                          LEFT JOIN users u ON u.username=s.value
                          LEFT JOIN account_roles ar ON ar.username=u.username
                          LEFT JOIN account_identities ai ON ai.username=u.username
                          WHERE s.key='system_owner_username' ''').fetchone()
    if not row:
        return None
    result = dict(row)
    result['verified'] = bool(row['active'] and row['role'] == 'diretor'
                              and row['email'] and row['identity_email'] == row['email']
                              and row['verified_at'])
    return result


def protect_account(conn, actor, username, action, *, email=None):
    """Enforce on the mutation path, including direct service calls.

Pending bootstrap may only prepare/send/cancel its own invitation to the pinned
mailbox. Public demo credentials cannot change that mailbox or gain ownership.
"""
    owner = owner_state(conn)
    if not owner or username != owner['username']:
        return
    if actor != username:
        raise ValueError('Esta conta pertence ao proprietário do sistema e não pode ser alterada pela equipe escolar.')
    if action in {'invite', 'send_invite', 'cancel_invite'}:
        if not owner['email'] or email != owner['email']:
            raise ValueError('O convite do proprietário só pode usar o e-mail reservado na configuração privada.')
        return
    if action == 'update' and owner['verified']:
        return
    raise ValueError('A conta do proprietário é protegida. Ative seu e-mail para editar o nome; bloqueio e recuperação pela secretaria não são permitidos.')


def protect_invitation(conn, actor, invitation_id, action):
    row = conn.execute('SELECT username,email FROM account_invitations WHERE id=?', (invitation_id,)).fetchone()
    if row:
        protect_account(conn, actor, row['username'], action, email=row['email'])


def is_protected(conn, username):
    row = conn.execute("SELECT value FROM enrollment_settings WHERE key='system_owner_username'").fetchone()
    return bool(row and row['value'] == username)


def protect_activation(conn, username, email):
    owner = owner_state(conn)
    if owner and owner['username'] == username and (not owner['email'] or email != owner['email']):
        raise ValueError('O convite não corresponde ao e-mail reservado do proprietário. Solicite a revisão pelo administrador do servidor.')
