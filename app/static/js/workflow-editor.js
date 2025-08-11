document.addEventListener('DOMContentLoaded', function () {
    const id = document.getElementById('drawflow');
    const editor = new Drawflow(id);
    editor.reroute = true;
    editor.start();

    // --- Drag and Drop Nodes ---
    let dragTimer;
    document.querySelectorAll('.palette-node').forEach(node => {
        node.addEventListener('dragstart', function (ev) {
            ev.dataTransfer.setData("node-name", ev.target.dataset.nodeName);
        });
    });

    id.addEventListener('dragover', function (ev) {
        ev.preventDefault();
    });

    id.addEventListener('drop', function (ev) {
        ev.preventDefault();
        const nodeName = ev.dataTransfer.getData("node-name");
        const toolConfig = tools[nodeName];

        if (toolConfig) {
            const nodeContent = `
                <div>
                    <strong>${toolConfig.name}</strong>
                    <textarea df-options placeholder="Enter options..."></textarea>
                </div>
            `;
            editor.addNode(nodeName, 1, 1, ev.clientX, ev.clientY, nodeName, { 'options': '' }, nodeContent);
        }
    });

    // --- Load Existing Workflow ---
    if (playbookData && playbookData.workflow_data) {
        editor.import(JSON.parse(playbookData.workflow_data));
    }

    // --- Save Workflow ---
    document.getElementById('save-button').addEventListener('click', function () {
        const workflowData = editor.export();
        const playbookId = playbookData ? playbookData.id : null;
        const name = document.getElementById('playbook-name').value;
        const description = document.getElementById('playbook-description').value;

        const url = playbookId ? `/playbooks/${playbookId}/edit` : '/playbooks/new';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description,
                workflow_data: JSON.stringify(workflowData)
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = '/playbooks';
            } else {
                alert('Error saving playbook: ' + data.message);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An unexpected error occurred. Please check the console.');
        });
    });
});
