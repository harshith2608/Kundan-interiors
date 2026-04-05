from flask import Blueprint, jsonify
from flask_login import login_required
from .models import MasterRoom, MasterItem, WoodRate

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/master-rooms')
@login_required
def master_rooms():
    rooms = MasterRoom.query.order_by(MasterRoom.name).all()
    return jsonify([r.name for r in rooms])


@api_bp.route('/master-items')
@login_required
def master_items():
    items = MasterItem.query.order_by(MasterItem.name).all()
    return jsonify([i.name for i in items])


@api_bp.route('/wood-rates')
@login_required
def wood_rates():
    rates = WoodRate.query.all()
    return jsonify({r.wood_type: r.rate_per_sqft for r in rates})
