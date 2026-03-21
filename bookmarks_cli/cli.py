from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from bookmarks_cli.config import Settings, load_settings
from bookmarks_cli.integrations.x_bookmarks import resolve_x_source
from bookmarks_cli.integrations.x_bookmarks import bookmark_from_payload
from bookmarks_cli.query import iter_markdown_items, query_items, search_items
from bookmarks_cli.storage import read_sync_state, write_influence_item, write_sync_state, utc_now_iso
from bookmarks_cli.x_auth import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_authenticated_user,
    generate_pkce_pair,
    generate_state,
    merge_token_state,
    read_token_state,
    resolve_api_access,
    wait_for_auth_code,
    write_token_state,
)


def _add_common_sync_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source",
        choices=["auto", "api", "file"],
        default=None,
        help="Bookmark source. Defaults to the configured source, which is 'api' unless overridden.",
    )
    parser.add_argument("--input", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def _add_common_retrieval_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date-from", default=None, help="Inclusive start date, e.g. 2026-03-14")
    parser.add_argument("--date-to", default=None, help="Inclusive end date, e.g. 2026-03-21")
    parser.add_argument("--days", type=int, default=None, help="Relative trailing window in days")


def _render_why_relevant(item) -> str:
    parts = []
    if item.matched_terms:
        parts.append(f"matched terms: {', '.join(item.matched_terms)}")
    if item.matched_fields:
        parts.append(f"in {', '.join(item.matched_fields)}")
    authors = item.frontmatter.get("authors", [])
    if authors:
        author_labels = []
        for author in authors:
            if not isinstance(author, dict):
                continue
            handle = str(author.get("handle", "")).strip()
            name = str(author.get("name", "")).strip()
            if handle:
                author_labels.append(f"@{handle}")
            elif name:
                author_labels.append(name)
        if author_labels:
            parts.append(f"author: {', '.join(author_labels)}")
    return "; ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bookmarks-cli")
    parser.add_argument("--env-file", default=".env")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("doctor")

    auth_parser = subparsers.add_parser("auth")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_target", required=True)
    auth_subparsers.add_parser("x-status")
    auth_login_parser = auth_subparsers.add_parser("x-login")
    auth_login_parser.add_argument("--client-id", default=None)
    auth_login_parser.add_argument("--redirect-uri", default=None)
    auth_login_parser.add_argument("--scopes", default=None)

    sync_parser = subparsers.add_parser("sync")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_target", required=True)
    sync_x_parser = sync_subparsers.add_parser("x-bookmarks")
    _add_common_sync_flags(sync_x_parser)

    backfill_parser = subparsers.add_parser("backfill")
    backfill_subparsers = backfill_parser.add_subparsers(dest="backfill_target", required=True)
    backfill_x_parser = backfill_subparsers.add_parser("x-bookmarks")
    _add_common_sync_flags(backfill_x_parser)

    ingest_parser = subparsers.add_parser("ingest")
    ingest_subparsers = ingest_parser.add_subparsers(dest="ingest_target", required=True)
    ingest_x_parser = ingest_subparsers.add_parser("x-bookmarks")
    _add_common_sync_flags(ingest_x_parser)
    ingest_x_parser.set_defaults(source="file")

    rebuild_parser = subparsers.add_parser("rebuild")
    rebuild_subparsers = rebuild_parser.add_subparsers(dest="rebuild_target", required=True)
    rebuild_x_parser = rebuild_subparsers.add_parser("x-bookmarks")
    rebuild_x_parser.add_argument("--limit", type=int, default=None)
    rebuild_x_parser.add_argument("--dry-run", action="store_true")

    query_parser = subparsers.add_parser("query")
    query_subparsers = query_parser.add_subparsers(dest="query_target", required=True)
    query_x_parser = query_subparsers.add_parser("x-bookmarks")
    query_x_parser.add_argument("--text", default=None)
    query_x_parser.add_argument("--tag", action="append", default=None)
    query_x_parser.add_argument("--theme", action="append", default=None)
    query_x_parser.add_argument("--person", action="append", default=None)
    query_x_parser.add_argument("--author", default=None)
    _add_common_retrieval_flags(query_x_parser)
    query_x_parser.add_argument("--limit", type=int, default=10)
    query_x_parser.add_argument("--format", choices=["text", "json"], default="text")

    search_parser = subparsers.add_parser("search")
    search_subparsers = search_parser.add_subparsers(dest="search_target", required=True)
    search_x_parser = search_subparsers.add_parser("x-bookmarks")
    search_x_parser.add_argument("--query", required=True)
    search_x_parser.add_argument("--tag", action="append", default=None)
    search_x_parser.add_argument("--theme", action="append", default=None)
    search_x_parser.add_argument("--person", action="append", default=None)
    search_x_parser.add_argument("--author", action="append", default=None)
    _add_common_retrieval_flags(search_x_parser)
    search_x_parser.add_argument("--limit", type=int, default=10)
    search_x_parser.add_argument("--format", choices=["text", "json"], default="text")

    return parser


def _print_doctor(settings: Settings) -> None:
    input_path = settings.x_bookmarks_input_path
    oauth_state = read_token_state(settings.x_oauth_state_file, strict=False)
    print(f"repo_root={settings.repo_root}")
    print(f"archive_path={settings.influence_path}")
    print(f"x_path={settings.x_path}")
    print(f"x_bookmarks_source={settings.x_bookmarks_source}")
    print(f"x_bookmarks_input_path={input_path if input_path else 'unset'}")
    print(f"x_client_id={'set' if settings.x_client_id else 'unset'}")
    print(f"x_redirect_uri={settings.x_redirect_uri}")
    if oauth_state.get("_read_error"):
        print("x_oauth_state=unreadable")
        print(f"x_oauth_error={oauth_state['_read_error']}")
    else:
        print(f"x_oauth_state={'present' if oauth_state else 'absent'}")
    print(
        "x_api_ready={ready}".format(
            ready="yes"
            if settings.x_user_access_token
            or oauth_state.get("access_token")
            or oauth_state.get("refresh_token")
            else "no"
        )
    )
    print(f"archive_path_exists={'yes' if settings.influence_path.exists() else 'no'}")


def _run_init(settings: Settings) -> int:
    settings.initialize_output_dirs()
    print(f"initialized={settings.influence_path}")
    return 0


def _run_x_auth_status(settings: Settings) -> int:
    state = read_token_state(settings.x_oauth_state_file, strict=False)
    print(f"x_oauth_state_file={settings.x_oauth_state_file}")
    if state.get("_read_error"):
        print("present=unreadable")
        print(f"error={state['_read_error']}")
    else:
        print(f"present={'yes' if state else 'no'}")
    if state and not state.get("_read_error"):
        print(f"user_id={state.get('user_id', 'unknown')}")
        print(f"username={state.get('username', 'unknown')}")
        print(f"expires_at={state.get('expires_at', 'unknown')}")
        print(f"has_refresh_token={'yes' if state.get('refresh_token') else 'no'}")
    return 0


def _run_x_auth_login(settings: Settings, args: argparse.Namespace) -> int:
    client_id = args.client_id or settings.x_client_id
    redirect_uri = args.redirect_uri or settings.x_redirect_uri
    scopes = args.scopes or settings.x_oauth_scopes

    if not client_id:
        raise ValueError("X client ID is required. Set X_CLIENT_ID in .env or pass --client-id.")

    settings.initialize_output_dirs()
    code_verifier, code_challenge = generate_pkce_pair()
    state = generate_state()
    auth_url = build_authorize_url(client_id, redirect_uri, scopes, state, code_challenge)

    print(f"Open this URL in your browser:\n{auth_url}\n")
    print(f"Waiting for callback on {redirect_uri} ...")
    code = wait_for_auth_code(redirect_uri, state)
    token_response = exchange_code_for_token(client_id, redirect_uri, code_verifier, code)
    token_state = merge_token_state(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
        },
        token_response,
    )

    user_payload = fetch_authenticated_user(token_state["access_token"], settings.x_api_base_url)
    user = user_payload.get("data", {})
    token_state["user_id"] = user.get("id")
    token_state["username"] = user.get("username")
    token_state["name"] = user.get("name")
    write_token_state(settings.x_oauth_state_file, token_state)

    print(
        "x_login=ok user_id={user_id} username={username} state_file={state_file}".format(
            user_id=token_state.get("user_id"),
            username=token_state.get("username"),
            state_file=settings.x_oauth_state_file,
        )
    )
    return 0


def _resolve_last_seen_bookmark_id(settings: Settings, state_file: Path) -> Optional[str]:
    primary_state = read_sync_state(state_file)
    last_seen_bookmark_id = primary_state.get("last_seen_bookmark_id")
    if last_seen_bookmark_id:
        return last_seen_bookmark_id

    if state_file == settings.x_bookmark_state_file:
        backfill_state = read_sync_state(settings.x_bookmark_backfill_state_file)
        return backfill_state.get("last_seen_bookmark_id")

    return None


def _run_rebuild_x_bookmarks(settings: Settings, args: argparse.Namespace) -> int:
    settings.initialize_output_dirs()
    raw_paths = sorted((settings.raw_path / "x").rglob("*.json"))
    if args.limit:
        raw_paths = raw_paths[: args.limit]

    rebuilt_count = 0
    processed_at = utc_now_iso()
    for raw_path in raw_paths:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        bookmark = bookmark_from_payload(payload)
        item = bookmark.to_influence_item(processed_at=processed_at)
        write_influence_item(
            item=item,
            raw_payload=payload,
            influence_path=settings.influence_path,
            force=True,
            dry_run=args.dry_run,
        )
        rebuilt_count += 1

    print(
        "operation=rebuild source=raw_x rebuilt={rebuilt} archive_path={path}".format(
            rebuilt=rebuilt_count,
            path=settings.influence_path,
        )
    )
    return 0


def _print_query_results(results: list, output_format: str) -> int:
    if output_format == "json":
        payload = [
            {
                "title": item.title,
                "canonical_url": item.canonical_url,
                "summary": item.summary,
                "path": str(item.path),
                "source_created_at": item.source_created_at,
                "search_score": item.search_score,
                "matched_fields": item.matched_fields,
                "matched_terms": item.matched_terms,
                "matched_queries": item.matched_queries,
                "why_relevant": _render_why_relevant(item),
                "authors": item.frontmatter.get("authors", []),
                "tags": item.frontmatter.get("tags", []),
                "themes": item.frontmatter.get("themes", []),
                "people": item.frontmatter.get("people", []),
            }
            for item in results
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    for index, item in enumerate(results, start=1):
        print(f"[{index}] {item.title}")
        if item.canonical_url:
            print(f"URL: {item.canonical_url}")
        print(f"Summary: {item.summary}")
        if item.matched_fields:
            print(f"Matched: {', '.join(item.matched_fields)}")
        if item.matched_queries:
            print(f"Queries: {', '.join(item.matched_queries)}")
        if item.frontmatter.get("authors"):
            author_handles = []
            for author in item.frontmatter.get("authors", []):
                if not isinstance(author, dict):
                    continue
                handle = str(author.get("handle", "")).strip()
                name = str(author.get("name", "")).strip()
                if handle:
                    author_handles.append(f"@{handle}")
                elif name:
                    author_handles.append(name)
            if author_handles:
                print(f"Authors: {', '.join(author_handles)}")
        print(f"Tags: {', '.join(item.frontmatter.get('tags', []))}")
        print(f"Path: {item.path}")
        print("")

    if not results:
        print("No matching X bookmarks found.")
    return 0


def _run_query_x_bookmarks(settings: Settings, args: argparse.Namespace) -> int:
    items = list(iter_markdown_items(settings.x_path))
    results = query_items(
        items,
        text=args.text,
        tags=args.tag,
        themes=args.theme,
        people=args.person,
        author=args.author,
        date_from=args.date_from,
        date_to=args.date_to,
        days=args.days,
        limit=args.limit,
    )
    return _print_query_results(results, args.format)


def _run_search_x_bookmarks(settings: Settings, args: argparse.Namespace) -> int:
    items = list(iter_markdown_items(settings.x_path))
    results = search_items(
        items,
        query=args.query,
        tags=args.tag,
        themes=args.theme,
        people=args.person,
        authors=args.author,
        date_from=args.date_from,
        date_to=args.date_to,
        days=args.days,
        limit=args.limit,
    )
    return _print_query_results(results, args.format)


def _run_x_bookmarks(
    settings: Settings,
    args: argparse.Namespace,
    *,
    mode_name: str,
    limit: Optional[int],
    state_file: Path,
) -> int:
    source_mode = args.source or settings.x_bookmarks_source
    input_path = Path(args.input).expanduser().resolve() if args.input else None

    access_token = None
    user_id = None
    if source_mode in {"api", "auto"} and not input_path and not settings.x_bookmarks_input_path:
        access_token, user_id, _ = resolve_api_access(
            api_base_url=settings.x_api_base_url,
            client_id=settings.x_client_id,
            explicit_access_token=settings.x_user_access_token,
            explicit_user_id=settings.x_user_id,
            state_file=settings.x_oauth_state_file,
        )

    source, resolved_mode = resolve_x_source(
        source_mode=source_mode,
        input_path=input_path,
        env_input_path=settings.x_bookmarks_input_path,
        api_base_url=settings.x_api_base_url,
        endpoint_template=settings.x_bookmarks_endpoint_template,
        access_token=access_token,
        user_id=user_id,
    )

    settings.initialize_output_dirs()
    processed_at = utc_now_iso()
    last_seen_bookmark_id = _resolve_last_seen_bookmark_id(settings, state_file)

    if mode_name == "sync":
        bookmarks, source_metadata = source.fetch_until_known(last_seen_bookmark_id, limit)
    else:
        bookmarks, source_metadata = source.fetch(limit)

    seen_count = 0
    written_count = 0
    skipped_count = 0
    newest_processed_bookmark_id = None

    for bookmark in bookmarks:
        seen_count += 1
        if newest_processed_bookmark_id is None:
            newest_processed_bookmark_id = bookmark.external_id
        item = bookmark.to_influence_item(processed_at=processed_at)
        result = write_influence_item(
            item=item,
            raw_payload=bookmark.raw_payload,
            influence_path=settings.influence_path,
            force=args.force,
            dry_run=args.dry_run,
        )
        if result.status == "written":
            written_count += 1
        elif result.status == "skipped":
            skipped_count += 1

    state_payload = {
        "operation": mode_name,
        "captured_at": processed_at,
        "mode": resolved_mode,
        "limit": limit,
        "last_seen_bookmark_id": newest_processed_bookmark_id or last_seen_bookmark_id,
        "seen_count": seen_count,
        "written_count": written_count,
        "skipped_count": skipped_count,
        "source_metadata": source_metadata,
    }
    write_sync_state(state_file, state_payload, dry_run=args.dry_run)

    print(
        "operation={operation} source={source} seen={seen} written={written} skipped={skipped} archive_path={path}".format(
            operation=mode_name,
            source=resolved_mode,
            seen=seen_count,
            written=written_count,
            skipped=skipped_count,
            path=settings.influence_path,
        )
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(Path.cwd(), env_file=args.env_file)

    if args.command == "init":
        return _run_init(settings)

    if args.command == "doctor":
        _print_doctor(settings)
        return 0

    if args.command == "auth" and args.auth_target == "x-status":
        return _run_x_auth_status(settings)

    if args.command == "auth" and args.auth_target == "x-login":
        return _run_x_auth_login(settings, args)

    if args.command == "sync" and args.sync_target == "x-bookmarks":
        return _run_x_bookmarks(
            settings,
            args,
            mode_name="sync",
            limit=args.limit or settings.x_bookmarks_limit,
            state_file=settings.x_bookmark_state_file,
        )

    if args.command == "backfill" and args.backfill_target == "x-bookmarks":
        return _run_x_bookmarks(
            settings,
            args,
            mode_name="backfill",
            limit=args.limit,
            state_file=settings.x_bookmark_backfill_state_file,
        )

    if args.command == "ingest" and args.ingest_target == "x-bookmarks":
        return _run_x_bookmarks(
            settings,
            args,
            mode_name="ingest",
            limit=args.limit or settings.x_bookmarks_limit,
            state_file=settings.x_bookmark_state_file,
        )

    if args.command == "rebuild" and args.rebuild_target == "x-bookmarks":
        return _run_rebuild_x_bookmarks(settings, args)

    if args.command == "query" and args.query_target == "x-bookmarks":
        return _run_query_x_bookmarks(settings, args)

    if args.command == "search" and args.search_target == "x-bookmarks":
        return _run_search_x_bookmarks(settings, args)

    parser.error("Unsupported command.")
    return 2
