# /S2E/app/settings/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db
from app.models import User, Project, Target, Playbook
from app.auth.routes import login_required
from app.utils.validation import sanitize_project_name, sanitize_target_list, ValidationError, escape_html
from app.home.routes import get_base_data # Import the helper function

settings_bp = Blueprint('settings', __name__, template_folder='../templates')

@settings_bp.route('/settings')
@login_required
def settings_home():
    """Renders the settings page, pre-loading data for the active project."""
    base_data = get_base_data()
    active_project_id = base_data.get('active_project_id')

    if not active_project_id:
        flash('Create a project to access settings.', 'info')
        return redirect(url_for('home.home'))

    return render_template('settings.html', base_data=base_data)

@settings_bp.route('/api/settings/<int:project_id>/details')
@login_required
def get_project_details(project_id):
    """Returns all necessary details for the settings page for a given project."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()

    all_playbooks = Playbook.query.all()
    linked_playbook_ids = {p.id for p in project.linked_playbooks}
    
    available_playbooks = [{'id': p.id, 'name': p.name} for p in all_playbooks if p.id not in linked_playbook_ids]
    linked_playbooks = [{'id': p.id, 'name': p.name} for p in project.linked_playbooks]

    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description or '',
        'targets': '\n'.join([t.value for t in project.targets.all()]),
        'linked_playbooks': linked_playbooks,
        'available_playbooks': available_playbooks
    }
    return jsonify(project_data)

@settings_bp.route('/settings/project/<int:project_id>')
@login_required
def project_settings(project_id):
    """Displays the main settings page for a specific project."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    
    # Set this as the active project when visiting its settings
    session['active_project_id'] = project_id

    # FIX: Fetch base_data to pass to the template for the sidebar
    base_data = get_base_data()

    all_playbooks = Playbook.query.all()
    linked_playbook_ids = {p.id for p in project.linked_playbooks}
    
    # Filter out already linked playbooks
    available_playbooks = [p for p in all_playbooks if p.id not in linked_playbook_ids]

    return render_template('settings.html', 
                           project=project, 
                           all_playbooks=all_playbooks,
                           available_playbooks=available_playbooks,
                           base_data=base_data) # Pass base_data to the template

@settings_bp.route('/api/settings/project/<int:project_id>/update', methods=['POST'])
@login_required
def update_project_settings(project_id):
    """API endpoint to update project details from the settings page."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    data = request.json

    try:
        project.name = sanitize_project_name(data.get('name', ''))
        project.description = escape_html(data.get('description', ''))
        
        # Update targets: delete old and create new
        Target.query.filter_by(project_id=project.id).delete()
        target_list = sanitize_target_list(data.get('targets', ''))
        for target_value in target_list:
            new_target = Target(value=target_value, project_id=project.id)
            db.session.add(new_target)
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Project details updated successfully.'})
    except ValidationError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'An internal error occurred.'}), 500

@settings_bp.route('/api/settings/project/<int:project_id>/link_playbook', methods=['POST'])
@login_required
def link_playbook(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    playbook_id = request.json.get('playbook_id')
    
    playbook = Playbook.query.get(playbook_id)
    if not playbook:
        return jsonify({'status': 'error', 'message': 'Playbook not found.'}), 404
        
    project.linked_playbooks.append(playbook)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f"Playbook '{playbook.name}' linked."})

@settings_bp.route('/api/settings/project/<int:project_id>/unlink_playbook', methods=['POST'])
@login_required
def unlink_playbook(project_id):
    user = User.query.filter_by(username=session['username']).first_or_404()
    project = user.projects.filter_by(id=project_id).first_or_404()
    playbook_id = request.json.get('playbook_id')
    
    playbook = Playbook.query.get(playbook_id)
    if not playbook:
        return jsonify({'status': 'error', 'message': 'Playbook not found.'}), 404
        
    if playbook in project.linked_playbooks:
        project.linked_playbooks.remove(playbook)
        db.session.commit()
    
    return jsonify({'status': 'success', 'message': f"Playbook '{playbook.name}' unlinked."})