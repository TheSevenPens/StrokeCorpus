#!/usr/bin/env python3
"""
Checks the corpus against its own definition, and the definition against its own examples.

Four things, in this order, and any failure is a non-zero exit:

1. Every recording in traces/ against schema/take.schema.json. The schema is per-version, so a
   version-two file with a height column is an error and not a curiosity.
2. The things a JSON Schema cannot say, because they relate one part of a file to another: a
   reading has as many slots as the file declares columns; a null appears only in the arrived
   column; the stroke and reading counts a file states are the counts it has.
3. manifest.json against schema/manifest.schema.json, and against the folder: every recording in
   traces/ is in it and nothing else is. The folder is the corpus, so a manifest that has drifted
   from it is a manifest that needs regenerating.
4. The schema against schema/examples/: every valid example passes, and every invalid one fails
   for the reason schema/examples/expectations.json gives. A schema that accepts everything would
   pass the first three, so this is the check that it still rejects what it is meant to.

This reads recordings; it never changes one.

Needs the jsonschema package:

    pip install jsonschema

Run from anywhere:

    python tools/validate.py                      everything
    python tools/validate.py traces/some.json     just these recordings (steps 1 and 2)
"""

import glob
import json
import os
import sys

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import best_match
except ImportError:
    sys.exit("This needs the jsonschema package: pip install jsonschema")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schema")
TRACES = os.path.join(ROOT, "traces")
EXAMPLES = os.path.join(SCHEMA, "examples")

# How many problems to print for one file before saying how many more there were.
SHOWN = 6


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validator(name):
    schema = load(os.path.join(SCHEMA, name))

    Draft202012Validator.check_schema(schema)

    return Draft202012Validator(schema), schema


def where(error):
    return ".".join(str(part) for part in error.absolute_path) or "(the file)"


def explain(error):
    """The deepest reason an error gives, which is the one worth reading.

    A oneOf or an if/then reports "not valid under any of the given schemas" and keeps the actual
    reasons in its context. Saying only the first would say nothing about which rule was broken.
    Where there are several branches the reasons are grouped by branch and the branch with the
    fewest is the one the file came closest to, which is nearly always the one it meant.
    """
    while error.context:
        branches = {}

        for reason in error.context:
            branches.setdefault(reason.relative_schema_path[0], []).append(reason)

        deeper = best_match(min(branches.values(), key=len))

        if deeper is None:
            break

        error = deeper

    # "not {}" is how the schema says a property may not be there at all. Its own message prints the
    # whole value and says nothing useful, so say it plainly.
    if error.validator == "not" and error.validator_value == {}:
        return f"{where(error)}: this property is not allowed in a recording like this"

    return f"{where(error)}: {error.message[:200]}"


def schema_problems(check, data):
    errors = sorted(check.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])

    # When a rule inside one of the allOf branches fails, the properties that branch would have
    # accounted for count as unaccounted for at the top, and the file is also told it has
    # "unevaluated properties". That is a consequence of the real error and not another one, so it
    # is left out whenever there is a real one to report.
    real = [e for e in errors if not (e.validator == "unevaluatedProperties" and not e.absolute_path)]

    return [explain(error) for error in (real or errors)]


def row_lists(data):
    """Every list of readings in a recording, with a name to say where it was."""
    strokes = data.get("strokes")

    if isinstance(strokes, list):
        for i, stroke in enumerate(strokes):
            if not isinstance(stroke, dict):
                continue

            for name in ("readings", "approach", "departure"):
                if isinstance(stroke.get(name), list):
                    yield f"strokes[{i}].{name}", stroke[name]

    for name in ("readings", "aloft"):
        if isinstance(data.get(name), list):
            yield name, data[name]


def meaning_problems(data):
    """What the schema cannot say: how the parts of one recording relate to each other."""
    problems = []
    columns = data.get("columns")

    if not isinstance(columns, list):
        return problems

    arrived = columns.index("arrived") if "arrived" in columns else None

    for name, rows in row_lists(data):
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                continue

            if len(row) != len(columns):
                problems.append(f"{name}[{i}]: a row has {len(row)} slots but the file declares {len(columns)} columns")
            else:
                for slot, cell in enumerate(row):
                    if cell is None and slot != arrived:
                        problems.append(f"{name}[{i}][{slot}]: a null in the {columns[slot]} column; "
                                        "only arrived may be null, and only where the take has no host clock")

    strokes = data.get("strokes")

    if isinstance(strokes, list):
        if "strokeCount" in data and data["strokeCount"] != len(strokes):
            problems.append(f"strokeCount: the file says {data['strokeCount']} and has {len(strokes)} strokes")

        for i, stroke in enumerate(strokes):
            if isinstance(stroke, dict) and "readingCount" in stroke and isinstance(stroke.get("readings"), list) \
                    and stroke["readingCount"] != len(stroke["readings"]):
                problems.append(f"strokes[{i}].readingCount: the stroke says {stroke['readingCount']} "
                                f"and has {len(stroke['readings'])} readings")

    return problems


def recording_problems(check, data):
    return schema_problems(check, data) + meaning_problems(data)


def report(name, problems):
    if not problems:
        return True

    print(f"FAIL {name}")

    for problem in problems[:SHOWN]:
        print(f"       {problem}")

    if len(problems) > SHOWN:
        print(f"       ... and {len(problems) - SHOWN} more")

    return False


def check_recordings(paths):
    check, _ = validator("take.schema.json")
    good = 0

    for path in paths:
        if report(os.path.basename(path), recording_problems(check, load(path))):
            good += 1

    print(f"recordings: {good} of {len(paths)} valid")

    return good == len(paths)


def set_aside():
    """
    The recordings set-aside.json leaves out of the catalogue, and what is wrong with the list.

    A mistake here is quiet in both directions -- a misspelt name hides nothing, a stale one hides
    something that was meant to come back -- so every entry has to name a recording that is in
    traces/, once, with a reason.
    """
    path = os.path.join(ROOT, "set-aside.json")

    if not os.path.exists(path):
        return set(), []

    listed = load(path)
    problems = []
    seen = set()

    if not isinstance(listed.get("groups"), list):
        return set(), ["set-aside.json: 'groups' must be a list"]

    present = {os.path.basename(each) for each in glob.glob(os.path.join(TRACES, "*.json"))}

    for number, group in enumerate(listed["groups"], start=1):
        if not (isinstance(group.get("reason"), str) and group["reason"].strip()):
            problems.append(f"set-aside.json: group {number} has no reason")

        for name in group.get("files", []):
            if name not in present:
                problems.append(f"set-aside.json: {name} is not in traces/")
            elif name in seen:
                problems.append(f"set-aside.json: {name} is listed twice")

            seen.add(name)

    return seen & present, problems


def supplied():
    """
    What supplied.json says about recordings, and what is wrong with the list.

    Same discipline as set-aside.json: every entry has to name a recording in traces/, once, with a
    reason and something to supply (a driver or a pen), because a misspelt name would quietly supply nothing.
    """
    path = os.path.join(ROOT, "supplied.json")

    if not os.path.exists(path):
        return []

    listed = load(path)
    problems = []
    seen = set()

    if not isinstance(listed.get("groups"), list):
        return ["supplied.json: 'groups' must be a list"]

    present = {os.path.basename(each) for each in glob.glob(os.path.join(TRACES, "*.json"))}

    for number, group in enumerate(listed["groups"], start=1):
        if not (isinstance(group.get("reason"), str) and group["reason"].strip()):
            problems.append(f"supplied.json: group {number} has no reason")

        said = [group.get(key) for key in ("driver", "pen")]

        if not any(isinstance(each, str) and each.strip() for each in said):
            problems.append(f"supplied.json: group {number} supplies neither a driver nor a pen")

        if any(each is not None and not (isinstance(each, str) and each.strip()) for each in said):
            problems.append(f"supplied.json: group {number} has an empty driver or pen")

        for name in group.get("files", []):
            if name not in present:
                problems.append(f"supplied.json: {name} is not in traces/")

            # A recording may appear in two groups, one for the driver and one for the pen, but not
            # be given two answers to the same question.
            for key in ("driver", "pen"):
                if group.get(key):
                    if (name, key) in seen:
                        problems.append(f"supplied.json: {name} is given a {key} twice")

                    seen.add((name, key))

    return problems


def check_manifest():
    check, schema = validator("manifest.schema.json")
    manifest = load(os.path.join(ROOT, "manifest.json"))
    problems = schema_problems(check, manifest)

    if manifest.get("$schema") != schema["$id"]:
        problems.append(f"$schema: the manifest points at {manifest.get('$schema')!r} and its schema is {schema['$id']!r}")

    listed = {entry.get("file") for entry in manifest.get("recordings", []) if isinstance(entry, dict)}
    present = {os.path.basename(path) for path in glob.glob(os.path.join(TRACES, "*.json"))}
    aside, aside_problems = set_aside()

    problems.extend(aside_problems)
    problems.extend(supplied())

    for name in sorted(present - aside - listed):
        problems.append(f"{name} is in traces/ and not in the manifest; run tools/manifest.py")

    for name in sorted(listed - present):
        problems.append(f"{name} is in the manifest and not in traces/; run tools/manifest.py")

    for name in sorted(listed & aside):
        problems.append(f"{name} is set aside in set-aside.json and is also in the manifest; run tools/manifest.py")

    ok = report("manifest.json", problems)

    print(f"manifest: {'valid' if ok else 'not valid'}, {len(listed)} recordings listed"
          + (f", {len(aside)} set aside" if aside else ""))

    return ok


def check_examples():
    check, _ = validator("take.schema.json")
    expected = load(os.path.join(EXAMPLES, "expectations.json"))["invalid"]
    ok = True

    valid = sorted(glob.glob(os.path.join(EXAMPLES, "valid", "*.json")))
    invalid = sorted(glob.glob(os.path.join(EXAMPLES, "invalid", "*.json")))

    for path in valid:
        ok &= report(f"examples/valid/{os.path.basename(path)}", recording_problems(check, load(path)))

    for path in invalid:
        name = os.path.basename(path)
        problems = recording_problems(check, load(path))
        word = expected.get(name)

        if word is None:
            ok &= report(f"examples/invalid/{name}", ["has no entry in expectations.json"])
        elif not problems:
            ok &= report(f"examples/invalid/{name}", ["was accepted, and it should break a rule"])
        elif not any(word.lower() in problem.lower() for problem in problems):
            ok &= report(f"examples/invalid/{name}", [f"failed, but not for the reason given ({word!r}):"] + problems)

    for name in sorted(set(expected) - {os.path.basename(p) for p in invalid}):
        ok &= report(f"expectations.json", [f"names {name}, which does not exist"])

    print(f"examples: {len(valid)} valid, {len(invalid)} invalid, {'all as expected' if ok else 'NOT as expected'}")

    return ok


def main(argv):
    if argv:
        return 0 if check_recordings(argv) else 1

    results = [
        check_recordings(sorted(glob.glob(os.path.join(TRACES, "*.json")))),
        check_manifest(),
        check_examples(),
    ]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
