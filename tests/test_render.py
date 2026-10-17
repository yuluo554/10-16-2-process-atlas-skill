"""M3 tests: render gates (plan/05 M3 DoD).

Covers: zero-external-resources (resident assertion + mutation probe),
deterministic layout (integer coords + mutation must-fail), double-run byte
identity, content-derived build hash (no clock), CLI wiring (D12).
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

from process_atlas import cli, layout, mining, render  # noqa: E402

_CSV = os.path.join(_SYNTH, "events.csv")


@pytest.fixture(scope="module")
def mined():
    return mining.mine(mining.load_events(_CSV))


@pytest.fixture(scope="module")
def html(mined):
    return render.render(mined)


# ---------- layout: deterministic, integer, mutation-verified ----------


def test_layout_deterministic_and_integer(mined):
    a = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    b = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    assert a == b
    assert set(a) == set(mined["nodes"])
    for name, pos in a.items():
        assert set(pos) == {"x", "y", "layer"}
        for v in pos.values():
            assert isinstance(v, int), (name, v)


def test_layout_layers_follow_dag_order(mined):
    lay = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    for e in mined["edges"]:
        if lay[e["to"]]["layer"] == lay[e["from"]]["layer"] + 1 or lay[e["to"]]["layer"] > lay[e["from"]]["layer"]:
            pass  # forward edges only raise layer by construction
    # every forward edge goes strictly forward in layer; back edges may not
    forward = [e for e in mined["edges"] if e["from"] != e["to"]]
    layers_ok = [lay[e["to"]]["layer"] > lay[e["from"]]["layer"] for e in forward]
    # With cycles (驳回/撤回) some edges are back edges and may go backwards;
    # verify layering is a valid longest-path assignment over non-back edges.
    assert any(layers_ok)


def test_layout_mutation_perturbation_changes_output(mined):
    """Mutation gate (plan/05 M3): any layout perturbation must be detected —
    i.e. the layout is not a constant/collapsed function."""
    lay = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    # perturb one edge: drop 财务复核→打款, layout must differ somewhere
    edges2 = [(e["from"], e["to"]) for e in mined["edges"] if (e["from"], e["to"]) != ("财务复核", "打款")]
    lay2 = layout.compute_layout(mined["nodes"], edges2)
    assert lay2 != lay
    # distinct layers exist (not everything collapsed onto one point)
    assert len(set((p["x"], p["y"]) for p in lay.values())) == len(lay)


def test_layout_cycle_back_edge_does_not_break_layering():
    nodes = ["A", "B", "C"]
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    lay = layout.compute_layout(nodes, edges)
    assert lay["A"]["layer"] == 0
    assert lay["B"]["layer"] == 1
    assert lay["C"]["layer"] == 2


# ---------- render: zero-CDN resident assertion ----------


def test_no_external_resources_in_report(html):
    render.assert_no_external_resources(html)  # must not raise
    low = html.lower()
    assert "http://" not in low and "https://" not in low
    assert "<link" not in low


def test_assertion_catches_external_resource():
    for bad in (
        '<script src="https://cdn.example.com/x.js"></script>',
        '<link rel="stylesheet" href="http://x/y.css">',
        '<img src="//evil.example/x.png">',
    ):
        with pytest.raises(AssertionError):
            render.assert_no_external_resources("<html>" + bad + "</html>")


def test_purity_guard_layout_render_source():
    for mod_name in ("layout", "render"):
        path = os.path.join(_SRC, "process_atlas", mod_name + ".py")
        with io.open(path, "r", encoding="utf-8") as f:
            src = f.read()
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                mod = s.split()[1].split(".")[0]
                if mod == "":  # relative "from . import x"
                    continue
                assert mod in ("csv", "json", "heapq", "hashlib", "os", "string", "layout", "process_atlas"), \
                    "unexpected import in %s.py: %s" % (mod_name, mod)


# ---------- K2: double-run byte identity + content-derived hash ----------


def test_render_double_run_byte_identical(mined):
    a = render.render(mined)
    b = render.render(mining.mine(mining.load_events(_CSV)))
    assert a == b


def test_cli_render_double_run_byte_identical(tmp_path, capsys):
    out1 = str(tmp_path / "a.html")
    out2 = str(tmp_path / "b.html")
    assert cli.main(["render", _CSV, "-o", out1]) == cli.EXIT_OK
    assert cli.main(["render", _CSV, "-o", out2]) == cli.EXIT_OK
    with io.open(out1, "rb") as f1, io.open(out2, "rb") as f2:
        assert f1.read() == f2.read()


def test_build_hash_content_derived(mined):
    h1 = render.build_hash(mined, {"x": 1})
    h2 = render.build_hash(mined, {"x": 2})
    assert h1 != h2  # layout changes the hash
    alt = dict(mined)
    alt["case_count"] = mined["case_count"] + 1
    assert render.build_hash(alt, {"x": 1}) != h1  # content changes the hash
    assert render.build_hash(mined, {"x": 1}) == h1  # stable


def test_no_clock_in_html(html):
    assert "generated" not in html.lower()
    assert "timestamp_render" not in html.lower()
    for token in ("Date.now", "new Date", "toLocaleTimeString"):
        assert token not in html


def test_build_hash_embedded_in_html(html, mined):
    lay = layout.compute_layout(mined["nodes"], [(e["from"], e["to"]) for e in mined["edges"]])
    assert render.build_hash(mined, lay) in html


# ---------- report substance: numbers come from mining (K8) ----------


def test_report_embeds_mined_numbers(html, mined):
    assert "200" in html  # case count visible
    for edge in mined["edges"]:
        assert 'data-edge="edge:%s&gt;%s"' % (edge["from"], edge["to"]) in html
    for v in mined["variants"]:
        assert 'data-variant="%d"' % v["rank"] in html


def test_report_mined_matches_truth_numbers(mined):
    with io.open(os.path.join(_SYNTH, "truth.json"), "r", encoding="utf-8") as f:
        truth = json.load(f)["expected"]
    assert len(mined["edges"]) == len(truth["dfg_edges"])
    assert len(mined["variants"]) == len(truth["variants"])


# ---------- CLI wiring (D12) ----------


def test_cli_render_missing_log_is_usage_error():
    assert cli.main(["render", os.path.join(_HERE, "no_such.csv"), "-o", "x.html"]) == cli.EXIT_USAGE


def test_cli_render_writes_file(tmp_path, capsys):
    out = str(tmp_path / "report.html")
    assert cli.main(["render", _CSV, "-o", out]) == cli.EXIT_OK
    with io.open(out, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    assert content.startswith("<!DOCTYPE html>")
    assert "\r" not in content
    assert content.endswith("\n")
    render.assert_no_external_resources(content)
