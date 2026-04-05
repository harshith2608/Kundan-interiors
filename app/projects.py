import json
from urllib.parse import quote
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, send_file, current_app)
from flask_login import login_required, current_user
from . import db
from .models import Project, Room, Item, MasterRoom, MasterItem, WoodRate
from .decorators import admin_required

projects_bp = Blueprint('projects', __name__)

WOOD_TYPES = ['Acrylic', 'Laminates', 'Veneer']


def _get_wood_rates():
    return {r.wood_type: r.rate_per_sqft for r in WoodRate.query.all()}


def _save_project_data(project, rooms_data):
    """Delete existing rooms/items and save new ones. Returns grand_total."""
    # Remove existing rooms (cascade deletes items)
    for room in project.rooms.all():
        db.session.delete(room)
    db.session.flush()

    rates = _get_wood_rates()
    wood_areas = {}

    for rd in rooms_data:
        room_name = rd.get('name', '').strip()
        if not room_name:
            continue
        room = Room(project_id=project.id, name=room_name)
        db.session.add(room)
        db.session.flush()

        # Auto-learn room name
        if not MasterRoom.query.filter_by(name=room_name).first():
            db.session.add(MasterRoom(name=room_name))

        for id_ in rd.get('items', []):
            item_name = id_.get('name', '').strip()
            if not item_name:
                continue
            try:
                length = float(id_.get('length', 0))
                width = float(id_.get('width', 0))
            except (ValueError, TypeError):
                continue
            if length <= 0 or width <= 0:
                continue
            area = round(length * width, 4)
            wood_type = id_.get('wood_type', 'Laminates')
            if wood_type not in WOOD_TYPES:
                wood_type = 'Laminates'

            item = Item(
                room_id=room.id,
                name=item_name,
                length=length,
                width=width,
                area=area,
                wood_type=wood_type
            )
            db.session.add(item)
            wood_areas[wood_type] = wood_areas.get(wood_type, 0.0) + area

            # Auto-learn item name
            if not MasterItem.query.filter_by(name=item_name).first():
                db.session.add(MasterItem(name=item_name))

    grand_total = sum(wood_areas.get(wt, 0) * rates.get(wt, 0) for wt in WOOD_TYPES)
    return round(grand_total, 2)


@projects_bp.route('/projects')
@login_required
def list_projects():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    if current_user.is_admin:
        query = Project.query
    else:
        query = Project.query.filter_by(created_by=current_user.id)
    if search:
        query = query.filter(
            db.or_(
                Project.customer_name.ilike(f'%{search}%'),
                Project.mobile.ilike(f'%{search}%')
            )
        )
    projects = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    return render_template('projects/list.html', projects=projects, search=search, title='Quotations')


@projects_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def create_project():
    master_rooms = [r.name for r in MasterRoom.query.order_by(MasterRoom.name).all()]
    master_items = [i.name for i in MasterItem.query.order_by(MasterItem.name).all()]
    rates = _get_wood_rates()

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        rooms_json = request.form.get('rooms_data', '[]')

        errors = []
        if not customer_name:
            errors.append('Customer name is required.')
        if not mobile:
            errors.append('Mobile number is required.')
        if not mobile.lstrip('+').replace('-', '').replace(' ', '').isdigit() and mobile:
            errors.append('Mobile number must contain only digits.')

        try:
            rooms_data = json.loads(rooms_json)
        except (json.JSONDecodeError, ValueError):
            rooms_data = []
            errors.append('Form data is invalid. Please try again.')

        valid_rooms = [
            r for r in rooms_data
            if r.get('name', '').strip() and
            any(i.get('name', '').strip() for i in r.get('items', []))
        ]
        if not valid_rooms:
            errors.append('At least one room with one item is required.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('projects/form.html',
                                   title='New Quotation',
                                   master_rooms=master_rooms,
                                   master_items=master_items,
                                   rates=rates,
                                   form_data={'customer_name': customer_name,
                                              'mobile': mobile,
                                              'email': email},
                                   rooms_json=rooms_json,
                                   project=None)

        project = Project(
            customer_name=customer_name,
            mobile=mobile,
            email=email or None,
            created_by=current_user.id,
            grand_total=0.0
        )
        db.session.add(project)
        db.session.flush()

        grand_total = _save_project_data(project, rooms_data)
        project.grand_total = grand_total
        db.session.commit()

        flash('Quotation created successfully!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    return render_template('projects/form.html',
                           title='New Quotation',
                           master_rooms=master_rooms,
                           master_items=master_items,
                           rates=rates,
                           form_data={},
                           rooms_json='[]',
                           project=None)


@projects_bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        abort(403)
    rates = _get_wood_rates()
    wood_totals = project.get_wood_totals()
    wood_summary = []
    for wt in WOOD_TYPES:
        area = wood_totals.get(wt, 0.0)
        if area > 0:
            rate = rates.get(wt, 0.0)
            wood_summary.append({
                'wood_type': wt,
                'area': area,
                'rate': rate,
                'subtotal': area * rate
            })
    return render_template('projects/view.html',
                           project=project,
                           wood_summary=wood_summary,
                           title=f'Quotation – {project.customer_name}')


@projects_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        abort(403)

    master_rooms = [r.name for r in MasterRoom.query.order_by(MasterRoom.name).all()]
    master_items = [i.name for i in MasterItem.query.order_by(MasterItem.name).all()]
    rates = _get_wood_rates()

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        rooms_json = request.form.get('rooms_data', '[]')

        errors = []
        if not customer_name:
            errors.append('Customer name is required.')
        if not mobile:
            errors.append('Mobile number is required.')

        try:
            rooms_data = json.loads(rooms_json)
        except (json.JSONDecodeError, ValueError):
            rooms_data = []
            errors.append('Form data is invalid.')

        valid_rooms = [
            r for r in rooms_data
            if r.get('name', '').strip() and
            any(i.get('name', '').strip() for i in r.get('items', []))
        ]
        if not valid_rooms:
            errors.append('At least one room with one item is required.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            # Build existing rooms JSON for re-render
            existing_json = _build_rooms_json(project)
            return render_template('projects/form.html',
                                   title='Edit Quotation',
                                   master_rooms=master_rooms,
                                   master_items=master_items,
                                   rates=rates,
                                   form_data={'customer_name': customer_name,
                                              'mobile': mobile, 'email': email},
                                   rooms_json=rooms_json,
                                   project=project)

        project.customer_name = customer_name
        project.mobile = mobile
        project.email = email or None
        grand_total = _save_project_data(project, rooms_data)
        project.grand_total = grand_total
        db.session.commit()

        flash('Quotation updated successfully!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))

    existing_json = _build_rooms_json(project)
    return render_template('projects/form.html',
                           title='Edit Quotation',
                           master_rooms=master_rooms,
                           master_items=master_items,
                           rates=rates,
                           form_data={
                               'customer_name': project.customer_name,
                               'mobile': project.mobile,
                               'email': project.email or ''
                           },
                           rooms_json=existing_json,
                           project=project)


def _build_rooms_json(project):
    rooms_data = []
    for room in project.rooms.all():
        room_dict = {
            'name': room.name,
            'items': [
                {
                    'name': item.name,
                    'length': item.length,
                    'width': item.width,
                    'wood_type': item.wood_type,
                    'area': item.area
                }
                for item in room.items.all()
            ]
        }
        rooms_data.append(room_dict)
    return json.dumps(rooms_data)


@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash(f'Quotation for {project.customer_name} deleted.', 'success')
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects/<int:project_id>/pdf')
@login_required
def download_pdf(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        abort(403)
    from .pdf_utils import generate_pdf
    pdf_buffer = generate_pdf(project)
    filename = f"Quotation_{project.customer_name.replace(' ', '_')}_{project.id}.pdf"
    # as_attachment=False  →  Content-Disposition: inline
    # iOS Safari opens the PDF in its built-in viewer (with Share ↑ button).
    # Desktop browsers open in their PDF viewer; user can save from there.
    return send_file(pdf_buffer, as_attachment=False,
                     download_name=filename, mimetype='application/pdf')


@projects_bp.route('/projects/<int:project_id>/whatsapp')
@login_required
def whatsapp_share(project_id):
    from flask import redirect as flask_redirect
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        abort(403)

    rates = _get_wood_rates()
    wood_totals = project.get_wood_totals()

    lines = [
        f"Hello {project.customer_name}! 👋",
        f"",
        f"Thank you for considering *Kundan's Interiors* for your home.",
        f"Here is your interior design quotation summary:",
        f"",
        f"📋 *Quotation #{project.id}*",
        f"📅 Date: {project.created_at.strftime('%d %b %Y')}",
        f"",
        f"*Room-wise Breakdown:*"
    ]
    def _ft_in(d):
        feet = int(d); inch = round((d - feet) * 12)
        if inch == 12: feet += 1; inch = 0
        return f"{feet}ft" if inch == 0 else f"{feet}ft {inch}in"

    for room in project.rooms.all():
        lines.append(f"\n🏠 *{room.name}*")
        for item in room.items.all():
            lines.append(f"  • {item.name}: {_ft_in(item.length)} × {_ft_in(item.width)} = {item.area:.2f} sqft ({item.wood_type})")

    lines += ["", "*Material Summary:*"]
    for wt in WOOD_TYPES:
        area = wood_totals.get(wt, 0.0)
        if area > 0:
            rate = rates.get(wt, 0.0)
            subtotal = area * rate
            lines.append(f"  • {wt}: {area:.2f} sqft × Rs.{rate:,.0f} = Rs.{subtotal:,.0f}")

    lines += [
        "",
        f"💰 *Grand Total: Rs.{project.grand_total:,.2f}*",
        "",
        "_Please find the detailed PDF quotation attached._",
        "",
        "Thank you for choosing Kundan's Interiors! 🏡",
        "We look forward to transforming your space."
    ]

    message = '\n'.join(lines)
    mobile = project.mobile.lstrip('+').replace(' ', '').replace('-', '')
    if not mobile.startswith('91') and len(mobile) == 10:
        mobile = '91' + mobile
    wa_url = f"https://wa.me/{mobile}?text={quote(message)}"
    return flask_redirect(wa_url)
