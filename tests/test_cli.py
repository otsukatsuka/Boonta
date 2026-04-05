"""Tests for CLI commands."""
from click.testing import CliRunner

from cli import _generate_dates, cli


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Boonta" in result.output

    def test_download_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output

    def test_parse_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["parse", "--help"])
        assert result.exit_code == 0

    def test_predict_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["predict", "--help"])
        assert result.exit_code == 0
        assert "--no-ml" in result.output

    def test_evaluate_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "--help"])
        assert result.exit_code == 0
        assert "fukusho_top3" in result.output

    def test_predict_missing_file(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["predict", "--date", "999999"])
        assert "not found" in result.output

    def test_parse_no_args(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["parse"])
        assert "specify" in result.output.lower() or result.exit_code == 0

    def test_download_no_date(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["download", "--type", "KYI"])
        assert "specify" in result.output.lower()


class TestGenerateDates:
    def test_single_day(self):
        dates = _generate_dates("20260405", "20260405")
        assert dates == ["260405"]

    def test_three_days(self):
        dates = _generate_dates("20260405", "20260407")
        assert len(dates) == 3
        assert dates[0] == "260405"
        assert dates[2] == "260407"

    def test_format_is_yymmdd(self):
        dates = _generate_dates("20260101", "20260101")
        assert dates == ["260101"]
