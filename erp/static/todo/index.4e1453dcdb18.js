// JavaScript/jQuery code
$(document).ready(function () {


  // $("#cancel_selected").hide();
  $('label[for="id_contact"]').hide();
  $('label[for="id_company"]').hide();
  $("#id_contact").hide();
  $("#id_company").hide();
  let nameInput = $("#contact-company-search");
  let suggestions = $("#suggestions-dropdown");

  nameInput.on("input", function () {
    const inputValue = nameInput.val();
    // console.log(inputValue);

    // Send an AJAX request to your Django backend
    $.ajax({
      url: "/todo/search/", // Replace with your Django URL
      method: "GET",
      data: {
        search_query: inputValue,
      },
      success: function (data) {
        console.log(data.suggestions[0]);
        // Clear existing suggestions
        suggestions.empty();

        // Display suggestions returned from the server
        data.suggestions.forEach(function (suggestion) {
          suggestions.append(
            '<div class="search_id_result" ' +
              "data-suggestion='" +
              JSON.stringify(suggestion) +
              "' " +
              'onclick="selected_contact_identifier(this)" ' +
              'id="search_result_' +
              suggestion.id +
              '">' +
              suggestion.name +
              "</div>"
          );
        });
        if (!inputValue) {
          suggestions.empty();
        }
      },
    });
  });
});

// let selected_contact_identifier = (element) => {
//     // Retrieve the JSON data from the data-suggestion attribute
//     var suggestionData = element.getAttribute('data-suggestion');

//     // Parse the JSON data
//     var suggestion = JSON.parse(suggestionData);

//     // Now you can access suggestion.id, suggestion.name, and suggestion.type
//     console.log(suggestion.id);
//     console.log(suggestion.name);
//     console.log(suggestion.type);

//     let company_selectElement = $('#id_company');
//     let contact_selectElement = $('#id_contact');

//     if (suggestion.type === 'company'){
//       company_selectElement.find('option').each(function() {
//         if ($(this).val() == suggestion.id) {
//             // Set the matched option as selected
//             $(this).prop('selected', true);
//         }
//     }}
//     else (suggestion.type === 'contact'){
//       contact_selectElement.find('option').each(function() {
//         if ($(this).val() == suggestion.id) {
//             // Set the matched option as selected
//             $(this).prop('selected', true);
//         }
//       }
//     }

// };

let selected_contact_identifier = (element) => {
  $(".search-container").hide();
  $("#cancel_selected").show();
  let selected_result = $(".selected_result");

  // Retrieve the JSON data from the data-suggestion attribute
  var suggestionData = element.getAttribute("data-suggestion");

  // Parse the JSON data
  var suggestion = JSON.parse(suggestionData);

  // Now you can access suggestion.id, suggestion.name, and suggestion.type
  console.log(suggestion.id);
  console.log(suggestion.name);
  console.log(suggestion.type);

  let company_selectElement = $("#id_company");
  let contact_selectElement = $("#id_contact");
  if (suggestion.type === "company") {
    company_selectElement.find("option").each(function () {
      if ($(this).val() == suggestion.id) {
        // Set the matched option as selected
        $(this).prop("selected", true);
        contact_selectElement.val("");
        // $('#contact-company-search').hide();
      }
    });
  } else if (suggestion.type === "contact") {
    contact_selectElement.find("option").each(function () {
      if ($(this).val() == suggestion.id) {
        // Set the matched option as selected
        $(this).prop("selected", true);
        company_selectElement.val("");
        // document.getElementsByClassName('search-container').style.display = 'none';
      }
    });
  }

  selected_result.prepend(suggestion.name);

  $("#cancel_selected").click(() => {
    $(".search-container").show();
    $("#cancel_selected").hide();
    $(".selected_result").hide();
    $(".search_id_result").hide();
    $("#contact-company-search").val("");
    // console.log($("#contact-company-search").val());
    // console.log(company_selectElement.val());
    // console.log(contact_selectElement.val());
  });

  // let firat = ()=>{
  //   $(".card-content").hide();
  // }
};
