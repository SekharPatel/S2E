// /S2E/app/static/js/home.js
// FINAL VERSION: Fixes New Project bug and adds fully functional Edit/Delete logic.

document.addEventListener('DOMContentLoaded', function() {

    const openModal = (modalElement) => modalElement.classList.add('show-modal');
    const closeModal = (modalElement) => {
        modalElement.classList.remove('show-modal');
        const form = modalElement.querySelector('form');
        if (form) form.reset();
    };

    const projectSelect = document.getElementById('project-select-dropdown');
    if (projectSelect) {
        projectSelect.addEventListener('change', function() {
            document.body.style.cursor = 'wait';
            fetch('/api/projects/set_active', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: this.value })
            }).then(response => {
                if (response.ok) window.location.reload();
                else {
                    alert('Error switching project.');
                    document.body.style.cursor = 'default';
                }
            });
        });
    }

    // --- NEW PROJECT MODAL LOGIC ---
    const newProjectModal = document.getElementById('newProjectModal');
    const newProjectBtn = document.getElementById('newProjectBtn');
    const closeNewProjectBtn = document.getElementById('closeNewProjectBtn');
    const newProjectForm = document.getElementById('newProjectForm');

    if (newProjectModal && newProjectBtn && closeNewProjectBtn && newProjectForm) {
        newProjectBtn.addEventListener('click', () => openModal(newProjectModal));
        closeNewProjectBtn.addEventListener('click', () => closeModal(newProjectModal));
        newProjectModal.addEventListener('click', (e) => { if (e.target === newProjectModal) closeModal(newProjectModal); });

        newProjectForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnHTML = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Creating...`;

            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());

            fetch('/api/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(res => res.json()).then(result => {
                if (result.status === 'success') window.location.reload();
                else alert('Error: ' + (result.message || 'Could not create project.'));
            }).catch(err => alert('An unexpected network error occurred.'))
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            });
        });
    }

    // --- EDIT & DELETE PROJECT MODAL LOGIC ---
    const editProjectModal = document.getElementById('editProjectModal');
    const editProjectBtn = document.getElementById('editProjectBtn');
    const closeEditProjectBtn = document.getElementById('closeEditProjectBtn');
    const editProjectForm = document.getElementById('editProjectForm');
    const deleteProjectBtn = document.getElementById('deleteProjectBtn');

    if (editProjectModal && editProjectBtn && closeEditProjectBtn && editProjectForm && deleteProjectBtn) {
        editProjectBtn.addEventListener('click', function() {
            const activeProjectId = projectSelect.value;
            if (!activeProjectId) return;

            fetch(`/api/projects/${activeProjectId}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('editProjectId').value = data.id;
                    document.getElementById('editProjectName').value = data.name;
                    document.getElementById('editProjectDescription').value = data.description;
                    document.getElementById('editProjectTargets').value = data.targets;
                    openModal(editProjectModal);
                })
                .catch(err => alert('Could not load project data.'));
        });

        closeEditProjectBtn.addEventListener('click', () => closeModal(editProjectModal));
        editProjectModal.addEventListener('click', (e) => { if (e.target === editProjectModal) closeModal(editProjectModal); });

        // CRITICAL FIX: Implement the save functionality
        editProjectForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnHTML = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Saving...`;

            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            const projectId = data.project_id;

            fetch(`/api/projects/${projectId}/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(res => res.json()).then(result => {
                if (result.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + (result.message || 'Could not update project.'));
                }
            }).catch(err => alert('An unexpected network error occurred.'))
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            });
        });

        deleteProjectBtn.addEventListener('click', function() {
            const projectId = document.getElementById('editProjectId').value;
            const projectName = document.getElementById('editProjectName').value;

            if (!projectId) return;

            if (confirm(`Are you sure you want to permanently delete the project "${projectName}"?\n\nThis will delete all associated targets and tasks.`)) {
                this.disabled = true;
                this.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Deleting...`;

                fetch(`/api/projects/${projectId}`, {
                    method: 'DELETE'
                }).then(response => {
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        alert('Error deleting project. Please try again.');
                        this.disabled = false;
                        this.innerHTML = `<i class="fas fa-trash-alt me-1"></i>Delete Project`;
                    }
                });
            }
        });
    }
});