// /S2E/app/static/js/base.js

// Create a global namespace for our app's functions and state
window.s2e = {
    // The global state that all pages can rely on
    state: {
        activeProjectId: null,
        allProjects: []
    },

    // Renders the sidebar project list using provided data
    renderSidebarProjects: function(data) {
        const container = document.getElementById('project-list-container');
        if (!container) return;

        container.innerHTML = ''; // Clear existing content
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
                a.innerHTML = `<i class="fas fa-folder fa-fw"></i> <span>${this.escapeHTML(project.name)}</span>`;
                li.appendChild(a);
                container.appendChild(li);
            });
        } else {
            container.innerHTML = `<li><a href="#"><i class="fas fa-info-circle fa-fw"></i> <span>No projects yet.</span></a></li>`;
        }
        this.attachProjectLinkListeners();
    },

    // The main function to refresh all UI components that depend on the project list
    refreshProjectUI: function() {
        return fetch('/api/projects_data')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Update the global state
                this.state.activeProjectId = data.active_project_id;
                this.state.allProjects = data.all_projects;

                // Render the sidebar with the new data
                this.renderSidebarProjects(data);

                // If a function to render the project grid exists (on home.html), call it
                if (typeof this.renderProjectGrid === 'function') {
                    this.renderProjectGrid(data.all_projects);
                }
            });
    },

    // Attaches click listeners to the project links in the sidebar
    attachProjectLinkListeners: function() {
        document.querySelectorAll('.project-link').forEach(link => {
            // Remove any existing listener to prevent duplicates
            link.replaceWith(link.cloneNode(true));
        });
        
        // Add new listeners
        document.querySelectorAll('.project-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const projectId = e.currentTarget.dataset.projectId;
                
                fetch('/api/projects/set_active', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_id: projectId })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        // Navigate to the correct page after setting the active project
                        const currentPage = window.location.pathname;
                        if (currentPage.startsWith('/settings')) {
                             window.location.href = '/settings';
                        } else {
                             window.location.reload();
                        }
                    } else {
                        alert('Error: ' + result.message);
                    }
                });
            });
        });
    },

    // Helper function to prevent XSS
    escapeHTML: function(str) {
        if (typeof str !== 'string') return '';
        return str.replace(/[&<>"']/g, match => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[match]));
    }
};

// Main execution block when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only run the initial data fetch if a sidebar exists on the page
    if (document.getElementById('sidebar')) {
        window.s2e.refreshProjectUI();
    }

    // --- Modal & New Project Form Logic ---
    const modal = document.getElementById('new-project-modal');
    const newProjectBtnSidebar = document.getElementById('new-project-sidebar-btn');
    const newProjectFabMain = document.getElementById('new-project-fab-main');
    const cancelModalBtn = document.getElementById('cancel-modal-btn');
    const newProjectForm = document.getElementById('new-project-modal-form');
    let isSubmitting = false;

    function openModal() {
        if (modal) modal.style.display = 'flex';
    }

    function closeModal() {
        if (modal) modal.style.display = 'none';
    }

    if (newProjectBtnSidebar) newProjectBtnSidebar.addEventListener('click', openModal);
    if (newProjectFabMain) newProjectFabMain.addEventListener('click', openModal);
    if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);

    if (newProjectForm) {
        newProjectForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (isSubmitting) return;
            isSubmitting = true;

            const projectName = document.getElementById('new-project-name').value;
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;

            fetch('/api/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: projectName })
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success' && result.redirect_url) {
                    window.location.href = result.redirect_url;
                } else {
                    alert('Error: ' + result.message);
                    isSubmitting = false;
                    submitButton.disabled = false;
                }
            });
        });
    }
});
