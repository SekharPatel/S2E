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

# --- CONSOLIDATED API ENDPOINT for all project list data ---
@projects_bp.route('/api/projects_data')
@login_required
def get_projects_data_api():
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
# ---------------------------------------------------------

@projects_bp.route('/api/projects/<int:project_id>/run_default_playbook', methods=['POST'])
@login_required
def run_default_playbook(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    if not project.linked_playbooks:
        return jsonify({'status': 'error', 'message': 'No playbooks are linked to this project.'}), 400

    playbook_to_run = project.linked_playbooks[0]

    job_data = {
        'playbook_id': playbook_to_run.id,
        'project_id': project.id
    }
    
    job_id = add_job_to_queue('playbook', job_data, priority=1, project_id=project.id)
    if job_id:
        return jsonify({'status': 'success', 'message': f"Playbook '{playbook_to_run.name}' has been queued."})
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
                playbook_id = int(playbook_id)
                playbook = Playbook.query.get(playbook_id)
                if not playbook:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Playbook with ID {playbook_id} not found'}), 400
                
                new_project.linked_playbooks.append(playbook)
        except (ValueError, TypeError):
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Invalid playbook ID format.'}), 400
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
