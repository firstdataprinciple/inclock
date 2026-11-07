const $ = (s) => document.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const COLORS = { native: 'var(--native)', ocr: 'var(--ocr)', recovered: 'var(--recovered)', pymupdf: 'var(--pymupdf)' };
const LABEL = { native: 'native', ocr: 'OCR', recovered: 'recovered', pymupdf: 'PyMuPDF fill' };

let data = null, jobId = null, boxes = new Map(); // item id -> {el, item, page}
let hits = [], cur = -1;

// ---- upload ---------------------------------------------------------------
$('#file').addEventListener('change', (e) => e.target.files[0] && run(e.target.files[0]));
const viewer = $('#viewer');
viewer.addEventListener('dragover', (e) => e.preventDefault());
viewer.addEventListener('drop', (e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) run(f); });

async function run(file) {
  const fd = new FormData(); fd.append('pdf', file);
  $('#prog').style.display = 'block';
  const r = await fetch('/api/extract', { method: 'POST', body: fd });
  const { id, error } = await r.json();
  if (error) return fail(error);
  jobId = id;
  for (;;) {
    const j = await (await fetch('/api/job/' + id)).json();
    $('#prog i').style.width = Math.round(j.progress * 100) + '%';
    $('#msg').textContent = j.message || '';
    if (j.status === 'error') return fail(j.message);
    if (j.status === 'done') { data = j.result; break; }
    await new Promise((r) => setTimeout(r, 700));
  }
  $('#prog').style.display = 'none';
  $('#msg').textContent = `Done in ${(data.elapsedMs / 1000).toFixed(1)}s` + (data.warnings?.length ? ' — ⚠ ' + data.warnings.join(' ') : '');
  await render();
}
function fail(m) { $('#msg').textContent = 'Error: ' + m; $('#prog').style.display = 'none'; }

// ---- viewer ---------------------------------------------------------------
async function render() {
  viewer.innerHTML = ''; boxes = new Map();
  const scale = Math.min(1.6, Math.max(0.8, (viewer.clientWidth - 48) / data.pages[0].width));
  for (const pg of data.pages) {
    const wrap = el('div', 'page'); wrap.id = 'pg' + pg.pageNum;
    wrap.style.width = pg.width * scale + 'px'; wrap.style.height = pg.height * scale + 'px';
    wrap.append(el('div', 'pnum', 'Page ' + pg.pageNum));
    const img = el('img'); img.loading = 'lazy'; img.alt = 'Page ' + pg.pageNum;
    img.style.cssText = 'display:block;width:100%;height:100%';
    img.src = `/api/page/${jobId}/${pg.pageNum}.png?scale=${(scale * (window.devicePixelRatio || 1)).toFixed(2)}`;
    wrap.append(img);
    const ov = el('div', 'ov'); wrap.append(ov);
    const k = scale; // viewer px per PDF point
    for (const r of pg.imageRegions) {
      const d = el('div', 'imgreg'); Object.assign(d.style, { left: r.x * k + 'px', top: r.y * k + 'px', width: r.w * k + 'px', height: r.h * k + 'px' });
      ov.append(d);
    }
    for (const it of pg.items) {
      const b = el('div', 'box ' + it.source + (it.review ? ' review' : ''));
      Object.assign(b.style, { left: it.x * k - 1 + 'px', top: it.y * k - 1 + 'px', width: it.w * k + 2 + 'px', height: it.h * k + 2 + 'px' });
      b.dataset.id = it.id;
      b.addEventListener('mouseenter', (e) => tip(e, it));
      b.addEventListener('mousemove', (e) => tip(e, it));
      b.addEventListener('mouseleave', () => ($('#tip').style.display = 'none'));
      b.addEventListener('click', () => { focusItem(it.id, false); });
      ov.append(b); boxes.set(it.id, { el: b, item: it, page: pg.pageNum });
    }
    viewer.append(wrap);
  }
  buildSide(); $('#q').disabled = false; $('#prev').disabled = false; $('#next').disabled = false;
}

function tip(e, it) {
  const t = $('#tip');
  let h = `<b>${esc(it.text)}</b><br>${LABEL[it.source]}${it.conf != null ? ` · conf ${(it.conf * 100).toFixed(0)}%` : ''}`;
  if (it.alts?.length) h += `<br>other readings: ${it.alts.map((a) => esc(a.text)).join(', ')}`;
  if (it.confirmed) h += '<br>✓ two OCR engines agree';
  if (it.review) h += '<br>⚠ needs review';
  t.innerHTML = h; t.style.display = 'block'; t.style.left = e.clientX + 12 + 'px'; t.style.top = e.clientY + 14 + 'px';
}

function focusItem(id, scroll = true) {
  document.querySelectorAll('.box.cur').forEach((b) => b.classList.remove('cur'));
  const b = boxes.get(id); if (!b) return;
  b.el.classList.add('cur');
  if (scroll) b.el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  document.querySelectorAll('.row.cur').forEach((r) => r.classList.remove('cur'));
  const row = document.querySelector(`.row[data-id="${id}"]`);
  if (row) { row.style.background = 'rgba(255,212,0,.35)'; row.scrollIntoView({ block: 'nearest' }); setTimeout(() => (row.style.background = ''), 1200); }
}

// ---- side panel -------------------------------------------------------------
document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('.tabs button').forEach((x) => x.classList.toggle('on', x === b));
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('on', t.id === 't-' + b.dataset.tab));
}));

function buildSide() {
  // Words list
  const w = $('#t-words'); w.innerHTML = '';
  for (const pg of data.pages) {
    w.append(el('div', '', `<b>Page ${pg.pageNum}</b> <small style="color:var(--muted)">${pg.items.length} words</small>`));
    for (const it of pg.items) {
      const r = el('div', 'row'); r.dataset.id = it.id;
      r.innerHTML = `<span class="chip" style="background:${COLORS[it.source]}">${LABEL[it.source]}</span><span>${esc(it.text)}</span>` +
        (it.review ? '<span title="needs review">⚠</span>' : '') +
        `<small>${it.conf != null ? (it.conf * 100).toFixed(0) + '%' : ''}</small>`;
      r.addEventListener('click', () => focusItem(it.id));
      w.append(r);
    }
  }
  // Coverage
  const tot = data.pages.reduce((a, p) => { for (const k of Object.keys(p.stats)) a[k] = (a[k] || 0) + p.stats[k]; return a; }, {});
  const c = $('#t-cov');
  c.innerHTML = `<div class="kpi">
    <div><b>${tot.total}</b>words extracted</div>
    <div><b>${tot.recoveredAdded + tot.crossCheckAdded}</b>added by recovery passes</div>
    <div><b>${tot.flaggedForReview}</b>flagged for review</div>
    <div><b>${data.pages.reduce((a, p) => a + p.imageRegions.length, 0)}</b>image regions</div></div>
    <p style="color:var(--muted)">Passes: LiteParse (native + Tesseract OCR) → PyMuPDF cross-check → 300-DPI RapidOCR recovery on pages and image crops → second look at weak words. Dashed purple boxes were only found by recovery. Orange-ringed boxes are low-confidence or have competing readings — hover to see alternatives.</p>
    <table><tr><th>Page</th><th>Words</th><th>+PyMuPDF</th><th>+Recovered</th><th>Review</th></tr>
    ${data.pages.map((p) => `<tr><td><a href="#pg${p.pageNum}">${p.pageNum}</a></td><td>${p.stats.total}</td><td>${p.stats.crossCheckAdded}</td><td>${p.stats.recoveredAdded}</td><td>${p.stats.flaggedForReview}</td></tr>`).join('')}</table>
    <h4>Image regions (dotted boxes)</h4>
    <table><tr><th>Page</th><th>Size</th><th>Words found</th></tr>
    ${data.pages.flatMap((p) => p.imageRegions.map((r) => `<tr><td>${p.pageNum}</td><td>${Math.round(r.w)}×${Math.round(r.h)}pt</td><td>${r.words === 0 ? '<b style="color:var(--review)">0 — check visually</b>' : r.words}</td></tr>`)).join('') || '<tr><td colspan=3>none</td></tr>'}</table>`;
  // Full text
  const t = $('#t-text'); t.innerHTML = '';
  const bar = el('div', '', '<button id="copy">Copy</button> <button id="dl">Download .txt</button> <button id="dlj">Download .json</button>');
  bar.style.marginBottom = '10px'; t.append(bar);
  const pre = el('pre'); pre.textContent = data.text; t.append(pre);
  $('#copy').onclick = () => navigator.clipboard.writeText(data.text);
  const save = (name, body, type) => { const a = el('a'); a.href = URL.createObjectURL(new Blob([body], { type })); a.download = name; a.click(); };
  $('#dl').onclick = () => save('extracted.txt', data.text, 'text/plain');
  $('#dlj').onclick = () => save('extracted.json', JSON.stringify(data, null, 2), 'application/json');
}

// ---- layers + search --------------------------------------------------------
document.querySelectorAll('[data-layer]').forEach((cb) => cb.addEventListener('change', () => viewer.classList.toggle('hide-' + cb.dataset.layer, !cb.checked)));
$('#onlyReview').addEventListener('change', (e) => viewer.classList.toggle('only-review', e.target.checked));

$('#q').addEventListener('input', () => {
  boxes.forEach((b) => b.el.classList.remove('hit', 'cur'));
  const q = $('#q').value.trim().toLowerCase(); hits = []; cur = -1;
  if (q) boxes.forEach((b, id) => {
    const alts = (b.item.alts || []).map((a) => a.text.toLowerCase());
    if (b.item.text.toLowerCase().includes(q) || alts.some((a) => a.includes(q))) { b.el.classList.add('hit'); hits.push(id); }
  });
  $('#hits').textContent = q ? `${hits.length} match${hits.length === 1 ? '' : 'es'}` : '';
  if (hits.length) step(1);
});
function step(d) { if (!hits.length) return; cur = (cur + d + hits.length) % hits.length; focusItem(hits[cur]); $('#hits').textContent = `${cur + 1}/${hits.length}`; }
$('#next').onclick = () => step(1); $('#prev').onclick = () => step(-1);
$('#q').addEventListener('keydown', (e) => { if (e.key === 'Enter') step(e.shiftKey ? -1 : 1); });
