"""Tests for claude_export_db.writers.markdown."""

from __future__ import annotations

from claude_export_db.writers.markdown import write_markdown

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_markdown_creates_directory(sample_data, tmp_path):
    """write_markdown creates the output directory."""
    out = tmp_path / "md_out"
    write_markdown(sample_data, out)
    assert out.is_dir()


def test_markdown_file_per_conversation(sample_data, tmp_path):
    """One .md file is created per conversation."""
    out = tmp_path / "md_out"
    write_markdown(sample_data, out)
    md_files = list(out.glob("*.md"))
    assert len(md_files) == len(sample_data.conversations)


def test_markdown_filename_format(sample_data, tmp_path):
    """Filename follows the YYYY-MM-DD_slug.md pattern."""
    out = tmp_path / "md_out"
    write_markdown(sample_data, out)
    md_files = list(out.glob("*.md"))
    assert len(md_files) == 1
    name = md_files[0].name
    # Expect: 2024-01-01_test-conversation.md
    assert name == "2024-01-01_test-conversation.md"


def test_markdown_thinking_included_by_default(sample_data, tmp_path):
    """By default, thinking blocks are rendered as blockquotes."""
    out = tmp_path / "md_out"
    write_markdown(sample_data, out)
    md_files = list(out.glob("*.md"))
    content = md_files[0].read_text(encoding="utf-8")
    # Thinking is rendered with *thinking:* header and blockquote
    assert "*thinking:*" in content
    assert "> User said hello" in content


def test_markdown_no_thinking_flag(sample_data, tmp_path):
    """With no_thinking=True, thinking blocks are omitted."""
    out = tmp_path / "md_out"
    write_markdown(sample_data, out, no_thinking=True)
    md_files = list(out.glob("*.md"))
    content = md_files[0].read_text(encoding="utf-8")
    assert "*thinking:*" not in content
    assert "User said hello" not in content
