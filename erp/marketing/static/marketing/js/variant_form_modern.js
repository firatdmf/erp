// Words the page translates for this script (see components/variant_form.html).
const VF_TEXT = window.VF_TEXT || {};
// Figures written by script follow the app's language (<html lang>), like
// the ones the server renders: 1,234.50 in English, 1.234,50 in Turkish.
window.fmtNum = window.fmtNum || function (n, decimals) {
  if (decimals == null) decimals = 2;
  var tr = /^tr\b/i.test(document.documentElement.lang || '');
  return (Number(n) || 0).toLocaleString(tr ? 'tr-TR' : 'en-US',
    { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

// Modern Variant Form System - Auto-updating with real-time table generation
let optionCounter = 0;
let variantData = {};
let variantImages = {}; // Store images for each variant: { variantIndex: { images: [], primaryIndex: 0 } }
let currentEditingVariantIndex = null;
let productAttributes = []; // Product-level attributes to show in variant table

// ── SKU rule for NEW products: PARENT.VALUE-VALUE (K24644.BEYAZ-140) ──
// The product SKU, a dot, then the variant's option values in capitals
// joined by dashes. The product form sets data-sku-rule only when creating;
// existing products keep the SKUs they have. ProductForm enforces the same
// rule on the server.
function skuRuleOn() {
    return !!document.querySelector('#product_form[data-sku-rule]');
}
function skuRuleMsg(key) {
    const form = document.getElementById('product_form');
    return (form && form.dataset[key]) || '';
}
function skuParent() {
    return (document.getElementById('id_sku')?.value || '').trim().toUpperCase();
}
function skuSuffixClean(text) {
    return String(text || '').trim().toUpperCase().replace(/\s+/g, '_');
}
function skuSuffixFromValues(values) {
    return values.map(skuSuffixClean).filter(Boolean).join('-');
}
// Without a product SKU yet, a variant holds just its suffix; the prefix
// is written in as soon as the product SKU is typed.
function skuJoin(parent, suffix) {
    return parent ? `${parent}.${suffix}` : suffix;
}
function skuSuffixOf(sku, parent) {
    sku = sku || '';
    if (parent && sku.startsWith(parent + '.')) return sku.slice(parent.length + 1);
    return parent ? null : sku;
}

// Keep the product SKU in capitals and dot-free, and carry every variant
// SKU along when it changes. A variant SKU that no longer starts with the
// old prefix was typed by hand some other way and is left alone.
document.addEventListener('DOMContentLoaded', () => {
    const parentInput = document.getElementById('id_sku');
    if (!parentInput || !skuRuleOn()) return;
    let lastParent = skuParent();
    parentInput.addEventListener('input', () => {
        const raw = parentInput.value;
        const clean = raw.toUpperCase().replace(/\./g, '');
        if (clean !== raw) {
            const caret = parentInput.selectionStart - (raw.length - clean.length);
            parentInput.value = clean;
            parentInput.setSelectionRange(caret, caret);
        }
        const next = skuParent();
        if (next === lastParent) return;
        document.querySelectorAll('input[name^="variant_sku_"]').forEach(inp => {
            const suffix = skuSuffixOf(inp.value, lastParent);
            if (suffix !== null) inp.value = skuJoin(next, suffix);
        });
        lastParent = next;
    });
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('variant_component')) {
        // Load product attributes
        loadProductAttributes();
        // Load existing variants if in edit mode
        loadExistingVariants();
        // A new product starts as a single item.
        refreshSingleItem();
        updateVariantRowsBar();
    }
});

// Load product attributes from backend data
function loadProductAttributes() {
    const productAttributesData = window.product_attributes_data;

    if (!productAttributesData || productAttributesData === '[]' || productAttributesData === '') {
        productAttributes = [];
        return;
    }

    try {
        productAttributes = JSON.parse(productAttributesData);
        console.log('Loaded product attributes:', productAttributes);
    } catch (e) {
        console.error('Error loading product attributes:', e);
        productAttributes = [];
    }
}

// Load existing variants from backend data
function loadExistingVariants() {
    const variantListData = window.product_variant_list_data;
    const variantOptionsData = window.product_variant_options_data;

    console.log('Loading existing variants...');
    console.log('Variant list:', variantListData);
    console.log('Variant options:', variantOptionsData);

    if (!variantOptionsData || variantOptionsData === '[]' || variantOptionsData === '') {
        // A product sold as one item has one variant and no options. Draw
        // it all the same: its price, cost and SKU live on it, and nowhere
        // else on the page.
        if (variantListData && variantListData !== '[]' && variantListData !== '') {
            loadExistingVariantImages();
            updateVariantTable();
        }
        return;
    }

    try {
        const options = JSON.parse(variantOptionsData);
        console.log('Parsed options:', options);

        if (options && options.length > 0) {
            // Show variant section
            document.getElementById('add_variant_trigger').style.display = 'none';
            document.getElementById('variant_component').style.display = 'block';

            // Create options from existing data
            options.forEach(option => {
                optionCounter++;
                const optionId = `option_${optionCounter}`;

                // IMPORTANT: Set variantData with actual values FIRST
                variantData[optionId] = {
                    name: option.name,
                    values: option.values.filter(v => v && v.trim()) // Only non-empty values
                };

                console.log(`Created ${optionId}:`, variantData[optionId]);

                // Create option card HTML
                const optionHTML = `
                    <div class="variant_option_card" id="${optionId}" data-option-id="${optionId}">
                        <div class="option_header">
                            <span class="drag_handle"><i class="fa fa-grip-vertical"></i></span>
                            <div class="option_name_input">
                                <label>${(window.VARIANT_T && window.VARIANT_T.option_name) || 'Option Name'}</label>
                                <input type="text"
                                       placeholder="${(window.VARIANT_T && window.VARIANT_T.option_placeholder) || 'e.g. Size, Color'}"
                                       value="${option.name}"
                                       oninput="updateOptionName('${optionId}', this.value)"
                                       class="option_name_field">
                            </div>
                        </div>
                        <div class="option_values_section">
                            <label>${(window.VARIANT_T && window.VARIANT_T.option_values) || 'Option Values'}</label>
                            <div class="option_values_list" id="${optionId}_values"></div>
                            <button type="button" class="btn_add_value" onclick="addValueField('${optionId}')">
                                <i class="fa fa-plus"></i> ${(window.VARIANT_T && window.VARIANT_T.add_value) || 'Add another value'}
                            </button>
                        </div>
                        <div class="option_actions">
                            <button type="button" class="btn_remove_option" onclick="removeOption('${optionId}')">
                                ${(window.VARIANT_T && window.VARIANT_T.delete) || 'Delete'}
                            </button>
                        </div>
                    </div>
                `;

                document.getElementById('variant_options_list').insertAdjacentHTML('beforeend', optionHTML);

                // Add existing values AND populate variantData
                option.values.forEach((value, index) => {
                    if (value) {  // Only add non-empty values
                        addValueField(optionId, value);
                        // Manually trigger update to populate variantData array properly
                        // Use setTimeout to ensure DOM is ready
                        setTimeout(() => {
                            const input = document.querySelector(`#${optionId}_values [data-value-index="${index}"] .value_input`);
                            if (input) {
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                        }, 10);
                    }
                });

                // Don't add empty field - user can use "Add another value" button or type will auto-add
            });

            // Load variant data (cost, price, sku, images, etc.) BEFORE rendering the table
            // so that generateRowHTML can populate hidden inputs with existing values
            loadExistingVariantImages();
            applyExistingAttributeValueImages();

            // Update table with existing variants
            console.log('About to update variant table...');
            console.log('Current variantData:', variantData);

            // Debug: Check what combinations are generated
            const testCombinations = generateCombinations();
            console.log('Generated combinations:', testCombinations);
            console.log('Number of combinations:', testCombinations.length);

            updateVariantTable();
            updateGroupingOptions();

            // Check if table is visible
            const table = document.getElementById('variant_table');
            const grouping = document.getElementById('variant_grouping');
            console.log('Table display:', table ? table.style.display : 'null');
            console.log('Grouping display:', grouping ? grouping.style.display : 'null');
        }
    } catch (e) {
        console.error('Error loading existing variants:', e);
        console.error('Stack trace:', e.stack);
    }
}

// Load existing variant data from backend
function loadExistingVariantImages() {
    const variantListData = window.product_variant_list_data;
    const variantFilesData = window.variant_files_json_data;

    if (!variantListData || variantListData === '[]' || variantListData === '') {
        return;
    }

    try {
        const variants = JSON.parse(variantListData);
        console.log('Loading existing variant data:', variants);

        // One row per saved variant, holding the values it has — a variant
        // without one of the options simply has no value for it.
        variantRows = [];
        variants.forEach((variant, index) => {
            const row = {};
            Object.entries(variant.variant_attribute_values || {}).forEach(([name, value]) => {
                if (name && value !== null && value !== undefined && String(value).trim()) row[name] = String(value);
            });
            variantRows.push(row);

            // A variant with priced stock on hand costs what that stock
            // cost on average — computed, so the modal shows it locked.
            if (variant.stock_cost !== null && variant.stock_cost !== undefined) {
                (window.computedVariantCosts = window.computedVariantCosts || {})[variant.variant_sku] = variant.stock_cost;
            }

            existingVariantData[index] = {
                variant_id: variant.variant_id,
                price: variant.variant_price,
                cost: variant.variant_cost,
                quantity: variant.variant_quantity,
                sku: variant.variant_sku,
                barcode: variant.variant_barcode,
                featured: variant.variant_featured,
                product_attributes: variant.product_attributes || [],
                images: []
            };

            if (variant.product_attributes && variant.product_attributes.length > 0
                    && typeof variantAttributesData !== 'undefined') {
                variantAttributesData[index] = variant.product_attributes;
            }
        });

        // Load variant images if available
        if (variantFilesData && variantFilesData !== '{}') {
            const filesDict = JSON.parse(variantFilesData);
            variants.forEach((variant, index) => {
                const files = filesDict[variant.variant_sku];
                if (files && files.length > 0 && existingVariantData[index]) {
                    existingVariantData[index].images = files.map(f => ({
                        id: f.id,
                        url: f.url,
                        name: f.name || f.url.split('/').pop()
                    }));
                }
            });
        }

        console.log('Loaded existing variant data:', existingVariantData);
    } catch (e) {
        console.error('Error loading variant data:', e);
    }
}

// Apply previously-saved attribute value images (color swatches) to variantData.
// Called after options are rendered so that imagesByValue is set per option.
function applyExistingAttributeValueImages() {
    const raw = window.attribute_value_images_data;
    if (!raw || raw === '{}') return;
    let imagesByAttr;
    try { imagesByAttr = JSON.parse(raw); } catch (e) { return; }
    if (!imagesByAttr || !Object.keys(imagesByAttr).length) return;

    Object.keys(variantData).forEach(optId => {
        const optName = (variantData[optId].name || '').toLowerCase().trim();
        if (!optName || !imagesByAttr[optName]) return;
        if (!variantData[optId].imagesByValue) variantData[optId].imagesByValue = {};
        Object.entries(imagesByAttr[optName]).forEach(([val, payload]) => {
            // Accept both new {name, url} and legacy "url" string
            if (typeof payload === 'string') {
                variantData[optId].imagesByValue[val] = { url: payload, id: null, display_name: val };
            } else if (payload && typeof payload === 'object') {
                variantData[optId].imagesByValue[val] = {
                    url: payload.url || '',
                    id: null,
                    display_name: payload.name || val,
                };
            }
        });
    });
    console.log('Loaded attribute value images:', imagesByAttr);

    // Re-render value field thumbnails for each option
    Object.keys(variantData).forEach(optId => {
        refreshColorOptionState(optId);
        const valuesList = document.getElementById(`${optId}_values`);
        if (!valuesList) return;
        Array.from(valuesList.children).forEach((wrapper, idx) => {
            restoreColorValueImage(optId, idx);
        });
    });
}


// Show variant section and initialize
function showVariantSection() {
    document.getElementById('add_variant_trigger').style.display = 'none';
    document.getElementById('variant_component').style.display = 'block';
    if (optionCounter === 0) {
        addNewOption(); // Add first option automatically
    }
    toggleProductImagesSection();
}

// Toggle product images section based on variants
function toggleProductImagesSection() {
    const productImagesContent = document.getElementById('product_images_content');
    const variantsImageNotice = document.getElementById('variants_image_notice');

    // Always show product images upload, hide notice (User request: allow manual primary image selection)
    if (productImagesContent) productImagesContent.style.display = 'block';
    if (variantsImageNotice) variantsImageNotice.style.display = 'none';
}

// Add a new option (e.g., Color, Size)
function addNewOption() {
    optionCounter++;
    const optionId = `option_${optionCounter}`;
    variantData[optionId] = { name: '', values: [] };

    const optionHTML = `
        <div class="variant_option_card" id="${optionId}" data-option-id="${optionId}">
            <div class="option_header">
                <span class="drag_handle"><i class="fa fa-grip-vertical"></i></span>
                <div class="option_name_input">
                    <label>${(window.VARIANT_T && window.VARIANT_T.option_name) || 'Option Name'}</label>
                    <input type="text"
                           placeholder="${(window.VARIANT_T && window.VARIANT_T.option_placeholder) || 'e.g. Size, Color'}"
                           oninput="updateOptionName('${optionId}', this.value)"
                           class="option_name_field">
                </div>
            </div>
            <div class="option_values_section">
                <label>${(window.VARIANT_T && window.VARIANT_T.option_values) || 'Option Values'}</label>
                <div class="option_values_list" id="${optionId}_values"></div>
                <button type="button" class="btn_add_value" onclick="addValueField('${optionId}')">
                    <i class="fa fa-plus"></i> ${(window.VARIANT_T && window.VARIANT_T.add_value) || 'Add another value'}
                </button>
            </div>
            <div class="option_actions">
                <button type="button" class="btn_remove_option" onclick="removeOption('${optionId}')">
                    ${(window.VARIANT_T && window.VARIANT_T.delete) || 'Delete'}
                </button>
            </div>
        </div>
    `;

    document.getElementById('variant_options_list').insertAdjacentHTML('beforeend', optionHTML);
    addValueField(optionId); // Add first value field
}

// Add a value input field
function addValueField(optionId, value = '') {
    const valuesList = document.getElementById(`${optionId}_values`);
    if (!valuesList) return;

    const valueIndex = valuesList.children.length;

    const valueHTML = `
        <div class="value_field_wrapper" data-value-index="${valueIndex}">
            <span class="drag_handle_small"><i class="fa fa-grip-vertical"></i></span>
            <input type="text"
                   placeholder="${valueIndex === 0 ? '' : ((window.VARIANT_T && window.VARIANT_T.add_value) || 'Add another value')}"
                   value="${value}"
                   oninput="updateOptionValue('${optionId}', ${valueIndex}, this.value)"
                   class="value_input">
            <div class="value_color_image" data-option-id="${optionId}" data-value-index="${valueIndex}">
                <input type="file" accept="image/*" style="display:none;"
                       onchange="onColorValueImagePick('${optionId}', ${valueIndex}, this)">
                <button type="button" class="btn_color_image" title="Set image for this color"
                        onclick="this.previousElementSibling.click()">
                    <i class="fa fa-image"></i>
                </button>
                <div class="color_image_thumb" style="display:none;">
                    <img alt="">
                    <button type="button" class="btn_remove_color_image" title="Remove image"
                            onclick="onColorValueImageRemove('${optionId}', ${valueIndex})">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            </div>
            <button type="button" class="btn_remove_value" onclick="removeValue('${optionId}', ${valueIndex})">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    `;

    valuesList.insertAdjacentHTML('beforeend', valueHTML);

    // Restore thumbnail if we already have an image stored for this value
    restoreColorValueImage(optionId, valueIndex);
}

// ─── Color attribute image upload ───────────────────────────────
// Storage: variantData[optionId].imagesByValue = { 'red': { url, id }, ... }
// Visible only when option name is 'color' / 'renk'

function isColorOption(optionId) {
    const name = (variantData[optionId] && variantData[optionId].name) || '';
    const n = name.toLowerCase().trim();
    return n === 'color' || n === 'colour' || n === 'renk';
}

function refreshColorOptionState(optionId) {
    const card = document.getElementById(optionId);
    if (!card) return;
    card.classList.toggle('is-color-option', isColorOption(optionId));
}

// Normalize a value the same way Django's ProductVariantAttributeValue.save() does
function normalizeAttrValue(s) {
    return (s || '').toString().trim().toLowerCase().replace(/\s+/g, '_');
}

function restoreColorValueImage(optionId, valueIndex) {
    const data = variantData[optionId];
    if (!data || !data.imagesByValue) return;
    const valueText = (data.values && data.values[valueIndex]) || '';
    if (!valueText) return;
    // Try normalized key first (DB format), then raw (in-session format)
    const norm = normalizeAttrValue(valueText);
    const stored = data.imagesByValue[norm] || data.imagesByValue[valueText.trim()];
    if (stored && stored.url) {
        showColorValueThumb(optionId, valueIndex, stored.url);
    }
}

function showColorValueThumb(optionId, valueIndex, url) {
    const wrapper = document.querySelector(
        `.value_color_image[data-option-id="${optionId}"][data-value-index="${valueIndex}"]`
    );
    if (!wrapper) return;
    const btn = wrapper.querySelector('.btn_color_image');
    const thumb = wrapper.querySelector('.color_image_thumb');
    const img = thumb.querySelector('img');
    img.src = url;
    btn.style.display = 'none';
    thumb.style.display = 'inline-flex';
}

function hideColorValueThumb(optionId, valueIndex) {
    const wrapper = document.querySelector(
        `.value_color_image[data-option-id="${optionId}"][data-value-index="${valueIndex}"]`
    );
    if (!wrapper) return;
    const btn = wrapper.querySelector('.btn_color_image');
    const thumb = wrapper.querySelector('.color_image_thumb');
    btn.style.display = '';
    thumb.style.display = 'none';
}

// Resize an image File to a square TARGET×TARGET PNG via Canvas
function resizeImageTo40(file, target = 40) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Could not read file'));
        reader.onload = () => {
            const img = new Image();
            img.onerror = () => reject(new Error('Could not load image'));
            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = target;
                canvas.height = target;
                const ctx = canvas.getContext('2d');
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';

                // Cover-fit: scale up to fill, crop center
                const ratio = Math.max(target / img.width, target / img.height);
                const w = img.width * ratio;
                const h = img.height * ratio;
                const dx = (target - w) / 2;
                const dy = (target - h) / 2;
                ctx.drawImage(img, dx, dy, w, h);

                canvas.toBlob((blob) => {
                    if (!blob) return reject(new Error('Resize failed'));
                    // Preserve filename, swap extension to .png
                    const baseName = (file.name || 'swatch').replace(/\.[^.]+$/, '');
                    const newFile = new File([blob], baseName + '_40.png', { type: 'image/png' });
                    resolve(newFile);
                }, 'image/png', 0.92);
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });
}

async function onColorValueImagePick(optionId, valueIndex, fileInput) {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;

    const data = variantData[optionId];
    if (!data) return;
    const valueText = ((data.values && data.values[valueIndex]) || '').trim();
    if (!valueText) {
        showToast('Enter the color value first', 'warning');
        fileInput.value = '';
        return;
    }

    // Auto-resize to 40×40 PNG before upload
    let uploadFile = file;
    try {
        if (file.type.startsWith('image/')) {
            uploadFile = await resizeImageTo40(file, 40);
            console.log(`[color] resized ${file.name}: ${file.size}B → ${uploadFile.size}B (40×40)`);
        }
    } catch (e) {
        console.warn('Resize failed, uploading original:', e);
    }

    // Upload using existing instant_upload endpoint when product exists,
    // otherwise temp_upload (create mode)
    const productEditMatch = window.location.pathname.match(/\/product_edit\/(\d+)\//)?.[1];
    const isCreateMode = window.location.pathname.includes('/product_create/');

    const formData = new FormData();
    formData.append('file', uploadFile);
    let url = '';
    let id = null;

    try {
        if (productEditMatch) {
            formData.append('product_id', productEditMatch);
            const res = await fetch('/marketing/api/instant_upload_file/', {
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : '' },
                body: formData,
            });
            const data2 = await res.json();
            if (!data2.success) throw new Error(data2.error || 'Upload failed');
            url = data2.file.url;
            id = data2.file.id;
        } else if (isCreateMode) {
            formData.append('file_type', 'color_image');
            formData.append('variant_temp_id', `color_${optionId}_${valueIndex}`);
            const res = await fetch('/marketing/api/temp_upload_file/', {
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : '' },
                body: formData,
            });
            const data2 = await res.json();
            if (!data2.success) throw new Error(data2.error || 'Upload failed');
            url = data2.file_data.url;
            id = data2.file_data.public_id;
        } else {
            throw new Error('Save the product first');
        }

        // Persist into variantData using normalized key (matches DB format)
        // Keep the original case-preserved name as display_name.
        if (!data.imagesByValue) data.imagesByValue = {};
        const key = normalizeAttrValue(valueText);
        data.imagesByValue[key] = { url, id, display_name: valueText };

        showColorValueThumb(optionId, valueIndex, url);
        showToast(`Image set for ${valueText}`, 'success');
    } catch (e) {
        console.error(e);
        showToast('Upload error: ' + e.message, 'error');
    } finally {
        fileInput.value = '';
    }
}

function onColorValueImageRemove(optionId, valueIndex) {
    const data = variantData[optionId];
    if (!data) return;
    const valueText = ((data.values && data.values[valueIndex]) || '').trim();
    if (data.imagesByValue) {
        delete data.imagesByValue[normalizeAttrValue(valueText)];
        delete data.imagesByValue[valueText];
    }
    hideColorValueThumb(optionId, valueIndex);
}

window.onColorValueImagePick = onColorValueImagePick;
window.onColorValueImageRemove = onColorValueImageRemove;

// Update option name
function updateOptionName(optionId, name) {
    if (!variantData[optionId]) return;
    // The rows carry the option under its name, so they follow a rename.
    // A name cleared on the way to a new one leaves them as they are.
    const carried = (optionId in rowOptionNames) ? rowOptionNames[optionId] : (variantData[optionId].name || '');
    const next = (name || '').trim();
    if (next) {
        if (carried && carried !== next) {
            variantRows.forEach(row => {
                if (Object.prototype.hasOwnProperty.call(row, carried)) {
                    row[next] = row[carried];
                    delete row[carried];
                }
            });
        }
        rowOptionNames[optionId] = next;
    } else {
        rowOptionNames[optionId] = carried;
    }
    variantData[optionId].name = name;
    refreshColorOptionState(optionId);
    updateVariantTable();
    updateGroupingOptions();
}

// Track original values for each option (before any edits in this session)
// Format: { optionId: { valueIndex: originalValue } }
let originalOptionValues = {};

// Update option value
function updateOptionValue(optionId, valueIndex, value) {
    if (!variantData[optionId]) return;

    // Ensure values array exists
    if (!variantData[optionId].values) {
        variantData[optionId].values = [];
    }

    // Track original value on first edit (for rename tracking)
    if (!originalOptionValues[optionId]) {
        originalOptionValues[optionId] = {};
    }
    const oldValue = variantData[optionId].values[valueIndex];

    // Store original value if this is the first time we're editing this field
    if (oldValue && oldValue.trim() && originalOptionValues[optionId][valueIndex] === undefined) {
        originalOptionValues[optionId][valueIndex] = oldValue.trim();
    }

    // Track rename mapping: original value -> current value
    const originalValue = originalOptionValues[optionId][valueIndex];
    if (originalValue && value.trim() && originalValue !== value.trim()) {
        // Store rename mapping
        if (!pendingValueRenames[optionId]) {
            pendingValueRenames[optionId] = {};
        }
        const optionName = variantData[optionId].name;
        if (optionName) {
            pendingValueRenames[optionId][originalValue] = value.trim();
            console.log(`Tracking rename: ${optionName}:${originalValue} -> ${value.trim()}`);
        }
    }

    // Rows that have this value follow a rename of it — keystroke by
    // keystroke. A value cleared on the way to a new one leaves them be.
    const rowNames = (rowOptionValues[optionId] = rowOptionValues[optionId] || {});
    const carriedValue = (valueIndex in rowNames) ? rowNames[valueIndex] : (oldValue || '').trim();
    const nextValue = (value || '').trim();
    const optionNameNow = variantData[optionId].name;
    if (nextValue) {
        if (carriedValue && carriedValue !== nextValue && optionNameNow) {
            variantRows.forEach(row => {
                if (row[optionNameNow] === carriedValue) row[optionNameNow] = nextValue;
            });
        }
        rowNames[valueIndex] = nextValue;
    } else {
        rowNames[valueIndex] = carriedValue;
    }

    // Store the new value
    variantData[optionId].values[valueIndex] = value;

    // Auto-add new field if this is the last field and has value
    const valuesList = document.getElementById(`${optionId}_values`);
    if (!valuesList) return;

    const isLastField = valueIndex === valuesList.children.length - 1;

    if (value.trim() && isLastField) {
        addValueField(optionId);
    }

    // DON'T update table if value is being cleared (user might be renaming)
    // User must click trash icon to actually delete a value
    // Only update table if:
    // 1. Value has content (rename or new value)
    // 2. OR this is a new field being filled for the first time (no original value)
    if (value.trim() || !originalValue) {
        updateVariantTable();
    }
}

// Remove option
function removeOption(optionId) {
    const removedName = (optionId in rowOptionNames) ? rowOptionNames[optionId] : (variantData[optionId] || {}).name;
    if (removedName) variantRows.forEach(row => { delete row[removedName]; });
    delete rowOptionNames[optionId];
    delete rowOptionValues[optionId];
    delete variantData[optionId];
    const element = document.getElementById(optionId);
    if (element) element.remove();
    updateVariantTable();
    updateGroupingOptions();

    // Check if all options are deleted - restore Add Product Variants button
    if (Object.keys(variantData).length === 0) {
        const trigger = document.getElementById('add_variant_trigger');
        const component = document.getElementById('variant_component');
        if (trigger) trigger.style.display = 'block';
        if (component) component.style.display = 'none';
    }
}

// Remove value - same logic as deleteVariantRow but for multiple variants
// Remove value - Re-implemented to fix index shifting issues
function removeValue(optionId, valueIndex) {
    const valuesList = document.getElementById(`${optionId}_values`);
    if (!valuesList) return;

    const wrapper = valuesList.querySelector(`[data-value-index="${valueIndex}"]`);
    const deletedValue = wrapper ? wrapper.querySelector('.value_input')?.value : '';

    // If empty value, just remove from DOM and update indices
    if (!deletedValue || !deletedValue.trim()) {
        if (wrapper) wrapper.remove();
        reindexDomFields(valuesList, optionId);
        // Also remove from variantData if it exists there as empty string
        if (variantData[optionId] && variantData[optionId].values) {
            // Check if the value at this index is indeed empty/undefined before splicing
            if (!variantData[optionId].values[valueIndex] || !variantData[optionId].values[valueIndex].trim()) {
                variantData[optionId].values.splice(valueIndex, 1);
            }
        }
        return;
    }

    // Confirmation for data deletion
    if (!confirm('Are you sure you want to delete this value? This will remove all associated variants and cannot be undone.')) {
        return;
    }

    console.log(`Deleting value "${deletedValue}" at index ${valueIndex} from option ${optionId}`);

    // The variants that have the value go with it: their rows leave the
    // table, and the saved ones are named for the save to delete.
    const optionName = variantData[optionId] ? variantData[optionId].name : '';
    const gone = deletedValue.trim();
    variantRows.forEach((row, index) => {
        if (deletedVariantIndices.has(index) || !optionName || row[optionName] !== gone) return;
        deletedVariantIndices.add(index);
        const id = (existingVariantData[index] || {}).variant_id;
        if (id) removedVariantIds.add(String(id));
    });

    if (variantData[optionId] && variantData[optionId].values) {
        variantData[optionId].values.splice(valueIndex, 1);
    }
    // The values move up one place, so what each place carries is read
    // afresh from the values themselves.
    delete rowOptionValues[optionId];

    if (wrapper) wrapper.remove();
    reindexDomFields(valuesList, optionId);

    updateVariantTable();
    updateGroupingOptions();
}

// Helper: Create unique signature for a variant combination
function createVariantSignature(combo) {
    return Object.entries(combo)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, val]) => `${key}:${val}`)
        .join('|');
}

// Helper: Re-index DOM fields after removal
function reindexDomFields(valuesList, optionId) {
    Array.from(valuesList.children).forEach((child, idx) => {
        child.setAttribute('data-value-index', idx);
        const input = child.querySelector('.value_input');
        if (input) {
            input.setAttribute('oninput', `updateOptionValue('${optionId}', ${idx}, this.value)`);
        }
        const btn = child.querySelector('.btn_remove_value');
        if (btn) {
            btn.setAttribute('onclick', `removeValue('${optionId}', ${idx})`);
        }
    });
}

// The page's variants, one per row — see variantRows. Copies, so a caller
// can't change a row by accident.
function generateCombinations() {
    return variantRows.map(row => ({ ...row }));
}

// Every combination of the option values: what "Create every combination"
// adds the missing ones of, for a product that does come in all of them.
function everyCombination() {
    const validOptions = Object.entries(variantData)
        .filter(([id, data]) => {
            // Must have a name and at least one non-empty value
            const hasName = data.name && data.name.trim();
            const hasValues = data.values && data.values.filter(v => v && v.trim()).length > 0;
            return hasName && hasValues;
        })
        .map(([id, data]) => ({
            id,
            name: data.name,
            // Filter out empty/whitespace AND duplicate values (case-insensitive)
            values: data.values
                .filter(v => v && typeof v === 'string' && v.trim())
                .map(v => v.trim())
                .filter((v, i, arr) => arr.findIndex(x => x.toLowerCase() === v.toLowerCase()) === i)
        }));

    console.log('Valid options for combinations:', validOptions);

    if (validOptions.length === 0) {
        console.log('No valid options found');
        return [];
    }

    function combine(arrays, index = 0, current = {}) {
        if (index === arrays.length) {
            return [current];
        }

        const results = [];
        const option = arrays[index];

        for (const value of option.values) {
            results.push(...combine(arrays, index + 1, {
                ...current,
                [option.name]: value
            }));
        }

        return results;
    }

    return combine(validOptions);
}

// Whether any option has a name and a value. Without one, the product is a
// single item: one variant, told apart by nothing but its SKU.
function hasOptionValues() {
    return Object.values(variantData).some(d => d.name && (d.values || []).some(v => v && v.trim()));
}

// A single item: no option has a value, and there is at most one variant —
// the saved one. It has no table: its SKU, price and cost are boxes on the
// Pricing card (#single_item_fields), saved to that variant on the server
// (ProductForm.save_single_item). Adding an option turns them into a table
// row, carrying what was typed.
function liveRowIndices() {
    return variantRows.map((_, index) => index).filter(index => !deletedVariantIndices.has(index));
}
function singleItemMode() {
    if (!document.getElementById('single_item') || hasOptionValues()) return false;
    const live = liveRowIndices();
    return live.length <= 1 && live.every(index => (existingVariantData[index] || {}).variant_id);
}
let wasSingleItem = null;
function refreshSingleItem() {
    const flag = document.getElementById('single_item');
    if (!flag) return;
    const single = singleItemMode();
    if (wasSingleItem === true && !single) carrySingleItemIntoRow();
    flag.value = single ? '1' : '';
    const fields = document.getElementById('single_item_fields');
    const summary = document.getElementById('variants_summary');
    if (fields) fields.hidden = !single;
    if (summary) summary.hidden = single;
    wasSingleItem = single;
}
function carrySingleItemIntoRow() {
    const live = liveRowIndices();
    if (live.length !== 1) return;
    const kept = existingVariantData[live[0]] || {};
    const typed = id => (document.getElementById(id)?.value || '').trim();
    existingVariantData[live[0]] = {
        ...kept,
        sku: typed('id_item_sku') || kept.sku,
        price: typed('id_item_price') || kept.price,
        cost: typed('id_item_cost') || kept.cost,
    };
}

// The rows as last drawn (generateCombinations())
let allCombinations = [];
// What each row holds, by row index: the saved variant's id, SKU, price…
let existingVariantData = {};
// The page's variants, one entry per row: { optionName: value } for the
// values that row has. A row is a variant, or one being added — not a
// combination worked out from the option values. Multiplying those out
// listed 72 rows for an embroidered design with 7 colourways, and saving
// created the 65 nobody makes. Rows are never taken out of the list, only
// marked in deletedVariantIndices, so a row's index — which names its
// inputs, images and attributes — stays its own.
let variantRows = [];
// Saved variants removed along with an option value. The save deletes
// these, and nothing else: a variant the page leaves out is left alone.
let removedVariantIds = new Set();
// The option name and values the rows carry, per option card, while one is
// being retyped (see updateOptionName / updateOptionValue).
let rowOptionNames = {};
let rowOptionValues = {};
// Track deleted variant indices
let deletedVariantIndices = new Set();
// Track value renames: { optionId: { oldValue: newValue } }
let pendingValueRenames = {};

// Update variant table with combinations
function updateVariantTable() {
    refreshSingleItem();
    if (singleItemMode()) {
        const table = document.getElementById('variant_table');
        if (table) { table.innerHTML = ''; table.style.display = 'none'; }
        const _grp = document.getElementById('grp_container');
        if (_grp) _grp.style.display = 'none';
        allCombinations = [];
        toggleProductImagesSection();
        updateVariantRowsBar();
        return;
    }
    // Keep what each row's inputs hold before the rows are drawn again.
    allCombinations.forEach((combo, index) => {
        if (deletedVariantIndices.has(index)) return;
        const kept = existingVariantData[index] || {};
        const input = name => document.querySelector(`input[name="variant_${name}_${index + 1}"]`);
        const price = input('price'), cost = input('cost'), quantity = input('quantity');
        const sku = input('sku'), barcode = input('barcode'), featured = input('featured'), active = input('active');
        // A new row's SKU follows its values until somebody types one; a
        // saved variant's is its own and never changes by itself.
        let skuValue = kept.sku || '';
        if (sku) {
            skuValue = (kept.variant_id || sku.value !== sku.dataset.autoSku) ? sku.value : '';
        }
        existingVariantData[index] = {
            ...kept,
            price: price ? price.value : kept.price,
            cost: cost ? cost.value : kept.cost,
            quantity: quantity ? quantity.value : kept.quantity,
            sku: skuValue,
            barcode: barcode ? barcode.value : kept.barcode,
            featured: featured ? featured.checked : kept.featured,
            is_active: active ? active.value === 'true' : kept.is_active,
            product_attributes: (typeof variantAttributesData !== 'undefined' && variantAttributesData[index])
                ? variantAttributesData[index] : (kept.product_attributes || []),
        };
    });

    allCombinations = generateCombinations();

    const table = document.getElementById('variant_table');
    if (!table) return;
    table.innerHTML = '';

    const liveRows = allCombinations.filter((_, index) => !deletedVariantIndices.has(index)).length;
    if (liveRows === 0) {
        table.style.display = 'none';
        const _grp = document.getElementById('grp_container');
        if (_grp) _grp.style.display = 'none';
        toggleProductImagesSection();
        updateVariantRowsBar();
        return;
    }

    table.style.display = 'table';
    table.style.visibility = 'visible';

    const select = document.getElementById('grouping_select');
    if (select && select.options.length > 0) {
        if (select.selectedIndex < 0) select.selectedIndex = 0;
        filterVariantTableByGroup();
    } else {
        renderVariantTable(allCombinations, null);
    }

    const grpC = document.getElementById('grp_container');
    if (grpC && select && select.options.length > 0) {
        grpC.style.display = 'inline-flex';
    }

    toggleProductImagesSection();
    updateVariantRowsBar();
}

// The values an option offers a row: the option card's, plus whatever a row
// already has (a value can be on a variant without being typed above).
function optionValuesFor(optionName) {
    const values = [];
    Object.values(variantData).forEach(d => {
        if (d.name !== optionName) return;
        (d.values || []).forEach(v => { if (v && v.trim() && !values.includes(v.trim())) values.push(v.trim()); });
    });
    variantRows.forEach(row => {
        const v = row[optionName];
        if (v && !values.includes(v)) values.push(v);
    });
    return values;
}

function vfEsc(text) {
    return String(text === null || text === undefined ? '' : text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// One of a row's values, picked in its cell.
function setVariantRowValue(index, optionName, value) {
    const row = variantRows[index];
    if (!row || !optionName) return;
    if (value) row[optionName] = value;
    else delete row[optionName];
    updateVariantTable();
}

// A row for a new variant, its values still to be picked.
function addVariantRow() {
    variantRows.push({});
    updateVariantTable();
    const rows = document.querySelectorAll('#variant_table tr.variant_row');
    const last = rows[rows.length - 1];
    if (last) last.scrollIntoView({ block: 'nearest' });
}

// A row for each combination of the option values that no row has yet.
function createEveryCombination() {
    const have = new Set(variantRows
        .filter((_, index) => !deletedVariantIndices.has(index))
        .map(row => createVariantSignature(row)));
    const missing = everyCombination().filter(combo => !have.has(createVariantSignature(combo)));
    const T = window.VARIANT_T || {};
    if (missing.length === 0) {
        showToast(T.every_combination_exists || 'Every combination is already a variant.', 'info');
        return;
    }
    if (missing.length > 50 && !confirm(
            (T.confirm_combinations || 'This adds %(count)s variants. Continue?').replace('%(count)s', missing.length))) {
        return;
    }
    missing.forEach(combo => variantRows.push({ ...combo }));
    updateVariantTable();
    updateGroupingOptions();
}

// Rows the save can't take: two with the same values, or a new one with none.
function variantRowProblems() {
    const T = window.VARIANT_T || {};
    const seen = {};
    const problems = [];
    if (singleItemMode()) return problems;   // the server checks its boxes
    if (!hasOptionValues()) {
        const live = variantRows.map((_, index) => index).filter(index => !deletedVariantIndices.has(index));
        // Saved ones are left as they are (some products already have
        // several); a new one beside another is what can't be told apart.
        const isNew = index => !(existingVariantData[index] || {}).variant_id;
        if (live.length > 1 && live.some(isNew)) {
            problems.push(T.rows_need_option || 'Without options a product has one variant. Add an option to tell more of them apart.');
        }
        live.forEach(index => {
            const sku = document.querySelector(`input[name="variant_sku_${index + 1}"]`);
            const typed = sku ? sku.value : (existingVariantData[index] || {}).sku;
            if (!(typed || '').trim()) problems.push(T.row_without_sku || 'Type a SKU for the variant.');
        });
        return problems;
    }
    variantRows.forEach((row, index) => {
        if (deletedVariantIndices.has(index)) return;
        const signature = createVariantSignature(row);
        if (!signature) {
            if (!(existingVariantData[index] || {}).variant_id) {
                problems.push(T.row_without_values || 'A new variant has no values — pick them, or delete the row.');
            }
            return;
        }
        if (signature in seen) {
            problems.push((T.rows_alike || 'Two variants have the same values: %(values)s — change one, or delete it.')
                .replace('%(values)s', Object.values(row).join(' / ')));
        }
        seen[signature] = index;
    });
    return problems;
}

// The buttons under the table, and what is wrong with its rows.
function updateVariantRowsBar() {
    const bar = document.getElementById('variant_rows_actions');
    if (!bar) return;
    if (singleItemMode()) { bar.style.display = 'none'; return; }
    const hasValues = hasOptionValues();
    const live = variantRows.filter((_, index) => !deletedVariantIndices.has(index)).length;
    // Without options: "Add variant" until the one variant is there.
    bar.style.display = (hasValues || !live) ? 'flex' : 'none';
    const every = document.getElementById('variant_rows_every');
    if (every) every.style.display = hasValues ? '' : 'none';
    const note = document.getElementById('variant_rows_note');
    if (!note) return;
    const T = window.VARIANT_T || {};
    const problems = variantRowProblems();
    if (problems.length) {
        note.textContent = problems[0];
        note.className = 'variant_rows_note bad';
    } else if (!live) {
        note.textContent = hasValues
            ? (T.no_rows_yet || 'No variants yet — add one, or create every combination of the values above.')
            : (T.no_rows_single || 'Every product has at least one variant. Add one for a single item, or add an option above.');
        note.className = 'variant_rows_note';
    } else {
        note.textContent = '';
        note.className = 'variant_rows_note';
    }
}

// Render variant table with given combinations
// Render variant table with given combinations
function renderVariantTable(combinations, selectedGrouping = null) {
    const table = document.getElementById('variant_table');
    if (!table) return;

    // Always show all option names for headers
    const displayOptions = Object.values(variantData)
        .filter(d => d.name)
        .map(d => d.name);

    // Build table HTML - Cost, SKU, Barcode columns are removed from view
    const VT = (window.VARIANT_T || { photo:'PHOTO', price:'PRICE', stock:'STOCK', featured:'FEATURED', attributes:'ATTRIBUTES', opt_labels: {} });
    const labelOf = (name) => {
        const k = (name || '').toLowerCase().trim();
        return (VT.opt_labels && VT.opt_labels[k]) || (name || '').toUpperCase();
    };
    let tableHTML = `<thead><tr><th style="width: 50px;"></th><th style="width: 60px;">${VT.photo}</th>`;
    displayOptions.forEach(name => {
        tableHTML += `<th>${labelOf(name)}</th>`;
    });
    // With no options there is nothing else to tell the row by.
    if (!displayOptions.length) tableHTML += `<th>SKU</th>`;
    tableHTML += `<th>${VT.price}</th><th>${VT.stock}</th><th>${VT.featured}</th><th style="text-align: center;">${VT.attributes}</th></tr></thead><tbody>`;

    // Helper to generate row HTML (avoids duplication between grouped/ungrouped)
    const generateRowHTML = (combo, originalIndex, displayOptions, groupId = '') => {
        // Skip deleted variants
        if (deletedVariantIndices.has(originalIndex)) return '';

        const existingData = existingVariantData[originalIndex] || {};
        const variantId = existingData.variant_id || '';
        const variantProductAttrs = existingData.product_attributes || [];

        // Load images if not already loaded
        if (existingData.images && existingData.images.length > 0 && !variantImages[originalIndex]) {
            variantImages[originalIndex] = {
                images: existingData.images,
                primaryIndex: 0
            };
        }

        // Prepare image content
        const variantImg = variantImages[originalIndex];
        const hasImages = variantImg && variantImg.images && variantImg.images.length > 0;
        const primaryImg = hasImages ? variantImg.images[0] : null;

        const imgContent = primaryImg
            ? `<img src="${primaryImg.url}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; border: 1px solid #e5e7eb;">`
            : `<div style="width: 40px; height: 40px; border: 1px dashed #d1d5db; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #6b7280; background: #f9fafb;"><i class="fa fa-image"></i></div>`;

        const countBadge = (hasImages && variantImg.images.length > 1)
            ? `<span style="position: absolute; top: -5px; right: -5px; background: #667eea; color: white; font-size: 9px; padding: 1px 4px; border-radius: 8px; font-weight: 600;">${variantImg.images.length}</span>`
            : '';

        // Retrieve current values (DOM > existingData > default)
        const priceInput = document.querySelector(`input[name="variant_price_${originalIndex + 1}"]`);
        const quantityInput = document.querySelector(`input[name="variant_quantity_${originalIndex + 1}"]`);
        const featuredInput = document.querySelector(`input[name="variant_featured_${originalIndex + 1}"]`);
        // Hidden inputs
        const costInput = document.querySelector(`input[name="variant_cost_${originalIndex + 1}"]`);
        const skuInput = document.querySelector(`input[name="variant_sku_${originalIndex + 1}"]`);
        const barcodeInput = document.querySelector(`input[name="variant_barcode_${originalIndex + 1}"]`);
        const activeInput = document.querySelector(`input[name="variant_active_${originalIndex + 1}"]`);

        // A new row's SKU falls back to "parent_sku_<value>". Price and
        // cost have no parent to inherit from: the product has none.
        const _parentSku   = (document.getElementById('id_sku')?.value || '').trim();
        const _slugBits = displayOptions
            .map(opt => (combo[opt] || '').toString().trim().toLowerCase().replace(/\s+/g, '_'))
            .filter(Boolean);
        // A variant with no options has no values to build a SKU from: its
        // SKU is typed by hand, and the PARENT.SUFFIX rule does not apply.
        const _autoSku = !displayOptions.length ? ''
            : skuRuleOn()
            ? skuJoin(skuParent(), skuSuffixFromValues(displayOptions.map(opt => combo[opt])))
            : (_parentSku
                ? `${_parentSku}_${_slugBits.join('_')}`
                : _slugBits.join('_'));

        const price = priceInput?.value || existingData.price || '';
        const quantity = quantityInput?.value || existingData.quantity || '';
        // Featured: prefer the live DOM checkbox if rendered already;
        // else respect server-loaded existingData; else default to true
        // for brand-new variants. The model default is also True so this
        // matches the server side.
        let featured;
        if (featuredInput) {
            featured = featuredInput.checked;
        } else if (Object.prototype.hasOwnProperty.call(existingData, 'featured')) {
            featured = existingData.featured !== false;
        } else {
            featured = true;
        }
        const cost = costInput?.value || existingData.cost || '';
        const sku = skuInput?.value || existingData.sku || existingData.item_code || _autoSku || '';
        const barcode = barcodeInput?.value || existingData.barcode || '';
        const active = activeInput ? (activeInput.value === 'true') : (existingData.is_active !== false);

        // Row HTML
        // Add onclick to open modal, but stop propagation for interactive elements
        let rowHTML = `<tr class="variant_row ${groupId}" data-variant-index="${originalIndex}" data-variant-id="${variantId}" style="cursor: pointer;" onclick="openVariantDetailModal(${originalIndex})">`;

        // Delete button
        rowHTML += `<td style="padding-left: 14px; vertical-align: middle;">
            <button type="button" class="btn_delete_variant" onclick="deleteVariantRow(${originalIndex}, event); event.stopPropagation();" title="Delete variant" style="background: white; border: 1px solid #d1d5db; color: #6b7280; width: 32px; height: 32px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.borderColor='#ef4444'; this.style.color='#ef4444'; this.style.background='#fef2f2';" onmouseout="this.style.borderColor='#d1d5db'; this.style.color='#6b7280'; this.style.background='white';">
                <i class="fa fa-trash" style="font-size: 14px;"></i>
            </button>
        </td>`;

        // Photo Column
        rowHTML += `
            <td style="text-align: center; vertical-align: middle;">
                <div onclick="openImagePicker(${originalIndex}); event.stopPropagation();" style="cursor: pointer; display: inline-block; position: relative;" title="Manage Images">
                    ${imgContent}
                    ${countBadge}
                    <div style="position: absolute; bottom: -5px; right: -5px; background: white; border: 1px solid #e5e7eb; border-radius: 50%; width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; font-size: 8px;">
                        <i class="fa fa-plus" style="color: #667eea;"></i>
                    </div>
                </div>
            </td>`;

        // Option values: each picked from its option's values. A variant
        // may have no value for an option, shown as "—".
        displayOptions.forEach((optionName, optIdx) => {
            const value = combo[optionName] || '';
            const choices = optionValuesFor(optionName).map(v =>
                `<option value="${vfEsc(v)}"${v === value ? ' selected' : ''}>${vfEsc(v)}</option>`).join('');
            const picker = `<select class="variant_row_value${value ? '' : ' blank'}" data-option="${vfEsc(optionName)}"
                onclick="event.stopPropagation()"
                onchange="setVariantRowValue(${originalIndex}, this.dataset.option, this.value)">
                <option value="">—</option>${choices}</select>`;
            if (optIdx === 0) {
                rowHTML += `<td>${picker}<br><span class="variant_row_edit_hint"><i class="fa fa-pencil-alt"></i> ${(window.VARIANT_T && window.VARIANT_T.edit_hint) || 'Edit'}</span></td>`;
            } else {
                rowHTML += `<td>${picker}</td>`;
            }
        });

        if (!displayOptions.length) {
            rowHTML += `<td>
            <input type="text" name="variant_sku_${originalIndex + 1}" value="${vfEsc(sku)}" data-auto-sku="" placeholder="SKU" style="min-width: 120px;" onclick="event.stopPropagation()" oninput="updateVariantRowsBar()">
        </td>`;
        }

        // Price Input
        rowHTML += `<td>
            <input type="number" name="variant_price_${originalIndex + 1}" step="0.01" placeholder="—" value="${price}" readonly tabindex="-1" title="${vfEsc((window.VARIANT_T && window.VARIANT_T.price_from_cost) || 'Worked out from the cost')}" style="min-width: 100px; background:#F3F4F6; cursor:not-allowed;" onclick="event.stopPropagation()">
        </td>`;

        // Stock Input
        rowHTML += `<td>
            <input type="number" name="variant_quantity_${originalIndex + 1}" step="0.01" placeholder="0" value="${quantity}" style="min-width: 60px;" onclick="event.stopPropagation()">
        </td>`;

        // Featured Checkbox - using toggle switch
        rowHTML += `<td style="text-align: center;">
            <label class="custom-checkbox" style="margin: 0; justify-content: center; gap: 0;" onclick="event.stopPropagation()">
                <input type="checkbox" name="variant_featured_${originalIndex + 1}" ${featured ? 'checked' : ''}>
                <span class="checkmark"></span>
            </label>
        </td>`;

        // Attributes Button
        rowHTML += `<td style="text-align: center;">
            <button type="button" class="attributes_btn" onclick="openVariantAttributesModal(${originalIndex}, ''); event.stopPropagation();" 
                    style="background: white; border: 1px solid #d1d5db; color: #374151; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s;"
                    onmouseover="this.style.borderColor='#667eea'; this.style.color='#667eea';"
                    onmouseout="this.style.borderColor='#d1d5db'; this.style.color='#374151';">
                <i class="fa fa-tags"></i>
                <span class="attr-count" id="attr_count_${originalIndex}">${variantProductAttrs.length}</span>
            </button>
        </td>`;

        // HIDDEN INPUTS for Modal Fields (wrapped in td to avoid browser foster-parenting)
        rowHTML += `<td style="display:none;">`;
        rowHTML += `<input type="hidden" name="variant_cost_${originalIndex + 1}" value="${cost}">`;
        if (displayOptions.length) {
            rowHTML += `<input type="hidden" name="variant_sku_${originalIndex + 1}" value="${sku}" data-auto-sku="${vfEsc(_autoSku)}">`;
        }
        rowHTML += `<input type="hidden" name="variant_barcode_${originalIndex + 1}" value="${barcode}">`;
        rowHTML += `<input type="hidden" name="variant_active_${originalIndex + 1}" value="${active}">`;
        rowHTML += `</td>`;

        rowHTML += `</tr>`;
        return rowHTML;
    };

    // If grouping is selected, create hierarchical structure
    if (selectedGrouping) {
        // Group all combinations by the selected option
        const grouped = {};
        allCombinations.forEach((combo, index) => {
            const groupValue = combo[selectedGrouping] || '—';
            if (!grouped[groupValue]) {
                grouped[groupValue] = [];
            }
            grouped[groupValue].push({ combo, originalIndex: index });
        });

        // Render each group
        Object.entries(grouped).forEach(([groupValue, variants]) => {
            // Skip deleted groups
            const hasNonDeletedVariants = variants.some(v => !deletedVariantIndices.has(v.originalIndex));
            if (!hasNonDeletedVariants) return;

            // Calculate price range for this group
            const prices = variants
                .filter(v => !deletedVariantIndices.has(v.originalIndex))
                .map(v => {
                    const priceInput = document.querySelector(`input[name="variant_price_${v.originalIndex + 1}"]`);
                    return parseFloat(priceInput?.value || 0);
                })
                .filter(p => p > 0);

            let priceRange = '$ 0.00';
            if (prices.length > 0) {
                const minPrice = Math.min(...prices);
                const maxPrice = Math.max(...prices);
                if (minPrice === maxPrice) {
                    priceRange = `$ ${fmtNum(minPrice)}`;
                } else {
                    priceRange = `$ ${fmtNum(minPrice)}-${fmtNum(maxPrice)}`;
                }
            }

            // Group header row (collapsible)
            const groupId = `group_${groupValue.replace(/\s+/g, '_')}`;
            const extraColsCount = 3; // stock, featured, attributes
            // Colspan logic: 1 (Action) + 1 (Photo) + Options + 1 (Price) + 3 (Extra)

            tableHTML += `
                <tr class="group_header_row" style="font-weight: 600; cursor: pointer;" onclick="toggleGroupCollapse('${groupId}')">
                    <td>
                        <i class="fa fa-chevron-down group_toggle_icon" id="icon_${groupId}" style="transition: transform 0.2s;"></i>
                    </td>
                    <td></td>
                    <td colspan="${displayOptions.length}">
                        <div style="display: flex; flex-direction: column;">
                            <span style="font-weight: 600; color: #111827;">${groupValue}</span>
                            <span style="font-weight: 400; color: #6b7280; font-size: 12px; margin-top: 2px;">Expand all</span>
                        </div>
                    </td>
                    <td id="price_range_${groupId}">${priceRange}</td>
                    <td colspan="${extraColsCount}"></td>
                </tr>
            `;

            // Render all variants in this group
            variants.forEach(({ combo, originalIndex }) => {
                tableHTML += generateRowHTML(combo, originalIndex, displayOptions, groupId);
            });
        });
    } else {
        // No grouping - show all variants flat
        allCombinations.forEach((combo, index) => {
            tableHTML += generateRowHTML(combo, index, displayOptions, '');
        });
    }

    tableHTML += '</tbody>';
    table.innerHTML = tableHTML;
}

// Toggle group collapse/expand
function toggleGroupCollapse(groupId) {
    const rows = document.querySelectorAll(`.${groupId}`);
    const icon = document.getElementById(`icon_${groupId}`);

    rows.forEach(row => {
        if (row.style.display === 'none') {
            row.style.display = '';
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            row.style.display = 'none';
            if (icon) icon.style.transform = 'rotate(-90deg)';
        }
    });
}

// Update group price range in real-time
function updateGroupPriceRange(groupId) {
    const priceRangeCell = document.getElementById(`price_range_${groupId}`);
    if (!priceRangeCell) return;

    // Find all variant rows in this group
    const variantRows = document.querySelectorAll(`.variant_row.${groupId}`);
    const prices = [];

    variantRows.forEach(row => {
        // Find price input in this row
        const priceInput = row.querySelector('input[name^="variant_price_"]');
        if (priceInput && priceInput.value) {
            const price = parseFloat(priceInput.value);
            if (!isNaN(price) && price > 0) {
                prices.push(price);
            }
        }
    });

    let priceRange = '$ 0.00';
    if (prices.length > 0) {
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        if (minPrice === maxPrice) {
            priceRange = `$ ${fmtNum(minPrice)}`;
        } else {
            priceRange = `$ ${fmtNum(minPrice)}-${fmtNum(maxPrice)}`;
        }
    }

    priceRangeCell.textContent = priceRange;
}

// Filter table by selected grouping option
function filterVariantTableByGroup() {
    const select = document.getElementById('grouping_select');
    if (!select) return;

    let selectedOption = select.value;

    // If no selection and there are options available, select the first one
    if (!selectedOption && select.options.length > 0) {
        select.selectedIndex = 0;
        selectedOption = select.options[0].value;
    }

    // Render table with grouping (or without if no selection)
    renderVariantTable(allCombinations, selectedOption || null);
}

// Render variant images as thumbnails - SIMPLE VERSION
function renderVariantImages(variantIndex) {
    const variantImg = variantImages[variantIndex];
    if (!variantImg || !variantImg.images || variantImg.images.length === 0) {
        return '';
    }

    // First image is always primary
    variantImg.primaryIndex = 0;

    // Build simple HTML
    const html = variantImg.images.map((img, idx) => {
        const isPrimary = idx === 0;
        // Detect if file is a video
        const isVideo = isVideoFile(img.url) || img.file_type === 'video';
        const thumbnailUrl = isVideo ? '' : img.url;

        if (isVideo) {
            return `
                <div class="variant-sortable-image" data-image-id="${img.id}" data-file-type="video" style="position: relative; border: 2px solid ${isPrimary ? '#667eea' : '#e5e7eb'}; border-radius: 6px; padding: 4px; background: #1a1a2e; width: 60px; height: 60px; cursor: move;">
                    ${isPrimary ? '<div style="position: absolute; top: -6px; left: 4px; background: #667eea; color: white; padding: 1px 4px; border-radius: 8px; font-size: 8px; font-weight: 600; z-index: 1;">PRIMARY</div>' : ''}
                    <div style="position: relative; width: 100%; height: 50px;">
                        <img src="${thumbnailUrl}" alt="Variant video" style="width: 100%; height: 50px; object-fit: cover; border-radius: 4px;" onerror="this.style.background='#1a1a2e'">
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 20px; height: 20px; background: rgba(0,0,0,0.7); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fa fa-play" style="color: white; font-size: 8px; margin-left: 1px;"></i>
                        </div>
                    </div>
                    <button type="button" class="remove-variant-btn" onclick="event.stopPropagation(); removeVariantImage(${variantIndex}, ${idx})" style="position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; border: none; border-radius: 3px; padding: 1px 3px; font-size: 8px; cursor: pointer;">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            `;
        } else {
            return `
                <div class="variant-sortable-image" data-image-id="${img.id}" data-file-type="image" style="position: relative; border: 2px solid ${isPrimary ? '#667eea' : '#e5e7eb'}; border-radius: 6px; padding: 4px; background: white; width: 60px; height: 60px; cursor: move;">
                    ${isPrimary ? '<div style="position: absolute; top: -6px; left: 4px; background: #667eea; color: white; padding: 1px 4px; border-radius: 8px; font-size: 8px; font-weight: 600; z-index: 1;">PRIMARY</div>' : ''}
                    <img src="${img.url}" alt="Variant image" style="width: 100%; height: 50px; object-fit: cover; border-radius: 4px;">
                    <button type="button" class="remove-variant-btn" onclick="event.stopPropagation(); removeVariantImage(${variantIndex}, ${idx})" style="position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; border: none; border-radius: 3px; padding: 1px 3px; font-size: 8px; cursor: pointer;">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            `;
        }
    }).join('');

    // Initialize sortable after rendering
    setTimeout(() => initVariantSortable(variantIndex), 0);

    return html;
}

// Initialize simple sortable for variant images
function initVariantSortable(variantIndex) {
    const container = document.getElementById(`variant_images_${variantIndex}`);
    if (!container) return;

    // Use CSS grid layout for 2-column display (defined in variant_form.css)
    // Do not override with flex - CSS handles the layout
    container.style.marginTop = '5px';

    // Desktop: SortableJS, Mobile: Custom drag (same as main product)
    const isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0 || window.innerWidth < 768;
    console.log('initVariantSortable called. Width:', window.innerWidth, 'isMobile:', isMobile);
    if (!isMobile) {
        if (typeof Sortable !== 'undefined') {
            new Sortable(container, {
                animation: 150,
                onEnd: function (evt) {
                    saveVariantImageOrder(variantIndex);
                }
            });
        } else if (typeof $ !== 'undefined' && $.fn.sortable) {
            $(container).sortable({
                tolerance: 'pointer',
                revert: true,
                stop: function (event, ui) {
                    saveVariantImageOrder(variantIndex);
                }
            }).disableSelection();
        }
    } else {
        // Mobile: Custom touch drag (same as main product images)
        console.log('Initializing mobile drag for variant', variantIndex);
        initVariantMobileDrag(variantIndex, container);
    }
}

// Mobile drag for variant images (same as main product)
function initVariantMobileDrag(variantIndex, container) {
    let draggedItem = null;
    let startY = 0;
    let longPressTimer = null;

    container.querySelectorAll('.variant-sortable-image').forEach(item => {
        item.addEventListener('touchstart', function (e) {
            startY = e.touches[0].clientY;
            const touchItem = this;

            longPressTimer = setTimeout(() => {
                draggedItem = touchItem;
                draggedItem.style.opacity = '0.6';
                draggedItem.style.transform = 'scale(1.05)';
                draggedItem.style.zIndex = '1000';
                draggedItem.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
            }, 50);
        }, { passive: true });

        item.addEventListener('touchmove', function (e) {
            if (!draggedItem) {
                clearTimeout(longPressTimer);
                return;
            }

            e.preventDefault();
            const touch = e.touches[0];
            const currentY = touch.clientY;

            const items = Array.from(container.querySelectorAll('.variant-sortable-image'));
            items.forEach(otherItem => {
                if (otherItem === draggedItem) return;

                const rect = otherItem.getBoundingClientRect();
                if (currentY >= rect.top && currentY <= rect.bottom) {
                    const draggedIdx = items.indexOf(draggedItem);
                    const targetIdx = items.indexOf(otherItem);

                    if (draggedIdx < targetIdx) {
                        container.insertBefore(draggedItem, otherItem.nextSibling);
                    } else {
                        container.insertBefore(draggedItem, otherItem);
                    }
                }
            });
        }, { passive: false });

        item.addEventListener('touchend', function (e) {
            clearTimeout(longPressTimer);

            if (draggedItem) {
                draggedItem.style.opacity = '1';
                draggedItem.style.transform = 'scale(1)';
                draggedItem.style.zIndex = '';
                draggedItem.style.boxShadow = '';

                saveVariantImageOrder(variantIndex);

                draggedItem = null;
            }
        });
    });
}

// Simple drag-and-drop fallback with touch support
function initSimpleDragDrop(variantIndex, container) {
    let draggedItem = null;
    let touchStartX = 0;
    let touchStartY = 0;
    const items = container.querySelectorAll('.variant-sortable-image');

    items.forEach(item => {
        item.draggable = true;
        item.style.touchAction = 'none'; // Prevent browser touch behaviors

        // Desktop drag-and-drop
        item.addEventListener('dragstart', function (e) {
            draggedItem = this;
            this.style.opacity = '0.5';
            e.dataTransfer.effectAllowed = 'move';
        });

        item.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            if (this !== draggedItem) {
                this.style.borderColor = '#667eea';
            }
        });

        item.addEventListener('dragleave', function () {
            item.classList.remove('drag-over');
        });

        item.addEventListener('drop', function (e) {
            e.preventDefault();
            if (draggedItem !== this) {
                const allItems = Array.from(container.children);
                const draggedIndex = allItems.indexOf(draggedItem);
                const targetIndex = allItems.indexOf(this);

                if (draggedIndex < targetIndex) {
                    container.insertBefore(draggedItem, this.nextSibling);
                } else {
                    container.insertBefore(draggedItem, this);
                }

                saveVariantImageOrder(variantIndex);
            }
        });

        item.addEventListener('dragend', function (e) {
            this.style.opacity = '1';
        });

        // Mobile touch support - SWIPE BASED
        let touchStartX = 0;
        let touchStartIdx = -1;
        item.addEventListener('touchstart', function (e) {
            draggedItem = this;
            touchStartX = e.touches[0].clientX;
            touchStartIdx = Array.from(items).indexOf(this);
            this.style.opacity = '0.5';
            this.style.transform = 'scale(1.05)';
            e.preventDefault();
        });

        item.addEventListener('touchend', function (e) {
            if (!draggedItem) return;

            const touchEndX = e.changedTouches[0].clientX;
            const swipeDistance = touchEndX - touchStartX;
            const allItems = Array.from(container.children);

            // Swipe right = move forward, Swipe left = move backward
            if (Math.abs(swipeDistance) > 30) { // Minimum swipe distance for small images
                if (swipeDistance > 0 && touchStartIdx < allItems.length - 1) {
                    // Swipe right - move to next position
                    const nextItem = allItems[touchStartIdx + 1];
                    container.insertBefore(draggedItem, nextItem.nextSibling);
                    saveVariantImageOrder(variantIndex);
                } else if (swipeDistance < 0 && touchStartIdx > 0) {
                    // Swipe left - move to previous position
                    const prevItem = allItems[touchStartIdx - 1];
                    container.insertBefore(draggedItem, prevItem);
                    saveVariantImageOrder(variantIndex);
                }
            }

            // Reset styles
            container.querySelectorAll('.variant-sortable-image').forEach(img => {
                img.style.opacity = '1';
                img.style.transform = 'scale(1)';
            });

            draggedItem = null;
            e.preventDefault();
        });
    });
}

// Save variant image order to database
function saveVariantImageOrder(variantIndex) {
    const container = document.getElementById(`variant_images_${variantIndex}`);
    if (!container) return;

    const items = container.querySelectorAll('.variant-sortable-image');
    const imageOrder = Array.from(items).map(item => item.getAttribute('data-image-id'));

    // Update local variantImages array
    const newOrder = [];
    items.forEach((item, idx) => {
        const imageId = item.getAttribute('data-image-id');
        const originalImg = variantImages[variantIndex].images.find(img => img.id == imageId);
        if (originalImg) {
            newOrder.push(originalImg);
        }
    });

    variantImages[variantIndex].images = newOrder;
    variantImages[variantIndex].primaryIndex = 0;

    // Update primary badge
    updatePrimaryBadgeAfterSort(variantIndex);

    console.log('Image order updated for variant', variantIndex);
}

// Update primary badge after sort
function updatePrimaryBadgeAfterSort(variantIndex) {
    const container = document.getElementById(`variant_images_${variantIndex}`);
    if (!container) return;

    // Remove all badges
    container.querySelectorAll('div').forEach(el => {
        if (el.textContent === 'PRIMARY') el.remove();
    });

    // Reset borders
    container.querySelectorAll('.variant-sortable-image').forEach(img => {
        img.style.borderColor = '#e5e7eb';
    });
}

// Remove image from variant - INSTANT delete with confirmation
async function removeVariantImage(variantIndex, imageIndex) {
    if (!variantImages[variantIndex]) return;

    const img = variantImages[variantIndex].images[imageIndex];
    if (!img) return;

    // Use modern confirmation dialog
    const confirmed = await window.showConfirmDialog(
        VF_TEXT.deleteImageTitle || 'Delete the image?',
        VF_TEXT.deleteImageBody || 'This image will be deleted permanently. This cannot be undone.',
        VF_TEXT.delete || 'Delete',
        VF_TEXT.cancel || 'Cancel'
    );

    if (!confirmed) return;

    // If image has DB ID, delete it (and its CDN file) via API
    if (img.id) {
        try {
            const response = await fetch('/marketing/api/instant_delete_file/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : getCsrfToken()
                },
                body: JSON.stringify({ file_id: img.id })
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || VF_TEXT.deleteFailed || 'The delete failed');
            }

            // Remove this image from ALL variants that share the same URL
            const deletedUrl = data.deleted_url || img.url;
            removeImageFromAllVariants(deletedUrl, variantIndex);

            // Also remove from main product gallery if exists
            removeImageFromMainGallery(deletedUrl);

            showToast('🗑️ ' + (VF_TEXT.imageDeleted || 'Image deleted!'), 'success');
            return; // Already handled UI update in removeImageFromAllVariants
        } catch (error) {
            console.error('Delete error:', error);
            showToast(`❌ ${VF_TEXT.deleteError || 'Delete error'}: ${error.message}`, 'error');
            return; // Don't remove from UI if delete failed
        }
    }

    // Remove from frontend array (for images not yet saved to DB)
    variantImages[variantIndex].images.splice(imageIndex, 1);

    // Adjust primary index if needed
    if (variantImages[variantIndex].images.length === 0) {
        variantImages[variantIndex].primaryIndex = 0;
    } else if (imageIndex === variantImages[variantIndex].primaryIndex) {
        variantImages[variantIndex].primaryIndex = 0;
    } else if (imageIndex < variantImages[variantIndex].primaryIndex) {
        variantImages[variantIndex].primaryIndex--;
    }

    // Update preview
    updateVariantImagePreview(variantIndex);
}

// Open image picker modal
let currentVariantIndex = null;
let selectionOrder = []; // Track selection order [url1, url2, ...]

async function openImagePicker(variantIndex) {
    currentVariantIndex = variantIndex;

    // Initialize variant images if not exists
    if (!variantImages[variantIndex]) {
        variantImages[variantIndex] = { images: [], primaryIndex: 0 };
    }

    // Initialize selectionOrder from existing images for this variant
    // This preserves the established order
    selectionOrder = variantImages[variantIndex].images.map(img => img.url).filter(url => url);
    selectionSet = new Set(selectionOrder);

    // RESET uploadedImages on every open — guarantees fresh view of shared pool
    uploadedImages = [];

    // Helper to normalize URL for comparison
    const normalizeUrl = (url) => {
        if (!url) return '';
        let normalized = url.split('?')[0];
        normalized = normalized.replace(/\/$/, '');
        return normalized;
    };

    // Helper to add unique images to uploadedImages
    const addUniqueImage = (newImg) => {
        if (!newImg.url) return;
        const normalizedNewUrl = normalizeUrl(newImg.url);
        const existingIndex = uploadedImages.findIndex(img => normalizeUrl(img.url) === normalizedNewUrl);
        if (existingIndex === -1) {
            uploadedImages.push(newImg);
        } else {
            const existing = uploadedImages[existingIndex];
            if (existing.name && existing.name.startsWith('Main Image') &&
                newImg.name && !newImg.name.startsWith('Main Image')) {
                uploadedImages[existingIndex] = { ...existing, ...newImg, name: newImg.name };
            }
        }
    };

    // 1. EDIT MODE: Fetch shared pool from server (source of truth)
    const productEditMatch = window.location.pathname.match(/\/product_edit\/(\d+)\//)?.[1];
    if (productEditMatch) {
        try {
            // Cache-buster to guarantee fresh data
            const cb = Date.now();
            const response = await fetch(`/marketing/api/get_product_files/?product_id=${productEditMatch}&_=${cb}`, {
                cache: 'no-store',
                headers: { 'Cache-Control': 'no-cache' }
            });
            const data = await response.json();
            console.log('[Picker] API raw response:', data);
            if (data.success && Array.isArray(data.files)) {
                data.files.forEach(file => {
                    addUniqueImage({
                        id: file.id,
                        url: file.url,
                        optimized_url: file.optimized_url || file.url,
                        name: file.name,
                        variant: file.variant || null,
                        file: null,
                        file_type: file.file_type || 'image'
                    });
                });
                console.log(`[Picker] Loaded ${data.files.length} files from server pool (total uploaded: ${uploadedImages.length})`);
            } else {
                console.warn('[Picker] API returned no files:', data);
            }
        } catch (error) {
            console.error('[Picker] Error loading product files:', error);
        }
    }

    // 2. Merge images from CURRENT variant and all other variants (for unsaved JS state)
    Object.values(variantImages).forEach(vData => {
        if (vData.images) {
            vData.images.forEach(img => {
                addUniqueImage({
                    id: img.id,
                    url: img.url,
                    name: img.name,
                    variant: null,
                    file: img.file,
                    file_type: img.file_type || 'image'
                });
            });
        }
    });

    // 3. CREATE MODE: Scrape Main Product Images from DOM (no API yet)
    if (!productEditMatch) {
        // CREATE MODE: Scrape from DOM (no API available)
        const mainImageGrid = document.getElementById('sortable_images');
        if (mainImageGrid) {
            const mainImages = mainImageGrid.querySelectorAll('.sortable-image');
            Array.from(mainImages).forEach((imgDiv, idx) => {
                const img = imgDiv.querySelector('img');
                const imgUrl = img ? img.src : '';

                if (imgUrl) {
                    const fileType = imgDiv.dataset.fileType || (isVideoFile(imgUrl) ? 'video' : 'image');
                    addUniqueImage({
                        id: imgDiv.dataset.fileId || `main_img_${idx}`,
                        url: imgUrl,
                        name: `Main Image ${idx + 1}`,
                        variant: null,
                        file: null,
                        temp_file: true,
                        from_main: true,
                        file_type: fileType
                    });
                }
            });
        }
    }

    // Sort uploadedImages? Maybe put selected ones first?
    // For now, preservation of order or simple append is fine.
    // Maybe Main images first?
    // uploadedImages.sort((a, b) => (a.from_main === b.from_main) ? 0 : a.from_main ? -1 : 1);

    // Create modal
    const modal = document.createElement('div');
    modal.id = 'image_picker_modal';
    modal.className = 'image_modal';

    const selectedCount = selectionOrder.length;
    modal.innerHTML = `
        <div class="imp_content">
            <div class="imp_header">
                <div class="imp_header_left">
                    <h3>Media</h3>
                    <span class="imp_count" id="imp_total_count">${uploadedImages.length} files</span>
                </div>
                <button type="button" class="imp_close" onclick="closeImagePicker()">&times;</button>
            </div>
            <div class="imp_toolbar">
                <div class="imp_dropzone" id="image_upload_dropzone">
                    <input type="file" id="image_file_input" accept="image/*,video/mp4,video/webm,video/quicktime,video/x-msvideo,video/avi" multiple style="display:none;" onchange="handleImageUpload(event)">
                    <button type="button" class="imp_upload_btn" onclick="document.getElementById('image_file_input').click()">
                        <i class="fa fa-plus"></i> Upload
                    </button>
                    <span class="imp_drop_hint">or drop files here</span>
                </div>
                <label class="imp_select_all_label" title="Select All">
                    <input type="checkbox" id="imp_select_all_cb" onchange="toggleSelectAllBulk(this)">
                    <span>Select All</span>
                </label>
            </div>
            <div class="imp_body image_modal_body">
                <div class="image_grid" id="image_grid">
                    ${generateImageGrid()}
                </div>
            </div>
            <div class="imp_footer">
                <span class="imp_selection_info" id="imp_selection_info">${selectedCount > 0 ? selectedCount + ' selected' : 'Click images to select'}</span>
                <div class="imp_footer_actions">
                    <button type="button" class="imp_btn_cancel" onclick="closeImagePicker()">Cancel</button>
                    <button type="button" class="imp_btn_done" onclick="confirmImageSelection()">Done</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    setTimeout(() => {
        modal.classList.add('show');
        updateSelectionBadges(); // Apply numbers after rendering
    }, 10);
}

// Store uploaded images globally
let uploadedImages = [];

// Generate image grid from uploaded images
function generateImageGrid() {
    if (uploadedImages.length === 0) {
        return '<div class="no_images_message"><i class="fa fa-cloud-upload-alt"></i><p>No files yet.<br>Upload images or videos to get started.</p></div>';
    }

    return uploadedImages.map((img, idx) => {
        const isVideo = isVideoFile(img.url) || img.file_type === 'video';
        const thumbnailUrl = isVideo ? '' : img.url;

        const lazyAttr = idx > 9 ? 'loading="lazy"' : '';
        const thumbHTML = isVideo
            ? `<div class="imp_thumb_video">
                   <img src="${thumbnailUrl}" alt="${img.name}" ${lazyAttr} onerror="this.style.display='none'">
                   <div class="imp_play"><i class="fa fa-play"></i></div>
               </div>`
            : `<img class="imp_thumb" src="${thumbnailUrl}" alt="${img.name}" ${lazyAttr}>`;

        return `
            <div class="image_item" data-url="${img.url}" data-name="${img.name}" data-index="${idx}" data-file-type="${isVideo ? 'video' : 'image'}" onclick="toggleImageSelection(this, event)">
                <div class="imp_card_media">
                    ${thumbHTML}
                    <div class="imp_bulk_check" onclick="toggleBulkCheck(this, event)" title="Select for bulk delete">
                        <i class="fa fa-check"></i>
                    </div>
                    <div class="imp_card_check"><i class="fa fa-check"></i></div>
                    <div class="imp_card_actions">
                        <button type="button" class="imp_act_btn" onclick="event.stopPropagation(); window.openMediaPreview('${img.optimized_url || img.url}', '${isVideo ? 'video' : 'image'}', ${img.id || 'null'})" title="Preview">
                            <i class="fa fa-expand"></i>
                        </button>
                        <button type="button" class="imp_act_btn imp_act_delete" onclick="removeUploadedImage(${idx}, event)" title="Delete">
                            <i class="fa fa-trash-alt"></i>
                        </button>
                    </div>
                </div>
                <div class="imp_card_name">${img.name}</div>
            </div>
        `;
    }).join('');
}

// Helper function to check if a file is a video
function isVideoFile(url) {
    if (!url) return false;
    const lowerUrl = url.toLowerCase();
    // Use regex to match exact extensions at end of URL (or before query string)
    // This avoids false positives like .avif matching .avi
    return /\.(mp4|mov|webm|avi|mkv|m4v|wmv)(\?.*)?$/i.test(lowerUrl);
}

// Toggle image selection with Order Tracking
function toggleImageSelection(element, event) {
    // Don't toggle if clicking on action buttons
    if (event.target.closest('.imp_act_btn, .imp_card_actions, .remove_image_btn')) {
        return;
    }

    const url = element.getAttribute('data-url');
    if (!url) return;

    if (selectionSet.has(url)) {
        const idx = selectionOrder.indexOf(url);
        if (idx !== -1) selectionOrder.splice(idx, 1);
        selectionSet.delete(url);
        console.log(`[🖱️ CLICK] DESELECT variant=${currentVariantIndex} url=${url.slice(-40)} | total now: ${selectionOrder.length}`);
    } else {
        selectionOrder.push(url);
        selectionSet.add(url);
        console.log(`[🖱️ CLICK] SELECT variant=${currentVariantIndex} url=${url.slice(-40)} | total now: ${selectionOrder.length}`);
    }

    updateSelectionBadges();
}

// Fast lookup Set for selectionOrder (kept in sync)
let selectionSet = new Set();

// Update badges on all images to reflect their order in selectionOrder
function updateSelectionBadges() {
    // Sync Set with array
    selectionSet = new Set(selectionOrder);

    const allItems = document.querySelectorAll('.image_item');
    allItems.forEach(item => {
        const url = item.getAttribute('data-url');
        const existingBadge = item.querySelector('.selection_badge');

        if (selectionSet.has(url)) {
            const orderIndex = selectionOrder.indexOf(url);
            item.classList.add('selected');
            if (orderIndex === 0) item.classList.add('primary');
            else item.classList.remove('primary');

            const isPrimary = orderIndex === 0;
            if (existingBadge) {
                // Update existing badge instead of removing/recreating
                existingBadge.textContent = orderIndex + 1;
                existingBadge.style.background = isPrimary ? '#10b981' : '#667eea';
            } else {
                // Create badge only if it doesn't exist
                const badge = document.createElement('div');
                badge.className = 'selection_badge';
                badge.textContent = orderIndex + 1;
                badge.style.cssText = `
                    position:absolute; top:8px; left:8px;
                    background:${isPrimary ? '#10b981' : '#667eea'};
                    color:white; width:22px; height:22px; border-radius:50%;
                    display:flex; align-items:center; justify-content:center;
                    font-weight:700; font-size:11px; z-index:12;
                    border:2px solid white;
                    box-shadow:0 2px 6px rgba(0,0,0,0.25);
                    pointer-events:none;
                `;
                const media = item.querySelector('.imp_card_media');
                if (media) media.appendChild(badge);
            }
        } else {
            item.classList.remove('selected', 'primary');
            if (existingBadge) existingBadge.remove();
        }
    });

    // Update footer info
    const info = document.getElementById('imp_selection_info');
    if (info) {
        const count = selectionOrder.length;
        info.textContent = count > 0 ? count + ' selected' : 'Click images to select';
    }
}

// ─── Ensure upload tracker is available (fallback if file_manager_modal.js not loaded yet) ───
(function ensureTrackerFunctions() {
    if (typeof window.createUploadTracker === 'function') return; // already defined

    let _uploadTracker = null;
    let _trackerCollapsed = false;

    window.createUploadTracker = function(totalFiles) {
        if (_uploadTracker) _uploadTracker.remove();
        const t = document.createElement('div');
        t.className = 'upload-tracker';
        t.id = 'uploadTracker';
        t.innerHTML = `
            <div class="upload-tracker-header" onclick="window.toggleTrackerCollapse()">
                <h4><span id="utTitle">Uploading <span id="utDoneCount">0</span> of ${totalFiles} items</span></h4>
                <div class="ut-actions">
                    <button onclick="event.stopPropagation(); window.toggleTrackerCollapse()" id="utCollapseBtn" title="Minimize"><i class="fa fa-chevron-down"></i></button>
                    <button onclick="event.stopPropagation(); window.closeUploadTracker()" id="utCloseBtn" title="Close" style="display:none;"><i class="fa fa-times"></i></button>
                </div>
            </div>
            <div class="ut-overall-progress"><div class="ut-overall-bar" id="utOverallBar" style="width:0%"></div></div>
            <div class="upload-tracker-body" id="utBody"></div>`;
        document.body.appendChild(t);
        _uploadTracker = t;
        _trackerCollapsed = false;

        // Inject CSS if not present
        if (!document.getElementById('ut-tracker-css')) {
            const s = document.createElement('style');
            s.id = 'ut-tracker-css';
            s.textContent = `
                .upload-tracker{position:fixed;bottom:24px;right:24px;width:360px;background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.18),0 2px 8px rgba(0,0,0,.08);z-index:2147483647;overflow:hidden;animation:trackerSlideUp .35s cubic-bezier(.4,0,.2,1);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
                .upload-tracker.closing{animation:trackerSlideDown .3s cubic-bezier(.4,0,.2,1) forwards}
                .upload-tracker-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:#1a1a2e;color:#fff;cursor:pointer;user-select:none}
                .upload-tracker-header h4{margin:0;font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}
                .upload-tracker-header .ut-actions{display:flex;gap:8px;align-items:center}
                .upload-tracker-header .ut-actions button{background:none;border:none;color:rgba(255,255,255,.7);cursor:pointer;font-size:14px;padding:2px 4px;border-radius:4px;transition:all .15s}
                .upload-tracker-header .ut-actions button:hover{color:#fff;background:rgba(255,255,255,.1)}
                .upload-tracker-body{max-height:280px;overflow-y:auto;transition:max-height .3s ease}
                .upload-tracker-body.collapsed{max-height:0}
                .upload-tracker-body::-webkit-scrollbar{width:4px}
                .upload-tracker-body::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:4px}
                .ut-file-row{display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid #f1f5f9;animation:utRowFadeIn .3s ease}
                .ut-file-row:last-child{border-bottom:none}
                .ut-file-thumb{width:36px;height:36px;border-radius:6px;object-fit:cover;flex-shrink:0;background:#f1f5f9}
                .ut-file-info{flex:1;min-width:0}
                .ut-file-name{font-size:13px;font-weight:500;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
                .ut-file-size{font-size:11px;color:#94a3b8;margin-top:2px}
                .ut-file-status{flex-shrink:0;width:24px;height:24px;display:flex;align-items:center;justify-content:center}
                .ut-spinner{width:20px;height:20px;border:2.5px solid #e2e8f0;border-top-color:#667eea;border-radius:50%;animation:utSpin .7s linear infinite}
                .ut-check{color:#22c55e;font-size:18px;animation:utPop .3s cubic-bezier(.175,.885,.32,1.275)}
                .ut-error{color:#ef4444;font-size:18px}
                .ut-overall-progress{height:3px;background:#e2e8f0}
                .ut-overall-bar{height:100%;background:linear-gradient(90deg,#667eea,#764ba2);transition:width .4s ease;border-radius:0 3px 3px 0}
                @keyframes trackerSlideUp{from{transform:translateY(100px);opacity:0}to{transform:translateY(0);opacity:1}}
                @keyframes trackerSlideDown{from{transform:translateY(0);opacity:1}to{transform:translateY(100px);opacity:0}}
                @keyframes utRowFadeIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}
                @keyframes utSpin{to{transform:rotate(360deg)}}
                @keyframes utPop{0%{transform:scale(0)}100%{transform:scale(1)}}`;
            document.head.appendChild(s);
        }
    };

    window.addTrackerRow = function(file) {
        const body = document.getElementById('utBody');
        if (!body) return null;
        const row = document.createElement('div');
        row.className = 'ut-file-row';
        const sizeStr = file.size > 1048576 ? (file.size/1048576).toFixed(1)+' MB' : (file.size/1024).toFixed(0)+' KB';
        const thumbUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : '';
        const thumbHTML = thumbUrl
            ? `<img class="ut-file-thumb" src="${thumbUrl}" alt="">`
            : `<div class="ut-file-thumb" style="display:flex;align-items:center;justify-content:center;background:#1a1a2e;color:#667eea;font-size:14px;"><i class="fa fa-film"></i></div>`;
        row.innerHTML = `${thumbHTML}<div class="ut-file-info"><div class="ut-file-name">${file.name}</div><div class="ut-file-size">${sizeStr}</div></div><div class="ut-file-status"><div class="ut-spinner"></div></div>`;
        body.appendChild(row);
        body.scrollTop = body.scrollHeight;
        return row;
    };

    window.updateTrackerRow = function(row, success) {
        if (!row) return;
        const s = row.querySelector('.ut-file-status');
        s.innerHTML = success ? '<i class="fa fa-check-circle ut-check"></i>' : '<i class="fa fa-times-circle ut-error"></i>';
    };

    window.updateTrackerProgress = function(done, total) {
        const bar = document.getElementById('utOverallBar');
        const countEl = document.getElementById('utDoneCount');
        const title = document.getElementById('utTitle');
        if (bar) bar.style.width = `${(done/total)*100}%`;
        if (countEl) countEl.textContent = done;
        if (done >= total) {
            if (title) title.innerHTML = `<i class="fa fa-check-circle" style="color:#22c55e"></i> ${total} file uploaded`;
            const closeBtn = document.getElementById('utCloseBtn');
            if (closeBtn) closeBtn.style.display = '';
            setTimeout(() => window.closeUploadTracker(), 4000);
        }
    };

    window.toggleTrackerCollapse = function() {
        const body = document.getElementById('utBody');
        const btn = document.getElementById('utCollapseBtn');
        if (!body) return;
        _trackerCollapsed = !_trackerCollapsed;
        body.classList.toggle('collapsed', _trackerCollapsed);
        if (btn) btn.innerHTML = _trackerCollapsed ? '<i class="fa fa-chevron-up"></i>' : '<i class="fa fa-chevron-down"></i>';
    };

    window.closeUploadTracker = function() {
        const tracker = document.getElementById('uploadTracker');
        if (tracker) {
            tracker.classList.add('closing');
            setTimeout(() => { tracker.remove(); _uploadTracker = null; }, 300);
        }
    };
})();

// Handle image upload - INSTANT upload with floating tracker
async function handleImageUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    // Check if product edit or create mode
    const productEditMatch = window.location.pathname.match(/\/product_edit\/(\d+)\//)?.[1];
    const isCreateMode = window.location.pathname.includes('/product_create/');

    if (!productEditMatch && !isCreateMode) {
        showToast('Product ID not found', 'error');
        return;
    }

    // Get variant ID from table row if variant exists (only in edit mode)
    const variantId = productEditMatch ? getVariantId(currentVariantIndex) : null;
    console.log('Uploading to variant index:', currentVariantIndex, 'variant ID:', variantId);

    // Filter valid files first
    const validFiles = [];
    for (const file of files) {
        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');

        if (!isImage && !isVideo) {
            showToast(`⚠️ "${file.name}" is not a supported file type`, 'warning');
            continue;
        }
        const existingFile = uploadedImages.find(img => img.name === file.name);
        if (existingFile) {
            showToast(`⚠️ "${file.name}" already exists`, 'warning');
            continue;
        }
        validFiles.push(file);
    }

    if (validFiles.length === 0) { event.target.value = ''; return; }

    // Create floating upload tracker
    if (typeof window.createUploadTracker === 'function') {
        window.createUploadTracker(validFiles.length);
    }
    let doneCount = 0;

    // Process each file
    for (const file of validFiles) {
        // Add row to floating tracker
        let trackerRow = null;
        if (typeof window.addTrackerRow === 'function') {
            trackerRow = window.addTrackerRow(file);
        }

        // Show progress placeholder in grid
        const grid = document.getElementById('image_grid');
        const placeholder = document.createElement('div');
        placeholder.className = 'image_item uploading';
        placeholder.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f3f4f6;">
                <i class="fa fa-spinner fa-spin" style="font-size: 24px; color: #667eea;"></i>
            </div>
            <p>Uploading...</p>
        `;
        if (grid) grid.prepend(placeholder);

        try {
            const formData = new FormData();
            formData.append('file', file);

            let data;
            if (isCreateMode) {
                formData.append('file_type', 'variant_image');
                formData.append('variant_temp_id', `variant_${currentVariantIndex}`);
                formData.append('sequence', uploadedImages.length);

                const response = await fetch('/marketing/api/temp_upload_file/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : '' },
                    body: formData
                });
                const text = await response.text();
                if (!text) throw new Error(`Server returned empty response (status ${response.status})`);
                try { data = JSON.parse(text); } catch(e) { throw new Error(`Server error (${response.status}): ${text.substring(0, 200)}`); }
            } else {
                formData.append('product_id', productEditMatch);
                const response = await fetch('/marketing/api/instant_upload_file/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : '' },
                    body: formData
                });
                const text = await response.text();
                if (!text) throw new Error(`Server returned empty response (status ${response.status})`);
                try { data = JSON.parse(text); } catch(e) { throw new Error(`Server error (${response.status}): ${text.substring(0, 200)}`); }
            }

            if (!data.success) {
                throw new Error(data.error || 'Upload failed');
            }

            // Normalize response data from both APIs
            const fileUrl = isCreateMode ? data.file_data.url : data.file.url;
            const fileId = isCreateMode ? data.file_data.public_id : data.file.id;
            const fileType = (data.file && data.file.file_type) ? data.file.file_type : (isVideoFile(fileUrl) ? 'video' : 'image');


            const newImage = {
                url: fileUrl,
                optimized_url: fileUrl,
                name: file.name,
                file: null,
                id: fileId,
                variant: null,
                file_type: fileType,
                temp_file: isCreateMode
            };

            // Insert at beginning so new uploads appear at top
            uploadedImages.unshift(newImage);

            // Remove placeholder and refresh grid
            if (placeholder) placeholder.remove();
            refreshImageGrid();

            // Also add to main Media gallery instantly
            addImageToMainGallery(newImage);

            // Update tracker row - success
            if (typeof window.updateTrackerRow === 'function') window.updateTrackerRow(trackerRow, true);

        } catch (error) {
            console.error('Upload error:', error);
            if (placeholder) placeholder.remove();
            showToast(`❌ Upload failed: ${error.message}`, 'error');
            if (typeof window.updateTrackerRow === 'function') window.updateTrackerRow(trackerRow, false);
        }

        doneCount++;
        if (typeof window.updateTrackerProgress === 'function') window.updateTrackerProgress(doneCount, validFiles.length);

    } // End of for loop

    // Clear the input so the same files can be uploaded again
    event.target.value = '';
} // End of handleImageUpload function


// Get variant ID from table row
function getVariantId(variantIndex) {
    const row = document.querySelector(`tr[data-variant-index="${variantIndex}"]`);
    const variantId = row ? row.getAttribute('data-variant-id') : null;
    // Return null if empty string or null
    return (variantId && variantId.trim()) ? variantId : null;
}

// Confirm image selection using the Selection Order
async function confirmImageSelection() {
    if (selectionOrder.length === 0) {
        // Allow clearing selection? User said "First selected is primary", implying selection.
        // But if they unchecked everything, they might want to clear images.
        // Let's allow it if they really want, or just return.
        // If they click Done with nothing selected, it clears the variant images.
    }

    const images = [];

    // Construct images array in the order of selectionOrder
    selectionOrder.forEach(url => {
        const uploadedImg = uploadedImages.find(img => img.url === url);
        if (uploadedImg) {
            images.push({
                url: url,
                name: uploadedImg.name,
                file: uploadedImg.file,
                id: uploadedImg.id,
                file_type: uploadedImg.file_type // Ensure file_type is carried over
            });
        }
    });

    // Check for images that were unselected (removed from this variant)
    // CRITICAL: Compare by URL, not ID. Same URL can have multiple IDs (Virtual Sharing clones).
    // If user kept the URL but picker's uploadedImages had a different ID (e.g. V2's clone ID
    // instead of V1's), we must NOT mark the old ID as deleted — the image is still selected.
    if (variantImages[currentVariantIndex] && variantImages[currentVariantIndex].images) {
        const oldImages = variantImages[currentVariantIndex].images;
        const newUrls = new Set(images.map(i => i.url).filter(Boolean));

        console.log(`[confirmImageSelection] variant ${currentVariantIndex}: OLD=${oldImages.length} NEW=${images.length}`);
        console.log(`  old URLs:`, oldImages.map(i => i.url));
        console.log(`  new URLs:`, Array.from(newUrls));

        oldImages.forEach(oldImg => {
            // Only unlink if the URL is genuinely gone from new selection
            if (oldImg.id && oldImg.url && !newUrls.has(oldImg.url)) {
                unlinkedVariantFiles.add(oldImg.id);
                console.log(`  → URL removed, added ID ${oldImg.id} (${oldImg.url.slice(-30)}) to unlinkedVariantFiles`);
            }
        });

        // Preserve this variant's original IDs for images that still match by URL
        // (don't let picker's dedup replace V1's ID with V2's ID)
        images.forEach((img, idx) => {
            const matchingOld = oldImages.find(o => o.url === img.url && o.id);
            if (matchingOld && matchingOld.id !== img.id) {
                console.log(`  🔄 Preserving this variant's ID ${matchingOld.id} for URL (picker had ${img.id})`);
                images[idx] = { ...img, id: matchingOld.id };
            }
        });
    }

    // Store selected images
    variantImages[currentVariantIndex] = {
        images: images,
        primaryIndex: 0  // First image in the ordered list is always primary
    };

    console.log(`Variant ${currentVariantIndex} images updated (count: ${images.length})`);

    showToast(`✅ ${images.length} image(s) updated for variant`, 'success');

    // Also update the simple icon in the table (we changed the render function to use a single icon)
    // We need to re-render that cell ideally, or just the whole table row content?
    // updateVariantTable() might be too heavy.
    // Ideally updateVariantImagePreview should handle the DOM update for the icon column now.
    // But updateVariantImagePreview implementation in our previous step was assuming the OLD layout (inside a div id="variant_images_X").
    // We moved the image to a new column.

    // Let's trigger a table update to be safe and clean, or update the specific cell manually.
    // For now, let's call updateVariantTable() if it's cheap enough, or better:
    // Update the innerHTML of the cell wrapper.
    updateVariantIconInTable(currentVariantIndex);

    closeImagePicker();
}

// Helper to update the specific icon cell in table without re-rendering whole table
function updateVariantIconInTable(variantIndex) {
    // We need to find the cell for this variant
    // In grouped view, finding by index is tricky if we don't have direct reference.
    // But we have data-variant-index on the TR.
    const row = document.querySelector(`tr[data-variant-index="${variantIndex}"]`);
    if (!row) return; // Might be hidden or filtered?

    // Re-render the table to be 100% sure we get the correct state including grouping/badges etc.
    const select = document.getElementById('grouping_select');
    const selectedGrouping = select ? select.value : null;

    if (typeof renderVariantTable === 'function') {
        renderVariantTable(allCombinations, selectedGrouping);
    }
}

// Animate-out and remove a single DOM element
function animateRemoveItem(el) {
    el.style.transition = 'transform 0.25s ease, opacity 0.25s ease';
    el.style.transform = 'scale(0.7)';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 250);
}

// Background delete with tracker + save button lock
function deleteImageInBackground(image, trackerRow) {
    if (!image || !image.id) {
        if (trackerRow && window.updateDeleteTrackerRow) window.updateDeleteTrackerRow(trackerRow, true);
        return Promise.resolve();
    }
    // Reserve a pending-delete slot — save button locked until this completes
    const token = window.__beginDelete ? window.__beginDelete() : null;
    return fetch('/marketing/api/instant_delete_file/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : ''
        },
        body: JSON.stringify({ file_id: image.id })
    })
    .then(r => r.json().catch(() => ({success: r.ok})))
    .then(data => {
        const success = !!(data && data.success !== false);
        if (trackerRow && window.updateDeleteTrackerRow) window.updateDeleteTrackerRow(trackerRow, success);
        return success;
    })
    .catch(err => {
        console.error('Background delete error:', err);
        if (trackerRow && window.updateDeleteTrackerRow) window.updateDeleteTrackerRow(trackerRow, false);
        return false;
    })
    .finally(() => {
        if (window.__endDelete && token) window.__endDelete(token);
    });
}

// Remove image from all in-memory state
function removeImageFromState(image) {
    uploadedImages = uploadedImages.filter(img => img.url !== image.url);
    selectionOrder = selectionOrder.filter(url => url !== image.url);
    selectionSet.delete(image.url);
    Object.values(variantImages).forEach(vi => {
        if (vi && vi.images) {
            vi.images = vi.images.filter(img => img.url !== image.url);
        }
    });
}

// Update file count in header
function updateFileCount() {
    const countEl = document.getElementById('imp_total_count');
    if (countEl) countEl.textContent = `${uploadedImages.length} files`;
    const grid = document.getElementById('image_grid');
    if (grid && uploadedImages.length === 0) {
        grid.innerHTML = '<div class="no_images_message"><i class="fa fa-cloud-upload-alt"></i><p>No files yet.<br>Upload images or videos to get started.</p></div>';
    }
}

// Remove single image - instant UI, background backend
async function removeUploadedImage(index, event) {
    event.stopPropagation();

    const clickedItem = event.target.closest('.image_item');
    const imageUrl = clickedItem ? clickedItem.getAttribute('data-url') : null;
    const image = imageUrl ? uploadedImages.find(img => img.url === imageUrl) : uploadedImages[index];
    if (!image) return;

    const confirmed = await window.showConfirmDialog('Delete Image?', 'This action cannot be undone.', 'Delete', 'Cancel');
    if (!confirmed) return;

    // 1. Animate out immediately
    if (clickedItem) animateRemoveItem(clickedItem);

    // 2. Remove from state
    removeImageFromState(image);
    updateFileCount();
    updateSelectionBadges();

    // 3. Remove from main product gallery + variant table previews
    removeFromMainGalleryAndVariants(image.url);

    // 4. Delete tracker — show bottom-right animation + lock save button
    if (window.createDeleteTracker) window.createDeleteTracker(1);
    const trackerRow = window.addDeleteTrackerRow ? window.addDeleteTrackerRow(image) : null;

    // 5. Backend delete with tracker
    deleteImageInBackground(image, trackerRow).then(() => {
        if (window.updateDeleteTrackerProgress) window.updateDeleteTrackerProgress(1, 1);
    });
}

// Bulk delete - instant UI, background backend
async function bulkDeleteSelectedImages() {
    const checkedItems = document.querySelectorAll('.image_item .imp_bulk_check.checked');
    if (checkedItems.length === 0) return;

    const items = [];
    checkedItems.forEach(chk => {
        const el = chk.closest('.image_item');
        if (el) items.push({ el, url: el.getAttribute('data-url') });
    });

    const confirmed = await window.showConfirmDialog(
        `Delete ${items.length} images?`, 'This action cannot be undone.', 'Delete All', 'Cancel'
    );
    if (!confirmed) return;

    // 1. Staggered animate out
    items.forEach((item, i) => {
        setTimeout(() => animateRemoveItem(item.el), i * 60);
    });

    // 2. Show delete tracker with total count (locks save button)
    if (window.createDeleteTracker) window.createDeleteTracker(items.length);

    // 3. Remove from state + fire backend deletes + remove from main gallery
    let doneCount = 0;
    const deletePromises = items.map(item => {
        const image = uploadedImages.find(img => img.url === item.url);
        if (!image) return Promise.resolve();
        removeImageFromState(image);
        removeFromMainGalleryAndVariants(image.url);
        const trackerRow = window.addDeleteTrackerRow ? window.addDeleteTrackerRow(image) : null;
        return deleteImageInBackground(image, trackerRow).then(() => {
            doneCount++;
            if (window.updateDeleteTrackerProgress) window.updateDeleteTrackerProgress(doneCount, items.length);
        });
    });

    setTimeout(() => {
        updateFileCount();
        updateSelectionBadges();
        hideBulkDeleteBar();
    }, items.length * 60 + 300);
}

// Re-render the entire image grid (used after upload)
function refreshImageGrid() {
    const grid = document.getElementById('image_grid');
    if (!grid) return;

    if (uploadedImages.length === 0) {
        grid.innerHTML = '<div class="no_images_message"><i class="fa fa-cloud-upload-alt"></i><p>No files yet.<br>Upload images or videos to get started.</p></div>';
    } else {
        grid.innerHTML = generateImageGrid();
    }

    selectionOrder.forEach(url => {
        const item = grid.querySelector(`.image_item[data-url="${CSS.escape(url)}"]`);
        if (item) item.classList.add('selected');
    });
    updateSelectionBadges();
    updateFileCount();
    updateBulkDeleteCount();
}

// Toggle bulk-select checkbox
function toggleBulkCheck(el, event) {
    event.stopPropagation();
    el.classList.toggle('checked');
    updateBulkDeleteCount();
}

// Show/hide bulk delete bar
function updateBulkDeleteCount() {
    const allItems = document.querySelectorAll('.image_item .imp_bulk_check');
    const checked = document.querySelectorAll('.image_item .imp_bulk_check.checked').length;
    let bar = document.getElementById('bulkDeleteBar');

    // Sync master checkbox
    const masterCb = document.getElementById('imp_select_all_cb');
    if (masterCb) {
        if (checked === 0) {
            masterCb.checked = false;
            masterCb.indeterminate = false;
        } else if (checked === allItems.length) {
            masterCb.checked = true;
            masterCb.indeterminate = false;
        } else {
            masterCb.checked = false;
            masterCb.indeterminate = true;
        }
    }

    if (checked > 0) {
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'bulkDeleteBar';
            bar.className = 'imp_bulk_bar';
            const toolbar = document.querySelector('.imp_toolbar');
            if (toolbar) toolbar.after(bar);
        }
        bar.innerHTML = `
            <span><strong>${checked}</strong> selected</span>
            <button type="button" class="imp_bulk_delete_btn" onclick="bulkDeleteSelectedImages()">
                <i class="fa fa-trash-alt"></i> Delete Selected
            </button>
            <button type="button" class="imp_bulk_cancel_btn" onclick="clearBulkSelection()">
                Cancel
            </button>
        `;
        bar.style.display = 'flex';
    } else {
        hideBulkDeleteBar();
    }
}

function hideBulkDeleteBar() {
    const bar = document.getElementById('bulkDeleteBar');
    if (bar) bar.style.display = 'none';
}

function clearBulkSelection() {
    document.querySelectorAll('.imp_bulk_check.checked').forEach(el => el.classList.remove('checked'));
    hideBulkDeleteBar();
    const cb = document.getElementById('imp_select_all_cb');
    if (cb) { cb.checked = false; cb.indeterminate = false; }
}

function toggleSelectAllBulk(masterCb) {
    const items = document.querySelectorAll('.image_item .imp_bulk_check');
    items.forEach(el => {
        if (masterCb.checked) {
            el.classList.add('checked');
        } else {
            el.classList.remove('checked');
        }
    });
    updateBulkDeleteCount();
}

// Close image picker modal
function closeImagePicker() {
    const modal = document.getElementById('image_picker_modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// Track files that were unlinked from variants (deleted from variant images, not from DB)
let unlinkedVariantFiles = new Set();

// Prepare variants data for form submission
function prepareVariantsForSubmission() {
    if (singleItemMode()) {
        // Its variant is written from the Pricing card's boxes. A saved one
        // is left to that; a new product still takes the "no variants" pass
        // for its images, which the server keeps from deleting anything.
        const saved = liveRowIndices().length > 0;
        return saved
            ? { product_variant_list: [], deleted_variant_ids: [], deleted_files: Array.from(unlinkedVariantFiles) }
            : { delete_all_variants: true, deleted_files: Array.from(unlinkedVariantFiles) };
    }
    const combinations = generateCombinations();
    // Saved variants the page never drew (a product whose variants have no
    // option values at all) are not ones anybody deleted: "delete all"
    // would take them.
    let savedVariants = 0;
    try { savedVariants = JSON.parse(window.product_variant_list_data || '[]').length; } catch (e) { savedVariants = 0; }
    if (combinations.length < savedVariants) {
        return {
            product_variant_list: [],
            deleted_variant_ids: Array.from(removedVariantIds),
            deleted_files: Array.from(unlinkedVariantFiles)
        };
    }
    if (combinations.every((_, index) => deletedVariantIndices.has(index))) {
        return { delete_all_variants: true, deleted_files: Array.from(unlinkedVariantFiles) };
    }

    const product_variant_list = [];

    combinations.forEach((combo, index) => {
        // Skip deleted variants
        if (deletedVariantIndices.has(index)) {
            console.log('Skipping deleted variant at index:', index);
            return;
        }

        // Generate variant SKU from combination values
        const variantValues = Object.values(combo).join('-').toLowerCase().replace(/\s+/g, '');

        // Get form values for this variant
        const priceInput = document.querySelector(`input[name="variant_price_${index + 1}"]`);
        const costInput = document.querySelector(`input[name="variant_cost_${index + 1}"]`);
        const quantityInput = document.querySelector(`input[name="variant_quantity_${index + 1}"]`);
        const skuInput = document.querySelector(`input[name="variant_sku_${index + 1}"]`);
        const barcodeInput = document.querySelector(`input[name="variant_barcode_${index + 1}"]`);
        const featuredInput = document.querySelector(`input[name="variant_featured_${index + 1}"]`);

        // Normalize decimal inputs (convert comma to dot)
        if (priceInput && priceInput.value) {
            priceInput.value = priceInput.value.replace(',', '.');
        }
        if (costInput && costInput.value) {
            costInput.value = costInput.value.replace(',', '.');
        }
        if (quantityInput && quantityInput.value) {
            quantityInput.value = quantityInput.value.replace(',', '.');
        }

        // Get images for this variant
        const variantImg = variantImages[index];
        const hasImages = variantImg && variantImg.images && variantImg.images.length > 0;

        // DEBUG: Log what we found
        console.log(`prepareVariantsForSubmission: index=${index}, variantImg:`, variantImg);
        console.log(`  hasImages=${hasImages}, images count=${variantImg?.images?.length || 0}`);

        // Resolve the stable variant_id (if this is an existing variant
        // being edited) so the backend can update by id — that way the
        // user can rename variant_sku without orphaning the row + losing
        // its images. Lookup key is the attribute combo, which is stable
        // across SKU renames.
        const _existingForId = existingVariantData[index] || {};
        const _variantId = _existingForId.variant_id || '';

        const variantData = {
            variant_id: _variantId,
            variant_sku: skuInput && skuInput.value ? skuInput.value : variantValues,
            variant_attribute_values: combo,
            variant_price: priceInput ? parseFloat(priceInput.value) || 0 : 0,
            variant_cost: costInput && costInput.value !== '' ? parseFloat(costInput.value) : null,
            variant_quantity: quantityInput ? parseFloat(quantityInput.value) || 0 : 0,
            variant_barcode: barcodeInput ? barcodeInput.value : '',
            variant_featured: featuredInput ? featuredInput.checked : true,
        };

        // Add product attributes for this variant from variantAttributesData
        // variantAttributesData is populated by the variant attributes modal (variant_attributes_modal.js)
        if (typeof variantAttributesData !== 'undefined' && variantAttributesData[index] && variantAttributesData[index].length > 0) {
            variantData.product_attributes = variantAttributesData[index];
            console.log(`  ✅ Added ${variantAttributesData[index].length} product attributes to variant ${index}`);
        } else {
            // Also check existingVariantData for attributes that were loaded from backend
            const existingData = existingVariantData[index] || {};
            if (existingData.product_attributes && existingData.product_attributes.length > 0) {
                variantData.product_attributes = existingData.product_attributes;
                console.log(`  ✅ Added ${existingData.product_attributes.length} existing product attributes to variant ${index}`);
            }
        }

        // Add image information
        if (hasImages) {
            variantData.variant_images = variantImg.images.map((img, imgIdx) => ({
                url: img.url,
                name: img.name,
                file: img.file,
                id: img.id,  // Include ID for existing images
                sequence: imgIdx  // Include sequence order
            }));
            variantData.primary_image_index = variantImg.primaryIndex;
            console.log(`  ✅ Added ${variantData.variant_images.length} images to variant ${index}`);
        } else {
            console.log(`  ⚠️ No images for variant ${index}`);
        }

        product_variant_list.push(variantData);
    });

    return {
        product_variant_list,
        deleted_variant_ids: Array.from(removedVariantIds),
        deleted_files: Array.from(unlinkedVariantFiles)
    };
}

// Handle form submission
document.addEventListener('DOMContentLoaded', () => {
    const productForm = document.getElementById('product_form');
    if (productForm) {
        productForm.addEventListener('submit', function (e) {
            const submitStartTime = performance.now();
            console.log('\n=== FORM SUBMIT STARTED ===');

            // Check for duplicate SKUs before submitting
            const dupCheckStart = performance.now();
            const allSkuInputs = document.querySelectorAll('input[name*="variant_sku"]');
            const skus = [];
            const duplicates = [];

            allSkuInputs.forEach(input => {
                const sku = input.value.trim().toLowerCase();
                if (sku) {
                    if (skus.includes(sku)) {
                        duplicates.push(sku);
                    } else {
                        skus.push(sku);
                    }
                }
            });

            const rowProblems = variantRowProblems();
            if (rowProblems.length > 0) {
                e.preventDefault();
                showErrorModal((window.VARIANT_T && window.VARIANT_T.rows_title) || 'Check the variants', rowProblems[0]);
                return false;
            }

            const dupCheckTime = performance.now() - dupCheckStart;
            console.log(`✓ Duplicate check: ${dupCheckTime.toFixed(2)}ms`);

            // If duplicates found, prevent submission
            if (duplicates.length > 0) {
                e.preventDefault();
                console.log('❌ Form submission blocked - duplicate SKU found');

                // Show modern error modal
                showErrorModal(
                    'Duplicate SKU Detected',
                    `Cannot submit form: Duplicate SKU "${duplicates[0]}" found.\n\nEach variant must have a unique SKU. Please correct the duplicate SKU(s) before submitting.`
                );

                // Highlight the duplicate SKU inputs
                allSkuInputs.forEach(input => {
                    const sku = input.value.trim().toLowerCase();
                    if (duplicates.includes(sku)) {
                        input.style.borderColor = 'red';
                        input.style.backgroundColor = '#fee';
                        input.focus();
                    }
                });

                return false;
            }

            // New product: variants need the product SKU to hang off, and
            // each needs a part of its own after the dot.
            if (skuRuleOn() && hasOptionValues()) {
                const variantSkus = document.querySelectorAll('input[name^="variant_sku_"]');
                if (variantSkus.length) {
                    const parent = skuParent();
                    if (!parent) {
                        e.preventDefault();
                        showErrorModal(skuRuleMsg('skuMsgTitle'), skuRuleMsg('skuMsgParent'));
                        document.getElementById('id_sku')?.focus();
                        return false;
                    }
                    const bare = Array.from(variantSkus).some(inp => !skuSuffixOf(inp.value, parent));
                    if (bare) {
                        e.preventDefault();
                        showErrorModal(skuRuleMsg('skuMsgTitle'), skuRuleMsg('skuMsgSuffix'));
                        return false;
                    }
                }
            }

            // Prepare variants data
            const prepareStart = performance.now();
            console.log('\n════════════ [SAVE] Variant state right before submit ════════════');
            Object.keys(variantImages).forEach(key => {
                const vi = variantImages[key];
                const imgs = (vi && vi.images) || [];
                console.log(`  Variant index ${key}: ${imgs.length} images`);
                imgs.forEach((img, i) => {
                    console.log(`    [${i}] id=${img.id} url=...${(img.url || '').slice(-50)}`);
                });
            });
            console.log(`  unlinkedVariantFiles (${unlinkedVariantFiles.size}):`, Array.from(unlinkedVariantFiles));
            console.log('══════════════════════════════════════════════════════════════════\n');

            const variantsData = prepareVariantsForSubmission();
            const prepareTime = performance.now() - prepareStart;
            console.log(`✓ Prepare variants data: ${prepareTime.toFixed(2)}ms`);
            console.log(`  - ${variantsData.product_variant_list?.length || 0} variants prepared`);

            // Create or update hidden input for variants_json
            const jsonStart = performance.now();
            let variantsInput = document.getElementById('variants_json_input');
            if (!variantsInput) {
                variantsInput = document.createElement('input');
                variantsInput.type = 'hidden';
                variantsInput.id = 'variants_json_input';
                variantsInput.name = 'variants_json';
                productForm.appendChild(variantsInput);
            }
            variantsInput.value = JSON.stringify(variantsData);
            const jsonTime = performance.now() - jsonStart;
            console.log(`✓ JSON stringify: ${jsonTime.toFixed(2)}ms`);

            // ─── Send attribute value images (color swatches) ───
            // Format: { "color": { "red": { "name": "Red", "url": "..." }, ... } }
            const attrValueImages = {};
            Object.values(variantData).forEach(opt => {
                const optName = (opt.name || '').toLowerCase().trim();
                if (!optName || !opt.imagesByValue) return;
                const byValue = {};
                Object.entries(opt.imagesByValue).forEach(([val, info]) => {
                    if (!info || !info.url) return;
                    const normKey = val.toLowerCase().replace(/\s+/g, '_');
                    // Use stored display_name if present, fall back to the original key
                    const displayName = (info.display_name || val).trim();
                    byValue[normKey] = { name: displayName, url: info.url };
                });
                if (Object.keys(byValue).length > 0) attrValueImages[optName] = byValue;
            });

            let attrImagesInput = document.getElementById('attribute_value_images_input');
            if (!attrImagesInput) {
                attrImagesInput = document.createElement('input');
                attrImagesInput.type = 'hidden';
                attrImagesInput.id = 'attribute_value_images_input';
                attrImagesInput.name = 'attribute_value_images';
                productForm.appendChild(attrImagesInput);
            }
            attrImagesInput.value = JSON.stringify(attrValueImages);
            console.log('Attribute value images:', attrValueImages);

            console.log('Submitting variants data:', variantsData);

            // DEBUG: Log each variant's images
            if (variantsData.product_variant_list) {
                variantsData.product_variant_list.forEach((variant, idx) => {
                    if (variant.variant_images && variant.variant_images.length > 0) {
                        console.log(`Variant ${idx + 1} (${variant.variant_sku}) has ${variant.variant_images.length} images:`);
                        variant.variant_images.forEach(img => {
                            console.log(`  - ID: ${img.id}, URL: ${img.url}`);
                        });
                    } else {
                        console.log(`Variant ${idx + 1} (${variant.variant_sku}) has NO images`);
                    }
                });
            }

            // Handle variant images upload
            const imagesStart = performance.now();
            let totalImages = 0;
            if (variantsData.product_variant_list) {
                variantsData.product_variant_list.forEach((variant, index) => {
                    if (variant.variant_images && variant.variant_images.length > 0) {
                        totalImages += variant.variant_images.length;
                        console.log(`Processing images for variant ${index + 1}:`, variant.variant_images);

                        // Create file inputs for variant images
                        const dt = new DataTransfer();
                        let addedCount = 0;

                        variant.variant_images.forEach(img => {
                            if (img.file && img.file instanceof File) {
                                dt.items.add(img.file);
                                addedCount++;
                                console.log(`Added file: ${img.file.name}`);
                            } else {
                                console.warn(`Skipping invalid file for variant ${index + 1}:`, img);
                            }
                        });

                        if (addedCount > 0) {
                            // Create a file input for this variant's images
                            let fileInput = document.querySelector(`input[name="variant_file_${index + 1}"]`);
                            if (!fileInput) {
                                fileInput = document.createElement('input');
                                fileInput.type = 'file';
                                fileInput.name = `variant_file_${index + 1}`;
                                fileInput.multiple = true;
                                fileInput.style.display = 'none';
                                productForm.appendChild(fileInput);
                            }
                            fileInput.files = dt.files;

                            console.log(`Successfully added ${addedCount} files for variant ${index + 1}`);
                        } else {
                            console.warn(`No valid files found for variant ${index + 1}`);
                        }
                    }
                });
            }
            const imagesTime = performance.now() - imagesStart;
            console.log(`✓ Process images: ${imagesTime.toFixed(2)}ms (${totalImages} images)`);

            const totalTime = performance.now() - submitStartTime;
            console.log(`\n⏱️  TOTAL FORM SUBMIT TIME: ${totalTime.toFixed(2)}ms`);
            console.log('=== FORM SUBMIT COMPLETED ===\n');
        });
    }
});

// Update grouping dropdown options + popover
function updateGroupingOptions() {
    const select = document.getElementById('grouping_select');
    const grpContainer = document.getElementById('grp_container');
    const grpOptions = document.getElementById('grp_options');
    const grpSelectedText = document.getElementById('grp_selected_text');
    if (!select) return;

    const optionNames = Object.values(variantData)
        .filter(d => d.name)
        .map(d => d.name);

    const uniqueNames = [...new Set(optionNames.map(n => n.toLowerCase()))];

    if (uniqueNames.length === 0) {
        const table = document.getElementById('variant_table');
        if (table) table.style.display = 'none';
        if (grpContainer) grpContainer.style.display = 'none';
        select.innerHTML = '';
        return;
    }

    // Update hidden select
    let optionsHTML = '';
    uniqueNames.forEach(name => {
        optionsHTML += `<option value="${name}">${name}</option>`;
    });
    select.innerHTML = optionsHTML;
    if (select.options.length > 0) select.selectedIndex = 0;

    // Build popover options
    if (grpOptions) {
        let html = '';
        uniqueNames.forEach((name, idx) => {
            html += `<div class="grp_option${idx === 0 ? ' active' : ''}" data-value="${name}" onclick="selectGroupingOption(this)">
                <span>${name}</span>
                <span class="grp_option_check"><i class="fa fa-check"></i></span>
            </div>`;
        });
        grpOptions.innerHTML = html;
    }
    if (grpSelectedText) grpSelectedText.textContent = uniqueNames[0];
    if (grpContainer) grpContainer.style.display = 'inline-flex';
}

// Toggle popover open/close
function toggleGroupingPopover() {
    const popover = document.getElementById('grp_popover');
    if (!popover) return;
    popover.classList.toggle('open');

    // Close on outside click
    if (popover.classList.contains('open')) {
        setTimeout(() => {
            document.addEventListener('click', closeGroupingPopoverOutside);
        }, 0);
    }
}

function closeGroupingPopoverOutside(e) {
    const wrap = document.querySelector('.grp_trigger_wrap');
    if (wrap && !wrap.contains(e.target)) {
        const popover = document.getElementById('grp_popover');
        if (popover) popover.classList.remove('open');
        document.removeEventListener('click', closeGroupingPopoverOutside);
    }
}

// Select an option from popover
function selectGroupingOption(el) {
    const value = el.dataset.value;

    // Update active state
    document.querySelectorAll('.grp_option').forEach(o => o.classList.remove('active'));
    el.classList.add('active');

    // Update trigger text
    const grpSelectedText = document.getElementById('grp_selected_text');
    if (grpSelectedText) grpSelectedText.textContent = value;

    // Close popover
    const popover = document.getElementById('grp_popover');
    if (popover) popover.classList.remove('open');
    document.removeEventListener('click', closeGroupingPopoverOutside);

    // Sync hidden select & filter
    const select = document.getElementById('grouping_select');
    if (select) {
        select.value = value;
        filterVariantTableByGroup();
    }
}

// Delete a variant row
async function deleteVariantRow(index, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    // Use modern confirmation from instant_file_manager.js
    const confirmed = await window.showConfirmDialog(
        'Delete Variant?',
        'This variant and all its images will be removed.',
        'Delete',
        'Cancel'
    );

    if (confirmed) {
        // Get variant ID from table row
        const row = document.querySelector(`tr[data-variant-index="${index}"]`);
        const variantId = row ? row.getAttribute('data-variant-id') : null;

        // If variant exists in DB, delete via API
        if (variantId && variantId.trim()) {
            try {
                const response = await fetch('/marketing/api/instant_delete_variant/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : getCsrfToken()
                    },
                    body: JSON.stringify({ variant_id: variantId })
                });

                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error || 'Delete failed');
                }

                showToast('✅ Variant deleted!', 'success');
            } catch (error) {
                console.error('Delete error:', error);
                showToast(`❌ Delete failed: ${error.message}`, 'error');
                return; // Don't remove from UI if delete failed
            }
        }

        // Mark this index as deleted (for newly created variants not in DB yet)
        deletedVariantIndices.add(index);

        // Remove from variantImages if exists
        if (variantImages[index]) {
            delete variantImages[index];
        }

        // Get the variant's attribute values before removing
        const combinations = generateCombinations();
        const deletedVariant = combinations[index];
        console.log('Deleted variant attributes:', deletedVariant);

        // Remove the specific row from table using data-variant-index attribute
        if (row) {
            row.remove();
            console.log('Removed row from table');
        } else {
            console.warn('Row not found for index:', index);
        }

        // Check which values are now unused and remove them from options
        // removeUnusedOptionValues(deletedVariant);

        // Refresh table to update group headers and totals
        updateVariantTable();

        // Check if table is empty now (only header left)
        const table = document.getElementById('variant_table');
        if (table) {
            const tbody = table.querySelector('tbody');
            const remainingRows = tbody ? tbody.querySelectorAll('tr:not(.group_header_row)').length : 0;

            console.log('Remaining variant rows:', remainingRows);

            // If no variants left, hide table and grouping
            if (remainingRows === 0) {
                table.style.display = 'none';
                const _grp2 = document.getElementById('grp_container');
                if (_grp2) _grp2.style.display = 'none';
                console.log('No variants left - hiding table');
            }
        }

        console.log('Deleted variant at index:', index);
        console.log('All deleted indices:', Array.from(deletedVariantIndices));
    }
}

// Helper function to get CSRF token (fallback if window.getCookie doesn't exist)
function getCsrfToken() {
    const name = 'csrftoken';
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

// Remove option values that are no longer used by any remaining variants
function removeUnusedOptionValues(deletedVariant) {
    if (!deletedVariant) return;

    // Get all remaining combinations (excluding deleted ones)
    const remainingCombinations = generateCombinations().filter((_, idx) => !deletedVariantIndices.has(idx));

    console.log('Remaining combinations:', remainingCombinations.length);

    // For each attribute in the deleted variant
    Object.entries(deletedVariant).forEach(([optionName, optionValue]) => {
        // Check if this value is still used by any remaining variant
        const isValueStillUsed = remainingCombinations.some(combo =>
            combo[optionName] && combo[optionName].toLowerCase() === optionValue.toLowerCase()
        );

        if (!isValueStillUsed) {
            console.log(`Value "${optionValue}" for option "${optionName}" is no longer used - removing`);

            // Find the option in variantData
            const optionId = Object.keys(variantData).find(id =>
                variantData[id].name && variantData[id].name.toLowerCase() === optionName.toLowerCase()
            );

            if (optionId && variantData[optionId]) {
                // Remove the value from variantData
                const valueIndex = variantData[optionId].values.findIndex(v =>
                    v && v.toLowerCase() === optionValue.toLowerCase()
                );

                if (valueIndex !== -1) {
                    variantData[optionId].values.splice(valueIndex, 1);
                    console.log(`Removed value from variantData`);

                    // Remove the value field from DOM
                    const valuesList = document.getElementById(`${optionId}_values`);
                    if (valuesList) {
                        const valueField = valuesList.querySelector(`[data-value-index="${valueIndex}"]`);
                        if (valueField) {
                            valueField.remove();
                            console.log(`Removed value field from DOM`);

                            // Reindex remaining fields
                            Array.from(valuesList.children).forEach((child, idx) => {
                                child.setAttribute('data-value-index', idx);
                                const input = child.querySelector('.value_input');
                                if (input) {
                                    input.setAttribute('oninput', `updateOptionValue('${optionId}', ${idx}, this.value)`);
                                }
                                const btn = child.querySelector('.btn_remove_value');
                                if (btn) {
                                    btn.setAttribute('onclick', `removeValue('${optionId}', ${idx})`);
                                }
                            });
                        }
                    }

                    // If no values left for this option, remove the entire option
                    const remainingValues = variantData[optionId].values.filter(v => v && v.trim());
                    if (remainingValues.length === 0) {
                        console.log(`No values left for option "${optionName}" - removing option`);
                        removeOption(optionId);
                    }
                }
            }
        }
    });

    // Regenerate table with updated options
    updateVariantTable();
    updateGroupingOptions();
}


// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-size: 14px;
        animation: slideInRight 0.3s, slideOutRight 0.3s 2.7s;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);
    setTimeout(() => document.body.removeChild(toast), 3000);
}

// Debug helper - expose to console
window.debugVariantImages = function () {
    console.log('=== DEBUG INFO ===');
    console.log('uploadedImages:', uploadedImages);
    console.log('variantImages:', variantImages);
    console.log('variantData:', variantData);
};

// Modern error modal
function showErrorModal(title, message) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
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
        animation: fadeIn 0.2s;
    `;

    // Create modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 0;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        animation: slideIn 0.3s;
    `;

    modal.innerHTML = `
        <div style="padding: 24px; border-bottom: 1px solid #e5e7eb;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: #fee; display: flex; align-items: center; justify-content: center;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <h3 style="margin: 0; font-size: 20px; font-weight: 600; color: #111;">${title}</h3>
            </div>
        </div>
        <div style="padding: 24px;">
            <p style="margin: 0; line-height: 1.6; color: #374151; white-space: pre-line;">${message}</p>
        </div>
        <div style="padding: 16px 24px; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end;">
            <button id="modal-close-btn" style="
                background: #ef4444;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
            ">OK</button>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        #modal-close-btn:hover {
            background: #dc2626 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
        }
    `;
    document.head.appendChild(style);

    // Close modal on button click
    const closeBtn = overlay.querySelector('#modal-close-btn');
    closeBtn.onclick = () => {
        overlay.style.animation = 'fadeOut 0.2s';
        setTimeout(() => {
            document.body.removeChild(overlay);
            document.head.removeChild(style);
        }, 200);
    };

    // Close on overlay click
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            closeBtn.click();
        }
    };
}

// Real-time duplicate detection for option names, values and SKUs
console.log('Duplicate detection loaded for modern variant form!');

document.addEventListener('input', function (e) {
    const target = e.target;

    // Check option name inputs
    if (target.classList.contains('option_name_field')) {
        checkDuplicateOptionName(target);
    }

    // Check option value inputs  
    if (target.classList.contains('value_input')) {
        checkDuplicateOptionValue(target);
    }

    // Check SKU inputs in variant table
    if (target.name && target.name.includes('variant_sku')) {
        checkDuplicateSku(target);
    }
});

function checkDuplicateOptionName(input) {
    const currentValue = input.value.trim().toLowerCase();

    // Remove existing error message
    let errorMsg = input.parentElement.querySelector('.duplicate-error');
    if (errorMsg) errorMsg.remove();

    if (!currentValue) {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false;
    }

    const allOptionNames = document.querySelectorAll('.option_name_field');
    let isDuplicate = false;

    allOptionNames.forEach(otherInput => {
        if (otherInput !== input && otherInput.value.trim().toLowerCase() === currentValue) {
            isDuplicate = true;
        }
    });

    if (isDuplicate) {
        input.style.color = 'red';
        input.style.borderColor = 'red';
        input.style.backgroundColor = '#fee';

        // Add error message below input
        const error = document.createElement('div');
        error.className = 'duplicate-error';
        error.style.cssText = 'color: red; font-size: 12px; margin-top: 4px;';
        error.textContent = '⚠️ This option name already exists';
        input.parentElement.appendChild(error);

        return true; // Is duplicate
    } else {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false; // Not duplicate
    }
}

function checkDuplicateOptionValue(input) {
    const currentValue = input.value.trim().toLowerCase();

    // Remove existing error message
    let errorMsg = input.parentElement.querySelector('.duplicate-error');
    if (errorMsg) errorMsg.remove();

    if (!currentValue) {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false;
    }

    // Get the parent option card to find sibling values
    const optionCard = input.closest('.variant_option_card');
    if (!optionCard) return false;

    const allValues = optionCard.querySelectorAll('.value_input');
    let isDuplicate = false;

    allValues.forEach(otherInput => {
        if (otherInput !== input && otherInput.value.trim().toLowerCase() === currentValue) {
            isDuplicate = true;
        }
    });

    if (isDuplicate) {
        input.style.color = 'red';
        input.style.borderColor = 'red';
        input.style.backgroundColor = '#fee';

        // Add error message below input
        const error = document.createElement('div');
        error.className = 'duplicate-error';
        error.style.cssText = 'color: red; font-size: 12px; margin-top: 4px;';
        error.textContent = '⚠️ This value already exists';
        input.parentElement.appendChild(error);

        return true; // Is duplicate
    } else {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false; // Not duplicate
    }
}

function checkDuplicateSku(input) {
    const currentValue = input.value.trim().toLowerCase();

    // Remove existing error message
    const cell = input.closest('td');
    if (cell) {
        let errorMsg = cell.querySelector('.duplicate-error');
        if (errorMsg) errorMsg.remove();
    }

    if (!currentValue) {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false;
    }

    const allSkus = document.querySelectorAll('input[name*="variant_sku"]');
    let isDuplicate = false;

    allSkus.forEach(otherInput => {
        if (otherInput !== input && otherInput.value.trim().toLowerCase() === currentValue) {
            isDuplicate = true;
        }
    });

    if (isDuplicate) {
        input.style.color = 'red';
        input.style.borderColor = 'red';
        input.style.backgroundColor = '#fee';

        // Add error message below input
        if (cell) {
            const error = document.createElement('div');
            error.className = 'duplicate-error';
            error.style.cssText = 'color: red; font-size: 11px; margin-top: 4px;';
            error.textContent = '⚠️ Duplicate SKU';
            cell.appendChild(error);
        }

        return true; // Is duplicate
    } else {
        input.style.color = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        return false; // Not duplicate
    }
}



// Variant Detail Modal Functions

function openVariantDetailModal(variantIndex) {
    currentEditingVariantIndex = variantIndex;
    const modal = document.getElementById('variant_detail_modal');
    if (!modal) return;

    // Get current values from hidden inputs
    // We can rely on the hidden inputs we just generated in renderVariantTable
    // Note: renderVariantTable MUST have been called at least once.

    // Select inputs using variant index (1-based for name attributes)
    const idx = variantIndex + 1;
    const price = document.querySelector(`input[name="variant_price_${idx}"]`)?.value || '';
    const cost = document.querySelector(`input[name="variant_cost_${idx}"]`)?.value || '';
    const sku = document.querySelector(`input[name="variant_sku_${idx}"]`)?.value || '';
    const barcode = document.querySelector(`input[name="variant_barcode_${idx}"]`)?.value || '';
    const activeInput = document.querySelector(`input[name="variant_active_${idx}"]`);
    const isActive = activeInput ? (activeInput.value === 'true') : true;

    // Populate modal inputs
    const priceEl = document.getElementById('modal_variant_price');
    const costEl = document.getElementById('modal_variant_cost');
    const skuEl = document.getElementById('modal_variant_sku');
    const barcodeEl = document.getElementById('modal_variant_barcode');
    const activeEl = document.getElementById('modal_variant_active');

    if (priceEl) priceEl.value = price;
    if (costEl) {
        const computed = (window.computedVariantCosts || {})[sku];
        const locked = computed !== undefined;
        costEl.value = locked ? computed : cost;
        costEl.readOnly = locked;
        costEl.style.background = locked ? '#F3F4F6' : '';
        costEl.style.cursor = locked ? 'not-allowed' : '';
        const hint = document.getElementById('modal_variant_cost_hint');
        if (hint) hint.hidden = !locked;
    }
    if (skuEl) skuEl.value = sku;
    if (barcodeEl) barcodeEl.value = barcode;
    if (activeEl) activeEl.checked = isActive;

    // New product: the product SKU is a fixed prefix, only the part after
    // the dot is typed.
    const prefixEl = document.getElementById('modal_variant_sku_prefix');
    const hintEl = document.getElementById('modal_variant_sku_hint');
    if (skuRuleOn()) {
        const parent = skuParent();
        const suffix = skuSuffixOf(sku, parent);
        if (skuEl) skuEl.value = suffix === null ? sku : suffix;
        if (prefixEl) { prefixEl.textContent = parent + '.'; prefixEl.hidden = !parent; }
        if (hintEl) hintEl.hidden = false;
    } else {
        if (prefixEl) prefixEl.hidden = true;
        if (hintEl) hintEl.hidden = true;
    }

    const titleEl = document.getElementById('variant_modal_title');
    if (titleEl) titleEl.textContent = `Edit Variant #${idx}`;

    modal.style.display = 'flex';
}

function closeVariantDetailModal() {
    const modal = document.getElementById('variant_detail_modal');
    if (modal) {
        modal.style.display = 'none';
        // Remove hash to clean URL if needed
        // window.location.hash = '';
    }
    currentEditingVariantIndex = null;
}

function saveVariantDetailModal() {
    if (currentEditingVariantIndex === null) return;

    const idx = currentEditingVariantIndex + 1;

    // Get values from modal
    const price = document.getElementById('modal_variant_price').value;
    const cost = document.getElementById('modal_variant_cost').value;
    let sku = document.getElementById('modal_variant_sku').value;
    if (skuRuleOn()) sku = skuJoin(skuParent(), skuSuffixClean(sku));
    const barcode = document.getElementById('modal_variant_barcode').value;
    const isActive = document.getElementById('modal_variant_active').checked;

    // Update DOM inputs (hidden and visible)
    const priceInput = document.querySelector(`input[name="variant_price_${idx}"]`);
    const costInput = document.querySelector(`input[name="variant_cost_${idx}"]`);
    const skuInput = document.querySelector(`input[name="variant_sku_${idx}"]`);
    const barcodeInput = document.querySelector(`input[name="variant_barcode_${idx}"]`);
    const activeInput = document.querySelector(`input[name="variant_active_${idx}"]`);

    if (priceInput) priceInput.value = price;
    // A computed cost was only shown, never typed: the stored one stays.
    if (costInput && !document.getElementById('modal_variant_cost').readOnly) costInput.value = cost;
    if (skuInput) skuInput.value = sku;
    if (barcodeInput) barcodeInput.value = barcode;
    if (activeInput) activeInput.value = isActive;

    // Trigger price range update if explicit group row exists
    const row = document.querySelector(`tr[data-variant-index="${currentEditingVariantIndex}"]`);
    if (row && row.classList.length > 1) {
        row.classList.forEach(cls => {
            if (cls.startsWith('group_')) {
                // Check if updateGroupPriceRange exists before calling
                if (typeof updateGroupPriceRange === 'function') {
                    updateGroupPriceRange(cls);
                }
            }
        });
    }

    closeVariantDetailModal();
}

// Remove a deleted image URL from ALL variant image arrays and update their UI
function removeImageFromAllVariants(deletedUrl) {
    if (!deletedUrl) return;

    Object.keys(variantImages).forEach(vIdx => {
        const vi = variantImages[vIdx];
        if (!vi || !vi.images) return;

        const before = vi.images.length;
        vi.images = vi.images.filter(img => img.url !== deletedUrl);

        if (vi.images.length !== before) {
            // Reset primary index
            if (vi.images.length === 0) {
                vi.primaryIndex = 0;
            } else if (vi.primaryIndex >= vi.images.length) {
                vi.primaryIndex = 0;
            }
            updateVariantImagePreview(parseInt(vIdx));
        }
    });
}

// Remove a deleted image from main gallery + all variant table previews
function removeFromMainGalleryAndVariants(deletedUrl) {
    if (!deletedUrl) return;
    removeImageFromMainGallery(deletedUrl);
    removeImageFromPrimaryPicker(deletedUrl);
    if (typeof removeImageFromAllVariants === 'function') {
        removeImageFromAllVariants(deletedUrl);
    }
}

// Remove a deleted image URL from the primary image picker grid
function removeImageFromPrimaryPicker(deletedUrl) {
    if (!deletedUrl) return;
    const grid = document.getElementById('primary_picker_grid');
    if (!grid) return;

    const normalizedUrl = deletedUrl.split('?')[0];
    let wasPrimary = false;

    grid.querySelectorAll('.primary-picker-item').forEach(item => {
        const img = item.querySelector('img');
        if (!img) return;
        const imgSrc = img.src.split('?')[0];
        if (imgSrc === normalizedUrl || imgSrc.endsWith(normalizedUrl) || normalizedUrl.endsWith(imgSrc.replace(location.origin, ''))) {
            if (item.classList.contains('active')) wasPrimary = true;
            item.style.transition = 'transform 0.2s ease, opacity 0.2s ease';
            item.style.transform = 'scale(0.7)';
            item.style.opacity = '0';
            setTimeout(() => item.remove(), 200);
        }
    });

    // If deleted item was the current primary, update the preview to first remaining image
    if (wasPrimary) {
        setTimeout(() => {
            const first = grid.querySelector('.primary-picker-item img');
            const previewImg = document.getElementById('primary_preview_img');
            const previewEmpty = document.getElementById('primary_preview_empty');
            const manualPrimaryInput = document.getElementById('manual_primary_image');

            if (first) {
                const firstItem = first.closest('.primary-picker-item');
                const firstId = firstItem?.dataset.fileId;
                if (previewImg) previewImg.src = first.src;
                if (firstItem) firstItem.classList.add('active');
                if (manualPrimaryInput && firstId) manualPrimaryInput.value = firstId;
            } else {
                if (previewImg) previewImg.style.display = 'none';
                if (previewEmpty) previewEmpty.style.display = '';
                if (manualPrimaryInput) manualPrimaryInput.value = '';
            }
        }, 220);
    }
}

// Add a newly uploaded image to the main Media gallery instantly
function addImageToMainGallery(image) {
    if (!image || !image.url) return;

    const gallery = document.getElementById('sortable_images');
    if (!gallery) return;

    // Don't add duplicates
    const normalizedUrl = image.url.split('?')[0];
    const exists = Array.from(gallery.querySelectorAll('.media-item img, .sortable-image img'))
        .some(img => img.src.split('?')[0] === normalizedUrl);
    if (exists) return;

    const isVideo = image.file_type === 'video';
    const displayUrl = image.optimized_url || image.url;
    const fileId = image.id || '';

    const div = document.createElement('div');
    div.className = 'media-item sortable-image';
    div.dataset.fileId = fileId;
    div.dataset.fileType = image.file_type || 'image';
    div.style.cssText = 'opacity:0; transform:scale(0.8); transition: opacity 0.3s ease, transform 0.3s ease;';

    div.innerHTML = `
        <div class="media-preview" onclick="openMediaPreview('${displayUrl}', '${image.file_type || 'image'}', ${fileId || 'null'})">
            ${isVideo
                ? `<img src="${displayUrl}" /><div class="play-icon"><i class="fa fa-play"></i></div>`
                : `<img src="${displayUrl}" /><div class="preview-icon"><i class="fa fa-search-plus"></i></div>`
            }
        </div>
        <div class="media-actions">
            <button type="button" class="icon-btn delete-btn instant-delete-btn" data-file-id="${fileId}">
                <i class="fa fa-trash"></i>
            </button>
            <div class="drag-handle"><i class="fa fa-grip-vertical"></i></div>
        </div>
    `;

    // Insert before the "Add Media" placeholder
    const placeholder = gallery.querySelector('.media-upload-placeholder');
    if (placeholder) {
        gallery.insertBefore(div, placeholder);
    } else {
        gallery.appendChild(div);
    }

    // Animate in
    requestAnimationFrame(() => {
        div.style.opacity = '1';
        div.style.transform = 'scale(1)';
    });

    // Attach delete handler
    const deleteBtn = div.querySelector('.instant-delete-btn');
    if (deleteBtn && typeof instantDeleteFile === 'function') {
        deleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            instantDeleteFile(fileId, div);
        });
    }
}

// Remove a deleted image URL from the main product gallery (non-variant images)
function removeImageFromMainGallery(deletedUrl) {
    if (!deletedUrl) return;

    const gallery = document.getElementById('sortable_images');
    if (!gallery) return;

    // Normalize for comparison (src may have origin prepended)
    const normalizedUrl = deletedUrl.split('?')[0];

    gallery.querySelectorAll('.media-item, .sortable-image').forEach(item => {
        const img = item.querySelector('img');
        if (!img) return;
        const imgSrc = img.src.split('?')[0];
        if (imgSrc === normalizedUrl || imgSrc.endsWith(normalizedUrl) || normalizedUrl.endsWith(imgSrc.replace(location.origin, ''))) {
            item.style.transition = 'transform 0.25s ease, opacity 0.25s ease';
            item.style.transform = 'scale(0.7)';
            item.style.opacity = '0';
            setTimeout(() => {
                item.remove();
                if (typeof updatePrimaryBadge === 'function') updatePrimaryBadge();
                if (typeof updateImageOrder === 'function') updateImageOrder();
            }, 250);
        }
    });
}
