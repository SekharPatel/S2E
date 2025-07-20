// /S2E/app/static/js/base.js

// Create a global namespace for our app's functions
window.s2e = window.s2e || {};

document.addEventListener('DOMContentLoaded', function() {
    
    function escapeHTML(str) {
        if (typeof str !== 'string') return '';
        return str.replace(/[&<>"']/g, function(match) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[match];
        });
    }

    // --- REFACTORED: This function now RENDERS data, it doesn't fetch it ---
    function renderSidebarProjects(data) {
        const container = document.getElementById('project-list-container');
        if (!container) return;

        container.innerHTML = ''; // Clear content
        if (data.all_projects && data.all_projects.length > 0) {
            data.all_projects.forEach(project => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.className = 'project-link';
                if (data.active_project_id === project.id) {
                    a.classList.add('active');
                }
                a.dataset.projectId = project.id;
                a.innerHTML = `<i class="fas fa-folder fa-fw"></i> <span>${escapeHTML(project.name)}</span>`;
                li.appendChild(a);
                container.appendChild(li);
            });
        } else {
            container.innerHTML = `<li><a href="#"><i class="fas fa-info-circle fa-fw"></i> <span>No projects yet.</span></a></li>`;
        }
        attachProjectLinkListeners();
    }
    // Expose the function to the global s2e namespace so home.js can call it
    window.s2e.renderSidebarProjects = renderSidebarProjects;

    function attachProjectLinkListeners() {
        document.querySelectorAll('.project-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const projectId = this.dataset.projectId;
                fetch('/api/projects/set_active', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_id: projectId })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        window.location.reload();
                    } else {
                        alert('Error: ' + result.message);
                    }
                });
            });
        });
    }

    // --- Initial Load Logic ---
    function initialLoad() {
        if (!document.getElementById('sidebar')) return;

        fetch('/api/projects_data')
            .then(response => response.json())
            .then(data => {
                renderSidebarProjects(data);
            })
            .catch(error => {
                console.error('Error fetching initial sidebar data:', error);
                const container = document.getElementById('project-list-container');
                if(container) container.innerHTML = `<li><a href="#" style="color: var(--danger);"><i class="fas fa-exclamation-triangle fa-fw"></i> <span>Error loading.</span></a></li>`;
            });
    }

    const slideOverPanel = document.getElementById('slide-over-panel');
    const newProjectBtnSidebar = document.getElementById('new-project-sidebar-btn');
    const newProjectFabMain = document.getElementById('new-project-fab-main');
    const closeSlideOverBtn = document.getElementById('close-slide-over');
    const cancelNewProjectBtn = document.getElementById('cancel-new-project');
    const newProjectForm = document.getElementById('new-project-form');
    const playbookSelect = document.getElementById('project-playbooks');
    let isSubmitting = false;

    function openSlideOver() {
        if (slideOverPanel) {
            if (typeof ALL_PLAYBOOKS !== 'undefined' && playbookSelect) {
                playbookSelect.innerHTML = '';
                ALL_PLAYBOOKS.forEach(playbook => {
                    const option = document.createElement('option');
                    option.value = playbook.id;
                    option.textContent = playbook.name;
                    playbookSelect.appendChild(option);
                });
            }
            slideOverPanel.classList.add('open');
        }
    }

    function closeSlideOver() {
        if (slideOverPanel) slideOverPanel.classList.remove('open');
    }

    if (newProjectBtnSidebar) newProjectBtnSidebar.addEventListener('click', openSlideOver);
    if (newProjectFabMain) newProjectFabMain.addEventListener('click', openSlideOver);
    if (closeSlideOverBtn) closeSlideOverBtn.addEventListener('click', closeSlideOver);
    if (cancelNewProjectBtn) cancelNewProjectBtn.addEventListener('click', closeSlideOver);

    if (newProjectForm) {
        newProjectForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (isSubmitting) return;
            isSubmitting = true;
            
            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Creating...`;

            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            const playbookIds = Array.from(playbookSelect.selectedOptions).map(opt => opt.value);
            data.playbook_ids = playbookIds;

            fetch('/api/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + result.message);
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                    isSubmitting = false;
                }
            })
            .catch(error => {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
                isSubmitting = false;
            });
        });
    }

    initialLoad();
});
