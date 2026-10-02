import os
import sqlite3

from database import DB_PATH


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _add_column(
    cursor: sqlite3.Cursor,
    table_name: str,
    existing_columns: set[str],
    column_name: str,
    column_type: str,
) -> None:
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        existing_columns.add(column_name)


def _ensure_index(cursor: sqlite3.Cursor, name: str, table: str, column: str) -> None:
    cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({column})")


def migrate():
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not _table_exists(cursor, "employees"):
        conn.close()
        return

    employee_columns = _table_columns(cursor, "employees")

    if "birth_year" in employee_columns and "birth_date" not in employee_columns:
        cursor.execute("ALTER TABLE employees RENAME COLUMN birth_year TO birth_date")
        employee_columns.remove("birth_year")
        employee_columns.add("birth_date")

    for column_name, column_type in [
        ("status", "VARCHAR DEFAULT 'Новый'"),
        ("phone", "VARCHAR"),
        ("email", "VARCHAR"),
        ("address", "VARCHAR"),
        ("contract_type", "VARCHAR"),
        ("work_schedule", "VARCHAR"),
        ("termination_date", "VARCHAR"),
        ("termination_reason", "VARCHAR"),
        ("document_number", "VARCHAR"),
        ("document_issue_date", "VARCHAR"),
        ("document_expiry_date", "VARCHAR"),
        ("is_deleted", "BOOLEAN DEFAULT 0"),
        ("updated_at", "VARCHAR"),
        ("birth_date_full", "VARCHAR"),
        ("identity_file_path", "VARCHAR"),
    ]:
        _add_column(cursor, "employees", employee_columns, column_name, column_type)

    if "birth_full" in employee_columns and "birth_date_full" in employee_columns:
        cursor.execute(
            "UPDATE employees SET birth_date_full = birth_full "
            "WHERE birth_date_full IS NULL AND birth_full IS NOT NULL"
        )

    cursor.execute(
        """
        UPDATE employees
        SET status = CASE
            WHEN status IN ('РќРѕРІС‹Р№', '�����') THEN 'Новый'
            WHEN status = 'Р Р°Р±РѕС‚Р°РµС‚' THEN 'Работает'
            WHEN status = 'РќР° РїСЂРѕРІРµСЂРєРµ' THEN 'На проверке'
            WHEN status = 'РЈРІРѕР»РµРЅ' THEN 'Уволен'
            WHEN status = 'РђСЂС…РёРІ' THEN 'Архив'
            WHEN status IS NULL OR status = '' THEN 'Новый'
            ELSE status
        END
        """
    )
    cursor.execute("UPDATE employees SET updated_at = created_at WHERE updated_at IS NULL")
    _ensure_index(cursor, "ix_employees_iin", "employees", "iin")
    _ensure_index(cursor, "ix_employees_full_name", "employees", "full_name")

    if _table_exists(cursor, "documents"):
        document_columns = _table_columns(cursor, "documents")
        for column_name, column_type in [
            ("template_id", "INTEGER"),
            ("created_by", "INTEGER"),
            ("status", "VARCHAR DEFAULT 'Готов'"),
            ("version", "VARCHAR"),
        ]:
            _add_column(cursor, "documents", document_columns, column_name, column_type)
        cursor.execute(
            """
            UPDATE documents
            SET status = CASE
                WHEN status = 'Р“РѕС‚РѕРІ' THEN 'Готов'
                WHEN status IS NULL OR status = '' THEN 'Готов'
                ELSE status
            END
            """
        )

    if _table_exists(cursor, "document_templates"):
        template_columns = _table_columns(cursor, "document_templates")
        for column_name, column_type in [
            ("description", "TEXT"),
            ("is_active", "BOOLEAN DEFAULT 0"),
            ("updated_at", "VARCHAR"),
        ]:
            _add_column(cursor, "document_templates", template_columns, column_name, column_type)

    if _table_exists(cursor, "audit_logs"):
        audit_columns = _table_columns(cursor, "audit_logs")
        _add_column(cursor, "audit_logs", audit_columns, "details", "TEXT")

    if _table_exists(cursor, "roles"):
        role_columns = _table_columns(cursor, "roles")
        _add_column(cursor, "roles", role_columns, "permissions", "TEXT")

    if _table_exists(cursor, "employee_history"):
        history_columns = _table_columns(cursor, "employee_history")
        for column_name in ("field_key", "field_label", "old_value", "new_value"):
            _add_column(cursor, "employee_history", history_columns, column_name, "TEXT")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
