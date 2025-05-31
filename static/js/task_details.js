document.addEventListener('DOMContentLoaded', function () {
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
                this.dataset.loaded = true; // Mark as loaded to prevent multiple fetches
            }
        });
    });

    // Copy output to clipboard
    const copyBtn = document.getElementById('copyOutputBtn');
    if (copyBtn) {
        copyBtn.onclick = function () {
            const outputText = document.querySelector('.task-details-terminal').innerText;
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

    // Load Nmap Analysis Data
    function loadNmapAnalysis() {
        const analysisContentDiv = document.getElementById('analysisContent');
        if (!analysisContentDiv) return;

        const taskId = "{{ task_id }}"; // Get task_id from Jinja context
        fetch(`/task/${taskId}/analyze_nmap`)
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success' && result.data) {
                    renderAnalysis(result.data, analysisContentDiv);
                } else {
                    analysisContentDiv.innerHTML = `<p style="color: #ef4444;">Error loading analysis: ${result.message || 'Unknown error'}</p>`;
                }
            })
            .catch(error => {
                console.error('Error fetching Nmap analysis:', error);
                analysisContentDiv.innerHTML = `<p style="color: #ef4444;">Could not fetch analysis data. Check console.</p>`;
            });
    }

    // Render Parsed Nmap Data
    function renderAnalysis(data, container) {
        if (!data.hosts || data.hosts.length === 0) {
            container.innerHTML = '<p>No open ports or host information found in the Nmap scan.</p>';
            return;
        }

        let html = '';
        const followUpActions = JSON.parse('{{ follow_up_actions | tojson | safe }}');
        const originalNmapTarget = "{{ task.original_target or '' }}";


        data.hosts.forEach(hostInfo => {
            html += `<div class="analysis-host-block">`;
            html += `<h4 class="analysis-host-title">Host: ${hostInfo.host} ${hostInfo.ip && hostInfo.ip !== hostInfo.host ? '(' + hostInfo.ip + ')' : ''}</h4>`;

            if (!hostInfo.ports || hostInfo.ports.length === 0) {
                html += '<p>No open ports found for this host.</p>';
            } else {
                html += '<table class="analysis-table">';
                html += `<thead><tr>
                            <th>Port/Proto</th>
                            <th>Service</th>
                            <th>Version</th>
                            <th>Actions</th>
                         </tr></thead><tbody>`;
                hostInfo.ports.forEach(p => {
                    html += `<tr>
                                <td><code>${p.port}/${p.protocol}</code></td>
                                <td>${p.service || 'N/A'}</td>
                                <td>${p.version || 'N/A'}</td>
                                <td class="analysis-actions">`;

                    Object.keys(followUpActions).forEach(actionId => {
                        const actionConfig = followUpActions[actionId];
                        // Check if all required placeholders for this action can be filled
                        let canRun = true;
                        if (actionConfig.query_format.includes("{version}") && !p.version) {
                            canRun = false;
                        }
                        if (actionConfig.query_format.includes("{service}") && !p.service) {
                            canRun = false;
                        }
                        // Add more checks if needed for other placeholders

                        if (canRun) {
                            html += `<button class="run-follow-up" 
                                        data-action-id="${actionId}" 
                                        data-port="${p.port}" 
                                        data-protocol="${p.protocol}" 
                                        data-service="${p.service || ''}" 
                                        data-version="${p.version || ''}"
                                        title="Run ${actionConfig.name} for ${p.service} ${p.version || ''}">
                                     <i class="fas fa-play-circle me-1"></i> ${actionConfig.name}
                                     </button>`;
                        }
                    });
                    html += `</td></tr>`;
                });
                html += '</tbody></table>';
            }
            html += `</div>`; // end analysis-host-block
        });
        container.innerHTML = html;

        // Add event listeners to newly created follow-up buttons
        document.querySelectorAll('.run-follow-up').forEach(button => {
            button.addEventListener('click', handleFollowUpClick);
        });
    }

    function handleFollowUpClick(event) {
        const button = event.currentTarget;
        const serviceInfo = {
            port: button.dataset.port,
            protocol: button.dataset.protocol,
            service: button.dataset.service,
            version: button.dataset.version
        };
        const actionId = button.dataset.actionId;
        const originalNmapTarget = "{{ task.original_target or '' }}"; // Get from Jinja

        if (!originalNmapTarget && (actionId.includes('nmap') || actionId.includes('target_host'))) {
            alert('Original Nmap target not found for this task. Cannot run host-specific follow-up.');
            return;
        }

        const originalButtonHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Starting...';

        fetch('/task/run_follow_up', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add CSRF token header if you implement CSRF protection globally
            },
            body: JSON.stringify({
                action_id: actionId,
                service_info: serviceInfo,
                original_nmap_target: originalNmapTarget
            })
        })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    alert(`Follow-up task started: ${result.message}\nTask ID: ${result.task_id}`);
                    // Optionally redirect or update UI further
                    // window.location.href = `/task/${result.task_id}`; // Example: redirect to new task
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

    // If analysis tab is present and should be shown, trigger load if it's the active one
    // (though unlikely on initial load unless you change default active tab)
    const activeTab = document.querySelector('.tabs-nav-item.active');
    if (activeTab && activeTab.dataset.tab === 'analysisTab' && !activeTab.dataset.loaded) {
        loadNmapAnalysis();
        activeTab.dataset.loaded = true;
    }

});