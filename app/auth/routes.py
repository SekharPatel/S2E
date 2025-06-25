# /S2E/app/auth/routes.py
# UPDATED: The redirect after a successful login now points to 'home.home'.

from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from functools import wraps

# Define the blueprint for this feature
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

# --- Authentication Decorator ---
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
        
        USERS = current_app.config.get('USERS', {})
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            # UPDATED: Redirect to the home page in the new 'home' blueprint
            return redirect(url_for('home.home')) 
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@auth_bp.route('/auth/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('auth.login'))