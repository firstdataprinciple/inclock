# extraction-exp

Lossless PDF text extraction with a visual highlight viewer. Built for PDFs whose
statistics and bar charts exist **only as images**.

## Run

```bash
npm install        # also unpacks the bundled OCR model (works offline)
npm start          # http://localhost:3000
npm test           # regression: every known word in test/sample.pdf must be found
node src/cli.js file.pdf out.json   # headless extraction
```

## How nothing gets lost

| Pass | What it does |
|------|--------------|
| 1. LiteParse | Native PDF text + built-in OCR, with exact word boxes |
| 2. pdf.js cross-check | Independent native extractor; any word LiteParse lacks is added (`pdf.js fill`) |
| 3. Recovery OCR | 300-DPI render of every page **and** every embedded image (2x upscaled, normal + inverted); uncovered words are added (`recovered`) |
| 4. Second look | Each low-confidence OCR word is re-read from a tight 3x crop (plain / thresholded / inverted); competing readings are kept as alternates |

Every word carries its source and confidence. Weak or contested words get an orange
ring (**needs review**); hover to see alternate readings. The *Coverage* tab lists
each image region with how many words were found in it (0 = check visually).

## Viewer

- Click a box ⇄ list row, search across all pages (Enter / Shift+Enter to step)
- Toggle layers (native / OCR / recovered / pdf.js fill) or show only needs-review
- Export full text (.txt) or complete word/box data (.json)

## Known limits (honest)

OCR is probabilistic: tiny, stylised or rotated chart labels can still be misread, so
review-flagged words exist. Numbers encoded purely as bar *heights* (no label) are not
text and cannot be extracted by OCR. A vision-model pass over chart regions is the
natural next step for those.
