/*
  Reading a trace, and drawing one.

  Every trace version is read by the same code, because a column a file does not carry
  gives the field's default and the absence is real: a version-two recording genuinely has
  no height, and a reader that invented one would be showing a number nobody measured.
*/

export async function loadManifest() {
  // Revalidated rather than taken from the cache. The manifest and the pages that read it
  // are separate files with separate cache lifetimes, so a browser can hold yesterday's
  // manifest against today's page -- which is how renaming one key in it emptied the front
  // page for a reader whose browser had the old one.
  const response = await fetch("manifest.json", { cache: "no-cache" });

  if (!response.ok) throw new Error(`manifest.json could not be read (${response.status})`);

  const manifest = await response.json();

  // `takes` was this key's name on the first day. Accepted so that a cached manifest is
  // merely old rather than fatal.
  const recordings = manifest.recordings ?? manifest.takes;

  if (!Array.isArray(recordings)) {
    throw new Error("manifest.json has no recordings in it");
  }

  const totals = manifest.totals ?? {};

  return {
    ...manifest,
    recordings,
    totals: { ...totals, recordings: totals.recordings ?? totals.takes ?? recordings.length },
  };
}

export async function loadRecording(file) {
  const response = await fetch(`traces/${file}`);

  if (!response.ok) throw new Error(`${file} could not be read (${response.status})`);

  return response.json();
}

/**
 * Runs a page, and says so on the page when it cannot.
 *
 * Every page here is a module that fetches before it renders, so anything that throws on
 * the way leaves the static HTML standing and every populated element empty. That is the
 * worst failure a page can have: it looks like an empty corpus rather than like a broken
 * one, and it tells the reader nothing to act on.
 */
export async function run(work) {
  try {
    await work();
  } catch (bad) {
    const main = document.querySelector("main") || document.body;

    main.insertAdjacentHTML("afterbegin", `
      <section class="panel" style="border-color: var(--bad)">
        <h2 style="color: var(--bad)">This page could not load its data</h2>
        <p class="note" style="margin-top:0">${String(bad.message || bad)}</p>
        <p class="note">
          A reload usually fixes it &mdash; hold shift while reloading, which asks the browser
          for fresh copies rather than the ones it kept. If it keeps happening,
          <a href="https://github.com/TheSevenPens/StrokeCorpus/issues">say so here</a> and
          quote the line above.
        </p>
      </section>
    `);

    throw bad;
  }
}

/** Which slot each field sits in, read once per file rather than once per row. */
export function slots(recording) {
  const named = recording.columns || [];
  const of = (name) => named.indexOf(name);

  return {
    at: of("at"),
    arrived: of("arrived"),
    x: of("x"),
    y: of("y"),
    pressure: of("pressure"),
    height: of("height"),
    status: of("status"),
    lean: of("lean"),
    azimuth: of("azimuth"),
    twist: of("twist"),
  };
}

const cell = (row, slot) => (slot >= 0 && slot < row.length ? row[slot] : 0);

export function reading(row, slot) {
  return {
    at: cell(row, slot.at),
    arrived: cell(row, slot.arrived),
    x: cell(row, slot.x),
    y: cell(row, slot.y),
    pressure: cell(row, slot.pressure),
    height: cell(row, slot.height),
    status: cell(row, slot.status),
    lean: cell(row, slot.lean),
    azimuth: cell(row, slot.azimuth),
    twist: cell(row, slot.twist),
  };
}

/**
 * Every stroke of a recording, in the order it was drawn.
 *
 * Version one put the readings at the top level with no strokes array, so a recording of
 * that vintage is one stroke as far as anything here is concerned. That is what the file says,
 * not a guess: nothing in it records where contact broke.
 */
export function strokesOf(recording) {
  const slot = slots(recording);
  const out = [];

  if (Array.isArray(recording.readings) && recording.readings.length) {
    out.push({
      readings: recording.readings.map((r) => reading(r, slot)),
      approach: [],
      endedBy: recording.endedBy || "",
      flat: true,
    });
  }

  for (const stroke of recording.strokes || []) {
    const rows = (stroke.readings || []).map((r) => reading(r, slot));

    if (!rows.length) continue;

    out.push({
      readings: rows,
      approach: (stroke.approach || []).map((r) => reading(r, slot)),
      endedBy: stroke.endedBy || "",
      flat: false,
    });
  }

  return out;
}

/** The box a list of readings occupies. */
export function boundsOf(readings) {
  const xs = readings.map((r) => r.x);
  const ys = readings.map((r) => r.y);

  return {
    left: Math.min(...xs),
    right: Math.max(...xs),
    top: Math.min(...ys),
    bottom: Math.max(...ys),
  };
}

/** The distance between two readings. */
export const gap = (a, b) => Math.hypot(b.x - a.x, b.y - a.y);

/**
 * How many millimetres one unit of x and of y is, or null where the recording does not say how big the
 * tablet is. FORMAT.md's rule, for either space: a tablet recording's counts are scaled by the area over
 * the largest count on each axis, and a desktop recording's pixels by the scale it states. One figure per
 * axis, because a tablet mapped across a desktop of another shape is stretched.
 */
export function millimetresPerUnit(recording) {
  const where = recording.coordinates;

  if (where?.space === "tablet") {
    return where.maxX > 0 && where.maxY > 0 && where.widthMm > 0 && where.heightMm > 0
      ? { x: where.widthMm / where.maxX, y: where.heightMm / where.maxY }
      : null;
  }

  return where?.mmPerPixelX > 0 && where?.mmPerPixelY > 0
    ? { x: where.mmPerPixelX, y: where.mmPerPixelY }
    : null;
}

/** The distance between two readings in millimetres: each axis by its own scale, then combined. */
export const gapMm = (a, b, mm) => Math.hypot((b.x - a.x) * mm.x, (b.y - a.y) * mm.y);

/** What a stroke is, in the terms a caption wants. */
export function describe(stroke) {
  const r = stroke.readings;
  let length = 0;
  let widest = 0;

  for (let i = 1; i < r.length; i++) {
    const step = gap(r[i - 1], r[i]);

    length += step;
    widest = Math.max(widest, step);
  }

  const pressures = r.map((p) => p.pressure);

  return {
    readings: r.length,
    length,
    widest,
    lowest: Math.min(...pressures),
    highest: Math.max(...pressures),
    approach: stroke.approach.length,
  };
}

/** Sets a canvas up for the display's pixel density and answers its drawing context. */
function fit(canvas, width, height) {
  const ratio = window.devicePixelRatio || 1;

  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  canvas.style.height = `${height}px`;

  const pen = canvas.getContext("2d");

  pen.setTransform(ratio, 0, 0, ratio, 0, 0);
  pen.clearRect(0, 0, width, height);

  return pen;
}

const styleOf = (name) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/**
 * A stroke as ink: a line whose width follows the pressure.
 *
 * For the gallery, where the question is "which stroke is this" and not "what did each
 * reading say". The analyser draws readings instead, which is a different picture of the
 * same data and answers the other question.
 */
export function drawInk(canvas, stroke, options = {}) {
  const width = options.width || canvas.clientWidth || 140;
  const height = options.height || Math.round(width * 0.72);
  const pen = fit(canvas, width, height);
  const r = stroke.readings;

  if (r.length < 1) return;

  const box = boundsOf(r);
  const pad = 8;
  const scale = Math.min(
    (width - pad * 2) / Math.max(1e-6, box.right - box.left),
    (height - pad * 2) / Math.max(1e-6, box.bottom - box.top)
  );

  const place = (p) => [
    pad + (p.x - box.left) * scale + (width - pad * 2 - (box.right - box.left) * scale) / 2,
    pad + (p.y - box.top) * scale + (height - pad * 2 - (box.bottom - box.top) * scale) / 2,
  ];

  const full = options.fullScale || 32767;

  pen.lineCap = "round";
  pen.lineJoin = "round";
  pen.strokeStyle = options.colour || styleOf("--ink");

  for (let i = 1; i < r.length; i++) {
    const [ax, ay] = place(r[i - 1]);
    const [bx, by] = place(r[i]);

    pen.lineWidth = 0.6 + 3.4 * Math.min(1, r[i].pressure / full);
    pen.beginPath();
    pen.moveTo(ax, ay);
    pen.lineTo(bx, by);
    pen.stroke();
  }

  if (r.length === 1) {
    const [x, y] = place(r[0]);

    pen.fillStyle = options.colour || styleOf("--ink");
    pen.beginPath();
    pen.arc(x, y, 1.6, 0, Math.PI * 2);
    pen.fill();
  }
}

/**
 * A stroke as readings rather than as ink.
 *
 * A dot per reading sized by its pressure, a thread between them, the approach in blue, and
 * the reading at the playhead ringed. Drawing the ink hides the thing worth looking at:
 * where the readings actually fell, how far apart they are, and how much of the mark is
 * being interpolated rather than reported.
 *
 * @param options.view  where to look: `zoom` is a multiple of the fit-to-canvas scale, and `cx`
 *   and `cy` are the stroke coordinates at the middle of the canvas. Left out, the whole stroke
 *   fits. Dot sizes stay the same on screen however far in the view is, so zooming spreads the
 *   readings out rather than inflating them.
 * @returns what a caller needs to turn a zoom into a view: the fit scale, the centre, the
 *   canvas size and the stroke's bounds, so the zoom can be held on the point under a cursor.
 */
export function drawClosely(canvas, stroke, at, options = {}) {
  const width = options.width || canvas.clientWidth || 600;
  const height = options.height || Math.round(width * 0.62);
  const pen = fit(canvas, width, height);

  const all = [...stroke.approach, ...stroke.readings];

  if (!all.length) return null;

  const box = boundsOf(all);
  const pad = 18;

  // One scale for both axes, so a stroke is the shape it was drawn and not that shape
  // stretched to fill a box.
  const base = Math.min(
    (width - pad * 2) / Math.max(1e-6, box.right - box.left),
    (height - pad * 2) / Math.max(1e-6, box.bottom - box.top)
  );

  const view = options.view || {};
  const scale = base * (view.zoom || 1);
  const cx = view.cx ?? (box.left + box.right) / 2;
  const cy = view.cy ?? (box.top + box.bottom) / 2;

  const place = (p) => [width / 2 + (p.x - cx) * scale, height / 2 + (p.y - cy) * scale];

  const ink = styleOf("--ink");
  const quiet = styleOf("--faint");
  const accent = styleOf("--accent");
  const full = options.fullScale || 32767;

  // The approach, in blue, because the pen was not touching: it is real data and it is not
  // part of the mark. It used to be small grey rings, which disappear against the thread and
  // the contact dots until the view is zoomed in; a solid blue dot, a little larger than the
  // faintest contact one, is readable at the fit-to-canvas size.
  pen.fillStyle = styleOf("--hover");

  for (const p of stroke.approach) {
    const [x, y] = place(p);

    pen.beginPath();
    pen.arc(x, y, 3, 0, Math.PI * 2);
    pen.fill();
  }

  // The thread, so the order is visible.
  pen.strokeStyle = quiet;
  pen.beginPath();

  stroke.readings.forEach((p, i) => {
    const [x, y] = place(p);

    if (i === 0) pen.moveTo(x, y);
    else pen.lineTo(x, y);
  });

  pen.stroke();

  stroke.readings.forEach((p, i) => {
    const [x, y] = place(p);
    const size = 1.4 + 3.6 * Math.min(1, p.pressure / full);

    pen.fillStyle = i <= at ? ink : quiet;
    pen.globalAlpha = i <= at ? 1 : 0.45;
    pen.beginPath();
    pen.arc(x, y, size, 0, Math.PI * 2);
    pen.fill();
  });

  pen.globalAlpha = 1;

  const here = stroke.readings[Math.max(0, Math.min(at, stroke.readings.length - 1))];

  if (here) {
    const [x, y] = place(here);

    pen.strokeStyle = accent;
    pen.lineWidth = 2;
    pen.beginPath();
    pen.arc(x, y, 8, 0, Math.PI * 2);
    pen.stroke();
  }

  return { base, width, height, box, cx, cy };
}

/**
 * One channel across a stroke, with a playhead.
 *
 * @param pick  what to read off each reading
 * @param at    which reading the playhead is on
 * @param options.minSpan  the least the vertical axis may cover, in the channel's own units.
 *   A channel that fits itself to its data turns a quantised value into a dramatic one: lean
 *   is reported in whole degrees, so a stroke that only ever read 37 and 38 filled the whole
 *   height with a single degree. A smaller range is centred in this span instead. Ignored
 *   where `from` and `to` fix the axis.
 */
export function drawChannel(canvas, stroke, pick, at, options = {}) {
  const width = options.width || canvas.clientWidth || 600;
  const height = options.height || 74;
  const pen = fit(canvas, width, height);

  const values = stroke.readings.map(pick);

  if (!values.length) return;

  const seenLow = Math.min(...values);
  const seenHigh = Math.max(...values);

  let low = options.from !== undefined ? options.from : seenLow;
  let high = options.to !== undefined ? options.to : seenHigh;

  if (options.minSpan && options.from === undefined && options.to === undefined
      && high - low < options.minSpan) {
    const middle = (low + high) / 2;

    low = middle - options.minSpan / 2;
    high = middle + options.minSpan / 2;
  }

  const range = Math.max(1e-9, high - low);

  const pad = 8;
  const plot = height - pad * 2;
  const step = width / Math.max(1, values.length - 1);

  pen.strokeStyle = styleOf("--rule");
  pen.lineWidth = 1;
  pen.beginPath();
  pen.moveTo(0, height - pad);
  pen.lineTo(width, height - pad);
  pen.stroke();

  pen.strokeStyle = options.colour || styleOf("--ink");
  pen.lineWidth = 1.4;
  pen.beginPath();

  values.forEach((v, i) => {
    const x = i * step;
    const y = pad + plot - ((v - low) / range) * plot;

    if (i === 0) pen.moveTo(x, y);
    else pen.lineTo(x, y);
  });

  pen.stroke();

  // A reading is not a measurement: a driver can hand over the same value twice, and a channel
  // that does is a staircase whose treads are repeats. With room to see them, mark which readings
  // carried a new value (filled) and which repeated the one before (hollow). Without it the
  // readings are a smear, so only the changes are ticked along the baseline.
  let repeated = 0;

  if (options.repeats) {
    const ink = options.colour || styleOf("--ink");
    const y = (v) => pad + plot - ((v - low) / range) * plot;

    values.forEach((v, i) => {
      const same = i > 0 && v === values[i - 1];

      if (same) repeated++;

      if (step >= 5) {
        pen.beginPath();
        pen.arc(i * step, y(v), 2.6, 0, Math.PI * 2);
        pen.lineWidth = 1.2;
        pen.strokeStyle = ink;

        if (same) {
          pen.fillStyle = styleOf("--card");
          pen.fill();
          pen.stroke();
        } else {
          pen.fillStyle = ink;
          pen.fill();
        }
      } else if (!same && i > 0) {
        pen.strokeStyle = ink;
        pen.lineWidth = 1;
        pen.beginPath();
        pen.moveTo(i * step, height - pad);
        pen.lineTo(i * step, height - pad + 5);
        pen.stroke();
      }
    });
  }

  pen.strokeStyle = styleOf("--accent");
  pen.lineWidth = 1.5;
  pen.beginPath();
  pen.moveTo(at * step, 0);
  pen.lineTo(at * step, height);
  pen.stroke();

  pen.fillStyle = styleOf("--quiet");
  pen.font = "11px " + styleOf("--mono").split(",")[0].replace(/"/g, "");
  // What the data covered, not the axis: where the axis was widened, saying "34 to 42" for a
  // channel that only ever read 37 and 38 would claim a range nobody measured.
  const shown = options.from !== undefined || options.to !== undefined
    ? [low, high]
    : [seenLow, seenHigh];

  pen.fillText(`${options.label || ""} ${fmt(shown[0])} to ${fmt(shown[1])}`, 4, 12);

  if (options.repeats && values.length > 1) {
    const say = `${repeated} of ${values.length - 1} readings repeat the one before`;

    pen.textAlign = "right";
    pen.fillText(say, width - 4, 12);
    pen.textAlign = "left";
  }
}

/**
 * Text made safe to put into markup.
 *
 * Recordings are contributed by other people and some of what they say is typed in -- the
 * tablet, the backend, the firmware -- so a page that builds markup from the catalogue must not
 * let one of those strings become markup.
 */
export function esc(text) {
  const entity = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

  return String(text ?? "").replace(/[&<>"']/g, (c) => entity[c]);
}

/**
 * A channel the recording did not measure, said so rather than drawn as a flat line of zeros.
 *
 * `reading()` zero-fills a column a file does not carry, which is right for drawing a position and
 * wrong for anything that claims something about a channel's values.
 */
export function drawAbsent(canvas, label, options = {}) {
  const width = options.width || canvas.clientWidth || 600;
  const height = options.height || 74;
  const pen = fit(canvas, width, height);

  pen.fillStyle = styleOf("--quiet");
  pen.font = "11px " + styleOf("--mono").split(",")[0].replace(/"/g, "");
  pen.fillText(`${label}: not measured in this recording`, 4, 12);
}

const ORDINALS = { 1: "first", 2: "second", 3: "third" };

/** "second", "17th": how a count of readings is said in a sentence about a cadence. */
export function ordinal(n) {
  if (ORDINALS[n]) return ORDINALS[n];

  const tens = n % 100;
  const suffix = tens >= 11 && tens <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th");

  return `${n}${suffix}`;
}

/**
 * How often a recording's pressure takes a new value, in words.
 *
 * Read from what the manifest measured, not from the format version: the cadence is a property
 * of the device and the way it was read, and two recordings of the same version can differ.
 * Answers an em dash where the recording had too few holds for there to be a pattern to state.
 */
export function pressureCadence(updates) {
  const period = updates?.pressurePeriod;

  if (!period) return "—";

  return period === 1 ? "every reading" : `every ${ordinal(period)} reading`;
}

export const fmt = (n) =>
  Math.abs(n) >= 1000 ? Math.round(n).toString() : (Math.round(n * 100) / 100).toString();

/** Reads the query string, which is how a link to one recording or one stroke is written. */
export function asked() {
  const q = new URLSearchParams(location.search);

  return {
    recording: q.get("recording") || "",
    stroke: parseInt(q.get("stroke") || "0", 10) || 0,
  };
}

/** Offers a blob as a download, which is the whole of what "download this one" means. */
export function offer(name, text) {
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
