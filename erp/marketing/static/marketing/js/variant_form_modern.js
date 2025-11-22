// Modern Variant Form System - Auto-updating with real-time table generation
let optionCounter = 0;
let variantData = {};
let variantImages = {}; // Store images for each variant: { variantIndex: { images: [], primaryIndex: 0 } }

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('variant_component')) {
        // Load existing variants if in edit mode
        loadExistingVariants();
    }
});

// Load existing variants from backend data
function loadExistingVariants() {
    const variantListData = window.product_variant_list_data;
    const variantOptionsData = window.product_variant_options_data;

    console.log('Loading existing variants...');
    console.log('Variant list:', variantListData);
    console.log('Variant options:', variantOptionsData);

    if (!variantOptionsData || variantOptionsData === '[]' || variantOptionsData === '') {
        console.log('No existing variants to load');
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
                                <label>Option Name</label>
                                <input type="text" 
                                       placeholder="e.g. Size, Color" 
                                       value="${option.name}"
                                       oninput="updateOptionName('${optionId}', this.value)"
                                       class="option_name_field">
                            </div>
                        </div>
                        <div class="option_values_section">
                            <label>Option Values</label>
                            <div class="option_values_list" id="${optionId}_values"></div>
                            <button type="button" class="btn_add_value" onclick="addValueField('${optionId}')">
                                <i class="fa fa-plus"></i> Add another value
                            </button>
                        </div>
                        <div class="option_actions">
                            <button type="button" class="btn_remove_option" onclick="removeOption('${optionId}')">
                                Delete
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

            // Load variant images if available
            loadExistingVariantImages();
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

        // Store variant data keyed by attribute values for easy lookup
        variants.forEach(variant => {
            // Create a key from attribute values (e.g., "color:white|size:1")
            const attrKey = Object.entries(variant.variant_attribute_values)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, val]) => `${key}:${val}`)
                .join('|');

            existingVariantData[attrKey] = {
                variant_id: variant.variant_id,
                price: variant.variant_price,
                quantity: variant.variant_quantity,
                sku: variant.variant_sku,
                barcode: variant.variant_barcode,
                featured: variant.variant_featured,
                images: []
            };
        });

        // Load variant images if available
        if (variantFilesData && variantFilesData !== '{}') {
            const filesDict = JSON.parse(variantFilesData);
            console.log('Variant files:', filesDict);

            // Map images to variants
            variants.forEach(variant => {
                const files = filesDict[variant.variant_sku];
                if (files && files.length > 0) {
                    const attrKey = Object.entries(variant.variant_attribute_values)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([key, val]) => `${key}:${val}`)
                        .join('|');

                    if (existingVariantData[attrKey]) {
                        existingVariantData[attrKey].images = files.map(f => ({
                            id: f.id,  // Add file ID for deletion tracking
                            url: f.url,
                            name: f.name || f.url.split('/').pop()
                        }));
                    }
                }
            });
        }

        console.log('Loaded existing variant data:', existingVariantData);
    } catch (e) {
        console.error('Error loading variant data:', e);
    }
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
                    <label>Option Name</label>
                    <input type="text" 
                           placeholder="e.g. Size, Color" 
                           oninput="updateOptionName('${optionId}', this.value)"
                           class="option_name_field">
                </div>
            </div>
            <div class="option_values_section">
                <label>Option Values</label>
                <div class="option_values_list" id="${optionId}_values"></div>
                <button type="button" class="btn_add_value" onclick="addValueField('${optionId}')">
                    <i class="fa fa-plus"></i> Add another value
                </button>
            </div>
            <div class="option_actions">
                <button type="button" class="btn_remove_option" onclick="removeOption('${optionId}')">
                    Delete
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
                   placeholder="${valueIndex === 0 ? '' : 'Add another value'}" 
                   value="${value}"
                   oninput="updateOptionValue('${optionId}', ${valueIndex}, this.value)"
                   class="value_input">
            <button type="button" class="btn_remove_value" onclick="removeValue('${optionId}', ${valueIndex})">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    `;

    valuesList.insertAdjacentHTML('beforeend', valueHTML);
}

// Update option name
function updateOptionName(optionId, name) {
    if (!variantData[optionId]) return;
    variantData[optionId].name = name;
    updateVariantTable();
    updateGroupingOptions();
}

// Update option value
function updateOptionValue(optionId, valueIndex, value) {
    if (!variantData[optionId]) return;

    // Ensure values array exists
    if (!variantData[optionId].values) {
        variantData[optionId].values = [];
    }

    variantData[optionId].values[valueIndex] = value;

    // Auto-add new field if this is the last field and has value
    const valuesList = document.getElementById(`${optionId}_values`);
    if (!valuesList) return;

    const isLastField = valueIndex === valuesList.children.length - 1;

    if (value.trim() && isLastField) {
        addValueField(optionId);
    }

    updateVariantTable();
}

// Remove option
function removeOption(optionId) {
    delete variantData[optionId];
    const element = document.getElementById(optionId);
    if (element) element.remove();
    updateVariantTable();
    updateGroupingOptions();
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

    // 1. BACKUP CURRENT STATE
    // We map all current variants by their unique signature (e.g. "Color:Red|Size:L")
    // This allows us to restore data to the correct variant even if indices change
    const variantBackup = {};
    const currentCombinations = generateCombinations();

    currentCombinations.forEach((combo, index) => {
        // Skip if this index is marked as deleted (user manually deleted this specific variant row)
        if (deletedVariantIndices.has(index)) return;

        // Create unique signature key
        const signature = createVariantSignature(combo);

        // Backup images
        const images = variantImages[index];

        // Backup input values from DOM
        // We try to get values from inputs first, then fall back to existingVariantData
        const priceInput = document.querySelector(`input[name="variant_price_${index + 1}"]`);
        const quantityInput = document.querySelector(`input[name="variant_quantity_${index + 1}"]`);
        const skuInput = document.querySelector(`input[name="variant_sku_${index + 1}"]`);
        const barcodeInput = document.querySelector(`input[name="variant_barcode_${index + 1}"]`);
        const featuredInput = document.querySelector(`input[name="variant_featured_${index + 1}"]`);

        // Get ID from row data attribute
        const row = document.querySelector(`tr[data-variant-index="${index}"]`);
        const variantId = row ? row.getAttribute('data-variant-id') : '';

        variantBackup[signature] = {
            images: images ? JSON.parse(JSON.stringify(images)) : null, // Deep copy images
            price: priceInput ? priceInput.value : '',
            quantity: quantityInput ? quantityInput.value : '',
            sku: skuInput ? skuInput.value : '',
            barcode: barcodeInput ? barcodeInput.value : '',
            featured: featuredInput ? featuredInput.checked : true,
            variant_id: variantId
        };
    });

    console.log('Variant backup created:', Object.keys(variantBackup).length, 'items');

    // 2. UPDATE DATA MODEL (Actually remove the value)
    if (variantData[optionId] && variantData[optionId].values) {
        variantData[optionId].values.splice(valueIndex, 1);
    }

    // 3. UPDATE DOM
    if (wrapper) wrapper.remove();
    reindexDomFields(valuesList, optionId);

    // 4. REGENERATE & RESTORE
    // Clear global trackers
    variantImages = {};
    deletedVariantIndices.clear(); // Clear deleted indices as we are regenerating table

    // Generate new combinations based on updated variantData
    const newCombinations = generateCombinations();

    // Update existingVariantData with our backup
    // renderVariantTable uses existingVariantData to populate the table
    existingVariantData = {}; // Clear old cache

    newCombinations.forEach((combo, newIndex) => {
        const signature = createVariantSignature(combo);
        const backup = variantBackup[signature];

        if (backup) {
            // Restore images to global variantImages
            if (backup.images) {
                variantImages[newIndex] = backup.images;
            }

            // Update existingVariantData so renderVariantTable picks it up
            existingVariantData[signature] = {
                variant_id: backup.variant_id,
                price: backup.price,
                quantity: backup.quantity,
                sku: backup.sku,
                barcode: backup.barcode,
                featured: backup.featured,
                images: backup.images ? backup.images.images : []
            };
        }
    });

    console.log('Restored data for', Object.keys(existingVariantData).length, 'variants');

    // 5. RENDER
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

// Generate variant combinations
function generateCombinations() {
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
            values: [...new Set(data.values
                .filter(v => v && typeof v === 'string' && v.trim())
                .map(v => v.trim().toLowerCase()))]
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

// Store all combinations globally for filtering
let allCombinations = [];
// Store existing variant data from backend
let existingVariantData = {};
// Track deleted variant indices
let deletedVariantIndices = new Set();

// Update variant table with combinations
function updateVariantTable() {
    console.log('updateVariantTable called');
    allCombinations = generateCombinations();
    console.log('Generated', allCombinations.length, 'combinations');

    const table = document.getElementById('variant_table');
    const grouping = document.getElementById('variant_grouping');

    if (!table) {
        console.error('variant_table not found!');
        return;
    }

    if (allCombinations.length === 0) {
        console.log('No combinations, hiding table');
        table.style.display = 'none';
        if (grouping) grouping.style.display = 'none';
        toggleProductImagesSection();
        return;
    }

    console.log('Showing table with', allCombinations.length, 'combinations');
    table.style.display = 'table';
    table.style.visibility = 'visible';
    if (grouping) {
        grouping.style.display = 'flex';
        grouping.style.visibility = 'visible';
    }

    // Auto-select first option in grouping dropdown
    const select = document.getElementById('grouping_select');
    if (select && select.options.length > 0) {
        select.selectedIndex = 0;
        filterVariantTableByGroup();
    }

    // Toggle product images section based on variants
    toggleProductImagesSection();

    console.log('Table should be visible now');
}

// Render variant table with given combinations
function renderVariantTable(combinations, selectedGrouping = null) {
    const table = document.getElementById('variant_table');
    if (!table) return;

    // Always show all option names for headers
    const displayOptions = Object.values(variantData)
        .filter(d => d.name)
        .map(d => d.name);

    // Build table HTML
    let tableHTML = '<thead><tr><th>ACTIONS</th>';
    displayOptions.forEach(name => {
        tableHTML += `<th>${name.toUpperCase()}</th>`;
    });
    tableHTML += '<th>PRICE</th><th>STOCK</th><th>PHOTO</th><th>SKU</th><th>BARCODE</th><th>FEATURED</th></tr></thead><tbody>';

    // If grouping is selected, create hierarchical structure
    if (selectedGrouping) {
        // Group all combinations by the selected option
        const grouped = {};
        allCombinations.forEach((combo, index) => {
            const groupValue = combo[selectedGrouping];
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
                    priceRange = `$ ${minPrice.toFixed(2)}`;
                } else {
                    priceRange = `$ ${minPrice.toFixed(2)}-${maxPrice.toFixed(2)}`;
                }
            }

            // Group header row (collapsible)
            const groupId = `group_${groupValue.replace(/\s+/g, '_')}`;
            const variantCount = variants.filter(v => !deletedVariantIndices.has(v.originalIndex)).length;
            tableHTML += `
                <tr class="group_header_row" style="background: #f3f4f6; font-weight: 600; cursor: pointer;" onclick="toggleGroupCollapse('${groupId}')">
                    <td>
                        <i class="fa fa-chevron-down group_toggle_icon" id="icon_${groupId}" style="transition: transform 0.2s;"></i>
                    </td>
                    <td colspan="${displayOptions.length}">
                        <div style="display: flex; flex-direction: column;">
                            <span style="font-weight: 600; color: #111827;">${groupValue}</span>
                            <span style="font-weight: 400; color: #6b7280; font-size: 12px; margin-top: 2px;">Tümünü genişlet</span>
                        </div>
                    </td>
                    <td id="price_range_${groupId}">${priceRange}</td>
                    <td colspan="5"></td>
                </tr>
            `;

            // Render all variants in this group
            variants.forEach(({ combo, originalIndex }) => {
                // Skip deleted variants
                if (deletedVariantIndices.has(originalIndex)) return;

                // Create key for looking up existing data - MUST BE FIRST
                const attrKey = Object.entries(combo)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, val]) => `${key}:${val}`)
                    .join('|');

                const existingData = existingVariantData[attrKey] || {};
                const variantId = existingData.variant_id || '';

                tableHTML += `<tr class="variant_row ${groupId}" data-variant-index="${originalIndex}" data-variant-id="${variantId}" style="background: white;">`;
                tableHTML += `<td style="padding-left: 30px;"><button type="button" class="btn_delete_variant" onclick="deleteVariantRow(${originalIndex}, event)" title="Delete variant"><i class="fa fa-trash"></i></button></td>`;

                // Show all option values
                displayOptions.forEach(optionName => {
                    const value = combo[optionName] || '';
                    tableHTML += `<td>${value}</td>`;
                });

                // Try to read current form values first (preserves user input during re-render)
                const priceInput = document.querySelector(`input[name="variant_price_${originalIndex + 1}"]`);
                const quantityInput = document.querySelector(`input[name="variant_quantity_${originalIndex + 1}"]`);
                const skuInput = document.querySelector(`input[name="variant_sku_${originalIndex + 1}"]`);
                const barcodeInput = document.querySelector(`input[name="variant_barcode_${originalIndex + 1}"]`);
                const featuredInput = document.querySelector(`input[name="variant_featured_${originalIndex + 1}"]`);

                const price = priceInput?.value || existingData.price || '';
                const quantity = quantityInput?.value || existingData.quantity || '';
                const sku = skuInput?.value || existingData.sku || '';
                const barcode = barcodeInput?.value || existingData.barcode || '';
                const featured = featuredInput ? featuredInput.checked : (existingData.featured !== false);

                // Load existing images for this variant
                if (existingData.images && existingData.images.length > 0 && !variantImages[originalIndex]) {
                    variantImages[originalIndex] = {
                        images: existingData.images,
                        primaryIndex: 0
                    };
                }

                const variantImagesHtml = renderVariantImages(originalIndex);

                tableHTML += `
                    <td><input type="number" name="variant_price_${originalIndex + 1}" step="0.01" placeholder="0.00" value="${price}" style="min-width: 100px;" oninput="updateGroupPriceRange('${groupId}')"></td>
                    <td><input type="number" name="variant_quantity_${originalIndex + 1}" step="0.01" placeholder="0" value="${quantity}" style="min-width: 60px;"></td>
                    <td>
                        <button type="button" class="photo_picker_btn" onclick="openImagePicker(${originalIndex})" title="Select images">
                            <i class="fa fa-camera"></i>
                        </button>
                        <div class="variant_images_preview" id="variant_images_${originalIndex}">
                            ${variantImagesHtml}
                        </div>
                    </td>
                    <td><input type="text" name="variant_sku_${originalIndex + 1}" value="${sku}" style="min-width: 120px;"></td>
                    <td><input type="text" name="variant_barcode_${originalIndex + 1}" value="${barcode}" style="min-width: 120px;"></td>
                    <td style="text-align: center;"><input type="checkbox" name="variant_featured_${originalIndex + 1}" ${featured ? 'checked' : ''}></td>
                </tr>`;
            });
        });
    } else {
        // No grouping - show all variants flat
        allCombinations.forEach((combo, index) => {
            // Skip deleted variants
            if (deletedVariantIndices.has(index)) return;

            // Create key for looking up existing data - MUST BE FIRST
            const attrKey = Object.entries(combo)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, val]) => `${key}:${val}`)
                .join('|');

            const existingData = existingVariantData[attrKey] || {};
            const variantId = existingData.variant_id || '';

            tableHTML += `<tr data-variant-index="${index}" data-variant-id="${variantId}"><td><button type="button" class="btn_delete_variant" onclick="deleteVariantRow(${index}, event)" title="Delete variant"><i class="fa fa-trash"></i></button></td>`;

            // Show all option values
            displayOptions.forEach(optionName => {
                const value = combo[optionName] || '';
                tableHTML += `<td>${value}</td>`;
            });

            // Try to read current form values first (preserves user input during re-render)
            const priceInput = document.querySelector(`input[name="variant_price_${index + 1}"]`);
            const quantityInput = document.querySelector(`input[name="variant_quantity_${index + 1}"]`);
            const skuInput = document.querySelector(`input[name="variant_sku_${index + 1}"]`);
            const barcodeInput = document.querySelector(`input[name="variant_barcode_${index + 1}"]`);
            const featuredInput = document.querySelector(`input[name="variant_featured_${index + 1}"]`);

            const price = priceInput?.value || existingData.price || '';
            const quantity = quantityInput?.value || existingData.quantity || '';
            const sku = skuInput?.value || existingData.sku || '';
            const barcode = barcodeInput?.value || existingData.barcode || '';
            const featured = featuredInput ? featuredInput.checked : (existingData.featured !== false);

            // Load existing images for this variant
            if (existingData.images && existingData.images.length > 0 && !variantImages[index]) {
                variantImages[index] = {
                    images: existingData.images,
                    primaryIndex: 0
                };
            }

            const variantImagesHtml = renderVariantImages(index);

            tableHTML += `
                <td><input type="number" name="variant_price_${index + 1}" step="0.01" placeholder="0.00" value="${price}" style="min-width: 100px;"></td>
                <td><input type="number" name="variant_quantity_${index + 1}" step="0.01" placeholder="0" value="${quantity}" style="min-width: 60px;"></td>
                <td>
                    <button type="button" class="photo_picker_btn" onclick="openImagePicker(${index})" title="Select images">
                        <i class="fa fa-camera"></i>
                    </button>
                    <div class="variant_images_preview" id="variant_images_${index}">
                        ${variantImagesHtml}
                    </div>
                </td>
                <td><input type="text" name="variant_sku_${index + 1}" value="${sku}" style="min-width: 120px;"></td>
                <td><input type="text" name="variant_barcode_${index + 1}" value="${barcode}" style="min-width: 120px;"></td>
                <td style="text-align: center;"><input type="checkbox" name="variant_featured_${index + 1}" ${featured ? 'checked' : ''}></td>
            </tr>`;
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
            priceRange = `$ ${minPrice.toFixed(2)}`;
        } else {
            priceRange = `$ ${minPrice.toFixed(2)}-${maxPrice.toFixed(2)}`;
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
        return `
            <div class="variant-sortable-image" data-image-id="${img.id}" style="position: relative; border: 2px solid ${isPrimary ? '#667eea' : '#e5e7eb'}; border-radius: 6px; padding: 4px; background: white; width: 60px; height: 60px; cursor: move;">
                ${isPrimary ? '<div style="position: absolute; top: -6px; left: 4px; background: #667eea; color: white; padding: 1px 4px; border-radius: 8px; font-size: 8px; font-weight: 600; z-index: 1;">PRIMARY</div>' : ''}
                <img src="${img.url}" alt="Variant image" style="width: 100%; height: 50px; object-fit: cover; border-radius: 4px;">
                <button type="button" class="remove-variant-btn" onclick="event.stopPropagation(); removeVariantImage(${variantIndex}, ${idx})" style="position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; border: none; border-radius: 3px; padding: 1px 3px; font-size: 8px; cursor: pointer;">
                    <i class="fa fa-times"></i>
                </button>
            </div>
        `;
    }).join('');

    // Initialize sortable after rendering
    setTimeout(() => initVariantSortable(variantIndex), 0);

    return html;
}

// Initialize simple sortable for variant images
function initVariantSortable(variantIndex) {
    const container = document.getElementById(`variant_images_${variantIndex}`);
    if (!container) return;

    // Set flex layout
    container.style.display = 'flex';
    container.style.flexWrap = 'wrap';
    container.style.gap = '8px';
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

    // Add badge to first
    const first = container.querySelector('.variant-sortable-image');
    if (first) {
        first.style.borderColor = '#667eea';
        const badge = document.createElement('div');
        badge.textContent = 'PRIMARY';
        badge.style.cssText = 'position: absolute; top: -6px; left: 4px; background: #667eea; color: white; padding: 1px 4px; border-radius: 8px; font-size: 8px; font-weight: 600;';
        first.insertBefore(badge, first.firstChild);
    }
}

// Remove image from variant
function removeVariantImage(variantIndex, imageIndex) {
    if (!variantImages[variantIndex]) return;

    const img = variantImages[variantIndex].images[imageIndex];
    if (!img) return;

    // Track for backend unlinking (if image has DB ID)
    if (img.id) {
        unlinkedVariantFiles.add(img.id);
        console.log('Tracking unlinked file:', img.id);
    }

    // Remove from frontend array (no confirmation, just unlink)
    variantImages[variantIndex].images.splice(imageIndex, 1);

    // Adjust primary index if needed
    if (variantImages[variantIndex].images.length === 0) {
        variantImages[variantIndex].primaryIndex = 0;
    } else if (imageIndex === variantImages[variantIndex].primaryIndex) {
        variantImages[variantIndex].primaryIndex = 0; // Set first as primary
    } else if (imageIndex < variantImages[variantIndex].primaryIndex) {
        variantImages[variantIndex].primaryIndex--;
    }

    // Update preview
    updateVariantImagePreview(variantIndex);
}

// Open image picker modal
let currentVariantIndex = null;

async function openImagePicker(variantIndex) {
    currentVariantIndex = variantIndex;

    // Initialize variant images if not exists
    if (!variantImages[variantIndex]) {
        variantImages[variantIndex] = { images: [], primaryIndex: 0 };
    }

    // CLEAR uploadedImages and reload from scratch to prevent duplicates
    uploadedImages = [];

    // Check if product edit or create mode
    const productEditMatch = window.location.pathname.match(/\/product_edit\/(\d+)\//)?.[1];
    const isCreateMode = window.location.pathname.includes('/product_create/');

    if (productEditMatch) {
        // Edit mode: Load from API
        try {
            const response = await fetch(`/marketing/api/get_product_files/?product_id=${productEditMatch}`);
            const data = await response.json();
            if (data.success && data.files) {
                // Replace uploadedImages with fresh data from API
                uploadedImages = data.files.map(file => ({
                    id: file.id,
                    url: file.url,
                    name: file.name,
                    variant: file.variant || null,  // Include variant info from API
                    file: null  // No file object needed (already uploaded)
                }));
                console.log(`Loaded ${uploadedImages.length} files from shared pool`);
            }
        } catch (error) {
            console.error('Error loading product files:', error);
        }
    } else if (isCreateMode) {
        // Create mode: Load from main product images grid (temp files)
        const mainImageGrid = document.getElementById('sortable_images');
        if (mainImageGrid) {
            const mainImages = mainImageGrid.querySelectorAll('.sortable-image');
            uploadedImages = Array.from(mainImages).map((imgDiv, idx) => {
                const img = imgDiv.querySelector('img');
                return {
                    id: imgDiv.dataset.fileId || `temp_${idx}`,
                    url: img ? img.src : '',
                    name: `Image ${idx + 1}`,
                    variant: null,
                    file: null,
                    temp_file: true  // Mark as temporary
                };
            });
            console.log(`Loaded ${uploadedImages.length} temp files from main grid`);
        }
    }

    // Create modal
    const modal = document.createElement('div');
    modal.id = 'image_picker_modal';
    modal.className = 'image_modal';

    // Get currently selected images for this variant (by ID, not URL)
    const selectedImageIds = variantImages[variantIndex].images.map(img => img.id).filter(id => id);
    const primaryIndex = variantImages[variantIndex].primaryIndex;

    modal.innerHTML = `
        <div class="image_modal_content">
            <div class="image_modal_header">
                <h3>Select Images</h3>
                <button type="button" class="modal_close" onclick="closeImagePicker()">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            <div class="image_modal_body">
                <div class="image_upload_area">
                    <button type="button" class="btn_upload" onclick="document.getElementById('image_file_input').click()">
                        <i class="fa fa-plus"></i> Add File
                    </button>
                    <input type="file" id="image_file_input" accept="image/*" multiple style="display: none;" onchange="handleImageUpload(event)">
                    <p>Drag and drop images here</p>
                </div>
                <div class="image_grid" id="image_grid">
                    ${generateImageGrid(selectedImageIds, primaryIndex)}
                </div>
            </div>
            <div class="image_modal_footer">
                <button type="button" class="btn_cancel" onclick="closeImagePicker()">Cancel</button>
                <button type="button" class="btn_confirm" onclick="confirmImageSelection()">Done</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

// Store uploaded images globally
let uploadedImages = [];

// Generate image grid from uploaded images
function generateImageGrid(selectedImageIds, primaryIndex) {
    if (uploadedImages.length === 0) {
        return '<div class="no_images_message"><i class="fa fa-image"></i><p>No images uploaded yet. Use the \"Add File\" button above to add images.</p></div>';
    }

    return uploadedImages.map((img, idx) => {
        // Check if this image is selected by ID (not URL)
        const isSelected = img.id && selectedImageIds.includes(img.id);
        const selectedIndex = isSelected ? selectedImageIds.indexOf(img.id) : -1;
        const isPrimary = isSelected && selectedIndex === primaryIndex;

        // No variant badges - shared pool

        return `
            <div class="image_item ${isSelected ? 'selected' : ''}" data-url="${img.url}" data-name="${img.name}" data-index="${idx}" onclick="toggleImageSelection(this, event)">
                <img src="${img.url}" alt="${img.name}">
                <p>${img.name}</p>
                <button type="button" class="remove_image_btn" onclick="removeUploadedImage(${idx}, event)" title="Delete">
                    <i class="fa fa-trash"></i>
                </button>
            </div>
        `;
    }).join('');
}

// Set primary image (only one can be primary)
function setPrimaryImage(imageIndex, event) {
    event.stopPropagation(); // Don't trigger toggleImageSelection

    const clickedItem = document.querySelector(`.image_item[data-index="${imageIndex}"]`);
    if (!clickedItem || !clickedItem.classList.contains('selected')) {
        return; // Only selected images can be primary
    }

    // Remove primary from all checkboxes
    document.querySelectorAll('.image_checkbox input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    // Set this one as primary
    const thisCheckbox = clickedItem.querySelector('input[type="checkbox"]');
    if (thisCheckbox) {
        thisCheckbox.checked = true;
    }
}

// Toggle image selection
function toggleImageSelection(element, event) {
    // Don't toggle if clicking on checkbox or remove button
    if (event.target.closest('.image_checkbox') || event.target.closest('.remove_image_btn')) {
        return;
    }

    const isCurrentlySelected = element.classList.contains('selected');
    const checkboxContainer = element.querySelector('.image_checkbox');
    const checkbox = element.querySelector('input[type="checkbox"]');

    if (isCurrentlySelected) {
        // Deselect
        const wasPrimary = checkbox && checkbox.checked;
        element.classList.remove('selected');
        if (checkboxContainer) checkboxContainer.style.display = 'none';
        if (checkbox) checkbox.checked = false;

        // If this was primary, make first selected image primary
        if (wasPrimary) {
            const remainingSelected = document.querySelectorAll('.image_item.selected');
            if (remainingSelected.length > 0) {
                const firstCheckbox = remainingSelected[0].querySelector('input[type="checkbox"]');
                if (firstCheckbox) firstCheckbox.checked = true;
            }
        }
    } else {
        // Select
        element.classList.add('selected');
        if (checkboxContainer) checkboxContainer.style.display = 'block';

        // If this is the first selected image, make it primary
        const allSelected = document.querySelectorAll('.image_item.selected');
        if (allSelected.length === 1) {
            if (checkbox) checkbox.checked = true;
        }
    }
}

// Handle image upload - INSTANT upload to Cloudinary
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

    // Process each file
    for (const file of files) {
        // Check if it's an image
        if (!file.type.startsWith('image/')) {
            console.warn(`${file.name} is not an image file.`);
            continue;
        }

        // Show progress placeholder
        const grid = document.getElementById('image_grid');
        const placeholder = document.createElement('div');
        placeholder.className = 'image_item uploading';
        placeholder.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f3f4f6;">
                <i class="fa fa-spinner fa-spin" style="font-size: 24px; color: #667eea;"></i>
            </div>
            <p>Uploading...</p>
        `;
        if (grid) grid.appendChild(placeholder);

        try {
            const formData = new FormData();
            formData.append('file', file);

            let apiUrl, data;

            if (isCreateMode) {
                // Create mode: Use temp upload API
                formData.append('file_type', 'variant_image');
                formData.append('variant_temp_id', `variant_${currentVariantIndex}`);
                formData.append('sequence', uploadedImages.length);

                const response = await fetch('/marketing/api/temp_upload_file/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : ''
                    },
                    body: formData
                });

                data = await response.json();

                if (data.success) {
                    // Add to uploadedImages from temp file data
                    uploadedImages.push({
                        url: data.file_data.url,
                        name: data.file_data.name,
                        file: null,
                        id: data.file_data.public_id,  // Use public_id for temp files
                        variant: null,
                        temp_file: true
                    });
                }
            } else {
                // Edit mode: Use instant upload API
                formData.append('product_id', productEditMatch);
                // DO NOT send variant_id - want files unlinked until form submit

                const response = await fetch('/marketing/api/instant_upload_file/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : ''
                    },
                    body: formData
                });

                data = await response.json();

                if (data.success) {
                    // Add to uploadedImages with real URL from Cloudinary
                    uploadedImages.push({
                        url: data.file.url,
                        name: file.name,
                        file: null,
                        id: data.file.id,
                        variant: null
                    });
                }
            }

            if (data && data.success) {
                // Remove placeholder and refresh grid
                if (placeholder) placeholder.remove();

                const variantImgs = variantImages[currentVariantIndex];
                const selectedImages = variantImgs ? variantImgs.images.map(img => img.url) : [];
                const primaryIndex = variantImgs ? variantImgs.primaryIndex : 0;
                if (grid) grid.innerHTML = generateImageGrid(selectedImages, primaryIndex);

                showToast(`✅ ${file.name} uploaded to shared pool!`, 'success');
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            if (placeholder) placeholder.remove();
            showToast(`❌ Upload failed: ${error.message}`, 'error');
        }
    }

    // Clear the input so the same file can be uploaded again if needed
    event.target.value = '';
}

// Get variant ID from table row
function getVariantId(variantIndex) {
    const row = document.querySelector(`tr[data-variant-index="${variantIndex}"]`);
    const variantId = row ? row.getAttribute('data-variant-id') : null;
    // Return null if empty string or null
    return (variantId && variantId.trim()) ? variantId : null;
}

// Confirm image selection
async function confirmImageSelection() {
    const selectedItems = document.querySelectorAll('.image_item.selected');

    if (selectedItems.length === 0) {
        alert('Please select at least one image.');
        return;
    }

    const images = [];

    selectedItems.forEach((item) => {
        const imageUrl = item.getAttribute('data-url');
        const imageName = item.getAttribute('data-name');

        // Find the actual file object from uploadedImages
        const uploadedImg = uploadedImages.find(img => img.url === imageUrl);

        images.push({
            url: imageUrl,
            name: imageName,
            file: uploadedImg ? uploadedImg.file : null,
            id: uploadedImg ? uploadedImg.id : null
        });
    });

    // Store selected images - first image is always primary
    variantImages[currentVariantIndex] = {
        images: images,
        primaryIndex: 0  // First image is always primary
    };

    console.log(`Variant ${currentVariantIndex} images:`, variantImages[currentVariantIndex]);

    // Note: Images are NOT linked to variant here
    // They will be linked when form is submitted
    showToast(`✅ ${images.length} image(s) selected for variant`, 'success');

    // Update preview in table
    updateVariantImagePreview(currentVariantIndex);

    closeImagePicker();
}

// Update variant image preview in table
function updateVariantImagePreview(variantIndex) {
    const previewContainer = document.getElementById(`variant_images_${variantIndex}`);
    if (!previewContainer) return;

    previewContainer.innerHTML = renderVariantImages(variantIndex);
}

// Remove uploaded image - INSTANT delete
async function removeUploadedImage(index, event) {
    event.stopPropagation(); // Prevent toggling selection

    const image = uploadedImages[index];
    if (!image) return;

    // Use modern confirmation
    const confirmed = await window.showConfirmDialog(
        'Delete Image?',
        'This action cannot be undone.',
        'Delete',
        'Cancel'
    );

    if (confirmed) {
        // If image has DB ID, delete from backend
        if (image.id) {
            try {
                const response = await fetch('/marketing/api/instant_delete_file/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : ''
                    },
                    body: JSON.stringify({ file_id: image.id })
                });

                const data = await response.json();
                if (!data.success) {
                    throw new Error(data.error || 'Delete failed');
                }

                showToast('🗑️ Image deleted!', 'success');
            } catch (error) {
                console.error('Delete error:', error);
                showToast(`❌ Delete failed: ${error.message}`, 'error');
                return;
            }
        }

        // Remove from array
        uploadedImages.splice(index, 1);

        // Refresh the grid
        const grid = document.getElementById('image_grid');
        if (grid) {
            const variantImgs = variantImages[currentVariantIndex];
            const selectedImages = variantImgs ? variantImgs.images.map(img => img.url) : [];
            const primaryIndex = variantImgs ? variantImgs.primaryIndex : 0;
            grid.innerHTML = generateImageGrid(selectedImages, primaryIndex);
        }
    }
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
    const combinations = generateCombinations();
    if (combinations.length === 0) {
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
        const quantityInput = document.querySelector(`input[name="variant_quantity_${index + 1}"]`);
        const skuInput = document.querySelector(`input[name="variant_sku_${index + 1}"]`);
        const barcodeInput = document.querySelector(`input[name="variant_barcode_${index + 1}"]`);
        const featuredInput = document.querySelector(`input[name="variant_featured_${index + 1}"]`);

        // Normalize decimal inputs (convert comma to dot)
        if (priceInput && priceInput.value) {
            priceInput.value = priceInput.value.replace(',', '.');
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

        const variantData = {
            variant_sku: skuInput && skuInput.value ? skuInput.value : variantValues,
            variant_attribute_values: combo,
            variant_price: priceInput ? parseFloat(priceInput.value) || 0 : 0,
            variant_quantity: quantityInput ? parseFloat(quantityInput.value) || 0 : 0,
            variant_barcode: barcodeInput ? barcodeInput.value : '',
            variant_featured: featuredInput ? featuredInput.checked : true,
        };

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

            // Prepare variants data
            const prepareStart = performance.now();
            console.log('\n=== VARIANT IMAGES STATE ===');
            console.log('variantImages object:', variantImages);
            Object.keys(variantImages).forEach(key => {
                console.log(`Variant ${key}:`, variantImages[key]);
            });
            console.log('===========================\n');

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

// Update grouping dropdown options
function updateGroupingOptions() {
    const select = document.getElementById('grouping_select');
    if (!select) return;

    // Get unique option names (filter out duplicates)
    const optionNames = Object.values(variantData)
        .filter(d => d.name)
        .map(d => d.name);

    // Remove duplicate names (case-insensitive)
    const uniqueNames = [...new Set(optionNames.map(n => n.toLowerCase()))];

    // If no options, hide table and grouping
    if (uniqueNames.length === 0) {
        const table = document.getElementById('variant_table');
        const grouping = document.getElementById('variant_grouping');
        if (table) table.style.display = 'none';
        if (grouping) grouping.style.display = 'none';
        select.innerHTML = '';
        return;
    }

    let optionsHTML = '';
    uniqueNames.forEach(name => {
        optionsHTML += `<option value="${name}">${name}</option>`;
    });

    select.innerHTML = optionsHTML;

    // Auto-select first option after updating
    if (select.options.length > 0) {
        select.selectedIndex = 0;
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
                const grouping = document.getElementById('variant_grouping');
                if (grouping) grouping.style.display = 'none';
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


