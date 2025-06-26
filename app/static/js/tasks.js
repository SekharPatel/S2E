// /S2E/app/static/js/tasks.js
// UPDATED: Fixes the bug where the preview panel does not open on click.

document.addEventListener('DOMContentLoaded', function() {
    const tasksPageWrapper = document.querySelector('.tasks-page-wrapper');
    const taskPreviewPane = document.getElementById('taskPreviewPane');
    const previewPaneTitle = document.getElementById('previewPaneTitle');
    const previewPaneContent = document.getElementById('previewPaneContent');
    const moreDetailsLink = document.getElementById('moreDetailsLink');
    const closePreviewBtn = document.getElementById('closePreviewBtn');
    const tasksTableBody = document.querySelector('#tasksTable tbody');

    let activePreviewTaskId = null;
    let isPreviewOpen = false;
    const pollingIntervals = {};

    document.querySelectorAll('.task-row').forEach(row => {
        const taskId = row.dataset.taskId;
        const status = row.dataset.status;

        if (status === 'running' || status === 'starting') {
            startTaskPolling(taskId, row);
        }

        const stopBtn = row.querySelector('.stop-task');
        if (stopBtn) {
            stopBtn.addEventListener('click', function(e) {
                e.stopPropagation(); 
                const taskId = this.getAttribute('data-task-id');
                if (confirm('Are you sure you want to stop this task?')) {
                    stopTask(taskId, this);
                }
            });
        }
    });
    
    document.querySelectorAll('.view-task-preview').forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const taskId = this.dataset.taskId;
            togglePreviewPane(taskId);
        });
    });

    if (closePreviewBtn) {
        closePreviewBtn.addEventListener('click', function() {
            closePreviewPane();
        });
    }

    function renderPreviewContent(status) {
        if (!isPreviewOpen || !previewPaneContent) return;
        
        status = status.toLowerCase();
        let contentHtml = '';

        if (status === 'running' || status === 'starting') {
            contentHtml = `
                <div class="terminal-placeholder">
                    <span class="loader"></span>
                    <p>Task is running...</p>
                    <p style="font-size:0.9em; color:#9ca3af;">Full output will be available upon completion.</p>
                </div>`;
        } else if (status === 'completed') {
            contentHtml = `
                <div class="terminal-placeholder" style="color:#86efac;">
                    <i class="fas fa-check-circle fa-2x"></i>
                    <p>Task completed successfully.</p>
                </div>`;
        } else if (status === 'failed' || status === 'error') {
            contentHtml = `
                <div class="terminal-placeholder error-state">
                    <i class="fas fa-exclamation-circle fa-2x"></i>
                    <p>Task ended with status: ${capitalize(status)}.</p>
                </div>`;
        } else if (status === 'stopped') {
            contentHtml = `
                <div class="terminal-placeholder stopped-state">
                    <i class="fas fa-stop-circle fa-2x"></i>
                    <p>Task was stopped by the user.</p>
                </div>`;
        } else {
            contentHtml = '<p class="text-muted">Loading preview...</p>';
        }

        previewPaneContent.innerHTML = contentHtml;
    }

    function fetchAndDisplayPreview(taskId) {
        if (!previewPaneContent || !previewPaneTitle || !moreDetailsLink) return;

        previewPaneTitle.textContent = `Preview: ${taskId}`;
        previewPaneContent.innerHTML = '<p class="text-muted">Loading preview...</p>'; 
        moreDetailsLink.href = `/task/${taskId}`;
        moreDetailsLink.classList.remove('d-none');

        fetch(`/api/task/${taskId}/status`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (activePreviewTaskId === taskId && isPreviewOpen) {
                    renderPreviewContent(data.status); 
                }
            })
            .catch(error => {
                console.error(`Error fetching preview for task ${taskId}:`, error);
                if (activePreviewTaskId === taskId && isPreviewOpen) {
                    previewPaneContent.innerHTML = '<p style="color:#ef4444;">Error loading preview.</p>';
                    moreDetailsLink.classList.add('d-none');
                }
            });
    }

    // --- MODIFIED FUNCTION ---
    function openPreviewPane(taskId) {
        if (!tasksPageWrapper || !taskPreviewPane) return;
        
        const currentlySelectedRow = tasksTableBody.querySelector('.task-row.selected-for-preview');
        if (currentlySelectedRow) currentlySelectedRow.classList.remove('selected-for-preview');
        
        const newSelectedRow = tasksTableBody.querySelector(`.task-row[data-task-id="${taskId}"]`);
        if (newSelectedRow) newSelectedRow.classList.add('selected-for-preview');

        activePreviewTaskId = taskId;
        isPreviewOpen = true;
        tasksPageWrapper.classList.add('preview-active');
        taskPreviewPane.classList.add('open'); // <-- THIS LINE WAS MISSING
        fetchAndDisplayPreview(taskId);
    }

    // --- MODIFIED FUNCTION ---
    function closePreviewPane() {
        if (!tasksPageWrapper || !taskPreviewPane) return;
        tasksPageWrapper.classList.remove('preview-active');
        taskPreviewPane.classList.remove('open'); // <-- THIS LINE WAS MISSING
        activePreviewTaskId = null;
        isPreviewOpen = false;

        const currentlySelectedRow = tasksTableBody.querySelector('.task-row.selected-for-preview');
        if (currentlySelectedRow) currentlySelectedRow.classList.remove('selected-for-preview');

        if (previewPaneTitle) previewPaneTitle.textContent = 'Task Preview';
        if (previewPaneContent) previewPaneContent.innerHTML = '<p class="text-muted">Select a task to view its preview.</p>';
        if (moreDetailsLink) moreDetailsLink.classList.add('d-none');
    }

    function togglePreviewPane(taskId) {
        if (activePreviewTaskId === taskId && isPreviewOpen) {
            closePreviewPane();
        } else {
            openPreviewPane(taskId);
        }
    }

    // The rest of the JS functions (startTaskPolling, updateTaskRowUI, stopTask, etc.) remain unchanged.
    function startTaskPolling(taskId, rowElement) {
        if (pollingIntervals[taskId]) return; 

        const statusBadgeSpan = rowElement.querySelector('.task-status-badge');
        if (!statusBadgeSpan) return;
        
        const poll = () => {
            fetch(`/api/task/${taskId}/status`)
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    const newStatusLower = data.status.toLowerCase();
                    const currentStatusOnPage = rowElement.dataset.status;

                    if (currentStatusOnPage !== newStatusLower) {
                        updateTaskRowUI(rowElement, newStatusLower);
                    }

                    if (isPreviewOpen && activePreviewTaskId === taskId) {
                        renderPreviewContent(data.status);
                    }

                    if (newStatusLower !== 'running' && newStatusLower !== 'starting') {
                        if (pollingIntervals[taskId]) {
                            clearInterval(pollingIntervals[taskId]);
                            delete pollingIntervals[taskId];
                        }
                        updateTaskStatistics();
                    }
                })
                .catch(error => {
                    console.error(`Error polling task ${taskId}:`, error);
                    if (pollingIntervals[taskId]) {
                        clearInterval(pollingIntervals[taskId]);
                        delete pollingIntervals[taskId];
                    }
                });
        };
        poll(); 
        pollingIntervals[taskId] = setInterval(poll, 3000);
    }
    
    function updateTaskRowUI(rowElement, newStatus) {
        const statusBadgeSpan = rowElement.querySelector('.task-status-badge');
        const statusTextSpan = statusBadgeSpan.querySelector('.status-text');
        const actionsCell = rowElement.querySelector('.task-actions');
        const taskId = rowElement.dataset.taskId;

        rowElement.dataset.status = newStatus;
        statusBadgeSpan.className = 'task-status-badge status-' + newStatus;
        statusTextSpan.textContent = capitalize(newStatus);
        
        let existingLoader = statusBadgeSpan.querySelector('.custom-loader');
        let existingIcon = statusBadgeSpan.querySelector('i.fas');
        if (existingLoader) existingLoader.remove();
        if (existingIcon) existingIcon.remove();

        const icon = document.createElement('i');
        icon.classList.add('fas', 'me-1');
        if (newStatus === 'running' || newStatus === 'starting') {
            const loaderSpan = document.createElement('span');
            loaderSpan.className = 'custom-loader';
            statusBadgeSpan.insertBefore(loaderSpan, statusTextSpan);
        } else {
            if (newStatus === 'completed') icon.classList.add('fa-check');
            else if (newStatus === 'failed' || newStatus === 'error') icon.classList.add('fa-times');
            else if (newStatus === 'stopped') icon.classList.add('fa-stop');
            else icon.classList.add('fa-clock');
            statusBadgeSpan.insertBefore(icon, statusTextSpan);
        }

        const existingStopButton = actionsCell.querySelector('.stop-task');
        if (newStatus === 'running') {
            if (!existingStopButton) {
                const newStopButton = document.createElement('button');
                newStopButton.className = 'btn-secondary btn-small btn-danger-themed stop-task';
                newStopButton.dataset.taskId = taskId;
                newStopButton.innerHTML = '<i class="fas fa-stop me-1"></i>Stop';
                newStopButton.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (confirm('Are you sure you want to stop this task?')) {
                        stopTask(taskId, newStopButton);
                    }
                });
                actionsCell.appendChild(newStopButton);
            }
        } else {
            if (existingStopButton) existingStopButton.remove();
        }
    }

    function stopTask(taskId, btn) {
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Stopping...';

        fetch(`/api/task/${taskId}/stop`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    const row = document.querySelector(`.task-row[data-task-id="${taskId}"]`);
                    if (row) {
                        updateTaskRowUI(row, 'stopped');
                    }
                    if (isPreviewOpen && activePreviewTaskId === taskId) {
                        renderPreviewContent('stopped');
                    }
                    updateTaskStatistics();
                } else {
                    alert('Error: ' + (data.message || 'Could not stop task.'));
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
            })
            .catch(() => {
                alert('An error occurred while stopping the task.');
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            });
    }

    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    updateTaskStatistics();
    function updateTaskStatistics() {
        const runningCountEl = document.querySelector('.stat-card-value.running-count');
        const completedCountEl = document.querySelector('.stat-card-value.completed-count');
        const failedCountEl = document.querySelector('.stat-card-value.failed-count');

        if (!runningCountEl || !completedCountEl || !failedCountEl) return;

        let running = 0, completed = 0, failed = 0;
        document.querySelectorAll('.task-row').forEach(row => {
            const status = row.dataset.status;
            if (status === 'running' || status === 'starting') running++;
            else if (status === 'completed') completed++;
            else if (status === 'failed' || status === 'error') failed++;
        });
        runningCountEl.textContent = running;
        completedCountEl.textContent = completed;
        failedCountEl.textContent = failed;
    }
});