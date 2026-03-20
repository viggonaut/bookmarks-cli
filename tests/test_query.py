import tempfile
import unittest
from pathlib import Path

from bookmarks_cli.models import Author, InfluenceItem
from bookmarks_cli.query import iter_markdown_items, query_items


class QueryTests(unittest.TestCase):
    def test_query_items_filters_and_returns_direct_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            item = InfluenceItem(
                item_id="x:1",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@danshipper: Proof and Codex",
                canonical_url="https://x.com/danshipper/status/1",
                source_created_at="2026-03-20T16:26:07Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Dan Shipper", handle="danshipper", id="1", url="https://x.com/danshipper")],
                language="en",
                tags=["x", "bookmark", "agents"],
                themes=["agents"],
                people=["@danshipper"],
                entities=["Proof", "Codex"],
                summary="Proof and Codex post.",
                key_ideas=["Proof and Codex post."],
                raw_text_hash="abc",
                body_text="Proof and Codex are discussed here.",
                source_metadata={"external_id": "1"},
                storage={},
            )
            markdown_path = root / "2026" / "03" / "20" / "1.md"
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(item.to_markdown(), encoding="utf-8")

            items = list(iter_markdown_items(root))
            results = query_items(items, text="codex", tags=["agents"], people=["@danshipper"], limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/danshipper/status/1")


if __name__ == "__main__":
    unittest.main()
