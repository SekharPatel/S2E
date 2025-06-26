// /S2E/app/static/js/task_details.js

document.addEventListener('DOMContentLoaded', function () {
    const taskId = TASK_ID_FROM_HTML;
    const initialTaskStatus = INITIAL_TASK_STATUS;
    const isNmapTask = IS_NMAP_TASK;
    let pollIntervalId = null;

    const rawOutputTerminal = document.getElementById('rawOutputTerminal');
    const stopButtonContainer = document.getElementById('stopButtonContainer');
    const stopBtn = document.getElementById('stopBtn');
    const taskStatusBadge = document.getElementById('taskStatusBadge');
    const taskStatusText = document.getElementById('taskStatusText');
    const analysisContentDiv = document.getElementById('analysisContent');
    const analysisTabItem = document.querySelector('.tabs-nav-item[data-tab="analysisTab"]');

    // --- NEW: Helper functions to render different terminal states ---

    function renderLoadingState() {
        rawOutputTerminal.innerHTML = `
            <div class="terminal-placeholder">
                <span class="loader"></span>
            </div>`;
    }

    function renderErrorState(status) {
        rawOutputTerminal.innerHTML = `
            <div class="terminal-placeholder error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>Task ${status}. Please check logs or try again.</p>
            </div>`;
    }

    function renderStoppedState() {
        rawOutputTerminal.innerHTML = `
            <div class="terminal-placeholder stopped-state">
                <i class="fas fa-stop-circle"></i>
                <p>Task was stopped by the user.</p>
            </div>`;
    }

    function loadFullOutput() {
        if (!rawOutputTerminal) return;
        rawOutputTerminal.innerHTML = `<pre>Loading full output...</pre>`; // Temporary loading text
        // This URL was already correct, no change needed
        fetch(`/api/task/${taskId}/output`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    rawOutputTerminal.innerHTML = `<pre>${data.output}</pre>`;
                } else {
                    renderErrorState(`failed with message: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error fetching full task output:', error);
                renderErrorState('failed to load output');
            });
    }

    // Tab switching logic
    const tabItems = document.querySelectorAll('.tabs-nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    tabItems.forEach(item => {
        item.addEventListener('click', function () {
            tabItems.forEach(i => i.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            this.classList.add('active');
            document.getElementById(this.dataset.tab).classList.add('active');

            if (this.dataset.tab === 'analysisTab' && !this.dataset.loaded) {
                loadNmapAnalysis();
            }
        });
    });

    // Copy output to clipboard
    const copyBtn = document.getElementById('copyOutputBtn');
    if (copyBtn) {
        copyBtn.onclick = function () {
            // Use innerText to get text content without HTML entities for copying
            const outputText = rawOutputTerminal ? rawOutputTerminal.innerText : '';
            navigator.clipboard.writeText(outputText)
                .then(() => {
                    copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy me-1"></i>Copy Output'; }, 1200);
                })
                .catch(err => {
                    console.error('Failed to copy text: ', err);
                    copyBtn.innerHTML = '<i class="fas fa-times me-1"></i>Copy Failed';
                    setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy me-1"></i>Copy Output'; }, 1500);
                });
        };
    }

    function updateStatusDisplay(newStatus) {
        if (!taskStatusBadge || !taskStatusText) return;

        const statusLower = newStatus.toLowerCase();
        taskStatusBadge.className = 'task-status-badge status-' + statusLower;
        taskStatusText.textContent = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);

        let iconClass = 'fas fa-clock me-1'; // Default
        if (statusLower === 'running') iconClass = 'fas fa-spinner fa-spin me-1';
        else if (statusLower === 'completed') iconClass = 'fas fa-check me-1';
        else if (statusLower === 'failed' || statusLower === 'error') iconClass = 'fas fa-times me-1';
        else if (statusLower === 'stopped') iconClass = 'fas fa-stop me-1';

        const iconElement = taskStatusBadge.querySelector('i.fas');
        if (iconElement) {
            iconElement.className = iconClass;
        } else {
            const newIcon = document.createElement('i');
            newIcon.className = iconClass;
            taskStatusBadge.insertBefore(newIcon, taskStatusText);
        }
    }


    // Updated polling logic: simplified to NOT update the terminal while running
    // --- Polling logic: REWRITTEN ---
    function pollTaskStatus() {
        // UPDATED URL: Added /api prefix
        fetch(`/api/task/${taskId}/status`)
            .then(response => response.json())
            .then(data => {
                const currentStatusOnPage = taskStatusText.textContent.toLowerCase();
                const newStatusLower = data.status.toLowerCase();

                if (newStatusLower !== currentStatusOnPage) {
                    updateStatusDisplay(data.status); // Update the top status badge

                    // If the task has just finished, stop polling and render the final state
                    if (['running', 'starting'].includes(currentStatusOnPage)) {
                        clearInterval(pollIntervalId);
                        pollIntervalId = null;
                        if (stopButtonContainer) stopButtonContainer.innerHTML = ''; // Remove stop button

                        if (newStatusLower === 'completed') {
                            loadFullOutput();
                            if (isNmapTask && analysisTabItem.classList.contains('active')) {
                                loadNmapAnalysis();
                            }
                        } else if (['failed', 'error'].includes(newStatusLower)) {
                            renderErrorState(newStatusLower);
                        }
                        // The 'stopped' case is handled by handleStopTask
                    }
                }
            })
            .catch(error => {
                console.error(`Error polling task ${taskId}:`, error);
                if (pollIntervalId) clearInterval(pollIntervalId);
            });
    }

    // --- Stop task logic: REWRITTEN ---
    function handleStopTask() {
        const currentStopBtn = document.getElementById('stopBtn');
        if (!currentStopBtn) return;
        currentStopBtn.disabled = true;
        currentStopBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Stopping...';

        // UPDATED URL: Added /api prefix
        fetch(`/api/task/${taskId}/stop`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateStatusDisplay('Stopped');
                    if (stopButtonContainer) stopButtonContainer.innerHTML = '';
                    if (pollIntervalId) clearInterval(pollIntervalId);
                    renderStoppedState(); // Render the stopped message in the terminal
                } else {
                    alert(`Error stopping task: ${data.message || 'Unknown error'}`);
                    currentStopBtn.disabled = false;
                    currentStopBtn.innerHTML = '<i class="fas fa-stop me-1"></i>Stop Task';
                }
            })
            .catch(error => {
                console.error('Error stopping task:', error);
                alert('An unexpected error occurred while trying to stop the task.');
                currentStopBtn.disabled = false;
                currentStopBtn.innerHTML = '<i class="fas fa-stop me-1"></i>Stop Task';
            });
    }
    // Initial Setup
    if (stopBtn) {
        stopBtn.addEventListener('click', handleStopTask);
    }

    // --- Initial Page Load Logic ---
    if (initialTaskStatus === 'running' || initialTaskStatus === 'starting') {
        renderLoadingState();
        pollIntervalId = setInterval(pollTaskStatus, 5000);
    } else if (initialTaskStatus === 'completed') {
        loadFullOutput();
    } else if (initialTaskStatus === 'failed' || initialTaskStatus === 'error') {
        renderErrorState(initialTaskStatus);
    } else if (initialTaskStatus === 'stopped') {
        renderStoppedState();
    }

    // Load Nmap Analysis Data
    function loadNmapAnalysis() {
        if (!analysisContentDiv || !isNmapTask) return;

        const isLoaded = analysisTabItem && analysisTabItem.dataset.loaded === 'true';

        analysisContentDiv.innerHTML = '<p>Loading analysis...</p>';
        if (analysisTabItem) analysisTabItem.dataset.loaded = 'true'; // Mark as loading/loaded

        // Use the correct API endpoint, now located in the scanner blueprint
        fetch(`/api/task/${taskId}/analyze_nmap`)
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success' && result.data) {
                    renderAnalysis(result.data, analysisContentDiv, result.source, result.data.warning);
                } else {
                    let errorMsg = `<p style="color: #ef4444;">Error loading analysis: ${result.message || 'Unknown error'}</p>`;
                    if (result.data && result.data.warning) {
                        errorMsg += `<p style="color: #ffc107; font-size:0.9em;">Note: ${result.data.warning}</p>`;
                    }
                    analysisContentDiv.innerHTML = errorMsg;
                }
            })
            .catch(error => {
                console.error('Error fetching Nmap analysis:', error);
                analysisContentDiv.innerHTML = `<p style="color: #ef4444;">Could not fetch analysis data. Check console.</p>`;
            });
    }

    // --- MODIFIED FUNCTION ---
    function renderAnalysis(data, container, source, topLevelWarning) {
        let html = '';

        // Display a warning if data is from text fallback or if the parser noted a problem
        if (topLevelWarning) {
            html += `<div class="analysis-warning"><strong>Notice:</strong> ${topLevelWarning} (Parsed from: ${source || 'unknown'})</div>`;
        } else if (source) {
            html += `<div class="analysis-info">Parsed from: ${source === 'xml' ? 'XML Output' : 'Text Output'}</div>`;
        }


        if (!data.hosts || data.hosts.length === 0) {
            html += '<p>No host information found in the Nmap scan results.</p>';
            container.innerHTML = html;
            return;
        }

        const followUpActions = FOLLOW_UP_ACTIONS_FROM_HTML;

        data.hosts.forEach(hostInfo => {
            html += `<div class="analysis-host-block">`;
            html += `<h4 class="analysis-host-title">Host: ${hostInfo.host || hostInfo.ip} ${hostInfo.ip && hostInfo.host && hostInfo.ip !== hostInfo.host ? '(' + hostInfo.ip + ')' : ''} <span class="host-status status-${hostInfo.status || 'unknown'}">${hostInfo.status || ''}</span></h4>`;

            // --- NEW: Display OS and Host CPE Information ---
            if (hostInfo.osmatch && hostInfo.osmatch.length > 0) {
                html += `<div class="os-info-block"><h5>Operating System Matches:</h5><ul>`;
                hostInfo.osmatch.forEach(os => {
                    html += `<li><strong>${os.name}</strong> (Accuracy: ${os.accuracy}%)`;
                    if (os.cpe && os.cpe.length > 0) {
                        html += `<br/>CPEs: ${os.cpe.map(c => `<code>${c}</code>`).join(', ')}`;
                    }
                    html += `</li>`;
                });
                html += `</ul></div>`;
            } else if (hostInfo.host_cpes && hostInfo.host_cpes.length > 0) {
                // Fallback for CPEs found elsewhere if no specific OS match
                html += `<div class="os-info-block"><h5>Host CPEs:</h5><ul>`;
                html += `<li>${hostInfo.host_cpes.map(c => `<code>${c}</code>`).join(', ')}</li>`;
                html += `</ul></div>`;
            }

            if (!hostInfo.ports || hostInfo.ports.length === 0) {
                html += '<p class="no-open-ports">No open ports found for this host.</p>';
            } else {
                html += '<table class="analysis-table">';
                html += `<thead><tr>
                        <th>Port/Proto</th>
                        <th>Service</th>
                        <th>Product/Version</th>
                        <th>CPE</th>
                        <th>Actions</th>
                     </tr></thead><tbody>`;

                hostInfo.ports.forEach(p => {
                    // --- NEW SMARTER ROW RENDERING LOGIC ---
                    // Only render a row if it has meaningful data or actions available
                    const hasMeaningfulData = p.service || p.product || p.version || p.cpe;

                    let hasActions = false;
                    Object.values(followUpActions).forEach(actionConfig => {
                        const queryFormat = actionConfig.query_format.toLowerCase();
                        if (queryFormat.includes("{version}") && !p.version && !p.product) return;
                        if (queryFormat.includes("{service}") && !p.service) return;
                        if (queryFormat.includes("{cpe}") && !p.cpe) return;
                        hasActions = true;
                    });

                    if (hasMeaningfulData || hasActions) {
                        let productVersion = p.product || '';
                        if (p.version) {
                            productVersion += (productVersion ? ' ' : '') + `(v${p.version})`;
                        }
                        if (p.extrainfo) {
                            productVersion += (productVersion ? ' ' : '') + `(${p.extrainfo})`;
                        }

                        html += `<tr>
                                <td><code>${p.port}/${p.protocol}</code></td>
                                <td>${p.service || 'N/A'}</td>
                                <td>${productVersion || 'N/A'}</td>
                                <td>${p.cpe ? `<code>${p.cpe}</code>` : 'N/A'}</td>
                                <td class="analysis-actions">`;

                        // Logic to render follow-up buttons
                        Object.keys(followUpActions).forEach(actionId => {
                            const actionConfig = followUpActions[actionId];
                            let canRun = true;
                            const queryFormat = actionConfig.query_format.toLowerCase();

                            if (queryFormat.includes("{version}") && !p.version && !p.product) canRun = false;
                            if (queryFormat.includes("{service}") && !p.service) canRun = false;
                            if (queryFormat.includes("{cpe}") && !p.cpe) canRun = false;

                            if (canRun) {
                                html += `<button class="run-follow-up" 
                                        data-action-id="${actionId}" 
                                        data-service="${p.service || ''}" 
                                        data-version="${p.version || ''}"
                                        data-product="${p.product || ''}"
                                        data-cpe="${p.cpe || ''}"
                                        data-host-ip="${hostInfo.ip || ''}"
                                        title="Run ${actionConfig.name}">
                                    <i class="fas fa-play-circle me-1"></i> ${actionConfig.name.replace('SearchSploit ', 'SS ')}
                                    </button>`;
                            }
                        });
                        html += `</td></tr>`;
                    }
                });
                html += '</tbody></table>';
            }
            html += `</div>`;
        });
        container.innerHTML = html;

        // Re-attach event listeners
        document.querySelectorAll('.run-follow-up').forEach(button => {
            button.addEventListener('click', handleFollowUpClick);
        });
    }

    // handleFollowUpClick (function definition from previous step - unchanged)
    function handleFollowUpClick(event) {
        const button = event.currentTarget;
        const serviceInfo = {
            port: button.dataset.port,
            protocol: button.dataset.protocol,
            service: button.dataset.service,
            version: button.dataset.version,
            cpe: button.dataset.cpe,
            host_ip: button.dataset.hostIp
        };
        if (!serviceInfo.version && button.dataset.product) {
            serviceInfo.version = button.dataset.product;
        }

        const actionId = button.dataset.actionId;
        const originalNmapTarget = ORIGINAL_NMAP_TARGET_FROM_HTML;

        if (!originalNmapTarget) {
            alert('Original Nmap target (overall scan target) not found. Cannot run follow-up.');
            return;
        }

        const originalButtonHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Starting...';

        // Use the correct API endpoint, now located in the scanner blueprint
        fetch('/api/task/run_follow_up', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action_id: actionId,
                service_info: serviceInfo,
                original_nmap_target: originalNmapTarget
            })
        })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    alert(`Follow-up task started: ${result.message}\nTask ID: ${result.task_id}. You can view it in the Tasks list.`);
                } else {
                    alert(`Error: ${result.message || 'Could not start follow-up task.'}`);
                }
            })
            .catch(error => {
                console.error('Error running follow-up action:', error);
                alert('An unexpected error occurred. Check console.');
            })
            .finally(() => {
                button.disabled = false;
                button.innerHTML = originalButtonHtml;
            });
    }

    // Auto-load analysis if Nmap and tab is active on initial page load
    // (if task is already completed)
    const activeTab = document.querySelector('.tabs-nav-item.active');
    if (activeTab && activeTab.dataset.tab === 'analysisTab' && isNmapTask) {
        if (!analysisTabItem.dataset.loaded) { // Check if not already loaded by some other means
            loadNmapAnalysis();
        }
    }
});