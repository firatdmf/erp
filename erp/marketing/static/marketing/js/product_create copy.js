document.addEventListener('DOMContentLoaded', function () {

    var hasVariantsCheckbox = document.getElementById('id_has_variants');
    var variantForm = document.getElementById('variant_form');
    let attribute_input = document.getElementById('attribute_input');
    let drop_down_attribute_value = document.getElementById('drop_down_attribute_value');
    let attribute_list = document.getElementById('attribute_list');
    let attributes = [];

    function toggleVariantForm() {
        if (hasVariantsCheckbox.checked) {
            variantForm.style.display = 'block';
        } else {
            variantForm.style.display = 'none';
        }
    }

    hasVariantsCheckbox.addEventListener('change', toggleVariantForm);

    let add_attribute_button = (event) => {
        if (event.key === "Enter") {
            add_attribute_value();
        }
        // console.log('you hit me');
        // console.log(attribute_input.value);

        if (attribute_input.value !== "") {

            // console.log(drop_down_attribute_value.style.display);
            drop_down_attribute_value.style.display = "block"
            if (attributes.includes(attribute_input.value) === true) {
                drop_down_attribute_value.innerHTML = "This attribute already exists"
                drop_down_attribute_value.style.cursor = "not-allowed"
            } else {
                drop_down_attribute_value.innerHTML = '<i class="fa fa-solid fa-circle-plus"></i> ' + attribute_input.value;
            }


        }
        else {
            drop_down_attribute_value.style.display = "none"

        }

    }

    let add_attribute_value = () => {
        if (attributes.includes(attribute_input.value) === false) {
            attribute_list.innerHTML += `<li>Option name:${attribute_input.value} <br/> Option Values: <br/><input type="text"></li>`
            attributes.push(attribute_input.value);
        }
    };

    attribute_input.addEventListener('keyup', add_attribute_button);

    drop_down_attribute_value.addEventListener('click', add_attribute_value);

    // Initialize the form display based on the initial state of the checkbox
    toggleVariantForm();
});