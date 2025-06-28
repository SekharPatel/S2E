# /S2E/app/projects/routes.py
# UPDATED: The create_project function now handles description and targets.

from flask import Blueprint, request, jsonify, session
from app import db
from app.models import User, Project, Target
from app.auth.routes import login_required

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    """API endpoint to create a new project with its initial scope."""
    data = request.get_json()
    project_name = data.get('name')
    project_desc = data.get('description', '')
    targets_string = data.get('targets', '')

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    user = User.query.filter_by(username=session['username']).first_or_404()
    
    # Create the Project
    new_project = Project(name=project_name, description=project_desc, owner=user)
    db.session.add(new_project)
    
    # Important: Flush the session to get the new_project.id before commit
    db.session.flush()

    # Add targets if they were provided
    if targets_string:
        target_list = [line.strip() for line in targets_string.strip().split('\n') if line.strip()]
        for target_value in target_list:
            new_target = Target(value=target_value, project_id=new_project.id)
            db.session.add(new_target)

    # Commit all changes to the database
    db.session.commit()

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
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first()
    if not project:
        return jsonify({'status': 'error', 'message': 'Project not found or access denied'}), 404
    session['active_project_id'] = project_id
    return jsonify({'status': 'success', 'message': f'Active project set to {project.name}'})


@projects_bp.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project_details(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    
    targets = [target.value for target in project.targets.all()]
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description or '',
        'targets': '\n'.join(targets)
    }
    return jsonify(project_data)



@projects_bp.route('/api/projects/<int:project_id>/edit', methods=['POST'])
@login_required
def update_project(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    data = request.get_json()
    project_name = data.get('name')
    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400
    
    # Update project fields
    project.name = project_name
    project.description = data.get('description', '')
    
    # Update targets: simple strategy is to delete old and create new
    Target.query.filter_by(project_id=project.id).delete()
    
    targets_string = data.get('targets', '')
    if targets_string:
        target_list = [line.strip() for line in targets_string.strip().split('\n') if line.strip()]
        for target_value in target_list:
            new_target = Target(value=target_value, project_id=project.id)
            db.session.add(new_target)
            
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Project updated successfully'})


@projects_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    # The 'cascade="all, delete-orphan"' in the model handles deleting
    # all associated Tasks and Targets automatically.
    db.session.delete(project)
    db.session.commit()
    
    # If the deleted project was the active one, clear it from the session
    if session.get('active_project_id') == project_id:
        session.pop('active_project_id', None)
        
    return jsonify({'status': 'success', 'message': 'Project deleted successfully'})