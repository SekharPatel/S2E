// /S2E/app/static/js/home.js

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('project-search');
    const projectGrid = document.getElementById('project-grid');

    // Homepage Search Functionality
    if (searchInput && projectGrid) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = projectGrid.querySelectorAll('.project-row');
            rows.forEach(row => {
                const name = row.dataset.projectName || '';
                if (name.includes(searchTerm)) {
                    // Use an empty string to revert to the stylesheet's display property (grid)
                    row.style.display = ''; 
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
