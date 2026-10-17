"""M4 tests: logio validator — line-by-line errors, non-first-error-abort,
JSON array-index errors, exit-code contract."""

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

from process_atlas import cli, logio  # noqa: E402

_CSV = os.path.join(_SYNTH, "events.csv")
_JSON_LOG = os.path.join(_SYNTH, "events_variants.json")


@pytest.fixture(scope="module")
def synthetic_ok():
    assert logio.validate_csv(_CSV) == []
    assert logio.validate_json_log(_JSON_LOG) == []


# ---------- happy path ----------


def test_synthetic_csv_and_json_clean(synthetic_ok):
    pass


def test_validate_log_dispatch_clean(synthetic_ok):
    assert logio.validate_log(_CSV) == []
    assert logio.validate_log(_JSON_LOG) == []


def test_cli_validate_ok(capsys):
    assert cli.main(["validate", _CSV]) == cli.EXIT_OK
    assert "validation ok" in capsys.readouterr().err


# ---------- CSV error collection: all errors at once, line numbers ----------


def test_csv_collects_all_errors_not_first_abort(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text(
        "case_id,activity,timestamp\n"
        "C1,提交申请,2026-01-01T10:00:00\n"        # line 2 ok
        ",提交申请,2026-01-01T10:01:00\n"           # line 3 empty case_id
        "C3,提交申请,not-a-date\n"                   # line 4 bad timestamp
        "C4,,2026-01-01T10:03:00\n"                 # line 5 empty activity
        "C5,提交申请,2026-13-99T99:00:00\n"         # line 6 bad timestamp too
        "\n",                                        # line 7 empty row
        encoding="utf-8",
    )
    errors = logio.validate_csv(str(p))
    joined = "\n".join(errors)
    # all five offending lines reported, not just the first
    assert "line 3" in joined and "case_id is empty" in joined
    assert "line 4" in joined and "timestamp not parseable" in joined
    assert "line 5" in joined and "activity is empty" in joined
    assert "line 6" in joined and "timestamp not parseable" in joined
    assert "line 7" in joined and "empty row" in joined
    assert len(errors) == 5
    # error format matches the contract sample
    assert "line 4: timestamp not parseable: 'not-a-date'" in joined


def test_csv_missing_column(tmp_path):
    p = tmp_path / "missing.csv"
    p.write_text("case_id,activity\nC1,提交\n", encoding="utf-8")
    errors = logio.validate_csv(str(p))
    assert any("missing columns: timestamp" in e for e in errors)


def test_csv_extra_column(tmp_path):
    p = tmp_path / "extra.csv"
    p.write_text(
        "case_id,activity,timestamp,extra_col\n"
        "C1,提交申请,2026-01-01T10:00:00,x\n",
        encoding="utf-8",
    )
    errors = logio.validate_csv(str(p))
    assert any("unexpected extra columns: extra_col" in e for e in errors)


def test_csv_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    errors = logio.validate_csv(str(p))
    assert any("empty file" in e for e in errors)


def test_timestamp_trailing_z_ok(tmp_path):
    p = tmp_path / "z.csv"
    p.write_text(
        "case_id,activity,timestamp\nC1,A,2026-01-01T10:00:00Z\n",
        encoding="utf-8",
    )
    assert logio.validate_csv(str(p)) == []


# ---------- JSON path: errors carry array index ----------


def test_json_errors_carry_index(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            [
                {"case_id": "C1", "activity": "A", "timestamp": "2026-01-01T10:00:00"},
                {"case_id": "", "activity": "A", "timestamp": "2026-01-01T10:00:00"},
                {"case_id": "C3", "activity": "A", "timestamp": "garbage"},
                {"case_id": "C4", "activity": "", "timestamp": "2026-01-01T10:00:00"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    errors = logio.validate_json_log(str(p))
    joined = "\n".join(errors)
    assert "events[1]: case_id is empty" in joined
    assert "events[2]: timestamp not parseable: 'garbage'" in joined
    assert "events[3]: activity is empty" in joined
    assert len(errors) == 3


def test_json_missing_field_reported_per_event(tmp_path):
    p = tmp_path / "miss.json"
    p.write_text(
        json.dumps([{"case_id": "C1", "activity": "A"}, {"activity": "A", "timestamp": "x"}]),
        encoding="utf-8",
    )
    errors = logio.validate_json_log(str(p))
    assert any("events[0]: missing fields: timestamp" in e for e in errors)
    assert any("events[1]: missing fields: case_id" in e for e in errors)


def test_json_not_an_array(tmp_path):
    p = tmp_path / "scalar.json"
    p.write_text("42", encoding="utf-8")
    errors = logio.validate_json_log(str(p))
    assert any("expected a JSON array" in e for e in errors)


def test_json_invalid_json(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{nope", encoding="utf-8")
    errors = logio.validate_json_log(str(p))
    assert any("not valid JSON" in e for e in errors)


def test_json_object_with_events_key(tmp_path):
    p = tmp_path / "wrapped.json"
    p.write_text(
        json.dumps({"events": [{"case_id": "C1", "activity": "A", "timestamp": "2026-01-01T10:00:00"}]}),
        encoding="utf-8",
    )
    assert logio.validate_log(str(p)) == []


# ---------- CLI contract ----------


def test_cli_validate_failure_exits_2_and_lists_all(tmp_path, capsys):
    p = tmp_path / "bad.csv"
    p.write_text(
        "case_id,activity,timestamp\n"
        "C1,A,bad-ts-1\n"
        ",A,bad-ts-2\n",
        encoding="utf-8",
    )
    assert cli.main(["validate", str(p)]) == cli.EXIT_USAGE
    err = capsys.readouterr().err
    assert "line 2" in err and "line 3" in err  # both, not first-error-abort
    assert "validation failed: 3 error(s)" in err


def test_cli_validate_missing_file_exit_2():
    assert cli.main(["validate", os.path.join(_HERE, "no_such.csv")]) == cli.EXIT_USAGE
