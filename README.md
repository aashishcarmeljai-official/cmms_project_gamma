# CMMS - Computerized Maintenance Management System

A comprehensive web-based Computerized Maintenance Management System (CMMS) built with Flask, PostgreSQL, and modern web technologies.

## 🏭 Features

### Core CMMS Functionality
- **Equipment Management**: Track and manage all equipment assets with detailed information
- **Work Order Management**: Create, assign, and track maintenance work orders
- **Preventive Maintenance**: Schedule and manage preventive maintenance tasks
- **Inventory Management**: Track spare parts and materials with stock levels
- **User Management**: Role-based access control (Admin, Manager, Technician)
- **Dashboard Analytics**: Real-time overview of maintenance operations

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

### Preventive Maintenance
- Scheduled maintenance tasks
- Frequency-based scheduling (Daily, Weekly, Monthly, Yearly)
- Due date tracking and notifications
- Maintenance history

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
- **Authentication**: Flask-Login (planned)

## 📁 Project Structure

```
cmms_project_gamma/
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings
├── models.py                 # Database models (User, Equipment, WorkOrder, etc.)
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── .gitignore               # Git ignore file
├── templates/               # HTML templates
│   ├── dashboard.html       # Main dashboard
│   ├── equipment/           # Equipment templates
│   │   ├── list.html
│   │   ├── new.html
│   │   └── detail.html
│   ├── work_orders/         # Work order templates
│   │   ├── list.html
│   │   ├── new.html
│   │   └── detail.html
│   └── inventory/           # Inventory templates
│       ├── list.html
│       └── new.html
└── static/                  # Static files
    ├── css/
    │   └── style.css        # Custom styles
    └── js/
        └── script.js        # JavaScript functionality
```

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

### 4. Create Initial Admin User

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

### 5. Run the Application

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

### Analytics
- `GET /api/dashboard-stats` - Dashboard statistics API

## 👥 User Roles

- **Admin**: Full system access, user management
- **Manager**: Equipment and work order management
- **Technician**: Work order execution, status updates

## 🔒 Security Features

- Password hashing with Werkzeug
- Role-based access control
- Session management
- Input validation and sanitization

## 📈 Future Enhancements

- [ ] User authentication and login system
- [ ] Advanced reporting and analytics
- [ ] Mobile-responsive design
- [ ] Email notifications
- [ ] File attachments for work orders
- [ ] Barcode/QR code scanning
- [ ] Maintenance cost tracking
- [ ] Equipment lifecycle management
- [ ] Integration with external systems
- [ ] Multi-language support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

For support and questions, please create an issue in the repository or contact the development team. 