from datetime import datetime, date
from flask import Blueprint, request, jsonify, session
from app.models import db, SupplyItem, SupplyTransaction
from app.auth import login_required, role_required

supplies_bp = Blueprint('supplies', __name__)


def parse_date(s, default=None):
    if not s:
        return default or date.today()
    return datetime.strptime(s, '%Y-%m-%d').date()


@supplies_bp.route('/api/supply-items', methods=['GET', 'POST'])
@login_required
def api_supply_items():
    if request.method == 'POST':
        d = request.get_json()
        name = d.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name required'})
        if SupplyItem.query.filter_by(name=name).first():
            return jsonify({'success': False, 'error': 'An item with that name already exists'})
        item = SupplyItem(name=name, low_stock_threshold=float(d.get('low_stock_threshold', 5)))
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'id': item.id})
    items = SupplyItem.query.filter_by(active=True).order_by(SupplyItem.name).all()
    return jsonify([i.to_dict() for i in items])


@supplies_bp.route('/api/supply-items/<int:iid>', methods=['PUT', 'DELETE'])
@login_required
@role_required('admin')
def api_supply_item(iid):
    item = SupplyItem.query.get_or_404(iid)
    if request.method == 'DELETE':
        item.active = False
        db.session.commit()
        return jsonify({'success': True})
    d = request.get_json()
    if 'low_stock_threshold' in d:
        item.low_stock_threshold = float(d['low_stock_threshold'])
    db.session.commit()
    return jsonify({'success': True})


@supplies_bp.route('/api/supply-items/<int:iid>/transactions', methods=['GET', 'POST'])
@login_required
def api_supply_txns(iid):
    item = SupplyItem.query.get_or_404(iid)
    if request.method == 'POST':
        d = request.get_json()
        txn_type = d.get('txn_type', 'OUT').upper()
        if txn_type == 'IN' and session.get('role') == 'staff':
            return jsonify({'success': False, 'error': 'Only admins can record supply purchases'}), 403
        qty = float(d.get('quantity', 0))
        if txn_type == 'IN':
            total_cost = float(d.get('total_cost', 0))
            cost_per_unit = (total_cost / qty) if qty else 0
        else:
            cost_per_unit = 0
        t = SupplyTransaction(
            item_id=item.id, txn_type=txn_type, txn_date=parse_date(d.get('txn_date')),
            quantity=qty, cost_per_unit=cost_per_unit, notes=d.get('notes', ''),
            recorded_by=session['user_id'],
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True, 'id': t.id})
    txns = SupplyTransaction.query.filter_by(item_id=item.id).order_by(SupplyTransaction.txn_date.desc()).limit(100).all()
    return jsonify([t.to_dict() for t in txns])


def supplies_low_stock_alerts():
    alerts = []
    for item in SupplyItem.query.filter_by(active=True).all():
        if item.balance_bags <= item.low_stock_threshold:
            alerts.append({
                'type': 'low_supply', 'severity': 'warning',
                'message': f'{item.name} stock is low: only {round(item.balance_bags, 1)} bags left (alert threshold: {item.low_stock_threshold} bags).'
            })
    return alerts
