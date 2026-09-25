"""Valida a conexão configurada e as tabelas essenciais do FaeHub+."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database  # noqa: E402


REQUIRED_TABLES = (
    "users",
    "academic_years",
    "classes",
    "students",
    "enrollments",
    "subjects",
)


def main() -> int:
    print(f"Backend configurado: {database.database_backend()}")
    if not database.using_postgres():
        print(f"SQLite local: {database.DB_PATH}")
        return 0
    try:
        with database.connection() as connection:
            version = connection.execute("SELECT current_database() AS database_name").fetchone()
            missing = [
                table
                for table in REQUIRED_TABLES
                if not connection.execute(
                    "SELECT to_regclass(?) AS table_name", (f"public.{table}",)
                ).fetchone()["table_name"]
            ]
        if missing:
            print("Tabelas ausentes: " + ", ".join(missing), file=sys.stderr)
            return 1
        print(f"Conexão válida: {version['database_name']}")
        print("Estrutura acadêmica essencial encontrada.")
        return 0
    except Exception as exc:
        print(f"Falha na validação: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
