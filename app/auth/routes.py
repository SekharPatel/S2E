# /S2E/app/auth/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from app.models import User
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home.home'))
        
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            session['username'] = username # Maintain session for compatibility if needed elsewhere
            return redirect(url_for('home.home')) 
        else:
            error = 'Invalid credentials. Please try again.'
            
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    logout_user()
    session.pop('username', None)
    return redirect(url_for('auth.login'))
