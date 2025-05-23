// Theme switching functionality
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const lightModeIcon = document.querySelector('.theme-icon.light-mode');
    const darkModeIcon = document.querySelector('.theme-icon.dark-mode');
    
    if (theme === 'dark') {
        lightModeIcon.style.display = 'none';
        darkModeIcon.style.display = 'inline';
    } else {
        lightModeIcon.style.display = 'inline';
        darkModeIcon.style.display = 'none';
    }
    
    // Force re-render of background colors
    document.body.style.backgroundColor = '';
    setTimeout(() => {
        document.body.style.backgroundColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--bg-color').trim();
    }, 50);
}

document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    
    themeToggle.addEventListener('click', function(e) {
        e.preventDefault();
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    });
    
    // Listen for storage events to sync theme across tabs
    window.addEventListener('storage', function(e) {
        if (e.key === 'theme') {
            applyTheme(e.newValue);
        }
    });
});
