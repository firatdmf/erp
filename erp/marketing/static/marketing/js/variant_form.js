console.log("welcome to the variant form my fellas");
// Let's combine the data and export it.
export_data = {
    "product_variant_options": {},
    // {"color": ["blue","black"]}
    "product_variant_list": [],
    // [
    //  {
    //     "variant_sku": "blue12",
    //     "variant_attribute_values": {
    //         "color": "blue"
    //     },
    //     "variant_price": 12,
    //     "variant_quantity": 12,
    //     "variant_barcode": 1212121212,
    //     "variant_featured": true
    // },
    // {
    //     "variant_sku": "black21",
    //     "variant_attribute_values": {
    //         "color": "black"
    //     },
    //     "variant_price": 21,
    //     "variant_quantity": 22,
    //     "variant_barcode": 2121212121,
    //     "variant_featured": true
    // }
    // ]
}

// ---------------------------------------------------------------------------------------------
// below two variables are passed from marketing_tags.py to variant_form.html and from there to here
const product_variant_options = JSON.parse(product_variant_options_data);
console.log("product_variant_options_data: ");

console.log(product_variant_options);

// product_variant_options = {"color": ["beige", "white"], "size": ["95", "84"]}
// ---------------------------------------------------------------------------------------------
const product_variant_list = JSON.parse(product_variant_list_data);
console.log("product_variant_list: ");

console.log(product_variant_list);
// ---------------------------------------------------------------------------------------------
const variant_files_json = JSON.parse(variant_files_json_data);
console.log("variant_files_json: ");
console.log(variant_files_json);





// product_variant_list = 
// [
//     {
//         "variant_sku": "RK24562RW8",
//         "variant_attribute_values": {
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
//         "variant_attribute_values": {
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
//         "variant_attribute_values": {
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
//         "variant_attribute_values": {
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

// optionsObj = { "color": ["beige", "white"], "size": ["95", "84"] }
let getCombinations = (optionsObj) => {

    const optionNames = Object.keys(optionsObj);
    if (optionNames.length === 0) return [];

    // Start with an array with one empty object
    let combinations = [{}];

    optionNames.forEach(optionName => {
        const values = optionsObj[optionName];
        // For each existing combination, add each value of this option
        combinations = combinations.flatMap(combination =>
            values.map(value => ({
                ...combination,
                [optionName]: value
            }))
        );
    });

    return combinations;
    // combinations = [
    //   { color: "beige", size: "95" },
    //   { color: "beige", size: "84" },
    //   { color: "white", size: "95" },
    //   { color: "white", size: "84" }
    // ]
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


// ----------------------------------------
// ----------------------------------------
const create_table_button = document.getElementById("create_table_button");
let createTable = () => {

    // Get all the input elements. (not the table inputs, just the option inputs (variant names and their values))
    const variant_container_input_elements = document.getElementById('variant_container').getElementsByTagName('input');

    // initialize variant array
    let new_product_variant_options = {};
    let variant_name = "";
    let variant_table_option_names = ""
    let variant_table_rows = ""
    // Below iterates through every input value and stores the value in the variant array
    // I do not know how this works, but it just works. Something is confusing me here with variant_name
    Object.values(variant_container_input_elements).map((element, index) => {
        // an element is either:
        // input#variant_name_1
        // or
        // input#variant_name_1_value_1

        // If there are empty input fields in variant_container, then stop createing table, and alert user.
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

        // If it is an option name (not a value)
        if (!element.id.includes("value")) {
            variant_name = element.value;
            variant_name_id = Number(element.id.split('_').at(-1));
            if (variant_name) {
                new_product_variant_options[variant_name] = [];
                variant_table_option_names += "<th>" + variant_name + "</th>";
            }
        } else {
            // If it is an option's value, add it to the correct variant_name
            // Find the corresponding option name's id
            let name_id = Number(element.id.split('_')[2]);
            // Find the corresponding option name by id
            let option_name_element = document.getElementById(`variant_name_${name_id}`);
            if (option_name_element && option_name_element.value) {
                let option_name = option_name_element.value;
                new_product_variant_options[option_name].push(element.value);
            }
        }
    });
    // console.log("your new_product_variant_options are");
    // console.log(new_product_variant_options);
    export_data.product_variant_options = new_product_variant_options;
    // variants = { "color": ["beige", "white"], "size": ["95", "84"] }

    // Get all combinations of the variant values
    const variant_combinations = getCombinations(new_product_variant_options)

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



    // variant_combinations is generated from the variant names and their valus in the variant container
    if (variant_combinations.length > 0) {

        let new_product_variant_list = []
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

            new_product_variant_list.push(
                {
                    "variant_sku": "",
                    "variant_attribute_values": element,
                    "variant_price": null,
                    "variant_quantity": null,
                    "variant_barcode": "",
                    "variant_featured": true
                }
            )
        })
        export_data.product_variant_list = new_product_variant_list
    }

    // Let's combine the data and export it.
    // export_data = {
    //     "variants": variants,
    //     "product_variant_list": product_variant_list,
    //     // "variant_names": variant_names
    // }

    console.log("your initial export data is");

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

let prepopulate_variant_table = () => {

    // If the product already has variants in the database then show them in the table
    // else skip to the next else if statement
    if (product_variant_list.length > 0) {
        // let new_product_variant_options = {};
        // let variant_name = "";
        let variant_table_option_names = ""
        let variant_table_rows = ""
        export_data.product_variant_list = product_variant_list
        // If we altered the existing variants (add or delete)
        // product_variants is passed in existing variants, and the variant_combinations is generated within the form

        // I don't think below does anything
        // if ((product_variant_list.length !== variant_combinations.length)) {
        //     product_variant_list = []
        //     variant_combinations.map((variant_combination, index) => {
        //         product_variant_list.push(
        //             {
        //                 "variant_sku": "",
        //                 "variant_attribute_values": variant_combination,
        //                 "variant_price": null,
        //                 "variant_quantity": null,
        //                 "variant_barcode": "",
        //                 "variant_featured": true
        //             }
        //         )
        //     })
        // }
        // 


        console.log("here it comes:");
        Object.keys(product_variant_options).forEach((key) => {
            variant_table_option_names += `<th>${key}</th>`
        })

        // Account for if the value is null
        // make this dynamically generated (for loop the possible product variant form inputs)

        // Comes from database
        product_variant_list.map((product_variant, index) => {

            // product_variant: {
            //     "variant_sku": "RK24562RW8",
            //     "variant_attribute_values": {
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
            const variantSKU = product_variant.variant_sku;
            const files = variant_files_json[variantSKU];
            variant_table_rows += '<tr>'
            Object.values(product_variant.variant_attribute_values).map((value) => {
                variant_table_rows += `<td>${value}</td>`
            })
            // Either we set the value to the existing value or we set it to an empty string
            // ------------------------------------------------------------------------
            variant_table_rows += "<td>"
            variant_table_rows += `<input type="file" name="variant_file_${index}" id="variant_file_${index}" multiple>`;
            const variant_file_input_element = document.getElementById(`variant_file_${index}`)
            console.log("your element variant_file_input_element is this:");
            console.log(variant_file_input_element);
            
            
            if (files && files.length > 0) {
                files.forEach((file) => {
                    const link = document.createElement("a");
                    link.href = file.url;
                    link.textContent = file.name;
                    link.target = "_blank";
                    // variant_file_input_element.after(link);
                })
            }
            variant_table_rows += "</td>"

            // ------------------------------------------------------------------------
            variant_table_rows += `<td><input type="number" name="variant_price_${index}" id="variant_price_${index}" value="${product_variant.variant_price || ''}"></td>`
            variant_table_rows += `<td><input type="number" name="variant_quantity_${index}" id="variant_quantity_${index}" value="${product_variant.variant_quantity || ''}" ></td>`
            variant_table_rows += `<td><input type="text" name="variant_sku_${index}" id="variant_sku_${index}" value="${product_variant.variant_sku || ''}" required></td>`
            variant_table_rows += `<td><input type="number" name="variant_barcode_${index}" id="variant_barcode_${index}" value="${product_variant.variant_barcode || ''}"></td>`

            // product_variant.varaint_featured returns true or false, not on or off.
            // so we need to alter it manually
            if (product_variant.variant_featured) {
                variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}" checked></td>`
            } else {

                variant_table_rows += `<td><input type="checkbox" name="variant_featured_${index}" id="variant_featured_${index}"></td>`
            }

            variant_table_rows += `</tr>`


        })

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
    }
}
// ----------------------------------------------
// ----------------------------------------------
// If the variant already exists, run below to prepoulate its table with existing variant data
// This function only runs if the product already has variants in the database
let prepopulate_variant_containers = () => {

    // product_variants variable comes from the variant_form.html component, and from marketing_tags.py to that.
    if (product_variant_list.length <= 0) {
        console.log("you have no variants")
    } else {
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
    prepopulate_variant_table();

}

// This is input field from django marketing.models product form
let hasVariantsCheckbox = document.getElementById('id_has_variants');
let variant_component = document.getElementById('variant_component');
let product_files_form = document.getElementById('product_files_form');

if (hasVariantsCheckbox.checked) {
    variant_component.style.display = 'block';
    product_files_form.style.display = 'none';
    prepopulate_variant_containers();
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

let loading = document.getElementById('loading');


hasVariantsCheckbox.addEventListener('change', toggleVariantForm);

let manual_post_data = {}
const form = document.getElementById('product_form');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    loading.style.display = 'block';
    console.log("Form submission prevented. Handling manually...");

    const variant_table_input_elements = document.getElementById('variant_table').getElementsByTagName('input');
    // const variant_data = { product_variant_list: [] };
    // let variant_data = export_data;

    Array.from(variant_table_input_elements).forEach((element, index) => {
        // splits the elements id string by underscores resulting in an array. Than we select the last element of that array which starts with 1. But index in js starts with 0 so we substract one from each. 
        const variant_row = Number(element.id.split('_').at(-1)) - 1;
        const element_name = element.name.replace(/^([^_]+)_([^_]+)_.*$/, '$1_$2');


        // for safetey, check if the element is not already in the export_data
        // I am not sure if this is needed, but I am doing it just in case
        if (!export_data.product_variant_list[variant_row]) {
            export_data.product_variant_list[variant_row] = {};
            // Add the combination for this row
            if (typeof variant_combinations !== "undefined" && variant_combinations[variant_row]) {
                export_data.product_variants[variant_row]["variant_attribute_values"] = variant_combinations[variant_row];
            }
        }

        if (element.name.includes("featured")) {
            export_data.product_variant_list[variant_row][element_name] = element.checked;
        } else if (!element_name.includes("variant_file")) {
            if (["variant_barcode", "variant_quantity", "variant_price"].some((key) => element_name.includes(key))) {
                export_data.product_variant_list[variant_row][element_name] = Number(element.value);
            } else {
                export_data.product_variant_list[variant_row][element_name] = element.value;
            }
        }
    });

    // console.log("Export data prepared:");
    // console.log(export_data);

    const formData = new FormData(form);
    formData.append('export_data', JSON.stringify(export_data));

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            console.log("Form submitted successfully. Reloading page to show results.");
            console.log("your response is: ");

            console.log(response);

            window.location.reload(); // Reload the page
        } else {
            console.error("Form submission failed:", response.statusText);
            const errorText = await response.text();
            console.error("Error Body:", errorText);
            // Optionally, you could try to parse the errorText if your server sends back error details in a specific format.
        }
    } catch (error) {
        console.error("Error submitting form:", error);
        loading.style.display = 'none';
        alert("An error occurred while submitting the form. Please try again.");

    }

    console.log("your export data is");
    console.log(export_data);


    // export_data = 
    // 
    // {
    //     "product_variant_options": {
    //         "color": [
    //             "blue",
    //             "black"
    //         ],
    //         "size": [
    //             "84",
    //             "95"
    //         ]
    //     },
    //     "product_variant_list": [
    //         {
    //             "variant_sku": "1",
    //             "variant_attribute_values": {
    //                 "color": "blue",
    //                 "size": "84"
    //             },
    //             "variant_price": 1,
    //             "variant_quantity": 1,
    //             "variant_barcode": 11111,
    //             "variant_featured": true
    //         },
    //         {
    //             "variant_sku": "2",
    //             "variant_attribute_values": {
    //                 "color": "blue",
    //                 "size": "95"
    //             },
    //             "variant_price": 2,
    //             "variant_quantity": 2,
    //             "variant_barcode": 22222,
    //             "variant_featured": false
    //         },
    //         {
    //             "variant_sku": "3",
    //             "variant_attribute_values": {
    //                 "color": "black",
    //                 "size": "84"
    //             },
    //             "variant_price": 3,
    //             "variant_quantity": 3,
    //             "variant_barcode": 33333,
    //             "variant_featured": false
    //         },
    //         {
    //             "variant_sku": "4",
    //             "variant_attribute_values": {
    //                 "color": "black",
    //                 "size": "95"
    //             },
    //             "variant_price": 4,
    //             "variant_quantity": 4,
    //             "variant_barcode": 44444,
    //             "variant_featured": true
    //         }
    //     ]
    // }

});

// auto generate variant_sku based on the parent sku and the variant_attribute_values
// TSHIRT001-BLK-95
// Enfore sku to be unique
// make the sure option values are unique within the same option name