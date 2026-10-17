"""M2 tests: mining vs frozen truth, purity guard, determinism (plan/05 M2 DoD).

Reconciliation is full-run, field-by-field against data/synthetic/truth.json —
no sampling. truth.json is read-only here (K8).
"""

import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SRC = os.path.join(_REPO, "src")
_SYNTH = os.path.join(_REPO, "data", "synthetic")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from process_atlas import cli, mining  # noqa: E402

_CSV = os.path.join(_SYNTH, "events.csv")
_JSON_LOG = os.path.join(_SYNTH, "events_variants.json")


@pytest.fixture(scope="module")
def truth():
    with io.open(os.path.join(_SYNTH, "truth.json"), "r", encoding="utf-8") as f:
        return json.load(f)["expected"]


@pytest.fixture(scope="module")
def mined():
    events = mining.load_events(_CSV)
    return mining.mine(events)


# ---------- truth reconciliation (full, field-by-field) ----------


def test_recon_dfg_edges(mined, truth):
    assert mined["edges"] == truth["dfg_edges"]


def test_recon_variants(mined, truth):
    assert mined["variants"] == truth["variants"]


def test_recon_bottlenecks(mined, truth):
    assert mined["bottlenecks"] == truth["bottlenecks"]


def test_recon_case_durations(mined, truth):
    assert mined["case_stats"] == truth["case_durations"]


def test_recon_nodes_and_case_count(mined, truth):
    with io.open(os.path.join(_SYNTH, "truth.json"), "r", encoding="utf-8") as f:
        whole = json.load(f)
    assert mined["nodes"] == whole["input"]["activities"]
    assert mined["case_count"] == whole["input"]["case_count"]


def test_recon_from_json_dual_form(mined):
    """CSV and JSON dual forms of the same log must mine identically (D5)."""
    events = mining.load_events(_JSON_LOG)
    assert mining.mine(events) == mined


# ---------- K1 retirement + CLI wiring ----------


class TestMineCli:
    def test_mine_ok_on_synthetic(self, capsys):
        assert cli.main(["mine", _CSV]) == cli.EXIT_OK
        out = capsys.readouterr().out
        assert json.loads(out)["case_count"] == 200

    def test_mine_missing_file_usage_error(self):
        assert cli.main(["mine", os.path.join(_HERE, "no_such.csv")]) == cli.EXIT_USAGE

    def test_mine_output_is_k2_canonical(self, capsys):
        cli.main(["mine", _CSV])
        out = capsys.readouterr().out
        obj = json.loads(out)
        assert out == json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


# ---------- purity guard: no third-party imports ----------


def _stdlib_top_modules():
    root = os.path.dirname(os.__file__)
    names = set()
    for entry in os.listdir(root):
        if entry.endswith(".py"):
            names.add(entry[:-3])
        elif os.path.isdir(os.path.join(root, entry)) and not entry.startswith("_"):
            names.add(entry)
        elif entry.endswith(".pyd") or (entry.endswith(".so") and "." in entry):
            names.add(entry.split(".")[0])
    names |= set(sys.builtin_module_names)
    return names


_STDLIB = _stdlib_top_modules()


def test_mining_source_has_no_third_party_imports():
    with io.open(os.path.join(_SRC, "process_atlas", "mining.py"), "r", encoding="utf-8") as f:
        src = f.read()
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            mod = s.split()[1].split(".")[0]
            assert mod in _STDLIB, "non-stdlib import in mining.py: %s" % mod


def test_mining_runtime_imports_are_stdlib_only():
    snapshot = set(sys.modules)
    mining.load_events(_CSV)
    mining.mine(mining.load_events(_CSV))
    new_mods = set(sys.modules) - snapshot
    for name in new_mods:
        top = name.split(".")[0]
        assert top in _STDLIB or top.startswith("_"), "non-stdlib module loaded: %s" % name


# ---------- determinism: double-run byte identity (K2) ----------


def test_double_run_byte_identical(mined):
    a = mining.mine_to_json(mining.load_events(_CSV))
    b = mining.mine_to_json(mining.load_events(_CSV))
    assert a == b
    assert a == mining.mine_to_json(mined and mining.load_events(_CSV))


def test_cli_mine_double_run_byte_identical(capsys):
    cli.main(["mine", _CSV])
    first = capsys.readouterr().out
    cli.main(["mine", _CSV])
    second = capsys.readouterr().out
    assert first == second


# ---------- tie-break behaviour (K4, direct unit probe) ----------


def test_row_order_tiebreak(tmp_path):
    """Equal timestamps resolve by source row order, deterministically."""
    p = tmp_path / "tie.csv"
    p.write_text(
        "case_id,activity,timestamp\n"
        "C1,审核,2026-01-01T10:00:00\n"
        "C1,打款,2026-01-01T10:00:00\n",
        encoding="utf-8",
    )
    edges = mining.mine_dfg(mining.load_events(str(p)))
    assert edges == {("审核", "打款"): 1}


def test_quantile_linear_interpolation():
    assert mining.quantile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert mining.quantile([10.0], 0.95) == 10.0
    assert mining.quantile([0.0, 10.0], 0.95) == 9.5
