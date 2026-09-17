#!/usr/bin/env python3
"""
Puts the current content hash of the site's own files into the pages that load them.

A page and the module it imports are separate files with separate cache lifetimes, so a
browser can hold an old `corpus.js` against a new page. When the two have drifted apart the
import itself fails -- *"does not provide an export named run"* -- and that happens **before
any of the page's code runs**, so the page cannot catch it and cannot say anything about it.
It just looks empty, which is exactly how this was reported.

Versioning the URL removes the question. A page only ever asks for the exact module it was
written against, and a browser that has never seen that URL cannot have a stale copy of it.

Run by `manifest.py`, or on its own from the repository root:

    python tools/stamp.py
"""

import glob
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS = ("corpus.js", "corpus.css")


def versions():
    """The short content hash of each asset the pages load."""
    found = {}

    for asset in ASSETS:
        with open(os.path.join(ROOT, asset), "rb") as handle:
            found[asset] = hashlib.sha256(handle.read()).hexdigest()[:8]

    return found


def stamp(quiet=False):
    """Rewrites every page's reference to those assets, and answers the versions used."""
    current = versions()
    changed = []

    for page in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        with open(page, encoding="utf-8") as handle:
            text = handle.read()

        before = text

        for asset, version in current.items():
            # Matches "./corpus.js", "corpus.js", and either of those already carrying a
            # version, so running this twice is the same as running it once.
            pattern = (
                r"([\"'])(\./)?" + re.escape(asset) + r"(\?v=[0-9a-f]+)?([\"'])"
            )

            text = re.sub(pattern, r"\1\g<2>" + asset + "?v=" + version + r"\4", text)

        if text != before:
            with open(page, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)

            changed.append(os.path.basename(page))

    if not quiet:
        for name in changed:
            print(f"  stamped {name}")

    return current


if __name__ == "__main__":
    for asset, version in stamp().items():
        print(f"{asset} v={version}")
