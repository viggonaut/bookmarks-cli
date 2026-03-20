from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen
import base64
import hashlib
import json
import secrets
import threading
import time


class TokenStateReadError(RuntimeError):
    pass


AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_pkce_pair() -> Tuple[str, str]:
    verifier = _base64url(secrets.token_bytes(48))
    challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def generate_state() -> str:
    return _base64url(secrets.token_bytes(24))


def build_authorize_url(client_id: str, redirect_uri: str, scopes: str, state: str, code_challenge: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        },
        quote_via=quote,
    )
    return f"{AUTHORIZE_URL}?{query}"


def _request_form(url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
    encoded = urlencode(form_data).encode("utf-8")
    request = Request(url, data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"X OAuth request failed with status {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"X OAuth request failed: {exc.reason}") from exc


def _request_json(url: str, access_token: str) -> Dict[str, Any]:
    request = Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"X API request failed with status {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"X API request failed: {exc.reason}") from exc


def exchange_code_for_token(
    client_id: str,
    redirect_uri: str,
    code_verifier: str,
    code: str,
) -> Dict[str, Any]:
    return _request_form(
        TOKEN_URL,
        {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )


def refresh_access_token(client_id: str, refresh_token: str) -> Dict[str, Any]:
    return _request_form(
        TOKEN_URL,
        {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": client_id,
        },
    )


def fetch_authenticated_user(access_token: str, api_base_url: str) -> Dict[str, Any]:
    return _request_json(f"{api_base_url.rstrip('/')}/users/me?user.fields=username,name", access_token)


def _expires_at(expires_in: Optional[int]) -> Optional[str]:
    if not expires_in:
        return None
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
    return expiry.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def token_is_expired(token_state: Dict[str, Any], skew_seconds: int = 60) -> bool:
    expires_at = token_state.get("expires_at")
    if not expires_at:
        return False
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) + timedelta(seconds=skew_seconds) >= expiry


def merge_token_state(existing: Dict[str, Any], token_response: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    merged.update(
        {
            "access_token": token_response.get("access_token"),
            "refresh_token": token_response.get("refresh_token", existing.get("refresh_token")),
            "scope": token_response.get("scope", existing.get("scope")),
            "token_type": token_response.get("token_type", existing.get("token_type")),
            "expires_in": token_response.get("expires_in"),
            "expires_at": _expires_at(token_response.get("expires_in")),
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
    )
    return merged


def read_token_state(path: Path, *, strict: bool = True) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        if strict:
            raise TokenStateReadError(f"Could not read token state at {path}: {exc}") from exc
        return {"_read_error": str(exc)}


def write_token_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "PersonalOSOAuth/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        code = query.get("code", [None])[0]
        state = query.get("state", [None])[0]
        error = query.get("error", [None])[0]

        self.server.auth_result = {"code": code, "state": state, "error": error}
        body = "Authentication complete. You can return to the terminal."
        self.send_response(200 if code else 400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return


def wait_for_auth_code(redirect_uri: str, expected_state: str, timeout_seconds: int = 300) -> str:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"

    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("X_REDIRECT_URI must use localhost or 127.0.0.1 for the built-in login flow.")

    class OAuthHTTPServer(HTTPServer):
        auth_result: Optional[Dict[str, Optional[str]]] = None

    server = OAuthHTTPServer((host, port), _OAuthCallbackHandler)

    if path != "/":
        original_handler = server.RequestHandlerClass

        class PathCheckingHandler(original_handler):
            def do_GET(self_inner) -> None:
                if urlparse(self_inner.path).path != path:
                    self_inner.send_response(404)
                    self_inner.end_headers()
                    return
                super().do_GET()

        server.RequestHandlerClass = PathCheckingHandler

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if getattr(server, "auth_result", None):
            result = server.auth_result or {}
            if result.get("error"):
                raise RuntimeError(f"X OAuth authorization failed: {result['error']}")
            if result.get("state") != expected_state:
                raise RuntimeError("X OAuth state mismatch.")
            code = result.get("code")
            if not code:
                raise RuntimeError("X OAuth callback did not include an authorization code.")
            server.server_close()
            return code
        time.sleep(0.2)

    server.server_close()
    raise TimeoutError("Timed out waiting for X OAuth callback.")


def resolve_api_access(
    *,
    api_base_url: str,
    client_id: Optional[str],
    explicit_access_token: Optional[str],
    explicit_user_id: Optional[str],
    state_file: Path,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    if explicit_access_token:
        return explicit_access_token, explicit_user_id, {}

    state = read_token_state(state_file)
    resolved_client_id = client_id or state.get("client_id")
    access_token = state.get("access_token")
    refresh_token = state.get("refresh_token")
    user_id = explicit_user_id or state.get("user_id")

    if not access_token and not refresh_token:
        raise ValueError("No X user access token available. Run `python3 -m bookmarks_cli auth x-login` first.")

    if token_is_expired(state):
        if not resolved_client_id or not refresh_token:
            raise ValueError("X access token is expired and no refresh path is configured.")
        refreshed = refresh_access_token(resolved_client_id, refresh_token)
        state = merge_token_state(state, refreshed)
        access_token = state.get("access_token")
        write_token_state(state_file, state)

    if not access_token:
        raise ValueError("No usable X access token available.")

    if not user_id:
        user_payload = fetch_authenticated_user(access_token, api_base_url)
        user = user_payload.get("data", {})
        state["user_id"] = user.get("id")
        state["username"] = user.get("username")
        state["name"] = user.get("name")
        write_token_state(state_file, state)
        user_id = state.get("user_id")

    return access_token, user_id, state
