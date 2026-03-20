import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from unittest.mock import patch

from bookmarks_cli.x_auth import (
    build_authorize_url,
    generate_pkce_pair,
    merge_token_state,
    resolve_api_access,
    token_is_expired,
    write_token_state,
)


class XAuthTests(unittest.TestCase):
    def test_generate_pkce_pair(self) -> None:
        verifier, challenge = generate_pkce_pair()
        self.assertTrue(len(verifier) > 20)
        self.assertTrue(len(challenge) > 20)

    def test_build_authorize_url_contains_expected_fields(self) -> None:
        url = build_authorize_url(
            client_id="client123",
            redirect_uri="http://127.0.0.1:8741/callback",
            scopes="bookmark.read tweet.read users.read offline.access",
            state="state123",
            code_challenge="challenge123",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(query["client_id"][0], "client123")
        self.assertEqual(query["state"][0], "state123")
        self.assertEqual(query["code_challenge_method"][0], "S256")

    def test_merge_token_state_sets_expiry(self) -> None:
        merged = merge_token_state({}, {"access_token": "abc", "refresh_token": "def", "expires_in": 7200})
        self.assertEqual(merged["access_token"], "abc")
        self.assertEqual(merged["refresh_token"], "def")
        self.assertFalse(token_is_expired(merged))

    def test_resolve_api_access_uses_client_id_from_saved_state_for_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "x_oauth.json"
            write_token_state(
                path,
                {
                    "client_id": "saved-client-id",
                    "user_id": "281793699",
                    "access_token": "expired-token",
                    "refresh_token": "refresh-token",
                    "expires_at": "2000-01-01T00:00:00Z",
                },
            )

            with patch("bookmarks_cli.x_auth.refresh_access_token") as refresh_mock:
                refresh_mock.return_value = {
                    "access_token": "fresh-token",
                    "refresh_token": "refresh-token",
                    "expires_in": 7200,
                }
                access_token, user_id, state = resolve_api_access(
                    api_base_url="https://api.x.com/2",
                    client_id=None,
                    explicit_access_token=None,
                    explicit_user_id=None,
                    state_file=path,
                )

            refresh_mock.assert_called_once_with("saved-client-id", "refresh-token")
            self.assertEqual(access_token, "fresh-token")
            self.assertEqual(user_id, "281793699")
            self.assertEqual(state["access_token"], "fresh-token")


if __name__ == "__main__":
    unittest.main()
