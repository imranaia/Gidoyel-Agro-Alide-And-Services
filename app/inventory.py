from datetime import datetime, date
from flask import Blueprint, request, jsonify, session
from app.models import db, ToolCategory, Tool, Expense
from app.auth import login_required, role_required

inventory_bp = Blueprint('inventory', __name__)


def parse_date(s, default=None):
    if not s:
        return default or date.today()
    return datetime.strptime(s, '%Y-%m-%d').date()


# ─── TOOL CATEGORIES ──────────────────────────────────────

@inventory_bp.route('/api/tool-categories', methods=['GET', 'POST'])
@login_required
def api_tool_categories():
    if request.method == 'POST':
        d = request.get_json()
        if ToolCategory.query.filter_by(name=d['name']).first():
            return jsonify({'success': False, 'error': 'Category already exists'})
        c = ToolCategory(name=d['name'])
        db.session.add(c)
        db.session.commit()
        return jsonify({'success': True, 'id': c.id})
    cats = ToolCategory.query.order_by(ToolCategory.name).all()
    return jsonify([c.to_dict() for c in cats])


@inventory_bp.route('/api/tool-categories/<int:cid>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_tool_category(cid):
    c = ToolCategory.query.get_or_404(cid)
    if any(t.active for t in c.tools):
        return jsonify({'success': False, 'error': 'Cannot delete: category has tools'})
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})


# ─── TOOLS ────────────────────────────────────────────────

@inventory_bp.route('/api/tools', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_tools():
    if request.method == 'POST':
        d = request.get_json()
        t = Tool(
            category_id=int(d['category_id']), name=d['name'],
            quantity=float(d.get('quantity', 1)), unit_cost=float(d.get('unit_cost', 0)),
            date_bought=parse_date(d.get('date_bought')), notes=d.get('notes', ''),
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True, 'id': t.id})
    tools = Tool.query.filter_by(active=True).order_by(Tool.date_bought.desc()).all()
    return jsonify([t.to_dict() for t in tools])


@inventory_bp.route('/api/tools/<int:tid>', methods=['PUT', 'DELETE'])
@login_required
@role_required('admin')
def api_tool(tid):
    t = Tool.query.get_or_404(tid)
    if request.method == 'DELETE':
        t.active = False
        db.session.commit()
        return jsonify({'success': True})
    d = request.get_json()
    for f in ['name', 'notes']:
        if f in d:
            setattr(t, f, d[f])
    for f in ['quantity', 'unit_cost']:
        if f in d:
            setattr(t, f, float(d[f]))
    if 'category_id' in d:
        t.category_id = int(d['category_id'])
    db.session.commit()
    return jsonify({'success': True})


# ─── EXPENSES ─────────────────────────────────────────────

EXPENSE_CATEGORIES = ['Labor', 'Transport', 'Utilities', 'Maintenance', 'Other']


@inventory_bp.route('/api/expenses', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_expenses():
    if request.method == 'POST':
        d = request.get_json()
        category = d.get('category', 'Other')
        description = d.get('description', '')
        if category == 'Other' and not description.strip():
            return jsonify({'success': False, 'error': 'Please describe what this "Other" expense is'})
        e = Expense(
            exp_date=parse_date(d.get('exp_date')),
            category=category, description=description,
            amount=float(d.get('amount', 0)), recorded_by=session['user_id'],
        )
        db.session.add(e)
        db.session.commit()
        return jsonify({'success': True, 'id': e.id})
    expenses = Expense.query.order_by(Expense.exp_date.desc()).limit(200).all()
    return jsonify([e.to_dict() for e in expenses])


@inventory_bp.route('/api/expenses/<int:eid>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_expense(eid):
    e = Expense.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    return jsonify({'success': True})
