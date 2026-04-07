"""Tests for claude_export_db.parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_export_db.parser import ExportError, parse_export

from .conftest import build_zip

# ---------------------------------------------------------------------------
# Happy-path parsing
# ---------------------------------------------------------------------------


def test_parse_valid_zip(sample_data):
    """Standard sample ZIP yields the expected record counts."""
    assert len(sample_data.users) == 1
    assert len(sample_data.projects) == 0
    assert len(sample_data.conversations) == 1
    assert len(sample_data.conversations[0].messages) == 2


# ---------------------------------------------------------------------------
# Error conditions
# ---------------------------------------------------------------------------


def test_parse_missing_conversations_json():
    """Missing conversations.json raises ExportError."""
    zp = build_zip(omit_files={"conversations.json"})
    with pytest.raises(ExportError, match=r"conversations\.json not found"):
        parse_export(zp)


def test_parse_missing_users_json():
    """Missing users.json raises ExportError."""
    zp = build_zip(omit_files={"users.json"})
    with pytest.raises(ExportError, match=r"users\.json not found"):
        parse_export(zp)


def test_parse_not_a_zip(tmp_path: Path):
    """Non-ZIP file raises ExportError."""
    bad = tmp_path / "not_a_zip.zip"
    bad.write_text("this is not a zip")
    with pytest.raises(ExportError, match="Not a valid ZIP"):
        parse_export(bad)


# ---------------------------------------------------------------------------
# Content block parsing
# ---------------------------------------------------------------------------


def test_parse_content_blocks_text(sample_data):
    """Text content block has correct text and citations_json."""
    msg = sample_data.conversations[0].messages[0]  # human "Hello"
    assert len(msg.content_blocks) == 1
    block = msg.content_blocks[0]
    assert block.type == "text"
    assert block.text == "Hello"
    assert block.citations_json == "[]"


def test_parse_content_blocks_thinking(sample_data):
    """Thinking content block has thinking, summaries, cut_off, truncated, signature."""
    msg = sample_data.conversations[0].messages[1]  # assistant
    thinking_block = msg.content_blocks[0]
    assert thinking_block.type == "thinking"
    assert thinking_block.thinking == "User said hello"
    assert json.loads(thinking_block.summaries_json) == [{"summary": "greeting"}]
    assert thinking_block.cut_off is False
    assert thinking_block.truncated is False
    assert thinking_block.signature == "abc123"


def test_parse_content_blocks_tool_use(tool_use_zip):
    """Tool_use block has tool_id, tool_name, tool_input_json."""
    data = parse_export(tool_use_zip)
    msg = data.conversations[0].messages[0]
    block = msg.content_blocks[0]
    assert block.type == "tool_use"
    assert block.tool_id == "tool-call-1"
    assert block.tool_name == "read_file"
    assert json.loads(block.tool_input_json) == {"path": "/tmp/test.txt"}


def test_parse_content_blocks_tool_result(tool_result_zip):
    """Tool_result block has tool_use_id and tool_result_content."""
    data = parse_export(tool_result_zip)
    msg = data.conversations[0].messages[0]
    block = msg.content_blocks[0]
    assert block.type == "tool_result"
    assert block.tool_use_id == "tool-call-1"
    assert block.tool_result_content == "file contents here"


def test_parse_message_missing_content_falls_back_to_text(no_content_zip):
    """Message with no 'content' key synthesizes a text block from 'text'."""
    data = parse_export(no_content_zip)
    msg = data.conversations[0].messages[0]
    assert len(msg.content_blocks) == 1
    block = msg.content_blocks[0]
    assert block.type == "text"
    assert block.text == "Legacy text only"


def test_parse_unknown_content_block_type(unknown_block_zip):
    """Unknown content block type stores raw_json and increments warnings."""
    data = parse_export(unknown_block_zip)
    msg = data.conversations[0].messages[0]
    block = msg.content_blocks[0]
    assert block.type == "magic_sparkle"
    assert block.raw_json is not None
    raw = json.loads(block.raw_json)
    assert raw["data"] == "something new"
    assert data.warning_count == 1


def test_parse_attachments(attachment_zip):
    """Message attachments are parsed correctly."""
    data = parse_export(attachment_zip)
    msg = data.conversations[0].messages[0]
    assert len(msg.attachments) == 1
    att = msg.attachments[0]
    assert att.file_name == "report.pdf"
    assert att.file_size == 12345
    assert att.file_type == "application/pdf"
    assert att.extracted_content == "Report body text"
    assert len(msg.files) == 1
    assert msg.files[0].file_name == "report.pdf"


def test_parse_empty_projects(sample_data):
    """Empty projects array is accepted without error."""
    assert sample_data.projects == []
