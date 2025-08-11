// Home page functionality for S2E Dashboard
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize the home page
    initHomePage();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadDashboardData();
    
    function initHomePage() {
        // Add loading states
        showLoadingStates();
        
        // Initialize animations
        initAnimations();
    }
    
    function setupEventListeners() {
        // New project buttons
        const newProjectHeroBtn = document.getElementById('new-project-hero-btn');
        const emptyStateCreateBtn = document.getElementById('empty-state-create-btn');
        const newProjectFabMain = document.getElementById('new-project-fab-main');
        
        if (newProjectHeroBtn) {
            newProjectHeroBtn.addEventListener('click', openNewProjectModal);
        }
        
        if (emptyStateCreateBtn) {
            emptyStateCreateBtn.addEventListener('click', openNewProjectModal);
        }
        
        if (newProjectFabMain) {
            newProjectFabMain.addEventListener('click', openNewProjectModal);
        }
        
        // Quick scan button
        const quickScanBtn = document.getElementById('quick-scan-btn');
        if (quickScanBtn) {
            quickScanBtn.addEventListener('click', handleQuickScan);
        }
        
        // Search functionality
        const searchInput = document.getElementById('project-search');
        if (searchInput) {
            searchInput.addEventListener('input', handleProjectSearch);
        }
    }
    
    function loadDashboardData() {
        // Load projects
        loadProjects();
        
        // Load dashboard stats
        loadDashboardStats();
        
        // Load recent activity
        loadRecentActivity();
    }
    
    function loadProjects() {
        fetch('/api/projects')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    renderProjects(data.projects || []);
                } else {
                    console.error('Failed to load projects:', data.message);
                    showEmptyProjectsState();
                }
            })
            .catch(error => {
                console.error('Error loading projects:', error);
                showEmptyProjectsState();
            });
    }
    
    function renderProjects(projects) {
        const projectsGrid = document.getElementById('projects-grid');
        const emptyState = document.getElementById('empty-projects');
        
        if (!projectsGrid) return;
        
        if (projects.length === 0) {
            showEmptyProjectsState();
            return;
        }
        
        // Hide empty state
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        
        // Clear existing content
        projectsGrid.innerHTML = '';
        
        // Render each project
        projects.forEach(project => {
            const projectCard = createProjectCard(project);
            projectsGrid.appendChild(projectCard);
        });
        
        // Add fade-in animation
        const cards = projectsGrid.querySelectorAll('.project-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
            card.classList.add('fade-in-up');
        });
    }
    
    function createProjectCard(project) {
        const card = document.createElement('div');
        card.className = 'project-card';
        card.setAttribute('data-project-id', project.id);
        
        const lastScanDate = project.last_scan ? new Date(project.last_scan).toLocaleDateString() : 'Never';
        const targetCount = project.targets ? project.targets.length : 0;
        const taskCount = project.tasks ? project.tasks.length : 0;
        
        card.innerHTML = `
            <div class="project-header">
                <h3 class="project-name">${escapeHtml(project.name)}</h3>
                <div class="project-status ${getProjectStatusClass(project)}">
                    ${getProjectStatusText(project)}
                </div>
            </div>
            
            <div class="project-stats">
                <div class="stat">
                    <span class="stat-label">Targets</span>
                    <span class="stat-value">${targetCount}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Tasks</span>
                    <span class="stat-value">${taskCount}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Last Scan</span>
                    <span class="stat-value">${lastScanDate}</span>
                </div>
            </div>
            
            <div class="project-actions">
                <button class="btn btn-sm btn-primary" onclick="openProject('${project.id}')">
                    <i class="fas fa-external-link-alt"></i>
                    Open
                </button>
                <button class="btn btn-sm btn-secondary" onclick="editProject('${project.id}')">
                    <i class="fas fa-edit"></i>
                    Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteProject('${project.id}')">
                    <i class="fas fa-trash"></i>
                    Delete
                </button>
            </div>
        `;
        
        return card;
    }
    
    function loadDashboardStats() {
        // Load total projects
        fetch('/api/projects')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const totalProjects = data.projects ? data.projects.length : 0;
                    updateStat('total-projects', totalProjects);
                }
            })
            .catch(error => console.error('Error loading project stats:', error));
        
        // Load total targets
        fetch('/api/targets')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const totalTargets = data.targets ? data.targets.length : 0;
                    updateStat('total-targets', totalTargets);
                }
            })
            .catch(error => console.error('Error loading target stats:', error));
        
        // Load total tasks
        fetch('/api/tasks')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const totalTasks = data.tasks ? data.tasks.length : 0;
                    updateStat('total-tasks', totalTasks);
                }
            })
            .catch(error => console.error('Error loading task stats:', error));
        
        // Load completed scans (placeholder - adjust based on your API)
        updateStat('completed-scans', 0);
    }
    
    function loadRecentActivity() {
        // Load recent tasks/activity
        fetch('/api/tasks?limit=5')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    renderRecentActivity(data.tasks || []);
                } else {
                    renderRecentActivity([]);
                }
            })
            .catch(error => {
                console.error('Error loading recent activity:', error);
                renderRecentActivity([]);
            });
    }
    
    function renderRecentActivity(activities) {
        const activityList = document.getElementById('recent-activity-list');
        if (!activityList) return;
        
        if (activities.length === 0) {
            activityList.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">No recent activity</div>
                        <div class="activity-time">Get started by creating a project</div>
                    </div>
                    <div class="activity-status info">None</div>
                </div>
            `;
            return;
        }
        
        // Clear existing content
        activityList.innerHTML = '';
        
        // Render each activity
        activities.forEach(activity => {
            const activityItem = createActivityItem(activity);
            activityList.appendChild(activityItem);
        });
    }
    
    function createActivityItem(activity) {
        const item = document.createElement('div');
        item.className = 'activity-item';
        
        const status = getTaskStatus(activity.status);
        const timeAgo = getTimeAgo(activity.created_at || activity.updated_at);
        
        item.innerHTML = `
            <div class="activity-icon">
                <i class="fas ${getActivityIcon(activity.type)}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${escapeHtml(activity.name || 'Task')}</div>
                <div class="activity-time">${timeAgo}</div>
            </div>
            <div class="activity-status ${status.class}">${status.text}</div>
        `;
        
        return item;
    }
    
    function showEmptyProjectsState() {
        const projectsGrid = document.getElementById('projects-grid');
        const emptyState = document.getElementById('empty-projects');
        
        if (projectsGrid) projectsGrid.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
    }
    
    function showLoadingStates() {
        // Show loading state for stats
        ['total-projects', 'total-targets', 'total-tasks', 'completed-scans'].forEach(id => {
            updateStat(id, '-');
        });
    }
    
    function updateStat(statId, value) {
        const statElement = document.getElementById(statId);
        if (statElement) {
            statElement.textContent = value;
        }
    }
    
    function initAnimations() {
        // Add stagger animation to stats
        const statCards = document.querySelectorAll('.stat-card');
        statCards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
        });
        
        // Add fade-in animation to sections
        const sections = document.querySelectorAll('section');
        sections.forEach((section, index) => {
            section.style.animationDelay = `${index * 0.2}s`;
        });
    }
    
    // Utility functions
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function getProjectStatusClass(project) {
        if (project.status === 'active') return 'active';
        if (project.status === 'paused') return 'paused';
        if (project.status === 'completed') return 'completed';
        return 'inactive';
    }
    
    function getProjectStatusText(project) {
        if (project.status === 'active') return 'Active';
        if (project.status === 'paused') return 'Paused';
        if (project.status === 'completed') return 'Completed';
        return 'Inactive';
    }
    
    function getTaskStatus(status) {
        const statusMap = {
            'running': { class: 'running', text: 'Running' },
            'completed': { class: 'completed', text: 'Completed' },
            'failed': { class: 'failed', text: 'Failed' },
            'pending': { class: 'pending', text: 'Pending' },
            'cancelled': { class: 'cancelled', text: 'Cancelled' }
        };
        return statusMap[status] || { class: 'pending', text: 'Unknown' };
    }
    
    function getActivityIcon(type) {
        const iconMap = {
            'scan': 'fa-search',
            'nmap': 'fa-network-wired',
            'task': 'fa-tasks',
            'project': 'fa-folder',
            'target': 'fa-crosshairs'
        };
        return iconMap[type] || 'fa-info-circle';
    }
    
    function getTimeAgo(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }
    
    // Event handlers
    function openNewProjectModal() {
        // Trigger the existing modal functionality
        const event = new Event('click');
        document.getElementById('new-project-sidebar-btn').dispatchEvent(event);
    }
    
    function handleQuickScan() {
        // Implement quick scan functionality
        alert('Quick scan functionality coming soon!');
    }
    
    function handleProjectSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const projectCards = document.querySelectorAll('.project-card');
        
        projectCards.forEach(card => {
            const projectName = card.querySelector('.project-name').textContent.toLowerCase();
            if (projectName.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    // Global functions for project actions
    window.openProject = function(projectId) {
        window.location.href = `/projects/${projectId}`;
    };
    
    window.editProject = function(projectId) {
        window.location.href = `/projects/${projectId}/edit`;
    };
    
    window.deleteProject = function(projectId) {
        if (confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
            fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Reload projects
                    loadProjects();
                    // Reload stats
                    loadDashboardStats();
                } else {
                    alert('Error deleting project: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error deleting project:', error);
                alert('Error deleting project. Please try again.');
            });
        }
    };
    
    // Refresh functionality for the existing s2e object
    if (window.s2e && window.s2e.refreshProjectUI) {
        // Override the existing refresh function to work with new UI
        const originalRefresh = window.s2e.refreshProjectUI;
        window.s2e.refreshProjectUI = function() {
            loadDashboardData();
            if (originalRefresh) {
                originalRefresh();
            }
        };
    }
});
