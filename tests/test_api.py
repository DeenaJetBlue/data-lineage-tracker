import unittest
from unittest import mock

from fastapi import HTTPException

from backend import main, settings


class ApiTest(unittest.TestCase):
    def test_lists_tables_with_their_classes(self):
        tables = main.list_tables()["tables"]
        demo = next(t for t in tables if t["name"] == "DemoTable")
        self.assertEqual([c["name"] for c in demo["classes"]], ["Landing Space", "Process", "HVR Jobs"])
        landing = demo["classes"][0]["sources"]
        self.assertEqual([s["label"] for s in landing], ["ADLS", "NAS", "JbSftp"])

    def test_table_lookup_is_case_insensitive(self):
        self.assertEqual(main.get_table("demotable")["name"], "DemoTable")

    def test_unknown_table_and_source_are_404(self):
        for call in (lambda: main.get_table("Nope"), lambda: main.check_source("DemoTable", "bogus")):
            with self.assertRaises(HTTPException) as caught:
                call()
            self.assertEqual(caught.exception.status_code, 404)

    def test_check_source_returns_a_card(self):
        with mock.patch.object(settings, "DEMO_MODE", True):
            card = main.check_source("DemoTable", "hvr")
        self.assertEqual(card["class_name"], "HVR Jobs")
        self.assertEqual(card["test_script"], "Test/HVR_Jobs.py")


if __name__ == "__main__":
    unittest.main()
