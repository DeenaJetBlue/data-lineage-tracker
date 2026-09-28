import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from backend import runner, settings
from backend.config_table import load_config_table
from backend.sources import SOURCES, SOURCES_BY_KEY, adf, dbt, fivetran, hvr, jbsftp, moveit_tasks
from backend.sources.base import ERROR, FAILED, NOT_CONFIGURED, RUNNING, SUCCESS, WARNING, iso

DEMO = load_config_table()["DemoTable"]


def sample(key):
    return copy.deepcopy(runner.sample_data()[key])


class SampleCardsTest(unittest.TestCase):
    def test_every_source_summarizes_its_sample(self):
        for source in SOURCES:
            with self.subTest(source=source.key):
                result = source.module.summarize(sample(source.key), DEMO.sources[source.key])
                self.assertIn(result["status"], (SUCCESS, RUNNING, WARNING, FAILED))
                self.assertTrue(result["summary"])
                json.dumps(result)  # the API must be able to serialise it

    def test_adf_lists_the_files_inside_list_of_files(self):
        result = adf.summarize(sample("adf"), DEMO.sources["adf"])
        files = next(d for d in result["details"] if d["label"] == "Files in this run")
        self.assertEqual(files["value"], "htrunk20260928.csv")


class StatusMappingTest(unittest.TestCase):
    def test_dbt_error_run_is_failed(self):
        raw = sample("dbt")
        raw["run"].update(status=20, status_humanized="Error")
        self.assertEqual(dbt.summarize(raw, DEMO.sources["dbt"])["status"], FAILED)

    def test_dbt_job_id_tolerates_config_comment(self):
        self.assertEqual(dbt.job_id({"Job_ID": "70437463784804 #Triggered ADF - fuel_master"}), "70437463784804")

    def test_adf_in_progress_is_running_and_no_runs_is_warning(self):
        raw = sample("adf")
        raw["run"]["status"] = "InProgress"
        self.assertEqual(adf.summarize(raw, DEMO.sources["adf"])["status"], RUNNING)
        empty = {"lookback_hours": 24, "run": None, "recent_runs": [], "runs_in_window": 0}
        self.assertEqual(adf.summarize(empty, DEMO.sources["adf"])["status"], WARNING)

    def test_fivetran_status_follows_the_latest_sync(self):
        raw = sample("fivetran")
        raw["syncs"][-1]["status"] = "FAILURE"  # the newest of the three
        self.assertEqual(fivetran.summarize(raw, DEMO.sources["fivetran"])["status"], FAILED)

    def test_moveit_exit_statuses(self):
        self.assertEqual(moveit_tasks.exit_tone("Success"), SUCCESS)
        self.assertEqual(moveit_tasks.exit_tone("Failure"), FAILED)
        self.assertEqual(moveit_tasks.exit_tone("No xfer"), WARNING)

    def test_hvr_states_and_job_filter(self):
        raw = sample("hvr")
        self.assertEqual(hvr.summarize(raw, {"Job_Filter": "*"})["status"], WARNING)  # one SUSPEND
        self.assertEqual(hvr.summarize(raw, {"Job_Filter": "sample_orders*"})["status"], SUCCESS)
        raw["jobs"][0]["state"] = "FAILED"
        self.assertEqual(hvr.summarize(raw, {})["status"], FAILED)

    def test_hvr_lists_problem_jobs_first(self):
        rows = hvr.summarize(sample("hvr"), {})["tables"][0]["rows"]
        self.assertEqual(rows[0]["state"]["text"], "SUSPEND")

    def test_jbsftp_folder_match_ignores_slashes_and_case(self):
        result = jbsftp.summarize(sample("jbsftp"), {"Root_Folder": "home\\qualtrics\\QualtricsSend"})
        self.assertEqual(result["status"], SUCCESS)
        self.assertNotIn("hidden", result["summary"])

    def test_jbsftp_hides_files_from_other_folders(self):
        raw = sample("jbsftp")
        raw["items"].insert(0, {"id": "1", "name": "other.txt", "path": "/Home/Other/other.txt", "size": 1})
        result = jbsftp.summarize(raw, DEMO.sources["jbsftp"])
        names = [row["name"] for row in result["tables"][0]["rows"]]
        self.assertNotIn("other.txt", names)
        self.assertIn("1 from other folders hidden", result["summary"])


class PayloadShapeTest(unittest.TestCase):
    """APIs sometimes send null where a list is expected."""

    def test_moveit_null_items_means_no_runs(self):
        token = mock.Mock(status_code=200, json=lambda: {"access_token": "t"})
        log = mock.Mock(status_code=200, json=lambda: {"items": None})
        env = {"WEBADMIN_SERVER": "srv", "USERNAME": "u", "PASSWORD": "p"}
        with mock.patch.object(moveit_tasks.requests, "post", return_value=token), \
                mock.patch.object(moveit_tasks.requests, "get", return_value=log):
            raw = moveit_tasks.fetch({"Task_ID": "1"}, env)
        self.assertEqual(moveit_tasks.summarize(raw, {"Task_ID": "1"})["status"], WARNING)

    def test_fivetran_null_data_means_no_syncs(self):
        response = mock.Mock(status_code=200, json=lambda: {"data": None})
        env = {"FIVETRAN_API_KEY": "k", "FIVETRAN_API_SECRET": "s"}
        with mock.patch.object(fivetran.requests, "get", return_value=response):
            self.assertEqual(fivetran.fetch({"Connection_ID": "c"}, env)["syncs"], [])


class EnvFileTest(unittest.TestCase):
    def test_moveit_keys_are_read_literally_like_the_test_scripts(self):
        with tempfile.TemporaryDirectory() as folder:
            env_file = Path(folder) / ".env"
            env_file.write_text("# comment\nPASSWORD=abc #123\nTPASSWORD=pa${HOME}ss\nQUOTED=\"x\"\n")
            with mock.patch.object(settings, "ENV_FILE", env_file):
                literal, parsed = settings.read_env(literal=True), settings.read_env()
        self.assertEqual(literal, {"PASSWORD": "abc #123", "TPASSWORD": "pa${HOME}ss", "QUOTED": '"x"'})
        self.assertEqual(parsed["PASSWORD"], "abc")  # python-dotenv, as load_dotenv gives the other scripts
        self.assertEqual(parsed["QUOTED"], "x")

    def test_moveit_sources_use_literal_parsing(self):
        self.assertEqual({s.key for s in SOURCES if s.literal_env}, {"jbsftp", "moveit_tasks"})


class WindowsTest(unittest.TestCase):
    def test_prefers_the_builtin_windows_curl(self):
        with mock.patch.object(jbsftp.sys, "platform", "win32"), \
                mock.patch.dict(jbsftp.os.environ, {"SystemRoot": "C:\\Windows"}), \
                mock.patch.object(jbsftp.Path, "exists", return_value=True):
            binary = jbsftp.curl_binary()
        self.assertTrue(binary.replace("\\", "/").endswith("Windows/System32/curl.exe"), binary)

    def test_frontend_mime_types_ignore_the_registry(self):
        import mimetypes
        from backend import main  # noqa: F401 - registers the types
        self.assertEqual(mimetypes.guess_type("app.js")[0], "text/javascript")
        self.assertEqual(mimetypes.guess_type("styles.css")[0], "text/css")


class IsoTest(unittest.TestCase):
    def test_normalises_api_timestamps(self):
        self.assertEqual(iso("2026-09-25 15:30:58.356445+00:00"), "2026-09-25T15:30:58.356+00:00")  # dbt
        self.assertEqual(iso("2026-09-28T06:48:42.985Z"), "2026-09-28T06:48:42.985+00:00")          # Fivetran
        self.assertEqual(iso("2026-09-28T09:04:13.3928405Z"), "2026-09-28T09:04:13.392+00:00")      # .NET
        self.assertEqual(iso("2026-09-28T05:00:05.500"), "2026-09-28T05:00:05.500")                 # MOVEit, no zone
        self.assertEqual(iso("N/A"), "N/A")
        self.assertIsNone(iso(None))


class RunnerTest(unittest.TestCase):
    def test_unconfigured_source(self):
        self.assertEqual(runner.run_source(SOURCES_BY_KEY["nas"], None)["status"], NOT_CONFIGURED)

    def test_missing_config_value(self):
        with self.assertLogs("backend.runner", level="WARNING"):
            result = runner.run_source(SOURCES_BY_KEY["dbt"], {"Account_ID": "1644", "Job_ID": ""})
        self.assertEqual(result["status"], ERROR)
        self.assertIn("Job_ID", result["error"])

    def test_missing_credentials(self):
        with mock.patch.object(settings, "DEMO_MODE", False), mock.patch.object(settings, "read_env", return_value={}), \
                self.assertLogs("backend.runner", level="WARNING"):
            result = runner.run_source(SOURCES_BY_KEY["fivetran"], DEMO.sources["fivetran"])
        self.assertEqual(result["status"], ERROR)
        self.assertIn("FIVETRAN_API_KEY", result["error"])

    def test_demo_mode_uses_samples_without_credentials(self):
        with mock.patch.object(settings, "DEMO_MODE", True), mock.patch.object(settings, "read_env") as read_env:
            result = runner.run_source(SOURCES_BY_KEY["fivetran"], DEMO.sources["fivetran"])
        read_env.assert_not_called()
        self.assertEqual(result["status"], SUCCESS)
        self.assertTrue(result["demo"])

    def test_network_failure_becomes_a_readable_error(self):
        request = requests.Request("POST", "https://10.0.0.1/api/v1/token").prepare()
        failure = requests.exceptions.ConnectTimeout("long urllib3 message", request=request)
        source = SOURCES_BY_KEY["moveit_tasks"]
        env = {"WEBADMIN_SERVER": "x", "USERNAME": "u", "PASSWORD": "p"}
        with mock.patch.object(settings, "DEMO_MODE", False), mock.patch.object(settings, "read_env", return_value=env), \
                mock.patch.object(source.module, "fetch", side_effect=failure), \
                self.assertLogs("backend.runner", level="WARNING"):
            result = runner.run_source(source, DEMO.sources["moveit_tasks"])
        self.assertEqual(result["error"], "Timed out connecting to 10.0.0.1")
        self.assertIn("AVD", result["hint"])

    def test_missing_nas_folder_explains_itself(self):
        folder = str(Path(tempfile.gettempdir()) / "lifecycle-test-no-such-folder")
        with mock.patch.object(settings, "DEMO_MODE", False), self.assertLogs("backend.runner", level="WARNING"):
            result = runner.run_source(SOURCES_BY_KEY["nas"], {"Root_Folder": folder})
        self.assertEqual(result["status"], ERROR)
        self.assertIn("does not exist or is not accessible", result["error"])


if __name__ == "__main__":
    unittest.main()
