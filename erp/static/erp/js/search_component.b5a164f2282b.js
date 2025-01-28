document.addEventListener("DOMContentLoaded", () => {
    const addButton = document.getElementById("addButton");
    const addExpanded = document.getElementById("addExpanded");
    const recent = document.querySelector(".recent");
  
    const addExpandedShow = () => {
      addExpanded.style.display = "block";
    };
  
    const addExpandedHide = (event) => {
      if (
        !addButton.contains(event.target) &&
        !addExpanded.contains(event.target)
      ) {
        addExpanded.style.display = "none";
      }
    };
  
    addButton.addEventListener("mouseover", addExpandedShow);
    document.addEventListener("mouseover", addExpandedHide);
  
    // Below is for search button
    const searchButton = document.getElementById("searchButton");
  
    const searchOverlay = document.getElementById("searchOverlay");
    const searchInput = document.getElementById("searchInput");
    const searchResults = document.getElementById("searchResults");
  
    searchButton.addEventListener("click", () => {
      searchOverlay.style.display = "flex";
      searchInput.focus();
    });
  
    searchOverlay.addEventListener("click", (event) => {
      if (event.target === searchOverlay) {
        searchOverlay.style.display = "none";
        searchResults.innerHTML = "";
  
        searchInput.value = "";
      }
    });
  
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim();
      if (query != "") {
        recent.style.display = "none";
      } else {
        recent.style.display = "flex";
      }
      if (query.length > 0) {
        performSearch(query);
      } else {
        searchResults.innerHTML = "";
      }
    });
  });
  