// Multi-pass, no-word-left-behind extraction pipeline.
//
//   Pass 1  LiteParse            native PDF text + built-in OCR for images
//   Pass 2  pdf.js cross-check   independent native extractor; any word LiteParse
//                                 lacks is added back ("pdfjs" source)
//   Pass 3  Recovery OCR         300-DPI render of every page and every embedded
//                                 image (upscaled, normal + inverted); words not
//                                 already covered are added ("recovered" source),
//                                 and differing readings of weak OCR words are kept
//                                 as alternates so a human can pick the right one.
//
// All coordinates are PDF points, top-left origin (same as LiteParse).

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LiteParse } from '@llamaindex/liteparse';
import { createWorker, PSM } from 'tesseract.js';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TESSDATA = path.join(ROOT, 'tessdata');
const RENDER_DPI = 300;
const LOW_CONF = 0.8; // below this an OCR word is flagged "review"

const norm = (s) => s.normalize('NFKC').replace(/\s+/g, '');
const area = (b) => Math.max(0, b.w) * Math.max(0, b.h);
function inter(a, b) {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}
// fraction of `a` that lies inside `b`
const covered = (a, b) => (area(a) ? inter(a, b) / area(a) : 0);

/** Split LiteParse text items into word-level items (uses word boxes when present). */
function itemsToWords(page) {
  const out = [];
  for (const it of page.textItems) {
    const source = it.confidence != null ? 'ocr' : 'native';
    const conf = it.confidence ?? null;
    if (it.words && it.words.length) {
      for (const w of it.words) {
        if (norm(w.text)) out.push({ text: w.text, x: w.x, y: w.y, w: w.width, h: w.height, source, conf });
      }
    } else if (/\s/.test(it.text.trim())) {
      // no word boxes: split proportionally by character count
      const parts = it.text.split(/(\s+)/);
      const total = it.text.length || 1;
      let off = 0;
      for (const p of parts) {
        if (p.trim()) {
          out.push({
            text: p, x: it.x + (it.width * off) / total, y: it.y,
            w: (it.width * p.length) / total, h: it.height, source, conf,
          });
        }
        off += p.length;
      }
    } else if (norm(it.text)) {
      out.push({ text: it.text.trim(), x: it.x, y: it.y, w: it.width, h: it.height, source, conf });
    }
  }
  return out;
}

/** Pass 2: independent native-text extraction via pdf.js. */
async function pdfjsWords(buf) {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const doc = await pdfjs.getDocument({ data: new Uint8Array(buf), useSystemFonts: true, verbosity: 0 }).promise;
  const pages = [];
  for (let n = 1; n <= doc.numPages; n++) {
    const page = await doc.getPage(n);
    const vp = page.getViewport({ scale: 1 });
    const tc = await page.getTextContent();
    const words = [];
    for (const it of tc.items) {
      if (!it.str || !norm(it.str)) continue;
      const [, , , d, e, f] = it.transform;
      const h = it.height || Math.abs(d) || 8;
      const box = { x: e, y: vp.height - f - h, w: it.width, h };
      const parts = it.str.split(/(\s+)/);
      const total = it.str.length || 1;
      let off = 0;
      for (const p of parts) {
        if (p.trim()) {
          words.push({ text: p, x: box.x + (box.w * off) / total, y: box.y, w: (box.w * p.length) / total, h: box.h });
        }
        off += p.length;
      }
    }
    pages.push({ pageNum: n, words });
  }
  await doc.destroy();
  return pages;
}

/** Run Tesseract on a PNG buffer; return words in pixel space with confidence 0..1. */
async function ocrBuffer(worker, buf) {
  const { data } = await worker.recognize(buf, {}, { blocks: true });
  const words = [];
  for (const b of data.blocks || [])
    for (const p of b.paragraphs || [])
      for (const l of p.lines || [])
        for (const w of l.words || []) {
          if (!norm(w.text)) continue;
          words.push({
            text: w.text.trim(),
            x0: w.bbox.x0, y0: w.bbox.y0, x1: w.bbox.x1, y1: w.bbox.y1,
            conf: Math.max(0, Math.min(1, w.confidence / 100)),
          });
        }
  return words;
}

/** Pass 3: recovery OCR over full pages and embedded-image crops. */
async function recoveryWords(worker, shot, pageW, pageH, imgBoxes) {
  const pxPerPt = shot.width / pageW;
  const found = [];
  const regions = [{ x: 0, y: 0, w: pageW, h: pageH, scale: 1, full: true }];
  for (const b of imgBoxes) {
    if (b.w > 20 && b.h > 20) regions.push({ ...b, scale: 2, full: false });
  }
  for (const r of regions) {
    const left = Math.max(0, Math.floor(r.x * pxPerPt));
    const top = Math.max(0, Math.floor(r.y * pxPerPt));
    const width = Math.min(shot.width - left, Math.ceil(r.w * pxPerPt));
    const height = Math.min(shot.height - top, Math.ceil(r.h * pxPerPt));
    if (width < 8 || height < 8) continue;
    // Variants: normal, and inverted (catches light text on dark bars/backgrounds)
    for (const invert of [false, true]) {
      let img = sharp(shot.imageBuffer).extract({ left, top, width, height }).flatten({ background: '#ffffff' }).grayscale();
      if (r.scale !== 1) img = img.resize({ width: Math.round(width * r.scale), kernel: 'lanczos3' });
      img = img.normalise();
      if (invert) img = img.negate();
      const png = await img.png().toBuffer();
      const words = await ocrBuffer(worker, png);
      // map crop pixels -> PDF points
      const k = r.scale * pxPerPt;
      for (const w of words) {
        found.push({
          text: w.text, conf: w.conf, source: 'recovered',
          x: (left + w.x0 / r.scale) / pxPerPt, y: (top + w.y0 / r.scale) / pxPerPt,
          w: (w.x1 - w.x0) / k, h: (w.y1 - w.y0) / k,
        });
      }
    }
  }
  return found;
}


/** Second look: re-read one weak word from a tight, upscaled crop in single-word mode. */
async function secondLook(worker, shot, pageW, it) {
  const pxPerPt = shot.width / pageW;
  const pad = Math.max(3, it.h * 0.25);
  const left = Math.max(0, Math.floor((it.x - pad) * pxPerPt));
  const top = Math.max(0, Math.floor((it.y - pad) * pxPerPt));
  const width = Math.min(shot.width - left, Math.ceil((it.w + 2 * pad) * pxPerPt));
  const height = Math.min(shot.height - top, Math.ceil((it.h + 2 * pad) * pxPerPt));
  if (width < 4 || height < 4) return [];
  const out = [];
  await worker.setParameters({ tessedit_pageseg_mode: PSM.SINGLE_WORD });
  for (const variant of ['plain', 'threshold', 'invert']) {
    let img = sharp(shot.imageBuffer).extract({ left, top, width, height }).flatten({ background: '#ffffff' }).grayscale()
      .resize({ height: Math.max(120, height * 3), kernel: 'lanczos3' }).normalise();
    if (variant === 'threshold') img = img.threshold(150);
    if (variant === 'invert') img = img.negate();
    const png = await img.extend({ top: 20, bottom: 20, left: 20, right: 20, background: variant === 'invert' ? '#000' : '#fff' }).png().toBuffer();
    for (const w of await ocrBuffer(worker, png)) out.push({ text: w.text, conf: w.conf });
  }
  await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
  return out;
}

/** Keep the highest-confidence word per location among recovery candidates. */
function dedupe(words) {
  const sorted = [...words].sort((a, b) => b.conf - a.conf);
  const kept = [];
  for (const w of sorted) {
    const dup = kept.find((k) => covered(w, k) > 0.5 || covered(k, w) > 0.5);
    if (dup) {
      if (norm(dup.text) !== norm(w.text)) (dup.alts ||= []).push({ text: w.text, conf: w.conf });
    } else kept.push({ ...w });
  }
  return kept;
}

function groupLines(words) {
  const sorted = [...words].sort((a, b) => a.y - b.y || a.x - b.x);
  const lines = [];
  for (const w of sorted) {
    const line = lines.find((l) => Math.abs(l.y - w.y) < Math.max(w.h, l.h) * 0.6);
    if (line) line.words.push(w);
    else lines.push({ y: w.y, h: w.h, words: [w] });
  }
  return lines.map((l) => l.words.sort((a, b) => a.x - b.x).map((w) => w.text).join(' '));
}

export async function extract(pdfPath, buf, onProgress = () => {}) {
  const t0 = Date.now();
  // --- Pass 1 -------------------------------------------------------------
  onProgress(0.05, 'LiteParse: native text + OCR');
  const lp = new LiteParse({
    ocrEnabled: true, ocrLanguage: 'eng', tessdataPath: TESSDATA,
    extractImages: true, quiet: true, ocrFailureFatal: false, emitWordBoxes: true,
  });
  const parsed = await lp.parse(pdfPath);

  // --- Pass 2 -------------------------------------------------------------
  onProgress(0.2, 'pdf.js cross-check');
  const pdfjsPages = await pdfjsWords(buf);

  // --- Render for pass 3 ----------------------------------------------------
  onProgress(0.3, `Rendering pages at ${RENDER_DPI} DPI`);
  const hi = new LiteParse({ ocrEnabled: false, dpi: RENDER_DPI, quiet: true });
  const shots = await hi.screenshot(pdfPath);

  const worker = await createWorker('eng', 1, { langPath: TESSDATA, gzip: false, cachePath: TESSDATA });
  await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT, preserve_interword_spaces: '1' });

  const pages = [];
  let id = 0;
  try {
    for (let i = 0; i < parsed.pages.length; i++) {
      const pg = parsed.pages[i];
      onProgress(0.3 + (0.65 * i) / parsed.pages.length, `Page ${pg.pageNum}/${parsed.pages.length}: recovery OCR`);
      const items = itemsToWords(pg);
      const stats = { liteparse: items.length, pdfjsAdded: 0, recoveredAdded: 0, flaggedForReview: 0 };

      // Pass 2 merge: add native words LiteParse missed
      const pool = new Map();
      for (const w of items) pool.set(norm(w.text), (pool.get(norm(w.text)) || 0) + 1);
      const pj = pdfjsPages.find((p) => p.pageNum === pg.pageNum)?.words || [];
      for (const w of pj) {
        const key = norm(w.text);
        if (pool.get(key) > 0) pool.set(key, pool.get(key) - 1);
        else {
          items.push({ ...w, source: 'pdfjs', conf: null });
          stats.pdfjsAdded++;
        }
      }

      // Pass 3
      const imgBoxes = (parsed.images || [])
        .filter((im) => im.page === pg.pageNum)
        .map((im) => ({ x: im.bbox.x, y: im.bbox.y, w: im.bbox.width, h: im.bbox.height }));
      const shot = shots.find((s) => s.pageNum === pg.pageNum);
      if (shot && !shot.isSolidFill) {
        const rec = dedupe(await recoveryWords(worker, shot, pg.width, pg.height, imgBoxes));
        for (const r of rec) {
          if (r.conf < 0.35 || r.text.length < 1) continue; // noise floor
          if (!/[\p{L}\p{N}]/u.test(r.text)) continue; // punctuation-only specks
          const hit = items.find((it) => covered(r, it) > 0.5 || covered(it, r) > 0.5);
          if (!hit) {
            items.push(r);
            stats.recoveredAdded++;
          } else if (hit.source === 'ocr' && norm(hit.text) !== norm(r.text) && r.conf > (hit.conf ?? 0)) {
            // A better reading of an existing OCR word: keep both, prefer the stronger.
            (hit.alts ||= []).push({ text: hit.text, conf: hit.conf });
            hit.prev = hit.prev || hit.text;
            hit.text = r.text;
            hit.conf = r.conf;
            hit.upgraded = true;
          } else if (hit.source === 'ocr' && norm(hit.text) !== norm(r.text)) {
            (hit.alts ||= []).push({ text: r.text, conf: r.conf });
          }
        }
      }

      // Second look at every weak OCR word (this is what rescues e.g. "Q4" read as "Qa").
      if (shot && !shot.isSolidFill) {
        for (const it of items) {
          if (it.source === 'native' || it.source === 'pdfjs' || (it.conf ?? 1) >= LOW_CONF) continue;
          for (const r of await secondLook(worker, shot, pg.width, it)) {
            if (norm(r.text) === norm(it.text)) { it.conf = Math.max(it.conf ?? 0, r.conf); continue; }
            if (r.conf > (it.conf ?? 0) + 0.05) {
              (it.alts ||= []).push({ text: it.text, conf: it.conf });
              it.prev = it.prev || it.text; it.text = r.text; it.conf = r.conf; it.upgraded = true;
            } else if (r.conf > 0.3 && !(it.alts || []).some((a) => norm(a.text) === norm(r.text))) {
              (it.alts ||= []).push({ text: r.text, conf: r.conf });
            }
          }
        }
      }

      for (const it of items) {
        it.id = ++id;
        it.review = it.source !== 'native' && it.source !== 'pdfjs' && ((it.conf ?? 1) < LOW_CONF || !!it.alts);
        if (it.review) stats.flaggedForReview++;
      }
      items.sort((a, b) => a.y - b.y || a.x - b.x);

      const imageRegions = imgBoxes.map((b) => ({
        ...b,
        words: items.filter((it) => it.source !== 'native' && covered(it, b) > 0.5).length,
      }));

      // Text: LiteParse layout text first, then everything it did not contain.
      const extra = items.filter((it) => it.source === 'pdfjs' || it.source === 'recovered');
      let text = pg.text.trimEnd();
      // Reflect better OCR readings in the layout text (first matching whole word).
      for (const it of items.filter((i) => i.upgraded && i.prev)) {
        const esc = it.prev.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        text = text.replace(new RegExp(`(?<![\\p{L}\\p{N}])${esc}(?![\\p{L}\\p{N}])`, 'u'), it.text);
      }
      if (extra.length) {
        text += `\n\n--- Additional text recovered on page ${pg.pageNum} (charts / images / missed) ---\n` + groupLines(extra).join('\n');
      }
      stats.total = items.length;
      pages.push({ pageNum: pg.pageNum, width: pg.width, height: pg.height, items, imageRegions, stats, text });
    }
  } finally {
    await worker.terminate();
  }
  onProgress(1, 'Done');
  return {
    totalPages: parsed.totalPages,
    pages,
    text: pages.map((p) => `===== Page ${p.pageNum} =====\n${p.text}`).join('\n\n'),
    elapsedMs: Date.now() - t0,
  };
}
