// tasks.js - Handles polling, stop button, and live UI updates for tasks page

document.addEventListener('DOMContentLoaded', function() {
    // For each running task, start polling
    document.querySelectorAll('.task-row[data-status="running"]').forEach(function(row) {
        const taskId = row.querySelector('.task-id-code').textContent.trim();
        startTaskPolling(taskId, row);
    });

    // Attach stop button handler (delegated)
    document.querySelectorAll('.stop-task').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const taskId = btn.getAttribute('data-task-id');
            if (confirm('Are you sure you want to stop this task?')) {
                stopTask(taskId, btn);
            }
        });
    });
});

function startTaskPolling(taskId, row) {
    const statusBadge = row.querySelector('.task-status-badge');
    const stopBtn = row.querySelector('.stop-task');
    const scanCard = document.getElementById('scan-card-' + taskId);
    const progressBar = scanCard ? scanCard.querySelector('.scan-progress-bar-inner') : null;
    const scanLog = scanCard ? scanCard.querySelector('.scan-log') : null;
    const scanStatus = scanCard ? scanCard.querySelector('.scan-status-badge') : null;

    function poll() {
        fetch(`/task/${taskId}/status`).then(r => r.json()).then(data => {
            // Update scan log and progress bar if present
            if (scanLog && data.recent_output) {
                scanLog.textContent = data.recent_output.join('\n');
                // Fake progress: estimate by number of lines (for demo)
                let progress = Math.min(100, data.recent_output.length * 2);
                if (progressBar) progressBar.style.width = progress + '%';
            }
            // Update status badge
            if (statusBadge) {
                statusBadge.textContent = capitalize(data.status);
                statusBadge.className = 'task-status-badge status-' + data.status.toLowerCase();
                // Add icon
                let icon = document.createElement('i');
                icon.classList.add('fas', 'me-1');
                if (data.status === 'running') icon.classList.add('fa-spinner', 'fa-spin');
                else if (data.status === 'completed') icon.classList.add('fa-check');
                else if (data.status === 'failed' || data.status === 'error') icon.classList.add('fa-times');
                else if (data.status === 'stopped') icon.classList.add('fa-stop');
                else icon.classList.add('fa-clock');
                statusBadge.prepend(icon);
            }
            // Update scan card status
            if (scanStatus) {
                scanStatus.textContent = capitalize(data.status);
            }
            // If finished, update actions
            if (data.status !== 'running') {
                if (stopBtn) stopBtn.remove();
                if (progressBar) progressBar.style.width = '100%';
            } else {
                setTimeout(poll, 2000);
            }
        });
    }
    poll();
}

function stopTask(taskId, btn) {
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Stopping...';
    fetch(`/task/${taskId}/stop`, {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                // Find the row and update status immediately
                const row = document.querySelector(`.task-row .task-id-code:contains('${taskId}')`);
                if (row) {
                    const badge = row.closest('tr').querySelector('.task-status-badge');
                    if (badge) {
                        badge.textContent = 'Stopped';
                        badge.className = 'task-status-badge status-stopped';
                        let icon = document.createElement('i');
                        icon.classList.add('fas', 'fa-stop', 'me-1');
                        badge.prepend(icon);
                    }
                }
                btn.remove();
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