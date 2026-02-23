"""Tests for CLI JSON output validation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from seo_linker.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_md(tmp_path):
    content = """\
# Test Article

This is a test article about bras and comfort.

## Section One

Looking for comfortable bras without underwire? Our collection has everything.

## Section Two

Find the perfect fit with our size calculator and guides.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestAuditJsonOutput:
    def test_audit_json_is_valid(self, runner, sample_md):
        result = runner.invoke(cli, ["audit", str(sample_md), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "file" in data
        assert "total_links" in data
        assert "issues" in data
        assert "links" in data
        assert isinstance(data["issues"], list)
        assert isinstance(data["links"], list)

    def test_audit_text_output(self, runner, sample_md):
        result = runner.invoke(cli, ["audit", str(sample_md), "--format", "text"])
        assert result.exit_code == 0
        assert "Audit:" in result.output

    def test_audit_with_domain(self, runner, sample_md):
        result = runner.invoke(cli, ["audit", str(sample_md), "--domain", "de.triumph.com", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["file"] == "test.md"


class TestGscClearCache:
    def test_clear_cache_command(self, runner):
        with patch("seo_linker.gsc.cache.GSCCache.clear", return_value=0):
            result = runner.invoke(cli, ["gsc-clear-cache"])
            assert result.exit_code == 0
            assert "Cleared" in result.output

    def test_clear_cache_with_site(self, runner):
        with patch("seo_linker.gsc.cache.GSCCache.clear", return_value=2) as mock_clear:
            result = runner.invoke(cli, ["gsc-clear-cache", "--site", "sc-domain:test.com"])
            assert result.exit_code == 0
            mock_clear.assert_called_once_with("sc-domain:test.com")
            assert "2" in result.output


class TestCliHelpAndVersion:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_shows_new_commands(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # All new commands should be visible
        assert "opportunities" in result.output
        assert "cross-gaps" in result.output
        assert "candidates" in result.output
        assert "link" in result.output
        assert "audit" in result.output
        assert "gsc-clear-cache" in result.output
        # Existing commands should still be there
        assert "process" in result.output
        assert "config" in result.output
        assert "add-sitemap" in result.output

    def test_opportunities_requires_gsc_site(self, runner):
        result = runner.invoke(cli, ["opportunities"])
        assert result.exit_code != 0
        assert "gsc-site" in result.output.lower() or "required" in result.output.lower()

    def test_cross_gaps_requires_gsc_site(self, runner):
        result = runner.invoke(cli, ["cross-gaps"])
        assert result.exit_code != 0
