import unittest
import os
import sqlite3
import tempfile
from types import SimpleNamespace

from fastapi import HTTPException

from docx import Document as DocxDocument

import migrate_db
from access_control import ALL_PERMISSIONS, HR_DEFAULT_PERMISSIONS, permissions_for_role
from routers.absences import _validate_date_range
from schemas import EmployeeCreate
from routers.employees import _employee_payload
from services.document_service import replace_placeholders
from services.ocr_service import TesseractOcrProvider


class EmployeePayloadTests(unittest.TestCase):
    def make_employee(self, birth_date: str) -> EmployeeCreate:
        return EmployeeCreate(
            full_name="Sample Employee",
            iin="123456789012",
            birth_date_full=birth_date,
            position="Technician",
            salary=200000,
            start_date="2026-10-01",
        )

    def test_birth_year_is_derived_from_supported_date_formats(self):
        for value in ("1990-01-02", "02.01.1990", "02/01/1990"):
            with self.subTest(value=value):
                self.assertEqual(_employee_payload(self.make_employee(value))["birth_date"], 1990)


class OcrNameTests(unittest.TestCase):
    def test_document_heading_is_not_selected_as_employee_name(self):
        lines = [
            "ЖЕКЕ КУӘЛІК",
            "РЕСПУБЛИКА ҚАЗАҚСТАН",
            "Фамилия Ivanov Ivan Ivanovich",
        ]
        self.assertEqual(TesseractOcrProvider()._guess_name(lines), "Ivanov Ivan Ivanovich")

    def test_name_parts_are_combined_from_labelled_lines(self):
        lines = [
            "РЕСПУБЛИКА ҚАЗАҚСТАН",
            "ТЕГІ / ФАМИЛИЯ",
            "Ivanov",
            "АТЫ / ИМЯ",
            "Ivan",
            "ӘКЕСІНІҢ АТЫ / ОТЧЕСТВО",
            "Ivanovich",
        ]
        self.assertEqual(
            TesseractOcrProvider()._extract_full_name(lines),
            ("Ivanov Ivan Ivanovich", True),
        )


class IinRecognitionTests(unittest.TestCase):
    def test_iin_ocr_confusions_are_normalized_and_checksum_checked(self):
        provider = TesseractOcrProvider()
        self.assertEqual(provider._extract_iin("ЖСН: OOOIOI5I2341"), ("000101512341", True, True))

    def test_high_confidence_iin_with_valid_birth_date_is_kept_for_hr_review(self):
        provider = TesseractOcrProvider()
        value, confident, checksum_valid = provider._extract_iin(
            "",
            ocr_candidates=[("000101512342", 85)],
        )
        self.assertEqual(value, "000101512342")
        self.assertTrue(confident)
        self.assertFalse(checksum_valid)

    def test_kazakh_identity_fields_are_extracted_from_common_layout(self):
        provider = TesseractOcrProvider()
        text = "\n".join([
            "УДОСТОВЕРЕНИЕ ЛИЧНОСТИ",
            "ФИО",
            "Марғұлан Ұрылатұлы",
            "ИИН",
            "000101512341",
            "Жарамдылық мерзімі",
            "10.12.2021",
        ])
        result = provider._parse(text)
        self.assertEqual(result["full_name"]["value"], "Марғұлан Ұрылатұлы")
        self.assertTrue(result["full_name"]["recognized"])
        self.assertEqual(result["iin"]["value"], "000101512341")
        self.assertTrue(result["iin"]["recognized"])
        self.assertEqual(result["document_expiry_date"]["value"], "10.12.2021")
        self.assertTrue(result["document_expiry_date"]["recognized"])

    def test_expiry_date_defaults_to_ten_year_validity_when_ocr_repeats_issue_date(self):
        provider = TesseractOcrProvider()
        text = "\n".join([
            "Дата выдачи",
            "28.12.2021",
            "Срок действия",
            "28.12.2021",
        ])
        result = provider._parse(text)
        self.assertEqual(result["document_issue_date"]["value"], "28.12.2021")
        self.assertEqual(result["document_expiry_date"]["value"], "28.12.2031")
        self.assertTrue(result["document_expiry_date"]["recognized"])

    def test_expiry_is_taken_from_the_second_date_when_labels_share_one_ocr_line(self):
        provider = TesseractOcrProvider()
        text = "Дата выдачи 28.12.2021 Срок действия 28.12.2021"
        result = provider._parse(text)
        self.assertEqual(result["document_issue_date"]["value"], "28.12.2021")
        self.assertEqual(result["document_expiry_date"]["value"], "28.12.2031")

    def test_real_kazakh_id_range_is_split_into_issue_and_expiry_dates(self):
        provider = TesseractOcrProvider()
        text = "\n".join([
            "БЕРІЛГЕН КУНІ / СРОК ДЕЙСТВИЯ",
            "08.04.2022 - 07.04.2032",
        ])
        result = provider._parse(text)
        self.assertEqual(result["document_issue_date"]["value"], "08.04.2022")
        self.assertEqual(result["document_expiry_date"]["value"], "07.04.2032")


class DocumentTemplateTests(unittest.TestCase):
    def test_placeholders_are_replaced_in_body_tables_and_headers(self):
        document = DocxDocument()
        document.add_paragraph("{{FULL_NAME}} / {{IIN}}")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "{{POSITION}}"
        document.sections[0].header.paragraphs[0].text = "{{COMPANY_NAME}}"

        replace_placeholders(
            document,
            {
                "FULL_NAME": "Sample Employee",
                "IIN": "123456789012",
                "POSITION": "Technician",
                "COMPANY_NAME": "NS System",
            },
        )

        self.assertEqual(document.paragraphs[0].text, "Sample Employee / 123456789012")
        self.assertEqual(document.tables[0].cell(0, 0).text, "Technician")
        self.assertEqual(document.sections[0].header.paragraphs[0].text, "NS System")


class PermissionTests(unittest.TestCase):
    def test_legacy_hr_role_gets_compatible_default_permissions(self):
        role = SimpleNamespace(name="HR", permissions=None)
        self.assertEqual(set(permissions_for_role(role)), HR_DEFAULT_PERMISSIONS)

    def test_admin_role_always_gets_full_permission_catalog(self):
        role = SimpleNamespace(name="Admin", permissions="[]")
        self.assertEqual(set(permissions_for_role(role)), ALL_PERMISSIONS)

    def test_custom_role_ignores_unknown_permissions(self):
        role = SimpleNamespace(name="Payroll", permissions='["employees.view", "root.access"]')
        self.assertEqual(permissions_for_role(role), ["employees.view"])


class AbsenceDateTests(unittest.TestCase):
    def test_valid_single_day_absence_is_allowed(self):
        _validate_date_range("2026-10-02", "2026-10-02")

    def test_end_date_before_start_date_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_date_range("2026-10-03", "2026-10-02")
        self.assertEqual(raised.exception.status_code, 422)

    def test_impossible_calendar_date_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_date_range("2026-02-30", "2026-03-01")
        self.assertEqual(raised.exception.status_code, 422)


class MigrationTests(unittest.TestCase):
    def test_old_role_and_history_tables_receive_new_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "legacy.db")
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    iin TEXT,
                    created_at TEXT
                );
                CREATE TABLE roles (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE employee_history (id INTEGER PRIMARY KEY, employee_id INTEGER, action TEXT);
                """
            )
            connection.close()

            original_db_path = migrate_db.DB_PATH
            migrate_db.DB_PATH = db_path
            try:
                migrate_db.migrate()
            finally:
                migrate_db.DB_PATH = original_db_path

            connection = sqlite3.connect(db_path)
            role_columns = {row[1] for row in connection.execute("PRAGMA table_info(roles)")}
            history_columns = {row[1] for row in connection.execute("PRAGMA table_info(employee_history)")}
            connection.close()
            self.assertIn("permissions", role_columns)
            self.assertTrue({"field_key", "field_label", "old_value", "new_value"}.issubset(history_columns))


if __name__ == "__main__":
    unittest.main()