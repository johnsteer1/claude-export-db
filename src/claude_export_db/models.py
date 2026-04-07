from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    uuid: str
    full_name: str
    email_address: str
    verified_phone_number: str | None = None


@dataclass
class Project:
    uuid: str
    name: str
    description: str
    is_private: bool
    is_starter_project: bool
    prompt_template: str
    created_at: str
    updated_at: str
    creator_uuid: str | None = None


@dataclass
class ContentBlock:
    type: str  # "text", "thinking", "tool_use", "tool_result", or unknown
    block_index: int = 0
    start_timestamp: str | None = None
    stop_timestamp: str | None = None
    # type="text"
    text: str | None = None
    citations_json: str | None = None  # serialized JSON array
    # type="thinking"
    thinking: str | None = None
    summaries_json: str | None = None  # serialized JSON array
    cut_off: bool | None = None
    truncated: bool | None = None
    signature: str | None = None
    # type="tool_use"
    tool_id: str | None = None
    tool_name: str | None = None
    tool_input_json: str | None = None
    # type="tool_result"
    tool_use_id: str | None = None
    tool_result_content: str | None = None
    # unknown block types
    raw_json: str | None = None


@dataclass
class Attachment:
    file_name: str
    file_size: int
    file_type: str
    extracted_content: str | None = None


@dataclass
class FileRef:
    file_name: str


@dataclass
class Message:
    uuid: str
    text: str  # legacy field
    sender: str  # "human" or "assistant"
    created_at: str
    updated_at: str
    content_blocks: list[ContentBlock] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    files: list[FileRef] = field(default_factory=list)


@dataclass
class Conversation:
    uuid: str
    name: str
    summary: str
    created_at: str
    updated_at: str
    account_uuid: str | None = None
    messages: list[Message] = field(default_factory=list)


@dataclass
class ExportData:
    users: list[User] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    conversations: list[Conversation] = field(default_factory=list)
    warning_count: int = 0
