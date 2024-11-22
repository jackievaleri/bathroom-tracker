/**
 * scripts.js
 * Contains shared JavaScript functionality for the "Potty Like a Rockstar" app.
 */

/* Update Student Status (Home Page) */
function updateStatus() {
    const container = document.getElementById('buttons-container');
    if (!container) return; // Exit if container doesn't exist (e.g., on login page)

    container.innerHTML = ''; // Clear existing buttons

    students.forEach(name => {
        const button = document.createElement('button');
        button.textContent = name;
        button.className = 'student-button'; // Add class for styling

        button.onclick = () => toggleStudentStatus(name);
        container.appendChild(button);
    });
}

/* Toggle Individual Student Status */
function toggleStudentStatus(name) {
    fetch('/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    }).then(response => response.json()).then(data => {
        alert(data.message);
        updateStatus();
    });
}

/* Mark All Students as "In" */
function markAllIn() {
    fetch('/mark_all_in', { method: 'POST' }).then(response => response.json()).then(data => {
        alert(data.message);
        updateStatus();
    });
}

/* Export All Logs */
function exportAll() {
    window.location.href = '/export_all';
}

/* Export Today's Logs */
function exportToday() {
    window.location.href = '/export_today';
}

/* Clear All Logs */
function clearLogs() {
    if (confirm('Are you sure you want to clear all logs?')) {
        fetch('/clear_logs', { method: 'POST' }).then(response => response.json()).then(data => {
            alert(data.message);
            updateStatus();
        });
    }
}

/* Upload Student List */
function uploadStudents() {
    const fileInput = document.getElementById('upload-file');
    if (!fileInput.files.length) {
        alert("Please select a file to upload.");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload_students', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') {
                window.location.reload();
            }
        })
        .catch(error => {
            console.error("Upload Error:", error);
            alert("Failed to upload the student list.");
        });
}

/* Initialize Page */
document.addEventListener("DOMContentLoaded", () => {
    updateStatus();
});
