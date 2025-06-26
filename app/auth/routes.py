# /S2E/app/auth/routes.py
# UPDATED: Uses the User database model for secure authentication.

from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
from app.models import User # Import the User model

# Define the blueprint for this feature
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

# --- Authentication Decorator (unchanged) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Query the database for the user
        user = User.query.filter_by(username=username).first()
        
        # Check if the user exists and the password is correct
        if user and user.check_password(password):
            session['username'] = username
            return redirect(url_for('home.home')) 
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@auth_bp.route('/auth/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))