
// ============== VARIANT ATTRIBUTES MODAL ==============
// Store variant attributes in memory (indexed by variant index)
let variantAttributesData = {};

// Open variant attributes modal
function openVariantAttributesModal(variantIndex, variantSku) {
    console.log(`Opening attributes modal for variant ${variantIndex}`);
    
    // Get existing attributes for this variant
    const combinations = generateCombinations();
    const combo = combinations[variantIndex];
    const attrKey = Object.entries(combo)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, val]) => `${key}:${val}`)
        .join('|');
    
    const existingData = existingVariantData[attrKey] || {};
    const variantAttrs = existingData.product_attributes || [];
    
    // Store in memory
    variantAttributesData[variantIndex] = JSON.parse(JSON.stringify(variantAttrs));
    
    // Create modal with modern styles
    const modal = document.createElement('div');
    modal.id = `variant_attr_modal_${variantIndex}`;
    modal.className = 'variant-attr-modal';
    
    modal.innerHTML = `
        <div class="variant-attr-modal-backdrop"></div>
        <div class="variant-attr-modal-content">
            <div class="variant-attr-modal-header">
                <h3>
                    <i class="fa fa-tags"></i> Variant Attributes
                </h3>
                <button class="modal-close-btn" onclick="closeVariantAttributesModal(${variantIndex})">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            
            <div class="variant-attr-info-box">
                <i class="fa fa-info-circle"></i>
                <div>
                    <strong>Variant: ${variantSku}</strong><br>
                    <small>Customize attributes for this specific variant. Leave empty to use product-level defaults.</small>
                </div>
            </div>
            
            <div class="variant-attr-list" id="variant_attr_list_${variantIndex}">
                <!-- Attributes will be rendered here -->
            </div>
            
            <div class="variant-attr-modal-footer">
                <button class="modal-btn modal-btn-secondary" onclick="closeVariantAttributesModal(${variantIndex})">
                    Cancel
                </button>
                <button class="modal-btn modal-btn-primary" onclick="saveVariantAttributes(${variantIndex})">
                    <i class="fa fa-check"></i> Save
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
    
    // Render attributes
    renderVariantAttributesList(variantIndex);
}

// Render variant attributes list
function renderVariantAttributesList(variantIndex) {
    const container = document.getElementById(`variant_attr_list_${variantIndex}`);
    if (!container) return;
    
    const attrs = variantAttributesData[variantIndex] || [];
    
    // Show product-level attributes as reference
    let html = '';
    
    if (productAttributes && productAttributes.length > 0) {
        productAttributes.forEach((prodAttr, idx) => {
            const variantAttr = attrs.find(a => a.name === prodAttr.name);
            const value = variantAttr ? variantAttr.value : '';
            
            html += `
                <div class="variant-attr-item">
                    <div class="variant-attr-name">
                        <div class="variant-attr-label">Attribute</div>
                        <div class="variant-attr-title">${prodAttr.name}</div>
                        <div class="variant-attr-default">Default: <strong>${prodAttr.value}</strong></div>
                    </div>
                    <div class="variant-attr-input-wrapper">
                        <label class="variant-attr-label">Variant Value</label>
                        <input type="text" 
                               class="variant-attr-input" 
                               data-attr-name="${prodAttr.name}"
                               value="${value}" 
                               placeholder="${prodAttr.value}">
                    </div>
                </div>
            `;
        });
    } else {
        html = `
            <div class="variant-attr-empty">
                <i class="fa fa-info-circle"></i>
                <p>No product-level attributes defined. Add attributes in the Product Attributes section.</p>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Save variant attributes
function saveVariantAttributes(variantIndex) {
    const inputs = document.querySelectorAll(`#variant_attr_list_${variantIndex} .variant-attr-input`);
    const attrs = [];
    
    inputs.forEach(input => {
        const name = input.getAttribute('data-attr-name');
        const value = input.value.trim();
        if (value) {
            attrs.push({ name, value });
        }
    });
    
    // Update memory
    variantAttributesData[variantIndex] = attrs;
    
    // Update existingVariantData for rendering
    const combinations = generateCombinations();
    const combo = combinations[variantIndex];
    const attrKey = Object.entries(combo)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, val]) => `${key}:${val}`)
        .join('|');
    
    if (existingVariantData[attrKey]) {
        existingVariantData[attrKey].product_attributes = attrs;
    } else {
        existingVariantData[attrKey] = { product_attributes: attrs };
    }
    
    // Update button counter
    const counter = document.getElementById(`attr_count_${variantIndex}`);
    if (counter) {
        counter.textContent = attrs.length;
    }
    
    // Close modal
    closeVariantAttributesModal(variantIndex);
    
    showToast(`✅ Attributes saved for variant`, 'success');
}

// Close variant attributes modal
function closeVariantAttributesModal(variantIndex) {
    const modal = document.getElementById(`variant_attr_modal_${variantIndex}`);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// Add CSS styles for variant attributes modal
if (!document.getElementById('variant-attr-modal-styles')) {
    const style = document.createElement('style');
    style.id = 'variant-attr-modal-styles';
    style.textContent = `
    .variant-attr-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
        padding: 20px;
    }
    
    .variant-attr-modal.show {
        opacity: 1;
    }
    
    .variant-attr-modal-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        z-index: -1;
        border-radius: 0;
    }
    
    .variant-attr-modal-content {
        background: white;
        border-radius: 16px;
        max-width: 650px;
        width: 100%;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        overflow: hidden;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from {
            transform: translateY(20px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .variant-attr-modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px;
        border-bottom: 1px solid #e5e7eb;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    .variant-attr-modal-header h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #111827;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .variant-attr-modal-header i {
        color: #667eea;
    }
    
    .modal-close-btn {
        background: transparent;
        border: none;
        font-size: 24px;
        color: #9ca3af;
        cursor: pointer;
        padding: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    .modal-close-btn:hover {
        background: white;
        color: #111827;
    }
    
    .variant-attr-info-box {
        margin: 20px 24px;
        padding: 14px 16px;
        background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
        border: 1px solid #bfdbfe;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        font-size: 13px;
        color: #1e40af;
        display: flex;
        align-items: flex-start;
        gap: 12px;
        line-height: 1.5;
    }
    
    .variant-attr-info-box i {
        color: #3b82f6;
        margin-top: 2px;
        flex-shrink: 0;
    }
    
    .variant-attr-info-box strong {
        color: #1e40af;
    }
    
    .variant-attr-info-box small {
        display: block;
        color: #0369a1;
    }
    
    .variant-attr-list {
        flex: 1;
        overflow-y: auto;
        padding: 0 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding-top: 16px;
        padding-bottom: 16px;
    }
    
    .variant-attr-item {
        display: grid;
        grid-template-columns: 150px 1fr;
        gap: 16px;
        padding: 16px;
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        transition: all 0.2s ease;
    }
    
    .variant-attr-item:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
    }
    
    .variant-attr-name {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .variant-attr-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .variant-attr-title {
        font-weight: 600;
        color: #111827;
        font-size: 14px;
    }
    
    .variant-attr-default {
        font-size: 12px;
        color: #6b7280;
    }
    
    .variant-attr-default strong {
        color: #111827;
    }
    
    .variant-attr-input-wrapper {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .variant-attr-input {
        width: 100%;
        padding: 12px 14px;
        border: 1.5px solid #e2e8f0;
        border-radius: 8px;
        font-size: 14px;
        background: white;
        transition: all 0.2s ease;
        box-sizing: border-box;
    }
    
    .variant-attr-input:focus {
        outline: none;
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .variant-attr-input::placeholder {
        color: #94a3b8;
    }
    
    .variant-attr-empty {
        padding: 40px 24px;
        text-align: center;
        color: #94a3b8;
    }
    
    .variant-attr-empty i {
        font-size: 40px;
        margin-bottom: 12px;
        display: block;
        opacity: 0.6;
    }
    
    .variant-attr-empty p {
        margin: 0;
        font-size: 14px;
        line-height: 1.5;
    }
    
    .variant-attr-modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        padding: 20px 24px;
        border-top: 1px solid #e5e7eb;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    .modal-btn {
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .modal-btn-secondary {
        background: white;
        color: #6b7280;
        border: 1px solid #d1d5db;
    }
    
    .modal-btn-secondary:hover {
        background: #f9fafb;
        border-color: #9ca3af;
    }
    
    .modal-btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
    }
    
    .modal-btn-primary:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
    }
    
    @media (max-width: 768px) {
        .variant-attr-modal-content {
            max-height: 90vh;
            width: 95vw;
        }
        
        .variant-attr-item {
            grid-template-columns: 1fr;
            gap: 12px;
        }
        
        .variant-attr-modal-header,
        .variant-attr-modal-footer,
        .variant-attr-list {
            padding-left: 16px;
            padding-right: 16px;
        }
    }
    `;
    document.head.appendChild(style);
}
