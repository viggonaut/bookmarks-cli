import tempfile
import unittest
from pathlib import Path

from bookmarks_cli.models import Author, InfluenceItem
from bookmarks_cli.query import iter_markdown_items, query_items, search_items


class QueryTests(unittest.TestCase):
    def _write_item(self, root: Path, item: InfluenceItem) -> None:
        external_id = str(item.source_metadata["external_id"])
        markdown_path = root / "2026" / "03" / "20" / f"{external_id}.md"
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(item.to_markdown(), encoding="utf-8")

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
            self._write_item(root, item)

            items = list(iter_markdown_items(root))
            results = query_items(items, text="codex", tags=["agents"], people=["@danshipper"], limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/danshipper/status/1")

    def test_query_items_supports_tokenized_text_matching(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            item = InfluenceItem(
                item_id="x:2",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@builder: AI companion app pattern",
                canonical_url="https://x.com/builder/status/2",
                source_created_at="2026-03-20T16:26:07Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Builder", handle="builder", id="2", url="https://x.com/builder")],
                language="en",
                tags=["x", "bookmark", "companions"],
                themes=["agents"],
                people=["@builder"],
                entities=["AI"],
                summary="A useful pattern for AI companion products.",
                key_ideas=["Companion products need strong memory and character consistency."],
                raw_text_hash="def",
                body_text="The AI companion market is starting to split by use case.",
                source_metadata={"external_id": "2"},
                storage={},
            )
            self._write_item(root, item)

            items = list(iter_markdown_items(root))
            results = query_items(items, text="AI companions", limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/builder/status/2")
            self.assertGreater(results[0].search_score, 0)
            self.assertIn("title", results[0].matched_fields)
            self.assertIn("ai", results[0].matched_terms)
            self.assertIn("companion", results[0].matched_terms)

    def test_query_items_boosts_author_matches_for_natural_language_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            josh_item = InfluenceItem(
                item_id="x:3",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@joshpuckett: AI character products",
                canonical_url="https://x.com/joshpuckett/status/3",
                source_created_at="2026-03-20T16:26:07Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Josh Puckett", handle="joshpuckett", id="3", url="https://x.com/joshpuckett")],
                language="en",
                tags=["x", "bookmark", "ai"],
                themes=["agents"],
                people=["@joshpuckett"],
                entities=["AI"],
                summary="Notes on where AI companions and character apps may go.",
                key_ideas=["Companions need better persistence than chat demos."],
                raw_text_hash="ghi",
                body_text="Character apps are converging with assistant products.",
                source_metadata={"external_id": "3"},
                storage={},
            )
            generic_item = InfluenceItem(
                item_id="x:4",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@other: AI products",
                canonical_url="https://x.com/other/status/4",
                source_created_at="2026-03-19T16:26:07Z",
                captured_at="2026-03-19T17:30:32Z",
                processed_at="2026-03-19T17:30:31Z",
                authors=[Author(name="Other Builder", handle="other", id="4", url="https://x.com/other")],
                language="en",
                tags=["x", "bookmark", "ai"],
                themes=["agents"],
                people=["@other"],
                entities=["AI"],
                summary="A generic AI products post.",
                key_ideas=["Another AI products post."],
                raw_text_hash="jkl",
                body_text="This one focuses on infrastructure and workflow tooling.",
                source_metadata={"external_id": "4"},
                storage={},
            )
            self._write_item(root, josh_item)
            self._write_item(root, generic_item)

            items = list(iter_markdown_items(root))
            results = query_items(items, text="which Josh Puckett AI companions posts", limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/joshpuckett/status/3")
            self.assertIn("authors", results[0].matched_fields)
            self.assertIn("josh", results[0].matched_terms)
            self.assertIn("puckett", results[0].matched_terms)

    def test_search_items_expands_semantic_queries_and_merges_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            item = InfluenceItem(
                item_id="x:5",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@founder: AI character products",
                canonical_url="https://x.com/founder/status/5",
                source_created_at="2026-03-20T16:26:07Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Founder", handle="founder", id="5", url="https://x.com/founder")],
                language="en",
                tags=["x", "bookmark", "ai"],
                themes=["agents", "memory"],
                people=["@founder"],
                entities=["AI"],
                summary="Character products depend on memory and strong product loops.",
                key_ideas=["Character apps are becoming a durable product category."],
                raw_text_hash="mno",
                body_text="Builders are figuring out how character apps retain users.",
                source_metadata={"external_id": "5"},
                storage={},
            )
            self._write_item(root, item)

            items = list(iter_markdown_items(root))
            results = search_items(items, query="AI companions", limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/founder/status/5")
            self.assertGreater(results[0].search_score, 0)
            self.assertIn("expanded", results[0].matched_queries)
            self.assertIn("character", results[0].matched_terms)

    def test_query_and_search_items_support_date_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            older_item = InfluenceItem(
                item_id="x:6",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@garrytan: GStack update",
                canonical_url="https://x.com/garrytan/status/6",
                source_created_at="2026-03-10T12:00:00Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Garry Tan", handle="garrytan", id="6", url="https://x.com/garrytan")],
                language="en",
                tags=["x", "bookmark", "gstack"],
                themes=["startups"],
                people=["@garrytan"],
                entities=["GStack"],
                summary="An older GStack note.",
                key_ideas=["Earlier GStack post."],
                raw_text_hash="pqr",
                body_text="Older GStack context.",
                source_metadata={"external_id": "6"},
                storage={},
            )
            recent_item = InfluenceItem(
                item_id="x:7",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@garrytan: building on GStack",
                canonical_url="https://x.com/garrytan/status/7",
                source_created_at="2026-03-16T12:00:00Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Garry Tan", handle="garrytan", id="7", url="https://x.com/garrytan")],
                language="en",
                tags=["x", "bookmark", "gstack"],
                themes=["startups"],
                people=["@garrytan"],
                entities=["GStack"],
                summary="Recent GStack note.",
                key_ideas=["GStack update from last week."],
                raw_text_hash="stu",
                body_text="Recent GStack context.",
                source_metadata={"external_id": "7"},
                storage={},
            )
            self._write_item(root, older_item)
            self._write_item(root, recent_item)

            items = list(iter_markdown_items(root))
            query_results = query_items(
                items,
                text="gstack",
                date_from="2026-03-14",
                date_to="2026-03-21",
                limit=5,
            )
            search_results = search_items(
                items,
                query="gstack",
                date_from="2026-03-14",
                date_to="2026-03-21",
                limit=5,
            )

            self.assertEqual(len(query_results), 1)
            self.assertEqual(query_results[0].canonical_url, "https://x.com/garrytan/status/7")
            self.assertEqual(len(search_results), 1)
            self.assertEqual(search_results[0].canonical_url, "https://x.com/garrytan/status/7")

    def test_search_items_handles_typos_and_from_author_phrases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            openai_item = InfluenceItem(
                item_id="x:8",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@openai: Symphony launch",
                canonical_url="https://x.com/openai/status/8",
                source_created_at="2026-03-20T12:00:00Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="OpenAI", handle="openai", id="8", url="https://x.com/openai")],
                language="en",
                tags=["x", "bookmark", "ai"],
                themes=["ai"],
                people=["@openai"],
                entities=["Symphony"],
                summary="OpenAI Symphony launch post.",
                key_ideas=["Symphony is now available."],
                raw_text_hash="vwx",
                body_text="Announcing Symphony from OpenAI.",
                source_metadata={"external_id": "8"},
                storage={},
            )
            mention_item = InfluenceItem(
                item_id="x:9",
                source_type="x",
                content_kind="post",
                capture_kind="bookmark",
                title="@dan: OpenAI Symphony thoughts",
                canonical_url="https://x.com/dan/status/9",
                source_created_at="2026-03-20T13:00:00Z",
                captured_at="2026-03-20T17:30:32Z",
                processed_at="2026-03-20T17:30:31Z",
                authors=[Author(name="Dan", handle="dan", id="9", url="https://x.com/dan")],
                language="en",
                tags=["x", "bookmark", "ai"],
                themes=["ai"],
                people=["@dan", "@openai"],
                entities=["Symphony", "OpenAI"],
                summary="Third-party post mentioning OpenAI Symphony.",
                key_ideas=["Dan comments on OpenAI Symphony."],
                raw_text_hash="yz1",
                body_text="This is a third-party mention of OpenAI Symphony.",
                source_metadata={"external_id": "9"},
                storage={},
            )
            self._write_item(root, openai_item)
            self._write_item(root, mention_item)

            items = list(iter_markdown_items(root))
            results = search_items(items, query="recent symphoni from OpenAI", limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].canonical_url, "https://x.com/openai/status/8")
            self.assertIn("author", results[0].matched_queries)


if __name__ == "__main__":
    unittest.main()
