document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('reportTable');

    function createTable(data) {
        const tableBody = table.querySelector('tbody');
        tableBody.innerHTML = ''; // Clear existing table content
        let number = 0; // Initialize outside the loop

        data.forEach(report => {
            const row = document.createElement('tr');

            // S.No.
            number++; // Increment for each row
            const serialNumber = document.createElement('td');
            serialNumber.textContent = number;
            row.appendChild(serialNumber);
            
            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = report.date || new Date().toLocaleDateString();
            row.appendChild(dateCell);
            
            // Report Name
            const nameCell = document.createElement('td');
            const nameSpan = document.createElement('span');
            nameSpan.className = 'report-name';
            nameSpan.textContent = report.name;
            nameSpan.title = report.name; // Add full name as title for default tooltip
            nameSpan.style.display = 'block';
            nameSpan.style.overflow = 'hidden';
            nameSpan.style.textOverflow = 'ellipsis';
            nameSpan.style.whiteSpace = 'nowrap';
            nameSpan.style.maxWidth = '200px'; // Adjust this value as needed
            nameCell.appendChild(nameSpan);
            row.appendChild(nameCell);
            
            // Status
            const statusCell = document.createElement('td');
            const statusBadge = document.createElement('span');
            statusBadge.className = `badge bg-${getStatusColor(report.status)}`;
            statusBadge.textContent = report.status;
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            const buttonGroup = document.createElement('div');
            buttonGroup.className = 'd-flex justify-content-between align-items-center';
            
            // Action buttons
            const actionButtonsGroup = document.createElement('div');
            actionButtonsGroup.className = 'btn-group';
            actionButtonsGroup.setAttribute('role', 'group');
            
            const actions = [
                { text: 'View Logs', route: 'view_logs' },
                { text: 'View Report', route: 'view_report' },
                { text: 'Edit', route: 'edit_report' }
            ];

            actions.forEach(action => {
                const link = document.createElement('a');
                link.href = `/dashboard-v2/${action.route}/${report.id}`; // Assuming your routes are in the format /<action>/<report_id>
                link.className = 'btn btn-outline-secondary btn-sm';
                link.textContent = action.text;
                actionButtonsGroup.appendChild(link);
            });
            
            buttonGroup.appendChild(actionButtonsGroup);

            // Info icon (remains the same)
            const infoIcon = document.createElement('i');
            infoIcon.className = 'bi bi-info-circle-fill ms-2';
            infoIcon.style.fontSize = '1em';
            infoIcon.style.cursor = 'pointer';
            infoIcon.setAttribute('data-bs-toggle', 'tooltip');
            infoIcon.setAttribute('data-bs-placement', 'top');
            infoIcon.setAttribute('title', `Report ID: ${report.id}`);
            buttonGroup.appendChild(infoIcon);

            // Delete (bin) icon
            const deleteIcon = document.createElement('i');
            deleteIcon.className = 'bi bi-trash ms-2';
            deleteIcon.style.fontSize = '1em';
            deleteIcon.style.cursor = 'pointer';
            //deleteIcon.style.color = 'red';
            deleteIcon.setAttribute('data-bs-toggle', 'tooltip');
            deleteIcon.setAttribute('data-bs-placement', 'top');
            deleteIcon.setAttribute('title', 'Delete Report');
            deleteIcon.addEventListener('click', () => deleteReport(report.id, row));
            buttonGroup.appendChild(deleteIcon);

            actionsCell.appendChild(buttonGroup);
            row.appendChild(actionsCell);
            
            tableBody.appendChild(row);
        });

        // Initialize tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    function deleteReport(reportId, rowElement) {
        if (confirm('Are you sure you want to delete this report?')) {
            fetch(`/dashboard-v2/delete_report/${reportId}`, {
                method: 'DELETE',
            })
            .then(response => {
                if (response.ok) {
                    rowElement.remove();
                    // Optionally, you can add a success message here
                } else {
                    throw new Error('Failed to delete report');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to delete report. Please try again.');
            });
        }
    }
    
    function getStatusColor(status) {
        switch (status.toLowerCase()) {
            case 'success': return 'success';
            case 'processing': return 'warning text-dark';
            case 'failed': return 'danger';
            default: return 'secondary';
        }
    }

    // Fetch data from Flask route and create table
    if (typeof REPORTS_URL !== 'undefined') {
        fetch(REPORTS_URL)
            .then(response => response.json())
            .then(data => createTable(data))
            .catch(error => console.error('Error fetching report data:', error));
    } else {
        console.error('REPORTS_URL is not defined');
    }
});