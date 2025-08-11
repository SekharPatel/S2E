# /S2E/app/playbooks/routes.py

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from app import db
from app.models import User, Playbook, PlaybookRule
from app.routes.auth.routes import login_required
from app.utils.validation import (
    sanitize_project_name, ValidationError, escape_html
)
import json

playbooks_bp = Blueprint('playbooks', __name__)

@playbooks_bp.route('/playbooks')
@login_required
def list_playbooks():
    """Display all playbooks with management options."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    
    # Get all playbooks (user's own + system playbooks)
    user_playbooks = user.playbooks.order_by(Playbook.created_at.desc()).all()
    system_playbooks = Playbook.query.filter(Playbook.user_id != user.id).order_by(Playbook.created_at.desc()).all()
    
    return render_template('playbooks/list.html', 
                         user_playbooks=user_playbooks,
                         system_playbooks=system_playbooks)


@playbooks_bp.route('/playbooks/new')
@login_required
def new_playbook():
    """Display form to create a new playbook."""
    # Get available tools for dropdowns
    from flask import current_app
    tools = current_app.config.get("TOOLS", {})
    
    return render_template('playbooks/new.html', tools=tools)


@playbooks_bp.route('/playbooks/new', methods=['POST'])
@login_required
def create_playbook():
    """Handle creation of a new playbook."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    data = request.get_json()

    try:
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        workflow_data = data.get('workflow_data')

        if not name:
            return jsonify({'success': False, 'message': 'Playbook name is required.'}), 400

        # Sanitize inputs
        name = sanitize_project_name(name)
        description = escape_html(description[:500])

        # Create the playbook
        new_playbook = Playbook(
            name=name,
            description=description,
            workflow_data=workflow_data,
            user_id=user.id,
            # Add dummy data for legacy fields
            trigger_name="Workflow Trigger",
            trigger_tool_id="n/a",
            trigger_options=""
        )
        
        db.session.add(new_playbook)
        db.session.commit()

        flash(f'Playbook "{name}" created successfully!', 'success')
        return jsonify({'success': True, 'redirect': url_for('playbooks.list_playbooks')})
        
    except ValidationError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating playbook: {str(e)}'}), 500


@playbooks_bp.route('/playbooks/<int:playbook_id>/edit')
@login_required
def edit_playbook(playbook_id):
    """Display form to edit an existing playbook."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    playbook = user.playbooks.filter_by(id=playbook_id).first_or_404()
    
    # Get available tools for dropdowns
    from flask import current_app
    tools = current_app.config.get("TOOLS", {})
    
    return render_template('playbooks/edit.html', playbook=playbook, tools=tools)


@playbooks_bp.route('/playbooks/<int:playbook_id>/edit', methods=['POST'])
@login_required
def update_playbook(playbook_id):
    """Handle updating an existing playbook."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    playbook = user.playbooks.filter_by(id=playbook_id).first_or_404()
    data = request.get_json()

    try:
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        workflow_data = data.get('workflow_data')

        if not name:
            return jsonify({'success': False, 'message': 'Playbook name is required.'}), 400

        # Sanitize inputs
        name = sanitize_project_name(name)
        description = escape_html(description[:500])

        # Update playbook
        playbook.name = name
        playbook.description = description
        playbook.workflow_data = workflow_data
        
        db.session.commit()

        flash(f'Playbook "{name}" updated successfully!', 'success')
        return jsonify({'success': True, 'redirect': url_for('playbooks.list_playbooks')})
        
    except ValidationError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating playbook: {str(e)}'}), 500


@playbooks_bp.route('/playbooks/<int:playbook_id>/delete', methods=['POST'])
@login_required
def delete_playbook(playbook_id):
    """Handle deletion of a playbook."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    playbook = user.playbooks.filter_by(id=playbook_id).first_or_404()
    
    try:
        playbook_name = playbook.name
        
        # Check if playbook is linked to any projects
        linked_projects_count = len(playbook.linked_projects)
        if linked_projects_count > 0:
            flash(f'Cannot delete playbook "{playbook_name}" - it is linked to {linked_projects_count} project(s). Remove the links first.', 'error')
            return redirect(url_for('playbooks.list_playbooks'))
        
        # Delete the playbook (cascade will delete rules)
        db.session.delete(playbook)
        db.session.commit()
        
        flash(f'Playbook "{playbook_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting playbook: {str(e)}', 'error')
    
    return redirect(url_for('playbooks.list_playbooks'))


@playbooks_bp.route('/playbooks/<int:playbook_id>/clone', methods=['POST'])
@login_required
def clone_playbook(playbook_id):
    """Create a copy of an existing playbook."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    
    # Get the source playbook (can be from any user)
    source_playbook = Playbook.query.get_or_404(playbook_id)
    
    try:
        # Create new playbook with copied data
        new_playbook = Playbook(
            name=f"{source_playbook.name} (Copy)",
            description=source_playbook.description,
            trigger_name=source_playbook.trigger_name,
            trigger_tool_id=source_playbook.trigger_tool_id,
            trigger_options=source_playbook.trigger_options,
            user_id=user.id  # Assign to current user
        )
        
        db.session.add(new_playbook)
        db.session.flush()  # Get the ID for rules
        
        # Copy all rules
        rule_count = 0
        for source_rule in source_playbook.rules.all():
            new_rule = PlaybookRule(
                action_name=source_rule.action_name,
                action_tool_id=source_rule.action_tool_id,
                action_options=source_rule.action_options,
                playbook_id=new_playbook.id
            )
            new_rule.set_on_service_list(source_rule.get_on_service_list())
            db.session.add(new_rule)
            rule_count += 1
        
        db.session.commit()
        flash(f'Playbook cloned successfully as "{new_playbook.name}" with {rule_count} rules!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cloning playbook: {str(e)}', 'error')
    
    return redirect(url_for('playbooks.list_playbooks'))


@playbooks_bp.route('/api/playbooks/<int:playbook_id>/export')
@login_required
def export_playbook(playbook_id):
    """Export a playbook as JSON for backup/sharing."""
    user = User.query.filter_by(username=session['username']).first_or_404()
    playbook = Playbook.query.get_or_404(playbook_id)
    
    # Allow export of any playbook (including system ones)
    export_data = {
        'export_info': {
            'exported_by': user.username,
            'exported_at': playbook.created_at.isoformat(),
            'version': '1.0'
        },
        'playbook': playbook.to_dict()
    }
    
    return jsonify(export_data)
