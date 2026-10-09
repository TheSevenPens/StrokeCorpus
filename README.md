# Stroke Corpus

Recordings of a real pen on a real drawing tablet: every reading the driver delivered,
including the ones made while the pen was still in the air.

**[Browse it](https://thesevenpens.github.io/StrokeCorpus/)** — every recording, every stroke in
it, a reading at a time, with the data downloadable.

## Why this exists

Anyone building a drawing application has to decide what to do with pen input, and almost
everyone decides it against strokes they made up. Generated strokes have no timing noise, no
dropouts, no jitter, and no hand behind them — and a brush engine correct on those has a
whole class of fault still in front of it.

There is very little real stylus data published, and almost none of it includes **hover**.
The pen spends a good part of its life above the glass, the driver reports it the whole time,
and what it does on the way down is a real and almost entirely undocumented signal.

What is listed here is one hand, one tablet, one backend, recorded deliberately: strokes that
rise smoothly from low to high pressure, low-pressure strokes, staccato strokes, quick taps,
circles, loops, zigzags, and pairs of strokes drawn in opposite directions.

An earlier set of 33 recordings, from a Wacom Cintiq 24, is kept in `traces/` and still validated
but is **set aside**: it is not in the catalogue or on the website. See [Set aside](#set-aside).

## What is in it

| | |
|---|---|
| recordings | 9 |
| strokes | 80 |
| readings in contact | 23,192 |
| approach readings | 4,398 |
| readings aloft | 0 |
| tablet | Wacom Intuos Pro Large (2025), driver 6.4.15-1 |
| pen | ACP-700 |
| backend | Wintab (digitizer), full-scale pressure 32767 |

Each recording carries positions, pressure, tilt as a lean and an azimuth, barrel rotation, and —
depending on its format version — height above the tablet, the raw status word, and a second
clock belonging to the host rather than to the pen.

## Read the quality tags before you use it

**Every recording's contact data is sound.** The tags are about the rest.

| tag | recordings | what it means |
|---|---|---|
| `complete` | 9 | every channel, both clocks, and the approach measured on the host clock |
| `partial` | 0 | version 6 or later, but the file does not carry every column, and the tag names which it lacks |
| `hover-suspect` | 0 | both clocks, but the approach was aged on the pen's packet counter, so hover is incomplete |
| `single-clock` | 0 | height and status, but only the pen's own timestamp |
| `early` | 0 | strokes, and none of the later channels |
| `raw` | 0 | a flat list of readings with no stroke segmentation at all |

None of the nine is tagged **wants re-recording**. (Thirty-one of the 33 set-aside recordings
were, and the tag is a list of recordings worth drawing again, not a warning about the data that
is there.)

## Set aside

[`set-aside.json`](set-aside.json) lists recordings that stay in `traces/` as original evidence
and are still validated, but are left out of `manifest.json` and so out of the website. It holds
the 33 earlier recordings from a Wacom Cintiq 24, in format versions 1 to 6, with the reason and
the date. Nothing is deleted: removing a recording from that file and running
`python tools/manifest.py` lists it again. `tools/validate.py` fails if an entry names a file that
is not in `traces/`, so the list cannot go stale without somebody noticing.

## The one thing to know before you compute anything

**The pen's own timestamp is a packet counter, not a clock.** It advances a flat 4.166 ms per
delivered packet whatever the elapsed time, runs at 0.673 of real time, and resynchronises at
each contact transition. It implies 240 readings a second; the real rate is **161.6**.

Takes at format version 5 and above carry a second timestamp taken from the host's monotonic
clock. Use that one. [FORMAT.md](FORMAT.md) has the rest.

## A reading is not always a new measurement

The same recordings show a second thing nobody had measured: **completed pressure holds are
almost always an even number of readings long**. Position changes on nearly every reading while
the pen moves, but a pressure value tends to last two readings, or four, never one or three. That
is consistent with pressure being refreshed every second delivered reading, so there would be
about half as many pressure measurements as readings. A brush that treats every reading as an
independent sample sees a pressure that is flat half the time and jumps the rest.

This is described for every recording on its page and on the
[devices page](https://thesevenpens.github.io/StrokeCorpus/devices.html). It is a description of
the readings and not a finding about the pen: the recordings cannot say whether the tablet, its
firmware, the driver or the way it was read produces it, and the same pen through another
backend may differ. [FORMAT.md](FORMAT.md#a-reading-is-not-a-measurement) has the method and its
limits.

## Contributing a recording

More hands, more tablets, and more backends are exactly what this needs — everything here is
one person on one device, so nothing in it can yet distinguish a fact about *pens* from a
fact about *this pen*.

The format is defined in [FORMAT.md](FORMAT.md) and, machine-readably, in
[`schema/take.schema.json`](schema/take.schema.json); a pull request is checked against it.
See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: record with the
[Stroke Recorder](https://github.com/TheSevenPens/StrokeRecorder), open a pull request with
the JSON file, and say what you drew and on what.

## Licence

The recordings are [CC BY 4.0](LICENSE) — use them for anything, including commercially, and
say where they came from. The site and tooling are MIT.

## Where it came from

Recorded for [StrokeFieldGuide](https://github.com/TheSevenPens/StrokeFieldGuide), a field
guide to turning pen input into marks on a surface, which uses this corpus as a test set.
Several things the guide now states were found by measuring these files rather than by
reasoning about the code — the packet counter, the 13-bit pressure in a 15-bit field, and
that a nib's lean follows the arm on a large stroke and stays where the grip put it on a
small one.
