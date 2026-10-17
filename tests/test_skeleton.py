"""M0 skeleton tests: exit-code contract locked (D6)."""

import importlib.util
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SRC = os.path.join(_REPO, "src")


def _load_cli():
    # Load cli.py directly by path so the skeleton test needs no package install.
    spec = importlib.util.spec_from_file_location(
        "process_atlas_cli", os.path.join(_SRC, "process_atlas", "cli.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cli = _load_cli()


class TestExitCodeContract:
    def test_no_args_is_usage_error(self, capsys):
        assert cli.main([]) == cli.EXIT_USAGE

    def test_unknown_command_is_usage_error(self):
        # argparse subparsers reject an invalid choice with SystemExit(2);
        # the contract is the exit code, whichever path raises it.
        with pytest.raises(SystemExit) as exc:
            cli.main(["bogus-command"])
        assert exc.value.code == cli.EXIT_USAGE

    def test_render_is_wired(self):
        """D12: render retired stage-not-ready on M3 landing. The skeleton test
        loads cli.py by path (relative imports would explode inside main()), so
        here we only assert the subcommand exists; functional render coverage
        lives in test_render.py / test_mining-style package imports."""
        parser = cli.build_parser()
        out = parser.format_help()
        assert "render" in out

    def test_selftest_is_not_ready(self, capsys):
        assert cli.main(["selftest"]) == cli.EXIT_NOT_READY

    def test_validate_missing_file_is_usage_error(self):
        # Schema checking lands in M4; missing-file handling is wired from M0.
        missing = os.path.join(_HERE, "no_such_log.csv")
        assert cli.main(["validate", missing]) == cli.EXIT_USAGE


class TestMineRetiredNotReady:
    """D11: `mine` exited stage-not-ready on M2 landing; guard against revival."""

    def test_mine_not_in_stage_not_ready(self):
        assert "mine" not in cli.STAGE_NOT_READY

    def test_mine_missing_file_is_usage_error(self):
        missing = os.path.join(_HERE, "no_such_log.csv")
        assert cli.main(["mine", missing]) == cli.EXIT_USAGE


class TestRenderRetiredNotReady:
    """D12: `render` exited stage-not-ready on M3 landing; guard against revival."""

    def test_render_not_in_stage_not_ready(self):
        assert "render" not in cli.STAGE_NOT_READY

    def test_render_missing_file_is_usage_error(self):
        missing = os.path.join(_HERE, "no_such_log.csv")
        assert cli.main(["render", missing, "-o", "out.html"]) == cli.EXIT_USAGE
