/**
 * File Manager Modal - Shopify Style
 * Modern dosya yönetim sistemi
 */

// Modal HTML yapısı
const modalHTML = `
<div id="fileManagerModal" class="fm-modal">
  <div class="fm-modal-content">
    <div class="fm-modal-header">
      <h2><i class="fa fa-images"></i> File Manager</h2>
      <button class="fm-close">&times;</button>
    </div>
    
    <div class="fm-modal-body">
      <!-- Upload Area -->
      <div class="fm-upload-zone" id="fmUploadZone">
        <input type="file" id="fmFileInput" multiple accept="image/*,video/mp4,video/webm,video/quicktime,video/x-msvideo,video/avi" style="display: none;">
        <i class="fa fa-cloud-upload"></i>
        <p>Drag & drop files here or <span class="fm-browse">browse</span></p>
        <small>Supports: JPG, PNG, GIF, WebP, MP4, MOV, WebM</small>
      </div>
      
      <!-- Files Grid -->
      <div class="fm-files-container">
        <div class="fm-files-header">
          <h3>All Files (<span id="fmFileCount">0</span>)</h3>
          <div class="fm-actions">
            <button class="fm-btn-primary" id="fmDoneBtn">
              <i class="fa fa-check"></i> Done
            </button>
          </div>
        </div>
        
        <div class="fm-files-grid" id="fmFilesGrid">
          <!-- Files will be loaded here -->
        </div>
      </div>
    </div>
  </div>
</div>
`;

// Modal CSS
const modalCSS = `
<style>
.fm-modal {
  display: none;
  position: fixed;
  z-index: 9999;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  animation: fadeIn 0.2s ease-out;
}

.fm-modal.active {
  display: flex;
  align-items: center;
  justify-content: center;
}

.fm-modal-content {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 1200px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  animation: slideUp 0.3s ease-out;
}

.fm-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.fm-modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #111827;
  display: flex;
  align-items: center;
  gap: 10px;
}

.fm-close {
  background: none;
  border: none;
  font-size: 32px;
  color: #6b7280;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
  transition: all 0.2s;
  border-radius: 6px;
}

.fm-close:hover {
  background: #f3f4f6;
  color: #111827;
}

.fm-modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* Upload Zone */
.fm-upload-zone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #f9fafb;
  margin-bottom: 30px;
}

.fm-upload-zone:hover {
  border-color: #667eea;
  background: #eef2ff;
}

.fm-upload-zone.dragover {
  border-color: #667eea;
  background: #eef2ff;
  transform: scale(1.02);
}

.fm-upload-zone i {
  font-size: 48px;
  color: #667eea;
  margin-bottom: 12px;
}

.fm-upload-zone p {
  margin: 12px 0 8px;
  font-size: 16px;
  color: #374151;
}

.fm-upload-zone .fm-browse {
  color: #667eea;
  font-weight: 600;
  text-decoration: underline;
}

.fm-upload-zone small {
  color: #6b7280;
  font-size: 13px;
}

/* Files Container */
.fm-files-container {
  margin-top: 24px;
}

.fm-files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.fm-files-header h3 {
  margin: 0;
  font-size: 16px;
  color: #374151;
  font-weight: 600;
}

.fm-btn-primary {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.fm-btn-primary:hover {
  background: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.fm-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Files Grid */
.fm-files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  min-height: 200px;
}

.fm-file-item {
  position: relative;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.fm-file-item:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.fm-file-item.selected {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.fm-file-item.uploading {
  pointer-events: none;
}

.fm-file-img {
  width: 100%;
  height: 150px;
  object-fit: cover;
  display: block;
}

.fm-file-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(102, 126, 234, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.fm-file-item.selected .fm-file-overlay {
  opacity: 1;
}

.fm-file-check {
  width: 40px;
  height: 40px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

/* Delete Button */
.fm-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  opacity: 0;
  transition: all 0.2s;
  z-index: 5;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.fm-file-item:hover .fm-delete-btn {
  opacity: 1;
}

.fm-delete-btn:hover {
  background: #dc2626;
  transform: scale(1.1);
}

/* Upload Progress Overlay */
.fm-upload-progress {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.fm-progress-circle {
  position: relative;
  width: 60px;
  height: 60px;
}

.fm-progress-svg {
  transform: rotate(-90deg);
}

.fm-progress-bg {
  fill: none;
  stroke: #e5e7eb;
  stroke-width: 4;
}

.fm-progress-bar {
  fill: none;
  stroke: #667eea;
  stroke-width: 4;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.3s ease;
}

.fm-progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

/* ─── Floating Upload Tracker (Google Drive style) ─── */
.upload-tracker {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 360px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
  z-index: 2147483647;
  overflow: hidden;
  animation: trackerSlideUp 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.upload-tracker.closing {
  animation: trackerSlideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
.upload-tracker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #1a1a2e;
  color: #fff;
  cursor: pointer;
  user-select: none;
}
.upload-tracker-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
.upload-tracker-header .ut-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.upload-tracker-header .ut-actions button {
  background: none;
  border: none;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.15s;
}
.upload-tracker-header .ut-actions button:hover {
  color: #fff;
  background: rgba(255,255,255,0.1);
}
.upload-tracker-body {
  max-height: 280px;
  overflow-y: auto;
  transition: max-height 0.3s ease;
}
.upload-tracker-body.collapsed {
  max-height: 0;
}
.upload-tracker-body::-webkit-scrollbar {
  width: 4px;
}
.upload-tracker-body::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.ut-file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  animation: utRowFadeIn 0.3s ease;
}
.ut-file-row:last-child { border-bottom: none; }
.ut-file-thumb {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
  background: #f1f5f9;
}
.ut-file-info {
  flex: 1;
  min-width: 0;
}
.ut-file-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ut-file-size {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}
.ut-file-status {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ut-spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: utSpin 0.7s linear infinite;
}
.ut-check {
  color: #22c55e;
  font-size: 18px;
  animation: utPop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.ut-error {
  color: #ef4444;
  font-size: 18px;
}
.ut-overall-progress {
  height: 3px;
  background: #e2e8f0;
}
.ut-overall-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.4s ease;
  border-radius: 0 3px 3px 0;
}

/* Save button lock visual */
.is-locked, button.is-locked {
  opacity: 0.55 !important;
  cursor: not-allowed !important;
  position: relative;
}
.is-locked::after {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  width: 12px; height: 12px;
  margin-top: -6px; margin-left: -6px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: utSpin 0.8s linear infinite;
  pointer-events: none;
}

@keyframes utSpin {
  to { transform: rotate(360deg); }
}

.delete-tracker .upload-tracker-header h4 i {
  margin-right: 6px;
}

@keyframes trackerSlideUp {
  from { transform: translateY(100px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
@keyframes trackerSlideDown {
  from { transform: translateY(0); opacity: 1; }
  to { transform: translateY(100px); opacity: 0; }
}
@keyframes utRowFadeIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes utSpin {
  to { transform: rotate(360deg); }
}
@keyframes utPop {
  0% { transform: scale(0); }
  100% { transform: scale(1); }
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Empty State */
.fm-empty {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
}

.fm-empty i {
  font-size: 64px;
  color: #d1d5db;
  margin-bottom: 16px;
}

.fm-empty p {
  font-size: 16px;
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .fm-modal-content {
    width: 95%;
    max-height: 90vh;
  }
  
  .fm-files-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }
  
  .fm-file-img {
    height: 120px;
  }
}

/* Video Play Icon Overlay */
.fm-video-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 50px;
  height: 50px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 2;
}

.fm-video-overlay i {
  color: white;
  font-size: 20px;
  margin-left: 3px;
}

.fm-file-video {
  width: 100%;
  height: 150px;
  object-fit: cover;
  display: block;
  background: #1a1a2e;
}
</style>
`;

// Inject CSS immediately on load (needed for upload tracker even before modal opens)
if (!document.getElementById('fmModalStyles')) {
  const _style = document.createElement('div');
  _style.id = 'fmModalStyles';
  _style.innerHTML = modalCSS;
  document.head.appendChild(_style);
}

// Initialize modal
function initFileManager() {
  // Add HTML
  if (!document.getElementById('fileManagerModal')) {
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    attachModalEvents();
  }
}

// Attach event listeners
function attachModalEvents() {
  const modal = document.getElementById('fileManagerModal');
  const closeBtn = modal.querySelector('.fm-close');
  const uploadZone = document.getElementById('fmUploadZone');
  const fileInput = document.getElementById('fmFileInput');
  const doneBtn = document.getElementById('fmDoneBtn');

  // Close modal
  closeBtn.addEventListener('click', closeFileManager);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeFileManager();
  });

  // Upload zone click
  uploadZone.addEventListener('click', () => fileInput.click());

  // File input change
  fileInput.addEventListener('change', handleFileSelect);

  // Drag & drop
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    handleFileDrop(e.dataTransfer.files);
  });

  // Done button - sync selection with product grid
  doneBtn.addEventListener('click', syncSelectionToProduct);
}

// Open modal
function openFileManager(productId, variantId = null) {
  initFileManager();
  const modal = document.getElementById('fileManagerModal');
  modal.classList.add('active');
  modal.dataset.productId = productId;
  modal.dataset.variantId = variantId || '';

  if (variantId) {
    loadExistingVariantFiles(productId, variantId);
  } else {
    loadExistingFiles(productId);
  }
}

// Close modal
function closeFileManager() {
  const modal = document.getElementById('fileManagerModal');
  modal.classList.remove('active');

  // Clear selections
  document.querySelectorAll('.fm-file-item.selected').forEach(item => {
    item.classList.remove('selected');
  });
}

// Load existing files
async function loadExistingFiles(productId) {
  const grid = document.getElementById('fmFilesGrid');
  const count = document.getElementById('fmFileCount');

  // Check if temp mode (product creation)
  const isCreateMode = (productId === 'temp' || productId === null || productId === 'null');

  if (isCreateMode) {
    // Load from session (temp files)
    grid.innerHTML = '';

    // Get currently displayed images from sortable grid
    const currentImages = Array.from(document.querySelectorAll('.sortable-image'));

    if (currentImages.length > 0) {
      currentImages.forEach(img => {
        const fileId = img.dataset.fileId;
        const fileUrl = img.querySelector('img')?.src;

        if (fileId && fileUrl) {
          const fileItem = createFileItem({
            id: fileId,
            url: fileUrl,
            name: 'Image',
            temp_file: true
          });
          fileItem.classList.add('selected');  // Auto-select all
          grid.appendChild(fileItem);
        }
      });

      count.textContent = currentImages.length;
    } else {
      grid.innerHTML = '<div class="fm-empty"><i class="fa fa-images"></i><p>No files yet. Upload some!</p></div>';
      count.textContent = '0';
    }

    updateDoneButton();
    return;
  }

  // Existing product mode - fetch from API
  grid.innerHTML = '<div class="fm-empty"><i class="fa fa-spinner fa-spin"></i><p>Loading files...</p></div>';

  try {
    const response = await fetch(`/marketing/api/get_product_files/?product_id=${productId}`);
    const data = await response.json();

    if (data.success && data.files.length > 0) {
      grid.innerHTML = '';

      // Get currently displayed product file IDs
      const currentFileIds = new Set(
        Array.from(document.querySelectorAll('.sortable-image'))
          .map(img => img.dataset.fileId)
      );

      data.files.forEach(file => {
        const fileItem = createFileItem(file);

        // Auto-select if already in product
        if (currentFileIds.has(String(file.id))) {
          fileItem.classList.add('selected');
        }

        grid.appendChild(fileItem);
      });

      count.textContent = data.files.length;
      updateDoneButton();
    } else {
      grid.innerHTML = '<div class="fm-empty"><i class="fa fa-images"></i><p>No files yet. Upload some!</p></div>';
      count.textContent = '0';
    }
  } catch (error) {
    console.error('Error loading files:', error);
    grid.innerHTML = '<div class="fm-empty"><i class="fa fa-exclamation-circle"></i><p>Error loading files</p></div>';
  }
}

// Load existing variant files
async function loadExistingVariantFiles(productId, variantId) {
  const grid = document.getElementById('fmFilesGrid');
  const count = document.getElementById('fmFileCount');

  grid.innerHTML = '<div class="fm-empty"><i class="fa fa-spinner fa-spin"></i><p>Loading variant files...</p></div>';

  try {
    const response = await fetch(`/marketing/api/get_variant_files/?product_id=${productId}&variant_id=${variantId}`);
    const data = await response.json();

    if (data.success && data.files.length > 0) {
      grid.innerHTML = '';

      // All variant files are auto-selected
      data.files.forEach(file => {
        const fileItem = createFileItem(file);
        fileItem.classList.add('selected');
        grid.appendChild(fileItem);
      });

      count.textContent = data.files.length;
      updateDoneButton();
    } else {
      grid.innerHTML = '<div class="fm-empty"><i class="fa fa-images"></i><p>No files yet. Upload some!</p></div>';
      count.textContent = '0';
    }
  } catch (error) {
    console.error('Error loading variant files:', error);
    grid.innerHTML = '<div class="fm-empty"><i class="fa fa-exclamation-circle"></i><p>Error loading files</p></div>';
  }
}

// Create file item element
function createFileItem(file, isNew = false) {
  const div = document.createElement('div');
  div.className = `fm-file-item${isNew ? ' uploading' : ''}`;

  // Use pk for existing files, id for temp files
  const fileId = file.pk || file.id;
  const fileUrl = file.file_url || file.url;
  const isTempFile = file.temp_file || false;

  // Detect if file is a video
  const fileType = file.file_type || file.media_type || detectFileType(fileUrl);
  const isVideo = fileType === 'video';

  div.dataset.fileId = fileId;
  div.dataset.isTempFile = isTempFile;
  div.dataset.fileType = fileType;

  // Generate appropriate HTML based on file type
  if (isVideo) {
    // For videos, show a thumbnail with play icon overlay
    const thumbnailUrl = file.video_thumbnail_url || getVideoThumbnailUrl(fileUrl);
    div.innerHTML = `
      <div style="position: relative;">
        <img src="${thumbnailUrl}" alt="${file.name || 'Video'}" class="fm-file-img" onerror="this.src='${fileUrl}'">
        <div class="fm-video-overlay">
          <i class="fa fa-play"></i>
        </div>
      </div>
      <div class="fm-file-overlay">
        <div class="fm-file-check"><i class="fa fa-check"></i></div>
      </div>
      <button type="button" class="fm-delete-btn" title="Delete">
        <i class="fa fa-trash"></i>
      </button>
    `;
  } else {
    // For images, show the image directly
    div.innerHTML = `
      <img src="${fileUrl}" alt="${file.name || 'Image'}" class="fm-file-img">
      <div class="fm-file-overlay">
        <div class="fm-file-check"><i class="fa fa-check"></i></div>
      </div>
      <button type="button" class="fm-delete-btn" title="Delete">
        <i class="fa fa-trash"></i>
      </button>
    `;
  }

  if (!isNew) {
    // Click on image area toggles selection
    div.addEventListener('click', (e) => {
      // Don't toggle if clicking delete button
      if (!e.target.closest('.fm-delete-btn')) {
        toggleFileSelection(div);
      }
    });

    // Delete button handler
    const deleteBtn = div.querySelector('.fm-delete-btn');
    deleteBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      deleteFileFromModal(fileId, div, isTempFile);
    });
  }

  return div;
}

// Detect file type from URL
function detectFileType(url) {
  if (!url) return 'image';
  // Use regex to match exact extensions at end of URL (or before query string)
  // This avoids false positives like .avif matching .avi
  if (/\.(mp4|mov|webm|avi|mkv|m4v|wmv)(\?.*)?$/i.test(url)) {
    return 'video';
  }
  return 'image';
}

// Generate Cloudinary video thumbnail URL
function getVideoThumbnailUrl(videoUrl) {
  if (!videoUrl) return '';
  // Cloudinary transformation to get video thumbnail (first frame as jpg)
  // w_300 = width, h_200 = height, c_fill = crop fill, so_0 = start offset 0
  const transformedUrl = videoUrl.replace(
    '/upload/',
    '/upload/w_300,h_200,c_fill,so_0,f_jpg/'
  );
  // Change extension to .jpg
  return transformedUrl.replace(/\.(mp4|mov|webm|avi|mkv|m4v|wmv)$/i, '.jpg');
}


// Delete file from modal while preserving other selections
async function deleteFileFromModal(fileId, element, isTempFile = false) {
  // Store current selections before deletion
  const selectedFileIds = new Set();
  document.querySelectorAll('.fm-file-item.selected').forEach(item => {
    if (item.dataset.fileId !== String(fileId)) {
      selectedFileIds.add(item.dataset.fileId);
    }
  });

  // Show confirmation using the existing dialog
  const confirmed = await showConfirmDialog(
    'Delete Image?',
    'This action cannot be undone.',
    'Delete',
    'Cancel'
  );

  if (!confirmed) {
    return;
  }

  // Show loading state
  element.style.opacity = '0.5';
  element.style.pointerEvents = 'none';

  try {
    // Call delete API
    const response = await fetch('/marketing/api/instant_delete_file/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ file_id: fileId })
    });

    const data = await response.json();

    if (data.success) {
      // Remove element from modal with animation
      element.style.animation = 'fadeOut 0.3s ease-out';
      setTimeout(() => {
        element.remove();

        // Update file count
        const count = document.getElementById('fmFileCount');
        if (count) {
          count.textContent = Math.max(0, parseInt(count.textContent) - 1);
        }

        // Restore selections to remaining items
        document.querySelectorAll('.fm-file-item').forEach(item => {
          if (selectedFileIds.has(item.dataset.fileId)) {
            item.classList.add('selected');
          }
        });

        // Update done button
        updateDoneButton();

        // Also remove from product grid if exists
        const productGridItem = document.querySelector(`.sortable-image[data-file-id="${fileId}"]`);
        if (productGridItem) {
          productGridItem.remove();
          if (typeof updatePrimaryBadge === 'function') {
            updatePrimaryBadge();
          }
          if (typeof updateImageOrder === 'function') {
            updateImageOrder();
          }
        }
      }, 300);

      showToast('🗑️ File deleted!', 'success');
    } else {
      throw new Error(data.error || 'Delete failed');
    }
  } catch (error) {
    console.error('Delete error:', error);
    element.style.opacity = '1';
    element.style.pointerEvents = 'auto';
    showToast(`❌ Delete error: ${error.message}`, 'error');
  }
}

// Toggle file selection
function toggleFileSelection(element) {
  element.classList.toggle('selected');
  updateDoneButton();
}

// Update done button state
function updateDoneButton() {
  const selected = document.querySelectorAll('.fm-file-item.selected').length;
  const btn = document.getElementById('fmDoneBtn');

  if (selected > 0) {
    btn.innerHTML = `<i class="fa fa-check"></i> Done (${selected})`;
  } else {
    btn.innerHTML = '<i class="fa fa-check"></i> Done';
  }
}

// Handle file select
function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  uploadFiles(files);
  e.target.value = '';
}

// Handle file drop
function handleFileDrop(files) {
  uploadFiles(Array.from(files));
}

// ─── Floating Upload Tracker (Google Drive style) ───
let uploadTracker = null;
let trackerCollapsed = false;

function createUploadTracker(totalFiles) {
  // Remove existing tracker
  if (uploadTracker) uploadTracker.remove();

  const tracker = document.createElement('div');
  tracker.className = 'upload-tracker';
  tracker.id = 'uploadTracker';
  tracker.innerHTML = `
    <div class="upload-tracker-header" onclick="toggleTrackerCollapse()">
      <h4>
        <span id="utTitle">Uploading <span id="utDoneCount">0</span> of ${totalFiles} items</span>
      </h4>
      <div class="ut-actions">
        <button onclick="event.stopPropagation(); toggleTrackerCollapse()" id="utCollapseBtn" title="Minimize">
          <i class="fa fa-chevron-down"></i>
        </button>
        <button onclick="event.stopPropagation(); closeUploadTracker()" id="utCloseBtn" title="Close" style="display:none;">
          <i class="fa fa-times"></i>
        </button>
      </div>
    </div>
    <div class="ut-overall-progress"><div class="ut-overall-bar" id="utOverallBar" style="width:0%"></div></div>
    <div class="upload-tracker-body" id="utBody"></div>
  `;
  document.body.appendChild(tracker);
  uploadTracker = tracker;
  trackerCollapsed = false;
  return tracker;
}

function addTrackerRow(file) {
  const body = document.getElementById('utBody');
  if (!body) return null;

  const row = document.createElement('div');
  row.className = 'ut-file-row';
  row.id = `ut-row-${file.name.replace(/[^a-zA-Z0-9]/g, '_')}`;

  const sizeStr = file.size > 1048576
    ? (file.size / 1048576).toFixed(1) + ' MB'
    : (file.size / 1024).toFixed(0) + ' KB';

  // Create a thumbnail from the file
  const thumbUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : '';
  const thumbHTML = thumbUrl
    ? `<img class="ut-file-thumb" src="${thumbUrl}" alt="">`
    : `<div class="ut-file-thumb" style="display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#667eea;font-size:14px;"><i class="fa fa-film"></i></div>`;

  row.innerHTML = `
    ${thumbHTML}
    <div class="ut-file-info">
      <div class="ut-file-name">${file.name}</div>
      <div class="ut-file-size">${sizeStr}</div>
    </div>
    <div class="ut-file-status"><div class="ut-spinner"></div></div>
  `;
  body.appendChild(row);

  // Auto-scroll to bottom
  body.scrollTop = body.scrollHeight;
  return row;
}

function updateTrackerRow(row, success) {
  if (!row) return;
  const status = row.querySelector('.ut-file-status');
  if (success) {
    status.innerHTML = '<i class="fa fa-check-circle ut-check"></i>';
  } else {
    status.innerHTML = '<i class="fa fa-times-circle ut-error"></i>';
  }
}

function updateTrackerProgress(done, total) {
  const bar = document.getElementById('utOverallBar');
  const countEl = document.getElementById('utDoneCount');
  const title = document.getElementById('utTitle');
  if (bar) bar.style.width = `${(done / total) * 100}%`;
  if (countEl) countEl.textContent = done;

  if (done >= total) {
    if (title) title.innerHTML = `<i class="fa fa-check-circle" style="color:#22c55e"></i> ${total} file uploaded`;
    const closeBtn = document.getElementById('utCloseBtn');
    if (closeBtn) closeBtn.style.display = '';
    // Auto-close after 4 seconds
    setTimeout(() => closeUploadTracker(), 4000);
  }
}

function toggleTrackerCollapse() {
  const body = document.getElementById('utBody');
  const btn = document.getElementById('utCollapseBtn');
  if (!body) return;
  trackerCollapsed = !trackerCollapsed;
  body.classList.toggle('collapsed', trackerCollapsed);
  if (btn) btn.innerHTML = trackerCollapsed ? '<i class="fa fa-chevron-up"></i>' : '<i class="fa fa-chevron-down"></i>';
}

function closeUploadTracker() {
  const tracker = document.getElementById('uploadTracker');
  if (tracker) {
    tracker.classList.add('closing');
    setTimeout(() => { tracker.remove(); uploadTracker = null; }, 300);
  }
}

// Expose tracker functions globally for variant_form_modern.js
window.createUploadTracker = createUploadTracker;
window.addTrackerRow = addTrackerRow;
window.updateTrackerRow = updateTrackerRow;
window.updateTrackerProgress = updateTrackerProgress;
window.closeUploadTracker = closeUploadTracker;
window.toggleTrackerCollapse = toggleTrackerCollapse;

// ─── DELETE TRACKER ─────────────────────────────────────────
let deleteTracker = null;
let deleteTotal = 0;
let deleteDone = 0;

// Track every in-flight delete by a unique token
// Save button stays locked while this Set has ANY items, unlocks when empty
const pendingDeletes = new Set();
let _deleteTokenCounter = 0;

function setSaveButtonLock(locked) {
  const saveBtns = document.querySelectorAll('#save_product_btn, button[name="save"], .save-product-btn, [data-save-product]');
  saveBtns.forEach(btn => {
    if (locked) {
      btn.disabled = true;
      btn.classList.add('is-locked');
      btn.setAttribute('title', 'Waiting for image deletion to complete...');
    } else {
      btn.disabled = false;
      btn.classList.remove('is-locked');
      btn.removeAttribute('title');
    }
  });
}

function beginDelete() {
  const token = ++_deleteTokenCounter;
  pendingDeletes.add(token);
  setSaveButtonLock(true);
  return token;
}

function endDelete(token) {
  pendingDeletes.delete(token);
  if (pendingDeletes.size === 0) {
    // All selected deletes have completed → unlock
    setSaveButtonLock(false);
  }
}

function createDeleteTracker(totalFiles) {
  if (deleteTracker) deleteTracker.remove();
  deleteTotal = totalFiles;
  deleteDone = 0;

  const tracker = document.createElement('div');
  tracker.className = 'upload-tracker delete-tracker';
  tracker.id = 'deleteTracker';
  tracker.innerHTML = `
    <div class="upload-tracker-header" onclick="toggleDeleteTrackerCollapse()">
      <h4>
        <i class="fa fa-trash-alt" style="color:#ef4444;"></i>
        <span id="dtTitle">Deleting <span id="dtDoneCount">0</span> of ${totalFiles} items</span>
      </h4>
      <div class="ut-actions">
        <button onclick="event.stopPropagation(); toggleDeleteTrackerCollapse()" id="dtCollapseBtn" title="Minimize">
          <i class="fa fa-chevron-down"></i>
        </button>
        <button onclick="event.stopPropagation(); closeDeleteTracker()" id="dtCloseBtn" title="Close" style="display:none;">
          <i class="fa fa-times"></i>
        </button>
      </div>
    </div>
    <div class="ut-overall-progress"><div class="ut-overall-bar" id="dtOverallBar" style="width:0%; background:#ef4444;"></div></div>
    <div class="upload-tracker-body" id="dtBody"></div>
  `;
  document.body.appendChild(tracker);
  deleteTracker = tracker;
  return tracker;
}

function addDeleteTrackerRow(image) {
  const body = document.getElementById('dtBody');
  if (!body) return null;

  const row = document.createElement('div');
  row.className = 'ut-file-row';
  const fileName = image.name || (image.url ? image.url.split('/').pop().split('?')[0] : 'image');

  const thumbUrl = image.optimized_url || image.url;
  const isVideo = image.file_type === 'video';
  const thumbHTML = thumbUrl && !isVideo
    ? `<img class="ut-file-thumb" src="${thumbUrl}" alt="" onerror="this.style.display='none'">`
    : `<div class="ut-file-thumb" style="display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#ef4444;font-size:14px;"><i class="fa ${isVideo ? 'fa-film' : 'fa-image'}"></i></div>`;

  row.innerHTML = `
    ${thumbHTML}
    <div class="ut-file-info">
      <div class="ut-file-name">${fileName}</div>
      <div class="ut-file-size">Deleting...</div>
    </div>
    <div class="ut-file-status"><div class="ut-spinner" style="border-top-color:#ef4444;"></div></div>
  `;
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;
  return row;
}

function updateDeleteTrackerRow(row, success) {
  if (!row) return;
  const status = row.querySelector('.ut-file-status');
  const sizeEl = row.querySelector('.ut-file-size');
  if (success) {
    status.innerHTML = '<i class="fa fa-check-circle ut-check" style="color:#22c55e;"></i>';
    if (sizeEl) sizeEl.textContent = 'Deleted';
  } else {
    status.innerHTML = '<i class="fa fa-times-circle ut-error"></i>';
    if (sizeEl) sizeEl.textContent = 'Failed';
  }
}

function updateDeleteTrackerProgress(done, total) {
  const bar = document.getElementById('dtOverallBar');
  const countEl = document.getElementById('dtDoneCount');
  const title = document.getElementById('dtTitle');
  if (bar) bar.style.width = `${(done / total) * 100}%`;
  if (countEl) countEl.textContent = done;

  if (done >= total) {
    if (title) title.innerHTML = `<i class="fa fa-check-circle" style="color:#22c55e"></i> ${total} item${total>1?'s':''} deleted`;
    const closeBtn = document.getElementById('dtCloseBtn');
    if (closeBtn) closeBtn.style.display = '';
    // NOTE: Save button unlock is driven by pendingDeletes Set (see endDelete), not tracker progress
    setTimeout(() => closeDeleteTracker(), 3000);
  }
}

function toggleDeleteTrackerCollapse() {
  const body = document.getElementById('dtBody');
  const btn = document.getElementById('dtCollapseBtn');
  if (!body) return;
  body.classList.toggle('collapsed');
  if (btn) btn.innerHTML = body.classList.contains('collapsed') ? '<i class="fa fa-chevron-up"></i>' : '<i class="fa fa-chevron-down"></i>';
}

function closeDeleteTracker() {
  const tracker = document.getElementById('deleteTracker');
  if (tracker) {
    tracker.classList.add('closing');
    setTimeout(() => { tracker.remove(); deleteTracker = null; }, 300);
  }
  // Safety: if any pending deletes left, keep locked; else unlock
  if (pendingDeletes.size === 0) setSaveButtonLock(false);
}

window.createDeleteTracker = createDeleteTracker;
window.addDeleteTrackerRow = addDeleteTrackerRow;
window.updateDeleteTrackerRow = updateDeleteTrackerRow;
window.updateDeleteTrackerProgress = updateDeleteTrackerProgress;
window.toggleDeleteTrackerCollapse = toggleDeleteTrackerCollapse;
window.closeDeleteTracker = closeDeleteTracker;
window.setSaveButtonLock = setSaveButtonLock;
// Pending-delete API: each delete takes a token, returns it when finished.
// Save button stays locked while ANY token is outstanding, unlocks when ALL are returned.
window.__beginDelete = beginDelete;
window.__endDelete = endDelete;
window.__pendingDeleteCount = () => pendingDeletes.size;
// Back-compat aliases
window.__incInflightDelete = () => beginDelete();
window.__decInflightDelete = (token) => { if (token) endDelete(token); };

// Upload files with progress
async function uploadFiles(files) {
  const modal = document.getElementById('fileManagerModal');
  const productId = modal.dataset.productId;
  const variantId = modal.dataset.variantId || null;
  const grid = document.getElementById('fmFilesGrid');

  // Get existing file names from grid
  const existingFileNames = new Set();
  grid.querySelectorAll('.fm-file-item .fm-file-img').forEach(img => {
    const url = img.src || '';
    const fileName = url.split('/').pop().split('?')[0];
    if (fileName) existingFileNames.add(fileName);
  });

  // Filter out duplicates first
  const filesToUpload = files.filter(file => {
    if (existingFileNames.has(file.name)) {
      showToast(`⚠️ "${file.name}" already exists`, 'warning');
      return false;
    }
    return true;
  });

  if (filesToUpload.length === 0) return;

  // Create floating tracker
  createUploadTracker(filesToUpload.length);
  let doneCount = 0;

  for (const file of filesToUpload) {
    // Add row to tracker
    const trackerRow = addTrackerRow(file);

    // Create placeholder in modal grid
    const placeholder = createUploadPlaceholder(file);
    grid.appendChild(placeholder);

    // Upload
    const uploadedFile = await uploadSingleFile(file, productId, placeholder, variantId);

    doneCount++;

    if (uploadedFile) {
      existingFileNames.add(file.name);

      const fileItem = createFileItem(uploadedFile);
      placeholder.replaceWith(fileItem);

      const count = document.getElementById('fmFileCount');
      count.textContent = parseInt(count.textContent) + 1;
      updateDoneButton();

      updateTrackerRow(trackerRow, true);
    } else {
      placeholder.remove();
      updateTrackerRow(trackerRow, false);
    }

    updateTrackerProgress(doneCount, filesToUpload.length);
  }
}

// Create upload placeholder
function createUploadPlaceholder(file) {
  const div = document.createElement('div');
  div.className = 'fm-file-item uploading';

  const reader = new FileReader();
  reader.onload = (e) => {
    div.innerHTML = `
      <img src="${e.target.result}" alt="Uploading" class="fm-file-img">
      <div class="fm-upload-progress">
        <div class="fm-progress-circle">
          <svg class="fm-progress-svg" width="60" height="60">
            <circle class="fm-progress-bg" cx="30" cy="30" r="26"></circle>
            <circle class="fm-progress-bar" cx="30" cy="30" r="26" 
              stroke-dasharray="163.36" 
              stroke-dashoffset="163.36"
              data-progress="0"></circle>
          </svg>
          <div class="fm-progress-text">0%</div>
        </div>
      </div>
    `;
  };
  reader.readAsDataURL(file);

  return div;
}

// Upload single file
async function uploadSingleFile(file, productId, placeholder, variantId = null) {
  // Wait for DOM to be ready
  await new Promise(resolve => setTimeout(resolve, 100));

  const progressBar = placeholder.querySelector('.fm-progress-bar');
  const progressText = placeholder.querySelector('.fm-progress-text');

  if (!progressBar || !progressText) {
    console.warn('Progress elements not found');
    return null;
  }

  const formData = new FormData();
  formData.append('file', file);

  // Check if product creation mode (productId === 'temp')
  const isCreateMode = (productId === 'temp' || productId === null || productId === 'null');

  if (isCreateMode) {
    // Use temporary upload API
    formData.append('file_type', variantId ? 'variant_image' : 'main_image');
    formData.append('sequence', 0);
    if (variantId) {
      formData.append('variant_temp_id', variantId);
    }
  } else {
    // Use instant upload API (existing product)
    formData.append('product_id', productId);
    if (variantId) {
      formData.append('variant_id', variantId);
    }
  }

  try {
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
      if (progress < 90 && progressBar && progressText) {
        progress += 10;
        updateProgress(progressBar, progressText, progress);
      }
    }, 100);

    const apiUrl = isCreateMode ? '/marketing/api/temp_upload_file/' : '/marketing/api/instant_upload_file/';
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: formData
    });

    clearInterval(progressInterval);
    updateProgress(progressBar, progressText, 100);

    const data = await response.json();

    if (data.success) {
      showToast('✅ File uploaded!', 'success');

      // For temp uploads, return file_data with a fake ID for tracking
      if (isCreateMode) {
        return {
          pk: data.file_data.public_id,  // Use public_id as temporary ID
          file_url: data.file_data.url,
          is_primary: false,
          temp_file: true  // Mark as temporary
        };
      }

      return data.file;
    } else {
      throw new Error(data.error || 'Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    showToast(`❌ Upload failed: ${error.message}`, 'error');
    return null;
  }
}

// Update progress
function updateProgress(circle, text, percent) {
  const circumference = 163.36;
  const offset = circumference - (percent / 100) * circumference;
  circle.style.strokeDashoffset = offset;
  text.textContent = `${percent}%`;
}

// Sync selection to product - Replace product grid with selected files
function syncSelectionToProduct() {
  const selectedItems = document.querySelectorAll('.fm-file-item.selected');
  const productGrid = document.getElementById('sortable_images');

  if (!productGrid) {
    showToast('❌ Product grid not found', 'error');
    return;
  }

  // Get selected file IDs and URLs
  const selectedFiles = Array.from(selectedItems).map(item => {
    const fileId = item.dataset.fileId;
    const fileUrl = item.querySelector('.fm-file-img').src;
    const fileType = item.dataset.fileType || detectFileType(fileUrl);
    console.log('Selected file:', fileId, fileUrl, 'type:', fileType);
    return {
      id: fileId,
      url: fileUrl,
      fileType: fileType
    };
  });

  if (selectedFiles.length === 0) {
    showToast('⚠️ No files selected', 'error');
    return;
  }

  // Get current grid files to preserve existing elements
  const currentFiles = new Map();
  productGrid.querySelectorAll('.sortable-image').forEach(img => {
    const fileId = img.dataset.fileId;
    if (fileId) {
      currentFiles.set(fileId, img);
    }
  });

  // Clear grid
  productGrid.innerHTML = '';

  // Add selected files - reuse existing elements or create new
  selectedFiles.forEach(file => {
    let fileElement;

    if (currentFiles.has(file.id)) {
      // Reuse existing element (preserves event handlers)
      fileElement = currentFiles.get(file.id);
      console.log('Reusing existing element for file:', file.id);
    } else {
      // Create new element with file type
      fileElement = createProductFileElement(file.id, file.url, file.fileType);
      console.log('Creating new element for file:', file.id, 'type:', file.fileType);
    }

    productGrid.appendChild(fileElement);
  });

  // Update primary badges
  if (typeof updatePrimaryBadge === 'function') {
    updatePrimaryBadge();
  }

  // Update image order hidden field
  if (typeof updateImageOrder === 'function') {
    updateImageOrder();
  }

  showToast(`✅ ${selectedFiles.length} file(s) synced!`, 'success');
  closeFileManager();
}

// Create product file element (matching existing style)
function createProductFileElement(fileId, fileSrc, fileType = 'image') {
  const div = document.createElement('div');
  div.className = 'sortable-image';
  div.setAttribute('data-file-id', fileId);
  div.setAttribute('data-file-type', fileType);
  div.style.cssText = 'position: relative; border: 2px solid #e5e7eb; border-radius: 8px; padding: 10px; background: white; width: 150px; opacity: 1;';

  const isVideo = fileType === 'video';
  const thumbnailUrl = isVideo ? getVideoThumbnailUrl(fileSrc) : fileSrc;

  if (isVideo) {
    // Video element with play icon overlay
    div.innerHTML = `
      <div class="drag-handle" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 5px 8px; border-radius: 4px; font-size: 12px; cursor: grab; user-select: none; z-index: 3;">
        <i class="fa fa-grip-vertical"></i>
      </div>
      <div style="position: relative;">
        <a href="${fileSrc}" target="_blank" style="pointer-events: none;">
          <img src="${thumbnailUrl}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 6px; pointer-events: none; user-select: none; background: #1a1a2e;" onerror="this.src='${fileSrc}'"/>
        </a>
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 40px; height: 40px; background: rgba(0,0,0,0.7); border-radius: 50%; display: flex; align-items: center; justify-content: center; pointer-events: none;">
          <i class="fa fa-play" style="color: white; font-size: 16px; margin-left: 3px;"></i>
        </div>
      </div>
      <div style="display: flex; justify-content: center; align-items: center; margin-top: 8px;">
        <button type="button" class="instant-delete-btn" data-file-id="${fileId}" style="background: #ef4444; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 11px; width: 100%;">
          <i class="fa fa-trash"></i> Delete
        </button>
      </div>
    `;
  } else {
    // Image element
    div.innerHTML = `
      <div class="drag-handle" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 5px 8px; border-radius: 4px; font-size: 12px; cursor: grab; user-select: none;">
        <i class="fa fa-grip-vertical"></i>
      </div>
      <a href="${fileSrc}" target="_blank" style="pointer-events: none;">
        <img src="${fileSrc}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 6px; pointer-events: none; user-select: none;"/>
      </a>
      <div style="display: flex; justify-content: center; align-items: center; margin-top: 8px;">
        <button type="button" class="instant-delete-btn" data-file-id="${fileId}" style="background: #ef4444; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 11px; width: 100%;">
          <i class="fa fa-trash"></i> Delete
        </button>
      </div>
    `;
  }

  // Add delete handler with logging
  const deleteBtn = div.querySelector('.instant-delete-btn');

  // Mark as already having handler
  deleteBtn.dataset.handlerAttached = 'true';

  deleteBtn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    console.log('Delete clicked for file ID:', fileId);
    if (typeof instantDeleteFile === 'function') {
      instantDeleteFile(fileId, div);
    } else {
      console.error('instantDeleteFile function not found');
    }
  });

  return div;
}

// CSRF token helper
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Toast notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${type === 'success' ? '#10b981' : '#ef4444'};
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Variant için özel fonksiyon
function openVariantFileManager(productId, variantId) {
  openFileManager(productId, variantId);
}

// Export functions
window.openFileManager = openFileManager;
window.openVariantFileManager = openVariantFileManager;
window.closeFileManager = closeFileManager;
