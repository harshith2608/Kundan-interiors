from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app(config_name='default'):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    from .projects import projects_bp
    from .admin_bp import admin_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.template_filter('ft_in')
    def ft_in_filter(decimal_ft):
        """Convert decimal feet to 'X ft Y in' string."""
        try:
            decimal_ft = float(decimal_ft or 0)
        except (ValueError, TypeError):
            return '—'
        feet = int(decimal_ft)
        inches = round((decimal_ft - feet) * 12)
        if inches == 12:
            feet += 1
            inches = 0
        if inches == 0:
            return f"{feet} ft"
        return f"{feet} ft {inches} in"

    @app.context_processor
    def inject_globals():
        return {'now': datetime.utcnow()}

    with app.app_context():
        db.create_all()
        _seed_database()

    return app


def _seed_database():
    from .models import User, WoodRate, MasterRoom, MasterItem
    from werkzeug.security import generate_password_hash

    # Create default admin if none exists
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

    # Seed wood rates if empty
    if not WoodRate.query.first():
        rates = [
            WoodRate(wood_type='Acrylic', rate_per_sqft=1200.0),
            WoodRate(wood_type='Laminates', rate_per_sqft=800.0),
            WoodRate(wood_type='Veneer', rate_per_sqft=1500.0),
        ]
        db.session.bulk_save_objects(rates)
        db.session.commit()

    # Seed master rooms if empty
    if not MasterRoom.query.first():
        rooms = [
            'Living Room', 'Master Bedroom', 'Bedroom', 'Guest Bedroom',
            'Kitchen', 'Dining Room', 'Study Room', 'Pooja Room',
            'Bathroom', 'Balcony', 'Entrance Foyer', 'Kids Room',
        ]
        db.session.bulk_save_objects([MasterRoom(name=r) for r in rooms])
        db.session.commit()

    # Seed master items if empty
    if not MasterItem.query.first():
        items = [
            'Wardrobe', 'TV Unit', 'Kitchen Cabinet', 'Study Table',
            'Shoe Rack', 'Crockery Unit', 'False Ceiling', 'Partition',
            'Bed Box', 'Dressing Table', 'Loft', 'Overhead Cabinet',
            'Base Cabinet', 'Island Counter', 'Display Unit', 'Pooja Unit',
            'Vanity Cabinet', 'Wall Paneling', 'Headboard', 'Side Table',
        ]
        db.session.bulk_save_objects([MasterItem(name=i) for i in items])
        db.session.commit()
