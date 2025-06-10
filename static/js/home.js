const toggleBtns = document.querySelectorAll('.home-toggle-btn');
const intensityInput = document.getElementById('intensityInput');
toggleBtns.forEach(btn => {
    btn.addEventListener('click', function() {
        toggleBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        intensityInput.value = this.getAttribute('data-value');
    });
});