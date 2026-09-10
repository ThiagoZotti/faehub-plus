"""Canonical class roster and compatibility mapping for legacy student IDs."""

ROSTER_NAMES = [
    "Alice Maria Car...", "Ana Luiza Azeve...", "Arthur Coelho", "Arthur do Amparo",
    "Bryan Batista S...", "Caike Vitor Sou...", "Caiky David Viei...", "Carlos Eduardo",
    "Davi Garrocho", "Davi Lucas dos...", "Eric Reis da Silva", "Isabely de Mede...",
    "Isaque do Nasc...", "Israel Lopes Ru...", "João Carlos Bo...", "João Paulo Ant...",
    "Jonathan Samuel", "Lucio Barbosa", "Luiz Felipe Cam...", "Marlon Eduardo",
    "Matheus da Silva", "Nicolas dos An...", "Pablo Sousa Ri...", "Renan Soares",
    "Ricardo dos Sa...", "Ryan de Jesus S...", "Saymon da Silva", "Thais Velloso D...",
    "Thiago Souza Zotti", "Tiago de Jesus", "Victor das Neves", "Vinicius Franca",
    "Isabella Ferreira", "Anna Klarah F...",
]

KNOWN_IDS = {
    "Jonathan Samuel": "23092",
    "Marlon Eduardo": "23117",
    "Pablo Sousa Ri...": "23104",
    "Thiago Souza Zotti": "23081",
}


def _build_roster():
    roster = []
    generic_accounts = []
    legacy_ids = {}
    generic_index = 0

    for position, name in enumerate(ROSTER_NAMES):
        student_id = KNOWN_IDS.get(name)
        if student_id is None:
            generic_index += 1
            student_id = f"31{generic_index:03d}"
            username = f"aluno3110_{generic_index:02d}"
            legacy_id = str(23200 + position)
            legacy_ids[legacy_id] = student_id
            generic_accounts.append(
                {
                    "username": username,
                    "name": name,
                    "student_id": student_id,
                    "legacy_id": legacy_id,
                }
            )

        roster.append(
            {
                "id": student_id,
                "nome": name,
                "turma": "3110",
                "nota": round(5.5 + (position * 0.37) % 4.3, 1),
                "freq": 78 + (position * 3) % 22,
            }
        )

    return roster, generic_accounts, legacy_ids


ROSTER, GENERIC_ACCOUNTS, LEGACY_STUDENT_IDS = _build_roster()


def canonical_student_id(student_id):
    """Return the current ID while accepting IDs emitted by older versions."""
    value = str(student_id) if student_id is not None else ""
    return LEGACY_STUDENT_IDS.get(value, value)

