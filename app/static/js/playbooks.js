document.addEventListener('DOMContentLoaded', function () {
    const policyTable = document.querySelector('.policy-table');

    if (policyTable) {
        policyTable.addEventListener('click', function (event) {
            const target = event.target;

            if (target.classList.contains('run-btn')) {
                // Handle run action
                console.log('Run button clicked');
            }

            if (target.classList.contains('edit-btn')) {
                // Handle edit action
                console.log('Edit button clicked');
            }
        });
    }
});
