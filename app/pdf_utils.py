from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from .models import AppSetting

WOOD_TYPES = ['Acrylic', 'Laminates', 'Veneer']
WORK_TYPES = ['Box Work', 'Frame Work']


def ft_in(decimal_ft):
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

# Brand colors
BRAND_DARK = colors.HexColor('#1a237e')
BRAND_ACCENT = colors.HexColor('#f57f17')
BRAND_LIGHT = colors.HexColor('#e8eaf6')
GREY_BG = colors.HexColor('#f5f5f5')
TABLE_HEADER_BG = colors.HexColor('#283593')
ROOM_HEADER_BG = colors.HexColor('#3949ab')


def generate_pdf(project, payment_settings=None, total_paid=0.0):
    """
    Generate a professional PDF quotation and return a BytesIO buffer.
    payment_settings: dict with keys upi_id, bank_name, account_name,
                      account_number, ifsc_code  (optional)
    total_paid: float – amount already received (optional)
    """
    """Generate a professional PDF quotation and return a BytesIO buffer."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # --- Custom Styles ---
    title_style = ParagraphStyle(
        'Title', parent=styles['Title'],
        fontSize=22, fontName='Helvetica-Bold',
        textColor=BRAND_DARK, alignment=TA_CENTER, spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica',
        textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER, spaceAfter=4
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=BRAND_DARK
    )
    normal_style = ParagraphStyle(
        'NormalCustom', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica'
    )
    right_style = ParagraphStyle(
        'Right', parent=styles['Normal'],
        fontSize=9, alignment=TA_RIGHT
    )
    total_style = ParagraphStyle(
        'Total', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold',
        textColor=BRAND_DARK, alignment=TA_RIGHT
    )

    # -------  HEADER -------
    elements.append(Paragraph("Kundann Interiors", title_style))
    elements.append(Paragraph("Premium Interior Design & Furnishing Solutions", subtitle_style))
    elements.append(HRFlowable(width='100%', thickness=2, color=BRAND_ACCENT, spaceAfter=8))

    # QUOTATION LABEL
    quot_header = Table(
        [['INTERIOR DESIGN QUOTATION',
          f'Quotation #: {project.id}\nDate: {project.created_at.strftime("%d %B %Y")}']],
        colWidths=['65%', '35%']
    )
    quot_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BRAND_DARK),
        ('BACKGROUND', (1, 0), (1, 0), BRAND_LIGHT),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('TEXTCOLOR', (1, 0), (1, 0), BRAND_DARK),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(quot_header)
    elements.append(Spacer(1, 12))

    # ------- CUSTOMER DETAILS -------
    elements.append(Paragraph("Customer Details", section_style))
    elements.append(Spacer(1, 4))
    cust_data = [
        ['Customer Name', project.customer_name, 'Mobile', project.mobile],
        ['Email', project.email or '—', 'Prepared By', project.creator.username],
    ]
    if project.address:
        cust_data.append(['Address', Paragraph(project.address, normal_style), '', ''])
    cust_table = Table(cust_data, colWidths=['18%', '32%', '18%', '32%'])
    span_cmds = []
    if project.address:
        last = len(cust_data) - 1
        span_cmds = [('SPAN', (1, last), (3, last))]
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
        ('BACKGROUND', (2, 0), (2, -1), GREY_BG),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (0, -1), BRAND_DARK),
        ('TEXTCOLOR', (2, 0), (2, -1), BRAND_DARK),
    ] + span_cmds))
    elements.append(cust_table)
    elements.append(Spacer(1, 14))

    # ------- ROOM-BY-ROOM BREAKDOWN -------
    elements.append(Paragraph("Room-by-Room Breakdown", section_style))
    elements.append(Spacer(1, 6))

    item_col_widths = ['22%', '11%', '11%', '14%', '14%', '14%', '14%']
    page_width = A4[0] - 3 * cm
    col_widths = [page_width * float(p.strip('%')) / 100 for p in item_col_widths]

    from .models import WoodRate as _WoodRate, WorkTypeRate as _WorkTypeRate
    _wood_rates_map = {r.wood_type: r.rate_per_sqft for r in _WoodRate.query.all()}
    _work_rates_map = {r.work_type: r.rate_per_sqft for r in _WorkTypeRate.query.all()}

    for room in project.rooms.all():
        # Room header row
        room_header = Table(
            [[f'  {room.name.upper()}']],
            colWidths=[page_width]
        )
        room_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ROOM_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(room_header)

        # Items table
        item_rows = [['Item Name', 'Length', 'Width', 'Wood Type', 'Work Type', 'Area (sqft)', 'Subtotal (Rs.)']]
        room_total_area = 0.0
        room_total_cost = 0.0
        for item in room.items.all():
            work_type  = getattr(item, 'work_type', 'Box Work')
            wood_rate  = _wood_rates_map.get(item.wood_type, 0.0)
            work_rate  = _work_rates_map.get(work_type, 0.0)
            subtotal   = item.area * (wood_rate + work_rate)
            room_total_area += item.area
            room_total_cost += subtotal
            item_rows.append([
                item.name,
                ft_in(item.length),
                ft_in(item.width),
                item.wood_type,
                work_type,
                f'{item.area:.2f}',
                f'{subtotal:,.2f}'
            ])
        # Room total row
        item_rows.append(['', '', '', '', 'Room Total:', f'{room_total_area:.2f} sqft', f'Rs. {room_total_cost:,.2f}'])

        item_table = Table(item_rows, colWidths=col_widths)
        item_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (6, 1), (6, -1), 'RIGHT'),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#fafafa')]),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), BRAND_LIGHT),
            ('FONTNAME', (4, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (4, -1), (-1, -1), BRAND_DARK),
            ('ALIGN', (4, -1), (5, -1), 'CENTER'),
            ('ALIGN', (6, -1), (6, -1), 'RIGHT'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND_DARK),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 8))

    # ------- COST SUMMARY -------
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
    elements.append(Paragraph("Cost Summary", section_style))
    elements.append(Spacer(1, 6))

    wood_rates = _wood_rates_map
    work_rates = _work_rates_map
    wood_totals = project.get_wood_totals()
    work_totals = project.get_work_totals()

    summary_cw = [page_width * p for p in [0.30, 0.25, 0.25, 0.20]]

    # Material cost sub-table
    elements.append(Paragraph("Material (Wood Type)", ParagraphStyle(
        'SubSection', parent=styles['Normal'], fontSize=9,
        fontName='Helvetica-Bold', textColor=colors.HexColor('#283593')
    )))
    elements.append(Spacer(1, 3))
    mat_data = [['Material', 'Total Area (sqft)', 'Rate (Rs./sqft)', 'Amount (Rs.)']]
    mat_total = 0.0
    for wt in WOOD_TYPES:
        area = wood_totals.get(wt, 0.0)
        if area > 0:
            rate = wood_rates.get(wt, 0.0)
            subtotal = area * rate
            mat_total += subtotal
            mat_data.append([wt, f'{area:,.2f}', f'{rate:,.0f}', f'{subtotal:,.2f}'])
    mat_data.append(['', '', 'Material Subtotal', f'Rs. {mat_total:,.2f}'])

    mat_table = Table(mat_data, colWidths=summary_cw)
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BRAND_LIGHT]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eaf6')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2, -1), (-1, -1), BRAND_DARK),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(mat_table)
    elements.append(Spacer(1, 8))

    # Work type cost sub-table
    elements.append(Paragraph("Work Type", ParagraphStyle(
        'SubSection2', parent=styles['Normal'], fontSize=9,
        fontName='Helvetica-Bold', textColor=colors.HexColor('#7c3aed')
    )))
    elements.append(Spacer(1, 3))
    work_data = [['Work Type', 'Total Area (sqft)', 'Rate (Rs./sqft)', 'Amount (Rs.)']]
    work_total = 0.0
    for wt in WORK_TYPES:
        area = work_totals.get(wt, 0.0)
        if area > 0:
            rate = work_rates.get(wt, 0.0)
            subtotal = area * rate
            work_total += subtotal
            work_data.append([wt, f'{area:,.2f}', f'{rate:,.0f}', f'{subtotal:,.2f}'])
    work_data.append(['', '', 'Work Subtotal', f'Rs. {work_total:,.2f}'])

    work_table = Table(work_data, colWidths=summary_cw)
    WORK_HEADER_BG = colors.HexColor('#5b21b6')
    work_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), WORK_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#ede9fe')]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ede9fe')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2, -1), (-1, -1), colors.HexColor('#5b21b6')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(work_table)
    elements.append(Spacer(1, 8))

    # Discount + Final total rows
    discount_amount = getattr(project, 'discount_amount', 0.0)
    final_total     = getattr(project, 'final_total',     project.grand_total)
    total_rows = []
    total_style_cmds = []

    if discount_amount > 0:
        dtype = getattr(project, 'discount_type', 'none')
        dval  = getattr(project, 'discount_value', 0) or 0
        disc_label = f'Discount ({dval:.0f}%)' if dtype == 'percentage' else 'Discount (Fixed)'
        total_rows.append(['', '', disc_label, f'- Rs. {discount_amount:,.2f}'])
        total_style_cmds += [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fef2f2')),
            ('TEXTCOLOR', (2, 0), (-1, 0), colors.HexColor('#b91c1c')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (2, 0), (-1, 0), 'RIGHT'),
            ('PADDING', (0, 0), (-1, 0), 7),
        ]

    fi = len(total_rows)
    total_rows.append(['', '', 'FINAL TOTAL', f'Rs. {final_total:,.2f}'])
    total_style_cmds += [
        ('BACKGROUND', (0, fi), (-1, fi), BRAND_DARK),
        ('TEXTCOLOR', (0, fi), (-1, fi), colors.white),
        ('FONTNAME', (0, fi), (-1, fi), 'Helvetica-Bold'),
        ('FONTSIZE', (0, fi), (-1, fi), 12),
        ('ALIGN', (0, fi), (1, fi), 'LEFT'),
        ('ALIGN', (2, fi), (-1, fi), 'RIGHT'),
        ('PADDING', (0, fi), (-1, fi), 9),
        ('TOPPADDING', (0, fi), (-1, fi), 10),
        ('BOTTOMPADDING', (0, fi), (-1, fi), 10),
    ]

    grand_total_table = Table(total_rows, colWidths=summary_cw)
    grand_total_table.setStyle(TableStyle(total_style_cmds))
    elements.append(grand_total_table)
    elements.append(Spacer(1, 20))

    # ------- MATERIAL SPECIFICATIONS -------
    _specs = AppSetting.get('material_specs', '')
    if _specs and _specs.strip():
        elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
        spec_header_style = ParagraphStyle('SpecHeader', parent=styles['Normal'],
                                           fontSize=9, textColor=BRAND_DARK,
                                           fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4)
        spec_body_style = ParagraphStyle('SpecBody', parent=styles['Normal'],
                                         fontSize=8, textColor=colors.HexColor('#333333'),
                                         leading=13, spaceAfter=1)
        elements.append(Paragraph("Material Specifications:", spec_header_style))
        elements.append(Spacer(1, 4))
        for line in _specs.splitlines():
            line = line.strip()
            if line:
                # Replace bullet character ● with a PDF-safe bullet
                display = line.replace('●', '\u2022')
                elements.append(Paragraph(display, spec_body_style))
        elements.append(Spacer(1, 14))

    # ------- TERMS & CONDITIONS -------
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
    tc_style = ParagraphStyle('TC', parent=styles['Normal'],
                              fontSize=7.5, textColor=colors.HexColor('#757575'))
    elements.append(Paragraph("<b>Terms &amp; Conditions:</b>", tc_style))
    terms = [
        "1. This is a preliminary estimate. Final price may vary based on site conditions and material selection.",
        "2. This quotation is valid for 30 days from the date of issue.",
        "3. A 50% advance payment is required to commence work.",
        "4. Delivery and installation timelines will be communicated separately.",
        "5. Any changes to design or material after order confirmation may attract additional charges.",
    ]
    for term in terms:
        elements.append(Paragraph(term, tc_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Thank you for choosing <b>Kundann Interiors</b>. We look forward to transforming your space!",
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontSize=9, textColor=BRAND_DARK, alignment=TA_CENTER)
    ))

    # ------- PAYMENT DETAILS -------
    ps = payment_settings or {}
    has_payment_info = any([
        ps.get('upi_id'), ps.get('account_number'),
        ps.get('bank_name'), total_paid > 0
    ])
    if has_payment_info:
        elements.append(Spacer(1, 14))
        elements.append(HRFlowable(width='100%', thickness=1, color=BRAND_ACCENT, spaceAfter=8))
        elements.append(Paragraph("Payment Details", section_style))
        elements.append(Spacer(1, 6))

        pay_rows = []

        # Payment status row
        balance = max(project.grand_total - total_paid, 0)
        if total_paid > 0:
            pay_rows.append(['Amount Paid', f'Rs. {total_paid:,.2f}',
                             'Balance Due', f'Rs. {balance:,.2f}'])

        upi   = ps.get('upi_id', '')
        bname = ps.get('bank_name', '')
        aname = ps.get('account_name', '')
        accno = ps.get('account_number', '')
        ifsc  = ps.get('ifsc_code', '')

        if upi:
            pay_rows.append(['UPI ID', upi, '', ''])
        if accno:
            pay_rows.append(['Bank', bname or '—', 'Account Holder', aname or '—'])
            pay_rows.append(['Account No.', accno, 'IFSC Code', ifsc or '—'])

        if pay_rows:
            pay_cw = ['18%', '32%', '18%', '32%']
            pay_cw_abs = [page_width * float(p.strip('%')) / 100 for p in pay_cw]
            pay_table = Table(pay_rows, colWidths=pay_cw_abs)
            span_cmds_pay = []
            for i, row in enumerate(pay_rows):
                if row[2] == '' and row[3] == '':
                    span_cmds_pay.append(('SPAN', (1, i), (3, i)))
            pay_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
                ('BACKGROUND', (2, 0), (2, -1), GREY_BG),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
                ('PADDING', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (0, -1), BRAND_DARK),
                ('TEXTCOLOR', (2, 0), (2, -1), BRAND_DARK),
            ] + span_cmds_pay))
            elements.append(pay_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_customer_pdf(project, payment_settings=None, total_paid=0.0):
    """
    Generate a customer-facing PDF with cost summary only — no item measurements.
    Shows wood type cost breakdown and work type area breakdown (display only).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    elements = []
    page_width = A4[0] - 3 * cm

    # --- Styles (same as main PDF) ---
    title_style = ParagraphStyle(
        'Title2', parent=styles['Title'],
        fontSize=22, fontName='Helvetica-Bold',
        textColor=BRAND_DARK, alignment=TA_CENTER, spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'Subtitle2', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica',
        textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER, spaceAfter=4
    )
    section_style = ParagraphStyle(
        'Section2', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=BRAND_DARK
    )
    normal_style = ParagraphStyle(
        'NormalCustom2', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica'
    )

    # ------- HEADER -------
    elements.append(Paragraph("Kundann Interiors", title_style))
    elements.append(Paragraph("Premium Interior Design & Furnishing Solutions", subtitle_style))
    elements.append(HRFlowable(width='100%', thickness=2, color=BRAND_ACCENT, spaceAfter=8))

    # QUOTATION LABEL
    quot_header = Table(
        [['CUSTOMER QUOTATION',
          f'Quotation #: {project.id}\nDate: {project.created_at.strftime("%d %B %Y")}']],
        colWidths=['65%', '35%']
    )
    quot_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BRAND_DARK),
        ('BACKGROUND', (1, 0), (1, 0), BRAND_LIGHT),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('TEXTCOLOR', (1, 0), (1, 0), BRAND_DARK),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(quot_header)
    elements.append(Spacer(1, 12))

    # ------- CUSTOMER DETAILS -------
    elements.append(Paragraph("Customer Details", section_style))
    elements.append(Spacer(1, 4))
    cust_data = [
        ['Customer Name', project.customer_name, 'Mobile', project.mobile],
        ['Email', project.email or '—', 'Prepared By', project.creator.username],
    ]
    if project.address:
        cust_data.append(['Address', Paragraph(project.address, normal_style), '', ''])
    cust_table = Table(cust_data, colWidths=['18%', '32%', '18%', '32%'])
    span_cmds = []
    if project.address:
        last = len(cust_data) - 1
        span_cmds = [('SPAN', (1, last), (3, last))]
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
        ('BACKGROUND', (2, 0), (2, -1), GREY_BG),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (0, -1), BRAND_DARK),
        ('TEXTCOLOR', (2, 0), (2, -1), BRAND_DARK),
    ] + span_cmds))
    elements.append(cust_table)
    elements.append(Spacer(1, 18))

    # ------- COST SUMMARY -------
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
    elements.append(Paragraph("Cost Summary", section_style))
    elements.append(Spacer(1, 8))

    from .models import WoodRate as _WoodRate
    _wood_rates_map = {r.wood_type: r.rate_per_sqft for r in _WoodRate.query.all()}

    wood_totals = project.get_wood_totals()
    work_totals = project.get_work_totals()
    summary_cw  = [page_width * p for p in [0.35, 0.25, 0.20, 0.20]]

    # Material cost table
    elements.append(Paragraph("Material Cost", ParagraphStyle(
        'SubSec', parent=styles['Normal'], fontSize=9,
        fontName='Helvetica-Bold', textColor=colors.HexColor('#283593')
    )))
    elements.append(Spacer(1, 3))
    mat_data  = [['Material', 'Total Area (sqft)', 'Rate (Rs./sqft)', 'Amount (Rs.)']]
    mat_total = 0.0
    for wt in WOOD_TYPES:
        area = wood_totals.get(wt, 0.0)
        if area > 0:
            rate     = _wood_rates_map.get(wt, 0.0)
            subtotal = area * rate
            mat_total += subtotal
            mat_data.append([wt, f'{area:,.2f}', f'{rate:,.0f}', f'{subtotal:,.2f}'])
    mat_data.append(['', '', 'Material Subtotal', f'Rs. {mat_total:,.2f}'])

    mat_table = Table(mat_data, colWidths=summary_cw)
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BRAND_LIGHT]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eaf6')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2, -1), (-1, -1), BRAND_DARK),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
    elements.append(mat_table)
    elements.append(Spacer(1, 10))

    # Work type breakdown (area only — no rates)
    if any(work_totals.get(wt, 0.0) > 0 for wt in WORK_TYPES):
        elements.append(Paragraph("Work Type Breakdown", ParagraphStyle(
            'SubSec2', parent=styles['Normal'], fontSize=9,
            fontName='Helvetica-Bold', textColor=colors.HexColor('#7c3aed')
        )))
        elements.append(Spacer(1, 3))
        work_cw = [page_width * p for p in [0.50, 0.50]]
        work_data = [['Work Type', 'Total Area (sqft)']]
        for wt in WORK_TYPES:
            area = work_totals.get(wt, 0.0)
            if area > 0:
                work_data.append([wt, f'{area:,.2f}'])
        WORK_HEADER_BG = colors.HexColor('#5b21b6')
        work_table = Table(work_data, colWidths=work_cw)
        work_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), WORK_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ede9fe')]),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 7),
        ]))
        elements.append(work_table)
        elements.append(Spacer(1, 10))

    # Discount + Final total
    discount_amount = getattr(project, 'discount_amount', 0.0)
    final_total     = getattr(project, 'final_total', project.grand_total)
    total_rows      = []
    total_style_cmds = []

    if discount_amount > 0:
        dtype = getattr(project, 'discount_type', 'none')
        dval  = getattr(project, 'discount_value', 0) or 0
        disc_label = f'Discount ({dval:.0f}%)' if dtype == 'percentage' else 'Discount (Fixed)'
        total_rows.append(['', disc_label, f'- Rs. {discount_amount:,.2f}'])
        total_style_cmds += [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fef2f2')),
            ('TEXTCOLOR', (1, 0), (-1, 0), colors.HexColor('#b91c1c')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
            ('PADDING', (0, 0), (-1, 0), 7),
        ]

    fi = len(total_rows)
    total_rows.append(['', 'FINAL TOTAL', f'Rs. {final_total:,.2f}'])
    ft_cw = [page_width * p for p in [0.40, 0.35, 0.25]]
    total_style_cmds += [
        ('BACKGROUND', (0, fi), (-1, fi), BRAND_DARK),
        ('TEXTCOLOR', (0, fi), (-1, fi), colors.white),
        ('FONTNAME', (0, fi), (-1, fi), 'Helvetica-Bold'),
        ('FONTSIZE', (0, fi), (-1, fi), 12),
        ('ALIGN', (1, fi), (-1, fi), 'RIGHT'),
        ('PADDING', (0, fi), (-1, fi), 9),
        ('TOPPADDING', (0, fi), (-1, fi), 10),
        ('BOTTOMPADDING', (0, fi), (-1, fi), 10),
    ]
    grand_total_table = Table(total_rows, colWidths=ft_cw)
    grand_total_table.setStyle(TableStyle(total_style_cmds))
    elements.append(grand_total_table)
    elements.append(Spacer(1, 20))

    # ------- MATERIAL SPECIFICATIONS -------
    _specs = AppSetting.get('material_specs', '')
    if _specs and _specs.strip():
        elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
        spec_header_style = ParagraphStyle('SpecHeader2', parent=styles['Normal'],
                                           fontSize=9, textColor=BRAND_DARK,
                                           fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4)
        spec_body_style = ParagraphStyle('SpecBody2', parent=styles['Normal'],
                                         fontSize=8, textColor=colors.HexColor('#333333'),
                                         leading=13, spaceAfter=1)
        elements.append(Paragraph("Material Specifications:", spec_header_style))
        elements.append(Spacer(1, 4))
        for line in _specs.splitlines():
            line = line.strip()
            if line:
                elements.append(Paragraph(line.replace('●', '\u2022'), spec_body_style))
        elements.append(Spacer(1, 14))

    # ------- TERMS & CONDITIONS -------
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
    tc_style = ParagraphStyle('TC2', parent=styles['Normal'],
                              fontSize=7.5, textColor=colors.HexColor('#757575'))
    elements.append(Paragraph("<b>Terms &amp; Conditions:</b>", tc_style))
    for term in [
        "1. This is a preliminary estimate. Final price may vary based on site conditions and material selection.",
        "2. This quotation is valid for 30 days from the date of issue.",
        "3. A 50% advance payment is required to commence work.",
        "4. Delivery and installation timelines will be communicated separately.",
        "5. Any changes to design or material after order confirmation may attract additional charges.",
    ]:
        elements.append(Paragraph(term, tc_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Thank you for choosing <b>Kundann Interiors</b>. We look forward to transforming your space!",
        ParagraphStyle('Footer2', parent=styles['Normal'],
                       fontSize=9, textColor=BRAND_DARK, alignment=TA_CENTER)
    ))

    # ------- PAYMENT DETAILS -------
    ps = payment_settings or {}
    has_payment_info = any([ps.get('upi_id'), ps.get('account_number'), ps.get('bank_name'), total_paid > 0])
    if has_payment_info:
        elements.append(Spacer(1, 14))
        elements.append(HRFlowable(width='100%', thickness=1, color=BRAND_ACCENT, spaceAfter=8))
        elements.append(Paragraph("Payment Details", section_style))
        elements.append(Spacer(1, 6))
        pay_rows = []
        balance = max(project.grand_total - total_paid, 0)
        if total_paid > 0:
            pay_rows.append(['Amount Paid', f'Rs. {total_paid:,.2f}', 'Balance Due', f'Rs. {balance:,.2f}'])
        if ps.get('upi_id'):
            pay_rows.append(['UPI ID', ps['upi_id'], '', ''])
        if ps.get('account_number'):
            pay_rows.append(['Bank', ps.get('bank_name', '—'), 'Account Holder', ps.get('account_name', '—')])
            pay_rows.append(['Account No.', ps['account_number'], 'IFSC Code', ps.get('ifsc_code', '—')])
        if pay_rows:
            pay_cw_abs = [page_width * float(p) / 100 for p in [18, 32, 18, 32]]
            pay_table  = Table(pay_rows, colWidths=pay_cw_abs)
            span_cmds_pay = [('SPAN', (1, i), (3, i)) for i, r in enumerate(pay_rows) if r[2] == '' and r[3] == '']
            pay_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
                ('BACKGROUND', (2, 0), (2, -1), GREY_BG),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
                ('PADDING', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (0, -1), BRAND_DARK),
                ('TEXTCOLOR', (2, 0), (2, -1), BRAND_DARK),
            ] + span_cmds_pay))
            elements.append(pay_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
