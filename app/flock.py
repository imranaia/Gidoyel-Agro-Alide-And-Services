from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session
from app.models import db, Batch, DailyLog, FeedTransaction, BodyWeight, Medication, Vaccination, EggLog, ChickenSale, EggSale
from app.auth import login_required, role_required

flock_bp = Blueprint('flock', __name__)


def parse_date(s, default=None):
    if not s:
        return default or date.today()
    return datetime.strptime(s, '%Y-%m-%d').date()


# ─── BATCHES ──────────────────────────────────────────────

@flock_bp.route('/api/batches', methods=['GET', 'POST'])
@login_required
def api_batches():
    if request.method == 'POST':
        d = request.get_json()
        date_purchased = parse_date(d.get('date_purchased'))
        point_of_lay = bool(d.get('point_of_lay'))
        b = Batch(
            label=d['label'],
            date_purchased=date_purchased,
            quantity_ordered=int(d.get('quantity_ordered', 0)),
            quantity_received=int(d.get('quantity_received', 0)),
            amount_paid=float(d.get('amount_paid', 0)),
            notes=d.get('notes', ''),
            created_by=session['user_id'],
        )
        if point_of_lay:
            b.status = 'laying'
            b.laying_start_date = date_purchased
        db.session.add(b)
        db.session.commit()
        return jsonify({'success': True, 'id': b.id})
    status = request.args.get('status', '')
    query = Batch.query.filter_by(active=True)
    if status:
        query = query.filter_by(status=status)
    return jsonify([b.to_dict() for b in query.order_by(Batch.date_purchased.desc()).all()])


@flock_bp.route('/api/batches/<int:bid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_batch(bid):
    b = Batch.query.get_or_404(bid)
    if request.method == 'DELETE':
        b.active = False
        db.session.commit()
        return jsonify({'success': True})
    if request.method == 'GET':
        return jsonify(b.to_dict())
    d = request.get_json()
    for f in ['label', 'notes']:
        if f in d:
            setattr(b, f, d[f])
    for f in ['quantity_ordered', 'quantity_received']:
        if f in d:
            setattr(b, f, int(d[f]))
    if 'amount_paid' in d:
        b.amount_paid = float(d['amount_paid'])
    if 'date_purchased' in d:
        b.date_purchased = parse_date(d['date_purchased'])
    if 'status' in d:
        b.status = d['status']
        if d['status'] == 'laying' and not b.laying_start_date:
            b.laying_start_date = date.today()
    if 'laying_start_date' in d and d['laying_start_date']:
        b.laying_start_date = parse_date(d['laying_start_date'])
    db.session.commit()
    return jsonify({'success': True})


# ─── DAILY LOG (mortality, water, remarks) ────────────────

@flock_bp.route('/api/batches/<int:bid>/daily-logs', methods=['GET', 'POST'])
@login_required
def api_daily_logs(bid):
    Batch.query.get_or_404(bid)
    if request.method == 'POST':
        d = request.get_json()
        log_date = parse_date(d.get('log_date'))
        entry = DailyLog.query.filter_by(batch_id=bid, log_date=log_date).first()
        if not entry:
            entry = DailyLog(batch_id=bid, log_date=log_date)
            db.session.add(entry)
        entry.mortality = int(d.get('mortality', 0))
        entry.water_liters = float(d.get('water_liters', 0))
        entry.remarks = d.get('remarks', '')
        entry.recorded_by = session['user_id']
        db.session.commit()
        return jsonify({'success': True, 'id': entry.id})
    logs = DailyLog.query.filter_by(batch_id=bid).order_by(DailyLog.log_date.desc()).limit(90).all()
    return jsonify([l.to_dict() for l in logs])


# ─── FEED (feed in / feed out) ────────────────────────────

@flock_bp.route('/api/feed', methods=['GET', 'POST'])
@login_required
def api_feed():
    if request.method == 'POST':
        d = request.get_json()
        txn_type = d.get('txn_type', 'OUT').upper()
        if txn_type == 'IN' and session.get('role') == 'staff':
            return jsonify({'success': False, 'error': 'Only admins can record feed purchases (feed in)'}), 403
        bags = float(d.get('bags', 0))
        if txn_type == 'IN':
            total_cost = float(d.get('total_cost', 0))
            cost_per_bag = (total_cost / bags) if bags else 0
        else:
            cost_per_bag = 0
        t = FeedTransaction(
            txn_type=txn_type,
            batch_id=d.get('batch_id') or None,
            txn_date=parse_date(d.get('txn_date')),
            bags=bags,
            cost_per_bag=cost_per_bag,
            notes=d.get('notes', ''),
            recorded_by=session['user_id'],
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True, 'id': t.id})
    batch_id = request.args.get('batch_id')
    query = FeedTransaction.query
    if batch_id:
        query = query.filter_by(batch_id=int(batch_id))
    txns = query.order_by(FeedTransaction.txn_date.desc()).limit(150).all()
    return jsonify([t.to_dict() for t in txns])


def feed_stock_summary():
    ins = FeedTransaction.query.filter_by(txn_type='IN').all()
    outs = FeedTransaction.query.filter_by(txn_type='OUT').all()
    total_in = sum(t.bags for t in ins)
    total_out = sum(t.bags for t in outs)
    total_in_cost = sum(t.bags * t.cost_per_bag for t in ins)
    avg_cost_per_bag = (total_in_cost / total_in) if total_in else 0
    balance_bags = total_in - total_out

    window_start = date.today() - timedelta(days=30)
    recent_out = sum(t.bags for t in outs if t.txn_date and t.txn_date >= window_start)
    avg_daily_consumption = recent_out / 30
    days_remaining = (balance_bags / avg_daily_consumption) if avg_daily_consumption else None

    return {
        'balance_bags': round(balance_bags, 2),
        'total_in': total_in, 'total_out': total_out,
        'avg_cost_per_bag': round(avg_cost_per_bag, 2),
        'total_in_cost': round(total_in_cost, 2),
        'avg_daily_consumption': round(avg_daily_consumption, 2),
        'days_remaining': round(days_remaining, 1) if days_remaining is not None else None,
    }


@flock_bp.route('/api/feed/stock')
@login_required
def api_feed_stock():
    return jsonify(feed_stock_summary())


# ─── BODY WEIGHT ──────────────────────────────────────────

@flock_bp.route('/api/batches/<int:bid>/weights', methods=['GET', 'POST'])
@login_required
def api_weights(bid):
    Batch.query.get_or_404(bid)
    if request.method == 'POST':
        d = request.get_json()
        w = BodyWeight(
            batch_id=bid, weigh_date=parse_date(d.get('weigh_date')),
            size_category=d.get('size_category', 'medium'),
            avg_weight_kg=float(d.get('avg_weight_kg', 0)),
            sample_count=int(d.get('sample_count', 0)),
            notes=d.get('notes', ''), recorded_by=session['user_id'],
        )
        db.session.add(w)
        db.session.commit()
        return jsonify({'success': True, 'id': w.id})
    ws = BodyWeight.query.filter_by(batch_id=bid).order_by(BodyWeight.weigh_date.desc()).limit(60).all()
    return jsonify([w.to_dict() for w in ws])


# ─── MEDICATION ───────────────────────────────────────────

@flock_bp.route('/api/batches/<int:bid>/medications', methods=['GET', 'POST'])
@login_required
def api_medications(bid):
    Batch.query.get_or_404(bid)
    if request.method == 'POST':
        d = request.get_json()
        m = Medication(
            batch_id=bid, med_date=parse_date(d.get('med_date')),
            name=d['name'], dosage=d.get('dosage', ''),
            cost=float(d.get('cost', 0)), notes=d.get('notes', ''),
            recorded_by=session['user_id'],
        )
        db.session.add(m)
        db.session.commit()
        return jsonify({'success': True, 'id': m.id})
    ms = Medication.query.filter_by(batch_id=bid).order_by(Medication.med_date.desc()).limit(60).all()
    return jsonify([m.to_dict() for m in ms])


# ─── VACCINATION ──────────────────────────────────────────

@flock_bp.route('/api/batches/<int:bid>/vaccinations', methods=['GET', 'POST'])
@login_required
def api_vaccinations(bid):
    Batch.query.get_or_404(bid)
    if request.method == 'POST':
        d = request.get_json()
        v = Vaccination(
            batch_id=bid, vac_date=parse_date(d.get('vac_date')),
            name=d['name'], cost=float(d.get('cost', 0)), notes=d.get('notes', ''),
            recorded_by=session['user_id'],
        )
        db.session.add(v)
        db.session.commit()
        return jsonify({'success': True, 'id': v.id})
    vs = Vaccination.query.filter_by(batch_id=bid).order_by(Vaccination.vac_date.desc()).limit(60).all()
    return jsonify([v.to_dict() for v in vs])


# ─── DAILY RECORD (everything logged for one batch on one date) ──

@flock_bp.route('/api/batches/<int:bid>/daily-record')
@login_required
def api_batch_daily_record(bid):
    Batch.query.get_or_404(bid)
    rec_date = parse_date(request.args.get('date'))

    daily_log = DailyLog.query.filter_by(batch_id=bid, log_date=rec_date).first()
    data = {
        'date': rec_date.isoformat(),
        'daily_log': daily_log.to_dict() if daily_log else None,
        'feed': [t.to_dict() for t in FeedTransaction.query.filter_by(batch_id=bid, txn_date=rec_date).all()],
        'weights': [w.to_dict() for w in BodyWeight.query.filter_by(batch_id=bid, weigh_date=rec_date).all()],
        'medications': [m.to_dict() for m in Medication.query.filter_by(batch_id=bid, med_date=rec_date).all()],
        'vaccinations': [v.to_dict() for v in Vaccination.query.filter_by(batch_id=bid, vac_date=rec_date).all()],
        'egg_logs': [e.to_dict() for e in EggLog.query.filter_by(batch_id=bid, log_date=rec_date).all()],
    }
    if session.get('role') in ('admin', 'super_admin'):
        data['chicken_sales'] = [s.to_dict() for s in ChickenSale.query.filter_by(batch_id=bid, sale_date=rec_date).all()]
        data['egg_sales'] = [s.to_dict() for s in EggSale.query.filter_by(batch_id=bid, sale_date=rec_date).all()]
    return jsonify(data)
