from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# We'll import db from a separate file to avoid circular imports
from extensions import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='technician')  # admin, manager, technician
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    assigned_work_orders = db.relationship('WorkOrder', 
                                         backref='assigned_technician', 
                                         lazy=True,
                                         foreign_keys='WorkOrder.assigned_technician_id')
    created_work_orders = db.relationship('WorkOrder', 
                                        backref='created_by', 
                                        lazy=True, 
                                        foreign_keys='WorkOrder.created_by_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'phone': self.phone,
            'department': self.department,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    equipment_id = db.Column(db.String(50), unique=True, nullable=False)  # Asset tag/ID
    category = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    location = db.Column(db.String(200))
    department = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    status = db.Column(db.String(20), default='operational')  # operational, maintenance, out_of_service
    criticality = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    description = db.Column(db.Text)
    specifications = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    work_orders = db.relationship('WorkOrder', backref='equipment', lazy=True)
    maintenance_schedules = db.relationship('MaintenanceSchedule', backref='equipment', lazy=True)
    
    def __repr__(self):
        return f'<Equipment {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'equipment_id': self.equipment_id,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'location': self.location,
            'department': self.department,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            'status': self.status,
            'criticality': self.criticality,
            'description': self.description,
            'specifications': self.specifications,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    work_order_number = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='open')  # open, in_progress, completed, cancelled
    type = db.Column(db.String(20), default='corrective')  # corrective, preventive, emergency
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    assigned_technician_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    actual_start_time = db.Column(db.DateTime)
    actual_end_time = db.Column(db.DateTime)
    completion_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<WorkOrder {self.work_order_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_number': self.work_order_number,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'type': self.type,
            'equipment_id': self.equipment_id,
            'equipment_name': self.equipment.name if self.equipment else None,
            'assigned_technician_id': self.assigned_technician_id,
            'assigned_technician': f"{self.assigned_technician.first_name} {self.assigned_technician.last_name}" if self.assigned_technician else None,
            'created_by_id': self.created_by_id,
            'created_by': f"{self.created_by.first_name} {self.created_by.last_name}" if self.created_by else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'actual_start_time': self.actual_start_time.isoformat() if self.actual_start_time else None,
            'actual_end_time': self.actual_end_time.isoformat() if self.actual_end_time else None,
            'completion_notes': self.completion_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class MaintenanceSchedule(db.Model):
    __tablename__ = 'maintenance_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    schedule_type = db.Column(db.String(20), default='calendar')  # calendar, runtime, condition
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    frequency_value = db.Column(db.Integer, default=1)  # every X days/weeks/months/years
    description = db.Column(db.Text, nullable=False)
    estimated_duration = db.Column(db.Integer)  # in minutes
    is_active = db.Column(db.Boolean, default=True)
    last_performed = db.Column(db.DateTime)
    next_due = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MaintenanceSchedule {self.equipment.name if self.equipment else "Unknown"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'equipment_id': self.equipment_id,
            'equipment_name': self.equipment.name if self.equipment else None,
            'schedule_type': self.schedule_type,
            'frequency': self.frequency,
            'frequency_value': self.frequency_value,
            'description': self.description,
            'estimated_duration': self.estimated_duration,
            'is_active': self.is_active,
            'last_performed': self.last_performed.isoformat() if self.last_performed else None,
            'next_due': self.next_due.isoformat() if self.next_due else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100))
    supplier = db.Column(db.String(100))
    unit_cost = db.Column(db.Numeric(10, 2))
    current_stock = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=0)
    maximum_stock = db.Column(db.Integer)
    unit_of_measure = db.Column(db.String(20), default='pieces')
    location = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inventory {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'part_number': self.part_number,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'supplier': self.supplier,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'current_stock': self.current_stock,
            'minimum_stock': self.minimum_stock,
            'maximum_stock': self.maximum_stock,
            'unit_of_measure': self.unit_of_measure,
            'location': self.location,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WorkOrderPart(db.Model):
    __tablename__ = 'work_order_parts'
    
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=False)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    work_order = db.relationship('WorkOrder', backref='parts_used')
    inventory_item = db.relationship('Inventory', backref='work_orders')
    
    def __repr__(self):
        return f'<WorkOrderPart {self.inventory_item.name if self.inventory_item else "Unknown"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_id': self.work_order_id,
            'inventory_id': self.inventory_id,
            'inventory_name': self.inventory_item.name if self.inventory_item else None,
            'quantity_used': self.quantity_used,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'total_cost': float(self.unit_cost * self.quantity_used) if self.unit_cost else None,
            'created_at': self.created_at.isoformat()
        } 