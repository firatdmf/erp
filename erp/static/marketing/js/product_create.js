function toggleVariantForm() {
    var hasVariants = document.getElementById('id_has_variants').checked;
    var variantForm = document.getElementById('variant-form');
    if (hasVariants) {
        variantForm.style.display = 'block';
    } else {
        variantForm.style.display = 'none';
    }
}


document.getElementById('id_has_variants').addEventListener('change', toggleVariantForm);