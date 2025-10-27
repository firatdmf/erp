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
function removeValue(optionId, valueIndex) {
    const valuesList = document.getElementById(`${optionId}_values`);
    if (!valuesList) return;
    
    const wrapper = valuesList.querySelector(`[data-value-index="${valueIndex}"]`);
    const deletedValue = wrapper ? wrapper.querySelector('.value_input')?.value : '';
    
    if (!deletedValue || !deletedValue.trim()) {
        // If empty value, just remove the field
        if (wrapper) wrapper.remove();
        return;
    }
    
    // SINGLE confirmation (like deleteVariantRow)
    if (!confirm('Are you sure you want to delete this variant?')) {
        return;
    }
    
    // Find all variant indices that have this value
    const combinations = generateCombinations();
    const optionName = variantData[optionId]?.name;
    const table = document.getElementById('variant_table');
    
    if (optionName && deletedValue && table) {
        combinations.forEach((combo, index) => {
            if (combo[optionName] === deletedValue) {
                // SAME logic as deleteVariantRow - no confirmation here
                deletedVariantIndices.add(index);
                
                // Remove from variantImages if exists
                if (variantImages[index]) {
                    delete variantImages[index];
                }
                
                // Remove the row from table DOM
                if (table.rows[index + 1]) {
                    table.rows[index + 1].remove();
                }
                
                console.log('Deleted variant at index:', index);
            }
        });
        
        console.log('All deleted indices:', Array.from(deletedVariantIndices));
    }
    
    // Remove the value field from DOM (visual only)
    if (wrapper) wrapper.remove();
    
    // DON'T modify variantData - keep it as is so indices stay correct!
    // The variants are already marked as deleted via deletedVariantIndices
    
    // Reindex remaining fields (visual only, variantData unchanged)
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
            // Filter out empty/whitespace values
            values: data.values.filter(v => v && typeof v === 'string' && v.trim())
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
    
    console.log('Table should be visible now');
}

// Render variant table with given combinations
function renderVariantTable(combinations, selectedGrouping = null) {
    const table = document.getElementById('variant_table');
    if (!table) return;
    
    // If a specific grouping is selected, show only that option column
    let displayOptions = [];
    if (selectedGrouping) {
        displayOptions = [selectedGrouping];
    } else {
        // Get all option names for headers
        displayOptions = Object.values(variantData)
            .filter(d => d.name)
            .map(d => d.name);
    }
    
    // Build table HTML
    let tableHTML = '<thead><tr><th>ACTIONS</th>';
    displayOptions.forEach(name => {
        tableHTML += `<th>${name.toUpperCase()}</th>`;
    });
    tableHTML += '<th>PRICE</th><th>STOCK</th><th>PHOTO</th><th>SKU</th><th>BARCODE</th><th>FEATURED</th></tr></thead><tbody>';
    
    combinations.forEach((combo, index) => {
        tableHTML += `<tr><td><button type="button" class="btn_delete_variant" onclick="deleteVariantRow(${index})" title="Delete variant"><i class="fa fa-trash"></i></button></td>`;
        
        // Only show selected option values
        displayOptions.forEach(optionName => {
            const value = combo[optionName] || '';
            tableHTML += `<td>${value}</td>`;
        });
        
        // Create key for looking up existing data
        const attrKey = Object.entries(combo)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([key, val]) => `${key}:${val}`)
            .join('|');
        
        const existingData = existingVariantData[attrKey] || {};
        
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
    
    tableHTML += '</tbody>';
    table.innerHTML = tableHTML;
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
    
    // If still no selection, return
    if (!selectedOption) {
        return;
    }
    
    // Get unique values for the selected option
    const uniqueValues = [...new Set(allCombinations.map(combo => combo[selectedOption]).filter(Boolean))];
    
    // Create simplified combinations with only the selected option
    const filteredCombinations = uniqueValues.map(value => {
        return { [selectedOption]: value };
    });
    
    renderVariantTable(filteredCombinations, selectedOption);
}

// Render variant images as thumbnails
function renderVariantImages(variantIndex) {
    const variantImg = variantImages[variantIndex];
    if (!variantImg || !variantImg.images || variantImg.images.length === 0) {
        return '';
    }
    
    // First image is always primary
    variantImg.primaryIndex = 0;
    
    return variantImg.images.map((img, idx) => {
        const isPrimary = idx === 0;
        return `
            <div class="variant_thumb ${isPrimary ? 'primary' : ''}" 
                 data-variant-index="${variantIndex}" 
                 data-image-index="${idx}" 
                 draggable="true"
                 ondragstart="dragStartVariantImage(event, ${variantIndex}, ${idx})"
                 ondragover="dragOverVariantImage(event)"
                 ondrop="dropVariantImage(event, ${variantIndex}, ${idx})"
                 ondragend="dragEndVariantImage(event)"
                 title="${isPrimary ? 'Primary image - Drag to reorder' : 'Drag to reorder'}">
                <span class="drag_handle_variant"><i class="fa fa-grip-vertical"></i></span>
                <img src="${img.url}" alt="Variant image">
                ${isPrimary ? '<div class="primary_label">PRIMARY</div>' : ''}
                <button type="button" class="remove_variant_img" onclick="event.stopPropagation(); removeVariantImage(${variantIndex}, ${idx})" title="Remove image">
                    <i class="fa fa-times"></i>
                </button>
            </div>
        `;
    }).join('');
}

// Drag and drop handlers for variant images
let draggedVariantImage = null;

function dragStartVariantImage(event, variantIndex, imageIndex) {
    draggedVariantImage = { variantIndex, imageIndex };
    event.target.style.opacity = '0.5';
}

function dragOverVariantImage(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function dropVariantImage(event, targetVariantIndex, targetImageIndex) {
    event.preventDefault();
    
    if (!draggedVariantImage || draggedVariantImage.variantIndex !== targetVariantIndex) return;
    
    const fromIndex = draggedVariantImage.imageIndex;
    const toIndex = targetImageIndex;
    
    if (fromIndex === toIndex) return;
    
    // Reorder images
    const images = variantImages[targetVariantIndex].images;
    const [movedImage] = images.splice(fromIndex, 1);
    images.splice(toIndex, 0, movedImage);
    
    // First image is always primary
    variantImages[targetVariantIndex].primaryIndex = 0;
    
    // Re-render
    updateVariantImagePreview(targetVariantIndex);
}

function dragEndVariantImage(event) {
    event.target.style.opacity = '1';
    draggedVariantImage = null;
}

// Remove image from variant
function removeVariantImage(variantIndex, imageIndex) {
    if (!variantImages[variantIndex]) return;
    
    if (confirm('Remove this image?')) {
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
}

// Open image picker modal
let currentVariantIndex = null;

function openImagePicker(variantIndex) {
    currentVariantIndex = variantIndex;
    
    // Initialize variant images if not exists
    if (!variantImages[variantIndex]) {
        variantImages[variantIndex] = { images: [], primaryIndex: 0 };
    }
    
    // Copy existing images to uploadedImages so they appear in modal
    const existingImages = variantImages[variantIndex].images || [];
    // Add existing images to uploadedImages if not already there
    existingImages.forEach(img => {
        if (!uploadedImages.find(u => u.url === img.url)) {
            uploadedImages.push(img);
        }
    });
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'image_picker_modal';
    modal.className = 'image_modal';
    
    const selectedImages = variantImages[variantIndex].images.map(img => img.url);
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
                    ${generateImageGrid(selectedImages, primaryIndex)}
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
function generateImageGrid(selectedImages, primaryIndex) {
    if (uploadedImages.length === 0) {
        return '<div class="no_images_message"><i class="fa fa-image"></i><p>No images uploaded yet. Use the \"Add File\" button above to add images.</p></div>';
    }
    
    return uploadedImages.map((img, idx) => {
        const isSelected = selectedImages.includes(img.url);
        const isPrimary = isSelected && selectedImages.indexOf(img.url) === primaryIndex;
        
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

// Handle image upload
function handleImageUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    // Process each file
    Array.from(files).forEach(file => {
        // Check if it's an image
        if (!file.type.startsWith('image/')) {
            alert(`${file.name} is not an image file.`);
            return;
        }
        
        // Create a FileReader to read the image
        const reader = new FileReader();
        reader.onload = function(e) {
            // Add image to uploaded images array
            uploadedImages.push({
                url: e.target.result,
                name: file.name,
                file: file
            });
            
            // Refresh the image grid
            const grid = document.getElementById('image_grid');
            if (grid) {
                const variantImgs = variantImages[currentVariantIndex];
                const selectedImages = variantImgs ? variantImgs.images.map(img => img.url) : [];
                const primaryIndex = variantImgs ? variantImgs.primaryIndex : 0;
                grid.innerHTML = generateImageGrid(selectedImages, primaryIndex);
            }
        };
        reader.readAsDataURL(file);
    });
    
    // Clear the input so the same file can be uploaded again if needed
    event.target.value = '';
}

// Confirm image selection
function confirmImageSelection() {
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
            file: uploadedImg ? uploadedImg.file : null
        });
    });
    
    // Store selected images - first image is always primary
    variantImages[currentVariantIndex] = {
        images: images,
        primaryIndex: 0  // First image is always primary
    };
    
    console.log(`Variant ${currentVariantIndex} images:`, variantImages[currentVariantIndex]);
    
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

// Remove uploaded image
function removeUploadedImage(index, event) {
    event.stopPropagation(); // Prevent toggling selection
    
    if (confirm('Are you sure you want to delete this image?')) {
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

// Prepare variants data for form submission
function prepareVariantsForSubmission() {
    const combinations = generateCombinations();
    if (combinations.length === 0) {
        return { delete_all_variants: true, deleted_files: [] };
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
        
        // Get images for this variant
        const variantImg = variantImages[index];
        const hasImages = variantImg && variantImg.images && variantImg.images.length > 0;
        
        const variantData = {
            variant_sku: skuInput && skuInput.value ? skuInput.value : variantValues,
            variant_attribute_values: combo,
            variant_price: priceInput ? parseFloat(priceInput.value) || 0 : 0,
            variant_quantity: quantityInput ? parseInt(quantityInput.value) || 0 : 0,
            variant_barcode: barcodeInput ? barcodeInput.value : '',
            variant_featured: featuredInput ? featuredInput.checked : true,
        };
        
        // Add image information
        if (hasImages) {
            variantData.variant_images = variantImg.images.map(img => ({
                url: img.url,
                name: img.name,
                file: img.file
            }));
            variantData.primary_image_index = variantImg.primaryIndex;
        }
        
        product_variant_list.push(variantData);
    });
    
    return { product_variant_list };
}

// Handle form submission
document.addEventListener('DOMContentLoaded', () => {
    const productForm = document.getElementById('product_form');
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            // Prepare variants data
            const variantsData = prepareVariantsForSubmission();
            
            // Create or update hidden input for variants_json
            let variantsInput = document.getElementById('variants_json_input');
            if (!variantsInput) {
                variantsInput = document.createElement('input');
                variantsInput.type = 'hidden';
                variantsInput.id = 'variants_json_input';
                variantsInput.name = 'variants_json';
                productForm.appendChild(variantsInput);
            }
            variantsInput.value = JSON.stringify(variantsData);
            
            console.log('Submitting variants data:', variantsData);
            
            // Handle variant images upload
            if (variantsData.product_variant_list) {
                variantsData.product_variant_list.forEach((variant, index) => {
                    if (variant.variant_images && variant.variant_images.length > 0) {
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
        });
    }
});

// Update grouping dropdown options
function updateGroupingOptions() {
    const select = document.getElementById('grouping_select');
    if (!select) return;
    
    const optionNames = Object.values(variantData)
        .filter(d => d.name)
        .map(d => d.name);
    
    // If no options, hide table and grouping
    if (optionNames.length === 0) {
        const table = document.getElementById('variant_table');
        const grouping = document.getElementById('variant_grouping');
        if (table) table.style.display = 'none';
        if (grouping) grouping.style.display = 'none';
        select.innerHTML = '';
        return;
    }
    
    let optionsHTML = '';
    optionNames.forEach(name => {
        optionsHTML += `<option value="${name}">${name}</option>`;
    });
    
    select.innerHTML = optionsHTML;
    
    // Auto-select first option after updating
    if (select.options.length > 0) {
        select.selectedIndex = 0;
    }
}

// Delete a variant row
function deleteVariantRow(index) {
    if (confirm('Are you sure you want to delete this variant?')) {
        // Mark this index as deleted
        deletedVariantIndices.add(index);
        
        // Remove from variantImages if exists
        if (variantImages[index]) {
            delete variantImages[index];
        }
        
        // Re-render table without this row
        const table = document.getElementById('variant_table');
        if (table && table.rows[index + 1]) { // +1 because row 0 is header
            table.rows[index + 1].remove();
        }
        
        console.log('Deleted variant at index:', index);
        console.log('All deleted indices:', Array.from(deletedVariantIndices));
    }
}

// Debug helper - expose to console
window.debugVariantImages = function() {
    console.log('=== DEBUG INFO ===');
    console.log('uploadedImages:', uploadedImages);
    console.log('variantImages:', variantImages);
    console.log('variantData:', variantData);
};


