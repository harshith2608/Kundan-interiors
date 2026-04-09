import json
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, send_file, current_app)
from flask_login import login_required, current_user
from . import db
from .models import (Project, Room, Item, MasterRoom, MasterItem, WoodRate,
                     ProjectEditLog, ProjectAccess, User, AppSetting, Payment)
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

        # Auto-learn room name (case-insensitive dedup)
        if not MasterRoom.query.filter(MasterRoom.name.ilike(room_name)).first():
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

            # Auto-learn item name (case-insensitive dedup)
            if not MasterItem.query.filter(MasterItem.name.ilike(item_name)).first():
                db.session.add(MasterItem(name=item_name))

    grand_total = sum(wood_areas.get(wt, 0) * rates.get(wt, 0) for wt in WOOD_TYPES)
    return round(grand_total, 2)


@projects_bp.route('/projects')
@login_required
def list_projects():
    # Purge drafts older than 48 hours
    cutoff = datetime.utcnow() - timedelta(hours=48)
    old_drafts = Project.query.filter(
        Project.status == 'draft',
        Project.updated_at < cutoff
    ).all()
    for d in old_drafts:
        db.session.delete(d)
    if old_drafts:
        db.session.commit()

    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    if current_user.is_admin:
        query = Project.query
    else:
        shared_ids = db.session.query(ProjectAccess.project_id).filter_by(user_id=current_user.id)
        query = Project.query.filter(
            db.or_(Project.created_by == current_user.id, Project.id.in_(shared_ids))
        )
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

    # Admin extras: employee list + per-project access map for the modal
    employees = []
    access_map = {}
    if current_user.is_admin:
        employees = User.query.filter_by(role='employee').order_by(User.username).all()
        page_ids = [p.id for p in projects.items]
        rows = ProjectAccess.query.filter(ProjectAccess.project_id.in_(page_ids)).all()
        for row in rows:
            access_map.setdefault(row.project_id, []).append(row.user_id)

    employees_json = [{'id': e.id, 'username': e.username} for e in employees]
    return render_template('projects/list.html', projects=projects, search=search,
                           title='Quotations', employees=employees,
                           employees_json=employees_json, access_map=access_map)


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
        address = request.form.get('address', '').strip()
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
                                              'email': email,
                                              'address': address},
                                   rooms_json=rooms_json,
                                   project=None)

        # If JS auto-saved a draft, promote it to complete instead of creating new
        draft_id = request.form.get('draft_id', '').strip()
        project = None
        if draft_id:
            project = Project.query.get(int(draft_id))
            if not project or project.created_by != current_user.id or project.status != 'draft':
                project = None

        if project:
            project.customer_name = customer_name
            project.mobile = mobile
            project.email = email or None
            project.address = address or None
        else:
            project = Project(
                customer_name=customer_name,
                mobile=mobile,
                email=email or None,
                address=address or None,
                created_by=current_user.id,
                grand_total=0.0
            )
            db.session.add(project)
            db.session.flush()

        grand_total = _save_project_data(project, rooms_data)
        project.grand_total = grand_total
        project.status = 'complete'
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
        if not ProjectAccess.query.filter_by(project_id=project_id, user_id=current_user.id).first():
            abort(403)
    # Drafts have no content to view — send to edit form to complete them
    if project.status == 'draft':
        flash('This quotation is still in progress. Complete and save it.', 'warning')
        return redirect(url_for('projects.edit_project', project_id=project.id))
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
    edit_logs = (ProjectEditLog.query
                 .filter_by(project_id=project.id)
                 .order_by(ProjectEditLog.edited_at.desc())
                 .all())
    payments = (Payment.query
                .filter_by(project_id=project.id)
                .order_by(Payment.recorded_at.desc())
                .all())
    total_paid = sum(p.amount for p in payments)
    balance    = max(project.grand_total - total_paid, 0)
    settings   = {k: AppSetting.get(k, '')
                  for k in ['upi_id', 'bank_name', 'account_name',
                             'account_number', 'ifsc_code', 'razorpay_key_id']}
    return render_template('projects/view.html',
                           project=project,
                           wood_summary=wood_summary,
                           edit_logs=edit_logs,
                           payments=payments,
                           total_paid=total_paid,
                           balance=balance,
                           settings=settings,
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
        address = request.form.get('address', '').strip()
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

        was_draft = project.status == 'draft'
        project.customer_name = customer_name
        project.mobile = mobile
        project.email = email or None
        project.address = address or None
        grand_total = _save_project_data(project, rooms_data)
        project.grand_total = grand_total
        project.status = 'complete'
        if not was_draft:
            db.session.add(ProjectEditLog(project_id=project.id, edited_by=current_user.id))
        db.session.commit()

        flash('Quotation saved successfully!' if was_draft else 'Quotation updated successfully!', 'success')
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
                               'email': project.email or '',
                               'address': project.address or ''
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


@projects_bp.route('/projects/<int:project_id>/access', methods=['POST'])
@login_required
@admin_required
def set_project_access(project_id):
    project = Project.query.get_or_404(project_id)
    selected_ids = set(int(uid) for uid in request.form.getlist('user_ids'))

    # Replace all existing access entries for this project
    ProjectAccess.query.filter_by(project_id=project_id).delete()
    for uid in selected_ids:
        user = User.query.get(uid)
        if user and user.role == 'employee':
            db.session.add(ProjectAccess(
                project_id=project_id,
                user_id=uid,
                granted_by=current_user.id
            ))
    db.session.commit()
    count = len(selected_ids)
    flash(f'Access updated — {count} employee{"s" if count != 1 else ""} can now view this quotation.', 'success')
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash(f'Quotation for {project.customer_name} deleted.', 'success')
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/projects/<int:project_id>/payments/add', methods=['POST'])
@login_required
@admin_required
def add_payment(project_id):
    project = Project.query.get_or_404(project_id)
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        amount = 0
    if amount <= 0:
        flash('Please enter a valid payment amount.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))
    note = request.form.get('note', '').strip()
    db.session.add(Payment(
        project_id=project_id,
        amount=amount,
        note=note or None,
        recorded_by=current_user.id
    ))
    db.session.commit()
    flash(f'Payment of ₹{amount:,.2f} recorded successfully.', 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))


@projects_bp.route('/projects/<int:project_id>/payments/<int:payment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_payment(project_id, payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if payment.project_id != project_id:
        abort(404)
    db.session.delete(payment)
    db.session.commit()
    flash('Payment record removed.', 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))


@projects_bp.route('/projects/<int:project_id>/payment-link', methods=['POST'])
@login_required
def generate_payment_link(project_id):
    from flask import jsonify
    import urllib.request, urllib.error
    import json as _json, base64

    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        if not ProjectAccess.query.filter_by(project_id=project_id, user_id=current_user.id).first():
            return jsonify({'error': 'Access denied.'}), 403

    api_key    = AppSetting.get('razorpay_key_id', '')
    api_secret = AppSetting.get('razorpay_key_secret', '')
    if not api_key or not api_secret:
        return jsonify({'error': 'Razorpay is not configured. Ask admin to add API keys in Payment Settings.'}), 400

    payments   = Payment.query.filter_by(project_id=project_id).all()
    total_paid = sum(p.amount for p in payments)
    remaining  = max(project.grand_total - total_paid, 0)
    if remaining <= 0:
        return jsonify({'error': 'This quotation is fully paid — no outstanding balance.'}), 400

    mobile_clean = project.mobile.lstrip('+').replace(' ', '').replace('-', '')
    if not mobile_clean.startswith('91') and len(mobile_clean) == 10:
        mobile_clean = '91' + mobile_clean

    payload = _json.dumps({
        'amount': int(remaining * 100),
        'currency': 'INR',
        'accept_partial': True,
        'description': f"Kundan's Interiors – Quotation #{project.id} for {project.customer_name}",
        'customer': {'name': project.customer_name, 'contact': '+' + mobile_clean},
        'notify': {'sms': True, 'email': bool(project.email)},
        'reminder_enable': True
    }).encode()

    credentials = base64.b64encode(f'{api_key}:{api_secret}'.encode()).decode()
    req = urllib.request.Request(
        'https://api.razorpay.com/v1/payment_links',
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Basic {credentials}'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
            return jsonify({'payment_link': data.get('short_url')})
    except urllib.error.HTTPError as e:
        err_body = _json.loads(e.read())
        return jsonify({'error': err_body.get('error', {}).get('description', 'Razorpay error.')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/projects/<int:project_id>/pdf')
@login_required
def download_pdf(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        if not ProjectAccess.query.filter_by(project_id=project_id, user_id=current_user.id).first():
            abort(403)
    from .pdf_utils import generate_pdf
    pay_settings = {k: AppSetting.get(k, '')
                    for k in ['upi_id', 'bank_name', 'account_name', 'account_number', 'ifsc_code']}
    payments_list = Payment.query.filter_by(project_id=project_id).all()
    total_paid = sum(p.amount for p in payments_list)
    pdf_buffer = generate_pdf(project, payment_settings=pay_settings, total_paid=total_paid)
    filename = f"Quotation_{project.customer_name.replace(' ', '_')}_{project.id}.pdf"
    # ?download=1  → Content-Disposition: attachment  (force save to device)
    # default      → Content-Disposition: inline      (open in viewer / share sheet)
    as_attachment = request.args.get('download') == '1'
    return send_file(pdf_buffer, as_attachment=as_attachment,
                     download_name=filename, mimetype='application/pdf')


@projects_bp.route('/projects/<int:project_id>/whatsapp')
@login_required
def whatsapp_share(project_id):
    from flask import redirect as flask_redirect
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin and project.created_by != current_user.id:
        if not ProjectAccess.query.filter_by(project_id=project_id, user_id=current_user.id).first():
            abort(403)

    rates = _get_wood_rates()
    wood_totals = project.get_wood_totals()

    # Payment info for WhatsApp
    pay_settings = {k: AppSetting.get(k, '')
                    for k in ['upi_id', 'bank_name', 'account_name', 'account_number', 'ifsc_code']}
    payments_list = Payment.query.filter_by(project_id=project_id).all()
    total_paid = sum(p.amount for p in payments_list)
    balance = max(project.grand_total - total_paid, 0)

    lines = [
        f"Hello {project.customer_name}! 👋",
        f"",
        f"Thank you for considering *Kundan's Interiors* for your home.",
        f"Here is your interior design quotation summary:",
        f"",
        f"📋 *Quotation #{project.id}*",
        f"📅 Date: {project.created_at.strftime('%d %b %Y')}",
    ]
    if project.address:
        lines.append(f"📍 Address: {project.address}")
    lines += ["", "*Room-wise Breakdown:*"]
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
    ]

    if total_paid > 0:
        lines.append(f"✅ Amount Paid: Rs.{total_paid:,.2f}")
        lines.append(f"⏳ Balance Due: Rs.{balance:,.2f}")

    # Payment instructions
    pay_lines = []
    if pay_settings.get('upi_id'):
        pay_lines.append(f"📱 UPI: *{pay_settings['upi_id']}*")
    if pay_settings.get('account_number'):
        pay_lines.append(
            f"🏦 Bank: {pay_settings.get('bank_name', '')} | "
            f"{pay_settings.get('account_name', '')} | "
            f"A/C: {pay_settings['account_number']} | "
            f"IFSC: {pay_settings.get('ifsc_code', '')}"
        )
    if pay_lines:
        lines += ["", "*Payment Details:*"] + pay_lines

    lines += [
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
