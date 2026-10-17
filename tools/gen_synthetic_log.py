#!/usr/bin/env python3
"""Synthetic event log + truth generator (module 5, "报销审批（虚构）" scenario).

Deterministic by construction (plan/02 §3, plan/04):
- RNG: self-implemented splitmix64 (K3); stdlib `random` is forbidden — its
  sequence is not promised stable across Python versions.
- Serialization: json.dumps(sort_keys=True, ensure_ascii=False, indent=2),
  LF line endings, trailing newline, no clock fields on disk (K2).
- Outputs (frozen into data/synthetic/, hand edits forbidden):
    events.csv            case_id,activity,timestamp (ISO 8601, naive)
    events_variants.json  same content as CSV, second form
    truth.json            input + expected only, no `observed` field (K8)
    manifest.json         sha256 ledger, computed not hand-written
- Identity asserted here: sum(edge counts) == sum(len(trace) - 1)
  == total events - case count.
- Tied timestamps are planted on purpose (K4: tie-break by source line number
  is exercised downstream); quantiles use linear interpolation (K4).
- --check regenerates into a temp dir and byte-compares against the frozen
  artifacts; mismatch exits 2 (integrity counts as an input-state error, D6).

Plant design (non-trivial truth): a long-wait edge (财务复核→打款), rare
variants (double/triple rework, withdraw-after-reject), and tied timestamps.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO_ROOT, "data", "synthetic")

SEED_DEFAULT = 20261017
SCENARIO = "报销审批（虚构）"
BASE_TIME_LABEL = "2026-01-05T08:00:00"  # fixed epoch label; no system clock
CASE_TARGET = 200

ARTIFACTS = ("events.csv", "events_variants.json", "truth.json", "manifest.json")

# (from, to) -> inclusive wait range in seconds. 财务复核→打款 is the planted
# bottleneck (25h–70h); everything else stays in hours.
EDGE_WAIT_S = {
    ("提交申请", "主管审批"): (300, 5400),
    ("主管审批", "主管审批"): (1800, 14400),
    ("主管审批", "财务复核"): (600, 7200),
    ("财务复核", "打款"): (90000, 250000),
    ("打款", "归档"): (60, 3600),
    ("财务复核", "驳回"): (900, 5400),
    ("驳回", "重新提交"): (7200, 172800),
    ("重新提交", "主管审批"): (300, 3600),
    ("主管审批", "撤回"): (1800, 14400),
    ("财务复核", "撤回"): (1800, 28800),
    ("驳回", "撤回"): (600, 43200),
    ("提交申请", "撤回"): (0, 0),
    ("撤回", "重新提交"): (14400, 86400),
}

# Variant catalogue: (sequence, weight). Weights fix the shape of Top-N; the
# RNG only jitters the remainder allocation, so counts stay near-proportional
# and every variant keeps count >= 1 (rare variants included).
VARIANTS = [
    (("提交申请", "主管审批", "财务复核", "打款", "归档"), 60),
    (("提交申请", "主管审批", "主管审批", "财务复核", "打款", "归档"), 22),
    (("提交申请", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "打款", "归档"), 20),
    (("提交申请", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "驳回", "撤回"), 5),
    (("提交申请", "主管审批", "撤回"), 8),
    (("提交申请", "撤回"), 4),
    (("提交申请", "主管审批", "财务复核", "撤回"), 6),
    (("提交申请", "主管审批", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "打款", "归档"), 9),
    (("提交申请", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "打款", "归档"), 2),
    (("提交申请", "主管审批", "主管审批", "主管审批", "财务复核", "打款", "归档"), 3),
    (("提交申请", "主管审批", "财务复核", "驳回", "撤回"), 4),
    (("提交申请", "主管审批", "财务复核", "打款"), 3),
    (("提交申请", "主管审批", "财务复核", "驳回", "重新提交", "主管审批", "财务复核", "撤回"), 3),
    (("提交申请", "主管审批", "撤回", "重新提交", "主管审批", "财务复核", "打款", "归档"), 5),
]

# Planted tied timestamps (K4): (variant index, position i merges event i with
# i-1, per-case probability). Variant 6 (提交申请→撤回) always ties because its
# edge wait range is (0, 0).
TIE_SPECS = [
    (0, 1, 0.15),  # auto-approval: 提交申请 ties 主管审批
    (4, 1, 0.30),  # 提交申请 ties 主管审批 on the quick-withdraw path
    (5, 1, 1.00),  # 提交申请 ties 撤回, always
]


class SplitMix64(object):
    """Self-implemented splitmix64; stdlib random is forbidden (K3)."""

    MASK64 = (1 << 64) - 1
    GOLDEN = 0x9E3779B97F4A7C15

    def __init__(self, seed):
        self.state = seed & self.MASK64

    def next_u64(self):
        self.state = (self.state + self.GOLDEN) & self.MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.MASK64
        return z ^ (z >> 31)

    def below(self, n):
        if n <= 0:
            raise ValueError("below() needs n > 0")
        return self.next_u64() % n

    def range(self, lo, hi):
        """Inclusive integer range [lo, hi]."""
        return lo + self.below(hi - lo + 1)


def quantile(sorted_vals, q):
    """Linear-interpolation quantile (K4); input must be pre-sorted."""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("quantile of empty list")
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac


def _round3(x):
    return round(x, 3)


def allocate_counts(rng, weights, total):
    """Largest-remainder allocation of `total` cases over variant weights."""
    weight_sum = float(sum(weights))
    raw = [w * total / weight_sum for w in weights]
    counts = [int(math.floor(r)) for r in raw]
    remainder = total - sum(counts)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - counts[i]), i))
    for i in range(remainder):
        counts[order[i % len(order)]] += 1
    # RNG is consumed here so the generator output depends on the seed even
    # when the remainder is empty — keeps the stream shape stable.
    rng.next_u64()
    return counts


def generate_case_events(rng, seq, start_minutes_from_base):
    """Return event timestamps (seconds from BASE) for one case, in order."""
    base_s = 0  # seconds offset from BASE; real datetimes applied later
    start_s = start_minutes_from_base * 60
    stamps = [start_s]
    for i in range(1, len(seq)):
        edge = (seq[i - 1], seq[i])
        lo, hi = EDGE_WAIT_S[edge]
        stamps.append(stamps[-1] + rng.range(lo, hi))
    assert all(stamps[i] >= stamps[i - 1] for i in range(1, len(stamps)))
    return stamps


def build_log(seed):
    """Generate the full event list. Returns (rows, ties_planted)."""
    rng = SplitMix64(seed)
    weights = [w for _, w in VARIANTS]
    counts = allocate_counts(rng, weights, CASE_TARGET)
    assert len([c for c in counts if c > 0]) == len(VARIANTS), "every variant must occur"

    tie_by_variant = {}
    for v_idx, pos, prob in TIE_SPECS:
        tie_by_variant.setdefault(v_idx, []).append((pos, prob))

    # One draw per (case, tie spec) keeps the RNG stream independent of
    # downstream sorting.
    tie_decisions = {}
    for v_idx, pos, _prob in TIE_SPECS:
        for k in range(counts[v_idx]):
            prob = dict((p, pr) for p, pr in tie_by_variant[v_idx])[pos]
            tie_decisions[(v_idx, k, pos)] = rng.below(10000) < int(prob * 10000)

    cases = []  # (start_seconds, variant_index, within-variant ordinal)
    ordinal = {}
    for v_idx, count in enumerate(counts):
        for k in range(count):
            start_minutes = rng.range(0, 60 * 24 * 60)
            cases.append((start_minutes, v_idx, k))
    # File order = start time order (ties by draw order) for a realistic log.
    cases.sort(key=lambda c: (c[0], c[2]))

    rows = []
    ties_planted = 0
    for case_no, (start_minutes, v_idx, k) in enumerate(cases):
        seq = VARIANTS[v_idx][0]
        stamps = generate_case_events(rng, seq, start_minutes)
        for pos, _prob in tie_by_variant.get(v_idx, ()):
            if tie_decisions[(v_idx, k, pos)]:
                stamps[pos] = stamps[pos - 1]
                ties_planted += 1
        case_id = "C%04d" % (case_no + 1)
        for activity, ts_s in zip(seq, stamps):
            rows.append((case_id, activity, ts_s))
    return rows, ties_planted


def derive_truth(rows):
    """Recompute expected values from the log rows alone (K8: no hand numbers).

    Ordering rule mirrors mining (K4/K5): within a case sort by
    (timestamp, source row index); variant Top-N = count desc, then seq
    lexicographic; quantiles = linear interpolation.
    """
    by_case = {}
    for idx, (case_id, activity, ts_s) in enumerate(rows):
        by_case.setdefault(case_id, []).append((ts_s, idx, activity))

    edge_counts = {}
    edge_waits = {}
    case_durations = []
    variants_counter = {}
    for case_id in sorted(by_case):
        events = sorted(by_case[case_id], key=lambda e: (e[0], e[1]))
        seq = tuple(e[2] for e in events)
        variants_counter[seq] = variants_counter.get(seq, 0) + 1
        case_durations.append(events[-1][0] - events[0][0])
        for i in range(1, len(events)):
            edge = (events[i - 1][2], events[i][2])
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
            edge_waits.setdefault(edge, []).append(events[i][0] - events[i - 1][0])

    total_events = len(rows)
    case_count = len(by_case)
    # Identity: every trace of length L contributes L-1 directly-follows pairs.
    trace_len_sum = sum(len(e) for e in by_case.values())
    assert sum(edge_counts.values()) == trace_len_sum - case_count
    assert sum(edge_counts.values()) == total_events - case_count

    edges = [
        {"from": f, "to": t, "count": c}
        for (f, t), c in sorted(edge_counts.items())
    ]

    ranked = sorted(variants_counter.items(), key=lambda kv: (-kv[1], list(kv[0])))
    variants = [
        {
            "rank": rank,
            "seq": list(seq),
            "count": count,
            "ratio": _round3(count / float(case_count)),
        }
        for rank, (seq, count) in enumerate(ranked, 1)
    ]

    bottlenecks = []
    for edge, waits in edge_waits.items():
        waits.sort()
        bottlenecks.append(
            {
                "from": edge[0],
                "to": edge[1],
                "count": edge_counts[edge],
                "median_wait_s": _round3(quantile(waits, 0.5)),
                "p95_wait_s": _round3(quantile(waits, 0.95)),
            }
        )
    bottlenecks.sort(key=lambda b: (-b["median_wait_s"], b["from"], b["to"]))
    for rank, b in enumerate(bottlenecks, 1):
        b["rank"] = rank

    case_durations.sort()
    duration_stats = {
        "min_s": case_durations[0],
        "median_s": _round3(quantile(case_durations, 0.5)),
        "p95_s": _round3(quantile(case_durations, 0.95)),
        "max_s": case_durations[-1],
    }

    activities = sorted(set(r[1] for r in rows))
    truth = {
        "input": {
            "scenario": SCENARIO,
            "seed": None,  # filled by caller
            "base_time": BASE_TIME_LABEL,
            "case_count": case_count,
            "event_count": total_events,
            "activities": activities,
        },
        "expected": {
            "dfg_edges": edges,
            "variants": variants,
            "bottlenecks": bottlenecks,
            "case_durations": duration_stats,
        },
    }
    return truth


def json_text(obj):
    """K2 frozen serialization: sorted keys, UTF-8, indent 2, LF, trailing \\n."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def render_outputs(seed):
    rows, ties_planted = build_log(seed)
    assert ties_planted >= 3, "tie-break coverage must survive any seed"

    truth = derive_truth(rows)
    truth["input"]["seed"] = seed

    # CSV/JSON second form share one source of truth: the row list itself.
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf, lineterminator="\n")
    writer.writerow(["case_id", "activity", "timestamp"])
    base = None  # timestamps rendered from fixed label arithmetic, no clock
    import datetime as _dt

    base = _dt.datetime(2026, 1, 5, 8, 0, 0)
    csv_rows = []
    json_rows = []
    for case_id, activity, ts_s in rows:
        ts_label = (base + _dt.timedelta(seconds=ts_s)).strftime("%Y-%m-%dT%H:%M:%S")
        csv_rows.append([case_id, activity, ts_label])
        json_rows.append({"case_id": case_id, "activity": activity, "timestamp": ts_label})
    writer.writerows(csv_rows)
    events_csv = csv_buf.getvalue()
    events_json = json_text(json_rows)
    truth_json = json_text(truth)

    manifest = {
        "scenario": SCENARIO,
        "seed": seed,
        "counts": {
            "cases": truth["input"]["case_count"],
            "events": truth["input"]["event_count"],
            "edges": len(truth["expected"]["dfg_edges"]),
            "variants": len(truth["expected"]["variants"]),
        },
        "sha256": {
            "events.csv": hashlib.sha256(events_csv.encode("utf-8")).hexdigest(),
            "events_variants.json": hashlib.sha256(events_json.encode("utf-8")).hexdigest(),
            "truth.json": hashlib.sha256(truth_json.encode("utf-8")).hexdigest(),
        },
    }
    return {
        "events.csv": events_csv,
        "events_variants.json": events_json,
        "truth.json": truth_json,
        "manifest.json": json_text(manifest),
    }


def write_outputs(out_dir, seed):
    artifacts = render_outputs(seed)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    for name in ARTIFACTS:
        with io.open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(artifacts[name])
    return artifacts


def run_check(seed):
    frozen = DEFAULT_OUT
    missing = [n for n in ARTIFACTS if not os.path.isfile(os.path.join(frozen, n))]
    if missing:
        print("check failed: frozen artifacts missing in %s: %s" % (frozen, ", ".join(missing)), file=sys.stderr)
        return 2
    tmp_dir = tempfile.mkdtemp(prefix="process_atlas_check_")
    try:
        write_outputs(tmp_dir, seed)
        ok = True
        for name in ARTIFACTS:
            with io.open(os.path.join(frozen, name), "rb") as f:
                frozen_bytes = f.read()
            with io.open(os.path.join(tmp_dir, name), "rb") as f:
                fresh_bytes = f.read()
            if frozen_bytes != fresh_bytes:
                ok = False
                print("check failed: %s differs from frozen artifact" % name, file=sys.stderr)
        if ok:
            print("check ok: regeneration is byte-identical for %d files" % len(ARTIFACTS))
            return 0
        return 2
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _ensure_utf8_stdio():
    """K6 encoding guard, same policy as cli.py (cp936 console left alone)."""
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, "encoding", None)
        if enc and enc.lower().replace("-", "") not in ("utf8",):
            if enc.lower() in ("cp936", "gbk"):
                continue
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def main(argv=None):
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="gen_synthetic_log.py",
        description="Generate the frozen synthetic event log + truth four-pack (deterministic).",
    )
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT, help="SplitMix64 seed (default %d)." % SEED_DEFAULT)
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory (default data/synthetic).")
    parser.add_argument("--check", action="store_true", help="Regenerate into a temp dir and byte-compare with the frozen artifacts.")
    args = parser.parse_args(argv)

    if args.check:
        return run_check(args.seed)
    write_outputs(args.out, args.seed)
    print("wrote %d artifacts to %s (seed=%d)" % (len(ARTIFACTS), args.out, args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
