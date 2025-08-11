# /S2E/app/projects/routes.py

from flask import Blueprint, request, jsonify, session, url_for
from app import db
from app.models import User, Project, Target
from app.auth.routes import login_required
from app.utils.validation import sanitize_project_name, ValidationError

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/api/projects_data')
@login_required
def get_projects_details():
    """API endpoint to fetch full project data for the main grid and sidebar."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    all_projects = user.projects.order_by(Project.created_at.desc()).all()
    active_project_id = session.get('active_project_id')
    
    projects_list = []
    for p in all_projects:
        projects_list.append({
            'id': p.id,
            'name': p.name,
            'targets_count': p.targets.count(),
            'tasks_count': p.tasks.count()
        })
    
    return jsonify({
        'all_projects': projects_list,
        'active_project_id': active_project_id
    })

@projects_bp.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    data = request.get_json()
    project_name = data.get('name')

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    try:
        project_name = sanitize_project_name(project_name)
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

    user = User.query.filter_by(username=session['username']).first_or_404()
    
    new_project = Project(name=project_name, owner=user)
    db.session.add(new_project)
    db.session.commit()

    session['active_project_id'] = new_project.id
    
    # --- CHANGED: Return a redirect URL to the new settings page ---
    return jsonify({
        'status': 'success', 
        'message': 'Project created successfully', 
        'redirect_url': url_for('settings.settings_home')
    }), 201

@projects_bp.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    """API endpoint to fetch all projects for the home page."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    all_projects = user.projects.order_by(Project.created_at.desc()).all()
    
    projects_list = []
    for p in all_projects:
        projects_list.append({
            'id': p.id,
            'name': p.name,
            'status': getattr(p, 'status', 'active'),
            'targets': [{'id': t.id, 'name': t.name} for t in p.targets.all()],
            'tasks': [{'id': t.id, 'name': t.name, 'status': t.status} for t in p.tasks.all()],
            'last_scan': getattr(p, 'last_scan', None),
            'created_at': p.created_at.isoformat() if p.created_at else None
        })
    
    return jsonify({
        'status': 'success',
        'projects': projects_list
    })

@projects_bp.route('/api/targets')
@login_required
def get_targets():
    """API endpoint to fetch all targets for the home page."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    active_project_id = session.get('active_project_id')
    
    query = Target.query.join(Project).filter(Project.owner == user)
    if active_project_id:
        query = query.filter_by(project_id=active_project_id)
    
    targets_from_db = query.all()
    
    targets_list = []
    for target in targets_from_db:
        targets_list.append({
            'id': target.id,
            'name': target.name,
            'ip_address': target.ip_address,
            'project_id': target.project_id
        })
    
    return jsonify({
        'status': 'success',
        'targets': targets_list
    })

@projects_bp.route('/api/projects/set_active', methods=['POST'])
@login_required
def set_active_project():
    # This remains useful for the sidebar
    data = request.get_json()
    project_id = data.get('project_id')
    
    if not project_id:
        return jsonify({'status': 'error', 'message': 'Project ID is required'}), 400
    
    try:
        project_id = int(project_id)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Invalid project ID'}), 400

    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first()
    
    if not project:
        return jsonify({'status': 'error', 'message': 'Project not found'}), 404
    
    session['active_project_id'] = project_id
    return jsonify({'status': 'success', 'message': f'Active project set to: {project.name}'})


@projects_bp.route('/api/active-project-id')
@login_required
def get_active_project_id():
    """Returns the active project ID from the session."""
    active_project_id = session.get('active_project_id')
    if not active_project_id:
        return jsonify({'error': 'No active project found'}), 404
    return jsonify({'active_project_id': active_project_id})

@projects_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    try:
        db.session.delete(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500
    
    if session.get('active_project_id') == project_id:
        session.pop('active_project_id', None)
        
    return jsonify({'status': 'success', 'message': 'Project deleted successfully'})
