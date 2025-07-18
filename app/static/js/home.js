document.addEventListener('DOMContentLoaded', function () {
    const newProjectFab = document.querySelector('.new-project-fab');
    const slideOverPanel = document.querySelector('.slide-over-panel');
    const closeSlideOver = document.querySelector('.close-slide-over');

    if (newProjectFab && slideOverPanel && closeSlideOver) {
        newProjectFab.addEventListener('click', () => {
            slideOverPanel.classList.add('open');
        });

        closeSlideOver.addEventListener('click', () => {
            slideOverPanel.classList.remove('open');
        });
    }

    const sidebar = document.querySelector('.sidebar');
    // Add logic to collapse/expand sidebar, e.g., on a button click
    // const toggleSidebarBtn = document.querySelector('#toggle-sidebar-btn');
    // if (sidebar && toggleSidebarBtn) {
    //     toggleSidebarBtn.addEventListener('click', () => {
    //         sidebar.classList.toggle('collapsed');
    //     });
    // }
});
