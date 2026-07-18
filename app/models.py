from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

EGGS_PER_CRATE = 30

# ─── USERS ────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='staff')  # super_admin / admin / staff
    phone = db.Column(db.String(20), default='')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {'id': self.id, 'full_name': self.full_name, 'username': self.username,
                'role': self.role, 'phone': self.phone, 'active': self.active}


# ─── FLOCK / BATCH ────────────────────────────────────────

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    date_purchased = db.Column(db.Date, default=date.today)
    quantity_ordered = db.Column(db.Integer, default=0)
    quantity_received = db.Column(db.Integer, default=0)
    amount_paid = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='growing')  # growing / laying / closed
    laying_start_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(300), default='')
    active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    daily_logs = db.relationship('DailyLog', backref='batch', lazy=True, order_by='DailyLog.log_date.desc()')
    feed_txns = db.relationship('FeedTransaction', backref='batch', lazy=True)
    weights = db.relationship('BodyWeight', backref='batch', lazy=True)
    medications = db.relationship('Medication', backref='batch', lazy=True)
    vaccinations = db.relationship('Vaccination', backref='batch', lazy=True)
    chicken_sales = db.relationship('ChickenSale', backref='batch', lazy=True)
    egg_logs = db.relationship('EggLog', backref='batch', lazy=True)
    egg_sales = db.relationship('EggSale', backref='batch', lazy=True)

    @property
    def cost_per_bird(self):
        return (self.amount_paid / self.quantity_received) if self.quantity_received else 0

    @property
    def total_mortality(self):
        return sum(d.mortality for d in self.daily_logs)

    @property
    def total_sold(self):
        return sum(s.quantity for s in self.chicken_sales)

    @property
    def quantity_current(self):
        return max(0, self.quantity_received - self.total_mortality - self.total_sold)

    @property
    def mortality_rate_pct(self):
        return round((self.total_mortality / self.quantity_received) * 100, 2) if self.quantity_received else 0

    def to_dict(self):
        return {
            'id': self.id, 'label': self.label,
            'date_purchased': self.date_purchased.isoformat() if self.date_purchased else None,
            'quantity_ordered': self.quantity_ordered, 'quantity_received': self.quantity_received,
            'amount_paid': self.amount_paid, 'cost_per_bird': round(self.cost_per_bird, 2),
            'status': self.status,
            'laying_start_date': self.laying_start_date.isoformat() if self.laying_start_date else None,
            'notes': self.notes, 'active': self.active,
            'total_mortality': self.total_mortality, 'total_sold': self.total_sold,
            'quantity_current': self.quantity_current, 'mortality_rate_pct': self.mortality_rate_pct,
        }


class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    log_date = db.Column(db.Date, default=date.today)
    mortality = db.Column(db.Integer, default=0)
    water_liters = db.Column(db.Float, default=0)
    remarks = db.Column(db.String(400), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'batch_id': self.batch_id,
                'log_date': self.log_date.isoformat() if self.log_date else None,
                'mortality': self.mortality, 'water_liters': self.water_liters,
                'remarks': self.remarks}


class FeedTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txn_type = db.Column(db.String(3), nullable=False)  # IN / OUT
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    txn_date = db.Column(db.Date, default=date.today)
    bags = db.Column(db.Float, default=0)
    cost_per_bag = db.Column(db.Float, default=0)  # only relevant for IN
    notes = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'txn_type': self.txn_type, 'batch_id': self.batch_id,
                'batch_label': self.batch.label if self.batch else '',
                'txn_date': self.txn_date.isoformat() if self.txn_date else None,
                'bags': self.bags, 'cost_per_bag': self.cost_per_bag,
                'total_cost': round(self.bags * self.cost_per_bag, 2), 'notes': self.notes}


class BodyWeight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    weigh_date = db.Column(db.Date, default=date.today)
    size_category = db.Column(db.String(10), default='medium')  # small / medium / big
    avg_weight_kg = db.Column(db.Float, default=0)
    sample_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'batch_id': self.batch_id,
                'weigh_date': self.weigh_date.isoformat() if self.weigh_date else None,
                'size_category': self.size_category, 'avg_weight_kg': self.avg_weight_kg,
                'sample_count': self.sample_count, 'notes': self.notes}


class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    med_date = db.Column(db.Date, default=date.today)
    name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), default='')
    cost = db.Column(db.Float, default=0)
    notes = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'batch_id': self.batch_id,
                'med_date': self.med_date.isoformat() if self.med_date else None,
                'name': self.name, 'dosage': self.dosage, 'cost': self.cost, 'notes': self.notes}


class Vaccination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    vac_date = db.Column(db.Date, default=date.today)
    name = db.Column(db.String(150), nullable=False)
    cost = db.Column(db.Float, default=0)
    notes = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'batch_id': self.batch_id,
                'vac_date': self.vac_date.isoformat() if self.vac_date else None,
                'name': self.name, 'cost': self.cost, 'notes': self.notes}


# ─── EGGS ─────────────────────────────────────────────────

class Pen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)

    batch = db.relationship('Batch', foreign_keys=[batch_id])

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'batch_id': self.batch_id,
                'batch_label': self.batch.label if self.batch else '', 'active': self.active}


class EggLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey('pen.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    log_date = db.Column(db.Date, default=date.today)
    crates_collected = db.Column(db.Float, default=0)
    cracked_eggs = db.Column(db.Integer, default=0)
    cracked_remarks = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pen = db.relationship('Pen', backref='egg_logs')

    def to_dict(self):
        return {'id': self.id, 'pen_id': self.pen_id, 'pen_name': self.pen.name if self.pen else '',
                'batch_id': self.batch_id, 'log_date': self.log_date.isoformat() if self.log_date else None,
                'crates_collected': self.crates_collected, 'cracked_eggs': self.cracked_eggs,
                'cracked_remarks': self.cracked_remarks}


# ─── SALES ────────────────────────────────────────────────

class ChickenSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(20), unique=True, nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    sale_date = db.Column(db.Date, default=date.today)
    buyer_name = db.Column(db.String(150), default='')
    buyer_phone = db.Column(db.String(20), default='')
    quantity = db.Column(db.Integer, default=0)
    price_per_bird = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.String(300), default='')
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('User', foreign_keys=[staff_id])

    def to_dict(self):
        return {'id': self.id, 'receipt_no': self.receipt_no, 'batch_id': self.batch_id,
                'batch_label': self.batch.label if self.batch else '',
                'sale_date': self.sale_date.isoformat() if self.sale_date else None,
                'buyer_name': self.buyer_name, 'buyer_phone': self.buyer_phone,
                'quantity': self.quantity, 'price_per_bird': self.price_per_bird,
                'total_amount': self.total_amount, 'notes': self.notes,
                'staff': self.staff.full_name if self.staff else ''}


class EggSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(20), unique=True, nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    sale_date = db.Column(db.Date, default=date.today)
    buyer_name = db.Column(db.String(150), default='')
    buyer_phone = db.Column(db.String(20), default='')
    crates_sold = db.Column(db.Float, default=0)
    price_per_crate = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.String(300), default='')
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('User', foreign_keys=[staff_id])

    def to_dict(self):
        return {'id': self.id, 'receipt_no': self.receipt_no, 'batch_id': self.batch_id,
                'batch_label': self.batch.label if self.batch else 'Mixed / Unassigned',
                'sale_date': self.sale_date.isoformat() if self.sale_date else None,
                'buyer_name': self.buyer_name, 'buyer_phone': self.buyer_phone,
                'crates_sold': self.crates_sold, 'price_per_crate': self.price_per_crate,
                'total_amount': self.total_amount, 'notes': self.notes,
                'staff': self.staff.full_name if self.staff else ''}


# ─── TOOLS / EQUIPMENT ────────────────────────────────────

class ToolCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    tools = db.relationship('Tool', backref='category', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'tool_count': len(self.tools)}


class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tool_category.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, default=1)
    unit_cost = db.Column(db.Float, default=0)
    date_bought = db.Column(db.Date, default=date.today)
    notes = db.Column(db.String(300), default='')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_cost(self): return self.quantity * self.unit_cost

    def to_dict(self):
        return {'id': self.id, 'category_id': self.category_id,
                'category_name': self.category.name if self.category else '',
                'name': self.name, 'quantity': self.quantity, 'unit_cost': self.unit_cost,
                'total_cost': self.total_cost,
                'date_bought': self.date_bought.isoformat() if self.date_bought else None,
                'notes': self.notes}


# ─── EXPENSES ─────────────────────────────────────────────

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exp_date = db.Column(db.Date, default=date.today)
    category = db.Column(db.String(50), default='Other')
    description = db.Column(db.String(300), default='')
    amount = db.Column(db.Float, default=0)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'exp_date': self.exp_date.isoformat() if self.exp_date else None,
                'category': self.category, 'description': self.description, 'amount': self.amount}


# ─── SUPPLIES (charcoal, sawdust, and other bagged consumables) ──

class SupplyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    low_stock_threshold = db.Column(db.Float, default=5)
    active = db.Column(db.Boolean, default=True)

    txns = db.relationship('SupplyTransaction', backref='item', lazy=True)

    @property
    def balance_bags(self):
        ins = sum(t.quantity for t in self.txns if t.txn_type == 'IN')
        outs = sum(t.quantity for t in self.txns if t.txn_type == 'OUT')
        return ins - outs

    @property
    def avg_cost_per_bag(self):
        ins = [t for t in self.txns if t.txn_type == 'IN']
        total_bags = sum(t.quantity for t in ins)
        total_cost = sum(t.quantity * t.cost_per_unit for t in ins)
        return (total_cost / total_bags) if total_bags else 0

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'low_stock_threshold': self.low_stock_threshold,
                'balance_bags': round(self.balance_bags, 2),
                'avg_cost_per_bag': round(self.avg_cost_per_bag, 2),
                'active': self.active}


class SupplyTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('supply_item.id'), nullable=False)
    txn_type = db.Column(db.String(3), nullable=False)  # IN / OUT
    txn_date = db.Column(db.Date, default=date.today)
    quantity = db.Column(db.Float, default=0)
    cost_per_unit = db.Column(db.Float, default=0)  # only relevant for IN
    notes = db.Column(db.String(300), default='')
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'item_id': self.item_id,
                'item_name': self.item.name if self.item else '',
                'txn_type': self.txn_type,
                'txn_date': self.txn_date.isoformat() if self.txn_date else None,
                'quantity': self.quantity, 'cost_per_unit': self.cost_per_unit,
                'total_cost': round(self.quantity * self.cost_per_unit, 2) if self.txn_type == 'IN' else 0,
                'notes': self.notes}


# ─── SETTINGS ─────────────────────────────────────────────

class FarmSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farm_name = db.Column(db.String(150), default='Gidoyel Agro Alide And Services')
    low_feed_threshold_bags = db.Column(db.Float, default=10)
    high_mortality_pct_alert = db.Column(db.Float, default=2.0)

    def to_dict(self):
        return {'farm_name': self.farm_name, 'low_feed_threshold_bags': self.low_feed_threshold_bags,
                'high_mortality_pct_alert': self.high_mortality_pct_alert}

    @staticmethod
    def get():
        s = FarmSetting.query.first()
        if not s:
            s = FarmSetting()
            db.session.add(s)
            db.session.commit()
        return s
