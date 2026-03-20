from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


def _parse_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned)


def _expand_path(raw_value: str) -> Path:
    return Path(raw_value).expanduser().resolve()


def _int_env(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if not raw_value:
        return default
    return int(raw_value)


def _resolve_repo_root(start: Path, env_file: str) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / env_file).exists():
            return candidate
        if (candidate / "pyproject.toml").exists() and (candidate / "bookmarks_cli").exists():
            return candidate
    return start


@dataclass
class Settings:
    repo_root: Path
    influence_path: Path
    x_bookmarks_source: str
    x_bookmarks_input_path: Optional[Path]
    x_api_base_url: str
    x_bookmarks_endpoint_template: str
    x_client_id: Optional[str]
    x_redirect_uri: str
    x_oauth_scopes: str
    x_user_access_token: Optional[str]
    x_user_id: Optional[str]
    x_bookmarks_limit: int

    @property
    def x_path(self) -> Path:
        return self.influence_path / "x"

    @property
    def meta_path(self) -> Path:
        return self.influence_path / "_meta"

    @property
    def raw_path(self) -> Path:
        return self.meta_path / "raw"

    @property
    def state_path(self) -> Path:
        return self.meta_path / "state"

    @property
    def x_bookmark_state_file(self) -> Path:
        return self.state_path / "x_bookmarks.json"

    @property
    def x_bookmark_backfill_state_file(self) -> Path:
        return self.state_path / "x_bookmarks_backfill.json"

    @property
    def x_oauth_state_file(self) -> Path:
        return self.state_path / "x_oauth.json"

    def initialize_output_dirs(self) -> None:
        for path in (
            self.x_path,
            self.raw_path / "x",
            self.state_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_settings(repo_root: Optional[Path] = None, env_file: str = ".env") -> Settings:
    resolved_root = _resolve_repo_root((repo_root or Path.cwd()).resolve(), env_file)
    _parse_env_file(resolved_root / env_file)

    influence_path = _expand_path(
        os.environ.get("BOOKMARKS_PATH")
        or os.environ.get("INFLUENCE_PATH", str(Path("~/bookmarks-archive").expanduser()))
    )
    input_path = os.environ.get("X_BOOKMARKS_INPUT_PATH")

    return Settings(
        repo_root=resolved_root,
        influence_path=influence_path,
        x_bookmarks_source=os.environ.get("X_BOOKMARKS_SOURCE", "api").strip().lower(),
        x_bookmarks_input_path=_expand_path(input_path) if input_path else None,
        x_api_base_url=os.environ.get("X_API_BASE_URL", "https://api.x.com/2").rstrip("/"),
        x_bookmarks_endpoint_template=os.environ.get(
            "X_BOOKMARKS_ENDPOINT_TEMPLATE", "/users/{user_id}/bookmarks"
        ),
        x_client_id=os.environ.get("X_CLIENT_ID"),
        x_redirect_uri=os.environ.get("X_REDIRECT_URI", "http://127.0.0.1:8741/callback"),
        x_oauth_scopes=os.environ.get(
            "X_OAUTH_SCOPES", "bookmark.read tweet.read users.read offline.access"
        ),
        x_user_access_token=os.environ.get("X_USER_ACCESS_TOKEN") or os.environ.get("X_BEARER_TOKEN"),
        x_user_id=os.environ.get("X_USER_ID"),
        x_bookmarks_limit=_int_env("X_BOOKMARKS_LIMIT", 100),
    )
