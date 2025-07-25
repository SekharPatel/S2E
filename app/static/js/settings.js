// /S2E/app/static/js/settings.js

document.addEventListener('DOMContentLoaded', function() {
    let currentProjectId = null;

    function initializeSettings() {
        fetch('/api/active-project-id')
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        // No active project, which is a valid state.
                        // The UI should guide the user to create or select a project.
                        const contentArea = document.querySelector('.settings-content');
                        contentArea.innerHTML = '<h2>No Active Project</h2><p>Please create or select a project to see its settings.</p>';
                        document.querySelector('.settings-project-title').textContent = 'No Project Selected';
                    } else {
                        // Other server-side error
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return null; // Stop the promise chain
                }
                return response.json();
            })
            .then(data => {
                if (data && data.active_project_id) {
                    currentProjectId = data.active_project_id;
                    // Now that we have the project ID, load its settings
                    loadProjectSettings(currentProjectId);
                }
            })
            .catch(error => {
                console.error('Error fetching active project ID:', error);
                const contentArea = document.querySelector('.settings-content');
                contentArea.innerHTML = '<h2>Error</h2><p>Could not determine the active project. Please refresh the page.</p>';
            });
    }


    // --- Tab Switching Logic ---
    const navLinks = document.querySelectorAll('.settings-nav-link');
    const sections = document.querySelectorAll('.settings-section');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            this.classList.add('active');
            const targetId = this.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });

    function loadProjectSettings(projectId) {
        const contentArea = document.querySelector('.settings-content');
        if (!projectId) {
            contentArea.innerHTML =
                '<h2>No Project Selected</h2><p>Please select a project from the sidebar or create a new one.</p>';
            return;
        }
        currentProjectId = projectId;

        fetch(`/api/project/${projectId}/details`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                document.getElementById('project-name').value = data.name;
                document.querySelector('.settings-project-title').textContent = data.name;
                document.getElementById('project-description').value = data.description;
                document.getElementById('project-targets').value = data.targets;

                const linkedList = document.getElementById('linked-playbooks-list');
                // FIX: Target the new available playbooks list
                const availableList = document.getElementById('available-playbooks-list');

                if (linkedList) {
                    linkedList.innerHTML = data.linked_playbooks.length ? '' : '<li class="empty-state">No playbooks linked yet.</li>';
                    data.linked_playbooks.forEach(p => {
                        linkedList.innerHTML += `<li data-playbook-id="${p.id}"><span>${p.name}</span><button class="btn-unlink"><i class="fas fa-times"></i></button></li>`;
                    });
                }

                // FIX: Populate the new available playbooks list
                if (availableList) {
                    availableList.innerHTML = data.available_playbooks.length ? '' : '<li class="empty-state">No other playbooks available.</li>';
                    data.available_playbooks.forEach(p => {
                        // Added btn-link class for event delegation
                        availableList.innerHTML += `<li data-playbook-id="${p.id}"><span>${p.name}</span><button class="btn-link"><i class="fas fa-plus"></i></button></li>`;
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

    initializeSettings();

    const saveButton = document.getElementById('save-project-settings');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const form = document.getElementById('project-settings-form');
            const linkedPlaybookIds = Array.from(document.querySelectorAll('#linked-playbooks-list li'))
                                           .map(li => li.dataset.playbookId)
                                           .filter(id => id);

            const data = {
                name: form.querySelector('#project-name').value,
                description: form.querySelector('#project-description').value,
                targets: form.querySelector('#project-targets').value,
                linked_playbook_ids: linkedPlaybookIds
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
            if (confirm('Are you sure you want to permanently delete this project?')) {
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
    
    // FIX: Updated logic to move items between the two lists
    const availableList = document.getElementById('available-playbooks-list');
    if (availableList) {
        availableList.addEventListener('click', function(e) {
            const linkButton = e.target.closest('.btn-link');
            if (linkButton) {
                const liToMove = linkButton.closest('li');
                const playbookId = liToMove.dataset.playbookId;
                const playbookName = liToMove.querySelector('span').textContent;

                // Add to linked list UI
                const linkedList = document.getElementById('linked-playbooks-list');
                const emptyState = linkedList.querySelector('.empty-state');
                if (emptyState) emptyState.remove();
                
                linkedList.innerHTML += `<li data-playbook-id="${playbookId}"><span>${playbookName}</span><button class="btn-unlink"><i class="fas fa-times"></i></button></li>`;

                // Remove from available list UI
                liToMove.remove();
                if (availableList.children.length === 0) {
                    availableList.innerHTML = '<li class="empty-state">No other playbooks available.</li>';
                }
            }
        });
    }


    const linkedList = document.getElementById('linked-playbooks-list');
    if (linkedList) {
        linkedList.addEventListener('click', function(e) {
            if (e.target.closest('.btn-unlink')) {
                const liToMove = e.target.closest('li');
                const playbookId = liToMove.dataset.playbookId;
                const playbookName = liToMove.querySelector('span').textContent;

                // Add back to available list
                const availableList = document.getElementById('available-playbooks-list');
                const emptyState = availableList.querySelector('.empty-state');
                if (emptyState) emptyState.remove();

                availableList.innerHTML += `<li data-playbook-id="${playbookId}"><span>${playbookName}</span><button class="btn-link"><i class="fas fa-plus"></i></button></li>`;

                // Remove from linked list UI
                liToMove.remove();

                if (linkedList.children.length === 0) {
                    linkedList.innerHTML = '<li class="empty-state">No playbooks linked yet.</li>';
                }
            }
        });
    }
});