"""Multi-pass, no-word-left-behind PDF extraction.

  Pass 1  LiteParse      native PDF text + its built-in (Tesseract) OCR, with word boxes
  Pass 2  PyMuPDF        independent native extractor; any word LiteParse lacks is
                         added back (source "pymupdf")
  Pass 3  Recovery OCR   RapidOCR (a second, independent OCR engine) over a 300-DPI
                         render of every page and every embedded image (upscaled,
                         normal + inverted). Uncovered words are added ("recovered");
                         where the two OCR engines disagree both readings are kept.
  Pass 4  Second look    every still-weak word is re-read from a tight, upscaled crop

All coordinates are PDF points, top-left origin (LiteParse's convention).
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Callable

import pymupdf as fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RENDER_DPI = 300
LOW_CONF = {"ocr": 0.8, "recovered": 0.6}  # below this a word is flagged "review"

Progress = Callable[[float, str], None]

_rapid = None


def rapid():
    global _rapid
    if _rapid is None:
        from rapidocr_onnxruntime import RapidOCR

        _rapid = RapidOCR()
    return _rapid


# ---------------------------------------------------------------- geometry
def norm(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def box(x, y, w, h):
    return {"x": float(x), "y": float(y), "w": float(w), "h": float(h)}


def _inter(a, b) -> float:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return w * h if w > 0 and h > 0 else 0.0


def covered(a, b) -> float:
    """Fraction of `a` lying inside `b`."""
    area = max(0.0, a["w"]) * max(0.0, a["h"])
    return _inter(a, b) / area if area else 0.0


def similar_len(a: str, b: str) -> bool:
    """Alternate readings only make sense for words of comparable length (not whole garbled lines)."""
    la, lb = len(norm(a)), len(norm(b))
    return max(la, lb) <= 1.8 * max(min(la, lb), 1) + 1


def overlaps(a, b) -> bool:
    return covered(a, b) > 0.5 or covered(b, a) > 0.5


def split_words(text: str, x, y, w, h):
    """Split a line box into word boxes proportionally by character count."""
    total = max(len(text), 1)
    out, off = [], 0
    for part in re.split(r"(\s+)", text):
        if part.strip():
            out.append((part, box(x + w * off / total, y, w * len(part) / total, h)))
        off += len(part)
    return out


# ------------------------------------------------------------------ pass 1
def liteparse_words(page):
    out = []
    for it in page.text_items:
        source = "ocr" if it.confidence is not None else "native"
        conf = it.confidence
        if it.words:
            for w in it.words:
                if norm(w.text):
                    out.append({"text": w.text, **box(w.x, w.y, w.width, w.height), "source": source, "conf": conf})
        elif re.search(r"\s", it.text.strip()):
            for t, b in split_words(it.text, it.x, it.y, it.width, it.height):
                out.append({"text": t, **b, "source": source, "conf": conf})
        elif norm(it.text):
            out.append({"text": it.text.strip(), **box(it.x, it.y, it.width, it.height), "source": source, "conf": conf})
    return out


def run_liteparse(pdf_path: str, warnings: list[str]):
    from liteparse import LiteParse

    tessdata = os.environ.get("TESSDATA_PATH") or (str(ROOT / "tessdata") if (ROOT / "tessdata").exists() else None)
    common = dict(emit_word_boxes=True, quiet=True)
    try:
        lp = LiteParse(ocr_enabled=True, ocr_language="eng", tessdata_path=tessdata, ocr_failure_fatal=True, **common)
        return lp.parse(pdf_path)
    except Exception as e:  # e.g. language data could not be downloaded
        warnings.append(f"LiteParse OCR unavailable ({str(e)[:140]}); relying on recovery OCR for images.")
        return LiteParse(ocr_enabled=False, **common).parse(pdf_path)


# ------------------------------------------------------------------ pass 2
def pymupdf_page_data(doc: fitz.Document, n: int):
    page = doc[n - 1]
    words = [
        {"text": w[4], **box(w[0], w[1], w[2] - w[0], w[3] - w[1])}
        for w in page.get_text("words")
        if norm(w[4])
    ]
    images = []
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"])
        if r.width > 20 and r.height > 20:
            images.append(box(r.x0, r.y0, r.width, r.height))
    return words, images


def render(doc: fitz.Document, n: int, dpi: int) -> Image.Image:
    pix = doc[n - 1].get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


# ------------------------------------------------------------------ pass 3
def ocr_image(img: Image.Image):
    """RapidOCR -> [(text, conf, x0, y0, x1, y1)] in pixel space (line level)."""
    res, _ = rapid()(np.asarray(img.convert("RGB")))
    out = []
    for pts, text, score in res or []:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if norm(text):
            out.append((text, float(score), min(xs), min(ys), max(xs), max(ys)))
    return out


def recover_words(shot: Image.Image, page_w: float, image_boxes: list[dict]):
    px_per_pt = shot.width / page_w
    regions = [(0.0, 0.0, page_w, shot.height / px_per_pt, 1, False)]
    regions += [(b["x"], b["y"], b["w"], b["h"], 2, True) for b in image_boxes]
    found = []
    for rx, ry, rw, rh, scale, invert_too in regions:
        left, top = max(0, int(rx * px_per_pt)), max(0, int(ry * px_per_pt))
        right, bottom = min(shot.width, int((rx + rw) * px_per_pt) + 1), min(shot.height, int((ry + rh) * px_per_pt) + 1)
        if right - left < 8 or bottom - top < 8:
            continue
        crop = shot.crop((left, top, right, bottom))
        if scale != 1:
            crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
        variants = [crop] + ([ImageOps.invert(ImageOps.autocontrast(crop.convert("L")))] if invert_too else [])
        for variant in variants:
            for text, conf, x0, y0, x1, y1 in ocr_image(variant):
                px = lambda v, o: (o + v / scale) / px_per_pt  # crop px -> PDF pt
                x, y = px(x0, left), px(y0, top)
                w, h = (x1 - x0) / scale / px_per_pt, (y1 - y0) / scale / px_per_pt
                for t, b in split_words(text, x, y, w, h):
                    found.append({"text": t, **b, "conf": conf, "source": "recovered"})
    return found


def dedupe(words):
    kept = []
    for w in sorted(words, key=lambda w: -w["conf"]):
        dup = next((k for k in kept if overlaps(w, k)), None)
        if dup is None:
            kept.append(dict(w))
        elif norm(dup["text"]) != norm(w["text"]) and similar_len(dup["text"], w["text"]):
            dup.setdefault("alts", []).append({"text": w["text"], "conf": w["conf"]})
    return kept


# ------------------------------------------------------------------ pass 4
def second_look(shot: Image.Image, page_w: float, it: dict):
    px_per_pt = shot.width / page_w
    pad = max(3.0, it["h"] * 0.35)
    left, top = max(0, int((it["x"] - pad) * px_per_pt)), max(0, int((it["y"] - pad) * px_per_pt))
    right = min(shot.width, int((it["x"] + it["w"] + pad) * px_per_pt))
    bottom = min(shot.height, int((it["y"] + it["h"] + pad) * px_per_pt))
    if right - left < 4 or bottom - top < 4:
        return []
    crop = shot.crop((left, top, right, bottom))
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    out = []
    for variant in (crop, ImageOps.invert(ImageOps.autocontrast(crop.convert("L")))):
        padded = ImageOps.expand(variant, border=40, fill=variant.getpixel((0, 0)))  # pad with background colour
        for text, conf, *_ in ocr_image(padded):
            out.append({"text": text.strip(), "conf": conf})
    return out


def group_lines(words):
    lines = []
    for w in sorted(words, key=lambda w: (w["y"], w["x"])):
        line = next((l for l in lines if abs(l["y"] - w["y"]) < max(w["h"], l["h"]) * 0.6), None)
        if line:
            line["words"].append(w)
        else:
            lines.append({"y": w["y"], "h": w["h"], "words": [w]})
    return [" ".join(x["text"] for x in sorted(l["words"], key=lambda w: w["x"])) for l in lines]


def _consider(it: dict, text: str, conf: float, engine: str = "rapid"):
    """Fold another reading of the same word into `it`.

    `confirmed` means two *different* OCR engines (Tesseract via LiteParse, RapidOCR)
    produced the same text; repeated passes of one engine do not count.
    """
    if not similar_len(text, it["text"]):
        return  # a neighbouring word / garbled line, not a reading of this word
    engines = it.setdefault("engines", {"tess" if it["source"] == "ocr" else "rapid"})
    if norm(text) == norm(it["text"]):
        it["conf"] = max(it.get("conf") or 0.0, conf)
        engines.add(engine)
        it["confirmed"] = len(engines) >= 2
        return
    it["confirmed"] = False
    if conf > (it.get("conf") or 0.0):
        it.setdefault("alts", []).append({"text": it["text"], "conf": it.get("conf")})
        it.setdefault("prev", it["text"])
        it["text"], it["conf"], it["upgraded"] = text, conf, True
        it["engines"] = {engine}
    elif not any(norm(a["text"]) == norm(text) for a in it.get("alts", [])):
        it.setdefault("alts", []).append({"text": text, "conf": conf})


# -------------------------------------------------------------------- main
def extract(pdf_path: str, on_progress: Progress = lambda p, m: None) -> dict:
    t0 = time.time()
    warnings: list[str] = []
    on_progress(0.03, "LiteParse: native text + OCR")
    parsed = run_liteparse(pdf_path, warnings)
    doc = fitz.open(pdf_path)

    pages, next_id = [], 0
    n_pages = len(parsed.pages)
    for i, pg in enumerate(parsed.pages):
        base = 0.1 + 0.88 * i / max(n_pages, 1)
        on_progress(base, f"Page {pg.page_num}/{n_pages}: cross-check")
        items = liteparse_words(pg)
        stats = {"liteparse": len(items), "crossCheckAdded": 0, "recoveredAdded": 0, "flaggedForReview": 0}

        # Pass 2 — add native words LiteParse missed (multiset difference)
        pool: dict[str, int] = {}
        for w in items:
            pool[norm(w["text"])] = pool.get(norm(w["text"]), 0) + 1
        mu_words, image_boxes = pymupdf_page_data(doc, pg.page_num)
        for w in mu_words:
            k = norm(w["text"])
            if pool.get(k, 0) > 0:
                pool[k] -= 1
            else:
                items.append({**w, "source": "pymupdf", "conf": None})
                stats["crossCheckAdded"] += 1

        # Pass 3 — recovery OCR
        on_progress(base + 0.3 * 0.88 / max(n_pages, 1), f"Page {pg.page_num}/{n_pages}: recovery OCR")
        shot = render(doc, pg.page_num, RENDER_DPI)
        for r in dedupe(recover_words(shot, pg.width, image_boxes)):
            if r["conf"] < 0.35 or not re.search(r"[\w]", r["text"]):
                continue  # noise floor / punctuation specks
            hit = next((it for it in items if overlaps(r, it)), None)
            if hit is None:
                items.append(r)
                stats["recoveredAdded"] += 1
            elif hit["source"] in ("ocr", "recovered"):
                _consider(hit, r["text"], r["conf"])
                for a in r.get("alts", []):
                    _consider(hit, a["text"], a["conf"])

        # Pass 4 — second look at weak words
        for it in items:
            if it["source"] not in ("ocr", "recovered") or it.get("confirmed"):
                continue
            if (it.get("conf") or 0) >= LOW_CONF[it["source"]] and not it.get("alts"):
                continue
            for r in second_look(shot, pg.width, it):
                _consider(it, r["text"], r["conf"])

        for it in items:
            it.pop("engines", None)
            next_id += 1
            it["id"] = next_id
            thr = LOW_CONF.get(it["source"])
            it["review"] = bool(
                thr is not None and not it.get("confirmed") and ((it.get("conf") or 1.0) < thr or it.get("alts"))
            )
            stats["flaggedForReview"] += it["review"]
        items.sort(key=lambda it: (it["y"], it["x"]))

        regions = [
            {**b, "words": sum(1 for it in items if it["source"] != "native" and covered(it, b) > 0.5)}
            for b in image_boxes
        ]

        text = pg.text.rstrip()
        for it in (x for x in items if x.get("upgraded") and x.get("prev")):  # reflect better readings
            pat = r"(?<![\w])" + re.escape(it["prev"]) + r"(?![\w])"
            text = re.sub(pat, lambda _m, t=it["text"]: t, text, count=1)
        extra = [x for x in items if x["source"] in ("pymupdf", "recovered")]
        if extra:
            text += f"\n\n--- Additional text recovered on page {pg.page_num} (charts / images / missed) ---\n"
            text += "\n".join(group_lines(extra))
        stats["total"] = len(items)
        pages.append(
            {"pageNum": pg.page_num, "width": pg.width, "height": pg.height, "items": items,
             "imageRegions": regions, "stats": stats, "text": text}
        )
    doc.close()
    on_progress(1.0, "Done")
    return {
        "totalPages": parsed.total_pages,
        "pages": pages,
        "text": "\n\n".join(f"===== Page {p['pageNum']} =====\n{p['text']}" for p in pages),
        "warnings": warnings,
        "elapsedMs": int((time.time() - t0) * 1000),
    }
