document.addEventListener('DOMContentLoaded', function() {
    // User dropdown functionality
    var dropdown = document.getElementById('userDropdown');
    var closeTimer = null;
    if (dropdown) {
        dropdown.addEventListener('mouseenter', function() {
            if (closeTimer) {
                clearTimeout(closeTimer);
                closeTimer = null;
            }
            dropdown.classList.add('open');
        });
        dropdown.addEventListener('mouseleave', function() {
            closeTimer = setTimeout(function() {
                dropdown.classList.remove('open');
            }, 200); // 200ms delay before closing
        });
    }
    
    // Navbar scroll behavior
    const navbar = document.querySelector('nav');
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > lastScrollY) {
            // Scrolling down
            navbar.classList.add('nav-hidden');
        } else {
            // Scrolling up
            navbar.classList.remove('nav-hidden');
        }
        lastScrollY = window.scrollY;
    });
});