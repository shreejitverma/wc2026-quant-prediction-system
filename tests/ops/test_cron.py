from click.testing import CliRunner

from wc2026.ops.cron import cli


def test_cron_live():
    runner = CliRunner()
    result = runner.invoke(cli, ['live'])
    assert result.exit_code == 0
    assert "Fetching latest" in result.output

def test_cron_backtest():
    runner = CliRunner()
    result = runner.invoke(cli, ['backtest'])
    assert result.exit_code == 0
    assert "Walk-Forward" in result.output

def test_cron_coherence():
    runner = CliRunner()
    result = runner.invoke(cli, ['coherence'])
    assert result.exit_code == 0
    assert "Hitting Kalshi L2" in result.output
