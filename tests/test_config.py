import os
import tempfile
import unittest
from pathlib import Path

from personal_os.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_load_settings_discovers_repo_root_from_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "personal-os"
            nested = repo / "subdir" / "child"
            package_dir = repo / "personal_os"
            package_dir.mkdir(parents=True)
            nested.mkdir(parents=True)
            (repo / "pyproject.toml").write_text("[project]\nname='personal-os'\n", encoding="utf-8")
            (repo / ".env").write_text(
                "INFLUENCE_PATH=~/personal-influence-test\nX_CLIENT_ID=test-client-id\n",
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


if __name__ == "__main__":
    unittest.main()
