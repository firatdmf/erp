// this will be adjusted and exported at the end to the server
let order_data = {
  "order_items": [
    // { "item_no": 1, "product": { "sku": "", "variant": false }, "description": "", "quantity": 1, "price": 1 },
  ]
}

const order_items_table = document.getElementById("order_items_table");

// index starts from 1, so the first row will be 1
const generate_order_item_row = (index, sku, variant, itemId = null) => {
  console.log("your index is", index);

  // sku, and variant are passed from the product_autocomplete function in the views.py
  let table_header = "";
  // if it is the first row, we need to add the table header
  if (index == 1) {
    table_header = `<tr>
          <th>Item No</th>
          <th>Product</th>
          <th>Description</th>
          <th>Quantity</th>
          <th>Unit Price</th>
          <th>Total</th>
          <th>Delete</th>
        </tr>`
  }
  
  const itemIdField = itemId ? `<input type="hidden" name="item_id_${index}" id="item_id_${index}" value="${itemId}" />` : '';
  
  return `
    ${table_header}
      <tr>
        <td>${index}</td>
        <td>
          <input type="text" readonly value="${sku}" id="sku_${index}" />
          <input type="hidden" name="variant_${index}" id="variant_${index}" value="${variant}" />
          ${itemIdField}
        </td>
        <td>
          <input type="text" name="description_${index}" id="description_${index}" />
        </td>
        <td>
          <input type="number" name="quantity_${index}" id="quantity_${index}" class="quantity-input" data-index="${index}" value="1" min="0" step="0.01"/>
        </td>

        <td>
          <input type="number" name="price_${index}" id="price_${index}" class="price-input" data-index="${index}" value="0" min="0" step="0.01" />
        </td>
        <td>
          <input type="number" name="total_${index}" id="total_${index}" class="total-input" data-index="${index}" value="0" readonly />
        </td>
        <td>
          <div class="delete-row-btn" style="cursor:pointer;">❌</div>
        </td>
      </tr>
    `;
}

// This function is called when a product is selected from the autocomplete
const selectProduct = (sku, variant) => {
  console.log(sku);

  // if the item already exists in the order_items, do not add it again
  if (order_data.order_items.some(item => item.sku === sku)) {
    const product_autocomplete_error = document.getElementById("product_autocomplete_error");
    product_autocomplete_error.innerHTML = `<div class="text-red-500">This product is already added.</div>`;
    setTimeout(() => {
      product_autocomplete_error.innerHTML = "";
    }, 3000);
    return;
  }
  
  const newItem = {
    "sku": sku,
    "variant": variant, // true if it is a variant, false if it is a parent product
    "quantity": 1,
    "price": 0
  };
  
  order_data.order_items.push(newItem);

  console.log("order_data.order_items", order_data.order_items);

  const row = generate_order_item_row(index = order_data.order_items.length, sku = sku, variant = variant);
  order_items_table.insertAdjacentHTML("beforeend", row);

  // Add event listeners for the new row
  addRowEventListeners(order_data.order_items.length);
}

// Function to add event listeners to a specific row
const addRowEventListeners = (index) => {
  const qtyInput = order_items_table.querySelector(`.quantity-input[data-index="${index}"]`);
  const priceInput = order_items_table.querySelector(`.price-input[data-index="${index}"]`);
  const totalInput = order_items_table.querySelector(`.total-input[data-index="${index}"]`);

  function updateTotal() {
    const qty = parseFloat(qtyInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    
    // Update order_data with the new values
    if (order_data.order_items[index - 1]) {
      order_data.order_items[index - 1].quantity = qty;
      order_data.order_items[index - 1].price = price;
    }
    
    totalInput.value = (qty * price).toFixed(2);
  }

  qtyInput.addEventListener('input', updateTotal);
  priceInput.addEventListener('input', updateTotal);

  // Initialize total
  updateTotal();
}

// Function to initialize event listeners for existing items (edit mode)
const initializeExistingItems = () => {
  const rows = order_items_table.querySelectorAll('tr');
  rows.forEach((row, index) => {
    if (index > 0) { // Skip header row
      addRowEventListeners(index);
    }
  });
}



// This is to handle product row deletions
order_items_table.addEventListener('click', function (e) {
  if (e.target.classList.contains('delete-row-btn')) {
    const tr = e.target.closest('tr');
    if (tr) tr.remove();
    // Optionally, remove from order_data.order_items as well:
    const skuInput = tr.querySelector('input[readonly]');
    if (skuInput) {
      order_data.order_items = order_data.order_items.filter(item => item.sku !== skuInput.value);
    }
    // Remove table header if no more order items
    // Find all rows except header
    const rows = order_items_table.querySelectorAll('tr');
    // If only the header remains, or no rows at all, remove the header
    if (order_data.order_items.length === 0) {
      const header = order_items_table.querySelector('tr');
      if (header) header.remove();
    }
  }
});


const collectOrderItemsFromTable = () => {
  const items = [];
  // Find all rows except the header
  // We'll count rows by checking for inputs with id="sku_X"
  let index = 1;
  while (true) {
    const skuInput = document.getElementById(`sku_${index}`);
    if (!skuInput) {
      // If no more rows, break
      // (or continue if you want to allow gaps in numbering)
      index++;
      // If you want to allow gaps, comment out the break and use continue
      if (index > 1000) break; // safety to avoid infinite loop
      continue;
    }
    const descriptionInput = document.getElementById(`description_${index}`);
    const quantityInput = document.getElementById(`quantity_${index}`);
    const priceInput = document.getElementById(`price_${index}`);
    const variantInput = document.getElementById(`variant_${index}`);
    const itemIdInput = document.getElementById(`item_id_${index}`);

    const sku = skuInput.value || "";
    const description = descriptionInput ? descriptionInput.value : "";
    const quantity = quantityInput ? parseFloat(quantityInput.value) || 0 : 0;
    const price = priceInput ? parseFloat(priceInput.value) || 0 : 0;
    const variant = variantInput ? (variantInput.value === "true" || variantInput.value === "1") : false;
    const itemId = itemIdInput ? parseInt(itemIdInput.value) : null;

    if (sku) {
      const item = {
        item_no: index,
        product: { sku: sku, variant: variant },
        description: description,
        quantity: quantity,
        price: price
      };
      
      // Include item_id for existing items (edit mode)
      if (itemId) {
        item.item_id = itemId;
      }
      
      items.push(item);
    }
    index++;
    if (index > 1000) break; // safety to avoid infinite loop
  }
  return items;
}

const submit_order_button = document.getElementById("submit_order_button");


// const generate_order_list_button = document.getElementById("generate_order_list_button");
// generate_order_list_button.addEventListener("click", (e) => {
//   // e.preventDefault();
//   // order_data.order_items = collectOrderItemsFromTable();
//   // console.log(order_data);
//   // Here you can send order_data to the server or process it further
//   collectOrderItemsFromTable();
// });

submit_order_button.addEventListener("click", (e) => {
  e.preventDefault();
  order_data.order_items = collectOrderItemsFromTable();
  const product_json = JSON.stringify(order_data.order_items);
  const product_json_input = document.getElementById("product_json_input");
  product_json_input.value = product_json;
  console.log("Final order data to submit:", order_data);

  // Submit the form programmatically
  submit_order_button.form.submit();
});

// Initialize event listeners for existing items when page loads (for edit mode)
document.addEventListener('DOMContentLoaded', function() {
  if (order_items_table && order_items_table.querySelectorAll('tr').length > 1) {
    initializeExistingItems();
  }
});