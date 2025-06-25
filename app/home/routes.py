# /S2E/app/home/routes.py
# NEW FILE: This module handles the main landing and home pages.

from flask import Blueprint, render_template, redirect, url_for, session

# Import the login decorator from the auth feature
from app.auth.routes import login_required

# Define the blueprint for this feature
home_bp = Blueprint('home', __name__, template_folder='../templates')


@home_bp.route('/')
@login_required
def index():
    """Handles the main landing page."""
    # If the user is already logged in, send them to the home dashboard.
    if 'username' in session:
        return redirect(url_for('home.home'))
    # Otherwise, show the public landing page.
    # return render_template('index.html')


@home_bp.route('/home')
@login_required
def home():
    """Shows the main dashboard for logged-in users to start scans."""
    return render_template('home.html')