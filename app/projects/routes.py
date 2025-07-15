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


@projects_bp.route('/api/playbooks/<playbook_id>/run', methods=['POST'])
@login_required
def run_playbook(playbook_id):
    active_project_id = session.get('active_project_id')
    if not active_project_id:
        return jsonify({'status': 'error', 'message': 'No active project selected'}), 400

    # Validate playbook_id
    if not isinstance(playbook_id, str) or len(playbook_id) > 64:
        return jsonify({'status': 'error', 'message': 'Invalid playbook ID'}), 400

    job_data = {
        'playbook_id': playbook_id,
        'project_id': active_project_id
    }
    
    # Add to the persistent database queue
    job_id = add_job_to_queue('playbook', job_data, priority=1, project_id=active_project_id)  # Higher priority for playbooks
    if job_id:
        return jsonify({'status': 'success', 'message': f"Playbook '{playbook_id}' has been queued."})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to queue playbook'}), 500

@projects_bp.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    """API endpoint to create a new project with its initial scope."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    project_name = data.get('name')
    project_desc = data.get('description', '')
    targets_string = data.get('targets', '')
    playbook_ids = data.get('playbook_ids', [])  # List of playbook IDs to link

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    try:
        # Sanitize project name
        project_name = sanitize_project_name(project_name)
        # Sanitize description
        project_desc = escape_html(project_desc[:500])  # Limit description length
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

    user = User.query.filter_by(username=session['username']).first_or_404()
    
    # Create the Project
    new_project = Project(name=project_name, description=project_desc, owner=user)
    db.session.add(new_project)
    
    # Important: Flush the session to get the new_project.id before commit
    db.session.flush()

    # Add targets if they were provided
    if targets_string:
        try:
            target_list = sanitize_target_list(targets_string)
            for target_value in target_list:
                new_target = Target(value=target_value, project_id=new_project.id)
                db.session.add(new_target)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error processing targets: {str(e)}'}), 400

    # Link playbooks if they were provided
    if playbook_ids:
        try:
            from app.models import Playbook
            for playbook_id in playbook_ids:
                # Validate playbook_id is an integer
                if not isinstance(playbook_id, int):
                    try:
                        playbook_id = int(playbook_id)
                    except (ValueError, TypeError):
                        db.session.rollback()
                        return jsonify({'status': 'error', 'message': f'Invalid playbook ID: {playbook_id}'}), 400
                
                # Check if playbook exists
                playbook = Playbook.query.get(playbook_id)
                if not playbook:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Playbook with ID {playbook_id} not found'}), 400
                
                # Link the playbook to the project
                new_project.linked_playbooks.append(playbook)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error linking playbooks: {str(e)}'}), 400

    # Commit all changes to the database
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500

    # Automatically set the new project as active
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
    
    # Validate project_id is an integer
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


@projects_bp.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project_details(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    
    targets = [target.value for target in project.targets.all()]
    linked_playbook_ids = [playbook.id for playbook in project.linked_playbooks]
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description or '',
        'targets': '\n'.join(targets),
        'playbook_ids': linked_playbook_ids
    }
    return jsonify(project_data)


@projects_bp.route('/api/projects/<int:project_id>/edit', methods=['POST'])
@login_required
def update_project(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    project_name = data.get('name')
    playbook_ids = data.get('playbook_ids', [])  # List of playbook IDs to link
    
    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400
    
    try:
        # Sanitize project name
        project_name = sanitize_project_name(project_name)
        # Sanitize description
        project_desc = escape_html(data.get('description', '')[:500])
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # Update project fields
    project.name = project_name
    project.description = project_desc
    
    # Update targets: simple strategy is to delete old and create new
    Target.query.filter_by(project_id=project.id).delete()
    
    targets_string = data.get('targets', '')
    if targets_string:
        try:
            target_list = sanitize_target_list(targets_string)
            for target_value in target_list:
                new_target = Target(value=target_value, project_id=project.id)
                db.session.add(new_target)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error processing targets: {str(e)}'}), 400

    # Update linked playbooks: clear existing links and add new ones
    project.linked_playbooks.clear()
    if playbook_ids:
        try:
            from app.models import Playbook
            for playbook_id in playbook_ids:
                # Validate playbook_id is an integer
                if not isinstance(playbook_id, int):
                    try:
                        playbook_id = int(playbook_id)
                    except (ValueError, TypeError):
                        db.session.rollback()
                        return jsonify({'status': 'error', 'message': f'Invalid playbook ID: {playbook_id}'}), 400
                
                # Check if playbook exists
                playbook = Playbook.query.get(playbook_id)
                if not playbook:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Playbook with ID {playbook_id} not found'}), 400
                
                # Link the playbook to the project
                project.linked_playbooks.append(playbook)
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error linking playbooks: {str(e)}'}), 400
            
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500
        
    return jsonify({'status': 'success', 'message': 'Project updated successfully'})


@projects_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    # The 'cascade="all, delete-orphan"' in the model handles deleting
    # all associated Tasks and Targets automatically.
    try:
        db.session.delete(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500
    
    # If the deleted project was the active one, clear it from the session
    if session.get('active_project_id') == project_id:
        session.pop('active_project_id', None)
        
    return jsonify({'status': 'success', 'message': 'Project deleted successfully'})