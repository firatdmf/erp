// There should not be identical values in the variant values
// there should not be identical variant names
// Variant name deletion should only be present at the last variant name.



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

    combinations.forEach(combination => {
        console.log(combination);
    });
    return combinations;
}


// let variant_name_1 = document.getElementById("variant_name_1");
// let variant_name_1_value_1 = document.getElementById("variant_name_1_value_1");
// let variant_name_1_value_2 = document.getElementById("variant_name_1_value_2");

let add_another_name = (el) => {
    let empty_option_name = false;
    console.log(el.innerHTML);
    //   This is the previous option's name_id
    let previous_option_name_id = Number(el.id.slice("_").at(-1))-1;
    console.log(`previous option name id is: ${previous_option_name_id}`);
    let previous_option_name_element = document.getElementById(`variant_name_${previous_option_name_id}`);
    // variant_array.push({"name":previous_option_name_element.value})
    // variant_array.push({"variant_name_id":1,"variant_name":"","variant_values":""})
    error_message_option_name_element = document.getElementById("error_message_option_name");
    if (previous_option_name_element.value === "") {
        empty_option_name = true;
        error_message_option_name_element.innerHTML = (`Enter option name ${previous_option_name_id} first`);
        return;
    } else {
        empty_option_name = false;
        error_message_option_name_element.innerHTML = ""
    }

    let current_option_name_id = previous_option_name_id + 1;
    // if(current_option_name_id)

    previous_delete_option_name_element = document.getElementById(`delete_option_name_${previous_option_name_id}`);
    if (previous_delete_option_name_element) {
        previous_delete_option_name_element.remove()
    }

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
    let next_option_name_id = current_option_name_id + 1;
    el.setAttribute('id', `add_another_name_${next_option_name_id}`)
    el.before(add_option_name)
}
//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

let delete_option_name = (el) => {
    let option_name_id = Number(el.id.slice("_").at(-1))
    let option_name_element = document.getElementById(`variantCard_${option_name_id}`)
    option_name_element.remove()
    let add_another_name_element = document.getElementById(`add_another_name_${(Number(el.id.slice("_").at(-1))+1)}`);
    add_another_name_element.id = `add_another_name_${Number(el.id.slice("_").at(-1))}`

    // let previous_option_name_element_id = option_name_id - 1;
    // if(previous_option_name_element_id > 1){
    //     console.log('yes it is,we should add')
    //     let previous_option_name_element = document.getElementById(`variantCard_${previous_option_name_element_id}`);
    //     let option_name_title_element = previous_option_name_element.getElementsByClassName("option_name")[0];
    //     // let delete_option_name_element = document.createElement("div")
    //     // delete_option_name_element.setAttribute('class', 'delete_option_name');
    //     // delete_option_name_element.setAttribute('id', `delete_option_name_${previous_option_name_element_id}`);
    //     // delete_option_name_element.setAttribute('onClick', `delete_option_name(this)`);
    //     option_name_title_element.children[0].after(delete_option_name_element)
    // }
    
}

let delete_option_value = (el, next_option_name_id, next_option_value_id) => {
    let deleted_option_value_id = Number(el.id.slice("_").at(-1))
    console.log("deleted option value id is:");
    console.log(deleted_option_value_id);
    let previous_option_value_emenet_id = deleted_option_value_id - 1
    let previous_option_value_element = document.getElementById(`variant_name_${next_option_name_id}_value_${previous_option_value_emenet_id}`)
    if (previous_option_value_emenet_id > 2) {
        let delete_option_value = document.createElement("div")
        delete_option_value.setAttribute('class', 'delete_option_value');
        delete_option_value.setAttribute('id', `delete_option_value_${previous_option_value_emenet_id}`);
        delete_option_value.setAttribute('onClick', `delete_option_value(this,${next_option_name_id},${previous_option_value_emenet_id})`);
        delete_option_value.innerHTML = '<svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>'
        previous_option_value_element.after(delete_option_value)
    }
    let add_another_value_element = document.getElementById(`variant_name_${next_option_name_id}_add_another_value_${deleted_option_value_id + 1}`);
    add_another_value_element.id = `variant_name_${next_option_name_id}_add_another_value_${deleted_option_value_id}`
    console.log("you are about to delete:");
    console.log(add_another_value_element);
    let option_value_id = Number(el.id.slice("_").at(-1))
    let option_value_element = document.getElementById(`variant_name_${next_option_name_id}_value_${option_value_id}`)
    option_value_element.remove()
    el.remove()
}


//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

let add_another_value = (el, next_option_name_id) => {

    //   Next option name id is just the current name id that is passed
    if (!next_option_name_id) {
        next_option_name_id = 1
    }
    //   ----------------------------------------------
    let previous_option_value_id = Number(el.id.slice('_').at(-1)) - 1
    console.log(`Prev option value id is: ${previous_option_value_id}`)
    console.log(`next option name id is: ${next_option_name_id}`)
    let first_option_name = document.getElementById(`variant_name_${next_option_name_id}`);
    let first_option_value = document.getElementById(`variant_name_${next_option_name_id}_value_1`)
    let previous_option_value = document.getElementById(`variant_name_${next_option_name_id}_value_${previous_option_value_id}`)
    // variant_array[next_option_name_id-1].variant_name = first_option_name.value
    // variant_array[next_option_name_id-1].variant_values = [first_option_value.value,previous_option_value.value];
    // console.log(previous_option_value);
    let empty_option_value = false;
    let empty_option_name = false;
    for (let i = 1; i <= previous_option_value_id; i++) {
        let option_value = document.getElementById(`variant_name_${next_option_name_id}_value_${i}`);
        if (option_value.value === "") {
            empty_option_value = true
        }
        if (first_option_name.value === "") {
            empty_option_name = true;
        }
    }
    error_element = document.getElementById(`error_message_option_value_${next_option_name_id}`);
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
    //   ----------------------------------------------
    let next_option_value_id = Number(el.id.slice("_").at(-1))

    let add_option_value = document.createElement("input")
    add_option_value.setAttribute('type', 'text');
    add_option_value.setAttribute('placeholder', `Add Option Value ${next_option_value_id}`);
    add_option_value.setAttribute('name', `variant_name_${next_option_name_id}_value_${next_option_value_id}`);
    add_option_value.setAttribute('id', `variant_name_${next_option_name_id}_value_${next_option_value_id}`);
    let delete_option_value = document.createElement("div")
    delete_option_value.setAttribute('class', 'delete_option_value');
    delete_option_value.setAttribute('id', `delete_option_name_${next_option_name_id}_value_${next_option_value_id}`);
    delete_option_value.setAttribute('onClick', `delete_option_value(this,${next_option_name_id},${next_option_value_id})`);
    delete_option_value.innerHTML = '<svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.--><path d="M135.2 17.7C140.6 6.8 151.7 0 163.8 0L284.2 0c12.1 0 23.2 6.8 28.6 17.7L320 32l96 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L32 96C14.3 96 0 81.7 0 64S14.3 32 32 32l96 0 7.2-14.3zM32 128l384 0 0 320c0 35.3-28.7 64-64 64L96 512c-35.3 0-64-28.7-64-64l0-320zm96 64c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16zm96 0c-8.8 0-16 7.2-16 16l0 224c0 8.8 7.2 16 16 16s16-7.2 16-16l0-224c0-8.8-7.2-16-16-16z"/></svg>'

    console.log(`la la la The previous option value id is: ${previous_option_value_id}`)
    let previous_option_delete_element = document.getElementById(`delete_option_name_${next_option_name_id}_value_${previous_option_value_id}`)
    if (previous_option_delete_element) {
        previous_option_delete_element.remove()
    }

    el.before(add_option_value)
    add_option_value.after(delete_option_value)
    console.log(`The next option value id will be: ${next_option_value_id}`)
    el.setAttribute('id', `variant_name_${next_option_name_id}_add_another_value_${next_option_value_id + 1}`)
}
//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

// let export_data ={}

// let table_submit = () => {

//     // Get all the elements in the table container
//     let input_elements = document.getElementById('variant_table').getElementsByTagName('input');
//     console.log(input_elements);
//     console.log(input_elements.length);
//     console.log('the table has been submitted.');
//     console.log(export_data)
//     Object.values(input_elements).map((element, index) => {
//         let element_id = element.id;
//         let element_type = element_id.split("_").at(0); // file, price, quantity, sku, barcode, featured
//         let element_variant = element_id.split("_").at(1); // 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
//         if(export_data["combinations"][element_variant]){
//             export_data["combinations"][element_variant] += "-" +element_type+ ":"+ element.value;
//         }
//     })
//     console.log("your final export data is:");

//     console.log(export_data)
// }

//   ----------------------------------------------
//   ----------------------------------------------
//   ----------------------------------------------

let hello = () => {
    console.log("hello");
    // variant_array = [];
    // console.log(variant_array)
    // Get all the input elements in the variant_container
    let input_elements = document.getElementById('variant_container').getElementsByTagName('input');
    // console.log(input_elements);
    // console.log(input_elements["1"].value)
    variant = []
    let variant_name;
    let variant_name_id;
    let variant_table_option_names = ""
    let number_of_table_rows = 1;
    let variant_table_rows = ""
    // Below iterates through every input value and stores the value in the variant array
    // I do not know how this works, but it just works. Something is confusing me here with variant_name
    Object.values(input_elements).map((element, index) => {
        if (variant_name === "") {
            // go to the next element
            return;
        } else {
            if (!element.id.includes("value")) {
                variant_name = element.value
                if (variant_name) {
                    variant_name_id = Number(element.id.split('_').at(-1))
                    variant.push({ "name": variant_name, "values": [] })
                    variant_table_option_names += "<th>" + variant_name + "</th>"
                }

            } else {
                // variant.variant_name.values.push(element.value)
                console.log(variant[variant_name_id - 1].values.push(element.value))
            }

        }


    });
    console.log(variant)
    // This is the number of options we have, and will be equal to the number of nested for loops
    console.log(variant.length)
    let n = 0;
    let variant_combinations = 1;
    variant.map((element) => {
        console.log(element.values.length)
        variant_combinations *= element.values.length
    })
    number_of_table_rows += variant_combinations
    console.log("the variants are listed below")
    console.log(variant);
    console.log("the combinations are listed below")
    const combinations = getCombinations(variant)
    console.log(combinations)



    // Calculate # of combinations of arrays
    // get number of option values and multiply with each other.
    const number_of_option_names = variant.length
    // for (let i = 0; i < combinations.length; i++) {
    if (combinations) {
        combinations.map((element, index) => {
            let element_values = element.split("-")
            // console.log('---------')
            // console.log(element_values)
            // console.log('---------')
            variant_table_rows += `<tr>`
            element_values.map((value) => { variant_table_rows += `<td>${value.split(":")[1]}</td>` })
            // Define name for below and state that the inputs are from the table.
            variant_table_rows += `<td><input type="file" id="file_${index}" multiple></td>`
            variant_table_rows += `<td><input type="number" id="price_${index}"></td>`
            variant_table_rows += `<td><input type="number" id="quantity_${index}"></td>`
            variant_table_rows += `<td><input type="text" id="sku_${index}"></td>`
            variant_table_rows += `<td><input type="number" id="barcode_${index}"></td>`
            variant_table_rows += `<td><input type="checkbox" id="featured_${index}" checked></td>`
            variant_table_rows += `</tr>`
            // // ["84","95"]
            // console.log('your elements are')
            // console.log(element)
            // console.log('your elements are')
            // // console.log(`the element values are ${element_values}`)
            // // while (0 < element_values.length){
            // //     variant_table_rows += `<td>${element_values.pop()}</td>`
            // // }
            // variant_table_rows += `</tr>`
        })

    }

    // }

    const export_data = {
        "variants": variant,
        "combinations": combinations
    }


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


    console.log('the export data is:')
    console.log(export_data)
    // input_elements.objects.map((element)=>{
    //   console.log(element.id)
    // })
}

