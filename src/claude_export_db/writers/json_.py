from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from claude_export_db.models import ExportData


def _filter_none(d: dict) -> dict:
    """Remove keys with None values from a dict."""
    return {k: v for k, v in d.items() if v is not None}


def _content_block_dict(block: dict) -> dict:
    """Filter None values from a content block dict."""
    return _filter_none(block)


def _prepare_data(data: ExportData, *, no_thinking: bool) -> dict:
    raw = dataclasses.asdict(data)

    for conv in raw["conversations"]:
        for msg in conv["messages"]:
            blocks = msg["content_blocks"]
            if no_thinking:
                blocks = [b for b in blocks if b.get("type") != "thinking"]
            msg["content_blocks"] = [_content_block_dict(b) for b in blocks]

    return raw


def _prepare_conversation(conv_raw: dict, *, no_thinking: bool) -> dict:
    for msg in conv_raw["messages"]:
        blocks = msg["content_blocks"]
        if no_thinking:
            blocks = [b for b in blocks if b.get("type") != "thinking"]
        msg["content_blocks"] = [_content_block_dict(b) for b in blocks]
    return conv_raw


def write_json(
    data: ExportData, output_path: Path, *, no_thinking: bool = False
) -> None:
    prepared = _prepare_data(data, no_thinking=no_thinking)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prepared, f, ensure_ascii=False, indent=2)


def write_jsonl(
    data: ExportData, output_path: Path, *, no_thinking: bool = False
) -> None:
    raw = dataclasses.asdict(data)

    with open(output_path, "w", encoding="utf-8") as f:
        for conv in raw["conversations"]:
            conv = _prepare_conversation(conv, no_thinking=no_thinking)
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")
