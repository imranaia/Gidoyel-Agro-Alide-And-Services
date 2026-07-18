from flask import Blueprint, request, jsonify, session
from app.models import db, User
from app.auth import login_required, role_required

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/api/staff', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_staff():
    if request.method == 'POST':
        d = request.get_json()
        role = d.get('role', 'staff')
        if role == 'admin' and session.get('role') != 'super_admin':
            return jsonify({'success': False, 'error': 'Only the super admin can create admin accounts'}), 403
        if role not in ('staff', 'admin'):
            role = 'staff'
        if User.query.filter_by(username=d['username']).first():
            return jsonify({'success': False, 'error': 'Username already exists'})
        u = User(full_name=d['full_name'], username=d['username'], phone=d.get('phone', ''), role=role)
        u.set_password(d.get('password', '1234'))
        db.session.add(u)
        db.session.commit()
        return jsonify({'success': True, 'id': u.id})
    users = User.query.filter(User.role.in_(['staff', 'admin'])).order_by(User.full_name).all()
    return jsonify([u.to_dict() for u in users])


@staff_bp.route('/api/staff/<int:uid>', methods=['PUT', 'DELETE'])
@login_required
@role_required('admin')
def api_staff_member(uid):
    u = User.query.get_or_404(uid)
    if u.role == 'admin' and session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'Only the super admin can manage admin accounts'}), 403
    if u.role == 'super_admin':
        return jsonify({'success': False, 'error': 'Cannot modify the super admin account here'}), 403
    if request.method == 'DELETE':
        u.active = False
        db.session.commit()
        return jsonify({'success': True})
    d = request.get_json()
    if 'full_name' in d:
        u.full_name = d['full_name']
    if 'phone' in d:
        u.phone = d['phone']
    if 'active' in d:
        u.active = bool(d['active'])
    if d.get('password'):
        u.set_password(d['password'])
    db.session.commit()
    return jsonify({'success': True})
