from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import json

from personal_os.models import InfluenceItem


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(raw_value: str) -> datetime:
    cleaned = (raw_value or utc_now_iso()).replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


@dataclass
class WriteResult:
    status: str
    markdown_path: Path
    raw_payload_path: Path


def _build_paths(item: InfluenceItem, influence_path: Path) -> Dict[str, Path]:
    external_id = str(item.source_metadata["external_id"])
    timestamp = parse_timestamp(item.source_created_at or item.captured_at)
    date_parts = [timestamp.strftime("%Y"), timestamp.strftime("%m"), timestamp.strftime("%d")]

    markdown_path = influence_path / "x" / date_parts[0] / date_parts[1] / date_parts[2] / (
        f"{external_id}.md"
    )
    raw_payload_path = (
        influence_path
        / "_meta"
        / "raw"
        / "x"
        / date_parts[0]
        / date_parts[1]
        / date_parts[2]
        / f"{external_id}.json"
    )
    return {"markdown_path": markdown_path, "raw_payload_path": raw_payload_path}


def write_influence_item(
    item: InfluenceItem,
    raw_payload: Dict[str, Any],
    influence_path: Path,
    force: bool = False,
    dry_run: bool = False,
) -> WriteResult:
    paths = _build_paths(item, influence_path)
    markdown_path = paths["markdown_path"]
    raw_payload_path = paths["raw_payload_path"]

    item.storage = {
        "markdown_path": markdown_path.relative_to(influence_path).as_posix(),
        "raw_payload_path": raw_payload_path.relative_to(influence_path).as_posix(),
    }

    if markdown_path.exists() and not force:
        return WriteResult("skipped", markdown_path, raw_payload_path)

    if not dry_run:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        raw_payload_path.parent.mkdir(parents=True, exist_ok=True)
        raw_payload_path.write_text(
            json.dumps(raw_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(item.to_markdown(), encoding="utf-8")

    return WriteResult("written", markdown_path, raw_payload_path)


def write_sync_state(state_file: Path, payload: Dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        return
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_sync_state(state_file: Path) -> Dict[str, Any]:
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))
