// tasks.js

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.task-row[data-status="running"], .task-row[data-status="starting"]').forEach(function(row) {
        const taskId = row.dataset.taskId || row.querySelector('.task-id-code').textContent.trim();
        startTaskPolling(taskId, row);
    });

    document.querySelectorAll('.stop-task').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const taskId = btn.getAttribute('data-task-id');
            if (confirm('Are you sure you want to stop this task?')) {
                stopTask(taskId, btn);
            }
        });
    });
    updateTaskStatistics(); // Initial call
});

function startTaskPolling(taskId, rowElement) {
    const statusBadgeSpan = rowElement.querySelector('.task-status-badge');
    const statusTextSpan = statusBadgeSpan.querySelector('.status-text'); // Target the text part
    const actionsCell = rowElement.querySelector('.task-actions');

    let pollIntervalId = null;

    function poll() {
        fetch(`/task/${taskId}/status`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                const newStatusLower = data.status.toLowerCase();
                const currentStatusOnPage = rowElement.dataset.status; // Get status from tr data attribute

                if (statusTextSpan && currentStatusOnPage !== newStatusLower) {
                    statusBadgeSpan.className = 'task-status-badge status-' + newStatusLower; // Update badge class
                    statusTextSpan.textContent = capitalize(data.status);
                    rowElement.dataset.status = newStatusLower; // Update tr data-status

                    // Handle spinner/icon visibility
                    let existingLoader = statusBadgeSpan.querySelector('.custom-loader');
                    let existingIcon = statusBadgeSpan.querySelector('i.fas');

                    if (existingLoader) existingLoader.remove();
                    if (existingIcon) existingIcon.remove();

                    if (newStatusLower === 'running' || newStatusLower === 'starting') {
                        const loaderSpan = document.createElement('span');
                        loaderSpan.className = 'custom-loader';
                        statusBadgeSpan.insertBefore(loaderSpan, statusTextSpan);
                    } else {
                        const icon = document.createElement('i');
                        icon.classList.add('fas', 'me-1');
                        if (newStatusLower === 'completed') icon.classList.add('fa-check');
                        else if (newStatusLower === 'failed' || newStatusLower === 'error') icon.classList.add('fa-times');
                        else if (newStatusLower === 'stopped') icon.classList.add('fa-stop');
                        else icon.classList.add('fa-clock');
                        statusBadgeSpan.insertBefore(icon, statusTextSpan);
                    }
                }

                // Update actions (Stop button)
                const existingStopButton = actionsCell.querySelector('.stop-task');
                if (newStatusLower === 'running') {
                    if (!existingStopButton) {
                        const newStopButton = document.createElement('button');
                        newStopButton.className = 'btn-secondary btn-small btn-danger-themed stop-task';
                        newStopButton.dataset.taskId = taskId;
                        newStopButton.innerHTML = '<i class="fas fa-stop me-1"></i>Stop';
                        newStopButton.addEventListener('click', function() {
                            if (confirm('Are you sure you want to stop this task?')) {
                                stopTask(taskId, newStopButton);
                            }
                        });
                        actionsCell.appendChild(newStopButton);
                    }
                } else {
                    if (existingStopButton) existingStopButton.remove();
                }
                
                if (newStatusLower !== 'running' && newStatusLower !== 'starting') {
                    if (pollIntervalId) clearInterval(pollIntervalId);
                    updateTaskStatistics();
                }
            })
            .catch(error => {
                console.error(`Error polling task ${taskId}:`, error);
                if (pollIntervalId) clearInterval(pollIntervalId);
            });
    }
    poll();
    pollIntervalId = setInterval(poll, 3000);
}

function stopTask(taskId, btn) {
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Stopping...';

    fetch(`/task/${taskId}/stop`, {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                // Polling will update the UI, but for immediate feedback:
                const row = document.querySelector(`.task-row[data-task-id="${taskId}"]`);
                if (row) {
                    const statusBadgeSpan = row.querySelector('.task-status-badge');
                    const statusTextSpan = statusBadgeSpan.querySelector('.status-text');
                    
                    statusBadgeSpan.className = 'task-status-badge status-stopped';
                    statusTextSpan.textContent = 'Stopped';
                    row.dataset.status = 'stopped'; // Update data attribute

                    let existingLoader = statusBadgeSpan.querySelector('.custom-loader');
                    if (existingLoader) existingLoader.remove();
                    
                    let existingIcon = statusBadgeSpan.querySelector('i.fas');
                    if (existingIcon) existingIcon.remove();
                    
                    const icon = document.createElement('i');
                    icon.classList.add('fas', 'fa-stop', 'me-1');
                    statusBadgeSpan.insertBefore(icon, statusTextSpan);
                }
                btn.remove();
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

function updateTaskStatistics() {
    const runningCountEl = document.querySelector('.stat-card-value.running-count');
    const completedCountEl = document.querySelector('.stat-card-value.completed-count');
    const failedCountEl = document.querySelector('.stat-card-value.failed-count');

    if (!runningCountEl || !completedCountEl || !failedCountEl) {
        // console.warn("Statistic count elements not found."); // Already handled by initial check
        return;
    }

    let running = 0;
    let completed = 0;
    let failed = 0;

    document.querySelectorAll('.task-row').forEach(row => { // Iterate over rows
        const status = row.dataset.status; // Use data-status from the row
        if (status === 'running' || status === 'starting') {
            running++;
        } else if (status === 'completed') {
            completed++;
        } else if (status === 'failed' || status === 'error') {
            failed++;
        }
    });

    runningCountEl.textContent = running;
    completedCountEl.textContent = completed;
    failedCountEl.textContent = failed;
}