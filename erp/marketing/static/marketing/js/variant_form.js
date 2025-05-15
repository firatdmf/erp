console.log("welcome to the variant form my fellas");


// ---------------------------------------------------------------------------------------------
// below two variables are passed from marketing_tags.py to variant_form.html and from there to here
let product_variant_options = JSON.parse(product_variant_options_data);
console.log(product_variant_options);

// product_variant_options = {"color": ["beige", "white"], "size": ["95", "84"]}
// ---------------------------------------------------------------------------------------------
// ---------------------------------------------------------------------------------------------
let product_variants = JSON.parse(product_variants_data);
// let product_variants_new = []
// product_variants = 
// [
//     {
//         "variant_sku": "RK24562RW8",
//         "variant_combination": {
//             "color": "white",
//             "size": "84"
//         },
//         "variant_price": null,
//         "variant_quantity": 102,
//         "variant_barcode": "712179795204",
//         "variant_featured": false
//     },
//     {
//         "variant_sku": "RK24562GW9",
//         "variant_combination": {
//             "color": "white",
//             "size": "95"
//         },
//         "variant_price": null,
//         "variant_quantity": 48,
//         "variant_barcode": "712179795228",
//         "variant_featured": true
//     },
//     {
//         "variant_sku": "RK24562RC8",
//         "variant_combination": {
//             "color": "beige",
//             "size": "84"
//         },
//         "variant_price": null,
//         "variant_quantity": 98,
//         "variant_barcode": "712179795211",
//         "variant_featured": true
//     },
//     {
//         "variant_sku": "RK24562GC9",
//         "variant_combination": {
//             "color": "beige",
//             "size": "95"
//         },
//         "variant_price": null,
//         "variant_quantity": 46,
//         "variant_barcode": "712179795235",
//         "variant_featured": true
//     }
// ]
// ---------------------------------------------------------------------------------------------

// returns false if the object is empty
let isEmptyObject = (obj) => {
    return Object.keys(obj).length === 0 && obj.constructor === Object;
}


let variants_exist = false

if (product_variants.length <= 0) {
    console.log("you have no variants");
} else {
    variants_exist = true

}

// ---------------------------------------------------------------------------------------------
const getCombinations = (variant_sets) => {
    // variant_sets:
    // [
    //     {
    //         "name": "color",
    //         "values": [
    //             "white",
    //             "beige"
    //         ]
    //     },
    //     {
    //         "name": "size",
    //         "values": [
    //             "84",
    //             "95"
    //         ]
    //     }
    // ]

    if (!variant_sets || variant_sets.length === 0) {
        console.error("variant_sets is empty");

        return;
    }

    const combinations = [];

    const generateCombinations = (index, variant_combination) => {
        // variant_combination:

        if (index === variant_sets.length) {
            // Push a copy of the current combination to avoid reference issues
            combinations.push({ ...variant_combination });
            return;
        }

        const currentOption = variant_sets[index];
        for (const value of currentOption.values) {
            // value = "white" or "84"
            // Create a new combination for each recursive call
            const newCombination = { ...variant_combination };
            newCombination[currentOption.name] = value;
            generateCombinations(index + 1, newCombination); // Create a copy of the array
            // variant_combination.pop(); // Backtrack
        }
    }

    generateCombinations(0, {});

    return combinations;
    // combinations = [
    //     {
    //         "color": "white",
    //         "size": "84"
    //     },
    //     {
    //         "color": "white",
    //         "size": "95"
    //     },
    //     {
    //         "color": "beige",
    //         "size": "84"
    //     },
    //     {
    //         "color": "beige",
    //         "size": "95"
    //     }
}
// ---------------------------------------------------------------------------------------------


//   ----------------------------------------------
// This is to add another option name: e.g. color, size, etc
let add_another_name = (el) => {
    let previous_option_name_id = Number(el.id.slice("_").at(-1)) - 1;
    let previous_option_name_element = document.getElementById(`variant_name_${previous_option_name_id}`);

    let error_message_option_name_element = document.getElementById("error_message_option_name");
    if (previous_option_name_element.value === "") {
        error_message_option_name_element.innerHTML = (`Enter option name for option name ${previous_option_name_id}`);
        return;
    } else {
        error_message_option_name_element.innerHTML = ""
    }

    let current_option_name_id = previous_option_name_id + 1;

    // Delete the previous delete option name element
    let previous_delete_option_name_element = document.getElementById(`delete_option_name_${previous_option_name_id}`);
    if (previous_delete_option_name_element) {
        previous_delete_option_name_element.remove()
    }

    // create a new option name element
    let add_option_name = document.createElement("div");
    add_option_name.setAttribute('class', 'variantCard');
    add_option_name.setAttribute('id', `variantCard_${current_option_name_id}`);
    add_option_name.innerHTML = `<div class="option_name">
    <div class="delete_option_name" id="delete_option_name_${current_option_name_id}" onClick=delete_option_name(this)>
    <svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>
    </div>
    <div>Option Name</div>
    <input type="text" placeholder="Add Option Name" name="variant_name_${current_option_name_id}" id="variant_name_${current_option_name_id}">
      </div>
    <div class="optionValues">
      <div>Option Values</div>
       <input type="text" placeholder="Add Option Value 1" name="variant_name_${current_option_name_id}_value_1" id= "variant_name_${current_option_name_id}_value_1">
      <input type="text" placeholder="Add Option Value 2" name="variant_name_${current_option_name_id}_value_2" id= "variant_name_${current_option_name_id}_value_2">
      <div id="variant_name_${current_option_name_id}_add_another_value_3" class="add_another_value" onClick=add_another_value(this,${current_option_name_id})>+ Add Another Option Value</div>
      <div id="error_message_option_value_${current_option_name_id}" class="alert"></div>
    </div>
  </div>`

    // adjust the id of the add_another_name element.
    let next_option_name_id = current_option_name_id + 1;
    el.setAttribute('id', `add_another_name_${next_option_name_id}`)

    // insert the new option name element before add_another_name element.
    el.before(add_option_name)



    document.getElementById("create_table_button").style.display = "block";
    return add_option_name
}
//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

let delete_option_name = (el) => {
    let option_name_id = Number(el.id.slice("_").at(-1))
    let option_name_element = document.getElementById(`variantCard_${option_name_id}`)
    let previous_option_name_id = option_name_id - 1;
    let previous_option_name_element = document.getElementById(`variantCard_${previous_option_name_id}`)
    let previous_option_name_title_element = previous_option_name_element.getElementsByClassName("option_name")[0].children[0]

    let add_another_name_element = document.getElementById(`add_another_name_${(Number(el.id.slice("_").at(-1)) + 1)}`);
    add_another_name_element.id = `add_another_name_${Number(el.id.slice("_").at(-1))}`
    if (previous_option_name_id > 1) {
        let delete_option_name_element = document.createElement("div")
        delete_option_name_element.setAttribute('class', 'delete_option_name');
        delete_option_name_element.setAttribute('id', `delete_option_name_${previous_option_name_id}`);
        delete_option_name_element.setAttribute('onClick', `delete_option_name(this)`);
        delete_option_name_element.innerHTML = `<svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>`

        previous_option_name_title_element.appendChild(delete_option_name_element)
    }

    option_name_element.remove()


    document.getElementById("create_table_button").style.display = "block";

}

let delete_option_value = (el, next_option_name_id, next_option_value_id) => {
    let deleted_option_value_id = Number(el.id.slice("_").at(-1))
    let previous_option_value_emenet_id = deleted_option_value_id - 1
    let previous_option_value_element = document.getElementById(`variant_name_${next_option_name_id}_value_${previous_option_value_emenet_id}`)

    // If we have more than 2 option values, then we can add a delete option value element
    if (previous_option_value_emenet_id > 2) {
        let delete_option_value = document.createElement("div")
        delete_option_value.setAttribute('class', 'delete_option_value');
        delete_option_value.setAttribute('id', `delete_option_value_${previous_option_value_emenet_id}`);
        delete_option_value.setAttribute('onClick', `delete_option_value(this,${next_option_name_id},${previous_option_value_emenet_id})`);
        delete_option_value.innerHTML = '<svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>'
        previous_option_value_element.after(delete_option_value)
    }

    // Now we need to adjust the id of the add_another_value element
    let add_another_value_element = document.getElementById(`variant_name_${next_option_name_id}_add_another_value_${deleted_option_value_id + 1}`);
    add_another_value_element.id = `variant_name_${next_option_name_id}_add_another_value_${deleted_option_value_id}`

    // Finally delete the option value element
    let option_value_id = Number(el.id.slice("_").at(-1))
    let option_value_element = document.getElementById(`variant_name_${next_option_name_id}_value_${option_value_id}`)
    option_value_element.remove()

    // Just in case we have a delete option value element, we need to remove it
    el.remove()




    document.getElementById("create_table_button").style.display = "block";
}


//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

let add_another_value = (el, next_option_name_id) => {

    //   Next option name id is just the current name id that is passed (the id of the variant container)
    // If no next option name id is passed, then we will just set it to 1, indicating the first option name
    if (!next_option_name_id) {
        next_option_name_id = 1
    }


    //   ----------------------------------------------
    let previous_option_value_id = Number(el.id.slice('_').at(-1)) - 1;
    // Get the element of first option name
    let first_option_name = document.getElementById(`variant_name_${next_option_name_id}`);

    // Initilize the error elements
    let empty_option_value = false;
    let empty_option_name = false;

    // Check if any of the previous option values are empty
    for (let i = 1; i <= previous_option_value_id; i++) {
        let option_value = document.getElementById(`variant_name_${next_option_name_id}_value_${i}`);
        if (option_value.value === "") {
            empty_option_value = true
        }
        if (first_option_name.value === "") {
            empty_option_name = true;
        }
    }

    // Get the error element
    error_element = document.getElementById(`error_message_option_value_${next_option_name_id}`);
    // Display errors if any
    if (empty_option_value) {
        error_element.style.display = "block";
        error_element.innerHTML = "Enter Option Value";
        return;
    } else if (empty_option_name) {
        error_element.style.display = "block";
        error_element.innerHTML = "Enter Option Name";
        return;
    } else {
        error_element.style.display = "none";
    }



    let next_option_value_id = Number(el.id.slice("_").at(-1))

    // Create the new option value element
    let add_option_value = document.createElement("input")
    add_option_value.setAttribute('type', 'text');
    add_option_value.setAttribute('placeholder', `Add Option Value ${next_option_value_id}`);
    add_option_value.setAttribute('name', `variant_name_${next_option_name_id}_value_${next_option_value_id}`);
    add_option_value.setAttribute('id', `variant_name_${next_option_name_id}_value_${next_option_value_id}`);
    // Create the new delete option value element
    let delete_option_value = document.createElement("div")
    delete_option_value.setAttribute('class', 'delete_option_value');
    delete_option_value.setAttribute('id', `delete_option_name_${next_option_name_id}_value_${next_option_value_id}`);
    delete_option_value.setAttribute('onClick', `delete_option_value(this,${next_option_name_id},${next_option_value_id})`);
    delete_option_value.innerHTML = '<svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>'

    // Delete the previous delete option value element if exists
    let previous_option_delete_element = document.getElementById(`delete_option_name_${next_option_name_id}_value_${previous_option_value_id}`)
    if (previous_option_delete_element) {
        previous_option_delete_element.remove()
    }

    // Add the new option value input element
    el.before(add_option_value)
    // Add the delete option value element
    add_option_value.after(delete_option_value)
    // Adjust the id of the add_another_value element
    el.setAttribute('id', `variant_name_${next_option_name_id}_add_another_value_${next_option_value_id + 1}`)

    document.getElementById("create_table_button").style.display = "block";
}







// ----------------------------------------
// ----------------------------------------
// ----------------------------------------
const create_table_button = document.getElementById("create_table_button");
let createTable = () => {


    // Get all the input elements. (not the table inputs, just the option inputs (variant names and their values))
    const variant_container_input_elements = document.getElementById('variant_container').getElementsByTagName('input');



    // initialize variant array
    let variants = []
    let variant_name;
    let variant_names = [];
    let variant_name_id;
    let variant_table_option_names = ""
    let variant_table_rows = ""
    // Below iterates through every input value and stores the value in the variant array
    // I do not know how this works, but it just works. Something is confusing me here with variant_name
    Object.values(variant_container_input_elements).map((element, index) => {
        // an element is either:
        // input#variant_name_1
        // or
        // input#variant_name_1_value_1

        // If there are empty input fields in variant_container, then prevent createing table.
        if (element.value.trim() === "") {
            let error_message_element = document.createElement("p")
            console.error("you have empty input fields");
            error_message_element.innerHTML = "Please fill all the input fields"
            error_message_element.setAttribute('class', 'alert')
            create_table_button.after(error_message_element)
            // remove error message after 5 seconds
            setTimeout(function () {
                error_message_element.innerHTML = ""
            }, 5000)
            return;
        }

        // If the user has not entered an option name, skip it. 
        if (variant_name === "") {
            // go to the next element
            return;
        } else {
            // If it is an option name, and not an option's value
            if (!element.id.includes("value")) {
                variant_name = element.value
                if (variant_name) {
                    variant_name_id = Number(element.id.split('_').at(-1))
                    variants.push({ "name": variant_name, "values": [] })
                    variant_names.push(variant_name)
                    variant_table_option_names += "<th>" + variant_name + "</th>"
                } else {
                    console.log("variant_name is empty");
                }
            } else {
                // If it is an option's value, and not an option name
                variants[variant_name_id - 1].values.push(element.value)
            }

        }

    });
    console.log("your variants are");
    console.log(variants);



    // variants =  [
    // {
    //     "name": "color",
    //     "values": [
    //         "white",
    //         "beige"
    //     ]
    // },
    // {
    //     "name": "size",
    //     "values": [
    //         "84",
    //         "95"
    //     ]
    // }

    // Get all combinations of the variant values
    // const combinations = getCombinations(variants)
    const variant_combinations = getCombinations(variants)
    // variant_combinations = [
    //     {
    //         "color": "white",
    //         "size": "84"
    //     },
    //     {
    //         "color": "white",
    //         "size": "95"
    //     },
    //     {
    //         "color": "beige",
    //         "size": "84"
    //     },
    //     {
    //         "color": "beige",
    //         "size": "95"
    //     }
    // ]


    // Generate table based on the combinations
    // if (product_variants) {
    //     console.log('you have product variants');
    //     console.log("your product_variants are");
    //     // product_variants = JSON.parse(product_variants);
    //     // if(product_variants.length > 0){
    //     //     console.log('shit you do have product variants');

    //     // }
    //     // this is the product_variants variable that is passed from the backend
    //     console.log(product_variants);
    //     let product_variants_new = product_variants
    //     console.log(typeof (product_variants));

    // }

    // product_variants = [
    //     {
    //         "variant_sku": "RK24562RW8",
    //         "variant_combination": {
    //             "color": "white",
    //             "size": "84"
    //         },
    //         "variant_price": null,
    //         "variant_": 102,
    //         "variant_barcode": "712179795204",
    //         "variant_featured": false
    //     },
    //     {
    //         "variant_sku": "RK24562GW9",
    //         "variant_combination": {
    //             "color": "white",
    //             "size": "95"
    //         },
    //         "variant_price": null,
    //         "variant_": 48,
    //         "variant_barcode": "712179795228",
    //         "variant_featured": true
    //     },
    //     {
    //         "variant_sku": "RK24562RC8",
    //         "variant_combination": {
    //             "color": "beige",
    //             "size": "84"
    //         },
    //         "variant_price": null,
    //         "variant_": 98,
    //         "variant_barcode": "712179795211",
    //         "variant_featured": true
    //     },
    //     {
    //         "variant_sku": "RK24562GC9",
    //         "variant_combination": {
    //             "color": "beige",
    //             "size": "95"
    //         },
    //         "variant_price": null,
    //         "variant_": 46,
    //         "variant_barcode": "712179795235",
    //         "variant_featured": true
    //     }
    // ]

    // If the product already has variants saved then show them in the table
    if ((variants_exist && product_variants.length > 0) && (variant_combinations.length > 0)) {
        // If we altered the existing variants (add or delete)
        // product_variants is passed in existing variants, and the variant_combinations is generated within the form
        if ((product_variants.length !== variant_combinations.length)) {
            product_variants = []
            variant_combinations.map((variant_combination, index) => {
                product_variants.push(
                    {
                        "variant_sku": "",
                        "variant_combination": variant_combination,
                        "variant_price": null,
                        "variant_quantity": null,
                        "variant_barcode": "",
                        "variant_featured": true
                    }
                )
            })
        }

        // Account for if the value is null
        // make this dynamically generated (for loop the possible product variant form inputs)

        // Comes from database
        product_variants.map((product_variant, index) => {
            // product_variant: {
            //     "variant_sku": "RK24562RW8",
            //     "variant_combination": {
            //         "color": "white",
            //         "size": "84"
            //     },
            //     "variant_price": null,
            //     "variant_": 102,
            //     "variant_barcode": "712179795204",
            //     "variant_featured": false
            // }
            // }

            // I do this because input id's start from one, not zero.
            index++

            variant_table_rows += '<tr>'
            Object.values(product_variant.variant_combination).map((value) => {
                variant_table_rows += `<td>${value}</td>`
            })


            // // Object.values(product_variant.variant_combination).map((value) => {
            // Object.values(variant_combinations).map((value) => {
            //     console.log(value);

            //     // variant_table_rows += `<td>${value}</td>`
            // })




            // if(!isEqualObject(product_variant.variant_combination, combinations2[index])){
            //     console.log("yes this exists");
            // }

            // Either we set the value to the existing value or we set it to an empty string
            variant_table_rows += `<td><input type="file" name="variant_file_${index}" id="variant_file_${index}" multiple></td>`
            variant_table_rows += `<td><input type="number" name="variant_price_${index}" id="variant_price_${index}" value="${product_variant.variant_price || ''}"></td>`
            variant_table_rows += `<td><input type="number" name="variant_quantity_${index}" id="variant_quantity_${index}" value="${product_variant.variant_quantity || ''}" ></td>`
            variant_table_rows += `<td><input type="text" name="variant_sku_${index}" id="variant_sku_${index}" value="${product_variant.variant_sku || ''}" required></td>`
            variant_table_rows += `<td><input type="number" name="variant_barcode_${index}" id="variant_barcode_${index}" value="${product_variant.variant_barcode || ''}"></td>`

            // product_variant.varaint_featured returns true or false, not on or off.
            if (product_variant.variant_featured) {
                variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}" checked></td>`
            } else {

                variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}"></td>`
            }

            variant_table_rows += `</tr>`


        })
    }
    // variant_combinations is generated from the variant names and their valus in the variant container
    else if (variant_combinations.length > 0) {

        variant_combinations.map((element, index) => {
            index++
            // Split the element and create a row for the table
            // The element is like [{"color":"white","size":"84"},{"color":"beige","size":"95"}]
            let element_values = Object.values(element)
            variant_table_rows += `<tr>`
            element_values.map((value) => { variant_table_rows += `<td>${value}</td>` })
            // Define name for below and state that the inputs are from the table.
            // Each input will refer to its combination index.
            variant_table_rows += `<td><input type="file" name="variant_file_${index}" id="variant_file_${index}" multiple></td>`
            variant_table_rows += `<td><input type="number" name="variant_price_${index}" id="variant_price_${index}"></td>`
            variant_table_rows += `<td><input type="number" name="variant_quantity_${index}" id="variant_quantity_${index}"></td>`
            variant_table_rows += `<td><input type="text" name="variant_sku_${index}" id="variant_sku_${index}" required></td>`
            variant_table_rows += `<td><input type="number" name="variant_barcode_${index}" id="variant_barcode_${index}"></td>`
            variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}" checked></td>`
            variant_table_rows += `</tr>`
        })
    }

    // Let's combine the data and export it.
    export_data = {
        "variants": variants,
        "product_variants": product_variants,
        // "variant_names": variant_names
    }

    console.log("your export data is:");
    console.log(export_data);
    
    


    // Get the table element and insert the values in it.
    variant_table_element = document.getElementById("variant_table")
    variant_table_element.style.display = "inline-block";
    variant_table_element.innerHTML = `
   <tr>
    ${variant_table_option_names}
    <th>
      Photo
    </th>
    <th>
      Price
    </th>
    <th>
      Quantity
    </th>
    <th>
      SKU
    </th>
    <th>
      BARCODE
    </th>
     <th>
      FEATURED
    </th>
  </tr>
  ${variant_table_rows}
  `;
    //   This shall go on the bottom of table
    //   <button onClick=submit_table(${export_data})>Submit Table</button>
    // I am not gonna put it there and handle the inputs in django because I am not sure how to handle the file inputs in js object


    // This is how I got rid of variant json
    // let variant_json_input_element = document.getElementById("variant_json");
    // variant_json_input_element.value = JSON.stringify(export_data)
    // console.log("your export data is");
    // console.log(export_data);


    return;

}



// ----------------------------------------------
// ----------------------------------------------
// ----------------------------------------------
// If the variant already exists, run below to prepoulate its table with existing variant data

let variant_form_constructor = () => {

    // product_variants variable comes from the variant_form.html component, and from marketing_tags.py to that.
    if (product_variants.length <= 0) {
        console.log("you have no variants")
    } else {
        // product_variants = JSON.parse(product_variants); // Parse the JSON string into an object
        // product_variant_options = JSON.parse(product_variant_options);

        let counter = 1
        for (const [attribute_name, attribute_values] of Object.entries(product_variant_options)) {
            let variant_name_element = document.getElementById(`variant_name_${counter}`);
            // Check if the element exists
            if (variant_name_element) {
                variant_name_element.value = attribute_name;
                for (i = 1; i <= attribute_values.length; i++) {
                    let variant_name_value_element = document.getElementById(`variant_name_${counter}_value_${i}`);
                    if (variant_name_value_element) {

                        variant_name_value_element.value = attribute_values[i - 1];
                    }
                    else {
                        let add_another_value_element = document.getElementById(`variant_name_${counter}_add_another_value_${i}`);


                        add_another_value(add_another_value_element, counter)
                        let new_variant_name_value = document.getElementById(`variant_name_${counter}_value_${i}`);
                        new_variant_name_value.value = attribute_values[i - 1];

                    }
                    // else{
                    //     add_another_value(document.getElementById(`variant_name_${counter+2}_add_another_value_${i}`), counter)
                    //     // in here adjust the add_another_value to input the variant div and automatically add to it
                    // }
                }
            } else {


                add_another_option_element = document.getElementById(`add_another_name_${counter}`)

                // variant_name_element = add_another_name(add_another_option_element).firstChild;
                // variant_name_element = add_another_name(add_another_option_element).firstElementChild;
                add_another_name(add_another_option_element)
                variant_name_element = document.getElementById(`variant_name_${counter}`);

                variant_name_element.value = attribute_name;
                for (i = 1; i <= attribute_values.length; i++) {
                    let variant_name_value_element = document.getElementById(`variant_name_${counter}_value_${i}`);
                    if (variant_name_value_element) {

                        variant_name_value_element.value = attribute_values[i - 1];
                    }
                    else {
                        let add_another_value_element = document.getElementById(`variant_name_${counter}_add_another_value_${i}`);


                        add_another_value(add_another_value_element, counter)
                        let new_variant_name_value = document.getElementById(`variant_name_${counter}_value_${i}`);
                        new_variant_name_value.value = attribute_values[i - 1];

                    }
                }

                // console.error(`Element with id variant_name_${counter} not found.`);
            }

            counter++;
        }
    }
    // document.getElementById("create_table_button").style.display = "none";
    createTable();

}




// 
// 
// 

// This is input field from django marketing.models product form
let hasVariantsCheckbox = document.getElementById('id_has_variants');
let variant_component = document.getElementById('variant_component');
let product_files_form = document.getElementById('product_files_form');

if (hasVariantsCheckbox.checked) {
    variant_component.style.display = 'block';
    product_files_form.style.display = 'none';
    variant_form_constructor();
}
let toggleVariantForm = () => {
    if (hasVariantsCheckbox.checked) {
        variant_component.style.display = 'block';
        product_files_form.style.display = 'none';
    } else {
        variant_component.style.display = 'none';
        product_files_form.style.display = 'block';
    }
}


hasVariantsCheckbox.addEventListener('change', toggleVariantForm);

let manual_post_data = {}
const form = document.getElementById('product_form');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    console.log("Form submission prevented. Handling manually...");

    const variant_table_input_elements = document.getElementById('variant_table').getElementsByTagName('input');
    const export_data = { product_variants: [] };

    Array.from(variant_table_input_elements).forEach((element) => {
        const variant_row = Number(element.id.split('_').at(-1)) - 1;
        const element_name = element.name.replace(/^([^_]+)_([^_]+)_.*$/, '$1_$2');

        if (!export_data.product_variants[variant_row]) {
            export_data.product_variants[variant_row] = {};
        }

        if (element.name.includes("featured")) {
            export_data.product_variants[variant_row][element_name] = element.checked;
        } else if (!element_name.includes("variant_file")) {
            if (["variant_barcode", "variant_quantity", "variant_price"].some((key) => element_name.includes(key))) {
                export_data.product_variants[variant_row][element_name] = Number(element.value);
            } else {
                export_data.product_variants[variant_row][element_name] = element.value;
            }
        }
    });

    console.log("Export data prepared:");
    console.log(export_data);

    const formData = new FormData(form);
    formData.append('export_data', JSON.stringify(export_data));

    // try {
    //     const response = await fetch(form.action, {
    //         method: 'POST',
    //         body: formData,
    //     });

    //     if (response.ok) {
    //         console.log("Form submitted successfully. Reloading page to show results.");
    //         console.log("your response is: ");
            
    //         console.log(response);
            
    //         // window.location.reload(); // Reload the page
    //     } else {
    //         console.error("Form submission failed:", response.statusText);
    //         const errorText = await response.text();
    //         console.error("Error Body:", errorText);
    //         // Optionally, you could try to parse the errorText if your server sends back error details in a specific format.
    //     }
    // } catch (error) {
    //     console.error("Error submitting form:", error);
    // }

    console.log("your export data is: ");
    console.log(export_data);
    
    
});