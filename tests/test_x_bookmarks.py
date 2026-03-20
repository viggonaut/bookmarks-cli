import unittest
from pathlib import Path

from personal_os.integrations.x_bookmarks import FileBookmarkSource


class XBookmarkTests(unittest.TestCase):
    def test_file_source_loads_sample(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )
        source = FileBookmarkSource(sample_path)
        bookmarks, metadata = source.fetch(limit=10)

        self.assertEqual(metadata["mode"], "file")
        self.assertEqual(len(bookmarks), 2)
        self.assertEqual(bookmarks[0].external_id, "1899900000000000002")
        self.assertEqual(bookmarks[1].author.handle, "coachx")
        self.assertIn("training", bookmarks[1].hashtags)

    def test_bookmark_converts_to_influence_item(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )
        source = FileBookmarkSource(sample_path)
        bookmarks, _ = source.fetch(limit=1)
        item = bookmarks[0].to_influence_item(processed_at="2026-03-20T12:00:00Z")

        self.assertEqual(item.item_id, "x:1899900000000000002")
        self.assertEqual(item.source_type, "x")
        self.assertEqual(item.capture_kind, "bookmark")
        self.assertIn("agents", item.tags)
        self.assertEqual(item.source_metadata["external_id"], "1899900000000000002")

    def test_file_source_fetch_all_when_limit_is_none(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )
        source = FileBookmarkSource(sample_path)
        bookmarks, metadata = source.fetch(limit=None)

        self.assertEqual(len(bookmarks), 2)
        self.assertTrue(metadata["complete"])

    def test_file_source_fetch_until_known_stops_before_known_id(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )
        source = FileBookmarkSource(sample_path)
        bookmarks, metadata = source.fetch_until_known("1899900000000000001")

        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0].external_id, "1899900000000000002")
        self.assertTrue(metadata["encountered_known_external_id"])

    def test_file_source_fetch_orders_newest_first(self) -> None:
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "x"
            / "samples"
            / "bookmarks.sample.json"
        )
        source = FileBookmarkSource(sample_path)
        bookmarks, _ = source.fetch(limit=None)

        self.assertEqual(bookmarks[0].external_id, "1899900000000000002")
        self.assertEqual(bookmarks[1].external_id, "1899900000000000001")


if __name__ == "__main__":
    unittest.main()
