from flask import Blueprint, redirect, url_for, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('projects.list_projects'))


@main_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@main_bp.app_errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404
