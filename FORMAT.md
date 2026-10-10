# The trace format

One recording is one JSON file: the pen arrived, drew some strokes, and the recording
stopped.

The files say `"format": "stroke-field-guide/take"`. That is the recorder's own name for the
same thing, and it is left alone here: it is a published identifier belonging to the tool
that writes these files rather than to this corpus.

Every file declares `formatVersion`, and **a reader must handle every version** — a column
a file does not carry is unmeasured, not zero. A version-two
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

## Who, on what, and anything else

The example above is a real version-6 recording. From **version 7** a recording also says who
made it, what firmware the tablet was running, and anything they wanted to add:

```json
{
  "formatVersion": 7,
  "username": "...",
  "notes": "...",
  "device": {
    "tablet": "Wacom Cintiq 24",
    "driver": "Wacom driver 6.4.14-1",
    "firmware": "..."
  }
}
```

| field | where | what it is |
|---|---|---|
| `username` | top level | who made the recording, as they chose to write it |
| `notes` | top level | free text from the person who made it. May contain line breaks |
| `firmware` | `device` | the tablet's firmware, as typed in |
| `pen` | `device` | the pen, as typed in; optional in any version (see below) |

All three are typed in by the person recording; nothing detects them, so treat them as
claims rather than measurements, like `tablet` and `driver`.

**Absent and empty mean different things.** A recording before version 7 has none of these
fields: nobody was asked, so they are unrecorded. In a version-7 recording they are always
present, and an empty string means the person was asked and wrote nothing. A reader should
not report an absent `firmware` as "no firmware" or an absent `username` as an anonymous
user.

## The pen

A recording may say which pen it was made with, in **`device.pen`**, as the person who made it typed
it:

```json
{
  "device": {
    "tablet": "Wacom Intuos Pro Large",
    "pen": "ACP-700"
  }
}
```

- **Optional, and any version can have one.** A non-empty string. Absent means nobody said, which
  is every recording made before the recorder asked. A reader should not report an absent `pen` as
  "no pen".
- **It is a claim, like `tablet` and `driver`.** Nothing detects it. The readings can hint at what
  a pen can do, such as whether it reports a `twist` or how many reports a second it makes, and in
  this corpus those separated the pens, but they cannot name one.
- **Like the name, it may be added or changed after a recording was made.** It is a label the person
  typed, not a measurement, so saying which pen a recording was made with later does not make it
  `editedAfterRecording`. Only the `device.pen` line may change; anything else is still an edit, and
  `tools/check_names_only.py` fails a pull request that makes one.
- **StrokeRecorder writes it** from the Save step, remembers the last one between launches, and
  the catalogue and each recording's page show it.

## The driver

**`device.driver`** is the driver version, as the person who made the recording typed it, and it is
a claim like the tablet's name: nothing detects it. The recorder's Save step asks for it, and an
empty string means it was left blank.

Like [the name](#a-name) and [the pen](#the-pen), it is a label and not a measurement, so it may be
filled in or corrected after a recording was made without making the recording
`editedAfterRecording`. Only the `device.driver` line may change; anything else is still an edit, and
`tools/check_names_only.py` fails a pull request that makes one.

## The tablet's name

**`device.tablet`** is the name of the tablet, as the person who made the recording typed it, and it is
a claim like the driver: nothing detects it. It may contain spaces (`Wacom PTK-870`); the recorder
strips whitespace round it and keeps what is inside.

Like [the name](#a-name), [the pen](#the-pen) and [the driver](#the-driver), it is a label and not a
measurement, so it may be corrected after a recording was made without making the recording
`editedAfterRecording`. Only the `device.tablet` line may change; anything else is still an edit, and
`tools/check_names_only.py` fails a pull request that makes one. The file name a recording was saved
under was made from the name it had then and is not renamed.

## The firmware

**`device.firmware`** is the tablet's firmware, as the person who made the recording typed it, and it is
a claim like the driver: nothing detects it. An empty string means it was left blank, and what was
typed is exactly what is there, whether or not it is a firmware version.

Like [the name](#a-name), [the pen](#the-pen) and [the driver](#the-driver), it is a label and not a
measurement, so it may be filled in or corrected after a recording was made without making the
recording `editedAfterRecording`. Only the `device.firmware` line may change; anything else is still an
edit, and `tools/check_names_only.py` fails a pull request that makes one.

## A name

A recording may carry a top-level **`name`**: what the person who made it calls it.

```json
{
  "formatVersion": 8,
  "id": "multi-stroke-intuosprolarge-2025-20261008-172252",
  "name": "Quick taps"
}
```

- **Optional, and any version can have one.** A non-empty string. Absent means nobody named the
  recording, and the catalogue then works a name out from the file name, as it did before this
  field existed.
- **The catalogue shows it.** `manifest.json`'s `name` is this when the recording has one, and is the
  name every page displays.
- **With [the tablet's name](#the-tablets-name), [the pen](#the-pen), [the driver](#the-driver) and
  [the firmware](#the-firmware), it is the only thing that may be added or changed after a recording
  was made.** Everything else in a recording is original evidence and is
  never rewritten. A name is a label and not a measurement, so giving a recording one, or changing it,
  does not make the recording `editedAfterRecording`. A change to anything but the `name`,
  `device.tablet`, `device.pen`, `device.driver` and `device.firmware` lines is still an edit, and `tools/check_names_only.py` fails a
  pull request that makes one.
- **StrokeRecorder writes it** from the Save step, where it is typed in like the tablet and driver
  names. Treat it as a claim, like those.

## What `x` and `y` are

Before version 8 a recording did not say, and `x` and `y` were positions on the desktop in the
units `placement` describes. From **version 8** a recording says so, in `coordinates`:

```json
{
  "formatVersion": 8,
  "coordinates": {
    "space": "tablet",
    "units": "digitizer counts",
    "maxX": 62500,
    "maxY": 39062,
    "widthMm": 224.0,
    "heightMm": 126.0
  }
}
```

A desktop recording from a Wintab backend, which can ask the driver how big the tablet is:

```json
{
  "formatVersion": 8,
  "coordinates": {
    "space": "desktop",
    "units": "desktop physical pixels, as reported by the session",
    "widthMm": 349,
    "heightMm": 195,
    "mappedWidthMm": 349,
    "mappedHeightMm": 195,
    "mmPerPixelX": 0.090885,
    "mmPerPixelY": 0.060185
  }
}
```

| `space` | `x` and `y` are | `coordinates` also carries | `placement` |
|---|---|---|---|
| `desktop` | positions on the desktop, in the units `placement` describes: what every earlier version means | `units`, and optionally `widthMm`, `heightMm`, `mappedWidthMm`, `mappedHeightMm`, `mmPerPixelX`, `mmPerPixelY` | required |
| `tablet` | the device's own digitizer counts, as it reported them, before any mapping to a display | `units`, `maxX`, `maxY`, `widthMm`, `heightMm` | absent |

- **Why a tablet space exists.** A position on the desktop has the driver's mapping, the display
  layout and the scaling mixed into it, so the same hand on the same tablet gives different
  numbers under different settings, and the file records where the monitors were. A count does
  not. It is also the only thing a tool that reads the device itself, rather than the operating
  system, can honestly say.
- **No pixels.** There is no screen in a tablet recording, so a length or a speed is in counts.
  `maxX` and `maxY` are the largest count the digitizer reports on each axis and `widthMm` and
  `heightMm` the physical size of its area, so a count is `x * widthMm / maxX` millimetres along
  that axis, and speeds from different devices can be compared in millimetres a second.
- **How far is that in millimetres, in either space.** A reader that wants a distance or a speed
  from a recording of either kind needs one number per axis, and gets it like this:

  | `space` | millimetres for one unit of `x` | and of `y` |
  |---|---|---|
  | `tablet` | `widthMm / maxX` | `heightMm / maxY` |
  | `desktop`, with `mmPerPixelX` and `mmPerPixelY` | `mmPerPixelX` | `mmPerPixelY` |
  | `desktop`, without them | unknown | unknown |

  Scale each component by its own axis and then combine them:
  `sqrt((dx * mmX)^2 + (dy * mmY)^2)`. **Do not scale a length in pixels by one figure.** A
  tablet mapped across a desktop of another shape is stretched: a 349 x 195 mm surface mapped
  across 3840 x 3240 pixels is 0.091 mm a pixel across and 0.060 mm a pixel down.
- **Desktop recordings may say how big the tablet is.** In both spaces `widthMm` and `heightMm`
  mean the same thing: the whole active area of the tablet. A desktop recording made through a
  backend that can ask the driver also carries the part of that area the driver had mapped to the
  desktop (`mappedWidthMm`, `mappedHeightMm`, the whole of it unless the user chose a partial or
  proportion-forced mapping) and the scale (`mmPerPixelX`, `mmPerPixelY`: the mapped size over
  the desktop pixels it lands on). They go in pairs, and the mapped size and the scale need
  `widthMm`. **Absent means the backend could not say**, which includes every recording made
  before this was added; it does not mean a tablet of no size. Wintab states it through the
  unit and resolution of its X and Y axes. The pointer backends are not asked yet.
- **Where the size comes from differs, and is not recorded.** A tablet recording takes it from
  the driver's specification for that tablet; a Wintab desktop recording asks the driver at the
  time. Both are what the driver says, not something measured with a ruler, and a driver that
  places the pen wrongly on the desktop has its distances wrong by the same factor.
- **The axes are the device's.** The origin and the direction of each axis are whatever the
  device reports and are not normalized. Do not assume the origin is at the top left.
- **Absent and empty mean different things.** A recording before version 8 has no `coordinates`,
  and a reader must treat that as `desktop`, not as unknown. In a version-8 recording it is
  always present.
- **`placement`.** It describes where a desktop recording was made, so a desktop recording keeps
  it and a tablet recording has none: there is no desktop to place.

Version 8 also changes what `columns` may be. Until now every version declared one fixed list,
because every recorder measured every channel. A recording from a tool that cannot measure one,
such as one that reads the device directly and so has no pen timestamp or status word, carries
only the columns it did measure, and must still carry `x`, `y` and `pressure`. A column the file
does not declare is unmeasured, not zero, as it always was.

## Readings are rows, not objects

A reading is an array whose slots are named by `columns`. One recording can hold tens of
thousands of them, and an object per reading would be mostly repeated key names.

| column | what it is |
|---|---|
| `at` | the pen's own timestamp, microseconds. **Not a clock** — see below |
| `arrived` | the host's monotonic clock, microseconds, stamped when the batch was drained |
| `x`, `y` | a position: on the desktop, in the units `placement` describes, or from version 8 whatever `coordinates` says |
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

## A reading is not a measurement

Every reading a driver handed over is kept, and a driver can hand over the same value more
than once. Two consecutive readings with the same pressure may be one measurement reported
twice, or two measurements that happened to agree, and the readings alone cannot say which.
A reader should not treat each reading as an independent sample of the pen, and should check
how often a channel actually changes before computing a rate of change from it.

How often a channel carries a new value belongs to the device and to the way it was read; it is
**not a rule of the format**. The catalogue describes it for every recording, in `updates`:

| field | what it is |
|---|---|
| `changed` | the share of consecutive in-contact readings, within a stroke, whose position, pressure, tilt, height or twist differs from the reading before. `null` where the file does not carry the column that measure needs (tilt needs both `lean` and `azimuth`) |
| `pressureHolds` | how many readings each pressure value lasted, counted when it ends, over every completed hold. A run still going when the stroke ends is not counted |
| `pressureHoldsInterior` | the same without the first hold of each stretch of contact. A landing can begin part-way through a value, so that hold may be shorter than the value lasted |
| `pressurePeriod`, `pressurePeriodFit`, `pressurePeriodSupport` | the largest N that at least 98% of the interior holds are a multiple of, the share that are, and how many interior holds there were. `null` below 30 interior holds, where there is too little to state a pattern |
| `readingRateHz`, `readingRateSeconds` | readings per second over whole strokes on the host clock, and the seconds of strokes it was measured over. `null` without the host clock |
| `pressureUpdateHzIfPeriodic` | `readingRateHz` divided by `pressurePeriod`: the pressure refresh rate **if** pressure is refreshed on that period. An inference, not a measurement |
| `pressureDistinct`, `pressureStep` | how many distinct non-zero pressures were seen, which is a floor on how many the device can report, and the smallest difference between two of them. The step is a fact about the readings and is not a bound on the resolution |

The period is a description of the hold lengths. Repeated gesture timing or quantization can
produce lengths that share a divisor with no device period behind them, and lost readings can
hide a real one. A hold of four readings in a recording whose period is two is compatible with
two refreshes that agreed, and does not show that two acquisitions happened. The reading rate is
an aggregate over whole strokes: a pause inside a stroke stays in the denominator, a stroke that
fits in one drained batch contributes nothing, and batching at the ends of short strokes can bias
it.

On the Wacom Cintiq 24 and Wintab setup measured here, completed holds are almost always an even
number of readings long, in every recording with enough of them to say. That is consistent with
pressure being refreshed every second delivered reading, which at the measured 161.6 readings a
second would be about 80 refreshes a second, while position changes on nearly every reading while
the pen is moving. The recordings do not establish the underlying acquisition rate, and they do
not say which part of the path from pen to file produces the pattern: the tablet, its firmware,
the driver, or the way the driver was read. That is a measured property of this setup and not a
rule of the format.

## The reading lists

- **`strokes[].readings`** — the pen was touching. This is the mark.
- **`strokes[].approach`** — the readings immediately before that contact, made in the air.
  Only trustworthy at `formatVersion` 6; before that they were aged on the packet counter.
- **`strokes[].departure`** — airborne readings stored after that contact.
- **`aloft`** — every airborne reading kept, when the recording asked for them.

Approach and departure readings can also appear in `aloft`. These lists are not disjoint:
adding their lengths does not count distinct driver packets. Preserve source order and
list membership rather than silently deduplicating identical rows.

A brush is never given an approach reading: a stroke starts where the tip goes down. They
are here because what the pen did on the way to the paper is real and almost nobody records
it.

### What approach and departure hold

Both lists are **windows of a quarter second on the host clock** (`arrived`), before the landing
and after the last contact reading, and both are **filtered**: a hovering reading is kept only
if the pen's position differs from the last one kept, or it carries a lean or an azimuth. A pen
resting in range repeats its position at every report, and keeping all of that would make the
pauses larger than the drawing. So an approach is the pen's *movement* through the air, not every
report it made, and **an empty approach does not mean the pen was not reported.** Both recorders
that write this format do this.

One consequence: the first hovering reading after a lift is not that stroke's departure (the
stroke is still being drawn when it arrives), though it can be in the next stroke's approach, and
a departure reading can also be the next stroke's approach. See the note on `aloft` above about
the lists overlapping.

### Per-stroke fields

| field | meaning |
|---|---|
| `readings` | the contact readings, one array per reading, in the file's `columns`. Required |
| `readingCount` | how many readings that is. A check, not data: the validator rejects a file where it disagrees with `readings` |
| `endedBy` | why the stroke ended, in words, for example `the pen lifted` or `the recording was stopped mid-stroke`. Free text, not a closed list |
| `lastSeenInTheAirMs` | how long before this stroke landed the pen was last reported in the air, in milliseconds on the host clock. Present when it was reported in the air at all |
| `lastSeenInTheAir` | written **instead of** `lastSeenInTheAirMs`, as the string `"the pen was not reported in the air at all"`, when no airborne reading came before the landing. A statement, not a number |

`lastSeenInTheAirMs` exists to answer one question about an empty `approach`: was the pen out of
range, or did the recorder fail to keep what it was given? A large value with an empty approach
means the pen was gone and there was nothing to keep. A small one is the thing to look at.

**How it is measured depends on the recorder, and the file does not say which.** StrokeRecorder
measures it from the last hovering reading *that moved*, because that is the only buffer it keeps.
A pen held still in range before it landed therefore reports the time since it last moved, which
overstates the gap: hover at 0 ms, the same hover again at 1000 ms and contact at 1001 ms is
written as 1001 ms, not 1 (TheSevenPens/StrokeRecorder#9). OpenTabletArtist measures it from the
last airborne reading of any kind. Read a large `lastSeenInTheAirMs` as an upper bound unless you
know the pen was moving, and do not assume a recording has the exact figure unless it came from
OpenTabletArtist's Record mode (its `device.api` is `OpenTabletDriver DeviceReport`). Neither
recorder's value is a measurement of the hardware's silence: it is the interval between reports as
they reached the application.

## Pressure is 13 bits in a 15-bit field

On the device measured here, `fullScalePressure` reports 32767, and every one of the 5,251
distinct pressure values seen across the corpus is `floor(raw * 32767 / 8191)`. The device
reports **8192 levels**, which matches its published specification. The 15-bit field is
wider than the measurement in it.

## Checking a recording

`schema/take.schema.json` is the machine-readable definition: one JSON Schema for a recording in
any of the eight versions. It is not one schema with everything optional. Each version declares
exactly the columns and fields it carries, so a version-two file with a height column, a
version-seven file with no firmware, and a version-eight tablet recording with a `placement` are
all errors and not curiosities. `schema/manifest.schema.json` does the same for `manifest.json`.

Some of what makes a recording well formed relates one part of it to another, which a JSON Schema
cannot say: a reading has as many slots as the file declares columns, only `arrived` may be
null, and the stroke and reading counts a file states are the counts it has. `tools/validate.py`
checks those as well, checks the manifest against the folder, and checks the schema against the
examples in `schema/examples/`, where every file in `invalid/` breaks exactly one rule and must be
rejected for that rule. A schema that accepted everything would pass the recordings, so that last
check is what shows it still rejects what it is meant to.

```
pip install jsonschema
python tools/validate.py                     # everything
python tools/validate.py traces/yours.json   # one recording
```

The examples are synthetic and live outside `traces/` on purpose: they are for testing the
schema, they are not evidence about a pen, and nothing counts them.

## Version history

| version | added |
|---|---|
| 1 | readings at the top level in a `readings` array, with no stroke segmentation |
| 2 | the `strokes` array |
| 3 | `height` |
| 4 | `status` |
| 5 | `arrived`, the host clock |
| 6 | the approach aged on the host clock, which is what makes hover trustworthy |
| 7 | `username`, `notes` and `device.firmware`. No columns change |
| 8 | `coordinates`, which says what `x` and `y` are. A recording may carry only the columns it measured |

A version-one file has **no `strokes`** and no record of where contact broke. Read its
top-level `readings` as one run and do not infer strokes from pressure unless you say that
is what you did.

## Reading one

`corpus.js` in this repository reads every version for display. Its normalized reading
objects use zero as a fallback for missing channels; that rendering behavior must not be
used to infer measured values. For analysis, read the original rows and index `columns`
once per file, not once per row, preserving which channels are absent.
