from flask import Blueprint, request, jsonify
from app.models import db, Batch, FeedTransaction, Medication, Vaccination, ChickenSale, EggSale, Tool, Expense, SupplyTransaction
from app.auth import login_required, role_required

finance_bp = Blueprint('finance', __name__)


def avg_cost_per_bag():
    ins = FeedTransaction.query.filter_by(txn_type='IN').all()
    total_in = sum(t.bags for t in ins)
    total_in_cost = sum(t.bags * t.cost_per_bag for t in ins)
    return (total_in_cost / total_in) if total_in else 0


def batch_financials(batch):
    acpb = avg_cost_per_bag()
    feed_out = FeedTransaction.query.filter_by(txn_type='OUT', batch_id=batch.id).all()
    feed_cost = sum(t.bags for t in feed_out) * acpb
    med_cost = sum(m.cost for m in Medication.query.filter_by(batch_id=batch.id).all())
    vac_cost = sum(v.cost for v in Vaccination.query.filter_by(batch_id=batch.id).all())
    purchase_cost = batch.amount_paid
    total_cost = purchase_cost + feed_cost + med_cost + vac_cost

    chicken_rev = sum(s.total_amount for s in ChickenSale.query.filter_by(batch_id=batch.id).all())
    egg_rev = sum(s.total_amount for s in EggSale.query.filter_by(batch_id=batch.id).all())
    total_revenue = chicken_rev + egg_rev

    return {
        'batch_id': batch.id, 'batch_label': batch.label,
        'purchase_cost': round(purchase_cost, 2), 'feed_cost': round(feed_cost, 2),
        'medication_cost': round(med_cost, 2), 'vaccination_cost': round(vac_cost, 2),
        'total_cost': round(total_cost, 2),
        'chicken_revenue': round(chicken_rev, 2), 'egg_revenue': round(egg_rev, 2),
        'total_revenue': round(total_revenue, 2),
        'profit': round(total_revenue - total_cost, 2),
        'quantity_current': batch.quantity_current,
    }


@finance_bp.route('/api/finance/batches/<int:bid>')
@login_required
@role_required('admin')
def api_batch_financials(bid):
    b = Batch.query.get_or_404(bid)
    return jsonify(batch_financials(b))


@finance_bp.route('/api/finance/breakdown')
@login_required
@role_required('admin')
def api_finance_breakdown():
    """Total spending grouped by category, across every place cost is recorded."""
    bird_cost = sum(b.amount_paid for b in Batch.query.filter_by(active=True).all())
    feed_cost = sum(t.bags * t.cost_per_bag for t in FeedTransaction.query.filter_by(txn_type='IN').all())
    med_cost = sum(m.cost for m in Medication.query.all())
    vac_cost = sum(v.cost for v in Vaccination.query.all())
    tools_cost = sum(t.total_cost for t in Tool.query.filter_by(active=True).all())
    supplies_cost = sum(t.quantity * t.cost_per_unit for t in SupplyTransaction.query.filter_by(txn_type='IN').all())

    categories = [
        {'category': 'Birds Purchased', 'amount': round(bird_cost, 2)},
        {'category': 'Feed', 'amount': round(feed_cost, 2)},
        {'category': 'Medication', 'amount': round(med_cost, 2)},
        {'category': 'Vaccination', 'amount': round(vac_cost, 2)},
        {'category': 'Tools & Equipment', 'amount': round(tools_cost, 2)},
        {'category': 'Other Supplies (charcoal, sawdust, etc.)', 'amount': round(supplies_cost, 2)},
    ]
    expense_by_cat = {}
    for e in Expense.query.all():
        expense_by_cat[e.category] = expense_by_cat.get(e.category, 0) + e.amount
    for cat, amt in expense_by_cat.items():
        categories.append({'category': cat, 'amount': round(amt, 2)})

    categories = [c for c in categories if c['amount'] > 0]
    categories.sort(key=lambda c: -c['amount'])
    total = sum(c['amount'] for c in categories)
    return jsonify({'categories': categories, 'total': round(total, 2)})


@finance_bp.route('/api/finance/summary')
@login_required
@role_required('admin')
def api_finance_summary():
    batches = Batch.query.filter_by(active=True).all()
    per_batch = [batch_financials(b) for b in batches]
    tools_cost = sum(t.total_cost for t in Tool.query.filter_by(active=True).all())
    expenses_total = sum(e.amount for e in Expense.query.all())
    unassigned_egg_rev = sum(s.total_amount for s in EggSale.query.filter_by(batch_id=None).all())

    total_cost = sum(p['total_cost'] for p in per_batch) + tools_cost + expenses_total
    total_revenue = sum(p['total_revenue'] for p in per_batch) + unassigned_egg_rev

    return jsonify({
        'per_batch': per_batch,
        'tools_cost': round(tools_cost, 2),
        'expenses_total': round(expenses_total, 2),
        'unassigned_egg_revenue': round(unassigned_egg_rev, 2),
        'total_cost': round(total_cost, 2),
        'total_revenue': round(total_revenue, 2),
        'total_profit': round(total_revenue - total_cost, 2),
    })


# ─── PREDICTIVE PRICING ───────────────────────────────────
# Given a batch, a target profit %, and what's being sold (chicken or egg),
# calculate the price per unit needed to hit that profit target.

@finance_bp.route('/api/finance/predict-price', methods=['POST'])
@login_required
@role_required('admin')
def api_predict_price():
    d = request.get_json()
    batch = Batch.query.get_or_404(int(d['batch_id']))
    sell_type = d.get('sell_type', 'chicken')  # chicken / egg
    target_pct = float(d.get('target_profit_pct', 20))

    fin = batch_financials(batch)
    target_total_revenue = fin['total_cost'] * (1 + target_pct / 100)

    if sell_type == 'chicken':
        already_realized = fin['chicken_revenue']
        default_qty = batch.quantity_current
    else:
        already_realized = fin['egg_revenue']
        default_qty = None  # eggs aren't tied to a fixed remaining count like birds

    qty = float(d['quantity']) if d.get('quantity') not in (None, '') else default_qty
    remaining_needed = max(0, target_total_revenue - already_realized)

    if not qty or qty <= 0:
        return jsonify({'success': False, 'error': 'Enter a quantity to price against (no remaining stock to auto-fill)'})

    price_per_unit = remaining_needed / qty

    return jsonify({
        'success': True,
        'batch_label': batch.label,
        'sell_type': sell_type,
        'total_cost': fin['total_cost'],
        'target_profit_pct': target_pct,
        'target_total_revenue': round(target_total_revenue, 2),
        'already_realized_revenue': round(already_realized, 2),
        'remaining_revenue_needed': round(remaining_needed, 2),
        'quantity_used': qty,
        'price_per_unit': round(price_per_unit, 2),
        'unit_label': 'per bird' if sell_type == 'chicken' else 'per crate',
    })
