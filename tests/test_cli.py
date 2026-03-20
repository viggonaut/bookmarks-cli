import unittest

from personal_os.cli import build_parser


class CliTests(unittest.TestCase):
    def test_sync_x_bookmarks_source_defaults_to_config_value(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["sync", "x-bookmarks"])

        self.assertIsNone(args.source)

    def test_ingest_x_bookmarks_source_defaults_to_file(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["ingest", "x-bookmarks", "--input", "sample.json"])

        self.assertEqual(args.source, "file")


if __name__ == "__main__":
    unittest.main()
