#!/usr/bin/env python3
"""
Builds docs/manifest.json from traces/.

The folder is the corpus. Nothing here lists the takes by name, because a corpus that
names its files is one that silently shrinks when somebody renames one -- so every take
in traces/ appears, and everything said about it is measured from it rather than typed
beside it.

Run from the repository root:

    python tools/manifest.py
"""

import json
import os
import glob
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES = os.path.join(ROOT, "traces")
OUT = os.path.join(ROOT, "docs", "manifest.json")

# What each format version added. A take carries what its version carried and no more,
# and the absence is real: a version-two recording genuinely has no height, and a corpus
# that filled one in would be publishing a number nobody measured.
VERSIONS = {
    1: "readings at the top level, with no stroke segmentation",
    2: "strokes",
    3: "height above the tablet",
    4: "the raw status word",
    5: "the host clock, so arrival can be told from the pen's own timestamp",
    6: "the approach aged on the host clock, which is what makes hover trustworthy",
}


def quality(version, approach):
    """The tag a take carries, and what it means for somebody using it."""
    if version >= 6:
        return "complete", "Every channel, both clocks, and the approach measured on the host clock."
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
    """Whether this take is worth drawing again, and why."""
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


def counts(take):
    strokes = take.get("strokes", [])
    flat = take.get("readings", [])

    return {
        "strokes": len(strokes),
        "contact": sum(len(s.get("readings", [])) for s in strokes) or len(flat),
        "approach": sum(len(s.get("approach", [])) for s in strokes),
        "departure": sum(len(s.get("departure", [])) for s in strokes),
        "aloft": len(take.get("aloft", [])),
    }


def reconciles(take):
    """Whether the session's own counters agree, where the take states them."""
    said = take.get("whatTheSessionCounted")

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


def span(take):
    """How long the take ran, on each clock it carries, in seconds."""
    columns = take.get("columns", [])
    rows = []

    for stroke in take.get("strokes", []):
        rows += stroke.get("readings", [])

    rows += take.get("readings", [])

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


def name(take, filename):
    """
    What to call a take.

    The recorder's own gesture field says which mode was used -- twenty-one of these say
    "multi-stroke" -- and its intent field is that mode's canned description. Neither
    says what was drawn. The filename does, because a hand typed it, so the leading part
    of the file name is the name until somebody writes better ones.
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    cut = stem.lower().find("-wacom-")

    return (stem[:cut] if cut > 0 else stem).replace("-", " ")


def main():
    takes = []

    for path in sorted(glob.glob(os.path.join(TRACES, "*.json"))):
        with open(path, encoding="utf-8") as handle:
            take = json.load(handle)

        version = take.get("formatVersion", 0)
        howMany = counts(take)
        tag, meaning = quality(version, howMany["approach"])
        device = take.get("device", {})

        takes.append({
            "file": os.path.basename(path),
            "id": take.get("id", ""),
            "name": name(take, path),
            "recordedAt": take.get("recordedAt", ""),
            "formatVersion": version,
            "formatAdded": VERSIONS.get(version, ""),
            "gesture": take.get("gesture", ""),
            "intent": take.get("intent", ""),
            "endedBy": take.get("endedBy", ""),
            "device": {
                "tablet": device.get("tablet", ""),
                "driver": device.get("driver", ""),
                "api": device.get("api", ""),
                "fullScalePressure": device.get("fullScalePressure", 0),
            },
            "columns": take.get("columns", []),
            "counts": howMany,
            "seconds": span(take),
            "counters": reconciles(take),
            "quality": tag,
            "qualityMeans": meaning,
            "reRecord": rerecord(version, howMany["approach"], howMany["aloft"]),
            "bytes": os.path.getsize(path),
        })

    manifest = {
        "format": "stroke-corpus/manifest",
        "formatVersion": 1,
        "takes": takes,
        "totals": {
            "takes": len(takes),
            "strokes": sum(t["counts"]["strokes"] for t in takes),
            "contact": sum(t["counts"]["contact"] for t in takes),
            "approach": sum(t["counts"]["approach"] for t in takes),
            "aloft": sum(t["counts"]["aloft"] for t in takes),
            "byQuality": dict(Counter(t["quality"] for t in takes)),
            "wantingReRecording": sum(1 for t in takes if t["reRecord"]),
            "devices": sorted({t["device"]["tablet"] for t in takes if t["device"]["tablet"]}),
            "backends": sorted({t["device"]["api"] for t in takes if t["device"]["api"]}),
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")

    print(f"{OUT}: {len(takes)} takes")
    print(f"  by quality: {manifest['totals']['byQuality']}")
    print(f"  wanting re-recording: {manifest['totals']['wantingReRecording']}")
    print(f"  readings: {manifest['totals']['contact']} in contact, "
          f"{manifest['totals']['approach']} approach, {manifest['totals']['aloft']} aloft")


if __name__ == "__main__":
    main()
