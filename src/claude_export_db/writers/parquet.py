from __future__ import annotations

from pathlib import Path

from claude_export_db.models import ExportData, Message


def _extract_text(msg: Message, *, no_thinking: bool) -> str:
    """Concatenate text from text-type content blocks."""
    parts: list[str] = []
    for block in msg.content_blocks:
        if block.type == "text" and block.text is not None:
            parts.append(block.text)
    return "\n\n".join(parts)


def _has_thinking(msg: Message) -> bool:
    return any(b.type == "thinking" for b in msg.content_blocks)


def _has_tool_use(msg: Message) -> bool:
    return any(b.type == "tool_use" for b in msg.content_blocks)


def write_parquet(
    data: ExportData, output_path: Path, *, no_thinking: bool = False
) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "Parquet output requires pyarrow.\n  Install it with: uv add pyarrow"
        ) from None

    columns: dict[str, list] = {
        "conversation_uuid": [],
        "conversation_name": [],
        "conversation_created_at": [],
        "message_uuid": [],
        "sender": [],
        "message_created_at": [],
        "text": [],
        "has_thinking": [],
        "has_tool_use": [],
        "attachment_count": [],
    }

    for conv in data.conversations:
        for msg in conv.messages:
            columns["conversation_uuid"].append(conv.uuid)
            columns["conversation_name"].append(conv.name)
            columns["conversation_created_at"].append(conv.created_at)
            columns["message_uuid"].append(msg.uuid)
            columns["sender"].append(msg.sender)
            columns["message_created_at"].append(msg.created_at)
            columns["text"].append(_extract_text(msg, no_thinking=no_thinking))
            columns["has_thinking"].append(_has_thinking(msg))
            columns["has_tool_use"].append(_has_tool_use(msg))
            columns["attachment_count"].append(len(msg.attachments))

    table = pa.Table.from_pydict(columns)
    pq.write_table(table, output_path)
