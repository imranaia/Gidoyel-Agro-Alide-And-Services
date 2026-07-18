from datetime import datetime, date
from flask import Blueprint, request, jsonify, session
from app.models import db, Pen, EggLog, EggSale
from app.auth import login_required

eggs_bp = Blueprint('eggs', __name__)


def parse_date(s, default=None):
    if not s:
        return default or date.today()
    return datetime.strptime(s, '%Y-%m-%d').date()


# ─── PENS ─────────────────────────────────────────────────

@eggs_bp.route('/api/pens', methods=['GET', 'POST'])
@login_required
def api_pens():
    if request.method == 'POST':
        d = request.get_json()
        p = Pen(name=d['name'], batch_id=d.get('batch_id') or None)
        db.session.add(p)
        db.session.commit()
        return jsonify({'success': True, 'id': p.id})
    pens = Pen.query.filter_by(active=True).order_by(Pen.name).all()
    return jsonify([p.to_dict() for p in pens])


@eggs_bp.route('/api/pens/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def api_pen(pid):
    p = Pen.query.get_or_404(pid)
    if request.method == 'DELETE':
        p.active = False
        db.session.commit()
        return jsonify({'success': True})
    d = request.get_json()
    if 'name' in d:
        p.name = d['name']
    if 'batch_id' in d:
        p.batch_id = d['batch_id'] or None
    db.session.commit()
    return jsonify({'success': True})


# ─── EGG LOGS ─────────────────────────────────────────────

@eggs_bp.route('/api/egg-logs', methods=['GET', 'POST'])
@login_required
def api_egg_logs():
    if request.method == 'POST':
        d = request.get_json()
        pen = Pen.query.get_or_404(int(d['pen_id']))
        e = EggLog(
            pen_id=pen.id, batch_id=pen.batch_id,
            log_date=parse_date(d.get('log_date')),
            crates_collected=float(d.get('crates_collected', 0)),
            cracked_eggs=int(d.get('cracked_eggs', 0)),
            cracked_remarks=d.get('cracked_remarks', ''),
            recorded_by=session['user_id'],
        )
        db.session.add(e)
        db.session.commit()
        return jsonify({'success': True, 'id': e.id})
    pen_id = request.args.get('pen_id')
    query = EggLog.query
    if pen_id:
        query = query.filter_by(pen_id=int(pen_id))
    logs = query.order_by(EggLog.log_date.desc()).limit(120).all()
    return jsonify([l.to_dict() for l in logs])


@eggs_bp.route('/api/eggs/stock')
@login_required
def api_egg_stock():
    total_collected = sum(l.crates_collected for l in EggLog.query.all())
    total_sold = sum(s.crates_sold for s in EggSale.query.all())
    total_cracked_eggs = sum(l.cracked_eggs for l in EggLog.query.all())
    return jsonify({
        'crates_collected': round(total_collected, 2),
        'crates_sold': round(total_sold, 2),
        'crates_in_stock': round(max(0, total_collected - total_sold), 2),
        'cracked_eggs_total': total_cracked_eggs,
    })
