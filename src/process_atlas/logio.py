"""Event log schema validation (module 1, M4).

Contract (plan/03 §M4):
  - CSV: column completeness (missing/extra columns), empty rows, parseable
    timestamps, non-empty case_id/activity.
  - All errors are collected first and reported together — never first-error
    aborts (逐行报错, 非首错即停). CSV errors cite 1-based line numbers; JSON
    errors cite the array index.
  - Any validation failure -> exit code 2 (K1: input error, D9/D10 precedent).

Pure stdlib; deterministic; no filesystem writes.
"""

import csv
import io
import json
import sys
from datetime import datetime

_REQUIRED = ("case_id", "activity", "timestamp")


def _parse_timestamp(value):
    """Return a naive datetime or None. Accepts trailing Z (UTC, stripped)."""
    if not isinstance(value, str):
        return None
    ts = value.strip()
    if ts.endswith("Z"):
        ts = ts[:-1]
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def validate_events(rows, source="log"):
    """Validate a list of (locator, case_id, activity, timestamp) tuples.

    `locator` is a pre-formatted position label ("line 12" / "events[3]");
    `source` is unused context kept for message symmetry. Returns the list of
    error strings; empty list means valid.
    """
    errors = []
    for loc, case_id, activity, ts in rows:
        if not str(case_id).strip():
            errors.append("%s: case_id is empty" % loc)
        if not str(activity).strip():
            errors.append("%s: activity is empty" % loc)
        if _parse_timestamp(ts) is None:
            errors.append("%s: timestamp not parseable: %r" % (loc, ts))
    return errors


def validate_csv(path):
    """Validate a CSV event log; returns list of error strings (may be empty)."""
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return ["%s: empty file (no header row)" % path]
        header = [h.strip() for h in header]
        missing = [c for c in _REQUIRED if c not in header]
        extra = [c for c in header if c and c not in _REQUIRED]
        errors = []
        if missing:
            errors.append("%s: missing columns: %s" % (path, ", ".join(missing)))
        if extra:
            errors.append("%s: unexpected extra columns: %s" % (path, ", ".join(extra)))
        if missing:
            # Rows cannot be field-checked without the required columns; stop here.
            return errors

        idx = {c: header.index(c) for c in _REQUIRED}
        for lineno, row in enumerate(reader, 2):  # header is line 1
            if not any(cell.strip() for cell in row):
                errors.append("line %d: empty row" % lineno)
                continue
            def cell(name, _row=row, _idx=idx, _lineno=lineno):
                pos = _idx[name]
                return _row[pos] if pos < len(_row) else ""
            triple = (cell("case_id"), cell("activity"), cell("timestamp"))
            errors.extend(validate_events([("line %d" % lineno,) + triple]))
    return errors


def validate_json_log(path):
    """Validate a JSON event log (array or {events: [...]});

    returns list of error strings, each citing the array index."""
    with io.open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return ["%s: not valid JSON: %s" % (path, exc)]
    if isinstance(data, dict):
        data = data.get("events")
        if data is None:
            return ["%s: object log must carry an 'events' array" % path]
    if not isinstance(data, list):
        return ["%s: expected a JSON array of events" % path]

    errors = []
    for i, item in enumerate(data):
        loc = "events[%d]" % i
        if not isinstance(item, dict):
            errors.append("%s: event must be an object" % loc)
            continue
        missing = [c for c in _REQUIRED if c not in item]
        if missing:
            errors.append("%s: missing fields: %s" % (loc, ", ".join(missing)))
            continue
        extra = [k for k in item if k not in _REQUIRED]
        if extra:
            errors.append("%s: unexpected extra fields: %s" % (loc, ", ".join(sorted(extra))))
        triple = (item["case_id"], item["activity"], item["timestamp"])
        errors.extend(validate_events([(loc,) + tuple(str(v) for v in triple)]))
    return errors


def validate_log(path):
    """Dispatch by first byte: '['/'{' -> JSON, otherwise CSV. Returns errors."""
    with io.open(path, "rb") as f:
        first = f.read(1)
    if first in (b"[", b"{"):
        return validate_json_log(path)
    return validate_csv(path)


def cmd_validate(path):
    """CLI `validate` wiring. Exit 0 when clean; exit 2 with all errors."""
    if not _path_is_file(path):
        sys.stderr.write("error: log file not found: %s\n" % path)
        return 2
    errors = validate_log(path)
    if errors:
        for err in errors:
            sys.stderr.write("error: %s\n" % err)
        sys.stderr.write("validation failed: %d error(s)\n" % len(errors))
        return 2
    sys.stderr.write("validation ok\n")
    return 0


def _path_is_file(path):
    import os
    return os.path.isfile(path)
