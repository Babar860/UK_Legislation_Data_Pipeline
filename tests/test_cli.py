"""
Unit tests for the CLI (extract.py).

Tests argument parsing, exit codes, stdout/stderr output.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from extract import main
from legislation_pipeline.fetcher import FetchError
from legislation_pipeline.extractor import ParseError
from legislation_pipeline.models import LegislationRecord


def _make_record(**kwargs) -> LegislationRecord:
    """Return a minimal LegislationRecord for mocking."""
    defaults = dict(
        title="Test Act 2024",
        type="ukpga",
        year=2024,
        number=1,
        status="enacted",
    )
    defaults.update(kwargs)
    return LegislationRecord(**defaults)


class TestCliExitCodes:
    def test_no_url_exits_1(self, capsys):
        code = main([])
        assert code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_malformed_url_exits_1(self, capsys):
        code = main(["not-a-url"])
        assert code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_fetch_error_exits_1(self, capsys):
        with patch("extract.run", side_effect=FetchError("HTTP 404")):
            code = main(["https://www.legislation.gov.uk/ukpga/2024/15"])
        assert code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_parse_error_exits_1(self, capsys):
        with patch("extract.run", side_effect=ParseError("bad xml")):
            code = main(["https://www.legislation.gov.uk/ukpga/2024/15"])
        assert code == 1

    def test_successful_run_exits_0(self, capsys):
        record = _make_record()
        with patch("extract.run", return_value=record):
            code = main(["https://www.legislation.gov.uk/ukpga/2024/15"])
        assert code == 0

    def test_help_exits_0(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestCliOutput:
    def test_stdout_is_valid_json(self, capsys):
        record = _make_record()
        with patch("extract.run", return_value=record):
            main(["https://www.legislation.gov.uk/ukpga/2024/15"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["title"] == "Test Act 2024"

    def test_output_flag_writes_file(self, tmp_path, capsys):
        record = _make_record()
        output_file = tmp_path / "output.json"
        with patch("extract.run", return_value=record):
            code = main([
                "https://www.legislation.gov.uk/ukpga/2024/15",
                "--output", str(output_file),
            ])
        assert code == 0
        assert output_file.exists()
        parsed = json.loads(output_file.read_text(encoding="utf-8"))
        assert parsed["title"] == "Test Act 2024"

    def test_output_flag_nothing_on_stdout(self, tmp_path, capsys):
        record = _make_record()
        output_file = tmp_path / "output.json"
        with patch("extract.run", return_value=record):
            main([
                "https://www.legislation.gov.uk/ukpga/2024/15",
                "--output", str(output_file),
            ])
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_unwritable_output_path_exits_1(self, capsys):
        record = _make_record()
        with patch("extract.run", return_value=record):
            code = main([
                "https://www.legislation.gov.uk/ukpga/2024/15",
                "--output", "/nonexistent_dir/output.json",
            ])
        assert code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
