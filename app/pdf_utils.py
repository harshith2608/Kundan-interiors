from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

WOOD_TYPES = ['Acrylic', 'Laminates', 'Veneer']


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
    elements.append(Paragraph("Kundan's Interiors", title_style))
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

    item_col_widths = ['25%', '13%', '13%', '15%', '18%', '16%']
    page_width = A4[0] - 3 * cm
    col_widths = [page_width * float(p.strip('%')) / 100 for p in item_col_widths]

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
        item_rows = [['Item Name', 'Length', 'Width', 'Wood Type', 'Area (sqft)', 'Subtotal (Rs.)']]
        room_total_area = 0.0
        for item in room.items.all():
            room_total_area += item.area
            item_rows.append([
                item.name,
                ft_in(item.length),
                ft_in(item.width),
                item.wood_type,
                f'{item.area:.2f}',
                '—'
            ])
        # Room total row
        item_rows.append(['', '', '', 'Room Total Area:', f'{room_total_area:.2f} sqft', ''])

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
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#fafafa')]),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), BRAND_LIGHT),
            ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (3, -1), (4, -1), BRAND_DARK),
            ('ALIGN', (3, -1), (4, -1), 'CENTER'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND_DARK),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 8))

    # ------- WOOD TYPE SUMMARY -------
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#bdbdbd'), spaceAfter=8))
    elements.append(Paragraph("Material Cost Summary", section_style))
    elements.append(Spacer(1, 6))

    from .models import WoodRate
    rates = {r.wood_type: r.rate_per_sqft for r in WoodRate.query.all()}
    wood_totals = project.get_wood_totals()

    summary_data = [['Material', 'Total Area (sqft)', 'Rate (Rs./sqft)', 'Amount (Rs.)']]
    grand_total = 0.0
    for wt in WOOD_TYPES:
        area = wood_totals.get(wt, 0.0)
        if area > 0:
            rate = rates.get(wt, 0.0)
            subtotal = area * rate
            grand_total += subtotal
            summary_data.append([
                wt,
                f'{area:,.2f}',
                f'{rate:,.0f}',
                f'{subtotal:,.2f}'
            ])
    summary_data.append(['', '', 'GRAND TOTAL', f'Rs. {project.grand_total:,.2f}'])

    summary_cw = [page_width * p for p in [0.30, 0.25, 0.25, 0.20]]
    summary_table = Table(summary_data, colWidths=summary_cw)
    summary_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BRAND_LIGHT]),
        # Grand total row
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_DARK),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        # Alignment
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

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
        "Thank you for choosing <b>Kundan's Interiors</b>. We look forward to transforming your space!",
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
