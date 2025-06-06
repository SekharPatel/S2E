// tasks.js

document.addEventListener('DOMContentLoaded', function() {
    const tasksListContainer = document.getElementById('tasksListContainer');
    const taskPreviewPane = document.getElementById('taskPreviewPane');
    const previewPaneTitle = document.getElementById('previewPaneTitle');
    const previewPaneContent = document.getElementById('previewPaneContent');
    const moreDetailsLink = document.getElementById('moreDetailsLink');
    const closePreviewBtn = document.getElementById('closePreviewBtn');
    const tasksTableBody = document.querySelector('#tasksTable tbody');

    let activePreviewTaskId = null;
    let isPreviewOpen = false; // Track preview pane state

    // --- Existing Polling and Stop Task Logic ---
    document.querySelectorAll('.task-row[data-status="running"], .task-row[data-status="starting"]').forEach(function(row) {
        const taskId = row.dataset.taskId;
        if (taskId) {
            startTaskPolling(taskId, row);
        }
    });

    document.querySelectorAll('.stop-task').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const taskId = btn.getAttribute('data-task-id');
            if (confirm('Are you sure you want to stop this task?')) {
                stopTask(taskId, btn);
            }
        });
    });
    updateTaskStatistics();

    // --- Preview Pane Logic ---
    document.querySelectorAll('.view-task-preview').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.dataset.taskId;
            togglePreviewPane(taskId);
        });
    });

    if (closePreviewBtn) {
        closePreviewBtn.addEventListener('click', function() {
            closePreviewPane();
        });
    }

    function togglePreviewPane(taskId) {
        if (activePreviewTaskId === taskId && isPreviewOpen) {
            closePreviewPane();
        } else {
            openPreviewPane(taskId);
        }
    }

    function fetchAndDisplayPreview(taskId, isInitialLoad = false) {
        if (!previewPaneContent || !previewPaneTitle || !moreDetailsLink) return;

        if (isInitialLoad) {
            previewPaneTitle.textContent = `Preview: ${taskId}`;
            previewPaneContent.innerHTML = '<p class="text-muted">Loading preview...</p>';
            moreDetailsLink.classList.add('d-none');
        }

        fetch(`/task/${taskId}/status`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                // Only update if the preview for this task is still active
                if (activePreviewTaskId === taskId && isPreviewOpen) {
                    if (data.recent_output && data.recent_output.length > 0) {
                        const sanitizedOutput = data.recent_output
                            .map(line => line.replace(/</g, "&lt;").replace(/>/g, "&gt;"))
                            .join('\n');
                        // Preserve scroll position if updating existing content and not just loading
                        const shouldPreserveScroll = !isInitialLoad && previewPaneContent.innerHTML !== '<p class="text-muted">Loading preview...</p>';
                        const oldScrollTop = shouldPreserveScroll ? previewPaneContent.scrollTop : 0;
                        const oldScrollHeight = shouldPreserveScroll ? previewPaneContent.scrollHeight : 0;

                        previewPaneContent.innerHTML = `<pre>${sanitizedOutput}</pre>`;

                        if (shouldPreserveScroll) {
                           // Auto-scroll to bottom if user was near the bottom, otherwise maintain position
                            if (oldScrollTop >= oldScrollHeight - previewPaneContent.clientHeight - 30) { // 30px tolerance
                                previewPaneContent.scrollTop = previewPaneContent.scrollHeight;
                            } else {
                                previewPaneContent.scrollTop = oldScrollTop;
                            }
                        } else {
                            previewPaneContent.scrollTop = previewPaneContent.scrollHeight; // Scroll to bottom on initial load
                        }

                    } else if (isInitialLoad) { // Only show "no output" on initial load
                        previewPaneContent.innerHTML = '<p class="text-muted">No recent output available for this task.</p>';
                    }
                    
                    if (isInitialLoad) { // Only setup link on initial open
                        moreDetailsLink.href = `/task/${taskId}`;
                        moreDetailsLink.classList.remove('d-none');
                    }
                }
            })
            .catch(error => {
                console.error(`Error fetching preview for task ${taskId}:`, error);
                if (activePreviewTaskId === taskId && isPreviewOpen && isInitialLoad) { // Only show error in pane on initial load
                    previewPaneContent.innerHTML = '<p style="color:#ef4444;">Error loading preview.</p>';
                    moreDetailsLink.classList.add('d-none');
                }
            });
    }


    function openPreviewPane(taskId) {
        if (!tasksListContainer || !taskPreviewPane) return;

        if (tasksTableBody) {
            const currentlySelectedRow = tasksTableBody.querySelector('.task-row.selected-for-preview');
            if (currentlySelectedRow) currentlySelectedRow.classList.remove('selected-for-preview');
            
            const newSelectedRow = tasksTableBody.querySelector(`.task-row[data-task-id="${taskId}"]`);
            if (newSelectedRow) newSelectedRow.classList.add('selected-for-preview');
        }

        activePreviewTaskId = taskId;
        isPreviewOpen = true;
        tasksListContainer.classList.add('preview-open');
        taskPreviewPane.classList.add('open');

        fetchAndDisplayPreview(taskId, true); // true for initial load
    }

    function closePreviewPane() {
        if (!tasksListContainer || !taskPreviewPane) return;

        tasksListContainer.classList.remove('preview-open');
        taskPreviewPane.classList.remove('open');
        activePreviewTaskId = null;
        isPreviewOpen = false;

        if (tasksTableBody) {
            const currentlySelectedRow = tasksTableBody.querySelector('.task-row.selected-for-preview');
            if (currentlySelectedRow) currentlySelectedRow.classList.remove('selected-for-preview');
        }
        if (previewPaneTitle) previewPaneTitle.textContent = 'Task Preview';
        if (previewPaneContent) previewPaneContent.innerHTML = '<p class="text-muted">Select a task to view its preview.</p>';
        if (moreDetailsLink) moreDetailsLink.classList.add('d-none');
    }


    function startTaskPolling(taskId, rowElement) {
        const statusBadgeSpan = rowElement.querySelector('.task-status-badge');
        if (!statusBadgeSpan) return;
        
        const statusTextSpan = statusBadgeSpan.querySelector('.status-text');
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
                    let currentStatusOnPage = rowElement.dataset.status;
                    
                    if (statusTextSpan && currentStatusOnPage !== newStatusLower) {
                        rowElement.dataset.status = newStatusLower;
                        statusBadgeSpan.className = 'task-status-badge status-' + newStatusLower;
                        statusTextSpan.textContent = capitalize(data.status);
                        
                        // Icon update logic (same as before)
                        let existingLoader = statusBadgeSpan.querySelector('.custom-loader');
                        let existingIcon = statusBadgeSpan.querySelector('i.fas');
                        if (existingLoader) existingLoader.remove();
                        if (existingIcon) existingIcon.remove();
                        if (newStatusLower === 'running' || newStatusLower === 'starting') { /* ... add loader ... */ 
                            const loaderSpan = document.createElement('span');
                            loaderSpan.className = 'custom-loader';
                            statusBadgeSpan.insertBefore(loaderSpan, statusTextSpan);
                        } else { /* ... add static icon ... */ 
                            const icon = document.createElement('i');
                            icon.classList.add('fas', 'me-1');
                            if (newStatusLower === 'completed') icon.classList.add('fa-check');
                            else if (newStatusLower === 'failed' || newStatusLower === 'error') icon.classList.add('fa-times');
                            else if (newStatusLower === 'stopped') icon.classList.add('fa-stop');
                            else icon.classList.add('fa-clock');
                            statusBadgeSpan.insertBefore(icon, statusTextSpan);
                        }
                    }

                    // Stop button logic (same as before)
                    if (actionsCell) { /* ... stop button logic ... */ 
                        const existingStopButton = actionsCell.querySelector('.stop-task');
                        if (newStatusLower === 'running') {
                            if (!existingStopButton) {
                                const newStopButton = document.createElement('button');
                                newStopButton.className = 'btn-secondary btn-small btn-danger-themed stop-task';
                                newStopButton.dataset.taskId = taskId;
                                newStopButton.innerHTML = '<i class="fas fa-stop me-1"></i>Stop';
                                newStopButton.addEventListener('click', function() { /* ... confirm and stop ... */ 
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
                    
                    // Auto-update preview if open and task is still running
                    if (isPreviewOpen && activePreviewTaskId === taskId && (newStatusLower === 'running' || newStatusLower === 'starting')) {
                        fetchAndDisplayPreview(taskId, false); // false for subsequent updates
                    }

                    if (newStatusLower !== 'running' && newStatusLower !== 'starting') {
                        if (pollIntervalId) clearInterval(pollIntervalId);
                        updateTaskStatistics();
                        // If preview was open for this task and it just finished, ensure final output is shown
                        if (isPreviewOpen && activePreviewTaskId === taskId) {
                             fetchAndDisplayPreview(taskId, false); // Get final recent output
                        }
                    }
                })
                .catch(error => {
                    console.error(`Error polling task ${taskId}:`, error);
                    if (pollIntervalId) clearInterval(pollIntervalId);
                });
        }
        poll();
        pollIntervalId = setInterval(poll, 2500); // Poll slightly more frequently for preview updates
    }

    // stopTask, capitalize, updateTaskStatistics functions remain the same as previous version.
    // Make sure they are correctly defined here.
    function stopTask(taskId, btn) {
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Stopping...';

        fetch(`/task/${taskId}/stop`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    const row = document.querySelector(`.task-row[data-task-id="${taskId}"]`);
                    if (row) {
                        const statusBadgeSpan = row.querySelector('.task-status-badge');
                        if (statusBadgeSpan) { 
                            const statusTextSpan = statusBadgeSpan.querySelector('.status-text');
                            statusBadgeSpan.className = 'task-status-badge status-stopped';
                           if(statusTextSpan) statusTextSpan.textContent = 'Stopped';
                            row.dataset.status = 'stopped';

                            let existingLoader = statusBadgeSpan.querySelector('.custom-loader');
                            if (existingLoader) existingLoader.remove();
                            let existingIcon = statusBadgeSpan.querySelector('i.fas');
                            if (existingIcon) existingIcon.remove();
                            const icon = document.createElement('i');
                            icon.classList.add('fas', 'fa-stop', 'me-1');
                            if(statusTextSpan) statusBadgeSpan.insertBefore(icon, statusTextSpan);
                            else statusBadgeSpan.appendChild(icon);
                        }
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