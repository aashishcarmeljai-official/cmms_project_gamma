from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Import extensions
from extensions import db

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://cmms_db_bszs_user:jplEjrfzMEwPZZ9oQHgGWW7LjMOLJobM@dpg-d1dnb295pdvs73ao4il0-a.oregon-postgres.render.com/cmms_db_bszs')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize database with app
db.init_app(app)

# Import models after db initialization
from models import User, Equipment, WorkOrder, MaintenanceSchedule, Inventory, WorkOrderPart

# Utility functions
def generate_work_order_number():
    """Generate unique work order number"""
    return f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def get_dashboard_stats():
    """Get dashboard statistics"""
    stats = {
        'total_equipment': Equipment.query.count(),
        'operational_equipment': Equipment.query.filter_by(status='operational').count(),
        'maintenance_equipment': Equipment.query.filter_by(status='maintenance').count(),
        'out_of_service_equipment': Equipment.query.filter_by(status='out_of_service').count(),
        'open_work_orders': WorkOrder.query.filter_by(status='open').count(),
        'in_progress_work_orders': WorkOrder.query.filter_by(status='in_progress').count(),
        'completed_work_orders': WorkOrder.query.filter_by(status='completed').count(),
        'total_users': User.query.count(),
        'low_stock_items': Inventory.query.filter(Inventory.current_stock <= Inventory.minimum_stock).count()
    }
    return stats

# Routes
@app.route('/')
def index():
    """Dashboard page"""
    stats = get_dashboard_stats()
    recent_work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).limit(5).all()
    upcoming_maintenance = MaintenanceSchedule.query.filter(
        MaintenanceSchedule.next_due >= datetime.now(),
        MaintenanceSchedule.is_active == True
    ).order_by(MaintenanceSchedule.next_due).limit(5).all()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_work_orders=recent_work_orders,
                         upcoming_maintenance=upcoming_maintenance)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'CMMS is running!'})

# Equipment routes
@app.route('/equipment')
def equipment_list():
    """List all equipment"""
    equipment = Equipment.query.all()
    return render_template('equipment/list.html', equipment=equipment)

@app.route('/equipment/new', methods=['GET', 'POST'])
def equipment_new():
    """Create new equipment"""
    if request.method == 'POST':
        data = request.form
        equipment = Equipment(
            name=data['name'],
            equipment_id=data['equipment_id'],
            category=data['category'],
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            location=data.get('location'),
            department=data.get('department'),
            criticality=data.get('criticality', 'medium'),
            description=data.get('description'),
            specifications=data.get('specifications')
        )
        db.session.add(equipment)
        db.session.commit()
        flash('Equipment created successfully!', 'success')
        return redirect(url_for('equipment_list'))
    
    return render_template('equipment/new.html')

@app.route('/equipment/<int:id>')
def equipment_detail(id):
    """Equipment detail page"""
    equipment = Equipment.query.get_or_404(id)
    work_orders = WorkOrder.query.filter_by(equipment_id=id).order_by(WorkOrder.created_at.desc()).all()
    maintenance_schedules = MaintenanceSchedule.query.filter_by(equipment_id=id).all()
    today = datetime.now()  # Use datetime instead of date for comparison
    return render_template('equipment/detail.html', 
                         equipment=equipment, 
                         work_orders=work_orders,
                         maintenance_schedules=maintenance_schedules,
                         today=today)

@app.route('/equipment/<int:id>/delete', methods=['POST'])
def equipment_delete(id):
    """Delete equipment"""
    equipment = Equipment.query.get_or_404(id)
    
    try:
        # Check if equipment has associated work orders
        work_orders = WorkOrder.query.filter_by(equipment_id=id).all()
        
        # Check if equipment has maintenance schedules
        maintenance_schedules = MaintenanceSchedule.query.filter_by(equipment_id=id).all()
        
        # Delete associated work order parts first
        for work_order in work_orders:
            work_order_parts = WorkOrderPart.query.filter_by(work_order_id=work_order.id).all()
            for part in work_order_parts:
                db.session.delete(part)
        
        # Delete work orders
        for work_order in work_orders:
            db.session.delete(work_order)
        
        # Delete maintenance schedules
        for schedule in maintenance_schedules:
            db.session.delete(schedule)
        
        # Delete the equipment
        db.session.delete(equipment)
        db.session.commit()
        
        flash(f'Equipment "{equipment.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting equipment: {str(e)}', 'error')
    
    return redirect(url_for('equipment_list'))

# Work Order routes
@app.route('/work-orders')
def work_orders_list():
    """List all work orders"""
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    
    query = WorkOrder.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    
    work_orders = query.order_by(WorkOrder.created_at.desc()).all()
    return render_template('work_orders/list.html', work_orders=work_orders)

@app.route('/work-orders/new', methods=['GET', 'POST'])
def work_order_new():
    """Create new work order"""
    if request.method == 'POST':
        data = request.form
        work_order = WorkOrder(
            work_order_number=generate_work_order_number(),
            title=data['title'],
            description=data['description'],
            priority=data.get('priority', 'medium'),
            type=data.get('type', 'corrective'),
            equipment_id=data['equipment_id'],
            assigned_technician_id=data.get('assigned_technician_id'),
            created_by_id=1,  # TODO: Get from session
            estimated_duration=data.get('estimated_duration'),
            scheduled_date=datetime.strptime(data['scheduled_date'], '%Y-%m-%dT%H:%M') if data.get('scheduled_date') else None
        )
        db.session.add(work_order)
        db.session.commit()
        flash('Work order created successfully!', 'success')
        return redirect(url_for('work_orders_list'))
    
    equipment = Equipment.query.all()
    technicians = User.query.filter_by(role='technician').all()
    return render_template('work_orders/new.html', equipment=equipment, technicians=technicians)

@app.route('/work-orders/<int:id>')
def work_order_detail(id):
    """Work order detail page"""
    work_order = WorkOrder.query.get_or_404(id)
    return render_template('work_orders/detail.html', work_order=work_order)

@app.route('/work-orders/<int:id>/update-status', methods=['POST'])
def work_order_update_status(id):
    """Update work order status"""
    work_order = WorkOrder.query.get_or_404(id)
    new_status = request.form.get('status')
    
    if new_status in ['open', 'in_progress', 'completed', 'cancelled']:
        work_order.status = new_status
        
        if new_status == 'in_progress' and not work_order.actual_start_time:
            work_order.actual_start_time = datetime.now()
        elif new_status == 'completed' and not work_order.actual_end_time:
            work_order.actual_end_time = datetime.now()
            if work_order.actual_start_time:
                work_order.actual_duration = int((work_order.actual_end_time - work_order.actual_start_time).total_seconds() / 60)
        
        db.session.commit()
        flash('Work order status updated!', 'success')
    
    return redirect(url_for('work_order_detail', id=id))

# Inventory routes
@app.route('/inventory')
def inventory_list():
    """List all inventory items"""
    inventory = Inventory.query.all()
    return render_template('inventory/list.html', inventory=inventory)

@app.route('/inventory/new', methods=['GET', 'POST'])
def inventory_new():
    """Create new inventory item"""
    if request.method == 'POST':
        data = request.form
        inventory = Inventory(
            part_number=data['part_number'],
            name=data['name'],
            description=data.get('description'),
            category=data.get('category'),
            manufacturer=data.get('manufacturer'),
            supplier=data.get('supplier'),
            unit_cost=data.get('unit_cost'),
            current_stock=data.get('current_stock', 0),
            minimum_stock=data.get('minimum_stock', 0),
            maximum_stock=data.get('maximum_stock'),
            unit_of_measure=data.get('unit_of_measure', 'pieces'),
            location=data.get('location')
        )
        db.session.add(inventory)
        db.session.commit()
        flash('Inventory item created successfully!', 'success')
        return redirect(url_for('inventory_list'))
    
    return render_template('inventory/new.html')

@app.route('/inventory/<int:id>')
def inventory_detail(id):
    """Inventory item detail page"""
    inventory = Inventory.query.get_or_404(id)
    return render_template('inventory/detail.html', inventory=inventory)

@app.route('/inventory/<int:id>/delete', methods=['POST'])
def inventory_delete(id):
    """Delete inventory item"""
    inventory = Inventory.query.get_or_404(id)
    
    try:
        # Check if inventory item is used in any work orders
        work_order_parts = WorkOrderPart.query.filter_by(inventory_id=id).all()
        
        if work_order_parts:
            # Delete associated work order parts first
            for part in work_order_parts:
                db.session.delete(part)
        
        # Delete the inventory item
        db.session.delete(inventory)
        db.session.commit()
        
        flash(f'Inventory item "{inventory.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting inventory item: {str(e)}', 'error')
    
    return redirect(url_for('inventory_list'))

# API routes
@app.route('/api/equipment')
def api_equipment():
    """API endpoint for equipment"""
    equipment = Equipment.query.all()
    return jsonify([eq.to_dict() for eq in equipment])

@app.route('/api/work-orders')
def api_work_orders():
    """API endpoint for work orders"""
    work_orders = WorkOrder.query.all()
    return jsonify([wo.to_dict() for wo in work_orders])

@app.route('/api/inventory')
def api_inventory():
    """API endpoint for inventory"""
    inventory = Inventory.query.all()
    return jsonify([inv.to_dict() for inv in inventory])

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    return jsonify(get_dashboard_stats())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 