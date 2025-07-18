// /S2E/app/static/js/base.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Helper to prevent XSS ---
    function escapeHTML(str) {
        if (typeof str !== 'string') return '';
        return str.replace(/[&<>"']/g, function(match) {
            return {
                '&': '&amp;', '<': '&lt;', '>': '&gt;',
                '"': '&quot;', "'": '&#39;'
            }[match];
        });
    }

    // --- Sidebar Project Loading ---
    function loadSidebarProjects() {
        const container = document.getElementById('project-list-container');
        if (!container) return;

        fetch('/api/sidebar_data')
            .then(response => response.json())
            .then(data => {
                container.innerHTML = ''; // Clear loading state
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
            })
            .catch(error => {
                console.error('Error fetching sidebar data:', error);
                container.innerHTML = `<li><a href="#" style="color: var(--danger);"><i class="fas fa-exclamation-triangle fa-fw"></i> <span>Error loading.</span></a></li>`;
            });
    }

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

    // --- New Project Slide-Over Panel Logic (Single Source of Truth) ---
    const slideOverPanel = document.getElementById('slide-over-panel');
    const newProjectBtnSidebar = document.getElementById('new-project-sidebar-btn');
    const newProjectFabMain = document.getElementById('new-project-fab-main');
    const closeSlideOverBtn = document.getElementById('close-slide-over');
    const cancelNewProjectBtn = document.getElementById('cancel-new-project');
    const newProjectForm = document.getElementById('new-project-form');
    const playbookSelect = document.getElementById('project-playbooks');
    let isSubmitting = false; // Submission guard flag

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

    // --- Initial Load ---
    if (document.getElementById('sidebar')) {
        loadSidebarProjects();
    }
});
