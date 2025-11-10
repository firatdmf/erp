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
        <input type="file" id="fmFileInput" multiple accept="image/*" style="display: none;">
        <i class="fa fa-cloud-upload"></i>
        <p>Drag & drop files here or <span class="fm-browse">browse</span></p>
        <small>Supports: JPG, PNG, GIF, WebP</small>
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
</style>
`;

// Initialize modal
function initFileManager() {
  // Add CSS
  if (!document.getElementById('fmModalStyles')) {
    const style = document.createElement('div');
    style.id = 'fmModalStyles';
    style.innerHTML = modalCSS;
    document.head.appendChild(style);
  }
  
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
  div.dataset.fileId = file.id;
  
  div.innerHTML = `
    <img src="${file.url}" alt="${file.name || 'Image'}" class="fm-file-img">
    <div class="fm-file-overlay">
      <div class="fm-file-check"><i class="fa fa-check"></i></div>
    </div>
  `;
  
  if (!isNew) {
    div.addEventListener('click', () => toggleFileSelection(div));
  }
  
  return div;
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

// Upload files with progress
async function uploadFiles(files) {
  const modal = document.getElementById('fileManagerModal');
  const productId = modal.dataset.productId;
  const variantId = modal.dataset.variantId || null;
  const grid = document.getElementById('fmFilesGrid');
  
  for (const file of files) {
    // Create placeholder with progress
    const placeholder = createUploadPlaceholder(file);
    // Add to END of grid, not beginning
    grid.appendChild(placeholder);
    
    // Upload
    const uploadedFile = await uploadSingleFile(file, productId, placeholder, variantId);
    
    if (uploadedFile) {
      console.log('Uploaded file object:', uploadedFile);
      
      // Replace placeholder with actual file
      const fileItem = createFileItem(uploadedFile);
      console.log('Created file item, dataset.fileId:', fileItem.dataset.fileId);
      placeholder.replaceWith(fileItem);
      
      // Update count
      const count = document.getElementById('fmFileCount');
      count.textContent = parseInt(count.textContent) + 1;
      
      // Update done button
      updateDoneButton();
    } else {
      placeholder.remove();
    }
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
  formData.append('product_id', productId);
  if (variantId) {
    formData.append('variant_id', variantId);
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
    
    const response = await fetch('/marketing/api/instant_upload_file/', {
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
    console.log('Selected file:', fileId, fileUrl);
    return {
      id: fileId,
      url: fileUrl
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
      // Create new element
      fileElement = createProductFileElement(file.id, file.url);
      console.log('Creating new element for file:', file.id);
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
function createProductFileElement(fileId, imgSrc) {
  const div = document.createElement('div');
  div.className = 'sortable-image';
  div.setAttribute('data-file-id', fileId);
  div.style.cssText = 'position: relative; border: 2px solid #e5e7eb; border-radius: 8px; padding: 10px; background: white; width: 150px; opacity: 1;';
  
  div.innerHTML = `
    <div class="drag-handle" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 5px 8px; border-radius: 4px; font-size: 12px; cursor: grab; user-select: none;">
      <i class="fa fa-grip-vertical"></i>
    </div>
    <a href="${imgSrc}" target="_blank" style="pointer-events: none;">
      <img src="${imgSrc}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 6px; pointer-events: none; user-select: none;"/>
    </a>
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 8px;">
      <button type="button" class="instant-delete-btn" data-file-id="${fileId}" style="background: #ef4444; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 11px; width: 100%;">
        <i class="fa fa-trash"></i> Delete
      </button>
    </div>
  `;
  
  // Add delete handler with logging
  const deleteBtn = div.querySelector('.instant-delete-btn');
  
  // Mark as already having handler
  deleteBtn.dataset.handlerAttached = 'true';
  
  deleteBtn.addEventListener('click', function(e) {
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
