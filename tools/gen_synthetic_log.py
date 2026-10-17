#!/usr/bin/env python3
"""Synthetic event log + truth generator (module 5, generator side).

M1 will implement: splitmix64 deterministic RNG, "报销审批（虚构）" scenario,
frozen outputs to data/synthetic/ (events.csv, events_variants.json, truth.json,
manifest.json) plus a --check byte-identical regeneration path.
"""

import argparse
import sys


def main(argv=None):
    print("stage not ready: generator is scheduled for milestone M1 (skeleton only)", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
