let sidebar = document.querySelector(".sidebar");
let closeBtn = document.querySelector("#btn");

// Ensure elements exist before adding listeners to prevent errors on pages without a sidebar
if (sidebar && closeBtn) {
    closeBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        menuBtnChange(); //calling the function(optional)
    });
}

// following are the code to change sidebar button(optional)
function menuBtnChange() {
    if (sidebar.classList.contains("open")) {
        closeBtn.classList.replace("bx-menu", "bx-menu-alt-right"); //replacing the iocns class
    } else {
        closeBtn.classList.replace("bx-menu-alt-right", "bx-menu"); //replacing the iocns class
    }
}