document.addEventListener('DOMContentLoaded', function() {
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
});