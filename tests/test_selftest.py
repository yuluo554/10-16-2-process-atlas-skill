"""M4 tests: selftest suite — green on frozen data, red on injected defects,
fails on empty data directory, CLI contract (D13)."""

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SRC = os.path.join(_REPO, "src")
_SYNTH = os.path.join(_REPO, "data", "synthetic")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from process_atlas import cli, selftest as st  # noqa: E402

_CSV = os.path.join(_SYNTH, "events.csv")


# ---------- green path on frozen synthetic data ----------


def test_selftest_all_green_on_synthetic():
    failures, checks = st.run_selftest(_SYNTH)
    assert failures == [], failures
    assert set(checks) == {
        "files_present",
        "identity",
        "truth_reconciliation",
        "dual_form",
        "double_run",
        "falsifiable_probe",
    }


def test_cli_selftest_exit_0(capsys):
    assert cli.main(["selftest"]) == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "selftest passed" in err


# ---------- falsifiable: injected defects must be caught (探活) ----------


def test_probe_detects_corrupted_variant():
    import io
    import json
    with io.open(os.path.join(_SYNTH, "truth.json"), "r", encoding="utf-8") as f:
        truth = json.load(f)["expected"]
    events = st.mining.load_events(_CSV)
    mined = st.mining.mine(events)
    bad = dict(mined)
    bad["variants"] = [dict(v) for v in mined["variants"]]
    bad["variants"][0]["count"] += 1
    assert st._check_truth_reconciliation(bad, truth) is not None


def test_probe_detects_dropped_edge_via_identity():
    events = st.mining.load_events(_CSV)
    edges = st.mining.mine_dfg(events)
    first = sorted(edges)[0]
    del edges[first]
    assert st._check_identity(events, len({e[0] for e in events}), edges) is not None


def test_selftest_on_empty_dir_fails(tmp_path):
    failures, checks = st.run_selftest(str(tmp_path))
    assert failures  # never a silent pass on an empty directory


def test_selftest_on_missing_dir_fails(tmp_path):
    failures, _ = st.run_selftest(str(tmp_path / "no_such_dir"))
    assert failures


def test_selftest_on_corrupted_copy_fails(tmp_path):
    """A tampered data directory must be caught by reconciliation or identity."""
    import io
    import shutil
    target = tmp_path / "synth"
    shutil.copytree(_SYNTH, target)
    # corrupt events.csv: append a phantom event to a case -> identity fires
    csv_path = target / "events.csv"
    with io.open(str(csv_path), "a", encoding="utf-8", newline="") as f:
        f.write("C0001,提交申请,2026-01-06T11:17:00\n")
    failures, _ = st.run_selftest(str(target))
    assert failures


# ---------- CLI contract (D13) ----------


def test_cli_selftest_missing_data_dir_exit_1(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        st, "_default_data_dir", lambda: str(tmp_path / "no_such"), raising=True
    )
    assert cli.main(["selftest"]) == cli.EXIT_SELFTEST_FAIL
    assert "selftest failed" in capsys.readouterr().err


def test_no_stdlib_random_in_selftest_source():
    import io
    with io.open(os.path.join(_SRC, "process_atlas", "selftest.py"), "r", encoding="utf-8") as f:
        src = f.read()
    assert "import random" not in src
    assert "random." not in src


def test_selftest_report_mentions_every_check(capsys):
    cli.main(["selftest"])
    out = capsys.readouterr().out
    for name in ("identity", "truth_reconciliation", "dual_form", "double_run", "falsifiable_probe"):
        assert ("ok   %s" % name) in out
