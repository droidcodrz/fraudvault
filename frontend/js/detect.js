let _selectedFile = null;

function renderDetect() {
  return `
    <div class="page">
      <div class="page-header">
        <h1>Detect Forgery</h1>
        <p>Upload an image or PDF to analyze for tampering</p>
      </div>

      <div id="detect-upload">
        <div class="upload-zone" id="drop-zone">
          <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
          </svg>
          <h3>Drop file here or click to browse</h3>
          <p>Supports JPEG, PNG, WebP, TIFF, HEIC (20MB) and PDF (50MB)</p>
        </div>
        <div id="file-preview" style="display:none"></div>
        <input type="file" id="file-input" accept=".jpg,.jpeg,.png,.webp,.tiff,.heic,.heif,.pdf" style="display:none">
        <div style="margin-top:16px; display:flex; gap:12px; align-items:center;">
          <button class="btn btn-primary btn-block" id="detect-btn" disabled>Analyze File</button>
        </div>
      </div>

      <div id="detect-progress" style="display:none">
        <div class="loading-state">
          <div class="spinner"></div>
          <span>Analyzing file... This may take a few seconds</span>
        </div>
      </div>

      <div id="detect-result" style="display:none"></div>
    </div>
  `;
}

function initDetect() {
  _selectedFile = null;
  const zone = document.getElementById('drop-zone');
  const input = document.getElementById('file-input');
  const btn = document.getElementById('detect-btn');

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files.length) selectFile(input.files[0]); });

  btn.addEventListener('click', runDetection);
}

function selectFile(file) {
  _selectedFile = file;
  const preview = document.getElementById('file-preview');
  const sizeMB = (file.size / 1024 / 1024).toFixed(2);
  const ext = file.name.split('.').pop().toUpperCase();
  preview.style.display = '';
  preview.innerHTML = `
    <div class="upload-preview">
      <div class="file-icon">${ext === 'PDF' ? 'PDF' : 'IMG'}</div>
      <div class="file-info">
        <div class="file-name">${escHtml(file.name)}</div>
        <div class="file-size">${sizeMB} MB</div>
      </div>
      <button class="file-remove" id="remove-file">&times;</button>
    </div>`;
  document.getElementById('remove-file').addEventListener('click', () => {
    _selectedFile = null;
    preview.style.display = 'none';
    document.getElementById('detect-btn').disabled = true;
  });
  document.getElementById('detect-btn').disabled = false;
}

async function runDetection() {
  if (!_selectedFile) return;
  const uploadEl = document.getElementById('detect-upload');
  const progressEl = document.getElementById('detect-progress');
  const resultEl = document.getElementById('detect-result');

  uploadEl.style.display = 'none';
  progressEl.style.display = '';
  resultEl.style.display = 'none';

  try {
    const data = await API.detect(_selectedFile);
    progressEl.style.display = 'none';
    resultEl.style.display = '';
    resultEl.innerHTML = buildResultHTML(data);
  } catch (err) {
    progressEl.style.display = 'none';
    uploadEl.style.display = '';
    App.toast(err.message, 'error');
  }
}
