# Working on Stroke Corpus

These instructions apply throughout this repository.

## Preserve the evidence and the public contract

- Treat `traces/*.json` as original evidence. Do not hand-correct, normalize or
  rewrite recordings. See [CONTRIBUTING.md](CONTRIBUTING.md) for new contributions.
- Read [FORMAT.md](FORMAT.md) before changing a reader. Preserve source columns,
  values, list membership and order. Missing channels are unmeasured, not zero.
  `corpus.js` currently zero-fills absent slots for display; do not copy that
  legacy behavior into analysis or exports.
- Respect the documented clock limitations and overlapping reading lists.
  Do not treat format-based quality tags as validation of every measurement.
- Call them **recordings** in prose. Preserve the published format identifier
  `stroke-field-guide/take` and the recorder's original `id`.
- Use the manifest's `file` as the lookup key, including its `.json` extension.
  Preserve published filenames, URLs and compatibility behavior deliberately.

## Build and generated files

- `manifest.json` is generated from the trace folder by `tools/manifest.py`.
  Change the generator, not the generated manifest; do not hand-list recordings.
- From the repository root, run `python tools/manifest.py` with Python 3 after
  trace or manifest-generator changes. It also runs the asset stamper.
- After editing `corpus.js` or `corpus.css`, run `python tools/stamp.py` (or the
  full build). It updates content-hash query strings in the HTML asset references.
  Do not type hashes by hand. Include regenerated files with the source changes.
- Run the relevant build again and verify it makes no further changes. Inspect
  `git diff` and `git status` so new files and unrelated edits are not overlooked.
- HTML content is maintained directly; tables render in the browser. Keep the
  permanent data/documentation links available without JavaScript. Do not add
  HTML pre-rendering or generate, commit or deploy per-recording CSV files.
  An optional user-requested CSV download is a separate convenience feature.

## Preview and check

- Run `python -m http.server 8000 --bind 127.0.0.1` from the repository root and
  open `http://127.0.0.1:8000/`. Use HTTP rather than opening HTML as a local file.
- For site changes, check the catalogue/filtering, quality page, and a recording
  and stroke reached through the catalogue. Check discovery links with JavaScript
  disabled or data loading failed. Use relative links that also work beneath
  the published `/StrokeCorpus/` path.
- Run `git diff --check`. Apply checks appropriate to the change; this guidance
  does not replace automated validation or generated-output checks in CI.

## Documentation

Use plain, concrete language and distinguish measured device behavior from
universal format rules. Keep `llms.txt` a short entry point into FORMAT.md and the
manifest; avoid copied corpus counts or duplicated technical documentation.
