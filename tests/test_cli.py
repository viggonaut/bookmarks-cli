import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from bookmarks_cli.cli import build_parser, main


class CliTests(unittest.TestCase):
    def test_sync_x_bookmarks_source_defaults_to_config_value(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["sync", "x-bookmarks"])

        self.assertIsNone(args.source)

    def test_ingest_x_bookmarks_source_defaults_to_file(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["ingest", "x-bookmarks", "--input", "sample.json"])

        self.assertEqual(args.source, "file")

    def test_main_prints_clean_runtime_error_and_returns_one(self) -> None:
        stderr = io.StringIO()
        with patch("bookmarks_cli.cli._run_x_bookmarks", side_effect=RuntimeError("status 402: Payment Required")):
            with redirect_stderr(stderr):
                exit_code = main(["sync", "x-bookmarks"])

        self.assertEqual(exit_code, 1)
        self.assertIn("error=status 402: Payment Required", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
