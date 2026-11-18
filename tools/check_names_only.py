#!/usr/bin/env python3
"""
Checks that only a recording's name, host OS, tablet, pen, driver or firmware labels changed.

Recordings are original evidence and are never rewritten (AGENTS.md, CONTRIBUTING.md). The exceptions
are labels that may be added or changed after the fact: the top-level `name` and `hostOS`,
and `device.tablet`, `device.pen`, `device.driver` and `device.firmware`. The checker compares
every recording in traces/ with the copy in a base revision and fails if any other line differs.

    python tools/check_names_only.py origin/main

A recording that does not exist in the base revision is new, and is not compared: it is checked by
validate.py like any other. A recording that is in the base revision and gone now is reported, because
removing one is a change to the evidence too.

The comparison is on lines, not on parsed JSON, on purpose. Parsed JSON would accept a file that had
been reformatted, or had a number rewritten as another spelling of the same value, and "the same
data" is a weaker claim than "the same file apart from those metadata lines".
"""

import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES = os.path.join(ROOT, "traces")

# The recorder writes a recording's top-level properties at two spaces of indent, one to a line.
# Nothing nested is called "name", and a name is a single line, so this and only this is the name.
NAME_LINE = re.compile(r'^  "name": ')
HOST_OS_PREFIX = '  "hostOS": '

# And the properties of "device" at four. The tablet, the pen, the driver and the firmware are one string
# each on one line, and nothing else at that depth is called any of them.
TABLET_LINE = re.compile(r'^    "tablet": ')
PEN_LINE = re.compile(r'^    "pen": ')
DRIVER_LINE = re.compile(r'^    "driver": ')
FIRMWARE_LINE = re.compile(r'^    "firmware": ')


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def in_base(base):
    """The recordings the base revision has, by file name."""
    listing = git("ls-tree", "--name-only", base, "traces/")

    return sorted(os.path.basename(line) for line in listing.splitlines() if line.endswith(".json"))


def host_os_line(line):
    if not line.startswith(HOST_OS_PREFIX):
        return False
    field = line[len(HOST_OS_PREFIX):].strip().removesuffix(",")
    try:
        value = json.loads(field)
    except json.JSONDecodeError:
        return False
    return isinstance(value, dict) and "name" in value and value.keys() <= {"name", "version"}


def without_labels(text):
    labels = (NAME_LINE, TABLET_LINE, PEN_LINE, DRIVER_LINE, FIRMWARE_LINE)
    return [line for line in text.splitlines()
            if not host_os_line(line) and not any(label.match(line) for label in labels)]


def first_difference(before, after):
    for position, (was, now) in enumerate(zip(before, after), start=1):
        if was != now:
            return position, was, now

    return min(len(before), len(after)) + 1, None, None


def main(argv):
    if len(argv) != 1:
        print(__doc__)

        return 2

    base = argv[0]
    problems = []
    labelled = 0

    for file in in_base(base):
        path = os.path.join(TRACES, file)

        if not os.path.exists(path):
            problems.append(f"{file}: removed. A recording is evidence and is not deleted.")

            continue

        old = git("show", f"{base}:traces/{file}")

        with open(path, encoding="utf-8", newline=None) as handle:
            new = handle.read()

        if old.splitlines() == new.splitlines():
            continue

        before, after = without_labels(old), without_labels(new)

        if before == after:
            labelled += 1

            continue

        line, was, now = first_difference(before, after)
        problems.append(
            f"{file}: changed outside the allowed metadata lines (first difference near line {line}"
            + (f": {was.strip()[:70]!r} became {now.strip()[:70]!r}" if was is not None else ": a different length")
            + ")."
        )

    for problem in problems:
        print("FAIL", problem)

    if problems:
        print(f"{len(problems)} recording(s) changed outside the allowed metadata lines.")

        return 1

    print(f"recordings against {base}: only allowed metadata changed ({labelled} labelled).")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
