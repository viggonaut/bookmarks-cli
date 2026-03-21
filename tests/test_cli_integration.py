import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bookmarks_cli.cli import main
from bookmarks_cli.storage import read_sync_state


class CliIntegrationTests(unittest.TestCase):
    def test_ingest_then_query_x_bookmarks_via_cli(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = (Path(temp_dir) / "bookmarks-data").resolve()
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(f"BOOKMARKS_PATH={archive_path}\n", encoding="utf-8")

            original_env = os.environ.copy()
            try:
                for key in ("BOOKMARKS_PATH", "INFLUENCE_PATH", "X_BOOKMARKS_INPUT_PATH", "X_BOOKMARKS_SOURCE"):
                    os.environ.pop(key, None)

                ingest_stdout = io.StringIO()
                with redirect_stdout(ingest_stdout):
                    exit_code = main(
                        [
                            "--env-file",
                            str(env_path),
                            "ingest",
                            "x-bookmarks",
                            "--input",
                            str(sample_path),
                        ]
                    )

                self.assertEqual(exit_code, 0)
                self.assertIn("operation=ingest", ingest_stdout.getvalue())
                self.assertIn("source=file", ingest_stdout.getvalue())
                self.assertIn(f"archive_path={archive_path}", ingest_stdout.getvalue())

                markdown_old = archive_path / "x" / "2026" / "03" / "18" / "1899900000000000001.md"
                markdown_new = archive_path / "x" / "2026" / "03" / "19" / "1899900000000000002.md"
                raw_old = archive_path / "_meta" / "raw" / "x" / "2026" / "03" / "18" / "1899900000000000001.json"
                raw_new = archive_path / "_meta" / "raw" / "x" / "2026" / "03" / "19" / "1899900000000000002.json"

                self.assertTrue(markdown_old.exists())
                self.assertTrue(markdown_new.exists())
                self.assertTrue(raw_old.exists())
                self.assertTrue(raw_new.exists())

                state = read_sync_state(archive_path / "_meta" / "state" / "x_bookmarks.json")
                self.assertEqual(state["operation"], "ingest")
                self.assertEqual(state["mode"], "file")
                self.assertEqual(state["seen_count"], 2)
                self.assertEqual(state["written_count"], 2)
                self.assertEqual(state["last_seen_bookmark_id"], "1899900000000000002")

                query_stdout = io.StringIO()
                with redirect_stdout(query_stdout):
                    exit_code = main(
                        [
                            "--env-file",
                            str(env_path),
                            "query",
                            "x-bookmarks",
                            "--text",
                            "portable",
                            "--format",
                            "json",
                        ]
                    )

                self.assertEqual(exit_code, 0)
                payload = json.loads(query_stdout.getvalue())
                self.assertEqual(len(payload), 1)
                self.assertEqual(
                    payload[0]["canonical_url"],
                    "https://x.com/syswriter/status/1899900000000000002",
                )
                self.assertEqual(payload[0]["path"], str(markdown_new))
                self.assertGreater(payload[0]["search_score"], 0)
                self.assertIn("title", payload[0]["matched_fields"])
                self.assertIn("portable", payload[0]["matched_terms"])
                self.assertIn("agents", payload[0]["tags"])

                search_stdout = io.StringIO()
                with redirect_stdout(search_stdout):
                    exit_code = main(
                        [
                            "--env-file",
                            str(env_path),
                            "search",
                            "x-bookmarks",
                            "--query",
                            "portable memory",
                            "--format",
                            "json",
                        ]
                    )

                self.assertEqual(exit_code, 0)
                search_payload = json.loads(search_stdout.getvalue())
                self.assertEqual(len(search_payload), 1)
                self.assertEqual(
                    search_payload[0]["canonical_url"],
                    "https://x.com/syswriter/status/1899900000000000002",
                )
                self.assertIn("exact", search_payload[0]["matched_queries"])
                self.assertGreater(search_payload[0]["search_score"], 0)
            finally:
                os.environ.clear()
                os.environ.update(original_env)


if __name__ == "__main__":
    unittest.main()
