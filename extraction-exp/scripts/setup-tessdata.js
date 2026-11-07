// Unpack the bundled English OCR model so no network download is needed at runtime.
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const src = path.resolve('node_modules/@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz');
const dst = path.resolve('tessdata/eng.traineddata');
if (fs.existsSync(dst)) process.exit(0);
if (!fs.existsSync(src)) { console.warn('tessdata source missing; run npm install'); process.exit(0); }
fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.writeFileSync(dst, zlib.gunzipSync(fs.readFileSync(src)));
console.log('tessdata ready');
