/**
 * Unsaved Changes Handler
 * Prevents accidental data loss when closing sidebars with unsaved form data
 */

// Track form changes
let formHasChanges = false;
let currentFormId = null;
let isSubmitting = false;

// Initialize tracking when form is opened
function initializeFormTracking(formId) {
  formHasChanges = false;
  currentFormId = formId;
  isSubmitting = false;
  
  const form = document.getElementById(formId);
  if (!form) return;
  
  // Track all input changes
  const inputs = form.querySelectorAll('input, textarea, select');
  inputs.forEach(input => {
    // Store initial value
    input.dataset.initialValue = input.value || '';
    
    // Listen for changes
    input.addEventListener('input', () => {
      formHasChanges = true;
    });
    
    input.addEventListener('change', () => {
      formHasChanges = true;
    });
  });
  
  // Track form submission
  form.addEventListener('submit', () => {
    isSubmitting = true;
  });
}

// Reset form tracking
function resetFormTracking() {
  formHasChanges = false;
  currentFormId = null;
  isSubmitting = false;
}

// Show unsaved changes modal
function showUnsavedChangesModal(onDiscard, onReturn) {
  // Create modal overlay
  const overlay = document.createElement('div');
  overlay.className = 'unsaved-changes-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    z-index: 10001;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s ease;
  `;
  
  // Create modal dialog
  const dialog = document.createElement('div');
  dialog.className = 'unsaved-changes-dialog';
  dialog.style.cssText = `
    background: white;
    border-radius: 16px;
    max-width: 480px;
    width: 90%;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    animation: slideUp 0.3s ease;
    overflow: hidden;
  `;
  
  dialog.innerHTML = `
    <div style="padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <div style="width: 64px; height: 64px; margin: 0 auto 16px; background: #fef3c7; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
          <i class="fa fa-exclamation-triangle" style="font-size: 28px; color: #f59e0b;"></i>
        </div>
        <h3 style="margin: 0 0 12px; font-size: 20px; font-weight: 700; color: #111827;">
          You have unsaved data!
        </h3>
        <p style="margin: 0; font-size: 15px; color: #6b7280; line-height: 1.6;">
          The form you just closed had unsaved changes. Are you sure you want to close the form and discard the changes?
        </p>
      </div>
      
      <div style="display: flex; gap: 12px; justify-content: center;">
        <button 
          type="button"
          class="btn-return-to-form"
          style="
            flex: 1;
            padding: 12px 24px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
          "
          onmouseover="this.style.background='#2563eb'"
          onmouseout="this.style.background='#3b82f6'">
          Return to the form
        </button>
        
        <button 
          type="button"
          class="btn-discard-changes"
          style="
            flex: 1;
            padding: 12px 24px;
            background: #f3f4f6;
            color: #374151;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
          "
          onmouseover="this.style.background='#e5e7eb'"
          onmouseout="this.style.background='#f3f4f6'">
          Discard changes
        </button>
      </div>
    </div>
  `;
  
  overlay.appendChild(dialog);
  document.body.appendChild(overlay);
  
  // Add event listeners
  const btnReturn = dialog.querySelector('.btn-return-to-form');
  const btnDiscard = dialog.querySelector('.btn-discard-changes');
  
  btnReturn.addEventListener('click', () => {
    overlay.remove();
    if (onReturn) onReturn();
  });
  
  btnDiscard.addEventListener('click', () => {
    overlay.remove();
    resetFormTracking();
    if (onDiscard) onDiscard();
  });
  
  // Close on Escape key
  const escapeHandler = (e) => {
    if (e.key === 'Escape') {
      overlay.remove();
      if (onReturn) onReturn();
      document.removeEventListener('keydown', escapeHandler);
    }
  };
  document.addEventListener('keydown', escapeHandler);
  
  // Add animation styles if not present
  if (!document.getElementById('unsaved-changes-animations')) {
    const style = document.createElement('style');
    style.id = 'unsaved-changes-animations';
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes slideUp {
        from { 
          opacity: 0;
          transform: translateY(20px) scale(0.95);
        }
        to { 
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }
    `;
    document.head.appendChild(style);
  }
}

// Wrap original close functions
function wrapCloseFunctionWithCheck(originalCloseFunction, formId) {
  return function() {
    // If form is being submitted, just close normally
    if (isSubmitting) {
      resetFormTracking();
      originalCloseFunction();
      return;
    }
    
    // If form has changes, show confirmation
    if (formHasChanges && currentFormId === formId) {
      showUnsavedChangesModal(
        // onDiscard
        () => {
          originalCloseFunction();
        },
        // onReturn
        () => {
          // Do nothing, user stays in form
        }
      );
    } else {
      // No changes, close normally
      resetFormTracking();
      originalCloseFunction();
    }
  };
}

// Export for use in base.html
window.initializeFormTracking = initializeFormTracking;
window.resetFormTracking = resetFormTracking;
window.wrapCloseFunctionWithCheck = wrapCloseFunctionWithCheck;
window.formChangeTracker = {
  hasChanges: () => formHasChanges,
  setSubmitting: () => { isSubmitting = true; },
  reset: resetFormTracking
};
