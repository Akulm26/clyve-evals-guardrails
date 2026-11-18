import pytest

from gtm_evals import cli


@pytest.fixture
def run_cli(capsys):
    """run_cli(*argv) -> (exit_code, stdout, stderr), in-process so coverage sees the CLI."""
    def _run(*argv):
        try:
            code = cli.main([str(a) for a in argv])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run
