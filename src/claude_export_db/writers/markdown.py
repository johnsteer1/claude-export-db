from __future__ import annotations

import json
import re
from pathlib import Path

from claude_export_db.models import ContentBlock, Conversation, ExportData


def _slugify(name: str) -> str:
    """Convert a conversation name to a filename-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug[:80].rstrip("-")


def _format_date(iso: str) -> str:
    """Extract YYYY-MM-DD from an ISO timestamp."""
    return iso[:10]


def _format_datetime(iso: str) -> str:
    """Extract YYYY-MM-DD HH:MM from an ISO timestamp."""
    # Handle various ISO formats: 2024-07-30T16:06:00Z, etc.
    dt = iso.replace("T", " ").replace("Z", "")
    # Return up to YYYY-MM-DD HH:MM
    return dt[:16]


def _render_content_block(block: ContentBlock) -> str:
    """Render a single content block to markdown."""
    if block.type == "text" and block.text is not None:
        return block.text
    if block.type == "thinking" and block.thinking is not None:
        quoted = "\n".join(f"> {line}" for line in block.thinking.splitlines())
        return f"*thinking:*\n\n{quoted}"
    if block.type == "tool_use":
        tool_name = block.tool_name or "tool"
        input_str = block.tool_input_json or ""
        try:
            formatted = json.dumps(json.loads(input_str), indent=2)
        except (json.JSONDecodeError, TypeError):
            formatted = input_str
        return f"**`{tool_name}`**\n```json\n{formatted}\n```"
    if block.type == "tool_result":
        content = block.tool_result_content or ""
        return f"**Output**\n```\n{content}\n```"
    # Unknown block types: skip or render raw
    if block.raw_json is not None:
        return f"```json\n{block.raw_json}\n```"
    return ""


def _render_conversation(conv: Conversation, *, no_thinking: bool) -> str:
    """Render a full conversation to markdown."""
    lines: list[str] = []
    lines.append(f"# {conv.name}")
    lines.append("")
    lines.append(f"**Date:** {_format_date(conv.created_at)}")
    lines.append(f"**Updated:** {_format_date(conv.updated_at)}")
    lines.append(f"**Messages:** {len(conv.messages)}")
    lines.append("")
    lines.append("---")

    for msg in conv.messages:
        sender = "Human" if msg.sender == "human" else "Assistant"
        timestamp = _format_datetime(msg.created_at)
        lines.append("")
        lines.append(f"**{sender}** \u00b7 {timestamp}")
        lines.append("")

        blocks = msg.content_blocks
        if no_thinking:
            blocks = [b for b in blocks if b.type != "thinking"]

        rendered_blocks: list[str] = []
        for block in blocks:
            rendered = _render_content_block(block)
            if rendered:
                rendered_blocks.append(rendered)

        if rendered_blocks:
            lines.append("\n\n".join(rendered_blocks))
        else:
            # Fall back to legacy text field
            if msg.text:
                lines.append(msg.text)

        lines.append("")
        lines.append("---")

    return "\n".join(lines) + "\n"


def write_markdown(
    data: ExportData, output_path: Path, *, no_thinking: bool = False
) -> None:
    output_path.mkdir(parents=True, exist_ok=True)

    used_filenames: dict[str, int] = {}

    for conv in data.conversations:
        date_prefix = _format_date(conv.created_at)
        slug = _slugify(conv.name) or "untitled"
        base_name = f"{date_prefix}_{slug}"

        if base_name in used_filenames:
            used_filenames[base_name] += 1
            filename = f"{base_name}_{used_filenames[base_name]}.md"
        else:
            used_filenames[base_name] = 1
            filename = f"{base_name}.md"

        content = _render_conversation(conv, no_thinking=no_thinking)
        (output_path / filename).write_text(content, encoding="utf-8")
