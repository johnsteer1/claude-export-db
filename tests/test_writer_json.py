"""Tests for claude_export_db.writers.json_."""

from __future__ import annotations

import json

from claude_export_db.writers.json_ import write_json, write_jsonl

from .conftest import build_zip

# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def test_json_valid_output(sample_data, tmp_path):
    """write_json produces a file that parses as valid JSON."""
    out = tmp_path / "out.json"
    write_json(sample_data, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_json_nested_structure(sample_data, tmp_path):
    """JSON output has conversations > messages > content_blocks nesting."""
    out = tmp_path / "out.json"
    write_json(sample_data, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "conversations" in data
    conv = data["conversations"][0]
    assert "messages" in conv
    msg = conv["messages"][0]
    assert "content_blocks" in msg


# ---------------------------------------------------------------------------
# JSONL
# ---------------------------------------------------------------------------


def _make_multi_conv_data():
    """Return ExportData with 3 conversations for JSONL tests."""
    from claude_export_db.parser import parse_export

    convs = []
    for i in range(3):
        convs.append(
            {
                "uuid": f"conv-{i}",
                "name": f"Conversation {i}",
                "summary": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
                "account": {"uuid": "user-1"},
                "chat_messages": [
                    {
                        "uuid": f"msg-{i}",
                        "text": f"Hi {i}",
                        "sender": "human",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Hi {i}",
                                "citations": [],
                                "start_timestamp": "2024-01-01T00:00:00Z",
                                "stop_timestamp": "2024-01-01T00:00:01Z",
                            }
                        ],
                        "attachments": [],
                        "files": [],
                    }
                ],
            }
        )
    zp = build_zip(conversations=convs)
    return parse_export(zp)


def test_jsonl_one_line_per_conversation(tmp_path):
    """JSONL output has one line per conversation."""
    data = _make_multi_conv_data()
    out = tmp_path / "out.jsonl"
    write_jsonl(data, out)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_jsonl_each_line_valid_json(tmp_path):
    """Each line in the JSONL output is valid JSON."""
    data = _make_multi_conv_data()
    out = tmp_path / "out.jsonl"
    write_jsonl(data, out)
    for line in out.read_text(encoding="utf-8").strip().splitlines():
        obj = json.loads(line)
        assert isinstance(obj, dict)
        assert "uuid" in obj
