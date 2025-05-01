// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            })
            .catch(error => {
                console.log('ServiceWorker registration failed: ', error);
            });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        updateThemeToggleButton();
    }

    // Initialize checkboxes
    initializeCheckboxes();

    // Initialize textareas
    initializeTextareas();

    // Initialize progress bars
    updateAllProgress();

    // Initialize job tracker
    initializeJobTracker();

    // Add event listeners
    addEventListeners();

    // Add animation classes
    document.querySelectorAll('section').forEach((section, index) => {
        setTimeout(() => {
            section.classList.add('fade-in');
        }, index * 100);
    });
});

// Initialize checkboxes
function initializeCheckboxes() {
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        const id = checkbox.id;
        // Load saved state
        checkbox.checked = localStorage.getItem(id) === 'true';
        // Save state on change
        checkbox.addEventListener('change', () => {
            localStorage.setItem(id, checkbox.checked);
            updateAllProgress();
        });
    });
}

// Initialize textareas
function initializeTextareas() {
    document.querySelectorAll('textarea').forEach(textarea => {
        const id = textarea.getAttribute('placeholder');
        // Load saved content
        textarea.value = localStorage.getItem(`textarea_${id}`) || '';
        // Save content on input
        textarea.addEventListener('input', () => {
            localStorage.setItem(`textarea_${id}`, textarea.value);
        });
    });
}

// Add event listeners
function addEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        // Update button text
        updateThemeToggleButton();
    }

    // Add job row button
    const addJobRowButton = document.getElementById('add-job-row');
    if (addJobRowButton) {
        addJobRowButton.addEventListener('click', addJobRow);
    }

    // Initialize delete row buttons
    initializeDeleteRowButtons();
}

// Toggle theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    updateThemeToggleButton();
}

// Update theme toggle button
function updateThemeToggleButton() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;

    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';

    if (currentTheme === 'dark') {
        themeToggle.innerHTML = '<i class="fas fa-moon"></i><i class="fas fa-sun"></i> Light Mode';
    } else {
        themeToggle.innerHTML = '<i class="fas fa-moon"></i><i class="fas fa-sun"></i> Dark Mode';
    }
}

// Week tabs functionality
function openWeek(event, weekId) {
    // Hide all week content
    document.querySelectorAll('.week-content').forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show the selected week content and mark the button as active
    document.getElementById(weekId).classList.add('active');
    event.currentTarget.classList.add('active');
}

// Goal week tabs functionality
function openGoalWeek(event, weekId) {
    // Hide all goal content
    document.querySelectorAll('.goal-content').forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all tab buttons
    document.querySelectorAll('.goal-tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show the selected goal content and mark the button as active
    document.getElementById(weekId).classList.add('active');
    event.currentTarget.classList.add('active');
}

// Update progress bars
function updateAllProgress() {
    // Technical skills progress
    updateProgressBar('skills-progress',
        document.querySelectorAll('#skills-dashboard .skills-column:first-child input[type="checkbox"]'));

    // Projects progress
    updateProgressBar('projects-progress',
        document.querySelectorAll('#skills-dashboard .skills-column:nth-child(2) input[type="checkbox"]'));

    // Job preparation progress
    updateProgressBar('job-progress',
        document.querySelectorAll('#skills-dashboard .skills-column:nth-child(3) input[type="checkbox"]'));

    // Overall progress
    updateProgressBar('',
        document.querySelectorAll('#skills-dashboard input[type="checkbox"]'));
}

// Update a specific progress bar
function updateProgressBar(id, checkboxes) {
    const total = checkboxes.length;
    let checked = 0;

    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            checked++;
        }
    });

    const percentage = total > 0 ? Math.round((checked / total) * 100) : 0;

    if (id) {
        const progressFill = document.querySelector(`#${id} .progress-fill`);
        const progressPercentage = document.querySelector(`#${id} .progress-percentage`);

        if (progressFill && progressPercentage) {
            progressFill.style.width = `${percentage}%`;
            progressPercentage.textContent = `${percentage}%`;
        }
    } else {
        // Overall progress
        const progressFill = document.querySelector('header .progress-fill');
        const progressPercentage = document.querySelector('header .progress-percentage');

        if (progressFill && progressPercentage) {
            progressFill.style.width = `${percentage}%`;
            progressPercentage.textContent = `${percentage}%`;
        }
    }
}

// Job tracker functionality
function initializeJobTracker() {
    // Load saved job applications
    const savedJobs = JSON.parse(localStorage.getItem('jobApplications')) || [];

    // Clear existing rows except the first one (template)
    const jobTable = document.getElementById('job-table');
    if (!jobTable) return;

    const tbody = jobTable.querySelector('tbody');
    while (tbody.rows.length > 1) {
        tbody.deleteRow(1);
    }

    // Add saved jobs
    savedJobs.forEach(job => {
        addJobRowWithData(job);
    });
}

// Add a new job row
function addJobRow() {
    addJobRowWithData({
        company: '',
        position: '',
        applicationDate: '',
        status: '',
        followUp: '',
        notes: ''
    });

    // Save job applications
    saveJobApplications();
}

// Add a job row with data
function addJobRowWithData(job) {
    const jobTable = document.getElementById('job-table');
    if (!jobTable) return;

    const tbody = jobTable.querySelector('tbody');
    const newRow = tbody.insertRow();

    // Add cells
    const companyCell = newRow.insertCell();
    companyCell.contentEditable = 'true';
    companyCell.textContent = job.company;

    const positionCell = newRow.insertCell();
    positionCell.contentEditable = 'true';
    positionCell.textContent = job.position;

    const applicationDateCell = newRow.insertCell();
    applicationDateCell.contentEditable = 'true';
    applicationDateCell.textContent = job.applicationDate;

    const statusCell = newRow.insertCell();
    statusCell.contentEditable = 'true';
    statusCell.textContent = job.status;

    const followUpCell = newRow.insertCell();
    followUpCell.contentEditable = 'true';
    followUpCell.textContent = job.followUp;

    const notesCell = newRow.insertCell();
    notesCell.contentEditable = 'true';
    notesCell.textContent = job.notes;

    const actionsCell = newRow.insertCell();
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-row';
    deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
    deleteButton.addEventListener('click', function() {
        tbody.removeChild(newRow);
        saveJobApplications();
    });
    actionsCell.appendChild(deleteButton);

    // Add input event listeners to save data
    [companyCell, positionCell, applicationDateCell, statusCell, followUpCell, notesCell].forEach(cell => {
        cell.addEventListener('input', saveJobApplications);
    });
}

// Initialize delete row buttons
function initializeDeleteRowButtons() {
    document.querySelectorAll('.delete-row').forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            row.parentNode.removeChild(row);
            saveJobApplications();
        });
    });
}

// Save job applications
function saveJobApplications() {
    const jobTable = document.getElementById('job-table');
    if (!jobTable) return;

    const tbody = jobTable.querySelector('tbody');
    const jobs = [];

    // Skip the first row (header)
    for (let i = 0; i < tbody.rows.length; i++) {
        const row = tbody.rows[i];

        // Skip empty rows
        if (!row.cells[0].textContent.trim() && !row.cells[1].textContent.trim()) {
            continue;
        }

        jobs.push({
            company: row.cells[0].textContent,
            position: row.cells[1].textContent,
            applicationDate: row.cells[2].textContent,
            status: row.cells[3].textContent,
            followUp: row.cells[4].textContent,
            notes: row.cells[5].textContent
        });
    }

    localStorage.setItem('jobApplications', JSON.stringify(jobs));
}

// Export data
function exportData() {
    const data = {
        checkboxes: {},
        textareas: {},
        jobApplications: JSON.parse(localStorage.getItem('jobApplications')) || [],
        theme: localStorage.getItem('theme') || 'light'
    };

    // Get all checkbox states
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        const id = checkbox.id;
        data.checkboxes[id] = checkbox.checked;
    });

    // Get all textarea content
    document.querySelectorAll('textarea').forEach(textarea => {
        const id = textarea.getAttribute('placeholder');
        data.textareas[`textarea_${id}`] = textarea.value;
    });

    // Create a download link
    const dataStr = JSON.stringify(data);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

    const exportFileDefaultName = 'ai-career-roadmap-data.json';

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

// Import data
function importData() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';

    input.onchange = e => {
        const file = e.target.files[0];

        const reader = new FileReader();
        reader.readAsText(file, 'UTF-8');

        reader.onload = readerEvent => {
            const content = readerEvent.target.result;
            try {
                const data = JSON.parse(content);

                // Import checkbox states
                if (data.checkboxes) {
                    Object.keys(data.checkboxes).forEach(id => {
                        localStorage.setItem(id, data.checkboxes[id]);
                    });
                }

                // Import textarea content
                if (data.textareas) {
                    Object.keys(data.textareas).forEach(id => {
                        localStorage.setItem(id, data.textareas[id]);
                    });
                }

                // Import job applications
                if (data.jobApplications) {
                    localStorage.setItem('jobApplications', JSON.stringify(data.jobApplications));
                }

                // Import theme
                if (data.theme) {
                    localStorage.setItem('theme', data.theme);
                }

                // Reload the page to apply changes
                window.location.reload();

            } catch (error) {
                alert('Error importing data: ' + error.message);
            }
        };
    };

    input.click();
}