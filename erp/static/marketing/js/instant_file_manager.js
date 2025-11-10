/**
 * Instant File Upload/Delete Manager
 * Shopify-style instant file operations for product edit page
 */

// Modern confirmation dialog
function showConfirmDialog(title, message, confirmText, cancelText) {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease-out;
        `;
        
        // Create dialog
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            border-radius: 16px;
            padding: 24px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideUp 0.3s ease-out;
        `;
        
        dialog.innerHTML = `
            <div style="text-align: center;">
                <div style="width: 56px; height: 56px; background: #fee2e2; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                    <i class="fa fa-trash" style="font-size: 24px; color: #dc2626;"></i>
                </div>
                <h3 style="margin: 0 0 8px; font-size: 20px; color: #111827;">${title}</h3>
                <p style="margin: 0 0 24px; color: #6b7280; font-size: 14px;">${message}</p>
                <div style="display: flex; gap: 12px;">
                    <button id="confirmCancel" style="flex: 1; padding: 10px 20px; background: #f3f4f6; color: #374151; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;">
                        ${cancelText}
                    </button>
                    <button id="confirmDelete" style="flex: 1; padding: 10px 20px; background: #dc2626; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;">
                        ${confirmText}
                    </button>
                </div>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // Handle buttons
        const cancelBtn = dialog.querySelector('#confirmCancel');
        const deleteBtn = dialog.querySelector('#confirmDelete');
        
        cancelBtn.addEventListener('mouseover', () => {
            cancelBtn.style.background = '#e5e7eb';
        });
        cancelBtn.addEventListener('mouseout', () => {
            cancelBtn.style.background = '#f3f4f6';
        });
        
        deleteBtn.addEventListener('mouseover', () => {
            deleteBtn.style.background = '#b91c1c';
        });
        deleteBtn.addEventListener('mouseout', () => {
            deleteBtn.style.background = '#dc2626';
        });
        
        cancelBtn.addEventListener('click', () => {
            overlay.style.animation = 'fadeOut 0.2s ease-out';
            setTimeout(() => overlay.remove(), 200);
            resolve(false);
        });
        
        deleteBtn.addEventListener('click', () => {
            overlay.style.animation = 'fadeOut 0.2s ease-out';
            setTimeout(() => overlay.remove(), 200);
            resolve(true);
        });
        
        // ESC key to cancel
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                cancelBtn.click();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    });
}

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

const csrftoken = getCookie('csrftoken');

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
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
    .upload-progress {
        position: relative;
        border: 2px dashed #3b82f6;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        background: #dbeafe;
    }
    .upload-progress-bar {
        width: 100%;
        height: 4px;
        background: #e5e7eb;
        border-radius: 2px;
        overflow: hidden;
        margin-top: 10px;
    }
    .upload-progress-fill {
        height: 100%;
        background: #3b82f6;
        transition: width 0.3s ease;
    }
`;
document.head.appendChild(style);

/**
 * Instant File Upload
 * @param {File} file - File object to upload
 * @param {number} productId - Product ID
 * @param {number|null} variantId - Variant ID (optional)
 * @param {HTMLElement} container - Container to show preview
 */
async function instantUploadFile(file, productId, variantId, container) {
    // Show progress
    const progressDiv = document.createElement('div');
    progressDiv.className = 'upload-progress';
    progressDiv.innerHTML = `
        <div>📤 Yükleniyor: ${file.name}</div>
        <div class="upload-progress-bar">
            <div class="upload-progress-fill" style="width: 30%"></div>
        </div>
    `;
    container.appendChild(progressDiv);
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('product_id', productId);
    if (variantId) {
        formData.append('variant_id', variantId);
    }
    
    try {
        // Update progress
        progressDiv.querySelector('.upload-progress-fill').style.width = '60%';
        
        // Upload
        const response = await fetch('/marketing/api/instant_upload_file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update progress
            progressDiv.querySelector('.upload-progress-fill').style.width = '100%';
            
            // Create preview
            const preview = createFilePreview(data.file);
            container.insertBefore(preview, progressDiv);
            
            // Remove progress
            setTimeout(() => progressDiv.remove(), 500);
            
            // Show success
            showToast('✅ Dosya yüklendi!', 'success');
            
            return data.file;
        } else {
            throw new Error(data.error || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        progressDiv.remove();
        showToast(`❌ Yükleme hatası: ${error.message}`, 'error');
        return null;
    }
}

/**
 * Create File Preview Element
 * @param {Object} file - File data from server
 * @returns {HTMLElement}
 */
function createFilePreview(file) {
    const div = document.createElement('div');
    div.className = 'file-preview-item';
    div.dataset.fileId = file.id;
    div.style.cssText = `
        position: relative;
        display: inline-block;
        margin: 10px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
        width: 150px;
        height: 150px;
        animation: fadeIn 0.3s ease-out;
    `;
    
    div.innerHTML = `
        <img src="${file.url}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover;">
        <button type="button" class="instant-delete-btn" data-file-id="${file.id}" style="
            position: absolute;
            top: 8px;
            right: 8px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            cursor: pointer;
            font-size: 18px;
            line-height: 1;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        ">×</button>
    `;
    
    // Add delete handler
    div.querySelector('.instant-delete-btn').addEventListener('click', function() {
        instantDeleteFile(file.id, div);
    });
    
    return div;
}

/**
 * Instant File Delete
 * @param {number} fileId - File ID to delete
 * @param {HTMLElement} element - Element to remove from DOM
 */
async function instantDeleteFile(fileId, element) {
    // Modern confirmation dialog
    const confirmed = await showConfirmDialog(
        'Delete Image?',
        'This action cannot be undone.',
        'Delete',
        'Cancel'
    );
    
    if (!confirmed) {
        return;
    }
    
    // Check if element still exists
    if (!element || !element.style) {
        console.error('Element not found or already deleted');
        return;
    }
    
    // Show loading
    element.style.opacity = '0.5';
    element.style.pointerEvents = 'none';
    
    try {
        const response = await fetch('/marketing/api/instant_delete_file/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ file_id: fileId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Fade out and remove
            element.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                element.remove();
                
                // Update primary badge after deletion
                if (typeof updatePrimaryBadge === 'function') {
                    updatePrimaryBadge();
                }
                
                // Update image order
                if (typeof updateImageOrder === 'function') {
                    updateImageOrder();
                }
            }, 300);
            
            showToast('🗑️ Dosya silindi!', 'success');
        } else {
            throw new Error(data.error || 'Delete failed');
        }
        
    } catch (error) {
        console.error('Delete error:', error);
        element.style.opacity = '1';
        element.style.pointerEvents = 'auto';
        showToast(`❌ Silme hatası: ${error.message}`, 'error');
    }
}

// Add fadeIn animation
style.textContent += `
    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }
    @keyframes fadeOut {
        from { opacity: 1; transform: scale(1); }
        to { opacity: 0; transform: scale(0.9); }
    }
`;

// Export for use in template and variants
window.instantUploadFile = instantUploadFile;
window.instantDeleteFile = instantDeleteFile;
window.showConfirmDialog = showConfirmDialog;
window.getCookie = getCookie;

// Note: Delete handlers are attached in product_form.html template
// and file_manager_modal.js - no need to attach here
