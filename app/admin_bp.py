from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from . import db
from .models import User, Project, Item, Room, WoodRate, MasterRoom, MasterItem
from .forms import CreateUserForm, WoodRateForm, ChangePasswordForm
from .decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

WOOD_TYPES = ['Acrylic', 'Laminates', 'Veneer']


@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)


@admin_bp.route('/dashboard')
def dashboard():
    # Employee performance stats
    employee_stats = (
        db.session.query(
            User.id,
            User.username,
            func.count(Project.id).label('project_count'),
            func.coalesce(func.sum(Project.grand_total), 0).label('total_value')
        )
        .outerjoin(Project, Project.created_by == User.id)
        .filter(User.role == 'employee')
        .group_by(User.id, User.username)
        .all()
    )

    # Wood type distribution (total area per wood type)
    wood_dist = (
        db.session.query(Item.wood_type, func.sum(Item.area).label('total_area'))
        .group_by(Item.wood_type)
        .all()
    )
    wood_labels = [w.wood_type for w in wood_dist]
    wood_data = [round(w.total_area, 2) for w in wood_dist]

    # Room type distribution (top 8)
    room_dist = (
        db.session.query(Room.name, func.count(Room.id).label('count'))
        .group_by(Room.name)
        .order_by(func.count(Room.id).desc())
        .limit(8)
        .all()
    )
    room_labels = [r.name for r in room_dist]
    room_data = [r.count for r in room_dist]

    # Overall stats
    total_projects = Project.query.count()
    total_value = db.session.query(func.coalesce(func.sum(Project.grand_total), 0)).scalar()
    total_customers = db.session.query(func.count(func.distinct(Project.mobile))).scalar()
    total_employees = User.query.filter_by(role='employee').count()

    return render_template(
        'admin/dashboard.html',
        title='Admin Dashboard',
        employee_stats=employee_stats,
        wood_labels=wood_labels,
        wood_data=wood_data,
        room_labels=room_labels,
        room_data=room_data,
        total_projects=total_projects,
        total_value=total_value,
        total_customers=total_customers,
        total_employees=total_employees
    )


@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    form = CreateUserForm()
    return render_template('admin/users.html', title='User Management',
                           users=all_users, form=form)


@admin_bp.route('/users/new', methods=['POST'])
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data.strip()).first()
        if existing:
            flash('Username already exists.', 'danger')
        else:
            user = User(
                username=form.username.data.strip(),
                password_hash=generate_password_hash(form.password.data, method='pbkdf2:sha256'),
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            flash(f'User "{user.username}" created successfully.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last admin account.', 'danger')
        return redirect(url_for('admin.users'))
    # Re-assign projects to current admin before deleting
    Project.query.filter_by(created_by=user.id).update({'created_by': current_user.id})
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" deleted. Their projects were reassigned to you.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/rename', methods=['POST'])
def rename_user(user_id):
    user = User.query.get_or_404(user_id)
    new_username = request.form.get('new_username', '').strip()
    if not new_username:
        flash('Username cannot be empty.', 'danger')
    elif User.query.filter(User.username == new_username, User.id != user_id).first():
        flash(f'Username "{new_username}" is already taken.', 'danger')
    else:
        old_name = user.username
        user.username = new_username
        db.session.commit()
        flash(f'Username changed from "{old_name}" to "{new_username}".', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/change-password', methods=['POST'])
def change_user_password(user_id):
    user = User.query.get_or_404(user_id)
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
        db.session.commit()
        flash(f'Password for "{user.username}" updated.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/rates', methods=['GET', 'POST'])
def rates():
    form = WoodRateForm()
    wood_rates = {r.wood_type: r for r in WoodRate.query.all()}

    if form.validate_on_submit():
        updates = {
            'Acrylic': form.acrylic_rate.data,
            'Laminates': form.laminates_rate.data,
            'Veneer': form.veneer_rate.data,
        }
        for wt, rate in updates.items():
            wr = wood_rates.get(wt)
            if wr:
                wr.rate_per_sqft = rate
            else:
                db.session.add(WoodRate(wood_type=wt, rate_per_sqft=rate))
        db.session.commit()
        flash('Wood rates updated successfully.', 'success')
        return redirect(url_for('admin.rates'))

    if wood_rates:
        form.acrylic_rate.data = wood_rates.get('Acrylic', WoodRate()).rate_per_sqft
        form.laminates_rate.data = wood_rates.get('Laminates', WoodRate()).rate_per_sqft
        form.veneer_rate.data = wood_rates.get('Veneer', WoodRate()).rate_per_sqft

    return render_template('admin/rates.html', title='Manage Rates',
                           form=form, wood_rates=wood_rates)


@admin_bp.route('/projects')
def all_projects():
    return redirect(url_for('projects.list_projects'))
