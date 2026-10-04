"""Importa o banco SQLite atual no Supabase sem apagar dados do destino.

Uso seguro:
    python scripts/migrate_sqlite_to_supabase.py          # apenas inventário
    python scripts/migrate_sqlite_to_supabase.py --apply  # executa a importação
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = Path(os.getenv("FAEHUB_DATABASE", ROOT / "faehub.db"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


TABLES = (
    ("users", ("username", "password_hash", "name", "role", "student_id", "active"), "username"),
    ("grades", ("student_id", "discipline", "n1", "n2", "updated_at"), "student_id, discipline"),
    ("attendance", ("student_id", "class_date", "status"), "student_id, class_date"),
    ("activity_log", ("id", "username", "action", "details", "created_at"), "id"),
    ("institution_settings", ("key", "value"), "key"),
    ("class_settings", ("class_name", "capacity", "shift"), "class_name"),
    ("auth_versions", ("username", "version"), "username"),
    ("messages", ("id", "sender", "recipient", "subject", "body", "is_read", "created_at"), "id"),
    ("exercises", ("id", "teacher", "title", "description", "discipline", "class_name", "due_date", "created_at"), "id"),
    ("submissions", ("id", "exercise_id", "student", "answer", "submitted_at"), "id"),
    ("teacher_assignments", ("teacher", "class_name", "discipline"), "teacher, class_name, discipline"),
    ("notices", ("id", "teacher", "class_name", "title", "body", "priority", "archived", "updated_at"), "id"),
    ("exercise_states", ("exercise_id", "archived"), "exercise_id"),
    ("submission_reviews", ("submission_id", "feedback", "score", "answer_snapshot", "reviewed_at"), "submission_id"),
    ("avatar_styles", ("username", "appearance", "hairstyle", "outfit", "bottom", "shoes"), "username"),
    ("avatar_profiles", ("username", "skin", "hair", "shirt", "accessory", "updated_at"), "username"),
    ("legacy_attendance_archive", ("legacy_student_id", "canonical_student_id", "class_date", "status", "migrated_at"), "legacy_student_id, class_date, status"),
    ("legacy_grade_archive", ("legacy_student_id", "canonical_student_id", "discipline", "n1", "n2", "source_updated_at", "migrated_at"), "legacy_student_id, discipline, source_updated_at, n1, n2"),
    ("seed_markers", ("name",), "name"),
)

BOOLEAN_FIELDS = {
    "users": {"active"},
    "messages": {"is_read"},
    "notices": {"archived"},
    "exercise_states": {"archived"},
}
IDENTITY_TABLES = {"activity_log", "messages", "exercises", "submissions", "notices"}


def existing_tables(source: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in source.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def source_rows(source: sqlite3.Connection, table: str, columns: tuple[str, ...]):
    available = {row[1] for row in source.execute(f'PRAGMA table_info("{table}")')}
    selected = tuple(column for column in columns if column in available)
    if not selected:
        return selected, []
    column_sql = ", ".join(f'"{column}"' for column in selected)
    rows = [tuple(row[column] for column in selected) for row in source.execute(
        f'SELECT {column_sql} FROM "{table}"'
    )]
    boolean_indexes = [selected.index(name) for name in BOOLEAN_FIELDS.get(table, set()) if name in selected]
    if boolean_indexes:
        rows = [
            tuple(bool(value) if index in boolean_indexes and value is not None else value
                  for index, value in enumerate(row))
            for row in rows
        ]
    return selected, rows


def upsert_sql(table: str, columns: tuple[str, ...], conflict: str) -> str:
    names = ", ".join(f'"{name}"' for name in columns)
    values = ", ".join(["%s"] * len(columns))
    identity = " OVERRIDING SYSTEM VALUE" if table in IDENTITY_TABLES and "id" in columns else ""
    conflict_columns = {part.strip() for part in conflict.split(",")}
    updates = [name for name in columns if name not in conflict_columns and name != "id"]
    if updates:
        resolution = "DO UPDATE SET " + ", ".join(
            f'"{name}" = EXCLUDED."{name}"' for name in updates
        )
    else:
        resolution = "DO NOTHING"
    return (
        f'INSERT INTO public."{table}" ({names}){identity} VALUES ({values}) '
        f"ON CONFLICT ({conflict}) {resolution}"
    )


def import_legacy_data(source: sqlite3.Connection, target) -> dict[str, int]:
    migrated: dict[str, int] = {}
    present = existing_tables(source)
    for table, expected_columns, conflict in TABLES:
        if table not in present:
            continue
        columns, rows = source_rows(source, table, expected_columns)
        if rows:
            target.executemany(upsert_sql(table, columns, conflict), rows)
        migrated[table] = len(rows)

    # A primeira versão normalizada já nasce ligada às contas de alunos e à 3110.
    target.execute(
        """
        INSERT INTO public.students (registration, user_username, full_name, active)
        SELECT u.student_id, u.username, u.name, u.active
          FROM public.users u
         WHERE u.role = 'aluno' AND u.student_id IS NOT NULL
        ON CONFLICT (registration) DO UPDATE SET
          user_username = EXCLUDED.user_username,
          full_name = EXCLUDED.full_name,
          active = EXCLUDED.active,
          updated_at = now()
        """
    )
    target.execute(
        """
        INSERT INTO public.enrollments (student_id, class_id, status)
        SELECT s.id, c.id, 'active'
          FROM public.students s
          JOIN public.classes c ON c.code = '3110'
          JOIN public.academic_years y ON y.id = c.academic_year_id AND y.name = '2026'
        ON CONFLICT DO NOTHING
        """
    )
    for table in sorted(IDENTITY_TABLES):
        target.execute(
            f"""
            SELECT setval(
              pg_get_serial_sequence('public.{table}', 'id'),
              COALESCE(MAX(id), 1),
              MAX(id) IS NOT NULL
            ) FROM public.{table}
            """
        )
    return migrated


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra os dados locais do FaeHub+ para o Supabase.")
    parser.add_argument("--apply", action="store_true", help="confirma e executa a importação")
    args = parser.parse_args()

    if not SQLITE_PATH.exists():
        print(f"Banco SQLite não encontrado: {SQLITE_PATH}", file=sys.stderr)
        return 2

    source = sqlite3.connect(SQLITE_PATH)
    source.row_factory = sqlite3.Row
    present = existing_tables(source)
    inventory = {
        table: source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table, _, _ in TABLES
        if table in present
    }
    print(f"Origem: {SQLITE_PATH}")
    for table, count in inventory.items():
        print(f"  {table}: {count}")

    if not args.apply:
        print("\nPrévia concluída. Nada foi alterado. Use --apply após aplicar as migrations.")
        source.close()
        return 0

    database_url = os.getenv("FAEHUB_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        print("Defina FAEHUB_DATABASE_URL no arquivo .env antes de usar --apply.", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("Instale as dependências com: pip install -r requirements.txt", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(database_url, sslmode=os.getenv("FAEHUB_DB_SSLMODE", "require")) as target:
            schema_ready = target.execute(
                "SELECT to_regclass('public.users') IS NOT NULL"
            ).fetchone()[0]
            if not schema_ready:
                raise RuntimeError("A migration inicial ainda não foi aplicada no Supabase.")
            migrated = import_legacy_data(source, target)
        print("\nImportação concluída com transação única:")
        for table, count in migrated.items():
            print(f"  {table}: {count}")
        return 0
    except Exception as exc:
        print(f"Importação cancelada e revertida: {exc}", file=sys.stderr)
        return 1
    finally:
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
