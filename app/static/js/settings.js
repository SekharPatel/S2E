// /S2E/app/static/js/settings.js

document.addEventListener('DOMContentLoaded', function() {
    let currentProjectId = typeof ACTIVE_PROJECT_ID !== 'undefined' ? ACTIVE_PROJECT_ID : null;

    // --- Tab Switching Logic ---
    const navLinks = document.querySelectorAll('.settings-nav-link');
    const sections = document.querySelectorAll('.settings-section');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Deactivate all links and sections
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Activate the clicked link
            this.classList.add('active');

            // Activate the corresponding section
            const targetId = this.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });

    // This function fetches and renders the settings for a specific project ID
    function loadProjectSettings(projectId) {
        const contentArea = document.querySelector('.settings-content');
        if (!projectId) {
            contentArea.innerHTML =
                '<h2>No Project Selected</h2><p>Please select a project from the sidebar or create a new one to view its settings.</p>';
            return;
        }
        currentProjectId = projectId;

        fetch(`/api/settings/${projectId}/details`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Populate form fields
                document.getElementById('project-name').value = data.name;
                document.querySelector('.settings-project-title').textContent = data.name;
                document.getElementById('project-description').value = data.description;
                document.getElementById('project-targets').value = data.targets;

                // Populate playbook lists
                const linkedList = document.getElementById('linked-playbooks-list');
                const availableSelect = document.getElementById('available-playbooks-select');

                if (linkedList) {
                    linkedList.innerHTML = data.linked_playbooks.length ? '' : '<li class="empty-state">No playbooks linked yet.</li>';
                    data.linked_playbooks.forEach(p => {
                        linkedList.innerHTML += `<li data-playbook-id="${p.id}"><span>${p.name}</span><button class="btn-unlink"><i class="fas fa-times"></i></button></li>`;
                    });
                }

                if (availableSelect) {
                    availableSelect.innerHTML = '<option value="">Select a playbook to add...</option>';
                    data.available_playbooks.forEach(p => {
                        availableSelect.innerHTML += `<option value="${p.id}">${p.name}</option>`;
                    });
                }
            })
            .catch(error => {
                console.error('Error loading project settings:', error);
                const projectSettingsSection = document.getElementById('project-settings');
                if(projectSettingsSection) {
                    projectSettingsSection.innerHTML = '<h2>Error</h2><p>Could not load project settings. Please try again.</p>';
                }
            });
    }

    loadProjectSettings(currentProjectId);

    const saveButton = document.getElementById('save-project-settings');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const form = document.getElementById('project-settings-form');
            const data = {
                name: form.querySelector('#project-name').value,
                description: form.querySelector('#project-description').value,
                targets: form.querySelector('#project-targets').value,
            };

            fetch(`/api/settings/project/${currentProjectId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                alert(result.message);
                if (result.status === 'success') {
                    window.s2e.refreshProjectUI();
                }
            });
        });
    }

    const deleteButton = document.getElementById('delete-project-btn');
    if (deleteButton) {
        deleteButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to permanently delete this project? This action cannot be undone.')) {
                fetch(`/api/projects/${currentProjectId}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        alert('Project deleted successfully.');
                        window.s2e.refreshProjectUI().then(() => {
                            const newActiveId = window.s2e.state.activeProjectId;
                            if (newActiveId) {
                                loadProjectSettings(newActiveId);
                            } else {
                                window.location.href = '/';
                            }
                        });
                    } else {
                        alert('Error: ' + result.message);
                    }
                });
            }
        });
    }
    
    const linkButton = document.getElementById('link-playbook-btn');
    if(linkButton) {
        linkButton.addEventListener('click', function() {
            const select = document.getElementById('available-playbooks-select');
            const playbookId = select.value;
            if (!playbookId) return;

            fetch(`/api/settings/project/${currentProjectId}/link_playbook`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ playbook_id: playbookId })
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    loadProjectSettings(currentProjectId);
                } else {
                    alert('Error: ' + result.message);
                }
            });
        });
    }

    const linkedList = document.getElementById('linked-playbooks-list');
    if (linkedList) {
        linkedList.addEventListener('click', function(e) {
            if (e.target.closest('.btn-unlink')) {
                const li = e.target.closest('li');
                const playbookId = li.dataset.playbookId;
                
                fetch(`/api/settings/project/${currentProjectId}/unlink_playbook`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ playbook_id: playbookId })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        loadProjectSettings(currentProjectId);
                    } else {
                        alert('Error: ' + result.message);
                    }
                });
            }
        });
    }
});