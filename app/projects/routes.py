# /S2E/app/projects/routes.py

from flask import Blueprint, request, jsonify, session
from app import db
from app.models import User, Project, Target
from app.auth.routes import login_required
from app.tasks.task_manager import add_job_to_queue
from app.utils.validation import (
    sanitize_project_name, sanitize_target_list, validate_target, 
    ValidationError, escape_html
)

projects_bp = Blueprint('projects', __name__)

# --- NEW API ENDPOINT FOR SIDEBAR ---
@projects_bp.route('/api/sidebar_data')
@login_required
def get_sidebar_data_api():
    """API endpoint to fetch data for the sidebar."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    all_projects = user.projects.order_by(Project.created_at.desc()).all()
    active_project_id = session.get('active_project_id')
    
    projects_list = [{'id': p.id, 'name': p.name} for p in all_projects]
    
    return jsonify({
        'all_projects': projects_list,
        'active_project_id': active_project_id
    })
# -----------------------------------------

@projects_bp.route('/api/playbooks/<playbook_id>/run', methods=['POST'])
@login_required
def run_playbook(playbook_id):
    # ... (rest of the file is unchanged)
    active_project_id = session.get('active_project_id')
    if not active_project_id:
        return jsonify({'status': 'error', 'message': 'No active project selected'}), 400

    if not isinstance(playbook_id, str) or len(playbook_id) > 64:
        return jsonify({'status': 'error', 'message': 'Invalid playbook ID'}), 400

    job_data = {
        'playbook_id': playbook_id,
        'project_id': active_project_id
    }
    
    job_id = add_job_to_queue('playbook', job_data, priority=1, project_id=active_project_id)
    if job_id:
        return jsonify({'status': 'success', 'message': f"Playbook '{playbook_id}' has been queued."})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to queue playbook'}), 500

@projects_bp.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    project_name = data.get('name')
    project_desc = data.get('description', '')
    targets_string = data.get('targets', '')
    playbook_ids = data.get('playbook_ids', [])

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    try:
        project_name = sanitize_project_name(project_name)
        project_desc = escape_html(project_desc[:500])
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

    user = User.query.filter_by(username=session['username']).first_or_404()
    
    new_project = Project(name=project_name, description=project_desc, owner=user)
    db.session.add(new_project)
    db.session.flush()

    if targets_string:
        try:
            target_list = sanitize_target_list(targets_string)
            for target_value in target_list:
                new_target = Target(value=target_value, project_id=new_project.id)
                db.session.add(new_target)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error processing targets: {str(e)}'}), 400

    if playbook_ids:
        try:
            from app.models import Playbook
            for playbook_id in playbook_ids:
                if not isinstance(playbook_id, int):
                    try:
                        playbook_id = int(playbook_id)
                    except (ValueError, TypeError):
                        db.session.rollback()
                        return jsonify({'status': 'error', 'message': f'Invalid playbook ID: {playbook_id}'}), 400
                
                playbook = Playbook.query.get(playbook_id)
                if not playbook:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Playbook with ID {playbook_id} not found'}), 400
                
                new_project.linked_playbooks.append(playbook)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error linking playbooks: {str(e)}'}), 400

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500

    session['active_project_id'] = new_project.id
    
    project_data = {
        'id': new_project.id,
        'name': new_project.name
    }
    return jsonify({'status': 'success', 'message': 'Project created successfully', 'project': project_data}), 201


@projects_bp.route('/api/projects/set_active', methods=['POST'])
@login_required
def set_active_project():
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

