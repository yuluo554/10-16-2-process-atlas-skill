"""M1 guard tests: frozen data/synthetic/ artifacts (two layers).

Layer 1 — frozen artifact form: schema, identity, ledger, no `observed`.
Layer 2 — regeneration: rerun the generator into a temp dir and byte-compare
          against the frozen artifacts (--check path exercised in-process).
"""

import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SYNTH = os.path.join(_REPO, "data", "synthetic")
_ARTIFACTS = ("events.csv", "events_variants.json", "truth.json", "manifest.json")


def _load_gen():
    spec = importlib.util.spec_from_file_location(
        "gen_synthetic_log", os.path.join(_REPO, "tools", "gen_synthetic_log.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_gen()


def _read(name):
    with io.open(os.path.join(_SYNTH, name), "r", encoding="utf-8", newline="") as f:
        return f.read()


@pytest.fixture(scope="module")
def frozen():
    return {name: _read(name) for name in _ARTIFACTS}


# ---------- layer 1: frozen artifact form ----------


def test_all_artifacts_present():
    for name in _ARTIFACTS:
        assert os.path.isfile(os.path.join(_SYNTH, name)), name


def test_frozen_csv_form(frozen):
    rows = list(csv.DictReader(io.StringIO(frozen["events.csv"])))
    assert len(rows) > 0
    assert list(rows[0].keys()) == ["case_id", "activity", "timestamp"]
    assert frozen["events.csv"].endswith("\n") and "\r" not in frozen["events.csv"]


def test_frozen_json_k2_form(frozen):
    for name in ("events_variants.json", "truth.json", "manifest.json"):
        obj = json.loads(frozen[name])
        reserialized = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        assert frozen[name] == reserialized, name


def test_dual_form_same_content(frozen):
    rows = list(csv.DictReader(io.StringIO(frozen["events.csv"])))
    jrows = json.loads(frozen["events_variants.json"])
    assert len(rows) == len(jrows)
    for r, j in zip(rows, jrows):
        assert (r["case_id"], r["activity"], r["timestamp"]) == (j["case_id"], j["activity"], j["timestamp"])


def test_truth_identity_and_no_observed(frozen):
    truth = json.loads(frozen["truth.json"])
    assert "observed" not in frozen["truth.json"]
    rows = list(csv.DictReader(io.StringIO(frozen["events.csv"])))
    case_ids = set(r["case_id"] for r in rows)
    edge_sum = sum(e["count"] for e in truth["expected"]["dfg_edges"])
    assert edge_sum == len(rows) - len(case_ids)
    # ratio denominator = case count; Top-N ordering = count desc, seq lex
    variants = truth["expected"]["variants"]
    assert sum(v["count"] for v in variants) == len(case_ids)
    keys = [(-v["count"], v["seq"]) for v in variants]
    assert keys == sorted(keys)
    for v in variants:
        assert v["ratio"] == round(v["count"] / float(len(case_ids)), 3)


def test_bottleneck_top_is_planted_long_wait(frozen):
    truth = json.loads(frozen["truth.json"])
    top = truth["expected"]["bottlenecks"][0]
    assert (top["from"], top["to"]) == ("财务复核", "打款")


def test_manifest_sha_matches_frozen_bytes(frozen):
    manifest = json.loads(frozen["manifest.json"])
    for name, digest in manifest["sha256"].items():
        actual = hashlib.sha256(frozen[name].encode("utf-8")).hexdigest()
        assert actual == digest, name
    counts = manifest["counts"]
    rows = list(csv.DictReader(io.StringIO(frozen["events.csv"])))
    truth = json.loads(frozen["truth.json"])
    assert counts["events"] == len(rows)
    assert counts["cases"] == truth["input"]["case_count"]
    assert counts["variants"] == len(truth["expected"]["variants"])
    assert counts["edges"] == len(truth["expected"]["dfg_edges"])


def test_frozen_scenario_and_seed(frozen):
    truth = json.loads(frozen["truth.json"])
    assert truth["input"]["scenario"] == "报销审批（虚构）"
    assert truth["input"]["seed"] == gen.SEED_DEFAULT
    manifest = json.loads(frozen["manifest.json"])
    assert manifest["seed"] == gen.SEED_DEFAULT


def test_no_clock_fields_on_disk(frozen):
    # ISO timestamps of events only; no generation-time fields anywhere.
    for name in _ARTIFACTS:
        assert "generated_at" not in frozen[name]
        assert "timestamp_generated" not in frozen[name]


def test_no_stdlib_random_in_generator():
    with io.open(os.path.join(_REPO, "tools", "gen_synthetic_log.py"), "r", encoding="utf-8") as f:
        src = f.read()
    assert "import random" not in src
    assert "random." not in src


# ---------- layer 2: regeneration byte-compare ----------


def test_regenerate_byte_identical(frozen):
    tmp = tempfile.mkdtemp(prefix="pa_guard_")
    try:
        gen.write_outputs(tmp, gen.SEED_DEFAULT)
        for name in _ARTIFACTS:
            with io.open(os.path.join(tmp, name), "rb") as f:
                fresh = f.read()
            assert fresh == frozen[name].encode("utf-8"), name
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_check_reports_ok(capsys):
    assert gen.run_check(gen.SEED_DEFAULT) == 0


def test_check_detects_tampered_frozen(frozen, monkeypatch, capsys):
    # Point the checker at a corrupted copy: integrity failure must exit 2.
    tmp = tempfile.mkdtemp(prefix="pa_tamper_")
    try:
        for name in _ARTIFACTS:
            content = frozen[name]
            if name == "events.csv":
                content = content.replace("提交申请", "提交申请X", 1)
            with io.open(os.path.join(tmp, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        monkeypatch.setattr(gen, "DEFAULT_OUT", tmp)
        assert gen.run_check(gen.SEED_DEFAULT) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_check_fails_on_missing_frozen(monkeypatch, capsys):
    monkeypatch.setattr(gen, "DEFAULT_OUT", os.path.join(_REPO, "data", "no_such_dir"))
    assert gen.run_check(gen.SEED_DEFAULT) == 2
