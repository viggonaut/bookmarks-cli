import unittest

from bookmarks_cli.frontmatter import render_frontmatter


class FrontmatterTests(unittest.TestCase):
    def test_render_frontmatter_supports_nested_objects(self) -> None:
        rendered = render_frontmatter(
            {
                "title": "Example",
                "tags": ["one", "two"],
                "nested": {"enabled": True, "count": 2},
            }
        )
        self.assertTrue(rendered.startswith("---\n"))
        self.assertIn('title: "Example"', rendered)
        self.assertIn("- \"one\"", rendered)
        self.assertIn("enabled: true", rendered)


if __name__ == "__main__":
    unittest.main()
