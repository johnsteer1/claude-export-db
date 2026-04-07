from __future__ import annotations

import json
import zipfile
from pathlib import Path

from rich.console import Console

from claude_export_db.models import (
    Attachment,
    ContentBlock,
    Conversation,
    ExportData,
    FileRef,
    Message,
    Project,
    User,
)

_stderr = Console(stderr=True)

REQUIRED_FILES = ("users.json", "projects.json", "conversations.json")


class ExportError(Exception):
    """Raised for fatal errors during export parsing."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _warn(msg: str, warnings: list[int]) -> None:
    """Print a warning to stderr and bump the counter."""
    _stderr.print(f"\u26a0 {msg}")
    warnings[0] += 1


def _load_json_array(zf: zipfile.ZipFile, filename: str) -> list[dict]:
    """Read *filename* from the open ZipFile, parse JSON, and validate it is a list."""
    try:
        raw = zf.read(filename)
    except RuntimeError as exc:
        # zipfile raises RuntimeError for password-protected entries
        if "password" in str(exc).lower():
            raise ExportError(
                "ZIP file is password-protected \u2014 cannot read"
            ) from exc
        raise  # pragma: no cover

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ExportError(f"Failed to parse {filename}: {exc}") from exc

    if not isinstance(data, list):
        actual = type(data).__name__
        raise ExportError(
            f"Unexpected format in {filename}: expected array, got {actual}"
        )
    return data


# ---------------------------------------------------------------------------
# Record parsers
# ---------------------------------------------------------------------------


def _parse_users(records: list[dict]) -> list[User]:
    return [
        User(
            uuid=r["uuid"],
            full_name=r.get("full_name", ""),
            email_address=r.get("email_address", ""),
            verified_phone_number=r.get("verified_phone_number"),
        )
        for r in records
    ]


def _parse_projects(records: list[dict]) -> list[Project]:
    results: list[Project] = []
    for r in records:
        creator = r.get("creator") or {}
        results.append(
            Project(
                uuid=r["uuid"],
                name=r.get("name", ""),
                description=r.get("description", ""),
                is_private=r.get("is_private", False),
                is_starter_project=r.get("is_starter_project", False),
                prompt_template=r.get("prompt_template", ""),
                created_at=r.get("created_at", ""),
                updated_at=r.get("updated_at", ""),
                creator_uuid=creator.get("uuid"),
            )
        )
    return results


def _parse_content_block(
    block: dict,
    index: int,
    warnings: list[int],
) -> ContentBlock | None:
    btype = block.get("type")
    if btype is None:
        _warn("Content block missing 'type' — skipping", warnings)
        return None

    cb = ContentBlock(
        type=btype,
        block_index=index,
        start_timestamp=block.get("start_timestamp"),
        stop_timestamp=block.get("stop_timestamp"),
    )

    if btype == "text":
        cb.text = block.get("text")
        citations = block.get("citations")
        if citations is not None:
            cb.citations_json = json.dumps(citations)

    elif btype == "thinking":
        cb.thinking = block.get("thinking")
        summaries = block.get("summaries")
        if summaries is not None:
            cb.summaries_json = json.dumps(summaries)
        cb.cut_off = block.get("cut_off")
        cb.truncated = block.get("truncated")
        cb.signature = block.get("signature")

    elif btype == "tool_use":
        cb.tool_id = block.get("id")
        cb.tool_name = block.get("name")
        tool_input = block.get("input")
        if tool_input is not None:
            cb.tool_input_json = json.dumps(tool_input)

    elif btype == "tool_result":
        cb.tool_use_id = block.get("tool_use_id")
        content = block.get("content")
        if content is not None:
            if isinstance(content, str):
                cb.tool_result_content = content
            else:
                cb.tool_result_content = json.dumps(content)

    else:
        _warn(f"Unknown content block type: {btype!r}", warnings)
        cb.raw_json = json.dumps(block)

    return cb


def _parse_attachments(raw: list[dict] | None) -> list[Attachment]:
    if not raw:
        return []
    return [
        Attachment(
            file_name=a.get("file_name", ""),
            file_size=a.get("file_size", 0),
            file_type=a.get("file_type", ""),
            extracted_content=a.get("extracted_content"),
        )
        for a in raw
    ]


def _parse_files(raw: list[dict] | None) -> list[FileRef]:
    if not raw:
        return []
    return [FileRef(file_name=f.get("file_name", "")) for f in raw]


def _parse_message(
    m: dict,
    warnings: list[int],
) -> Message | None:
    # Required fields
    for key in ("uuid", "sender", "created_at"):
        if key not in m:
            _warn(f"Message missing required field '{key}' — skipping", warnings)
            return None

    # Content blocks
    content_blocks: list[ContentBlock] = []
    raw_content = m.get("content")
    if raw_content is not None and isinstance(raw_content, list):
        for idx, block in enumerate(raw_content):
            cb = _parse_content_block(block, idx, warnings)
            if cb is not None:
                content_blocks.append(cb)
    else:
        # Synthesize a single text block from the text field
        text_val = m.get("text", "")
        content_blocks.append(ContentBlock(type="text", block_index=0, text=text_val))

    return Message(
        uuid=m["uuid"],
        text=m.get("text", ""),
        sender=m["sender"],
        created_at=m["created_at"],
        updated_at=m.get("updated_at", ""),
        content_blocks=content_blocks,
        attachments=_parse_attachments(m.get("attachments")),
        files=_parse_files(m.get("files")),
    )


def _parse_conversations(
    records: list[dict],
    warnings: list[int],
) -> list[Conversation]:
    seen_uuids: set[str] = set()
    results: list[Conversation] = []

    for r in records:
        # Required fields check
        missing = [k for k in ("uuid", "created_at", "chat_messages") if k not in r]
        if missing:
            _warn(
                f"Conversation missing required field(s) {missing} — skipping",
                warnings,
            )
            continue

        uuid = r["uuid"]
        if uuid in seen_uuids:
            _warn(f"Duplicate conversation UUID {uuid!r} — skipping", warnings)
            continue
        seen_uuids.add(uuid)

        # Parse messages
        msg_seen: set[str] = set()
        messages: list[Message] = []
        for m in r.get("chat_messages", []):
            msg = _parse_message(m, warnings)
            if msg is None:
                continue
            if msg.uuid in msg_seen:
                _warn(f"Duplicate message UUID {msg.uuid!r} — skipping", warnings)
                continue
            msg_seen.add(msg.uuid)
            messages.append(msg)

        account = r.get("account") or {}
        results.append(
            Conversation(
                uuid=uuid,
                name=r.get("name", ""),
                summary=r.get("summary", ""),
                created_at=r["created_at"],
                updated_at=r.get("updated_at", ""),
                account_uuid=account.get("uuid"),
                messages=messages,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_export(zip_path: Path, *, verbose: bool = False) -> ExportData:
    """Parse a Claude data-export ZIP and return structured data."""
    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise ExportError(f"File not found: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise ExportError(f"Not a valid ZIP file: {zip_path}")

    # Mutable counter passed by reference (single-element list)
    warnings: list[int] = [0]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())

        # Check for password-protected entries early
        for info in zf.infolist():
            if info.flag_bits & 0x1:
                raise ExportError("ZIP file is password-protected \u2014 cannot read")

        # Validate required files
        for fname in REQUIRED_FILES:
            if fname not in names:
                raise ExportError(f"Invalid export: {fname} not found in ZIP")

        users_raw = _load_json_array(zf, "users.json")
        projects_raw = _load_json_array(zf, "projects.json")
        conversations_raw = _load_json_array(zf, "conversations.json")

    users = _parse_users(users_raw)
    projects = _parse_projects(projects_raw)
    conversations = _parse_conversations(conversations_raw, warnings)

    wcount = warnings[0]
    if wcount and verbose:
        _stderr.print(f"\u26a0 Parsing complete with {wcount} warning(s)")

    return ExportData(
        users=users,
        projects=projects,
        conversations=conversations,
        warning_count=wcount,
    )
