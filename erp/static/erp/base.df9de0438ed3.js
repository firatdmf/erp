const addButton = document.getElementById("#addButton");
const addExpanded = document.getElementById("#addExpanded");

const addExpandedShow = ()=>{
    console.log('looked at it');
    addExpanded.style.display = "block";
}

const addExpandedHide = (event) =>{
    if (!addButton.contains(event.target) && !addExpanded.contains(event.target)) {
        addExpanded.style.display = "none";
    }
}

const setupHoverListeners = () => {
    addButton.addEventListener("mouseover", addExpandedShow);
    document.addEventListener("mouseover", addExpandedHide);
};

window.onload = setupHoverListeners;
console.log('hello');