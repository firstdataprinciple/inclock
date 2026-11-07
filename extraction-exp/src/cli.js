// Usage: node src/cli.js file.pdf [out.json]
import fs from 'node:fs';
import { extract } from './pipeline.js';
const [file, out] = process.argv.slice(2);
if (!file) { console.error('usage: node src/cli.js file.pdf [out.json]'); process.exit(1); }
const r = await extract(file, fs.readFileSync(file), (p, m) => console.error(`${Math.round(p * 100)}% ${m}`));
if (out) fs.writeFileSync(out, JSON.stringify(r, null, 2)); else console.log(r.text);
for (const p of r.pages) console.error(`page ${p.pageNum}:`, JSON.stringify(p.stats));
