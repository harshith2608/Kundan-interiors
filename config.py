import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Railway/Render supply DATABASE_URL as postgres:// but SQLAlchemy needs postgresql://
    _db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'kundans_interiors.db')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL connection pooling (ignored for SQLite)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size':    10,
        'max_overflow': 20,
        'pool_recycle': 1800,   # recycle connections every 30 min
        'pool_pre_ping': True,  # verify connection is alive before use
    }

    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True
    # Relax cookie security for local HTTP development
    SESSION_COOKIE_SECURE   = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE   = True   # HTTPS only
    SESSION_COOKIE_HTTPONLY = True   # no JS access
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig
}
