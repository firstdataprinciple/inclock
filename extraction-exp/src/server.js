import express from 'express';
import multer from 'multer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { extract } from './pipeline.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'extraction-exp-'));
const upload = multer({ dest: tmp, limits: { fileSize: 200 * 1024 * 1024 } });
const jobs = new Map();

const app = express();
app.use(express.static(path.join(ROOT, 'public')));
app.use('/vendor/pdfjs', express.static(path.join(ROOT, 'node_modules/pdfjs-dist/build')));

app.post('/api/extract', upload.single('pdf'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded (field name "pdf").' });
  const id = crypto.randomUUID();
  const pdfPath = req.file.path + '.pdf';
  fs.renameSync(req.file.path, pdfPath);
  const job = { id, pdfPath, name: req.file.originalname, status: 'running', progress: 0, message: 'Queued' };
  jobs.set(id, job);
  extract(pdfPath, fs.readFileSync(pdfPath), (p, m) => Object.assign(job, { progress: p, message: m }))
    .then((result) => Object.assign(job, { status: 'done', result }))
    .catch((e) => Object.assign(job, { status: 'error', message: String(e?.message || e) }));
  res.json({ id });
});

app.get('/api/job/:id', (req, res) => {
  const j = jobs.get(req.params.id);
  if (!j) return res.status(404).json({ error: 'unknown job' });
  const { result, pdfPath, ...meta } = j;
  res.json(j.status === 'done' ? { ...meta, result } : meta);
});

app.get('/api/pdf/:id', (req, res) => {
  const j = jobs.get(req.params.id);
  if (!j) return res.status(404).end();
  res.type('application/pdf').sendFile(j.pdfPath);
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => console.log(`extraction-exp running at http://localhost:${port}`));
