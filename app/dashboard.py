from datetime import date
from flask import Blueprint, jsonify, session
from app.models import (db, Batch, DailyLog, EggLog, ChickenSale, EggSale, FarmSetting, FeedTransaction, Expense)
from app.auth import login_required
from app.finance import avg_cost_per_bag, batch_financials
from app.flock import feed_stock_summary
from app.supplies import supplies_low_stock_alerts

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    today = date.today()
    role = session.get('role')
    settings = FarmSetting.get()

    batches = Batch.query.filter_by(active=True).all()
    active_batches = [b for b in batches if b.status != 'closed']

    total_birds = sum(b.quantity_current for b in active_batches)
    today_mortality = sum(l.mortality for l in DailyLog.query.filter_by(log_date=today).all())

    feed_summary = feed_stock_summary()
    feed_balance = feed_summary['balance_bags']

    egg_collected_today = sum(l.crates_collected for l in EggLog.query.filter_by(log_date=today).all())
    total_collected = sum(l.crates_collected for l in EggLog.query.all())
    total_sold = sum(s.crates_sold for s in EggSale.query.all())
    egg_stock = max(0, total_collected - total_sold)

    today_chicken_sales = [s for s in ChickenSale.query.filter_by(sale_date=today).all()]
    today_egg_sales = [s for s in EggSale.query.filter_by(sale_date=today).all()]
    today_revenue = sum(s.total_amount for s in today_chicken_sales) + sum(s.total_amount for s in today_egg_sales)

    today_feed_bags = sum(t.bags for t in FeedTransaction.query.filter_by(txn_type='OUT', txn_date=today).all())
    today_expenses = sum(e.amount for e in Expense.query.filter_by(exp_date=today).all())

    alerts = []
    if feed_balance <= settings.low_feed_threshold_bags:
        days_left = feed_summary['days_remaining']
        days_msg = f' - about {days_left} days left at current usage' if days_left is not None else ''
        alerts.append({
            'type': 'low_feed', 'severity': 'warning',
            'message': f'Feed stock is low: only {round(feed_balance,1)} bags left{days_msg} (alert threshold: {settings.low_feed_threshold_bags} bags).'
        })
    alerts.extend(supplies_low_stock_alerts())
    for b in active_batches:
        today_log = DailyLog.query.filter_by(batch_id=b.id, log_date=today).first()
        if today_log and b.quantity_current > 0:
            pct = (today_log.mortality / b.quantity_current) * 100
            if pct >= settings.high_mortality_pct_alert:
                alerts.append({
                    'type': 'high_mortality', 'severity': 'danger',
                    'message': f'{b.label}: {today_log.mortality} deaths today ({round(pct,1)}% of stock) - above alert threshold.'
                })
        if not today_log:
            alerts.append({
                'type': 'missing_log', 'severity': 'info',
                'message': f'{b.label}: no daily log recorded yet today.'
            })

    data = {
        'farm_name': settings.farm_name,
        'active_batches': len(active_batches),
        'total_birds': total_birds,
        'today_mortality': today_mortality,
        'feed_balance_bags': round(feed_balance, 2),
        'feed_days_remaining': feed_summary['days_remaining'],
        'low_feed_threshold': settings.low_feed_threshold_bags,
        'egg_collected_today_crates': round(egg_collected_today, 2),
        'egg_stock_crates': round(egg_stock, 2),
        'today_revenue': round(today_revenue, 2),
        'today_sales_count': len(today_chicken_sales) + len(today_egg_sales),
        'today_feed_bags': round(today_feed_bags, 2),
        'alerts': alerts,
        'batches': [b.to_dict() for b in active_batches],
    }

    if role in ('admin', 'super_admin'):
        acpb = avg_cost_per_bag()
        per_batch = [batch_financials(b) for b in active_batches]
        data['avg_cost_per_bag'] = round(acpb, 2)
        data['total_cost_all_batches'] = round(sum(p['total_cost'] for p in per_batch), 2)
        data['total_revenue_all_batches'] = round(sum(p['total_revenue'] for p in per_batch), 2)
        data['total_profit_all_batches'] = round(sum(p['profit'] for p in per_batch), 2)
        data['today_expenses'] = round(today_expenses, 2)

    return jsonify(data)


@dashboard_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    from flask import request
    s = FarmSetting.get()
    if request.method == 'POST':
        if session.get('role') != 'super_admin':
            return jsonify({'success': False, 'error': 'Only the super admin can change farm settings'}), 403
        d = request.get_json()
        if 'farm_name' in d:
            s.farm_name = d['farm_name']
        if 'low_feed_threshold_bags' in d:
            s.low_feed_threshold_bags = float(d['low_feed_threshold_bags'])
        if 'high_mortality_pct_alert' in d:
            s.high_mortality_pct_alert = float(d['high_mortality_pct_alert'])
        db.session.commit()
        return jsonify({'success': True})
    return jsonify(s.to_dict())
