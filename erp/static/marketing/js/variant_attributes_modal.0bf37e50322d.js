
// ============== VARIANT ATTRIBUTES MODAL ==============
// Store variant attributes in memory (indexed by variant index)
let variantAttributesData = {};

// Get current product attributes from DOM (latest values)
function getCurrentProductAttributes() {
    const attributes = [];
    const cards = document.querySelectorAll('#product_attributes_container .attribute-card');
    
    cards.forEach(card => {
        const nameInput = card.querySelector('input[name="attribute_names[]"]');
        const valueInput = card.querySelector('input[name="attribute_values[]"]');
        
        if (nameInput && valueInput) {
            const name = nameInput.value.trim();
            const value = valueInput.value.trim();
            if (name && value) {
                attributes.push({ name, value });
            }
        }
    });
    
    return attributes;
}

// Open variant attributes modal
function openVariantAttributesModal(variantIndex, variantSku) {
    console.log(`Opening attributes modal for variant ${variantIndex}`);
    
    // Get LATEST product attributes from DOM (not from window.productAttributes which may be stale)
    const currentProductAttrs = getCurrentProductAttributes();
    console.log('Current product attributes from DOM:', currentProductAttrs);
    
    // Update the global productAttributes to ensure it's in sync
    if (typeof window.productAttributes !== 'undefined') {
        window.productAttributes = currentProductAttrs;
    }
    
    // Get existing variant-specific attributes
    const combinations = generateCombinations();
    const combo = combinations[variantIndex];
    const attrKey = Object.entries(combo)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, val]) => `${key}:${val}`)
        .join('|');
    
    const existingData = existingVariantData[attrKey] || {};
    const variantAttrs = variantAttributesData[variantIndex] || existingData.product_attributes || [];
    
    // Store in memory - keep existing variant-specific values if they exist
    if (!variantAttributesData[variantIndex]) {
        variantAttributesData[variantIndex] = JSON.parse(JSON.stringify(variantAttrs));
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = `variant_attr_modal_${variantIndex}`;
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.2s;
    `;
    
    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: #111827;">
                    <i class="fa fa-tags" style="color: #667eea;"></i> Variant Attributes
                </h3>
                <button onclick="closeVariantAttributesModal(${variantIndex})" style="background: transparent; border: none; font-size: 24px; color: #9ca3af; cursor: pointer; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 6px; transition: all 0.2s;" onmouseover="this.style.background='#f3f4f6'; this.style.color='#111827'" onmouseout="this.style.background='transparent'; this.style.color='#9ca3af'">&times;</button>
            </div>
            
            <div style="padding: 14px; background: #f0f9ff; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: start; gap: 10px;">
                <i class="fa fa-info-circle" style="color: #0ea5e9; margin-top: 2px;"></i>
                <div style="font-size: 13px; color: #0369a1; line-height: 1.5;">
                    <strong>Variant: ${variantSku}</strong><br>
                    Customize attributes for this specific variant. Leave empty to use product-level defaults.
                </div>
            </div>
            
            <div id="variant_attr_list_${variantIndex}" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
                <!-- Attributes will be rendered here -->
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <button onclick="closeVariantAttributesModal(${variantIndex})" style="padding: 10px 18px; background: #fff; color: #6b7280; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;" onmouseover="this.style.background='#f9fafb'; this.style.borderColor='#9ca3af'" onmouseout="this.style.background='#fff'; this.style.borderColor='#d1d5db'">
                    Cancel
                </button>
                <button onclick="saveVariantAttributes(${variantIndex})" style="padding: 10px 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2); transition: all 0.2s;" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 12px rgba(102, 126, 234, 0.3)'" onmouseout="this.style.transform=''; this.style.boxShadow='0 2px 8px rgba(102, 126, 234, 0.2)'">
                    <i class="fa fa-check"></i> Save
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => modal.style.opacity = '1', 10);
    
    // Render attributes with CURRENT product attributes from DOM
    renderVariantAttributesList(variantIndex, currentProductAttrs);
}

// Render variant attributes list
// currentProductAttrs is passed from openVariantAttributesModal (fresh from DOM)
function renderVariantAttributesList(variantIndex, currentProductAttrs) {
    const container = document.getElementById(`variant_attr_list_${variantIndex}`);
    if (!container) return;
    
    // Use passed product attributes or fallback to global
    const prodAttrs = currentProductAttrs || getCurrentProductAttributes() || productAttributes || [];
    const variantAttrs = variantAttributesData[variantIndex] || [];
    
    console.log('Rendering variant attributes list:');
    console.log('  Product attributes:', prodAttrs);
    console.log('  Variant-specific attributes:', variantAttrs);
    
    // Show product-level attributes as reference
    let html = '';
    
    if (prodAttrs && prodAttrs.length > 0) {
        prodAttrs.forEach((prodAttr, idx) => {
            const variantAttr = variantAttrs.find(a => a.name === prodAttr.name);
            const value = variantAttr ? variantAttr.value : '';
            
            html += `
                <div style="display: grid; grid-template-columns: 150px 1fr; gap: 12px; padding: 14px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; align-items: center;">
                    <div style="min-width: 0;">
                        <div style="font-size: 12px; font-weight: 500; color: #6b7280; margin-bottom: 4px;">Attribute</div>
                        <div style="font-weight: 500; color: #111827;">${prodAttr.name}</div>
                        <div style="font-size: 11px; color: #9ca3af; margin-top: 2px;">Default: ${prodAttr.value}</div>
                    </div>
                    <div style="min-width: 0;">
                        <label style="display: block; font-size: 12px; font-weight: 500; color: #6b7280; margin-bottom: 4px;">Variant Value</label>
                        <input type="text" 
                               class="variant-attr-input" 
                               data-attr-name="${prodAttr.name}"
                               value="${value}" 
                               placeholder="${prodAttr.value}" 
                               style="width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; box-sizing: border-box;">
                    </div>
                </div>
            `;
        });
    } else {
        html = `
            <div style="padding: 20px; text-align: center; color: #9ca3af; font-size: 14px;">
                <i class="fa fa-info-circle" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
                No product-level attributes defined. Add attributes in the Product Attributes section above.
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
        modal.style.opacity = '0';
        setTimeout(() => modal.remove(), 200);
    }
}
