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
    const response = await fetch('/api/example');
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
