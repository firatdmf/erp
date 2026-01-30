/**
 * Temporary File Manager for Product Creation
 * Handles file uploads before product_id exists
 * Includes automatic cleanup on page unload
 */

// Track uploaded files
let tempFiles = {
    main_images: [],
    variant_images: {}
};

let hasUnsavedFiles = false;

// Get CSRF token
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

const tempCsrfToken = getCookie('csrftoken');

// Toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
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
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add CSS animations
const tempStyle = document.createElement('style');
tempStyle.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
    .temp-upload-progress {
        position: relative;
        border: 2px dashed #3b82f6;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        background: #dbeafe;
        margin: 10px 0;
    }
    .temp-upload-progress-bar {
        width: 100%;
        height: 4px;
        background: #e5e7eb;
        border-radius: 2px;
        overflow: hidden;
        margin-top: 10px;
    }
    .temp-upload-progress-fill {
        height: 100%;
        background: #3b82f6;
        transition: width 0.3s ease;
    }
    .temp-file-preview {
        position: relative;
        display: inline-block;
        margin: 10px;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .temp-file-preview img {
        width: 120px;
        height: 120px;
        object-fit: cover;
        display: block;
    }
    .temp-file-delete-btn {
        position: absolute;
        top: 5px;
        right: 5px;
        background: rgba(220, 38, 38, 0.9);
        color: white;
        border: none;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
    }
    .temp-file-delete-btn:hover {
        background: rgba(185, 28, 28, 0.9);
        transform: scale(1.1);
    }
`;
document.head.appendChild(tempStyle);

/**
 * Upload file to temporary storage
 * @param {File} file - File to upload
 * @param {string} fileType - 'main_image' or 'variant_image'
 * @param {string|null} variantTempId - Temporary variant ID for variant images
 * @param {HTMLElement} container - Container to show preview
 */
async function tempUploadFile(file, fileType, variantTempId, container) {
    // Show progress
    const progressDiv = document.createElement('div');
    progressDiv.className = 'temp-upload-progress';
    progressDiv.innerHTML = `
        <div>📤 Uploading: ${file.name}</div>
        <div class="temp-upload-progress-bar">
            <div class="temp-upload-progress-fill" style="width: 30%"></div>
        </div>
    `;
    container.appendChild(progressDiv);

    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    formData.append('sequence', fileType === 'main_image' ? tempFiles.main_images.length : (tempFiles.variant_images[variantTempId]?.length || 0));

    if (variantTempId) {
        formData.append('variant_temp_id', variantTempId);
    }

    try {
        // Update progress to 60%
        progressDiv.querySelector('.temp-upload-progress-fill').style.width = '60%';

        const response = await fetch('/marketing/api/temp_upload_file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': tempCsrfToken,
            },
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Update progress to 100%
            progressDiv.querySelector('.temp-upload-progress-fill').style.width = '100%';

            // Store file data
            const fileData = result.file_data;
            if (fileType === 'main_image') {
                tempFiles.main_images.push(fileData);
            } else if (fileType === 'variant_image' && variantTempId) {
                if (!tempFiles.variant_images[variantTempId]) {
                    tempFiles.variant_images[variantTempId] = [];
                }
                tempFiles.variant_images[variantTempId].push(fileData);
            }

            hasUnsavedFiles = true;

            // Replace progress with preview
            setTimeout(() => {
                progressDiv.remove();

                const preview = document.createElement('div');
                preview.className = 'temp-file-preview';
                preview.dataset.publicId = fileData.public_id;
                preview.innerHTML = `
                    <img src="${fileData.url}" alt="${fileData.name}" loading="lazy">
                    <button class="temp-file-delete-btn" onclick="tempDeleteFile('${fileData.public_id}', '${fileType}', '${variantTempId || ''}', this)">
                        <i class="fa fa-times"></i>
                    </button>
                `;
                container.appendChild(preview);

                showToast('✅ File uploaded!');
            }, 500);
        } else {
            throw new Error(result.error || 'Upload failed');
        }

    } catch (error) {
        console.error('Upload error:', error);
        progressDiv.remove();
        showToast(`❌ Upload error: ${error.message}`, 'error');
    }
}

/**
 * Delete temporary file
 * @param {string} publicId - Cloudinary public_id
 * @param {string} fileType - 'main_image' or 'variant_image'
 * @param {string} variantTempId - Temporary variant ID (empty string if not variant)
 * @param {HTMLElement} btn - Delete button element
 */
async function tempDeleteFile(publicId, fileType, variantTempId, btn) {
    const preview = btn.closest('.temp-file-preview');

    // Remove from local tracking
    if (fileType === 'main_image') {
        tempFiles.main_images = tempFiles.main_images.filter(f => f.public_id !== publicId);
    } else if (fileType === 'variant_image' && variantTempId) {
        if (tempFiles.variant_images[variantTempId]) {
            tempFiles.variant_images[variantTempId] = tempFiles.variant_images[variantTempId].filter(f => f.public_id !== publicId);
        }
    }

    // Update hasUnsavedFiles flag
    hasUnsavedFiles = (tempFiles.main_images.length > 0) ||
        (Object.values(tempFiles.variant_images).some(arr => arr.length > 0));

    // Remove preview
    preview.remove();
    showToast('🗑️ File deleted!');

    // Note: No need to call cleanup API here since session-based deletion
    // happens automatically on page unload
}

/**
 * Cleanup all temporary files
 * Called on page unload
 */
async function cleanupTempFiles() {
    if (!hasUnsavedFiles) {
        return;
    }

    try {
        // Use sendBeacon for reliable cleanup during page unload
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', tempCsrfToken);

        // sendBeacon doesn't support custom headers, so use FormData
        navigator.sendBeacon('/marketing/api/cleanup_temp_files/', formData);

        console.log('🧹 Cleanup triggered for temp files');
    } catch (error) {
        console.error('Cleanup error:', error);
    }
}

/**
 * Warn user before leaving if they have unsaved files
 */
function beforeUnloadWarning(e) {
    if (hasUnsavedFiles) {
        // Trigger cleanup
        cleanupTempFiles();

        // Show browser warning
        const message = 'You have uploaded files but haven\'t saved the product yet. Files will be deleted if you leave.';
        e.preventDefault();
        e.returnValue = message;
        return message;
    }
}

// Setup beforeunload event
window.addEventListener('beforeunload', beforeUnloadWarning);

// Cleanup on page hide (mobile/tab close)
window.addEventListener('pagehide', () => {
    if (hasUnsavedFiles) {
        cleanupTempFiles();
    }
});

/**
 * Mark files as saved (call this when product is successfully created)
 */
function markFilesAsSaved() {
    hasUnsavedFiles = false;
    tempFiles = { main_images: [], variant_images: {} };
}

// Export functions for use in product create form
window.tempUploadFile = tempUploadFile;
window.tempDeleteFile = tempDeleteFile;
window.markFilesAsSaved = markFilesAsSaved;
window.tempFiles = tempFiles;

console.log('✅ Temporary file manager loaded');
