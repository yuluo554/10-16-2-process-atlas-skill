"""DFG / variant / bottleneck mining (modules 2-3).

K conventions implemented here (see plan/06 decision log):
  K4  tie-break = source row order for equal timestamps; quantiles =
      linear interpolation, self-implemented (no stdlib statistics.quantiles).
  K5  Top-N = count descending, ties by activity-sequence lexicographic;
      variant ratio denominator = total case count.
  K8  truth.json is read-only comparison input; this module never writes it.

All numbers are re-derivable: same input -> byte-identical output (K2).
Pure stdlib only.
"""

import csv
import json
from datetime import datetime


def quantile(sorted_vals, q):
    """Linear-interpolation quantile (K4); input must be pre-sorted ascending."""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("quantile of empty list")
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac


def _round3(x):
    return round(x, 3)


def load_events(path):
    """Load an event log (CSV or JSON) into lists of (case_id, activity, datetime, row_no).

    timestamp becomes a naive datetime (no-tz logs per project scope); row_no is
    the 0-based source order, used as the K4 tie-break.
    """
    with open(path, "r", encoding="utf-8", newline="") as f:
        first = f.read(1)
    if first == "[" or first == "{":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("events", [])
        rows = [
            (d["case_id"], d["activity"], d["timestamp"])
            for d in data
        ]
    else:
        with open(path, "r", encoding="utf-8", newline="") as f:
            rows = [
                (r["case_id"], r["activity"], r["timestamp"])
                for r in csv.DictReader(f)
                if r.get("case_id") is not None and r.get("case_id") != ""
            ]

    events = []
    for row_no, (case_id, activity, ts) in enumerate(rows):
        ts = ts.strip()
        if ts.endswith("Z"):
            ts = ts[:-1]
        dt = datetime.fromisoformat(ts)
        events.append((case_id, activity, dt, row_no))
    return events


def mine_dfg(events):
    """Directly-follows edge counts; adjacent pairs after (timestamp, row_no) sort.

    Returns {("from", "to"): count}.
    """
    by_case = {}
    for e in events:
        by_case.setdefault(e[0], []).append(e)
    edges = {}
    for case_id in sorted(by_case):
        evs = sorted(by_case[case_id], key=lambda e: (e[2], e[3]))
        for prev, cur in zip(evs, evs[1:]):
            key = (prev[1], cur[1])
            edges[key] = edges.get(key, 0) + 1
    return edges


def mine_variants(events, case_total=None):
    """Variant sequences with counts, ratio (denominator = case count) and rank (K5).

    Returns (list of {rank, seq, count, ratio}, case_total).
    """
    by_case = {}
    for e in events:
        by_case.setdefault(e[0], []).append(e)
    counts = {}
    for case_id in sorted(by_case):
        evs = sorted(by_case[case_id], key=lambda e: (e[2], e[3]))
        seq = tuple(a for _, a, _, _ in evs)
        counts[seq] = counts.get(seq, 0) + 1
    if case_total is None:
        case_total = len(by_case)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], list(kv[0])))
    variants = [
        {
            "rank": rank,
            "seq": list(seq),
            "count": count,
            "ratio": _round3(count / float(case_total)),
        }
        for rank, (seq, count) in enumerate(ranked, 1)
    ]
    return variants, case_total


def bottlenecks(events, edge_counts=None):
    """Per-edge wait-time stats over adjacent pairs; ranked by median desc (K5 tie by from,to).

    Returns list of {from, to, count, median_wait_s, p95_wait_s, rank}.
    """
    by_case = {}
    for e in events:
        by_case.setdefault(e[0], []).append(e)
    if edge_counts is None:
        edge_counts = mine_dfg(events)
    waits = {}
    for case_id in sorted(by_case):
        evs = sorted(by_case[case_id], key=lambda e: (e[2], e[3]))
        for prev, cur in zip(evs, evs[1:]):
            key = (prev[1], cur[1])
            waits.setdefault(key, []).append((cur[2] - prev[2]).total_seconds())

    out = []
    for edge, count in edge_counts.items():
        ws = sorted(waits.get(edge, []))
        out.append(
            {
                "from": edge[0],
                "to": edge[1],
                "count": count,
                "median_wait_s": _round3(quantile(ws, 0.5)),
                "p95_wait_s": _round3(quantile(ws, 0.95)),
            }
        )
    out.sort(key=lambda b: (-b["median_wait_s"], b["from"], b["to"]))
    for rank, b in enumerate(out, 1):
        b["rank"] = rank
    return out


def case_stats(events):
    """Case duration distribution: min / median / p95 / max, seconds."""
    by_case = {}
    for e in events:
        by_case.setdefault(e[0], []).append(e)
    durations = []
    for case_id in sorted(by_case):
        evs = sorted(by_case[case_id], key=lambda e: (e[2], e[3]))
        durations.append(int((evs[-1][2] - evs[0][2]).total_seconds()))
    durations.sort()
    return {
        "min_s": durations[0],
        "median_s": _round3(quantile(durations, 0.5)),
        "p95_s": _round3(quantile(durations, 0.95)),
        "max_s": durations[-1],
    }


def mine(events):
    """Full mining result dict (schema per plan/03 M2): nodes/edges/variants/case_stats."""
    edge_counts = mine_dfg(events)
    variants, case_total = mine_variants(events)
    nodes = sorted(set(a for _, a, _, _ in events))
    dfg_edges = [
        {"from": f, "to": t, "count": c}
        for (f, t), c in sorted(edge_counts.items())
    ]
    return {
        "nodes": nodes,
        "edges": dfg_edges,
        "variants": variants,
        "bottlenecks": bottlenecks(events, edge_counts),
        "case_stats": case_stats(events),
        "case_count": case_total,
    }


def mine_to_json(events):
    """K2 serialization: sort_keys, no ascii escapes, indent=2, trailing newline."""
    return json.dumps(mine(events), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
