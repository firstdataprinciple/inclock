// Regression: every known word in test/sample.pdf (including chart labels that live
// only in an image) must appear in the extraction output.
import fs from 'node:fs';
import { extract } from '../src/pipeline.js';
const f = new URL('./sample.pdf', import.meta.url).pathname;
const r = await extract(f, fs.readFileSync(f));
const got = new Set(r.pages.flatMap((p) => p.items.flatMap((i) => [i.text, ...(i.alts || []).map((a) => a.text)])).map((t) => t.toLowerCase()));
const expected = ['Annual', 'Report:', 'Statistics', 'Overview', 'native', 'extracted.', '25%', 'Quarterly', 'Revenue', '2025', '42M', '58M', '73M', '91M', 'Q1', 'Q2', 'Q3', 'Q4', 'Figure', 'chart'];
const missing = expected.filter((w) => !got.has(w.toLowerCase()));
console.log(missing.length ? `MISSING: ${missing.join(', ')}` : `OK: all ${expected.length} expected words present (${r.pages[0].items.length} extracted)`);
process.exit(missing.length ? 1 : 0);
