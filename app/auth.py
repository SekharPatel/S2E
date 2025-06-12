# /S2E/app/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from functools import wraps

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login')) # Note: blueprint name is prefixed
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Access users from the app's configuration
        USERS = current_app.config.get('USERS', {})
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('main.home')) # Redirect to home page in 'main' blueprint
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))