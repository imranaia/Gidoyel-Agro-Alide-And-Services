from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

ROLE_LEVEL = {'staff': 1, 'admin': 2, 'super_admin': 3}


def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('auth.login'))
        return f(*a, **kw)
    return dec


def role_required(min_role):
    """Require session role to be at least min_role in the staff < admin < super_admin hierarchy."""
    def wrapper(f):
        @wraps(f)
        def dec(*a, **kw):
            if 'user_id' not in session:
                return jsonify({'error': 'Not authenticated'}), 401
            if ROLE_LEVEL.get(session.get('role'), 0) < ROLE_LEVEL[min_role]:
                return jsonify({'error': 'You do not have permission to do this'}), 403
            return f(*a, **kw)
        return dec
    return wrapper


@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        d = request.get_json()
        user = User.query.filter_by(username=d.get('username', '')).first()
        if not user or not user.check_password(d.get('password', '')):
            return jsonify({'success': False, 'error': 'Invalid username or password'})
        if not user.active:
            return jsonify({'success': False, 'error': 'This account is deactivated'})
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.full_name
        return jsonify({'success': True, 'role': user.role})
    return render_template('index.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')


# ─── SESSION / PROFILE ────────────────────────────────────

@auth_bp.route('/api/me')
@login_required
def api_me():
    u = User.query.get(session['user_id'])
    return jsonify(u.to_dict())


@auth_bp.route('/api/me/update', methods=['POST'])
@login_required
def api_me_update():
    d = request.get_json()
    u = User.query.get(session['user_id'])
    if d.get('full_name'):
        u.full_name = d['full_name']
    if d.get('username'):
        ex = User.query.filter_by(username=d['username']).first()
        if ex and ex.id != u.id:
            return jsonify({'success': False, 'error': 'Username taken'})
        u.username = d['username']
    if 'phone' in d:
        u.phone = d['phone']
    if d.get('new_password'):
        if not u.check_password(d.get('current_password', '')):
            return jsonify({'success': False, 'error': 'Current password incorrect'})
        u.set_password(d['new_password'])
    db.session.commit()
    session['name'] = u.full_name
    return jsonify({'success': True})
