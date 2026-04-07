"""Shared fixtures for claude-export-db tests."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from claude_export_db.parser import parse_export

# ---------------------------------------------------------------------------
# Sample data constants
# ---------------------------------------------------------------------------

SAMPLE_USERS = [
    {
        "uuid": "user-1",
        "full_name": "Test User",
        "email_address": "test@example.com",
        "verified_phone_number": None,
    }
]

SAMPLE_PROJECTS: list[dict] = []

SAMPLE_CONVERSATIONS = [
    {
        "uuid": "conv-1",
        "name": "Test Conversation",
        "summary": "",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:01:00Z",
        "account": {"uuid": "user-1"},
        "chat_messages": [
            {
                "uuid": "msg-1",
                "text": "Hello",
                "sender": "human",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello",
                        "citations": [],
                        "start_timestamp": "2024-01-01T00:00:00Z",
                        "stop_timestamp": "2024-01-01T00:00:01Z",
                        "flags": None,
                        "alternative_display_type": None,
                    }
                ],
                "attachments": [],
                "files": [],
            },
            {
                "uuid": "msg-2",
                "text": "Hi there",
                "sender": "assistant",
                "created_at": "2024-01-01T00:00:05Z",
                "updated_at": "2024-01-01T00:00:05Z",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "User said hello",
                        "summaries": [{"summary": "greeting"}],
                        "cut_off": False,
                        "truncated": False,
                        "signature": "abc123",
                        "start_timestamp": "2024-01-01T00:00:04Z",
                        "stop_timestamp": "2024-01-01T00:00:05Z",
                        "flags": None,
                        "alternative_display_type": None,
                    },
                    {
                        "type": "text",
                        "text": "Hi there",
                        "citations": [],
                        "start_timestamp": "2024-01-01T00:00:05Z",
                        "stop_timestamp": "2024-01-01T00:00:06Z",
                        "flags": None,
                        "alternative_display_type": None,
                    },
                ],
                "attachments": [],
                "files": [],
            },
        ],
    }
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_zip(
    users: list[dict] | None = None,
    projects: list[dict] | None = None,
    conversations: list[dict] | None = None,
    *,
    omit_files: set[str] | None = None,
) -> Path:
    """Build a ZIP file in a temp directory and return the path.

    Any of *users*, *projects*, *conversations* defaults to the SAMPLE_*
    constants when ``None``.  Pass an explicit empty list to override.
    """
    if users is None:
        users = SAMPLE_USERS
    if projects is None:
        projects = SAMPLE_PROJECTS
    if conversations is None:
        conversations = SAMPLE_CONVERSATIONS

    omit = omit_files or set()
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()

    with zipfile.ZipFile(tmp.name, "w") as zf:
        if "users.json" not in omit:
            zf.writestr("users.json", json.dumps(users))
        if "projects.json" not in omit:
            zf.writestr("projects.json", json.dumps(projects))
        if "conversations.json" not in omit:
            zf.writestr("conversations.json", json.dumps(conversations))

    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_zip(tmp_path: Path) -> Path:
    """Build the standard sample ZIP and return its path."""
    return build_zip()


@pytest.fixture()
def sample_data(sample_zip: Path):
    """Parse the standard sample ZIP and return an ExportData."""
    return parse_export(sample_zip)


@pytest.fixture()
def tool_use_zip() -> Path:
    """ZIP containing a conversation with a tool_use content block."""
    conversations = [
        {
            "uuid": "conv-tool",
            "name": "Tool Conversation",
            "summary": "",
            "created_at": "2024-02-01T00:00:00Z",
            "updated_at": "2024-02-01T00:01:00Z",
            "account": {"uuid": "user-1"},
            "chat_messages": [
                {
                    "uuid": "msg-tool-use",
                    "text": "",
                    "sender": "assistant",
                    "created_at": "2024-02-01T00:00:05Z",
                    "updated_at": "2024-02-01T00:00:05Z",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-call-1",
                            "name": "read_file",
                            "input": {"path": "/tmp/test.txt"},
                            "start_timestamp": "2024-02-01T00:00:05Z",
                            "stop_timestamp": "2024-02-01T00:00:06Z",
                        }
                    ],
                    "attachments": [],
                    "files": [],
                },
            ],
        }
    ]
    return build_zip(conversations=conversations)


@pytest.fixture()
def tool_result_zip() -> Path:
    """ZIP containing a conversation with a tool_result content block."""
    conversations = [
        {
            "uuid": "conv-result",
            "name": "Tool Result Conversation",
            "summary": "",
            "created_at": "2024-02-01T00:00:00Z",
            "updated_at": "2024-02-01T00:01:00Z",
            "account": {"uuid": "user-1"},
            "chat_messages": [
                {
                    "uuid": "msg-tool-result",
                    "text": "",
                    "sender": "human",
                    "created_at": "2024-02-01T00:00:10Z",
                    "updated_at": "2024-02-01T00:00:10Z",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tool-call-1",
                            "content": "file contents here",
                            "start_timestamp": "2024-02-01T00:00:10Z",
                            "stop_timestamp": "2024-02-01T00:00:11Z",
                        }
                    ],
                    "attachments": [],
                    "files": [],
                },
            ],
        }
    ]
    return build_zip(conversations=conversations)


@pytest.fixture()
def attachment_zip() -> Path:
    """ZIP containing a conversation with message attachments."""
    conversations = [
        {
            "uuid": "conv-att",
            "name": "Attachment Conversation",
            "summary": "",
            "created_at": "2024-03-01T00:00:00Z",
            "updated_at": "2024-03-01T00:01:00Z",
            "account": {"uuid": "user-1"},
            "chat_messages": [
                {
                    "uuid": "msg-att",
                    "text": "See attached",
                    "sender": "human",
                    "created_at": "2024-03-01T00:00:00Z",
                    "updated_at": "2024-03-01T00:00:00Z",
                    "content": [
                        {
                            "type": "text",
                            "text": "See attached",
                            "citations": [],
                            "start_timestamp": "2024-03-01T00:00:00Z",
                            "stop_timestamp": "2024-03-01T00:00:01Z",
                        }
                    ],
                    "attachments": [
                        {
                            "file_name": "report.pdf",
                            "file_size": 12345,
                            "file_type": "application/pdf",
                            "extracted_content": "Report body text",
                        }
                    ],
                    "files": [{"file_name": "report.pdf"}],
                },
            ],
        }
    ]
    return build_zip(conversations=conversations)


@pytest.fixture()
def unknown_block_zip() -> Path:
    """ZIP containing a conversation with an unknown content block type."""
    conversations = [
        {
            "uuid": "conv-unk",
            "name": "Unknown Block Conversation",
            "summary": "",
            "created_at": "2024-04-01T00:00:00Z",
            "updated_at": "2024-04-01T00:01:00Z",
            "account": {"uuid": "user-1"},
            "chat_messages": [
                {
                    "uuid": "msg-unk",
                    "text": "",
                    "sender": "assistant",
                    "created_at": "2024-04-01T00:00:00Z",
                    "updated_at": "2024-04-01T00:00:00Z",
                    "content": [
                        {
                            "type": "magic_sparkle",
                            "data": "something new",
                            "start_timestamp": "2024-04-01T00:00:00Z",
                            "stop_timestamp": "2024-04-01T00:00:01Z",
                        }
                    ],
                    "attachments": [],
                    "files": [],
                },
            ],
        }
    ]
    return build_zip(conversations=conversations)


@pytest.fixture()
def no_content_zip() -> Path:
    """ZIP with a message that has no ``content`` key (fallback to ``text``)."""
    conversations = [
        {
            "uuid": "conv-nc",
            "name": "No Content Key",
            "summary": "",
            "created_at": "2024-05-01T00:00:00Z",
            "updated_at": "2024-05-01T00:01:00Z",
            "account": {"uuid": "user-1"},
            "chat_messages": [
                {
                    "uuid": "msg-nc",
                    "text": "Legacy text only",
                    "sender": "human",
                    "created_at": "2024-05-01T00:00:00Z",
                    "updated_at": "2024-05-01T00:00:00Z",
                    "attachments": [],
                    "files": [],
                },
            ],
        }
    ]
    return build_zip(conversations=conversations)
