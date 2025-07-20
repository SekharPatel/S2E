# /S2E/app/home/routes.py
from flask import Blueprint, render_template, session, current_app
from app.auth.routes import login_required
from app.models import User, Project, Playbook

home_bp = Blueprint('home', __name__, template_folder='../templates')

def get_base_data():
    """Gets the data required by the base template (e.g., for the sidebar)."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    all_projects = user.projects.order_by(Project.created_at.desc()).all()
    active_project_id = session.get('active_project_id')
    
    # Ensure an active project is always set if projects exist
    if not active_project_id and all_projects:
        active_project_id = all_projects[0].id
        session['active_project_id'] = active_project_id
        
    return {
        "all_projects": all_projects,
        "active_project_id": active_project_id
    }

@home_bp.route('/')
@login_required
def home():
    """Shows the main project dashboard."""
    base_data = get_base_data()
    active_project = Project.query.get(base_data['active_project_id']) if base_data['active_project_id'] else None
    
    all_playbooks = Playbook.query.all()
    playbooks_for_modal = [p.to_dict() for p in all_playbooks]
    
    # FIX: Pass data to the template in a single dictionary named 'data'
    data_for_template = {
        'base_data': base_data,
        'active_project': active_project,
        'all_projects': base_data.get('all_projects', []),
        'all_playbooks': playbooks_for_modal
    }
        
    return render_template('home.html', data=data_for_template)