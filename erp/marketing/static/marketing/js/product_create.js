document.addEventListener('DOMContentLoaded', function () {

    var hasVariantsCheckbox = document.getElementById('id_has_variants');
    var variantForm = document.getElementById('variant_form');
    let attribute_option_input = document.getElementById('attribute_option_input');
    let drop_down_attribute_value = document.getElementById('drop_down_attribute_value');
    let attribute_value_input = document.getElementById('attribute_value_input');
    let attribute_list = document.getElementById('attribute_list');
    let attributes = [];

    let attribute_json_array = [];

    let attribute_value_input_creator = ()=>{
        let attribute_value_input = document.createElement('input');
        attribute_value_input.setAttribute('type', 'text');
        attribute_value_input.setAttribute('placeholder', 'Enter attribute value');
        attribute_value_input.setAttribute('name', 'attribute_value');
        return attribute_value_input;
    }


    let add_attribute_button = (event) => {
        if (event.key === "Enter") {
            add_attribute_value();
        }
        // console.log('you hit me');
        // console.log(attribute_option_input.value);

        if (attribute_option_input.value !== "") {

            // console.log(drop_down_attribute_value.style.display);
            drop_down_attribute_value.style.display = "block"
            if (attributes.includes(attribute_option_input.value) === true) {
                drop_down_attribute_value.innerHTML = "This attribute already exists"
                drop_down_attribute_value.style.cursor = "not-allowed"
            } else {
                drop_down_attribute_value.innerHTML = '<i class="fa fa-solid fa-circle-plus"></i> ' + attribute_option_input.value;
            }


        }
        else {
            drop_down_attribute_value.style.display = "none"

        }

    }

    let add_attribute_value = () => {
        if (attributes.includes(attribute_option_input.value) === false) {
            attribute_list.innerHTML += `<li>Option name:${attribute_option_input.value} <br/> Option Values: <br/><input type="text"></li>`
            attributes.push(attribute_option_input.value);
        }
    };



    attribute_option_input.addEventListener('keyup', add_attribute_button);

    drop_down_attribute_value.addEventListener('click', add_attribute_value);

});