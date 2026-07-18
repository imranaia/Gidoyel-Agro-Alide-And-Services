import os
from flask import Flask
from app.models import db, User, FarmSetting


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'farm-system-dev-secret-change-me')

    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    if not db_url:
        if os.environ.get('VERCEL'):
            # Vercel's filesystem is read-only except /tmp, and /tmp doesn't
            # persist between cold starts - fine for testing, not for real data.
            db_url = 'sqlite:////tmp/farm.db'
        else:
            db_url = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'farm.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from app.auth import auth_bp
    from app.flock import flock_bp
    from app.eggs import eggs_bp
    from app.sales import sales_bp
    from app.inventory import inventory_bp
    from app.finance import finance_bp
    from app.dashboard import dashboard_bp
    from app.staff import staff_bp
    from app.supplies import supplies_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(flock_bp)
    app.register_blueprint(eggs_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(supplies_bp)

    return app


def seed():
    """Create the Super Admin account and default farm settings on first run only."""
    if User.query.first():
        return
    admin = User(full_name='Super Admin', username='admin', role='super_admin', phone='')
    admin.set_password('admin1234')
    db.session.add(admin)
    FarmSetting.get()
    db.session.commit()
    print("Farm system ready. Super Admin account created.")
    print("   Username : admin")
    print("   Password : admin1234")
    print("   Please log in and change your password via My Profile.")
