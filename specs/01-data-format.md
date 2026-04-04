# Input Data Format

The Anthropic export ZIP contains exactly three files. The tool should read them directly from the ZIP without extracting to disk.

## users.json

Array of user objects. In practice always one element (your account).

```json
[
  {
    "uuid": "8fce2d85-c0a4-48a2-93fc-2effee2fda5f",
    "full_name": "John Steer",
    "email_address": "johnsteer3@gmail.com",
    "verified_phone_number": "+12032475298"
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `uuid` | string | Primary key |
| `full_name` | string | |
| `email_address` | string | |
| `verified_phone_number` | string \| null | May be absent or null |

## projects.json

Array of Claude Projects. May be empty (`[]`).

```json
[
  {
    "uuid": "01977f37-5a80-75ce-afa9-f4ef1a55147b",
    "name": "R&D Team Git Workflows",
    "description": "...",
    "is_private": true,
    "is_starter_project": false,
    "prompt_template": "",
    "created_at": "2025-06-17T18:47:03.557042+00:00",
    "updated_at": "2025-06-17T18:47:03.557042+00:00",
    "creator": {
      "uuid": "8fce2d85-c0a4-48a2-93fc-2effee2fda5f",
      "full_name": "John Steer"
    },
    "docs": []
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `uuid` | string | Primary key |
| `name` | string | |
| `description` | string | May be empty string |
| `is_private` | bool | |
| `is_starter_project` | bool | |
| `prompt_template` | string | May be empty string |
| `created_at` | ISO 8601 string | Includes timezone offset |
| `updated_at` | ISO 8601 string | |
| `creator.uuid` | string | FK → users.uuid |
| `creator.full_name` | string | Denormalized copy |
| `docs` | array | Always `[]` in observed exports — schema unknown |

## conversations.json

Array of conversation objects. This is the large file (~6MB for 198 conversations).

### Conversation object

```json
{
  "uuid": "f15683f3-59c8-481d-b299-0232e2e0bfdd",
  "name": "Python Script to Evaluate Total File Size",
  "summary": "",
  "created_at": "2024-07-30T16:06:23.747046Z",
  "updated_at": "2024-08-01T14:39:32.302850Z",
  "account": {
    "uuid": "8fce2d85-c0a4-48a2-93fc-2effee2fda5f"
  },
  "chat_messages": [ ... ]
}
```

| Field | Type | Notes |
|---|---|---|
| `uuid` | string | Primary key |
| `name` | string | Auto-generated title |
| `summary` | string | May be empty string; sometimes populated |
| `created_at` | ISO 8601 | Ends in `Z` (UTC) |
| `updated_at` | ISO 8601 | |
| `account.uuid` | string | FK → users.uuid |
| `chat_messages` | array | Ordered list of messages |

**Note:** There is no explicit `project_uuid` on conversations in the export. Conversations are not linked to projects in the current schema.

### Message object

```json
{
  "uuid": "1e0ff178-3006-48da-9241-3f71f5ac617e",
  "text": "You are assuming the role...",
  "content": [ ... ],
  "sender": "human",
  "created_at": "2024-07-30T16:06:38.215705Z",
  "updated_at": "2024-07-30T16:06:38.215705Z",
  "attachments": [],
  "files": []
}
```

| Field | Type | Notes |
|---|---|---|
| `uuid` | string | Primary key |
| `text` | string | **Legacy flat-text field.** Duplicates content from `content[]`. Do not use as primary source — use `content[]` instead. May be empty for some assistant messages. |
| `content` | array | **Source of truth.** Array of typed content blocks (see below). |
| `sender` | string | `"human"` or `"assistant"` |
| `created_at` | ISO 8601 | |
| `updated_at` | ISO 8601 | |
| `attachments` | array | File attachments uploaded by user |
| `files` | array | Separate files list — schema differs from attachments |

### Content block types

All blocks share these fields:

| Field | Type | Notes |
|---|---|---|
| `type` | string | One of: `text`, `thinking`, `tool_use`, `tool_result` |
| `start_timestamp` | ISO 8601 \| null | When block generation started |
| `stop_timestamp` | ISO 8601 \| null | When block generation ended |
| `flags` | null | Always null in observed data |
| `alternative_display_type` | null | Always null in observed data |

#### type: `text`

```json
{
  "type": "text",
  "text": "Here is the Python script...",
  "citations": [],
  "start_timestamp": "2024-07-30T16:06:38.215705Z",
  "stop_timestamp": "2024-07-30T16:06:38.215705Z",
  "flags": null,
  "alternative_display_type": null
}
```

| Field | Notes |
|---|---|
| `text` | The actual text content |
| `citations` | Array; always `[]` in observed data — schema unknown |

#### type: `thinking`

Extended reasoning blocks. Only present on assistant messages when the model used extended thinking.

```json
{
  "type": "thinking",
  "thinking": "The user shared a URL from X (Twitter). Let me fetch it...",
  "summaries": [
    { "summary": "Thinking about concerns with accessing external URLs." }
  ],
  "cut_off": false,
  "truncated": false,
  "signature": "EtoBCigIDBgCKiCg02LV8kqpiX9...",
  "start_timestamp": "2026-04-01T22:09:54.777237Z",
  "stop_timestamp": "2026-04-01T22:09:55.731512Z",
  "flags": null,
  "alternative_display_type": null
}
```

| Field | Notes |
|---|---|
| `thinking` | Full internal reasoning text |
| `summaries` | Array of `{summary: string}` — condensed summaries |
| `cut_off` | bool — whether reasoning was cut off mid-stream |
| `truncated` | bool — whether thinking was truncated in export |
| `signature` | Cryptographic signature string |

#### type: `tool_use`

```json
{
  "type": "tool_use",
  "id": "toolu_01...",
  "name": "bash",
  "input": { "command": "ls -la" },
  "start_timestamp": "...",
  "stop_timestamp": "...",
  "flags": null,
  "alternative_display_type": null
}
```

| Field | Notes |
|---|---|
| `id` | Tool call ID — matches `tool_use_id` in the corresponding `tool_result` |
| `name` | Tool name (e.g. `bash`, `read_file`, `web_search`) |
| `input` | Object — tool-specific input parameters |

#### type: `tool_result`

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01...",
  "content": "output text here",
  "start_timestamp": "...",
  "stop_timestamp": "...",
  "flags": null,
  "alternative_display_type": null
}
```

| Field | Notes |
|---|---|
| `tool_use_id` | FK → `tool_use` block `id` |
| `content` | String or array — tool output |

### Attachment object

```json
{
  "file_name": "schema.sql",
  "file_size": 4096,
  "file_type": "text/plain",
  "extracted_content": "CREATE TABLE ..."
}
```

| Field | Type | Notes |
|---|---|---|
| `file_name` | string | |
| `file_size` | int | Bytes |
| `file_type` | string | MIME type |
| `extracted_content` | string | Full text content of the file |

### Files object

```json
{ "file_name": "image.png" }
```

Simpler than attachments — only a filename, no content. Likely images or binary files that couldn't be text-extracted.

## Real-world stats (April 2026 export, 21 months of usage)

| Metric | Value |
|---|---|
| Conversations | 198 |
| Messages | 1,166 |
| Human messages | 589 |
| Assistant messages | 577 |
| Content blocks — text | 1,279 |
| Content blocks — tool_use | 174 |
| Content blocks — tool_result | 173 |
| Content blocks — thinking | 118 |
| Date range | July 2024 → April 2026 |
| conversations.json size | ~6.3 MB |
