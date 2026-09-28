import tempfile
import unittest
from pathlib import Path

from backend.config_table import ConfigError, load_config_table
from backend.sources import SOURCES

HEADER = "Table_Name,Class,Source,Parameter,Value\n"


def write_csv(text, bom=False):
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig" if bom else "utf-8")
    with handle:
        handle.write(text)
    return Path(handle.name)


class ShippedConfigTableTest(unittest.TestCase):
    def test_demo_table_configures_every_source(self):
        demo = load_config_table()["DemoTable"]
        self.assertEqual(set(demo.sources), {source.key for source in SOURCES})

    def test_values_match_the_old_config_file(self):
        demo = load_config_table()["DemoTable"]
        self.assertEqual(demo.sources["dbt"]["Job_ID"], "70437463784804")
        self.assertEqual(demo.sources["adls"]["Root_Folder"], "aerodata/2026/09/08/")
        self.assertTrue(demo.sources["nas"]["Root_Folder"].startswith("\\\\shares.jetblue.com\\Apps\\"))

    def test_rows_are_kept_in_file_order(self):
        rows = load_config_table()["DemoTable"].rows
        self.assertEqual(rows[0], {"class": "Landing Space", "source": "ADLS",
                                   "parameter": "Resource_Group", "value": "jb-rg-eastus2-analytics-prd"})


class ConfigTableValidationTest(unittest.TestCase):
    def load(self, body, **kwargs):
        return load_config_table(write_csv(HEADER + body, **kwargs))

    def assertRejected(self, body, message):
        with self.assertRaises(ConfigError) as caught:
            self.load(body)
        self.assertIn(message, str(caught.exception))

    def test_accepts_excel_bom_aliases_and_any_case(self):
        tables = self.load("T1,process,Azure Data Factory,pipeline_name,p1\n,,,,\nT1,Process,adf,Factory_Name,f1\n",
                           bom=True)
        self.assertEqual(tables["T1"].sources["adf"], {"Pipeline_Name": "p1", "Factory_Name": "f1"})

    def test_rejects_unknown_source(self):
        self.assertRejected("T1,Process,Airflow,Dag,x\n", "unknown Source 'Airflow'")

    def test_rejects_source_in_the_wrong_class(self):
        self.assertRejected("T1,Process,ADLS,Root_Folder,x\n", "ADLS belongs to class 'Landing Space'")

    def test_rejects_unknown_parameter(self):
        self.assertRejected("T1,Landing Space,NAS,Root_Foldr,x\n", "unknown Parameter 'Root_Foldr'")

    def test_rejects_duplicate_parameter(self):
        self.assertRejected("T1,Process,DBT,Job_ID,1\nT1,Process,DBT,Job_ID,2\n", "set twice")

    def test_reports_the_line_number(self):
        self.assertRejected("T1,Process,DBT,Job_ID,1\nT1,Process,DBT,Bad,2\n", "line 3")

    def test_reads_excel_default_csv_encoding(self):
        path = write_csv("")
        path.write_bytes((HEADER + "T1,Landing Space,NAS,Root_Folder,\\\\srv\\Données\n").encode("cp1252"))
        self.assertEqual(load_config_table(path)["T1"].sources["nas"]["Root_Folder"], "\\\\srv\\Données")

    def test_rejects_slash_in_table_name(self):
        self.assertRejected("Finance/GL,Process,DBT,Job_ID,1\n", "can't contain '/'")

    def test_rejects_missing_columns(self):
        with self.assertRaises(ConfigError) as caught:
            load_config_table(write_csv("Table_Name,Source,Value\nT1,DBT,1\n"))
        self.assertIn("missing column(s): Class, Parameter", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
