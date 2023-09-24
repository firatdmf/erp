// JavaScript/jQuery code
$(document).ready(function () {
  // Add a click event handler to the elements with class "search_id_result"
  $("#suggestions-dropdown").click(function (event) {
    event.stopPropagation();
    console.log( "I was clicked, but my parent will not be." );
    // Display an alert when clicked
    alert("You clicked on the element!");
  });
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
        console.log(data);
        // Clear existing suggestions
        suggestions.empty();

        // Display suggestions returned from the server
        data.suggestions.forEach(function (suggestion) {
          suggestions.append(
            '<div class="search_id_result" id="search_result_' +
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
  //   $(".search_id_result").on("click", function () {
  //     alert("hey");
  //     let t = $(this).attr("id");
  //     console.log(t);
  //     alert("hey!");
  //   });
});

// $(document).ready(function () {
//   // Your existing autocomplete code for contact_company_search

//   // When a contact or company is selected from the autocomplete suggestions
// //   $("#contact_company_search").on("autocompleteselect", function (event, ui) {
// //     // Set the selected contact or company's ID in the hidden input field
// //     $("#contact_company_id").val(ui.item.id);
// //   });

// });
