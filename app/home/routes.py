# /S2E/app/home/routes.py
from flask import Blueprint, render_template, redirect, url_for, session, current_app
from app.auth.routes import login_required
from app.models import User, Project, Task, Target, Playbook

home_bp = Blueprint('home', __name__, template_folder='../templates')

@home_bp.route('/')
# @home_bp.route('/home')
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
    }
    
    all_playbooks = Playbook.query.all()
    dashboard_data["all_playbooks"] = [playbook.to_dict() for playbook in all_playbooks]
        
    return render_template('home.html', data=dashboard_data)
