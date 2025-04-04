// @Author: Muhammed Firat Ozturk
// Handle in python
// There should not be identical values in the variant values
// there should not be identical variant names
// Variant name deletion should only be present at the last variant name. // This is done
// Variant value deletion should only be present at the last variant value. // This is done
// Variant value addition should only be present at the last variant value. // This is done

// Checks if an object is empty
let isEmptyObject = (obj) => {
    return Object.keys(obj).length === 0 && obj.constructor === Object;
}


// This is to calculate the possible combinations of the variants
// It returns an array: where each element is a combination
// [
//     "color:white-size:84",
//     "color:white-size:95",
//     "color:beige-size:84",
//     "color:beige-size:95"
// ]
let getCombinations = (options) => {
    if (!options || options.length === 0) {
        return;
    }

    const combinations = [];

    function generateCombinations(index, currentCombination) {
        if (index === options.length) {
            combinations.push(currentCombination.join("-"));
            return;
        }

        const currentOption = options[index];
        for (const value of currentOption.values) {
            // console.log('hey,hey ,hey' + options[index].name, value);
            currentCombination.push(options[index].name + ":" + value);
            generateCombinations(index + 1, [...currentCombination]); // Create a copy of the array
            currentCombination.pop(); // Backtrack
        }
    }

    generateCombinations(0, []);

    // combinations.forEach(combination => {
    //     console.log(combination);
    // });
    return combinations;
}

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

//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------




// ----------------------------------------
// ----------------------------------------
// ----------------------------------------

let createTable = () => {
    // Get all the input elements. (not the table inputs)
    let input_elements = document.getElementById('variant_container').getElementsByTagName('input');


    // initialize variant array
    let variant = []
    let variant_name;
    let variant_names = [];
    let variant_name_id;
    let variant_table_option_names = ""
    let variant_table_rows = ""
    // Below iterates through every input value and stores the value in the variant array
    // I do not know how this works, but it just works. Something is confusing me here with variant_name
    Object.values(input_elements).map((element, index) => {
        // an element is either.
        // input#variant_name_1
        // input#variant_name_1_value_1

        // If the user has not entered an option name, skip it. 
        if (variant_name === "") {
            // go to the next element
            return;
        } else {


            // If we it is an option name, and not an option's value
            if (!element.id.includes("value")) {
                variant_name = element.value
                if (variant_name) {
                    variant_name_id = Number(element.id.split('_').at(-1))
                    variant.push({ "name": variant_name, "values": [] })
                    variant_names.push(variant_name)
                    variant_table_option_names += "<th>" + variant_name + "</th>"
                } else {
                    // variant.variant_name.values.push(element.value)
                    // variant[variant_name_id - 1].values.push(element.value)
                    console.log("variant_name is empty");

                    // console.log(variant[variant_name_id - 1].values.push(element.value))
                    // console.log(variant);

                }
            } else {
                console.log(variant[variant_name_id - 1].values.push(element.value))
            }

        }


    });

    // console.log("your variant array is");
    // console.log(variant);

    // Get all combinations of the variant values
    const combinations = getCombinations(variant)

    // Generate table based on the combinations
    if (combinations) {

        console.log("your variant combinations are:");
        console.log(combinations);
        console.log("your product_variants are");
        console.log(product_variants);

        // Account for if the value is null
        // make this dynamically generated (for loop the possible product variant form inputs)
        if (product_variants) {
            product_variants.map((product_variant, index) => {
                index++
                variant_table_rows += '<tr>'
                Object.values(product_variant.variant_combination).map((value) => {
                    variant_table_rows += `<td>${value}</td>`
                })
                variant_table_rows += `<td><input type="file" name="variant_file_${index}" id="variant_file_${index}" multiple></td>`
                variant_table_rows += `<td><input type="number" name="variant_price_${index}" id="variant_price_${index}" value="${product_variant.variant_price}"></td>`
                variant_table_rows += `<td><input type="number" name="variant_quantity_${index}" id="variant_quantity_${index}" value="${product_variant.variant_quantity}" ></td>`
                variant_table_rows += `<td><input type="text" name="variant_sku_${index}" id="variant_sku_${index}" value="${product_variant.variant_sku}"></td>`
                variant_table_rows += `<td><input type="number" name="variant_barcode_${index}" id="variant_barcode_${index}" value="${product_variant.variant_barcode}"></td>`

                // product_variant.varaint_featured returns true or false, not on or off.
                if (product_variant.variant_featured) {
                    variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}" checked></td>`
                } else {

                    variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}"></td>`
                }

                variant_table_rows += `</tr>`
            })
        } else {

            combinations.map((element, index) => {
                index++
                // Split the element and create a row for the table
                // The element is like color:white-size:84-header:grommet
                let element_values = element.split("-")
                variant_table_rows += `<tr>`
                element_values.map((value) => { variant_table_rows += `<td>${value.split(":")[1]}</td>` })
                // Define name for below and state that the inputs are from the table.
                // Each input will refer to its combination index.
                variant_table_rows += `<td><input type="file" name="variant_file_${index}" id="variant_file_${index}" multiple></td>`
                variant_table_rows += `<td><input type="number" name="variant_price_${index}" id="variant_price_${index}"></td>`
                variant_table_rows += `<td><input type="number" name="variant_quantity_${index}" id="variant_quantity_${index}"></td>`
                variant_table_rows += `<td><input type="text" name="variant_sku_${index}" id="variant_sku_${index}"></td>`
                variant_table_rows += `<td><input type="number" name="variant_barcode_${index}" id="variant_barcode_${index}"></td>`
                variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}" checked></td>`
                variant_table_rows += `</tr>`
            })
        }

    }

    // Let's combine the data and export it.
    const export_data = {
        "variants": variant,
        "combinations": combinations,
        "variant_names": variant_names
    }


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
  `
    //   This shall go on the bottom of table
    //   <button onClick=submit_table(${export_data})>Submit Table</button>
    // I am not gonna put it there and handle the inputs in django because I am not sure how to handle the file inputs in js object


    variant_json_input_element = document.getElementById("variant_json");
    variant_json_input_element.value = JSON.stringify(export_data)
    return;

}


// ----------------------------------------------
// ----------------------------------------------
// ----------------------------------------------

let variant_form_constructor = () => {

    if (isEmptyObject(product_variants)) {
        console.log("you have no variants")
    } else {
        product_variants = JSON.parse(product_variants); // Parse the JSON string into an object
        product_variant_options = JSON.parse(product_variant_options);

        console.log("product variants are:");
        console.log(product_variants);



        // console.log(product_variant_options) // Output: { color: ["white", "beige"], size: ["84", "95"] }
        // product_variant_options = { color: ["white", "beige", "black", "orange"], size: ["84", "95", "1128"], "header": ["rod pocket", "grommet", "japon"], "length": ["long", "short", "medium","wide","xlarge","xxxlarge"] }
        console.log("product variant options are");

        console.log(product_variant_options);

        let counter = 1
        for (const [attribute_name, attribute_values] of Object.entries(product_variant_options)) {
            // console.log(key, values);
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
                // console.log(add_another_option_element);

                // variant_name_element = add_another_name(add_another_option_element).firstChild;
                // variant_name_element = add_another_name(add_another_option_element).firstElementChild;
                add_another_name(add_another_option_element)
                variant_name_element = document.getElementById(`variant_name_${counter}`);

                variant_name_element.value = attribute_name;
                for (i = 1; i <= attribute_values.length; i++) {
                    // console.log(i)
                    // let variant_name_value_element = document.getElementById(`variant_name_${counter}_value_${i}`);
                    // variant_name_value_element.value = attribute_values[i - 1];
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
    document.getElementById("create_table_button").style.display = "none";
    createTable();

}



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





