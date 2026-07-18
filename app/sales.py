from datetime import datetime, date
from flask import Blueprint, request, jsonify, session
from app.models import db, Batch, ChickenSale, EggSale, EggLog
from app.auth import login_required, role_required

sales_bp = Blueprint('sales', __name__)


def parse_date(s, default=None):
    if not s:
        return default or date.today()
    return datetime.strptime(s, '%Y-%m-%d').date()


def gen_receipt(prefix, model):
    last = model.query.order_by(model.id.desc()).first()
    return f"{prefix}-{((last.id if last else 0) + 1):05d}"


# ─── CHICKEN SALES ────────────────────────────────────────

@sales_bp.route('/api/sales/chickens', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_chicken_sales():
    if request.method == 'POST':
        d = request.get_json()
        batch = Batch.query.get_or_404(int(d['batch_id']))
        qty = int(d.get('quantity', 0))
        if qty <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be greater than zero'})
        if qty > batch.quantity_current:
            return jsonify({'success': False, 'error': f'Only {batch.quantity_current} birds available in this batch'})
        price = float(d.get('price_per_bird', 0))
        s = ChickenSale(
            receipt_no=gen_receipt('CHK', ChickenSale), batch_id=batch.id,
            sale_date=parse_date(d.get('sale_date')),
            buyer_name=d.get('buyer_name', ''), buyer_phone=d.get('buyer_phone', ''),
            quantity=qty, price_per_bird=price, total_amount=round(qty * price, 2),
            notes=d.get('notes', ''), staff_id=session['user_id'],
        )
        db.session.add(s)
        db.session.commit()
        return jsonify({'success': True, 'id': s.id, 'receipt_no': s.receipt_no})
    batch_id = request.args.get('batch_id')
    query = ChickenSale.query
    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))
    sales = query.order_by(ChickenSale.sale_date.desc()).limit(150).all()
    return jsonify([s.to_dict() for s in sales])


# ─── EGG SALES ────────────────────────────────────────────

@sales_bp.route('/api/sales/eggs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def api_egg_sales():
    if request.method == 'POST':
        d = request.get_json()
        crates = float(d.get('crates_sold', 0))
        if crates <= 0:
            return jsonify({'success': False, 'error': 'Crates sold must be greater than zero'})
        total_collected = sum(l.crates_collected for l in EggLog.query.all())
        total_sold = sum(s.crates_sold for s in EggSale.query.all())
        in_stock = total_collected - total_sold
        if crates > in_stock + 0.01:
            return jsonify({'success': False, 'error': f'Only {round(in_stock,2)} crates available in stock'})
        price = float(d.get('price_per_crate', 0))
        s = EggSale(
            receipt_no=gen_receipt('EGG', EggSale), batch_id=d.get('batch_id') or None,
            sale_date=parse_date(d.get('sale_date')),
            buyer_name=d.get('buyer_name', ''), buyer_phone=d.get('buyer_phone', ''),
            crates_sold=crates, price_per_crate=price, total_amount=round(crates * price, 2),
            notes=d.get('notes', ''), staff_id=session['user_id'],
        )
        db.session.add(s)
        db.session.commit()
        return jsonify({'success': True, 'id': s.id, 'receipt_no': s.receipt_no})
    sales = EggSale.query.order_by(EggSale.sale_date.desc()).limit(150).all()
    return jsonify([s.to_dict() for s in sales])
