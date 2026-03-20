import unittest

from bookmarks_cli.enrichment import build_title, clean_text, extract_entities, extract_tags, extract_themes


class EnrichmentTests(unittest.TestCase):
    def test_extract_tags_includes_generic_and_domain_tags(self) -> None:
        tags = extract_tags(
            "Portable memory matters for agents and workflows.",
            hashtags=["agents"],
            urls=["https://example.com/post"],
        )
        self.assertEqual(tags[:2], ["x", "bookmark"])
        self.assertIn("agents", tags)
        self.assertIn("workflows", tags)
        self.assertIn("example.com", tags)

    def test_extract_themes_uses_keyword_map(self) -> None:
        themes = extract_themes("Training systems get stronger with boring consistency.")
        self.assertIn("training", themes)
        self.assertIn("systems", themes)
        self.assertNotIn("ai", themes)

    def test_build_title_truncates(self) -> None:
        title = build_title("coachx", "a" * 120)
        self.assertTrue(title.startswith("@coachx: "))
        self.assertTrue(title.endswith("..."))

    def test_clean_text_unescapes_html_entities(self) -> None:
        cleaned = clean_text("Codex &gt; Linear")
        self.assertEqual(cleaned, "Codex > Linear")

    def test_extract_entities_drops_generic_sentence_starters(self) -> None:
        entities = extract_entities(
            "Last week our vibe-coded editor, Proof, went viral. Codex agents debugged the crashes."
        )
        self.assertIn("Proof", entities)
        self.assertIn("Codex", entities)
        self.assertNotIn("Last", entities)


if __name__ == "__main__":
    unittest.main()
