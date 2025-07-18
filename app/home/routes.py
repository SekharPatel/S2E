# /S2E/app/home/routes.py
from flask import Blueprint, render_template, redirect, url_for, session, current_app
import json
import os

from app.auth.routes import login_required
from app.models import User, Project, Task, Target, Playbook

# Define the blueprint for this feature
home_bp = Blueprint('home', __name__, template_folder='../templates')

@home_bp.route('/')
@home_bp.route('/home')
@login_required
def home():
    """Shows the main project dashboard."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    
    active_project_id = session.get('active_project_id')
    user_projects = user.projects.order_by(Project.created_at.desc()).all()
    
    if not active_project_id and user_projects:
        active_project_id = user_projects[0].id
        session['active_project_id'] = active_project_id
        
    active_project = Project.query.get(active_project_id) if active_project_id else None
    
    dashboard_data = {
        "all_projects": user_projects,
        "active_project": active_project,
        "targets": [],
        "recent_tasks": [],
        "stats": {"targets": 0, "tasks": 0, "findings": 0}
    }
    
    if active_project:
        dashboard_data["targets"] = active_project.targets.all()
        # Ensure we get the correct tool name by checking if the tool_id exists in the config
        recent_tasks = active_project.tasks.order_by(Task.start_time.desc()).limit(5).all()
        dashboard_data["recent_tasks"] = [task for task in recent_tasks if task.tool_id in current_app.config.get("TOOLS", {})]
        
        dashboard_data["stats"]["targets"] = active_project.targets.count()
        dashboard_data["stats"]["tasks"] = active_project.tasks.count()

    dashboard_data["tools"] = current_app.config.get("TOOLS", {})
    
    # Get all available playbooks for the project creation/edit modals
    all_playbooks = Playbook.query.all()
    dashboard_data["all_playbooks"] = [playbook.to_dict() for playbook in all_playbooks]
    
    # Get only the linked playbooks for the active project dashboard
    if active_project:
        dashboard_data["linked_playbooks"] = [playbook.to_dict() for playbook in active_project.linked_playbooks]
    else:
        dashboard_data["linked_playbooks"] = []
        
    return render_template('home.html', data=dashboard_data)
