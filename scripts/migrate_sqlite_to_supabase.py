"""Migra integralmente o SQLite do FaeHub+ para PostgreSQL/Supabase.

Sem ``--apply`` o comando audita a origem. A aplicação usa uma única
transação, preserva chaves, atualiza sequências e valida contagens.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = Path(os.getenv("FAEHUB_DATABASE", ROOT / "faehub.db"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# Pais sempre precedem filhos. A ordem por chave também resolve referências
# internas, como respostas que apontam para mensagens anteriores.
TABLE_ORDER = (
    "users", "activity_log", "institution_settings", "class_settings", "auth_versions",
    "seed_markers", "academic_years", "academic_periods", "courses",
    "subjects", "classes", "class_subjects", "students", "enrollments",
    "teacher_assignments", "teacher_subjects", "schedule_slots",
    "assessments", "assessment_scores", "lessons", "attendance_records",
    "grades", "attendance", "legacy_attendance_archive",
    "legacy_grade_archive", "account_roles", "guardian_links",
    "period_closure_log", "class_diary_entries", "document_requests",
    "pedagogical_interventions", "notifications", "notification_reads",
    "calendar_events", "password_recovery_requests", "notices",
    "internships", "exercises", "exercise_states", "submissions",
    "submission_reviews", "message_groups", "message_group_members",
    "messages", "message_receipts", "message_reactions",
    "communication_states", "file_attachments",
)


def quote_identifier(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Identificador SQL inválido")
    return '"' + value.replace('"', '""') + '"'


def sqlite_tables(source: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in source.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def sqlite_table_info(source: sqlite3.Connection, table: str):
    return source.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()


def sqlite_columns(source: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in sqlite_table_info(source, table)]


def sqlite_primary_key(source: sqlite3.Connection, table: str) -> list[str]:
    rows = sqlite_table_info(source, table)
    return [row[1] for row in sorted(rows, key=lambda item: item[5]) if row[5]]


def postgres_metadata(target) -> dict[str, dict]:
    columns = target.execute(
        """
        SELECT table_name, column_name, data_type, is_identity
          FROM information_schema.columns
         WHERE table_schema = 'public'
         ORDER BY table_name, ordinal_position
        """
    ).fetchall()
    primary_keys = target.execute(
        """
        SELECT tc.table_name, kcu.column_name, kcu.ordinal_position
          FROM information_schema.table_constraints tc
          JOIN information_schema.key_column_usage kcu
            ON kcu.constraint_name = tc.constraint_name
           AND kcu.constraint_schema = tc.constraint_schema
         WHERE tc.table_schema = 'public'
           AND tc.constraint_type = 'PRIMARY KEY'
         ORDER BY tc.table_name, kcu.ordinal_position
        """
    ).fetchall()
    result: dict[str, dict] = {}
    for table, column, data_type, is_identity in columns:
        item = result.setdefault(
            table, {"columns": [], "types": {}, "identity": set(), "pk": []}
        )
        item["columns"].append(column)
        item["types"][column] = data_type
        if is_identity == "YES":
            item["identity"].add(column)
    for table, column, _position in primary_keys:
        result.setdefault(
            table, {"columns": [], "types": {}, "identity": set(), "pk": []}
        )["pk"].append(column)
    return result


def coerce_value(value, target_type: str):
    if value is None:
        return None
    if target_type == "boolean":
        return bool(value)
    if target_type == "bytea" and isinstance(value, memoryview):
        return value.tobytes()
    return value


def rows_for_table(source, table, columns, types, primary_key) -> list[tuple]:
    selected = ", ".join(quote_identifier(column) for column in columns)
    ordering = primary_key or sqlite_primary_key(source, table)
    order_sql = ""
    if ordering:
        order_sql = " ORDER BY " + ", ".join(map(quote_identifier, ordering))
    raw_rows = source.execute(
        f"SELECT {selected} FROM {quote_identifier(table)}{order_sql}"
    ).fetchall()
    return [
        tuple(coerce_value(row[index], types[column]) for index, column in enumerate(columns))
        for row in raw_rows
    ]


def upsert_statement(table: str, columns: list[str], metadata: dict) -> str:
    names = ", ".join(map(quote_identifier, columns))
    placeholders = ", ".join(["%s"] * len(columns))
    override = " OVERRIDING SYSTEM VALUE" if metadata["identity"].intersection(columns) else ""
    primary_key = metadata["pk"]
    if not primary_key:
        raise RuntimeError(f"{table}: tabela sem chave primária")
    conflict = ", ".join(map(quote_identifier, primary_key))
    updates = [
        column for column in columns
        if column not in primary_key and column not in metadata["identity"]
    ]
    resolution = "DO NOTHING"
    if updates:
        resolution = "DO UPDATE SET " + ", ".join(
            f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}"
            for column in updates
        )
    return (
        f"INSERT INTO public.{quote_identifier(table)} ({names}){override} "
        f"VALUES ({placeholders}) ON CONFLICT ({conflict}) {resolution}"
    )


def reset_identity_sequences(target, metadata: dict[str, dict]) -> None:
    for table, item in metadata.items():
        for column in item["identity"]:
            target.execute(
                "SELECT setval(pg_get_serial_sequence(%s, %s), "
                f"COALESCE(MAX({quote_identifier(column)}), 1), "
                f"MAX({quote_identifier(column)}) IS NOT NULL) "
                f"FROM public.{quote_identifier(table)}",
                (f"public.{table}", column),
            )


def validate_sqlite(source: sqlite3.Connection) -> None:
    integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite reprovado no integrity_check: {integrity}")
    foreign_key_errors = source.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(
            f"SQLite contém {len(foreign_key_errors)} violação(ões) de chave estrangeira"
        )


def ordered_tables(present: set[str]) -> list[str]:
    missing_order = sorted(present.difference(TABLE_ORDER))
    if missing_order:
        raise RuntimeError(
            "Tabelas locais sem ordem de migração: " + ", ".join(missing_order)
        )
    return [table for table in TABLE_ORDER if table in present]


def inventory(source: sqlite3.Connection, tables: Iterable[str]) -> dict[str, int]:
    return {
        table: source.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table)}"
        ).fetchone()[0]
        for table in tables
    }


def migrate(source: sqlite3.Connection, target) -> dict[str, int]:
    validate_sqlite(source)
    tables = ordered_tables(sqlite_tables(source))
    expected = inventory(source, tables)
    metadata = postgres_metadata(target)
    absent = [table for table in tables if table not in metadata]
    if absent:
        raise RuntimeError("Tabelas ausentes no Supabase: " + ", ".join(absent))

    for table in tables:
        source_columns = sqlite_columns(source, table)
        target_columns = metadata[table]["columns"]
        columns = [column for column in source_columns if column in target_columns]
        omitted = sorted(set(source_columns).difference(columns))
        if omitted:
            raise RuntimeError(
                f"{table}: colunas ausentes no Supabase: {', '.join(omitted)}"
            )
        rows = rows_for_table(
            source, table, columns, metadata[table]["types"], metadata[table]["pk"]
        )
        if rows:
            target.executemany(upsert_statement(table, columns, metadata[table]), rows)

    reset_identity_sequences(target, metadata)
    for table, source_count in expected.items():
        target_count = target.execute(
            f"SELECT COUNT(*) FROM public.{quote_identifier(table)}"
        ).fetchone()[0]
        if target_count < source_count:
            raise RuntimeError(
                f"{table}: {source_count} na origem e {target_count} no destino"
            )
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migração integral e transacional do FaeHub+ para Supabase."
    )
    parser.add_argument("--apply", action="store_true", help="executa a importação")
    args = parser.parse_args()
    if not SQLITE_PATH.exists():
        print(f"Banco SQLite não encontrado: {SQLITE_PATH}", file=sys.stderr)
        return 2

    source = sqlite3.connect(SQLITE_PATH)
    try:
        source.row_factory = sqlite3.Row
        validate_sqlite(source)
        tables = ordered_tables(sqlite_tables(source))
        counts = inventory(source, tables)
        print(f"Origem validada: {SQLITE_PATH}")
        print(f"Tabelas: {len(tables)} | Registros: {sum(counts.values())}")
        for table, count in counts.items():
            print(f"  {table}: {count}")
        if not args.apply:
            print("\nPrévia concluída. Nenhum dado foi alterado.")
            return 0

        database_url = os.getenv("FAEHUB_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            print("Defina FAEHUB_DATABASE_URL no .env antes de usar --apply.", file=sys.stderr)
            return 2
        try:
            import psycopg
        except ImportError:
            print("Instale as dependências com: pip install -r requirements.txt", file=sys.stderr)
            return 2
        with psycopg.connect(
            database_url, sslmode=os.getenv("FAEHUB_DB_SSLMODE", "require")
        ) as target:
            migrated = migrate(source, target)
        print("\nMigração concluída e validada em uma única transação:")
        for table, count in migrated.items():
            print(f"  {table}: {count}")
        return 0
    except Exception as exc:
        print(f"Migração cancelada e revertida: {exc}", file=sys.stderr)
        return 1
    finally:
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
