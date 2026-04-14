import io
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from bookmarks_cli.integrations.x_bookmarks import ApiBookmarkSource, FileBookmarkSource


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

    def test_api_source_surfaces_402_detail_and_file_mode_guidance(self) -> None:
        source = ApiBookmarkSource(
            api_base_url="https://api.x.com/2",
            endpoint_template="/users/{user_id}/bookmarks",
            access_token="token",
            user_id="123",
        )
        error = HTTPError(
            url="https://api.x.com/2/users/123/bookmarks",
            code=402,
            msg="Payment Required",
            hdrs=None,
            fp=io.BytesIO(
                b'{"title":"Usage Cap Exceeded","detail":"Project monthly product cap reached."}'
            ),
        )

        with patch("bookmarks_cli.integrations.x_bookmarks.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as context:
                source.fetch_until_known(None, limit=10)

        message = str(context.exception)
        self.assertIn("status 402", message)
        self.assertIn("Usage Cap Exceeded", message)
        self.assertIn("Project monthly product cap reached.", message)
        self.assertIn("paid access or credits", message)
        self.assertIn("sync x-bookmarks --source file --input /path/to/bookmarks.json", message)


if __name__ == "__main__":
    unittest.main()
