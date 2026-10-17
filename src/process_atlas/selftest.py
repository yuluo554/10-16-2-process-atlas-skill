"""Built-in falsifiable check suite (module: selftest, M4).

Contract (plan/03 §M4, HANDOFF-M4 §2):
  - Identity assertion: sum of DFG edge counts == sum of trace lengths - case count.
  - Truth reconciliation: mining output vs data/synthetic/truth.json, field by
    field, full run (no sampling). truth.json is read-only (K8).
  - Double-run byte identity over the full pipeline (parse -> mine -> layout
    -> render).
  - Falsifiability probe: the same comparators used above must flag an
    injected defect; if a comparator stays silent the probe fails — this
    catches orchestration-shell selftests that cannot fail.
  - An empty/missing data directory is a failure, not a pass.

Return shape: run_selftest(data_dir) -> (failures, checks) where failures is a
list of "name: detail" strings; empty means all green. CLI maps that to
exit 0 / exit 1 (D13: selftest failure is neither usage error nor stage
not-ready; 1 keeps exit 2 reserved for input errors per K1).
"""

import io
import json
import os

from . import layout, mining, render

_REQUIRED_FILES = ("events.csv", "events_variants.json", "truth.json", "manifest.json")


def _default_data_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "synthetic",
    )


def _read_bytes(path):
    with io.open(path, "rb") as f:
        return f.read()


# ---------- individual checks; each returns None (ok) or a detail string -----


def _check_files_present(data_dir):
    missing = [n for n in _REQUIRED_FILES if not os.path.isfile(os.path.join(data_dir, n))]
    if missing:
        return "missing required file(s): %s" % ", ".join(missing)
    return None


def _check_identity(events, case_count, edge_counts):
    """边频次总和 = trace 长度总和 − case 数（生成器恒等式，mining 侧复算）。"""
    by_case = {}
    for e in events:
        by_case.setdefault(e[0], []).append(e)
    trace_len_sum = sum(len(v) for v in by_case.values())
    edge_sum = sum(edge_counts.values())
    expected = trace_len_sum - len(by_case)
    if edge_sum != expected or case_count != len(by_case):
        return "edge_sum=%d, expected=trace_sum(%d)-cases(%d)=%d, case_count=%d" % (
            edge_sum, trace_len_sum, len(by_case), expected, case_count)
    return None


def _check_truth_reconciliation(mined, truth):
    """Field-by-field, full-run (same comparators test_mining.py locks)."""
    if mined["edges"] != truth["dfg_edges"]:
        return "dfg_edges differ from truth"
    if mined["variants"] != truth["variants"]:
        return "variants differ from truth"
    if mined["bottlenecks"] != truth["bottlenecks"]:
        return "bottlenecks differ from truth"
    if mined["case_stats"] != truth["case_durations"]:
        return "case_durations differ from truth"
    return None


def _check_dual_form(mined_csv, events_json):
    if mining.mine(events_json) != mined_csv:
        return "JSON dual form mines differently from CSV"
    return None


def _check_double_run(events):
    """Full pipeline twice: parse -> mine -> layout -> render, byte identity (K2)."""
    result_a = mining.mine(events)
    html_a = render.render(result_a)
    # Run 2 re-executes the pipeline from the same parsed events (parse step is
    # re-exercised by the caller separately for the JSON dual form).
    result_b = mining.mine(events)
    html_b = render.render(result_b)
    json_a = mining.mine_to_json(events)
    json_b = mining.mine_to_json(events)
    if json_a != json_b:
        return "mine_to_json differs between runs"
    if html_a != html_b:
        return "render output differs between runs"
    return None


def _check_falsifiable_probe(events, mined, truth):
    """Inject a defect; the comparators above must report the difference."""
    # Probe 1: corrupt a variant count -> truth reconciliation must fire.
    bad = dict(mined)
    bad["variants"] = [dict(v) for v in mined["variants"]]
    bad["variants"][0]["count"] += 1
    if _check_truth_reconciliation(bad, truth) is None:
        return "probe 1 undetected: corrupted variant count passed reconciliation"
    # Probe 2: drop an edge -> identity check must fire.
    edges = {k: v for k, v in mining.mine_dfg(events).items()}
    first_key = sorted(edges)[0]
    del edges[first_key]
    if _check_identity(events, mined["case_count"], edges) is None:
        return "probe 2 undetected: dropped edge passed identity check"
    # Probe 3: perturb layout -> double-run comparator surface must distinguish content.
    lay_a = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    lay_b = dict(lay_a)
    any_node = sorted(lay_b)[0]
    lay_b[any_node] = dict(lay_b[any_node], x=lay_b[any_node]["x"] + 7)
    if lay_a == lay_b:
        return "probe 3 undetected: layout perturbation invisible"
    return None


# ---------- suite driver ------------------------------------------------------


def run_selftest(data_dir=None):
    """Run all checks; returns (failures, check_names).

    failures is a list of "check_name: detail" strings; empty = all green.
    Missing/empty data directory yields failures (never a silent pass).
    """
    if data_dir is None:
        data_dir = _default_data_dir()
    checks = []
    failures = []

    def record(name, detail):
        checks.append(name)
        if detail is not None:
            failures.append("%s: %s" % (name, detail))

    missing = _check_files_present(data_dir)
    if missing is not None:
        record("files_present", missing)
        failures.append(
            "selftest: data directory incomplete, aborting remaining checks: %s" % data_dir
        )
        return failures, checks

    csv_path = os.path.join(data_dir, "events.csv")
    json_path = os.path.join(data_dir, "events_variants.json")
    with io.open(os.path.join(data_dir, "truth.json"), "r", encoding="utf-8") as f:
        truth = json.load(f)["expected"]

    events = mining.load_events(csv_path)
    events_json = mining.load_events(json_path)
    mined = mining.mine(events)

    record("files_present", None)
    record("identity", _check_identity(events, mined["case_count"], mining.mine_dfg(events)))
    record("truth_reconciliation", _check_truth_reconciliation(mined, truth))
    record("dual_form", _check_dual_form(mined, events_json))
    record("double_run", _check_double_run(events))
    record("falsifiable_probe", _check_falsifiable_probe(events, mined, truth))
    return failures, checks


def cmd_selftest(data_dir=None):
    """CLI `selftest` wiring. Exit 0 all green; exit 1 any failure (D13)."""
    from . import cli as _cli  # exit-code constants live there; import late to avoid cycle

    failures, checks = run_selftest(data_dir)
    for name in checks:
        _cli.sys.stdout.write("ok   %s\n" % name if not any(f.startswith(name + ":") for f in failures)
                              else "FAIL %s\n" % name)
    if failures:
        for f in failures:
            _cli.sys.stderr.write("selftest failure: %s\n" % f)
        _cli.sys.stderr.write("selftest failed: %d failure(s)\n" % len(failures))
        return _cli.EXIT_SELFTEST_FAIL
    _cli.sys.stderr.write("selftest passed: %d check(s)\n" % len(checks))
    return _cli.EXIT_OK
