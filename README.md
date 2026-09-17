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

What is here is one hand, one tablet, one backend, recorded deliberately: a tap, a spiral, a
pressure ramp, cross-hatching, flicks that reverse inside a single step, loops at four sizes
to see how the pen's lean follows the arm, a stroke held still while the pressure rises.

## What is in it

| | |
|---|---|
| recordings | 33 |
| strokes | 200 |
| readings in contact | 31,332 |
| approach readings | 3,235 |
| readings aloft | 31,240 |
| tablet | Wacom Cintiq 24, driver 6.4.14-1 |
| backend | Wintab (digitizer), full-scale pressure 32767 |

Each recording carries positions, pressure, tilt as a lean and an azimuth, barrel rotation, and —
depending on its format version — height above the tablet, the raw status word, and a second
clock belonging to the host rather than to the pen.

## Read the quality tags before you use it

**Every recording's contact data is sound.** The tags are about the rest.

| tag | recordings | what it means |
|---|---|---|
| `complete` | 1 | every channel, both clocks, and the approach measured on the host clock |
| `hover-suspect` | 4 | both clocks, but the approach was aged on the pen's packet counter, so hover is incomplete |
| `single-clock` | 9 | height and status, but only the pen's own timestamp |
| `early` | 7 | strokes, and none of the later channels |
| `raw` | 12 | a flat list of readings with no stroke segmentation at all |

Thirty-one of the thirty-three are tagged **wants re-recording**, and the site says why for
each. That is not a warning about the data that is there; it is a list of recordings worth drawing
again now that the recorder is better.

## The one thing to know before you compute anything

**The pen's own timestamp is a packet counter, not a clock.** It advances a flat 4.166 ms per
delivered packet whatever the elapsed time, runs at 0.673 of real time, and resynchronises at
each contact transition. It implies 240 readings a second; the real rate is **161.6**.

Takes at format version 5 and above carry a second timestamp taken from the host's monotonic
clock. Use that one. [FORMAT.md](FORMAT.md) has the rest.

## Contributing a recording

More hands, more tablets, and more backends are exactly what this needs — everything here is
one person on one device, so nothing in it can yet distinguish a fact about *pens* from a
fact about *this pen*.

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
