// /S2E/app/static/js/home.js

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('project-search');
    const projectGrid = document.getElementById('project-grid');

    function renderProjectGrid(projects) {
        if (!projectGrid) return;
        
        let gridHtml = '';
        if (projects && projects.length > 0) {
            projects.forEach(project => {
                gridHtml += `
                    <div class="project-row" data-project-name="${project.name.toLowerCase()}" data-project-id="${project.id}">
                        <div>${escapeHTML(project.name)}</div>
                        <div>${project.targets_count}</div>
                        <div>${project.tasks_count}</div>
                        <div>N/A</div>
                        <div class="project-actions">
                            <button class="run-btn" title="Run Default Playbook"><i class="fas fa-play"></i></button>
                            <button class="delete-btn" title="Delete Project"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                `;
            });
        } else {
            gridHtml = '<p style="padding: 20px;">No projects found. Create one to get started!</p>';
        }
        projectGrid.innerHTML = gridHtml;
    }
    
    function escapeHTML(str) {
        if (typeof str !== 'string') return '';
        return str.replace(/[&<>"']/g, function(match) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[match];
        });
    }

    function attachActionListeners() {
        projectGrid.addEventListener('click', function(e) {
            const target = e.target.closest('button');
            if (!target) return;

            const row = target.closest('.project-row');
            const projectId = row.dataset.projectId;

            if (target.classList.contains('delete-btn')) {
                handleDeleteProject(projectId);
            } else if (target.classList.contains('run-btn')) {
                handleRunPlaybook(projectId, target);
            }
        });
    }

    function handleDeleteProject(projectId) {
        if (confirm('Are you sure you want to delete this project and all its associated data?')) {
            fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    // --- THIS IS THE FIX ---
                    // Fetch the new, complete data once, then pass it to both render functions
                    fetch('/api/projects_data')
                        .then(res => res.json())
                        .then(data => {
                            renderProjectGrid(data.all_projects);
                            if (window.s2e && typeof window.s2e.renderSidebarProjects === 'function') {
                                window.s2e.renderSidebarProjects(data);
                            }
                        });
                    // -----------------------
                } else {
                    alert('Error: ' + result.message);
                }
            })
            .catch(error => console.error('Error deleting project:', error));
        }
    }

    function handleRunPlaybook(projectId, buttonElement) {
        const originalIcon = buttonElement.innerHTML;
        buttonElement.disabled = true;
        buttonElement.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;

        fetch(`/api/projects/${projectId}/run_default_playbook`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                buttonElement.innerHTML = `<i class="fas fa-check"></i>`;
                buttonElement.title = "Queued!";
                setTimeout(() => {
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = originalIcon;
                    buttonElement.title = "Run Default Playbook";
                }, 2000);
            } else {
                alert('Error: ' + result.message);
                buttonElement.disabled = false;
                buttonElement.innerHTML = originalIcon;
            }
        })
        .catch(error => {
            console.error('Error running playbook:', error);
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalIcon;
        });
    }

    if (searchInput && projectGrid) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = projectGrid.querySelectorAll('.project-row');
            rows.forEach(row => {
                const name = row.dataset.projectName || '';
                if (name.includes(searchTerm)) {
                    row.style.display = ''; 
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    if (projectGrid) {
        attachActionListeners();
    }
});
