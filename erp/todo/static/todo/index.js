// JavaScript/jQuery code
// asd = (input)=>{
//   alert(input)
// }
$(document).ready(function () {
  // Add a click event handler to the elements with class "search_id_result"
  $(".search_id_result").click(function (event) {
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
            '<div class="search_id_result" onclick="()=>{console.log("I was clicked")}" id="search_result_' +
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

