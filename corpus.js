/*
  Reading a trace, and drawing one.

  Every trace version is read by the same code, because a column a file does not carry
  gives the field's default and the absence is real: a version-two recording genuinely has
  no height, and a reader that invented one would be showing a number nobody measured.
*/

export async function loadManifest() {
  const response = await fetch("manifest.json");

  if (!response.ok) throw new Error(`manifest.json: ${response.status}`);

  return response.json();
}

export async function loadTake(file) {
  const response = await fetch(`traces/${file}`);

  if (!response.ok) throw new Error(`${file}: ${response.status}`);

  return response.json();
}

/** Which slot each field sits in, read once per file rather than once per row. */
export function slots(take) {
  const named = take.columns || [];
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
 * Every stroke of a take, in the order it was drawn.
 *
 * Version one put the readings at the top level with no strokes array, so a take of that
 * vintage is one stroke as far as anything here is concerned. That is what the file says,
 * not a guess: nothing in it records where contact broke.
 */
export function strokesOf(take) {
  const slot = slots(take);
  const out = [];

  if (Array.isArray(take.readings) && take.readings.length) {
    out.push({
      readings: take.readings.map((r) => reading(r, slot)),
      approach: [],
      endedBy: take.endedBy || "",
      flat: true,
    });
  }

  for (const stroke of take.strokes || []) {
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
 * A dot per reading sized by its pressure, a thread between them, the approach hollow, and
 * the reading at the playhead ringed. Drawing the ink hides the thing worth looking at:
 * where the readings actually fell, how far apart they are, and how much of the mark is
 * being interpolated rather than reported.
 */
export function drawClosely(canvas, stroke, at, options = {}) {
  const width = options.width || canvas.clientWidth || 600;
  const height = options.height || Math.round(width * 0.62);
  const pen = fit(canvas, width, height);

  const all = [...stroke.approach, ...stroke.readings];

  if (!all.length) return;

  const box = boundsOf(all);
  const pad = 18;

  // One scale for both axes, so a stroke is the shape it was drawn and not that shape
  // stretched to fill a box.
  const scale = Math.min(
    (width - pad * 2) / Math.max(1e-6, box.right - box.left),
    (height - pad * 2) / Math.max(1e-6, box.bottom - box.top)
  );

  const offX = (width - (box.right - box.left) * scale) / 2;
  const offY = (height - (box.bottom - box.top) * scale) / 2;
  const place = (p) => [offX + (p.x - box.left) * scale, offY + (p.y - box.top) * scale];

  const ink = styleOf("--ink");
  const quiet = styleOf("--faint");
  const accent = styleOf("--accent");
  const full = options.fullScale || 32767;

  // The approach, hollow, because the pen was not touching: it is real data and it is not
  // part of the mark.
  pen.strokeStyle = quiet;
  pen.lineWidth = 1;

  for (const p of stroke.approach) {
    const [x, y] = place(p);

    pen.beginPath();
    pen.arc(x, y, 2, 0, Math.PI * 2);
    pen.stroke();
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
}

/**
 * One channel across a stroke, with a playhead.
 *
 * @param pick  what to read off each reading
 * @param at    which reading the playhead is on
 */
export function drawChannel(canvas, stroke, pick, at, options = {}) {
  const width = options.width || canvas.clientWidth || 600;
  const height = options.height || 74;
  const pen = fit(canvas, width, height);

  const values = stroke.readings.map(pick);

  if (!values.length) return;

  const low = options.from !== undefined ? options.from : Math.min(...values);
  const high = options.to !== undefined ? options.to : Math.max(...values);
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

  pen.strokeStyle = styleOf("--accent");
  pen.lineWidth = 1.5;
  pen.beginPath();
  pen.moveTo(at * step, 0);
  pen.lineTo(at * step, height);
  pen.stroke();

  pen.fillStyle = styleOf("--quiet");
  pen.font = "11px " + styleOf("--mono").split(",")[0].replace(/"/g, "");
  pen.fillText(`${options.label || ""} ${fmt(low)} to ${fmt(high)}`, 4, 12);
}

export const fmt = (n) =>
  Math.abs(n) >= 1000 ? Math.round(n).toString() : (Math.round(n * 100) / 100).toString();

/** Reads the query string, which is how a link to one take or one stroke is written. */
export function asked() {
  const q = new URLSearchParams(location.search);

  return { take: q.get("take") || "", stroke: parseInt(q.get("stroke") || "0", 10) || 0 };
}

/** Offers a blob as a download, which is the whole of what "download this take" means. */
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
