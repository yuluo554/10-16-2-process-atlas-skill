"""CLI entry: orchestration + exit-code contract.

Exit codes (D6, locked in tests):
  0 = success
  2 = usage / input error (missing file, schema validation failure, unknown subcommand)
  3 = stage not ready (module exists as skeleton only; no fake empty results)

D11 (M2): the `mine` stage retired its not-ready semantics on landing.
D12 (M3): the `render` stage retired its not-ready semantics the same way
(`STAGE_NOT_READY` no longer holds a "render" entry; exit 3 remains for M4).
"""

import argparse
import json
import sys

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_READY = 3

STAGE_NOT_READY = {
    "selftest": "M4",
}


def _ensure_utf8_stdio():
    """Reconfigure stdio to UTF-8 when the console encoding is not UTF-8.

    cp936 (Chinese Windows console) is left untouched per project convention.
    """
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, "encoding", None)
        if enc and enc.lower().replace("-", "") not in ("utf8",):
            if enc.lower() == "cp936" or enc.lower() == "gbk":
                continue
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def build_parser():
    parser = argparse.ArgumentParser(
        prog="process-atlas",
        description="Event log -> deterministic process discovery graph (DFG, variants, bottlenecks).",
    )
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="Validate an event log (CSV/JSON: case_id, activity, timestamp).")
    p_validate.add_argument("log", help="Path to the event log file.")

    p_mine = sub.add_parser("mine", help="Mine DFG, variants and bottlenecks; print result JSON.")
    p_mine.add_argument("log", help="Path to the event log file.")

    p_render = sub.add_parser("render", help="Render the single-file HTML report.")
    p_render.add_argument("log", help="Path to the event log file.")
    p_render.add_argument("-o", "--output", required=True, help="Output HTML path.")

    sub.add_parser("selftest", help="Run the built-in falsifiable check suite.")

    return parser


def main(argv=None):
    _ensure_utf8_stdio()
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    if unknown or (
        args.command not in STAGE_NOT_READY
        and args.command not in ("validate", "mine", "render")
        and args.command is not None
    ):
        print("error: unknown command or arguments: %s" % (unknown or [args.command]), file=sys.stderr)
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    if args.command == "validate":
        import os
        if not os.path.isfile(args.log):
            print("error: log file not found: %s" % args.log, file=sys.stderr)
            return EXIT_USAGE
        from .logio import cmd_validate
        return cmd_validate(args.log)

    if args.command == "mine":
        import os
        if not os.path.isfile(args.log):
            print("error: log file not found: %s" % args.log, file=sys.stderr)
            return EXIT_USAGE
        from .mining import load_events, mine_to_json
        try:
            events = load_events(args.log)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print("error: cannot parse log: %s" % exc, file=sys.stderr)
            return EXIT_USAGE
        sys.stdout.write(mine_to_json(events))
        return EXIT_OK

    if args.command == "render":
        import os
        if not os.path.isfile(args.log):
            print("error: log file not found: %s" % args.log, file=sys.stderr)
            return EXIT_USAGE
        from .mining import load_events, mine
        from .render import write_report
        try:
            events = load_events(args.log)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print("error: cannot parse log: %s" % exc, file=sys.stderr)
            return EXIT_USAGE
        write_report(mine(events), args.output)
        print("report written: %s" % args.output, file=sys.stderr)
        return EXIT_OK

    if args.command in STAGE_NOT_READY:
        print(
            "stage not ready: '%s' is scheduled for milestone %s (skeleton only, no fake output)"
            % (args.command, STAGE_NOT_READY[args.command]),
            file=sys.stderr,
        )
        return EXIT_NOT_READY

    parser.print_help(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
