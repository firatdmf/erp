document.addEventListener("DOMContentLoaded", () => {
  const table = document.getElementById("production_table");
  const rowCount = document.querySelectorAll("#production_table tbody tr").length;

  function updatePackCount(i) {
    const orderQtyEl = document.getElementById(`order_quantity_${i}`);
    const packQtyInput = document.getElementById(`target_quantity_per_pack_${i}`);
    const packCountEl = document.getElementById(`pack_count_${i}`);
    const packCountInput = document.getElementById(`hidden_pack_count_${i}`)
    const target_quantity_per_pack = document.getElementById(`hidden_target_quantity_per_pack_${i}`)

    if (orderQtyEl && packQtyInput && packCountEl) {
      const orderQty = parseFloat(orderQtyEl.textContent.trim());
      const packQty = parseFloat(packQtyInput.value);

      if (!isNaN(orderQty) && !isNaN(packQty) && packQty > 0) {
        const packCount = Math.ceil(orderQty / packQty);
        packCountEl.textContent = packCount;
        packCountInput.value = packCount;
        target_quantity_per_pack.value = packQty;
      } else {
        packCountEl.textContent = 0;
      }
    }
  }

  for (let i = 0; i < rowCount; i++) {
    const packQtyInput = document.getElementById(`target_quantity_per_pack_${i}`);
    if (packQtyInput) {
      packQtyInput.addEventListener("input", () => updatePackCount(i));
      updatePackCount(i); // initial calculation
    }
  }

  const form = document.querySelector("form");
  form.addEventListener("submit", (e) => {
    let isValid = true;

    for (let i = 0; i < rowCount; i++) {
      const orderQtyEl = document.getElementById(`order_quantity_${i}`);
      const packQtyInput = document.getElementById(`id_form-${i}-target_quantity_per_pack`);

      if (orderQtyEl && packQtyInput) {
        const orderQty = parseFloat(orderQtyEl.textContent.trim());
        const packQty = parseFloat(packQtyInput.value);

        if (!isNaN(orderQty) && !isNaN(packQty) && packQty > orderQty) {
          alert(`Row ${i + 1}: Target quantity per pack cannot exceed order quantity (${orderQty}).`);
          packQtyInput.focus();
          isValid = false;
          break;
        }
      }
    }

    if (!isValid) {
      e.preventDefault();
    }
  });
});