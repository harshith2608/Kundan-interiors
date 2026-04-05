from datetime import datetime
from flask_login import UserMixin
from . import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='creator', lazy='dynamic',
                               foreign_keys='Project.created_by')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    grand_total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rooms = db.relationship('Room', backref='project', lazy='dynamic',
                            cascade='all, delete-orphan')

    def get_wood_totals(self):
        """Returns dict of {wood_type: total_area}"""
        totals = {}
        for room in self.rooms:
            for item in room.items:
                totals[item.wood_type] = totals.get(item.wood_type, 0.0) + item.area
        return totals

    def __repr__(self):
        return f'<Project {self.id}: {self.customer_name}>'


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    items = db.relationship('Item', backref='room', lazy='dynamic',
                            cascade='all, delete-orphan')

    @property
    def total_area(self):
        return sum(item.area for item in self.items)

    def __repr__(self):
        return f'<Room {self.name}>'


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    area = db.Column(db.Float, nullable=False)
    wood_type = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Item {self.name}>'


class MasterRoom(db.Model):
    __tablename__ = 'master_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<MasterRoom {self.name}>'


class MasterItem(db.Model):
    __tablename__ = 'master_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<MasterItem {self.name}>'


class WoodRate(db.Model):
    __tablename__ = 'wood_rates'
    id = db.Column(db.Integer, primary_key=True)
    wood_type = db.Column(db.String(50), unique=True, nullable=False)
    rate_per_sqft = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<WoodRate {self.wood_type}: {self.rate_per_sqft}>'
