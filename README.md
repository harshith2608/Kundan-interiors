# Kundann Interiors — Quotation & Project Management System

A full-stack web application built for **Kundann Interiors**, an interior design business. It allows admin and employee users to create detailed wood-work quotations, track payments, generate PDF documents, and share them with customers via WhatsApp.

Live deployment: [Vercel](https://vercel.com) · Database: [Neon PostgreSQL](https://neon.tech)

---

## Features

### Quotation Management
- Create quotations with customer details, rooms, and items (length × width → sqft)
- Material types: **Acrylic**, **Laminates**, **Veneer**
- Work types: **Box Work**, **Frame Work**
- Auto-calculates area and cost per item using admin-configured rates
- Discount support — percentage or fixed amount
- Live cost summary updates as rooms/items are added
- **Plywood thickness selection** (18mm 8×4, 12mm 8×4, 6mm 8×4, 25mm Blackboard, 18mm Blackboard)
- **Live plywood board estimate** — calculates approximate number of 8×4 ft boards needed based on total project area (32 sqft per board)
- Auto-save draft while editing; promoted to complete on final save
- Search, paginate, and filter quotations

### PDF Generation
Two PDF formats via **ReportLab Platypus**:

| PDF Type | Contents |
|---|---|
| **Internal PDF** | Full room-by-room breakdown with rates, combo cost summary, total area, plywood used, material specs, T&C, signature section, payment details |
| **Customer PDF** | Simplified view without per-item rates, shows final total, plywood used, material specs, T&C, signature section |

Both PDFs include:
- Company header (name, address, mobile, email — configurable from admin)
- Total area (sqft) alongside final total
- **Signature section** — customer name (left) and Kundan Interior / Proprietor (right)
- Plywood Used section (if selected)
- Material Specifications (if configured)
- Terms & Conditions (admin-editable)

### Payment Tracking
- Record manual payments with notes
- **Razorpay Payment Links** — generate and send payment links to customers
- **Razorpay Webhook** — auto-records payments on `payment_link.paid` event with HMAC-SHA256 signature verification
- Payment status bar showing amount paid vs. balance due
- Email notifications (SMTP) to admin and customer on auto-payment

### WhatsApp Sharing
- One-click WhatsApp share with pre-formatted project summary including customer details, room breakdown, total, and payment link

### Admin Panel
- **Dashboard** — employee performance stats, wood type distribution chart, room type distribution, overall KPIs
- **User Management** — create/rename/delete employees and admins, change passwords
- **Rates** — configure per-sqft rates for each wood × work type combination
- **App Settings** — Razorpay API keys, webhook secret, UPI ID, bank account details, SMTP email, company details, material specifications, terms & conditions
- **Employee Access Control** — grant/revoke employee access to specific quotations
- **Notifications** — in-app alerts for auto-payments received

### Access Control
- Role-based: `admin` and `employee`
- Employees see only their own quotations (unless access is granted by admin)
- Admin-only actions: delete quotation, add/delete payments, generate payment links, manage users, access settings

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 · Flask 3.0 (Application Factory + Blueprints) |
| ORM | SQLAlchemy 3 (Flask-SQLAlchemy) |
| Database | SQLite (development) · PostgreSQL via Neon (production) |
| Auth | Flask-Login · PBKDF2-SHA256 password hashing · Flask-WTF CSRF |
| PDF | ReportLab Platypus (SimpleDocTemplate, Flowables, TableStyle) |
| Payments | Razorpay Payment Links API + Webhook |
| Static Files | WhiteNoise (serves static files through WSGI — no separate CDN needed) |
| Frontend | Bootstrap 5 · Bootstrap Icons · Vanilla JS |
| Deployment | Vercel (`@vercel/python` serverless) |

---

## Project Structure

```
kundanns-interiors/
├── app/
│   ├── __init__.py          # Application factory, blueprint registration, seed DB
│   ├── models.py            # SQLAlchemy models (User, Project, Room, Item, Payment, ...)
│   ├── auth.py              # Login / logout routes
│   ├── main.py              # Root redirect, error handlers (403, 404, 500)
│   ├── projects.py          # Quotation CRUD, PDF download, WhatsApp, payments, webhook
│   ├── admin_bp.py          # Admin dashboard, users, rates, app settings
│   ├── api.py               # Internal JSON API (master rooms/items, wood rates, draft save)
│   ├── pdf_utils.py         # ReportLab PDF generation (internal + customer PDF)
│   ├── forms.py             # WTForms definitions
│   └── decorators.py        # @admin_required decorator
├── templates/
│   ├── base.html            # Shared layout, navbar, flash messages
│   ├── auth/                # Login page
│   ├── projects/            # list, form (create/edit), view
│   ├── admin/               # dashboard, users, rates, payment_settings, notifications
│   └── errors/              # 403, 404, 500 pages
├── static/
│   ├── css/style.css        # Custom styles, brand colours
│   └── js/project_form.js   # Live cost summary, room/item management, auto-save draft
├── config.py                # Dev/Prod config classes (SECRET_KEY, DB URL, cookies)
├── run.py                   # App entry point
├── requirements.txt         # Python dependencies
├── vercel.json              # Vercel deployment config
├── render.yaml              # Render deployment config (alternative)
└── Procfile                 # Gunicorn entry (Render/Heroku)
```

---

## Database Schema

### `users`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| username | String(80) | unique |
| full_name | String(120) | optional display name |
| password_hash | String(256) | PBKDF2-SHA256 |
| role | String(20) | `admin` or `employee` |
| created_at | DateTime | |

### `projects`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| customer_name | String(100) | |
| mobile | String(20) | |
| email | String(100) | optional |
| address | Text | optional |
| created_by | FK → users.id | |
| grand_total | Float | sum of all item costs |
| discount_type | String(20) | `none`, `percentage`, `fixed` |
| discount_value | Float | |
| status | String(20) | `complete` or `draft` |
| plywood_thickness | Text | comma-separated selected options |
| created_at | DateTime | |
| updated_at | DateTime | auto-updated on save |

### `rooms`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| project_id | FK → projects.id | CASCADE delete |
| name | String(100) | e.g. "Master Bedroom" |

### `items`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| room_id | FK → rooms.id | CASCADE delete |
| name | String(100) | e.g. "Wardrobe" |
| length | Float | decimal feet |
| width | Float | decimal feet |
| area | Float | length × width (sqft) |
| wood_type | String(50) | Acrylic / Laminates / Veneer |
| work_type | String(50) | Box Work / Frame Work |

### `item_rates`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| wood_type | String(50) | |
| work_type | String(50) | |
| rate_per_sqft | Float | unique per (wood_type, work_type) |

### `payments`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| project_id | FK → projects.id | CASCADE delete |
| amount | Float | |
| note | String(200) | optional |
| recorded_by | FK → users.id | |
| recorded_at | DateTime | |
| source | String(20) | `manual` or `razorpay` |
| razorpay_payment_id | String(100) | unique, from webhook |

### `payment_links`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| project_id | FK → projects.id | CASCADE delete |
| razorpay_link_id | String(100) | unique |
| amount | Float | |
| created_at | DateTime | |

### `app_settings`
| Column | Type | Notes |
|---|---|---|
| key | String(100) PK | setting name |
| value | Text | setting value |

Key settings: `razorpay_key_id`, `razorpay_key_secret`, `webhook_secret`, `upi_id`, `bank_name`, `account_name`, `account_number`, `ifsc_code`, `admin_email`, `smtp_*`, `company_*`, `material_specs`, `terms_conditions`

### Other tables
- **`master_rooms`** / **`master_items`** — autocomplete suggestions for room/item names
- **`project_access`** — grants employee access to quotations they didn't create
- **`project_edit_logs`** — tracks who last edited a quotation
- **`notifications`** — in-app alerts for admin (e.g. auto-payment received)

---

## Local Development Setup

### 1. Clone the repo
```bash
git clone https://github.com/harshith2608/Kundan-interiors.git
cd Kundan-interiors
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the app
```bash
python run.py
```

The app starts at `http://localhost:5000`. On first run it:
- Creates `kundans_interiors.db` (SQLite)
- Seeds a default admin user: **username** `admin` / **password** `admin123`
- Seeds default room names, item names, and item rates

### 4. Environment variables (optional for local)
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///kundans_interiors.db
```

---

## Production Deployment (Vercel + Neon)

### 1. Set environment variables in Vercel dashboard
```env
FLASK_ENV=production
SECRET_KEY=<strong-random-secret>
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
```

### 2. Deploy
Push to GitHub — Vercel auto-deploys on every push to `main`.

### 3. Database migrations
Since there is no migration tool, new columns must be added manually on Neon:
```sql
-- Example: adding a new column
ALTER TABLE projects ADD COLUMN IF NOT EXISTS plywood_thickness TEXT DEFAULT '';
```

Run SQL from the [Neon console](https://console.neon.tech) → your project → SQL Editor.

---

## API Endpoints (Internal)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/master-rooms` | JSON list of room name suggestions |
| GET | `/api/master-items` | JSON list of item name suggestions |
| GET | `/api/wood-rates` | JSON map of `wood_type: rate` |
| POST | `/api/draft` | Auto-save project as draft |
| POST | `/webhook/razorpay` | Razorpay payment webhook |

---

## Security

- **CSRF protection** on all forms via Flask-WTF
- **PBKDF2-SHA256** password hashing (Werkzeug)
- **HMAC-SHA256** webhook signature verification for Razorpay
- **Role-based access control** — admin-only routes guarded by `@admin_required`
- **Session cookies** — `Secure`, `HttpOnly`, `SameSite=Lax` in production
- **WhiteNoise** serves static files directly — no separate static server needed

---

## License

This project is proprietary software built for Kundann Interiors. All rights reserved.
