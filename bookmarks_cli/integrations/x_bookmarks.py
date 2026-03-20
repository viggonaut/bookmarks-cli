from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from bookmarks_cli.enrichment import (
    build_title,
    clean_text,
    extract_entities,
    extract_hashtags,
    extract_key_ideas,
    extract_mentions,
    extract_tags,
    extract_themes,
    summarize_text,
    unique,
)
from bookmarks_cli.models import Author, InfluenceItem
from bookmarks_cli.storage import parse_timestamp, utc_now_iso


def _sort_bookmarks_newest_first(bookmarks: List["XBookmark"]) -> List["XBookmark"]:
    return sorted(
        bookmarks,
        key=lambda bookmark: (
            parse_timestamp(bookmark.captured_at),
            parse_timestamp(bookmark.source_created_at),
            bookmark.external_id,
        ),
        reverse=True,
    )


def _first_nonempty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _load_json_like(path: Path) -> Any:
    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        records = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
        return records


def _records_from_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        raise ValueError("Unsupported bookmark payload shape.")

    if "data" in payload and isinstance(payload["data"], list):
        users = {
            user["id"]: user
            for user in payload.get("includes", {}).get("users", [])
            if isinstance(user, dict) and user.get("id")
        }
        records = []
        for item in payload["data"]:
            merged = dict(item)
            author_id = item.get("author_id")
            if author_id and author_id in users and "author" not in merged:
                merged["author"] = users[author_id]
            records.append(merged)
        return records

    for key in ("bookmarks", "results", "items"):
        if key in payload and isinstance(payload[key], list):
            return payload[key]

    return [payload]


def _entities_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return record.get("entities") or record.get("tweet", {}).get("entities") or {}


def _extract_urls(record: Dict[str, Any]) -> List[str]:
    urls = []
    for url_entry in _entities_from_record(record).get("urls", []):
        candidate = _first_nonempty(
            url_entry.get("expanded_url"),
            url_entry.get("unwound_url"),
            url_entry.get("url"),
        )
        if candidate:
            urls.append(candidate)
    return unique(urls)


def _extract_hashtag_values(record: Dict[str, Any], text: str) -> List[str]:
    hashtags = []
    for hashtag_entry in _entities_from_record(record).get("hashtags", []):
        tag = hashtag_entry.get("tag")
        if tag:
            hashtags.append(tag.lower())
    hashtags.extend(extract_hashtags(text))
    return unique(hashtags)


def _extract_mention_values(record: Dict[str, Any], text: str) -> List[str]:
    mentions = []
    for mention_entry in _entities_from_record(record).get("mentions", []):
        username = mention_entry.get("username")
        if username:
            mentions.append(username.lower())
    mentions.extend(extract_mentions(text))
    return unique(mentions)


def _public_metrics(record: Dict[str, Any]) -> Dict[str, int]:
    metrics = record.get("public_metrics", {})
    if metrics:
        return {
            "like_count": int(metrics.get("like_count", 0)),
            "repost_count": int(metrics.get("retweet_count", metrics.get("repost_count", 0))),
            "reply_count": int(metrics.get("reply_count", 0)),
            "quote_count": int(metrics.get("quote_count", 0)),
        }

    return {
        "like_count": int(record.get("favorite_count", 0)),
        "repost_count": int(record.get("retweet_count", 0)),
        "reply_count": int(record.get("reply_count", 0)),
        "quote_count": int(record.get("quote_count", 0)),
    }


@dataclass
class XBookmark:
    external_id: str
    text: str
    source_created_at: str
    captured_at: str
    canonical_url: str
    author: Author
    language: Optional[str]
    hashtags: List[str]
    mentions: List[str]
    urls: List[str]
    public_metrics: Dict[str, int]
    conversation_id: Optional[str]
    raw_payload: Dict[str, Any]

    def to_influence_item(self, processed_at: Optional[str] = None) -> InfluenceItem:
        cleaned_text = clean_text(self.text)
        author_ref = self.author.handle or self.author.name
        people = []
        if self.author.handle:
            people.append(f"@{self.author.handle}")
        elif self.author.name:
            people.append(self.author.name)
        people.extend(f"@{mention}" for mention in self.mentions)

        item = InfluenceItem(
            item_id=f"x:{self.external_id}",
            source_type="x",
            content_kind="post",
            capture_kind="bookmark",
            title=build_title(author_ref if self.author.handle else "", cleaned_text),
            canonical_url=self.canonical_url,
            source_created_at=self.source_created_at,
            captured_at=self.captured_at,
            processed_at=processed_at or utc_now_iso(),
            authors=[self.author],
            language=self.language,
            tags=extract_tags(cleaned_text, self.hashtags, self.urls),
            themes=extract_themes(cleaned_text),
            people=unique(people),
            entities=extract_entities(cleaned_text),
            summary=summarize_text(cleaned_text),
            key_ideas=extract_key_ideas(cleaned_text),
            raw_text_hash=sha256(cleaned_text.encode("utf-8")).hexdigest(),
            body_text=cleaned_text,
            source_metadata={
                "platform": "x",
                "external_id": self.external_id,
                "author_id": self.author.id,
                "author_handle": self.author.handle,
                "conversation_id": self.conversation_id or self.external_id,
                "bookmarked_at": self.captured_at,
                "hashtags": self.hashtags,
                "mentions": self.mentions,
                "urls": self.urls,
                "public_metrics": self.public_metrics,
            },
        )
        return item


def _normalize_record(record: Dict[str, Any]) -> XBookmark:
    tweet = record.get("tweet", record)
    external_id = str(
        _first_nonempty(tweet.get("id"), record.get("id"), record.get("tweet_id"), record.get("rest_id"))
    )
    if not external_id:
        raise ValueError("Bookmark record is missing an id.")

    text = _first_nonempty(
        tweet.get("full_text"),
        tweet.get("text"),
        tweet.get("note_tweet", {}).get("text"),
        record.get("full_text"),
        record.get("text"),
    )
    if not text:
        raise ValueError("Bookmark record is missing text.")

    author_payload = _first_nonempty(tweet.get("author"), record.get("author"), {}) or {}
    author_handle = _first_nonempty(
        author_payload.get("username"),
        author_payload.get("screen_name"),
        record.get("author_username"),
        record.get("username"),
    )
    author_name = _first_nonempty(
        author_payload.get("name"),
        record.get("author_name"),
        author_handle,
        "Unknown author",
    )
    author_id = _first_nonempty(author_payload.get("id"), record.get("author_id"))
    author_url = f"https://x.com/{author_handle}" if author_handle else None

    source_created_at = _first_nonempty(tweet.get("created_at"), record.get("created_at"), utc_now_iso())
    captured_at = _first_nonempty(
        record.get("bookmarked_at"),
        record.get("saved_at"),
        record.get("captured_at"),
        utc_now_iso(),
    )
    canonical_url = _first_nonempty(
        record.get("url"),
        tweet.get("url"),
        f"https://x.com/{author_handle}/status/{external_id}" if author_handle else None,
        f"https://x.com/i/web/status/{external_id}",
    )

    cleaned_text = clean_text(str(text))
    return XBookmark(
        external_id=external_id,
        text=cleaned_text,
        source_created_at=str(source_created_at),
        captured_at=str(captured_at),
        canonical_url=str(canonical_url),
        author=Author(
            id=str(author_id) if author_id is not None else None,
            name=str(author_name),
            handle=str(author_handle) if author_handle is not None else None,
            url=author_url,
        ),
        language=tweet.get("lang") or record.get("lang"),
        hashtags=_extract_hashtag_values(record, cleaned_text),
        mentions=_extract_mention_values(record, cleaned_text),
        urls=_extract_urls(record),
        public_metrics=_public_metrics(tweet),
        conversation_id=_first_nonempty(tweet.get("conversation_id"), record.get("conversation_id")),
        raw_payload=record,
    )


def bookmark_from_payload(payload: Dict[str, Any]) -> XBookmark:
    return _normalize_record(payload)


class FileBookmarkSource:
    def __init__(self, input_path: Path):
        self.input_path = input_path

    def fetch(self, limit: Optional[int]) -> Tuple[List[XBookmark], Dict[str, Any]]:
        payload = _load_json_like(self.input_path)
        records = _records_from_payload(payload)
        bookmarks = _sort_bookmarks_newest_first([_normalize_record(record) for record in records])
        if limit is not None:
            bookmarks = bookmarks[:limit]
        metadata = {
            "mode": "file",
            "input_path": str(self.input_path),
            "complete": True,
        }
        return bookmarks, metadata

    def fetch_until_known(
        self,
        known_external_id: Optional[str],
        limit: Optional[int] = None,
    ) -> Tuple[List[XBookmark], Dict[str, Any]]:
        bookmarks, metadata = self.fetch(limit)
        new_bookmarks = []
        encountered_known = False
        for bookmark in bookmarks:
            if known_external_id and bookmark.external_id == known_external_id:
                encountered_known = True
                break
            new_bookmarks.append(bookmark)
        metadata.update(
            {
                "complete": True,
                "encountered_known_external_id": encountered_known,
                "known_external_id": known_external_id,
            }
        )
        return new_bookmarks, metadata


class ApiBookmarkSource:
    def __init__(
        self,
        api_base_url: str,
        endpoint_template: str,
        access_token: str,
        user_id: str,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.endpoint_template = endpoint_template
        self.access_token = access_token
        self.user_id = user_id

    def _build_url(self, limit: int, next_token: Optional[str]) -> str:
        endpoint = self.endpoint_template.format(user_id=self.user_id)
        params = {
            "max_results": min(limit, 100),
            "expansions": "author_id",
            "tweet.fields": "created_at,lang,entities,public_metrics,conversation_id",
            "user.fields": "name,username",
        }
        if next_token:
            params["pagination_token"] = next_token
        return f"{self.api_base_url}{endpoint}?{urlencode(params)}"

    def fetch(self, limit: Optional[int]) -> Tuple[List[XBookmark], Dict[str, Any]]:
        next_token = None
        bookmarks: List[XBookmark] = []
        pages = 0

        while limit is None or len(bookmarks) < limit:
            remaining = 100 if limit is None else max(limit - len(bookmarks), 1)
            url = self._build_url(remaining, next_token)
            request = Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise RuntimeError(f"X API request failed with status {exc.code}.") from exc
            except URLError as exc:
                raise RuntimeError(f"X API request failed: {exc.reason}.") from exc

            page_records = _records_from_payload(payload)
            bookmarks.extend(_normalize_record(record) for record in page_records)
            next_token = payload.get("meta", {}).get("next_token")
            pages += 1
            if not next_token:
                break
            if not page_records:
                break

        metadata = {
            "mode": "api",
            "pages": pages,
            "next_token": next_token,
            "complete": next_token is None,
        }
        return bookmarks if limit is None else bookmarks[:limit], metadata

    def fetch_until_known(
        self,
        known_external_id: Optional[str],
        limit: Optional[int] = None,
    ) -> Tuple[List[XBookmark], Dict[str, Any]]:
        next_token = None
        bookmarks: List[XBookmark] = []
        pages = 0
        encountered_known = False

        while limit is None or len(bookmarks) < limit:
            remaining = 100 if limit is None else max(limit - len(bookmarks), 1)
            url = self._build_url(remaining, next_token)
            request = Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise RuntimeError(f"X API request failed with status {exc.code}.") from exc
            except URLError as exc:
                raise RuntimeError(f"X API request failed: {exc.reason}.") from exc

            page_records = _records_from_payload(payload)
            normalized_page = [_normalize_record(record) for record in page_records]
            pages += 1

            for bookmark in normalized_page:
                if known_external_id and bookmark.external_id == known_external_id:
                    encountered_known = True
                    break
                bookmarks.append(bookmark)
                if limit is not None and len(bookmarks) >= limit:
                    break

            if encountered_known or (limit is not None and len(bookmarks) >= limit):
                next_token = payload.get("meta", {}).get("next_token")
                break

            next_token = payload.get("meta", {}).get("next_token")
            if not next_token or not normalized_page:
                break

        metadata = {
            "mode": "api",
            "pages": pages,
            "next_token": next_token,
            "complete": encountered_known or next_token is None,
            "encountered_known_external_id": encountered_known,
            "known_external_id": known_external_id,
        }
        return bookmarks, metadata


def resolve_x_source(
    source_mode: str,
    input_path: Optional[Path],
    env_input_path: Optional[Path],
    api_base_url: str,
    endpoint_template: str,
    access_token: Optional[str],
    user_id: Optional[str],
) -> Tuple[Any, str]:
    mode = source_mode
    effective_input_path = input_path or env_input_path

    if mode == "auto":
        if effective_input_path:
            mode = "file"
        elif access_token and user_id:
            mode = "api"
        else:
            raise ValueError(
                "Could not resolve X bookmark source. Provide --input, set X_BOOKMARKS_INPUT_PATH, "
                "or configure X API user auth."
            )

    if mode == "file":
        if not effective_input_path:
            raise ValueError("File mode requires --input or X_BOOKMARKS_INPUT_PATH.")
        return FileBookmarkSource(effective_input_path), mode

    if mode == "api":
        if not access_token or not user_id:
            raise ValueError("API mode requires an X user access token and user id.")
        return ApiBookmarkSource(api_base_url, endpoint_template, access_token, user_id), mode

    raise ValueError(f"Unsupported X bookmark source mode: {source_mode}")
