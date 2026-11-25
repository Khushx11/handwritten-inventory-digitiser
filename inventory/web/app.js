const $ = id => document.getElementById(id);
const node = (tag, text = '') => Object.assign(document.createElement(tag), {textContent: text});
let encoded, previewUrl, current, selected, points = [];

async function api(path, options) {
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error);
  return value;
}
const post = (path, value) => api(path, {
  method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(value),
});

async function loadImage(file) {
  if (file.size > 10_000_000) throw new Error('Choose an image under 10 MB.');
  const reader = new FileReader();
  encoded = await new Promise((resolve, reject) => {
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () => reject(new Error('Unable to read the image.'));
    reader.readAsDataURL(file);
  });
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  $('input-preview').src = previewUrl;
  $('perspective').hidden = false;
  $('corners').value = '';
  points = [];
}
$('file').addEventListener('change', async () => {
  encoded = undefined;
  try {
    if ($('file').files[0]) await loadImage($('file').files[0]);
    $('status').textContent = '';
  } catch (error) {
    $('status').textContent = error.message;
  }
});
$('input-preview').addEventListener('click', event => {
  const preview = $('input-preview');
  const rectangle = preview.getBoundingClientRect();
  if (points.length === 4) points = [];
  points.push([
    Math.min(preview.naturalWidth-1, Math.round((event.clientX-rectangle.left)*preview.naturalWidth/rectangle.width)),
    Math.min(preview.naturalHeight-1, Math.round((event.clientY-rectangle.top)*preview.naturalHeight/rectangle.height)),
  ]);
  $('corners').value = JSON.stringify(points);
  $('status').textContent = `${points.length} of 4 corners marked.`;
});
$('upload').addEventListener('submit', event => {
  event.preventDefault();
  processImage();
});
$('example').addEventListener('click', async () => {
  $('example').disabled = true;
  try {
    const response = await fetch('/api/example/' + encodeURIComponent($('example-condition').value));
    if (!response.ok) throw new Error('Unable to load the example.');
    $('file').value = '';
    $('rotation').value = '0';
    await loadImage(await response.blob());
    await processImage();
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    $('example').disabled = false;
  }
});
async function processImage() {
  if (!encoded) {
    $('status').textContent = 'Choose an image or load the labelled example.';
    return;
  }
  $('process').disabled = true;
  $('status').textContent = 'Reading the sheet…';
  try {
    const corners = $('corners').value ? JSON.parse($('corners').value) : null;
    current = await post('/api/sheets', {
      image: encoded, rotation: Number($('rotation').value), strategy: $('strategy').value, corners,
    });
    selected = null;
    localStorage.setItem('stocktake-sheet', current.sheet);
    display();
    $('status').textContent = 'Extraction complete. Select a row to inspect its source.';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    $('process').disabled = false;
  }
}

const base = () => `/api/sheets/${current.sheet}`;
function display() {
  const {report, reconciliation} = current;
  $('workspace').hidden = false;
  const warnings = report.scan_quality?.warnings ?? [];
  $('scan-warnings').replaceChildren(...warnings.map(warning => node('li', warning)));
  $('scan-warnings').hidden = !warnings.length;
  const source = base() + '/image';
  if ($('sheet').getAttribute('src') !== source) $('sheet').src = source;
  $('original').href = base() + '/original';
  $('download-json').href = base() + '/json';
  $('download-csv').href = base() + '/csv';
  const {unresolved, approved_sum, stated_total, difference, excluded} = reconciliation;
  const sum = stated_total === null ? 'Printed total unconfirmed' : `${reconciliation.total_source === 'reviewed' ? 'Confirmed' : 'OCR'} total ${stated_total}`;
  $('total').value = report.verified_total ?? report.total.raw;
  const diff = difference === null ? '' : ` · Difference ${difference}`;
  $('stats').textContent = `${unresolved} unresolved · ${excluded} excluded · Approved sum ${approved_sum} · ${sum}${diff} · Export: ${current.export_status}`;
  $('history').replaceChildren(...report.history.map(event => {
    if (event.action === 'confirm-total') {
      return node('li', `Printed total confirmed as ${event.after} · ${event.time}`);
    }
    const value = event.after?.exclusion_reason ?? (event.after ? `${event.after.sku}, ${event.after.quantity}` : 'unresolved');
    return node('li', `Row ${event.row} · ${event.action} · ${value} · ${event.time}`);
  }));
  renderRows();
  inspect();
}
function renderRows() {
  const rows = current.report.rows.filter(row => !$('flagged').checked || (row.flags.length && !row.verified && !row.exclusion_reason));
  $('rows').replaceChildren(...rows.map(row => {
    const button = node('button');
    button.className = 'row-button';
    button.setAttribute('aria-pressed', row.id === selected);
    const value = row.verified || {sku: row.sku.raw || '—', quantity: row.count.raw || row.count.state};
    button.append(node('strong', `Row ${row.id} · ${value.sku}`));
    const state = node('span', `${value.quantity} · ${row.verified ? 'Approved' : row.exclusion_reason ? 'Excluded' : row.flags.join(', ') || 'Needs approval'}`);
    state.className = row.flags.length && !row.verified ? 'state flag' : 'state';
    button.append(state);
    button.addEventListener('click', () => {
      selected = row.id;
      for (const peer of $('rows').children) peer.setAttribute('aria-pressed', peer === button);
      $('review-status').textContent = '';
      inspect();
    });
    return button;
  }));
}
function drawSources(row) {
  const source = $('sheet');
  $('overlay').replaceChildren();
  $('crops').replaceChildren();
  $('source-cells').hidden = !row || !source.naturalWidth;
  if ($('source-cells').hidden) return;
  row.boxes.forEach(([left, top, right, bottom], index) => {
    const width = right-left, height = bottom-top;
    const mark = node('span');
    mark.style.cssText = `left:${left/source.naturalWidth*100}%;top:${top/source.naturalHeight*100}%;width:${width/source.naturalWidth*100}%;height:${height/source.naturalHeight*100}%`;
    $('overlay').append(mark);
    const figure = node('figure');
    const canvas = node('canvas');
    canvas.width = width;
    canvas.height = height;
    canvas.getContext('2d').drawImage(source, left, top, width, height, 0, 0, width, height);
    const label = index ? 'Quantity source crop' : 'SKU source crop';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', label);
    figure.append(canvas, node('figcaption', label));
    $('crops').append(figure);
  });
}
function activeRow() {
  return current?.report.rows.find(row => row.id === selected);
}
$('sheet').addEventListener('load', () => drawSources(activeRow()));
function inspect() {
  const row = activeRow();
  drawSources(row);
  $('review').hidden = !row;
  if (!row) return;
  $('selected').textContent = `Review row ${row.id} · OCR ${row.sku.raw || '—'} / ${row.count.raw || row.count.state}`;
  $('sku').value = row.verified?.sku ?? (row.sku.model_disagreement ? '' : row.sku.raw);
  const strict = current.report.quality_gate;
  const uncertainCount = row.count.model_disagreement || (strict && (
    row.count.confidence < current.report.review_cutoff ||
    current.report.scan_quality.warnings.length > 0
  ));
  $('quantity').value = row.verified?.quantity ?? (uncertainCount ? '' : row.count.raw);
  const differences = [
    ['SKU', row.sku], ['Quantity', row.count],
  ].filter(([, field]) => field.model_disagreement);
  $('model-comparison').textContent = differences.map(([label, field]) =>
    `${label}: primary read ${field.raw}, comparison read ${field.comparison_raw}. Check the source crop.`
  ).join(' ');
  $('reopen').disabled = !row.verified && !row.exclusion_reason;
  $('exclusion-reason').value = row.exclusion_reason ?? '';
  $('suggestions').replaceChildren(...row.suggestions.map(sku => {
    const button = node('button', `Use ${sku} · ${current.report.catalogue.items[sku]}`);
    button.type = 'button';
    button.addEventListener('click', () => { $('sku').value = sku; $('sku').focus(); });
    return button;
  }));
}
$('flagged').addEventListener('change', renderRows);

async function change(action) {
  const form = $('review');
  const buttons = [...form.querySelectorAll('button')];
  buttons.forEach(button => { button.disabled = true; });
  try {
    current = await post(base() + '/review', {
      row: selected, revision: current.report.revision ?? 0,
      sku: $('sku').value.trim(), quantity: $('quantity').value.trim(),
      reason: $('exclusion-reason').value.trim(), action,
    });
    display();
    $('review-status').textContent = {approve: 'Row approved.', reopen: 'Row reopened.', exclude: 'Row excluded.'}[action];
  } catch (error) {
    $('review-status').textContent = error.message;
  } finally {
    buttons.forEach(button => { button.disabled = false; });
    $('reopen').disabled = !activeRow()?.verified && !activeRow()?.exclusion_reason;
  }
}
$('review').addEventListener('submit', event => {
  event.preventDefault();
  change('approve');
});
for (const format of ['json', 'csv']) {
  $('download-' + format).addEventListener('click', event => {
    if (current.export_status !== 'mismatch') return;
    event.preventDefault();
    if (window.confirm(`The approved sum differs from the stated total by ${current.reconciliation.difference}. Export this mismatched revision?`)) {
      const link = node('a');
      link.href = base() + '/' + format + '?confirm_revision=' + encodeURIComponent(current.report.revision ?? 0);
      link.click();
    }
  });
}
$('exclude').addEventListener('click', () => change('exclude'));
$('reopen').addEventListener('click', () => change('reopen'));
$('total-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  try {
    current = await post(base() + '/review', {
      row: null, revision: current.report.revision ?? 0,
      quantity: $('total').value.trim(), action: 'confirm-total',
    });
    display();
    $('status').textContent = 'Printed total confirmed.';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
const recent = localStorage.getItem('stocktake-sheet');
if (recent && /^[a-f0-9]{32}$/.test(recent)) {
  api('/api/sheets/' + recent).then(result => {
    if (!current) { current = result; display(); }
  }).catch(() => localStorage.removeItem('stocktake-sheet'));
}
