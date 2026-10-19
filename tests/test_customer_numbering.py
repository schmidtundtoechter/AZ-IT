"""Exercise the shipped Server Script with isolated document/database doubles.

These checks do not replace execution in Frappe's ERPNext 15 sandbox.
"""

import json
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
FIELD = "custom_interne_kundennummer"


class Document:
    name = "CUST-TEST"

    def __init__(self, new=True, number=None):
        self.new = new
        self.values = {FIELD: number}

    def is_new(self):
        return self.new

    def get(self, field):
        return self.values.get(field)

    def set(self, field, value):
        self.values[field] = value


class CustomerNumberingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = json.loads((ROOT / "az_it/fixtures/server_script.json").read_text(encoding="utf-8"))
        cls.record = next(r for r in fixtures if r["name"] == "Customer Internal Number Auto Assignment - Update")
        cls.code = compile(cls.record["script"], "Customer Internal Number Auto Assignment - Update", "exec")

    def run_script(self, doc, highest=None, duplicate=None):
        database = Mock()
        database.sql.return_value = [SimpleNamespace(highest=highest)]
        database.exists.return_value = duplicate

        def throw(message):
            raise ValueError(message)

        exec(self.code, {"doc": doc, "frappe": SimpleNamespace(db=database, throw=throw)})
        return database

    def test_new_customer_number_range(self):
        for highest, expected in [(None, "20000"), (20000, "20001"), (99998, "99999")]:
            with self.subTest(highest=highest):
                doc = Document()
                database = self.run_script(doc, highest=highest)
                self.assertEqual(doc.get(FIELD), expected)
                database.exists.assert_called_once_with("Customer", {FIELD: expected, "name": ["!=", doc.name]})

    def test_existing_customer_without_number_is_unchanged(self):
        doc = Document(new=False)
        database = self.run_script(doc)
        self.assertIsNone(doc.get(FIELD))
        database.sql.assert_not_called()
        database.exists.assert_not_called()

    def test_manual_numbers_are_kept_for_new_and_existing_customers(self):
        for new in (True, False):
            with self.subTest(new=new):
                doc = Document(new=new, number="24567")
                database = self.run_script(doc)
                self.assertEqual(doc.get(FIELD), "24567")
                database.sql.assert_not_called()
                database.exists.assert_called_once()

    def test_duplicates_are_rejected(self):
        for new in (True, False):
            with self.subTest(new=new):
                with self.assertRaisesRegex(ValueError, "24567.*CUST-OTHER"):
                    self.run_script(Document(new=new, number="24567"), duplicate="CUST-OTHER")

    def test_exhausted_range_is_rejected(self):
        doc = Document()
        with self.assertRaisesRegex(ValueError, "20000 bis 99999"):
            self.run_script(doc, highest=99999)
        self.assertIsNone(doc.get(FIELD))

    def test_fixture_activation_and_events(self):
        self.assertEqual(self.record["disabled"], 0)
        self.assertEqual(self.record["reference_doctype"], "Customer")
        self.assertEqual(self.record["doctype_event"], "Before Save")
        clients = json.loads((ROOT / "az_it/fixtures/client_script.json").read_text(encoding="utf-8"))
        for name in ("Internal Customer Series", "Kunde - automatische Kundennummer"):
            matches = [r for r in clients if r["name"] == name]
            self.assertEqual(matches, [], f"Removed client script must not be installed: {name}")
        hooks = ast.parse((ROOT / "az_it/hooks.py").read_text(encoding="utf-8"))
        fixtures = next(ast.literal_eval(node.value) for node in hooks.body
                        if isinstance(node, ast.Assign)
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == "fixtures")
        client_names = next(item["filters"][0][2] for item in fixtures
                            if item["doctype"] == "Client Script")
        self.assertNotIn("Internal Customer Series", client_names)
        self.assertNotIn("Kunde - automatische Kundennummer", client_names)


if __name__ == "__main__":
    unittest.main()
