# CMMS - Computerized Maintenance Management System

A comprehensive web-based Computerized Maintenance Management System (CMMS) built with Flask, PostgreSQL, and modern web technologies, featuring advanced WhatsApp integration for real-time communication.

## 🏭 Features

### Core CMMS Functionality
- **Equipment Management**: Track and manage all equipment assets with detailed information
- **Work Order Management**: Create, assign, and track maintenance work orders
- **Preventive Maintenance**: Schedule and manage preventive maintenance tasks
- **Inventory Management**: Track spare parts and materials with stock levels
- **User Management**: Role-based access control (Admin, Manager, Technician)
- **Dashboard Analytics**: Real-time overview of maintenance operations

### 🚀 WhatsApp Integration (NEW!)
- **Real-Time Notifications**: Instant WhatsApp messages for work order assignments, priority escalations, and parts delivery
- **Interactive Updates**: Technicians can update work order status and send photos/videos via WhatsApp
- **Emergency Broadcasts**: Send urgent alerts to all technicians instantly
- **Multilingual Support**: Automatic translation of notifications in multiple languages
- **WhatsApp Chatbot**: Full CMMS interaction via WhatsApp commands (`/wo`, `/status`, `/help`)
- **Maintenance Reminders**: Interactive PM reminders with "Mark as Done" buttons
- **Checklist Submissions**: Daily/weekly checklists with tappable buttons
- **Training & Onboarding**: Share training content and SOPs via WhatsApp

### Equipment Management
- Equipment registration with unique IDs
- Categorization and criticality levels
- Location and department tracking
- Manufacturer and model information
- Status tracking (Operational, Maintenance, Out of Service)

### Work Order System
- Automated work order numbering
- Priority levels (Low, Medium, High, Urgent)
- Status tracking (Open, In Progress, Completed, Cancelled)
- Equipment assignment and technician assignment
- Time tracking and completion notes
- Parts usage tracking
- **WhatsApp Integration**: Real-time notifications and status updates

### Preventive Maintenance
- Scheduled maintenance tasks
- Frequency-based scheduling (Daily, Weekly, Monthly, Yearly)
- Due date tracking and notifications
- Maintenance history
- **WhatsApp Reminders**: Interactive maintenance reminders

### Inventory Management
- Part number tracking
- Stock level monitoring
- Minimum/maximum stock alerts
- Supplier information
- Cost tracking
- Location management

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Icons**: Font Awesome
- **Authentication**: Flask-Login
- **WhatsApp Integration**: WhatsApp Business API, googletrans for multilingual support
- **Background Tasks**: Celery with Redis (optional)

## 📁 Project Structure

```
cmms_project_gamma/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── delete_all_tables.py    # Script to delete all DB tables
├── extensions.py           # Flask extensions setup
├── generate_qr_codes.py    # QR code generation script
├── init_db.py              # Database initialization script
├── models.py               # SQLAlchemy models
├── multitenancy.py         # Multi-tenancy utilities
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── whatsapp_integration.py # WhatsApp integration logic
├── whatsapp_notifications.py # WhatsApp notification logic
├── whatsapp_webhook.py     # WhatsApp webhook endpoint
├── instance/
│   └── cmms.db             # SQLite database (example)
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles
│   ├── img/
│   │   └── README.md       # Image assets info
│   ├── js/
│   │   ├── media-upload.js # Media upload JS
│   │   └── script.js       # General JS
│   ├── manifest.json       # PWA manifest
│   ├── sw.js               # Service worker
│   └── uploads/
│       ├── comments/       # Uploaded comment media
│       └── work_orders/    # Uploaded work order media
├── templates/
│   ├── admin/
│   │   ├── analytics.html
│   │   ├── assets.html
│   │   ├── dashboard.html
│   │   ├── quick_actions.html
│   │   ├── settings.html
│   │   ├── technicians.html
│   │   ├── users.html
│   │   └── work_orders.html
│   ├── base.html
│   ├── change_password.html
│   ├── dashboard.html
│   ├── delete_account.html
│   ├── equipment/
│   │   ├── detail.html
│   │   ├── list.html
│   │   └── new.html
│   ├── generate_qr.html
│   ├── index.html
│   ├── inventory/
│   │   ├── detail.html
│   │   ├── list.html
│   │   └── new.html
│   ├── locations/
│   │   ├── detail.html
│   │   ├── edit.html
│   │   ├── list.html
│   │   └── new.html
│   ├── login.html
│   ├── maintenance_calendar.html
│   ├── maintenance_schedule_form.html
│   ├── maps.html
│   ├── mobile/
│   │   ├── complete_task.html
│   │   ├── dashboard.html
│   │   ├── login.html
│   │   ├── profile.html
│   │   ├── task_detail.html
│   │   └── tasks.html
│   ├── profile_edit.html
│   ├── profile.html
│   ├── qr_failure_report_success.html
│   ├── qr_failure_report.html
│   ├── quick_assets/
│   │   ├── add.html
│   │   ├── edit.html
│   │   └── index.html
│   ├── quick_maintenance_schedule.html
│   ├── reports/
│   │   ├── dashboard.html
│   │   ├── equipment_analytics.html
│   │   ├── equipment_list.html
│   │   ├── performance_metrics.html
│   │   └── task_logs.html
│   ├── signup.html
│   ├── sops/
│   │   ├── detail.html
│   │   ├── edit.html
│   │   ├── list.html
│   │   └── new.html
│   ├── team_form.html
│   ├── teams.html
│   ├── test_qr.html
│   ├── whatsapp_emergency.html
│   ├── whatsapp_notifications.html
│   ├── whatsapp_settings.html
│   ├── whatsapp_template_edit.html
│   ├── whatsapp_template_new.html
│   ├── whatsapp_templates.html
│   ├── whatsapp_verify.html
│   ├── work_orders/
│   │   ├── detail.html
│   │   ├── list.html
│   │   └── new.html
├── Updates and Info/
│   ├── ADMIN_DASHBOARD_IMPLEMENTATION.md
│   ├── BASIC_REPORTING_LOGS.md
│   ├── MEDIA_UPLOAD_SYSTEM.md
│   ├── MOBILE_TECHNICIAN_VIEW.md
│   ├── PHOTO_VIDEO_UPLOAD_IMPLEMENTATION.md
│   ├── QR_CODE_SYSTEM_IMPLEMENTATION.md
│   ├── QUICK_ASSET_REGISTRY_IMPLEMENTATION.md
│   ├── SOP_SYSTEM_IMPLEMENTATION.md
├── WHATSAPP_INTEGRATION_README.md
```

_This structure reflects the current organization of the project, including all main modules, templates, static assets, and documentation._

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

1. Install PostgreSQL on your system
2. Create a new database:
   ```sql
   CREATE DATABASE cmms_db;
   ```
3. Update the database URL in `config.py` or set environment variables:
   ```bash
   export DATABASE_URL="postgresql://username:password@localhost/cmms_db"
   export SECRET_KEY="your-super-secret-key"
   ```

### 3. Initialize Database

```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 4. WhatsApp Integration Setup (Optional but Recommended)

1. **Set up WhatsApp Business API**:
   - Create Facebook Developer account
   - Set up WhatsApp Business API
   - Get access token and phone number ID

2. **Configure environment variables**:
   ```bash
   export WHATSAPP_ACCESS_TOKEN="your_access_token"
   export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
   export WHATSAPP_VERIFY_TOKEN="your_verify_token"
   ```

3. **Run WhatsApp migration**:
   ```bash
   python migrate_whatsapp_tables.py
   ```

4. **Configure webhook**:
   - Set webhook URL: `https://yourdomain.com/whatsapp/webhook`
   - Verify token matches your `WHATSAPP_VERIFY_TOKEN`

For detailed WhatsApp setup instructions, see [WHATSAPP_INTEGRATION_README.md](WHATSAPP_INTEGRATION_README.md)

### 5. Create Initial Admin User

```bash
python
>>> from app import app, db
>>> from models import User
>>> with app.app_context():
...     admin = User(
...         username='admin',
...         email='admin@company.com',
...         first_name='Admin',
...         last_name='User',
...         role='admin'
...     )
...     admin.set_password('admin123')
...     db.session.add(admin)
...     db.session.commit()
>>> exit()
```

### 6. Run the Application

```bash
python app.py
```

The CMMS will be available at `http://localhost:5000`

## 📊 Database Schema

### Core Tables
- **users**: User accounts with roles and permissions
- **equipment**: Equipment assets with specifications and status
- **work_orders**: Maintenance work orders with assignments
- **maintenance_schedules**: Preventive maintenance schedules
- **inventory**: Spare parts and materials
- **work_order_parts**: Parts used in work orders

### WhatsApp Integration Tables
- **whatsapp_users**: WhatsApp number verification and preferences
- **whatsapp_messages**: Incoming and outgoing WhatsApp messages
- **whatsapp_templates**: Message templates for notifications
- **notification_logs**: Log of all sent notifications
- **emergency_broadcasts**: Emergency broadcast messages

## 🔧 API Endpoints

### Dashboard
- `GET /` - Main dashboard with statistics
- `GET /health` - System health check

### Equipment
- `GET /equipment` - List all equipment
- `GET /equipment/new` - Add new equipment form
- `POST /equipment/new` - Create new equipment
- `GET /equipment/<id>` - Equipment details
- `GET /api/equipment` - Equipment API

### Work Orders
- `GET /work-orders` - List all work orders
- `GET /work-orders/new` - Create work order form
- `POST /work-orders/new` - Create new work order
- `GET /work-orders/<id>` - Work order details
- `POST /work-orders/<id>/update-status` - Update work order status
- `GET /api/work-orders` - Work orders API

### Inventory
- `GET /inventory` - List all inventory items
- `GET /inventory/new` - Add inventory item form
- `POST /inventory/new` - Create new inventory item
- `GET /api/inventory` - Inventory API

### WhatsApp Integration
- `GET /whatsapp/verify` - WhatsApp verification page
- `POST /whatsapp/verify` - Submit verification
- `GET /whatsapp/settings` - WhatsApp settings
- `POST /whatsapp/settings` - Update settings
- `GET /whatsapp/emergency` - Emergency broadcast page
- `POST /whatsapp/emergency` - Send emergency broadcast
- `POST /whatsapp/webhook` - WhatsApp webhook endpoint
- `POST /api/whatsapp/send-test` - Send test message

### Analytics
- `GET /api/dashboard-stats` - Dashboard statistics API

## 💬 WhatsApp Commands

Users can interact with the CMMS directly via WhatsApp:

| Command | Description | Example |
|---------|-------------|---------|
| `/wo [number]` | View work order details | `/wo WO-20241201-ABC123` |
| `/status [number] [status]` | Update work order status | `/status WO-20241201-ABC123 completed` |
| `/help` | Show available commands | `/help` |

## 👥 User Roles

- **Admin**: Full system access, user management, emergency broadcasts
- **Manager**: Equipment and work order management, WhatsApp templates
- **Technician**: Work order execution, status updates, WhatsApp interactions

## 🔒 Security Features

- Password hashing with Werkzeug
- Role-based access control
- Session management
- Input validation and sanitization
- WhatsApp number verification
- Secure webhook handling

## 📈 Future Enhancements

- [x] WhatsApp integration for real-time communication
- [x] Emergency broadcast system
- [x] Multilingual support
- [x] Interactive notifications
- [ ] Advanced reporting and analytics
- [ ] Mobile-responsive design
- [ ] Email notifications
- [ ] File attachments for work orders
- [ ] AI-powered chatbot responses
- [ ] Voice commands integration

## 📞 Support

For WhatsApp integration support, see [WHATSAPP_INTEGRATION_README.md](WHATSAPP_INTEGRATION_README.md)

For general CMMS support:
1. Check the application logs
2. Verify database connectivity
3. Ensure all environment variables are set correctly
4. Test WhatsApp integration with `/api/whatsapp/send-test`

---

**Note**: The WhatsApp integration requires a WhatsApp Business API account and proper configuration. See the WhatsApp integration README for detailed setup instructions. 