# The trace format

One recording is one JSON file: the pen arrived, drew some strokes, and the recording
stopped.

The files say `"format": "stroke-field-guide/take"`. That is the recorder's own name for the
same thing, and it is left alone here: it is a published identifier belonging to the tool
that writes these files rather than to this corpus.

Every file declares `formatVersion`, and **a reader must handle every version** — a column
a file does not carry gives the field's default, because the absence is real. A version-two
recording genuinely has no height, and a reader that invented one would be reporting a
number nobody measured.

```json
{
  "format": "stroke-field-guide/take",
  "formatVersion": 6,
  "id": "approach-confirmed-wacom-cintiq-24-20260917-071628",
  "gesture": "multi-stroke",
  "intent": "A series of strokes recorded as one recording, with the pen lifting between them.",
  "recordedAt": "2026-09-17T07:16:28.9136152-07:00",
  "endedBy": "the recording was stopped",
  "device": {
    "tablet": "Wacom Cintiq 24",
    "driver": "Wacom driver 6.4.14-1",
    "api": "WintabDigitizer",
    "fullScalePressure": 32767,
    "conventions": "..."
  },
  "placement": { "units": "desktop physical pixels, ...", "scaleX": 1, "scaleY": 1, "originX": -2816, "originY": 0 },
  "columns": ["at", "arrived", "x", "y", "pressure", "height", "status", "lean", "azimuth", "twist"],
  "strokes": [
    {
      "approach":  [[...], [...]],
      "readings":  [[...], [...]],
      "departure": [[...]],
      "endedBy": "the pen lifted"
    }
  ],
  "aloft": [[...]],
  "whatTheSessionCounted": {
    "packetsFromTheDriver": 5664,
    "packetsOutsideTheCaptureRegion": 0,
    "pointsDelivered": 5664
  }
}
```

## Readings are rows, not objects

A reading is an array whose slots are named by `columns`. One recording can hold tens of
thousands of them, and an object per reading would be mostly repeated key names.

| column | what it is |
|---|---|
| `at` | the pen's own timestamp, microseconds. **Not a clock** — see below |
| `arrived` | the host's monotonic clock, microseconds, stamped when the batch was drained |
| `x`, `y` | desktop position, in the units `placement` describes |
| `pressure` | a raw count. Meaningless without `device.fullScalePressure` |
| `height` | Wintab's `pkZ`, height above the tablet. 0 to about 401 on the device measured here |
| `status` | the raw status word from the driver, unmasked |
| `lean` | degrees away from vertical: `90 - altitude` |
| `azimuth` | the compass bearing the pen is leaning towards, degrees |
| `twist` | barrel rotation, degrees |

## `at` is a packet counter, not a clock

This is the single most important thing to know before using this data.

On the hardware measured here, `at` **advances a flat 4.166 ms per delivered packet
regardless of how much time actually passed**, runs at **0.673 of real time**, and
resynchronises to real time at each contact transition. It implies a 240/s report rate; the
real one is **161.6/s**, measured against the host clock and confirmed independently.

So:

- **Do not compute speed from `at`** unless you mean speed per counter-second.
- The gap in `at` before every landing is that resynchronisation, not a gap in the data.
- Takes at `formatVersion` 5 and above carry `arrived`, which is a real clock. Use it.

Every reading drained in one batch **shares one `arrived` value**, deliberately. They
genuinely did arrive together — they were sitting in the driver's queue and were handed over
in one call — so giving each its own stamp would invent a spread the delivery did not have.

## The three lists

- **`strokes[].readings`** — the pen was touching. This is the mark.
- **`strokes[].approach`** — the readings immediately before that contact, made in the air.
  Only trustworthy at `formatVersion` 6; before that they were aged on the packet counter.
- **`aloft`** — every airborne reading kept, when the recording asked for them.

A brush is never given an approach reading: a stroke starts where the tip goes down. They
are here because what the pen did on the way to the paper is real and almost nobody records
it.

## Pressure is 13 bits in a 15-bit field

On the device measured here, `fullScalePressure` reports 32767, and every one of the 5,251
distinct pressure values seen across the corpus is `floor(raw * 32767 / 8191)`. The device
reports **8192 levels**, which matches its published specification. The 15-bit field is
wider than the measurement in it.

## Version history

| version | added |
|---|---|
| 1 | readings at the top level in a `readings` array, with no stroke segmentation |
| 2 | the `strokes` array |
| 3 | `height` |
| 4 | `status` |
| 5 | `arrived`, the host clock |
| 6 | the approach aged on the host clock, which is what makes hover trustworthy |

A version-one file has **no `strokes`** and no record of where contact broke. Read its
top-level `readings` as one run and do not infer strokes from pressure unless you say that
is what you did.

## Reading one

`corpus.js` in this repository reads every version in about a hundred lines, and is
the reference. The short version: index `columns` once per file, not once per row.
