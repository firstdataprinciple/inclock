# extraction-exp

Lossless PDF text extraction (Python backend) with a visual highlight viewer. Built for
PDFs whose statistics and bar charts exist **only as images**.

## Run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --port 3000      # open http://localhost:3000
pytest -q                               # regression: every known word in tests/sample.pdf is found
python -m app.cli file.pdf out.json     # headless extraction (prints text if no out file)
```

First run: LiteParse downloads its Tesseract English data once (or set `TESSDATA_PATH` to a
folder containing `eng.traineddata`). If that download is blocked, the app still works — it
warns in the UI and relies on the RapidOCR passes below, whose models ship inside the wheel.

## How nothing gets lost

| Pass | Engine | What it does |
|------|--------|--------------|
| 1 | LiteParse | Native PDF text + built-in Tesseract OCR, with exact word boxes |
| 2 | PyMuPDF | Independent native extractor; any word LiteParse lacks is added (`PyMuPDF fill`) |
| 3 | RapidOCR | Second OCR engine on a 300-DPI render of every page **and** every embedded image (2x upscaled, normal + inverted); uncovered words are added (`recovered`) |
| 4 | RapidOCR | Second look: each weak word is re-read from a tight 3x crop |

Where Tesseract and RapidOCR agree a word is marked ✓ *confirmed*. Where they disagree both
readings are kept (hover to see alternates) and the word gets an orange **needs review** ring.
The *Coverage* tab lists each image region with how many words were found in it (0 = look at it).

## Layout

```
app/pipeline.py   the four passes + merge          app/server.py   FastAPI (upload, jobs, page PNGs)
app/cli.py        headless runner                  static/         viewer (plain HTML/JS, no build step)
tests/            sample PDF + regression test
```

## Known limits

OCR is probabilistic: tiny, stylised or rotated chart labels can still be misread, hence the
review flags. Values encoded only as bar *heights* (no printed label) are not text and cannot
be extracted by OCR; a vision-model pass over chart regions is the natural next step for those.
