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
        const emptyStateCreateBtn = document.getElementById('empty-projects') ? document.getElementById('empty-state-create-btn') : null;
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
        fetch(`/api/projects?_=${Date.now()}`, { cache: 'no-store' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const projects = data.projects || [];
                    renderProjects(projects);
                    updateHomeHeroUI(projects.length > 0);
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
        fetch(`/api/projects?_=${Date.now()}`, { cache: 'no-store' })
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
        
        // Ensure hero shows welcome/create when no projects
        updateHomeHeroUI(false);
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
            fetch(`/api/projects/${projectId}?_=${Date.now()}`, {
                method: 'DELETE',
                cache: 'no-store'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Reload projects on Home
                    loadProjects();
                    // Reload stats
                    loadDashboardStats();
                    // Always refresh sidebar across the app
                    if (window.s2e && typeof window.s2e.refreshProjectUI === 'function') {
                        window.s2e.refreshProjectUI();
                    }
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
    
    // Provide lowercase aliases to avoid casing errors from inline handlers
    // e.g., openproject(int) or editproject(int)
    window.openproject = window.openProject;
    window.editproject = window.editProject;
    window.deleteproject = window.deleteProject;
    
    // Define a render hook so global refresh updates the Home project grid too
    if (window.s2e) {
        window.s2e.renderProjectGrid = function(allProjects) {
            try {
                renderProjects(allProjects || []);
                updateHomeHeroUI(Array.isArray(allProjects) && allProjects.length > 0);
            } catch (e) {
                console.error('Error rendering project grid from global refresh:', e);
            }
        };
    }
    
    // Refresh functionality for the existing s2e object
    if (window.s2e && window.s2e.refreshProjectUI) {
        // Override the existing refresh function to work with new UI
        const originalRefresh = window.s2e.refreshProjectUI;
        window.s2e.refreshProjectUI = function() {
            // Keep Home dashboard sections in sync
            loadDashboardData();
            // Call original refresh to update sidebar and invoke renderProjectGrid
            if (originalRefresh) {
                return originalRefresh();
            }
        };
    }

    // Toggle hero UI based on whether projects exist
    function updateHomeHeroUI(hasProjects) {
        const heroSection = document.querySelector('.hero-section');
        const title = heroSection ? heroSection.querySelector('h1') : null;
        const subtitle = heroSection ? heroSection.querySelector('p') : null;
        const heroActions = heroSection ? heroSection.querySelector('.hero-actions') : null;
        const existingScanBtn = document.getElementById('quick-scan-btn');
        const createBtn = document.getElementById('new-project-hero-btn');

        if (!heroSection) return;

        if (hasProjects) {
            // Hide welcome messaging
            if (title) title.style.display = 'none';
            if (subtitle) subtitle.style.display = 'none';

            // Replace the create button with a scan button
            if (createBtn) {
                const scanBtn = createBtn.cloneNode(true);
                scanBtn.id = 'quick-scan-btn';
                scanBtn.innerHTML = '<i class="fas fa-search"></i> Quick Scan';
                // Remove any previous listeners by replacing node
                createBtn.parentNode.replaceChild(scanBtn, createBtn);
                scanBtn.addEventListener('click', handleQuickScan);
            } else if (!existingScanBtn && heroActions) {
                // Ensure a scan button exists if the create button isn't present
                const scanBtn = document.createElement('a');
                scanBtn.className = 'btn btn-secondary btn-lg';
                scanBtn.id = 'quick-scan-btn';
                scanBtn.innerHTML = '<i class="fas fa-search"></i> Quick Scan';
                scanBtn.href = '#';
                scanBtn.addEventListener('click', (e) => { e.preventDefault(); handleQuickScan(); });
                heroActions.prepend(scanBtn);
            }
        } else {
            // Show welcome messaging and ensure create button exists
            if (title) title.style.display = '';
            if (subtitle) subtitle.style.display = '';
            
            // If the hero button was converted to scan, convert it back to create
            const scanBtnNow = document.getElementById('quick-scan-btn');
            if (scanBtnNow) {
                const createBtnNew = scanBtnNow.cloneNode(true);
                createBtnNew.id = 'new-project-hero-btn';
                createBtnNew.className = 'btn btn-primary btn-lg';
                createBtnNew.innerHTML = '<i class="fas fa-plus"></i> Create New Project';
                scanBtnNow.parentNode.replaceChild(createBtnNew, scanBtnNow);
                createBtnNew.addEventListener('click', openNewProjectModal);
            }
        }
    }
});
