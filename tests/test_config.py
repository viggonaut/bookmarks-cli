import os
import tempfile
import unittest
from pathlib import Path

from bookmarks_cli.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_load_settings_discovers_repo_root_from_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "bookmarks-cli"
            nested = repo / "subdir" / "child"
            package_dir = repo / "bookmarks_cli"
            package_dir.mkdir(parents=True)
            nested.mkdir(parents=True)
            (repo / "pyproject.toml").write_text("[project]\nname='bookmarks-cli'\n", encoding="utf-8")
            (repo / ".env").write_text(
                "INFLUENCE_PATH=~/bookmarks-data-test\nX_CLIENT_ID=test-client-id\n",
                encoding="utf-8",
            )

            original_env = os.environ.copy()
            try:
                os.environ.pop("INFLUENCE_PATH", None)
                os.environ.pop("X_CLIENT_ID", None)
                settings = load_settings(nested)
            finally:
                os.environ.clear()
                os.environ.update(original_env)

            self.assertEqual(settings.repo_root, repo.resolve())
            self.assertEqual(settings.x_client_id, "test-client-id")

    def test_load_settings_prefers_bookmarks_path_over_legacy_influence_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "bookmarks-cli"
            package_dir = repo / "bookmarks_cli"
            package_dir.mkdir(parents=True)
            (repo / "pyproject.toml").write_text("[project]\nname='bookmarks-cli'\n", encoding="utf-8")
            (repo / ".env").write_text(
                "BOOKMARKS_PATH=/tmp/bookmarks-path\nINFLUENCE_PATH=/tmp/influence-path\n",
                encoding="utf-8",
            )

            original_env = os.environ.copy()
            try:
                os.environ.pop("BOOKMARKS_PATH", None)
                os.environ.pop("INFLUENCE_PATH", None)
                settings = load_settings(repo)
            finally:
                os.environ.clear()
                os.environ.update(original_env)

            self.assertEqual(settings.influence_path, Path("/tmp/bookmarks-path").resolve())


if __name__ == "__main__":
    unittest.main()
