document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('reportTable');
    let reportRows = new Map(); // To store references to report rows

    function createTable(data) {
        const tableBody = table.querySelector('tbody');
        tableBody.innerHTML = ''; // Clear existing table content
        let number = (currentPage - 1) * reportsPerPage; // Initialize outside the loop

        data.forEach(report => {
            const row = document.createElement('tr');
            // Add both IDs to the row
            row.id = `report-row-${report.id}`;
            row.dataset.taskId = report.task_id;

            // Store reference to the row using both IDs
            reportRows.set(report.id, row);
            reportRows.set(report.task_id, row);

            // S.No.
            number++;
            const serialNumber = document.createElement('td');
            serialNumber.textContent = number;
            row.appendChild(serialNumber);
            
            // Date (using Moment.js)
            const dateCell = document.createElement('td');
            const dateSpan = document.createElement('span');
            dateSpan.textContent = moment(report.date).format('DD-MM-YYYY HH:mm')
            dateCell.appendChild(dateSpan);
            row.appendChild(dateCell);
            
            // Report Name
            const nameCell = document.createElement('td');
            const nameSpan = document.createElement('span');
            nameSpan.className = 'report-name';
            nameSpan.textContent = report.name;
            nameSpan.title = report.name;
            nameSpan.style.cssText = 'display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px;';
            nameCell.appendChild(nameSpan);
            row.appendChild(nameCell);
            
            // Status
            const statusCell = document.createElement('td');
            statusCell.className = 'status-cell';
            updateStatusCell(statusCell, report.status);
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
                { text: 'Chat', route: 'chat_report' }
            ];

            actions.forEach(action => {
                const link = document.createElement('a');
                let url;
                switch (action.route) {
                    case 'view_report':
                        url = VIEW_REPORT_URL;
                        if (statusCell.textContent.trim().toUpperCase() !== 'SUCCESS') {
                            link.setAttribute('data-bs-toggle', 'modal');
                            link.setAttribute('data-bs-target', '#processingModal');
                            link.href = '#';
                        } else {
                            link.href = url.replace('_REPORT_ID_', report.id);
                        }
                        break;
                    case 'view_logs':
                        url = VIEW_LOGS_URL;
                        link.href = url.replace('_REPORT_ID_', report.id);
                        break;
                    case 'chat_report':
                        url = CHAT_REPORT_URL;
                        link.href = url.replace('_REPORT_ID_', report.id);
                        if (statusCell.textContent.trim().toUpperCase() !== 'SUCCESS') {
                            link.setAttribute('data-bs-toggle', 'modal');
                            link.setAttribute('data-bs-target', '#processingModal');
                            link.href = '#';
                        } else {
                            link.href = url.replace('_REPORT_ID_', report.id);
                        }
                        break;
                    default:
                        console.warn(`Undefined route: ${action.route}`);
                        link.href = '#';
                        break;
                }
                link.className = 'btn btn-outline-secondary btn-sm';
                link.textContent = action.text;
                actionButtonsGroup.appendChild(link);
            });
            
            buttonGroup.appendChild(actionButtonsGroup);

            // Info icon
            const infoIcon = document.createElement('i');
            infoIcon.className = 'bi bi-info-circle-fill ms-2';
            infoIcon.style.cssText = 'font-size: 1em; cursor: pointer;';
            infoIcon.setAttribute('data-bs-toggle', 'tooltip');
            infoIcon.setAttribute('data-bs-placement', 'top');
            infoIcon.setAttribute('title', `Report ID: ${report.id}`);
            buttonGroup.appendChild(infoIcon);

            // Delete icon
            const deleteIcon = document.createElement('i');
            deleteIcon.className = 'bi bi-trash ms-2';
            deleteIcon.style.cssText = 'font-size: 1em; cursor: pointer;';
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

    function updateStatusCell(cell, status) {
        const statusInfo = getStatusInfo(status);
        cell.innerHTML = ''; // Clear existing content
        const statusBadge = document.createElement('span');
        statusBadge.className = `badge bg-${statusInfo.color}`;
        statusBadge.textContent = statusInfo.text;
        cell.appendChild(statusBadge);
    }

    function deleteReport(reportId, rowElement) {
        if (confirm('Are you sure you want to delete this report?')) {
            fetch(`/dashboardv2/delete_report/${reportId}`, {
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
    
    function getStatusInfo(status) {
        switch (status.toUpperCase()) {
            case 'STARTED':
                return { color: 'warning text-dark', text: 'Processing' };
            case 'SUCCESS':
                return { color: 'success', text: 'Success' };
            case 'FAILURE':
                return { color: 'danger', text: 'Failed' };
            default:
                return { color: 'secondary', text: 'Submitted' };
        }
    }

    // Fetch data from Flask route and create table
    if (typeof REPORTS_URL !== 'undefined') {
        fetch(`${REPORTS_URL}?page=${currentPage}`)
            .then(response => response.json())
            .then(data => createTable(data))
            .catch(error => console.error('Error fetching report data:', error));
    } else {
        console.error('REPORTS_URL is not defined');
    }
    
    function updateActionButtons(row, status) {
        const reportId = row.id.replace('report-row-', ''); // Get the report ID from the row ID
        const actionButtons = row.querySelectorAll('.btn-group a');
        const viewReportLink = actionButtons[1];  // Second button is View Report
        const chatReportLink = actionButtons[2];  // Third button is Chat
        
        if (status.toUpperCase() === 'SUCCESS') {
            if (viewReportLink) {
                viewReportLink.removeAttribute('data-bs-toggle');
                viewReportLink.removeAttribute('data-bs-target');
                viewReportLink.href = VIEW_REPORT_URL.replace('_REPORT_ID_', reportId);
            }
            if (chatReportLink) {
                chatReportLink.removeAttribute('data-bs-toggle');
                chatReportLink.removeAttribute('data-bs-target');
                chatReportLink.href = CHAT_REPORT_URL.replace('_REPORT_ID_', reportId);
            }
        } else {
            if (viewReportLink) {
                viewReportLink.setAttribute('data-bs-toggle', 'modal');
                viewReportLink.setAttribute('data-bs-target', '#processingModal');
                viewReportLink.href = '#';
            }
            if (chatReportLink) {
                chatReportLink.setAttribute('data-bs-toggle', 'modal');
                chatReportLink.setAttribute('data-bs-target', '#processingModal');
                chatReportLink.href = '#';
            }
        }
    }


    // SSE implementation with user-specific channel
    if (typeof CHANNEL_ID !== 'undefined') {
        // Create an EventSource for the user-specific channel
        //var source = new EventSource(`/stream?channel=${encodeURIComponent(CHANNEL_ID)}`);
        var source = new EventSource(`${SSE_URL}?channel=${encodeURIComponent(CHANNEL_ID)}`);

        console.log('EventSource created:', source);
        
        source.onopen = function(event) {
            console.log('EventSource connection opened:', event);
        };
        
        source.addEventListener('status_update', function(event) {
            console.log('Status update event received:', event);
            var data = JSON.parse(event.data);
            console.log('SSE update received:', data);
            
            // Find the row using task_id
            const row = reportRows.get(data.task_id);

            if (row) {
                const statusCell = row.querySelector('.status-cell');
                if (statusCell) {
                    updateStatusCell(statusCell, data.status);
                    updateActionButtons(row, data.status);
                }
            } else {
                console.warn(`No row found for report with task_id: ${data.task_id}`);
            }
        }, false);

        source.onerror = function(e) {
            console.error('SSE error:', e);
            source.close();
            setTimeout(function() {
                source = new EventSource(`${SSE_URL}?channel=${encodeURIComponent(CHANNEL_ID)}`);
            }, 5000);  // Try to reconnect after 5 seconds
        };
    } else {
        console.error('Channel is not defined');
    }
});