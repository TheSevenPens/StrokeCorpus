#!/usr/bin/env python3
"""
Builds manifest.json from traces/.

The folder is the corpus. Nothing here lists the recordings by name, because a corpus that
names its files is one that silently shrinks when somebody renames one -- so every recording
in traces/ appears, and everything said about it is measured from it rather than typed
beside it.

Run from the repository root:

    python tools/manifest.py
"""

import json
import os
import re
import glob
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stamp import stamp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES = os.path.join(ROOT, "traces")
OUT = os.path.join(ROOT, "manifest.json")

# What each format version added. A recording carries what its version carried and no more,
# and the absence is real: a version-two recording genuinely has no height, and a corpus
# that filled one in would be publishing a number nobody measured.
VERSIONS = {
    1: "readings at the top level, with no stroke segmentation",
    2: "strokes",
    3: "height above the tablet",
    4: "the raw status word",
    5: "the host clock, so arrival can be told from the pen's own timestamp",
    6: "the approach aged on the host clock, which is what makes hover trustworthy",
    7: "who made it, the tablet's firmware and free-text notes",
}


# Every column the format has ever declared, in the order the format lists them.
KNOWN_COLUMNS = ["at", "arrived", "x", "y", "pressure", "height", "status", "lean", "azimuth", "twist"]

# What a "complete" recording must carry for its tag to be true: both clocks, so the pen's counter
# can be told from real time, and the two channels that say what the pen was doing above the glass.
# Lean, azimuth and twist are not on the list: a tablet that cannot sense twist is not a worse
# recording, so their absence is reported under "channels" and not made a fault.
COMPLETE_NEEDS = ["at", "arrived", "height", "status"]


def channels(recording):
    """Which of the format's columns this recording carries, read from the file and not guessed."""
    declared = recording.get("columns", [])

    return {
        "measured": [c for c in KNOWN_COLUMNS if c in declared],
        "absent": [c for c in KNOWN_COLUMNS if c not in declared],
    }


def hover_trusted(version, columns):
    """Whether the approach and departure can be taken at their word.

    That is a statement about how the recorder aged them -- on the host clock, from format
    version 6 -- so it needs the host clock to be there to be checked against.
    """
    return version >= 6 and "arrived" in columns


def quality(version, columns):
    """The tag a recording carries, and what it means for somebody using it.

    Read from the columns the file declares as well as from its version. A version number says
    what a recorder of that vintage wrote; the columns say what is in this file, and a tool that
    is not that recorder can write version seven and carry less.
    """
    has = set(columns)

    if version >= 6:
        missing = [c for c in COMPLETE_NEEDS if c not in has]

        if not missing:
            return "complete", "Every channel, both clocks, and the approach measured on the host clock."

        return "partial", (
            "The approach is aged on the host clock, as from format version 6. But this recording "
            "does not carry " + ", ".join(missing) + ", so some of what the other recordings "
            "can say about timing or the pen in the air it cannot. What it does carry is sound."
        )
    if version == 5:
        return "hover-suspect", (
            "Both clocks, but the approach was aged on the pen's packet counter, which "
            "runs at 0.673 of real time. Hover here is incomplete; the contact data is sound."
        )
    if version >= 3:
        return "single-clock", (
            "Height and status, but only the pen's own timestamp -- and that is a packet "
            "counter rather than a clock, so nothing here dates a reading in real time."
        )
    if version == 2:
        return "early", "Strokes, and none of the later channels."
    return "raw", (
        "The earliest format: a flat list of readings with no stroke segmentation, no "
        "height, no status, no host clock and no approach."
    )


def rerecord(version, approach, aloft):
    """Whether this recording is worth drawing again, and why."""
    reasons = []

    if approach > 0 and version < 6:
        reasons.append(
            f"carries {approach} approach readings captured before the hover fix, so its "
            "most interesting data is the part that cannot be trusted"
        )

    if version <= 2:
        reasons.append(
            "predates height, status and the host clock, so it cannot answer anything "
            "about timing or about what the pen was doing above the glass"
        )
    elif version < 5:
        reasons.append("has no host clock, so arrival cannot be told from the pen's stamp")

    return reasons


def counts(recording):
    strokes = recording.get("strokes", [])
    flat = recording.get("readings", [])

    return {
        "strokes": len(strokes),
        "contact": sum(len(s.get("readings", [])) for s in strokes) or len(flat),
        "approach": sum(len(s.get("approach", [])) for s in strokes),
        "departure": sum(len(s.get("departure", [])) for s in strokes),
        "aloft": len(recording.get("aloft", [])),
    }


def contact_runs(recording):
    """The runs of consecutive in-contact readings, which is where "the next reading" means something.

    Each stroke is a run, and a version-one file's flat list is one run. Approach and departure
    are left out on purpose: they are airborne, and a pen in the air has no pressure to repeat.
    """
    runs = [stroke.get("readings", []) for stroke in recording.get("strokes", [])]

    if recording.get("readings"):
        runs.append(recording["readings"])

    return runs


# How many holds there must be before a pattern in their lengths is believed. A few that happen
# to be even say nothing; hundreds that are all even say something.
MIN_HOLDS = 30

# The share of holds that must be a multiple of N for N to be called the pressure's period.
PERIOD_FIT = 0.98


def updates(recording, full_scale):
    """How often each channel actually carries a new value, measured from the readings themselves.

    **A reading is not a measurement.** The format records every reading the driver handed over,
    and a driver can hand over the same pressure more than once. On the Cintiq 24 here pressure
    only ever changes on every second reading -- every hold is two readings long, or four, or six,
    never one or three -- while position changes on nearly every one. Nothing in the file says
    so, and nobody looking at a stroke would see it, so it is measured here.

    A figure is None where the recording does not carry the column or has too little to say.
    """
    columns = recording.get("columns", [])
    slot = {name: columns.index(name) for name in columns}
    runs = [run for run in contact_runs(recording) if len(run) >= 2]

    def at(row, name):
        i = slot.get(name)
        return row[i] if i is not None and i < len(row) else None

    pairs = 0
    moved = Counter()
    holds = Counter()
    levels = set()
    seconds = 0.0
    spanned = 0

    for run in runs:
        held = 1
        levels.add(at(run[0], "pressure"))

        for i in range(1, len(run)):
            row, before = run[i], run[i - 1]
            levels.add(at(row, "pressure"))

            # Contact only: a pair with the tip up on either side is a hover, not an update.
            if not (at(before, "pressure") or 0) > 0 or not (at(row, "pressure") or 0) > 0:
                held = 1
                continue

            pairs += 1

            if at(row, "x") != at(before, "x") or at(row, "y") != at(before, "y"):
                moved["position"] += 1

            if at(row, "pressure") != at(before, "pressure"):
                moved["pressure"] += 1
                holds[held] += 1
                held = 1
            else:
                held += 1

            if at(row, "lean") != at(before, "lean") or at(row, "azimuth") != at(before, "azimuth"):
                moved["tilt"] += 1

            for name in ("height", "twist"):
                if at(row, name) != at(before, name):
                    moved[name] += 1

        # The host clock is stamped in batches, so two neighbours say little about time and a
        # whole stroke says a good deal: readings over the time between the first and the last.
        first, last = at(run[0], "arrived"), at(run[-1], "arrived")

        if first is not None and last is not None and last > first:
            seconds += (last - first) / 1e6
            spanned += len(run) - 1

    def share(name, wanted):
        if not pairs or not all(c in slot for c in wanted):
            return None

        return round(moved[name] / pairs, 4)

    # The period is the largest N for which nearly every hold is a multiple of N: a hold of two,
    # four or six readings says "pressure changes every second reading", one of which has the same
    # value twice running. "Nearly" and not "every", because one stray hold in a few hundred --
    # a glitch, a landing -- would otherwise make a plain greatest common divisor read as 1 and
    # hide a pattern that is plainly there.
    total = sum(holds.values())
    period = None
    fit = None

    if total >= MIN_HOLDS:
        for n in range(1, 65):
            share_fitting = sum(c for length, c in holds.items() if length % n == 0) / total

            if share_fitting >= PERIOD_FIT:
                period, fit = n, round(share_fitting, 4)

    distinct = sorted(v for v in levels if v)
    step = min((b - a for a, b in zip(distinct, distinct[1:])), default=None)
    rate = round(spanned / seconds, 1) if seconds > 0 else None

    return {
        "pairs": pairs,
        "changed": {
            "position": share("position", ["x", "y"]),
            "pressure": share("pressure", ["pressure"]),
            "tilt": share("tilt", ["lean"]),
            "height": share("height", ["height"]),
            "twist": share("twist", ["twist"]),
        },
        "pressureHolds": {str(k): holds[k] for k in sorted(holds)},
        "pressurePeriod": period,
        "pressurePeriodFit": fit,
        "pressureStep": step,
        "pressureLevelsAtLeast": (int(full_scale // step) + 1) if step and full_scale else None,
        "readingRateHz": rate,
        "pressureUpdateHz": round(rate / period, 1) if rate and period else None,
    }


def reconciles(recording):
    """Whether the session's own counters agree, where the recording states them."""
    said = recording.get("whatTheSessionCounted")

    if not said:
        return None

    driver = said.get("packetsFromTheDriver", 0)
    delivered = said.get("pointsDelivered", 0)
    offpad = said.get("packetsOutsideTheCaptureRegion", 0)

    return {
        "fromTheDriver": driver,
        "delivered": delivered,
        "outsideTheRegion": offpad,
        "agrees": driver == delivered + offpad or driver == delivered,
    }


def span(recording):
    """How long the recording ran, on each clock it carries, in seconds."""
    columns = recording.get("columns", [])
    rows = []

    for stroke in recording.get("strokes", []):
        rows += stroke.get("readings", [])

    rows += recording.get("readings", [])

    if len(rows) < 2:
        return {}

    out = {}

    for name, key in (("pen", "at"), ("host", "arrived")):
        if key not in columns:
            continue

        slot = columns.index(key)
        values = [r[slot] for r in rows if len(r) > slot]

        if len(values) < 2:
            continue

        out[name] = round((max(values) - min(values)) / 1e6, 3)

    return out


def name(recording, filename):
    """
    What to call a recording.

    The recorder's own gesture field says which mode was used -- twenty-one of these say
    "multi-stroke" -- and its intent field is that mode's canned description. Neither
    says what was drawn. The filename does, because a hand typed it, so the leading part
    of the file name is the name until somebody writes better ones.

    The recorder appends the tablet and the time to what was typed, so that tail is cut off
    again: from the tablet's own name where the file carries one, from the old "-wacom-" marker
    where it does not, and failing both just the timestamp.
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    tablet = recording.get("device", {}).get("tablet", "")
    slug = re.sub(r"[^a-z0-9]+", "-", tablet.lower()).strip("-")

    cut = stem.lower().find("-" + slug + "-") if slug else -1

    if cut < 0:
        cut = stem.lower().find("-wacom-")

    if cut > 0:
        stem = stem[:cut]
    else:
        stem = re.sub(r"-\d{8}-\d{6}$", "", stem)

    return stem.replace("-", " ")


def main():
    recordings = []

    for path in sorted(glob.glob(os.path.join(TRACES, "*.json"))):
        with open(path, encoding="utf-8") as handle:
            recording = json.load(handle)

        version = recording.get("formatVersion", 0)
        howMany = counts(recording)
        columns = recording.get("columns", [])
        tag, meaning = quality(version, columns)
        device = recording.get("device", {})
        full_scale = device.get("fullScalePressure", 0)

        recordings.append({
            "file": os.path.basename(path),
            "id": recording.get("id", ""),
            "name": name(recording, path),
            "recordedAt": recording.get("recordedAt", ""),
            "formatVersion": version,
            "formatAdded": VERSIONS.get(version, ""),
            "gesture": recording.get("gesture", ""),
            "intent": recording.get("intent", ""),
            "endedBy": recording.get("endedBy", ""),
            "device": {
                "tablet": device.get("tablet", ""),
                "driver": device.get("driver", ""),
                "api": device.get("api", ""),
                "fullScalePressure": full_scale,
                # Absent before format version 7, and empty when the person was asked and wrote
                # nothing. Those are different answers, so the absence is kept as null.
                "firmware": device.get("firmware"),
            },
            "columns": columns,
            "channels": channels(recording),
            "counts": howMany,
            "seconds": span(recording),
            "updates": updates(recording, full_scale),
            "counters": reconciles(recording),
            "quality": tag,
            "qualityMeans": meaning,
            "hoverTrusted": hover_trusted(version, columns),
            "reRecord": rerecord(version, howMany["approach"], howMany["aloft"]),
            "bytes": os.path.getsize(path),
        })

    manifest = {
        "format": "stroke-corpus/manifest",
        "formatVersion": 1,
        "recordings": recordings,
        "totals": {
            "recordings": len(recordings),
            "strokes": sum(t["counts"]["strokes"] for t in recordings),
            "contact": sum(t["counts"]["contact"] for t in recordings),
            "approach": sum(t["counts"]["approach"] for t in recordings),
            "aloft": sum(t["counts"]["aloft"] for t in recordings),
            "byQuality": dict(Counter(t["quality"] for t in recordings)),
            # How many readings go by between one pressure update and the next, where the
            # recording had enough holds to say. 1 is a fresh pressure on every reading.
            "byPressurePeriod": dict(Counter(
                str(t["updates"]["pressurePeriod"]) for t in recordings
                if t["updates"]["pressurePeriod"])),
            "wantingReRecording": sum(1 for t in recordings if t["reRecord"]),
            "devices": sorted({t["device"]["tablet"] for t in recordings if t["device"]["tablet"]}),
            "backends": sorted({t["device"]["api"] for t in recordings if t["device"]["api"]}),
        },
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")

    versions = stamp()

    print(f"{OUT}: {len(recordings)} recordings")
    print(f"  assets: " + ", ".join(f"{a} v={v}" for a, v in versions.items()))
    print(f"  by quality: {manifest['totals']['byQuality']}")
    print(f"  pressure changes every N readings, by recording: {manifest['totals']['byPressurePeriod']}")
    print(f"  wanting re-recording: {manifest['totals']['wantingReRecording']}")
    print(f"  readings: {manifest['totals']['contact']} in contact, "
          f"{manifest['totals']['approach']} approach, {manifest['totals']['aloft']} aloft")


if __name__ == "__main__":
    main()
