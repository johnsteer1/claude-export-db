"""Tests for claude_export_db.cli."""

from __future__ import annotations

from typer.testing import CliRunner

from claude_export_db.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# convert command
# ---------------------------------------------------------------------------


def test_convert_default_output(sample_zip, tmp_path, monkeypatch):
    """Default convert creates brain.db in the working directory."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["convert", str(sample_zip)])
    assert result.exit_code == 0
    assert (tmp_path / "brain.db").exists()


def test_convert_json_format(sample_zip, tmp_path, monkeypatch):
    """Convert with --output json creates export.json."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["convert", str(sample_zip), "--output", "json"])
    assert result.exit_code == 0
    assert (tmp_path / "export.json").exists()


# ---------------------------------------------------------------------------
# inspect command
# ---------------------------------------------------------------------------


def test_inspect_output(sample_zip):
    """Inspect command prints summary stats to stdout."""
    result = runner.invoke(app, ["inspect", str(sample_zip)])
    assert result.exit_code == 0
    # Should contain stats like number of conversations and messages
    assert "Conversations" in result.output
    assert "Messages" in result.output


# ---------------------------------------------------------------------------
# schema command
# ---------------------------------------------------------------------------


def test_schema_output():
    """Schema command prints DDL to stdout."""
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    assert "CREATE TABLE" in result.output


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_error_nonexistent_zip(tmp_path, monkeypatch):
    """Non-existent ZIP file results in exit code 1."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["convert", "nope.zip"])
    assert result.exit_code == 1


def test_error_output_exists_no_overwrite(sample_zip, tmp_path, monkeypatch):
    """Existing output without --overwrite results in exit code 1."""
    monkeypatch.chdir(tmp_path)
    # Create the default output file first
    (tmp_path / "brain.db").write_text("existing")
    result = runner.invoke(app, ["convert", str(sample_zip)])
    assert result.exit_code == 1
