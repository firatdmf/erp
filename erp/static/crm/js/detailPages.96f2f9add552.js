// console.log("Hello");

openAddContactForm = ()=>{

  document.querySelector(".addContactForm").style.display = "flex";
  document.querySelector(".addContact").style.display = "none";

}

selectedContact = () =>{
  print('hello')
}


























// $(document).ready(function () {
//     $(".delete-note-form").submit(function (event) {
//       event.preventDefault();
//       var form = $(this);
//       var noteId = form.find('input[name="note_id"]').val();
//       $.ajax({
//         type: "POST",
//         url: form.attr("action"),
//         data: {
//           note_id: noteId,
//           csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
//         },
//         dataType: "json",
//         success: function (data) {
//           // Handle success response
//           console.log(data.message);
//           // Optionally, you can remove the deleted note from the list
//           form.closest("li").remove();
//         },
//         error: function (xhr, status, error) {
//           // Handle error response
//           console.error(xhr.responseText);
//         },
//       });
//     });
//   });