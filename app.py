from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory, Response, send_file
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, IntegerField, BooleanField, DateTimeField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from flask_dance.contrib.google import make_google_blueprint, google
from flask import abort
from werkzeug.utils import secure_filename
import csv
from io import StringIO
import qrcode
import io
import base64
import json
from multitenancy import filter_by_company, enforce_company_access

# Load environment variables
load_dotenv()

# Import extensions
from extensions import db

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize database with app
db.init_app(app)

# Import models after db initialization
from models import User, Equipment, WorkOrder, MaintenanceSchedule, Inventory, WorkOrderPart, Location, Team, WorkOrderComment, SOP, SOPChecklistItem, WorkOrderChecklist, WhatsAppUser, EmergencyBroadcast, NotificationLog, WhatsAppTemplate, WhatsAppMessage, Company

# Utility functions
def generate_work_order_number():
    """Generate unique work order number"""
    return f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def get_dashboard_stats():
    """Get dashboard statistics (company-scoped)"""
    stats = {
        'total_equipment': filter_by_company(Equipment.query).count(),
        'operational_equipment': filter_by_company(Equipment.query).filter_by(status='operational').count(),
        'maintenance_equipment': filter_by_company(Equipment.query).filter_by(status='maintenance').count(),
        'out_of_service_equipment': filter_by_company(Equipment.query).filter_by(status='out_of_service').count(),
        'open_work_orders': filter_by_company(WorkOrder.query).filter_by(status='open').count(),
        'in_progress_work_orders': filter_by_company(WorkOrder.query).filter_by(status='in_progress').count(),
        'completed_work_orders': filter_by_company(WorkOrder.query).filter_by(status='completed').count(),
        'total_users': filter_by_company(User.query).count(),
        'low_stock_items': filter_by_company(Inventory.query).filter(Inventory.current_stock <= Inventory.minimum_stock).count()
    }
    return stats

def calculate_system_health():
    """Calculate comprehensive system health score based on multiple metrics"""
    try:
        health_metrics = {}
        total_score = 0
        max_score = 0
        
        # 1. Database Health (25% weight)
        try:
            # Test database connection
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            db_health = 100
            health_metrics['database'] = {'status': 'healthy', 'score': db_health, 'details': 'Database connection successful'}
        except Exception as e:
            db_health = 0
            health_metrics['database'] = {'status': 'critical', 'score': db_health, 'details': f'Database error: {str(e)}'}
        
        total_score += db_health * 0.25
        max_score += 100 * 0.25
        
        # 2. Equipment Health (20% weight)
        try:
            total_equipment = Equipment.query.count()
            if total_equipment > 0:
                operational_equipment = Equipment.query.filter_by(status='operational').count()
                equipment_health = (operational_equipment / total_equipment) * 100
            else:
                equipment_health = 100  # No equipment means no issues
            
            health_metrics['equipment'] = {
                'status': 'healthy' if equipment_health >= 80 else 'warning' if equipment_health >= 60 else 'critical',
                'score': equipment_health,
                'details': f'{operational_equipment}/{total_equipment} equipment operational'
            }
        except Exception as e:
            equipment_health = 0
            health_metrics['equipment'] = {'status': 'critical', 'score': equipment_health, 'details': f'Equipment query error: {str(e)}'}
        
        total_score += equipment_health * 0.20
        max_score += 100 * 0.20
        
        # 3. Work Order Efficiency (20% weight)
        try:
            total_work_orders = filter_by_company(WorkOrder.query).count()
            if total_work_orders > 0:
                completed_work_orders = filter_by_company(WorkOrder.query).filter_by(status='completed').count()
                overdue_work_orders = filter_by_company(WorkOrder.query).filter(
                    WorkOrder.due_date < datetime.now(),
                    WorkOrder.status.in_(['open', 'in_progress'])
                ).count()
                
                # Calculate efficiency based on completion rate and overdue ratio
                completion_rate = (completed_work_orders / total_work_orders) * 100
                overdue_penalty = min((overdue_work_orders / total_work_orders) * 100, 50)  # Max 50% penalty
                work_order_health = max(completion_rate - overdue_penalty, 0)
            else:
                work_order_health = 100
            
            health_metrics['work_orders'] = {
                'status': 'healthy' if work_order_health >= 80 else 'warning' if work_order_health >= 60 else 'critical',
                'score': work_order_health,
                'details': f'{completed_work_orders}/{total_work_orders} completed, {overdue_work_orders} overdue'
            }
        except Exception as e:
            work_order_health = 0
            health_metrics['work_orders'] = {'status': 'critical', 'score': work_order_health, 'details': f'Work order query error: {str(e)}'}
        
        total_score += work_order_health * 0.20
        max_score += 100 * 0.20
        
        # 4. User Activity (15% weight)
        try:
            total_users = User.query.count()
            if total_users > 0:
                # Check for users who logged in within last 30 days
                thirty_days_ago = datetime.now() - timedelta(days=30)
                active_users = User.query.filter(User.last_login >= thirty_days_ago).count()
                user_activity_health = (active_users / total_users) * 100
            else:
                user_activity_health = 100
            
            health_metrics['user_activity'] = {
                'status': 'healthy' if user_activity_health >= 70 else 'warning' if user_activity_health >= 40 else 'critical',
                'score': user_activity_health,
                'details': f'{active_users}/{total_users} users active in last 30 days'
            }
        except Exception as e:
            user_activity_health = 0
            health_metrics['user_activity'] = {'status': 'critical', 'score': user_activity_health, 'details': f'User activity query error: {str(e)}'}
        
        total_score += user_activity_health * 0.15
        max_score += 100 * 0.15
        
        # 5. System Performance (10% weight)
        try:
            # Check for recent errors in notification logs
            recent_errors = NotificationLog.query.filter(
                NotificationLog.status == 'failed',
                NotificationLog.created_at >= datetime.now() - timedelta(hours=24)
            ).count()
            
            # Check for recent successful notifications
            recent_success = NotificationLog.query.filter(
                NotificationLog.status == 'sent',
                NotificationLog.created_at >= datetime.now() - timedelta(hours=24)
            ).count()
            
            total_recent = recent_errors + recent_success
            if total_recent > 0:
                performance_health = ((total_recent - recent_errors) / total_recent) * 100
            else:
                performance_health = 100  # No notifications means no errors
            
            health_metrics['performance'] = {
                'status': 'healthy' if performance_health >= 90 else 'warning' if performance_health >= 70 else 'critical',
                'score': performance_health,
                'details': f'{recent_success} successful, {recent_errors} failed notifications in last 24h'
            }
        except Exception as e:
            performance_health = 0
            health_metrics['performance'] = {'status': 'critical', 'score': performance_health, 'details': f'Performance query error: {str(e)}'}
        
        total_score += performance_health * 0.10
        max_score += 100 * 0.10
        
        # 6. Storage Health (10% weight)
        try:
            # Check upload directory space (if exists)
            upload_dir = os.path.join(os.getcwd(), 'static', 'uploads')
            if os.path.exists(upload_dir):
                total_size = 0
                file_count = 0
                for dirpath, dirnames, filenames in os.walk(upload_dir):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                            file_count += 1
                        except OSError:
                            pass
                
                # Simple heuristic: if less than 1GB and less than 1000 files, consider healthy
                storage_health = 100
                if total_size > 1024 * 1024 * 1024:  # 1GB
                    storage_health -= 20
                if file_count > 1000:
                    storage_health -= 20
                storage_health = max(storage_health, 0)
                
                health_metrics['storage'] = {
                    'status': 'healthy' if storage_health >= 80 else 'warning' if storage_health >= 60 else 'critical',
                    'score': storage_health,
                    'details': f'{file_count} files, {total_size / (1024*1024):.1f} MB used'
                }
            else:
                storage_health = 100
                health_metrics['storage'] = {'status': 'healthy', 'score': storage_health, 'details': 'Upload directory not configured'}
        except Exception as e:
            storage_health = 0
            health_metrics['storage'] = {'status': 'critical', 'score': storage_health, 'details': f'Storage check error: {str(e)}'}
        
        total_score += storage_health * 0.10
        max_score += 100 * 0.10
        
        # Calculate overall health percentage
        overall_health = (total_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'overall_health': round(overall_health, 1),
            'metrics': health_metrics,
            'status': 'healthy' if overall_health >= 80 else 'warning' if overall_health >= 60 else 'critical'
        }
        
    except Exception as e:
        return {
            'overall_health': 0,
            'metrics': {'error': {'status': 'critical', 'score': 0, 'details': f'System health calculation error: {str(e)}'}},
            'status': 'critical'
        }

# File upload configuration
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_dir, file_type):
    """Save uploaded file with proper validation and naming"""
    if file and file.filename:
        # Validate file extension
        if file_type == 'image' and not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return None
        elif file_type == 'video' and not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return None
        elif file_type == 'audio' and not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
            return None
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return None
        
        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(file_path)
        
        # Return relative path for database storage
        return f"uploads/{os.path.basename(upload_dir)}/{filename}"
    
    return None

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard page"""
    stats = get_dashboard_stats()
    recent_work_orders = filter_by_company(WorkOrder.query).order_by(WorkOrder.created_at.desc()).limit(5).all()
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
@login_required
def equipment_list():
    """List all equipment for the current company"""
    equipment = filter_by_company(Equipment.query).all()
    return render_template('equipment/list.html', equipment=equipment)

@app.route('/equipment/new', methods=['GET', 'POST'])
@login_required
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
            specifications=data.get('specifications'),
            company_id=current_user.company_id  # Ensure multi-tenancy
        )
        db.session.add(equipment)
        db.session.commit()
        flash('Equipment created successfully!', 'success')
        return redirect(url_for('equipment_list'))
    
    return render_template('equipment/new.html')

@app.route('/equipment/<int:id>')
@login_required
def equipment_detail(id):
    """Equipment detail page"""
    equipment = Equipment.query.get_or_404(id)
    work_orders = filter_by_company(WorkOrder.query).filter_by(equipment_id=id).order_by(WorkOrder.created_at.desc()).all()
    maintenance_schedules = MaintenanceSchedule.query.filter_by(equipment_id=id).all()
    today = datetime.now()  # Use datetime instead of date for comparison
    return render_template('equipment/detail.html', 
                         equipment=equipment, 
                         work_orders=work_orders,
                         maintenance_schedules=maintenance_schedules,
                         today=today)

@app.route('/equipment/<int:id>/delete', methods=['POST'])
@login_required
def equipment_delete(id):
    """Delete equipment"""
    equipment = Equipment.query.get_or_404(id)
    
    try:
        # Check if equipment has associated work orders
        work_orders = filter_by_company(WorkOrder.query).filter_by(equipment_id=id).all()
        
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
@login_required
def work_orders_list():
    """List all work orders"""
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    query = filter_by_company(WorkOrder.query)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    work_orders = query.order_by(WorkOrder.created_at.desc()).all()
    return render_template('work_orders/list.html', work_orders=work_orders)

@app.route('/work-orders/new', methods=['GET', 'POST'])
@login_required
def work_order_new():
    """Create new work order"""
    if request.method == 'POST':
        data = request.form
        
        # Handle image uploads
        images = []
        if 'images' in request.files:
            uploaded_files = request.files.getlist('images')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'work_orders'), 'image')
                if file_path:
                    images.append(file_path)
        
        # Handle video uploads
        videos = []
        if 'videos' in request.files:
            uploaded_files = request.files.getlist('videos')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'work_orders'), 'video')
                if file_path:
                    videos.append(file_path)
        
        # Handle voice note uploads
        voice_notes = []
        if 'voice_notes' in request.files:
            uploaded_files = request.files.getlist('voice_notes')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'work_orders'), 'audio')
                if file_path:
                    voice_notes.append(file_path)
        
        work_order = WorkOrder(
            work_order_number=generate_work_order_number(),
            title=data['title'],
            description=data['description'],
            priority=data.get('priority', 'medium'),
            type=data.get('type', 'corrective'),
            equipment_id=data['equipment_id'],
            assigned_technician_id=data.get('assigned_technician_id') if data.get('assigned_technician_id') else None,
            assigned_team_id=data.get('assigned_team_id') if data.get('assigned_team_id') else None,
            created_by_id=current_user.id,
            estimated_duration=data.get('estimated_duration'),
            scheduled_date=datetime.strptime(data['scheduled_date'], '%Y-%m-%dT%H:%M') if data.get('scheduled_date') else None,
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%dT%H:%M') if data.get('due_date') else None,
            images=','.join(images) if images else None,
            videos=','.join(videos) if videos else None,
            voice_notes=','.join(voice_notes) if voice_notes else None
        )
        db.session.add(work_order)
        db.session.commit()
        flash('Work order created successfully!', 'success')
        return redirect(url_for('work_orders_list'))
    
    equipment = Equipment.query.all()
    technicians = User.query.filter_by(role='technician').all()
    teams = Team.query.all()
    return render_template('work_orders/new.html', equipment=equipment, technicians=technicians, teams=teams)

@app.route('/work-orders/<int:id>')
@login_required
def work_order_detail(id):
    """Work order detail page"""
    work_order = WorkOrder.query.get_or_404(id)
    enforce_company_access(work_order)
    return render_template('work_orders/detail.html', work_order=work_order)

@app.route('/work-orders/<int:id>/update-status', methods=['POST'])
@login_required
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

@app.route('/work-orders/<int:id>/add-comment', methods=['POST'])
@login_required
def work_order_add_comment(id):
    """Add comment to work order"""
    work_order = WorkOrder.query.get_or_404(id)
    comment_text = request.form.get('comment')
    
    if comment_text:
        # Handle image uploads for comments
        images = []
        if 'images' in request.files:
            uploaded_files = request.files.getlist('images')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'comments'), 'image')
                if file_path:
                    images.append(file_path)
        
        # Handle video uploads for comments
        videos = []
        if 'videos' in request.files:
            uploaded_files = request.files.getlist('videos')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'comments'), 'video')
                if file_path:
                    videos.append(file_path)
        
        # Handle voice note uploads for comments
        voice_notes = []
        if 'voice_notes' in request.files:
            uploaded_files = request.files.getlist('voice_notes')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'comments'), 'audio')
                if file_path:
                    voice_notes.append(file_path)
        
        comment = WorkOrderComment(
            work_order_id=id,
            user_id=current_user.id,
            comment=comment_text,
            images=','.join(images) if images else None,
            videos=','.join(videos) if videos else None,
            voice_notes=','.join(voice_notes) if voice_notes else None
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    
    return redirect(url_for('work_order_detail', id=id))

@app.route('/work-orders/<int:work_order_id>/checklist/<int:checklist_item_id>/toggle', methods=['POST'])
@login_required
def toggle_checklist_item(work_order_id, checklist_item_id):
    """Toggle checklist item completion status"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    checklist_item = WorkOrderChecklist.query.get_or_404(checklist_item_id)
    
    if checklist_item.work_order_id != work_order_id:
        abort(404)
    
    checklist_item.is_completed = not checklist_item.is_completed
    
    if checklist_item.is_completed:
        checklist_item.completed_by_id = current_user.id
        checklist_item.completed_at = datetime.utcnow()
    else:
        checklist_item.completed_by_id = None
        checklist_item.completed_at = None
    
    db.session.commit()
    
    flash('Checklist item updated!', 'success')
    return redirect(url_for('work_order_detail', id=work_order_id))

@app.route('/work-orders/<int:work_order_id>/checklist/<int:checklist_item_id>/notes', methods=['POST'])
@login_required
def add_checklist_notes(work_order_id, checklist_item_id):
    """Add notes to checklist item"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    checklist_item = WorkOrderChecklist.query.get_or_404(checklist_item_id)
    
    if checklist_item.work_order_id != work_order_id:
        abort(404)
    
    notes = request.form.get('notes', '').strip()
    checklist_item.notes = notes
    
    db.session.commit()
    
    flash('Notes added to checklist item!', 'success')
    return redirect(url_for('work_order_detail', id=work_order_id))

# Inventory routes
@app.route('/inventory')
@login_required
def inventory_list():
    """List all inventory items"""
    search_query = request.args.get('search', '').strip()
    query = filter_by_company(Inventory.query)
    if search_query:
        query = query.filter(
            db.or_(
                Inventory.part_number.ilike(f'%{search_query}%'),
                Inventory.name.ilike(f'%{search_query}%'),
                Inventory.category.ilike(f'%{search_query}%'),
                Inventory.location.ilike(f'%{search_query}%')
            )
        )
    inventory = query.all()
    return render_template('inventory/list.html', inventory=inventory)

@app.route('/inventory/new', methods=['GET', 'POST'])
@login_required
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
@login_required
def inventory_detail(id):
    """Inventory item detail page"""
    inventory = Inventory.query.get_or_404(id)
    enforce_company_access(inventory)
    return render_template('inventory/detail.html', inventory=inventory)

@app.route('/inventory/<int:id>/delete', methods=['POST'])
@login_required
def inventory_delete(id):
    """Delete inventory item"""
    inventory = Inventory.query.get_or_404(id)
    enforce_company_access(inventory)
    db.session.delete(inventory)
    db.session.commit()
    flash('Inventory item deleted!', 'success')
    return redirect(url_for('inventory_list'))

@app.route('/inventory/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def inventory_edit(id):
    inventory = Inventory.query.get_or_404(id)
    enforce_company_access(inventory)
    form = InventoryForm(obj=inventory)
    # Company-scoped dropdowns
    form.equipment_id.choices = [(0, '-- Select Equipment --')] + [(e.id, e.name) for e in filter_by_company(Equipment.query).order_by(Equipment.name).all()]
    if form.validate_on_submit():
        # ... update fields ...
        db.session.commit()
        flash('Inventory item updated!', 'success')
        return redirect(url_for('inventory_detail', id=inventory.id))
    return render_template('inventory/edit.html', form=form, inventory=inventory)

# API routes
@app.route('/api/equipment')
def api_equipment():
    """API endpoint for equipment (company-scoped)"""
    equipment = filter_by_company(Equipment.query).all()
    return jsonify([eq.to_dict() for eq in equipment])

@app.route('/api/work-orders')
def api_work_orders():
    """API endpoint for work orders (company-scoped)"""
    work_orders = filter_by_company(WorkOrder.query).all()
    return jsonify([wo.to_dict() for wo in work_orders])

@app.route('/api/inventory')
def api_inventory():
    """API endpoint for inventory (company-scoped)"""
    inventory = filter_by_company(Inventory.query).all()
    return jsonify([inv.to_dict() for inv in inventory])

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    return jsonify(get_dashboard_stats())

@app.route('/api/system-health')
@login_required
def api_system_health():
    """API endpoint for system health data"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    health_data = calculate_system_health()
    return jsonify(health_data)

@app.route('/api/locations')
def api_locations():
    """API endpoint for locations (company-scoped)"""
    locations = filter_by_company(Location.query).all()
    return jsonify([loc.to_dict() for loc in locations])

@app.route('/api/calendar-events')
@login_required
def api_calendar_events():
    work_orders = filter_by_company(WorkOrder.query).filter(WorkOrder.scheduled_date != None).all()
    maints = MaintenanceSchedule.query.filter(MaintenanceSchedule.next_due != None, MaintenanceSchedule.is_active == True).all()
    events = []
    for wo in work_orders:
        events.append({
            'id': f'wo-{wo.id}',
            'title': f'WO: {wo.title}',
            'start': wo.scheduled_date.isoformat() if wo.scheduled_date else None,
            'url': url_for('work_order_detail', id=wo.id)
        })
    for ms in maints:
        events.append({
            'id': f'ms-{ms.id}',
            'title': f'Maintenance: {ms.equipment.name if ms.equipment else "Unknown"}',
            'start': ms.next_due.isoformat() if ms.next_due else None,
            'url': url_for('equipment_detail', id=ms.equipment_id)
        })
    return jsonify(events)

# API Routes for Mobile Media Uploads
@app.route('/api/work-orders/<int:work_order_id>/upload-media', methods=['POST'])
@login_required
def api_upload_media(work_order_id):
    """API endpoint for mobile media uploads with progress tracking"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    try:
        media_type = request.form.get('media_type', 'image')  # image, video, voice
        media_files = []
        
        if media_type == 'image':
            files = request.files.getlist('images')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'work_orders')
                file_path = save_uploaded_file(file, upload_dir, 'image')
                if file_path:
                    media_files.append(file_path)
        elif media_type == 'video':
            files = request.files.getlist('videos')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'work_orders')
                file_path = save_uploaded_file(file, upload_dir, 'video')
                if file_path:
                    media_files.append(file_path)
        elif media_type == 'voice':
            files = request.files.getlist('voice_notes')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'work_orders')
                file_path = save_uploaded_file(file, upload_dir, 'audio')
                if file_path:
                    media_files.append(file_path)
        
        # Update work order with new media
        if media_files:
            current_media = getattr(work_order, f'{media_type}s', '') or ''
            updated_media = ','.join([current_media, *media_files]) if current_media else ','.join(media_files)
            setattr(work_order, f'{media_type}s', updated_media)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(media_files)} {media_type}(s) uploaded successfully',
            'uploaded_files': media_files
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500

@app.route('/api/work-orders/<int:work_order_id>/comments/<int:comment_id>/upload-media', methods=['POST'])
@login_required
def api_upload_comment_media(work_order_id, comment_id):
    """API endpoint for uploading media to comments"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    comment = WorkOrderComment.query.get_or_404(comment_id)
    
    if comment.work_order_id != work_order_id:
        return jsonify({'success': False, 'message': 'Comment not found'}), 404
    
    try:
        media_type = request.form.get('media_type', 'image')
        media_files = []
        
        if media_type == 'image':
            files = request.files.getlist('images')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'comments')
                file_path = save_uploaded_file(file, upload_dir, 'image')
                if file_path:
                    media_files.append(file_path)
        elif media_type == 'video':
            files = request.files.getlist('videos')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'comments')
                file_path = save_uploaded_file(file, upload_dir, 'video')
                if file_path:
                    media_files.append(file_path)
        elif media_type == 'voice':
            files = request.files.getlist('voice_notes')
            for file in files:
                upload_dir = os.path.join(app.static_folder or '', 'uploads', 'comments')
                file_path = save_uploaded_file(file, upload_dir, 'audio')
                if file_path:
                    media_files.append(file_path)
        
        # Update comment with new media
        if media_files:
            current_media = getattr(comment, f'{media_type}s', '') or ''
            updated_media = ','.join([current_media, *media_files]) if current_media else ','.join(media_files)
            setattr(comment, f'{media_type}s', updated_media)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(media_files)} {media_type}(s) uploaded successfully',
            'uploaded_files': media_files
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500

@app.route('/api/work-orders/<int:work_order_id>/sync-offline-data', methods=['POST'])
@login_required
def api_sync_offline_data(work_order_id):
    """API endpoint for syncing offline work order data"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    try:
        data = request.get_json()
        
        # Update work order status if provided
        if 'status' in data:
            work_order.status = data['status']
            if data['status'] == 'in_progress' and not work_order.actual_start_time:
                work_order.actual_start_time = datetime.utcnow()
            elif data['status'] == 'completed' and not work_order.actual_end_time:
                work_order.actual_end_time = datetime.utcnow()
                if work_order.actual_start_time:
                    work_order.actual_duration = int((work_order.actual_end_time - work_order.actual_start_time).total_seconds() / 60)
        
        # Update completion notes if provided
        if 'completion_notes' in data:
            work_order.completion_notes = data['completion_notes']
        
        # Handle offline media uploads
        if 'offline_media' in data:
            for media_item in data['offline_media']:
                media_type = media_item.get('type')  # image, video, voice
                file_data = media_item.get('file_data')  # Base64 encoded file
                
                if media_type and file_data:
                    # Decode and save file
                    import base64
                    file_bytes = base64.b64decode(file_data.split(',')[1])
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{timestamp}_offline_{media_type}.{media_item.get('extension', 'jpg')}"
                    
                    upload_dir = os.path.join(app.static_folder or '', 'uploads', 'work_orders')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_bytes)
                    
                    # Update work order media
                    media_path = f"uploads/work_orders/{filename}"
                    current_media = getattr(work_order, f'{media_type}s', '') or ''
                    updated_media = ','.join([current_media, media_path]) if current_media else media_path
                    setattr(work_order, f'{media_type}s', updated_media)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Offline data synced successfully',
            'work_order': work_order.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Sync failed: {str(e)}'
        }), 500

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Flask-WTF Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    organization_type = SelectField('I want to:', choices=[
        ('new_org', 'Start a new organization'),
        ('existing_org', 'Join an existing organization')
    ], validators=[DataRequired()])
    company_id = SelectField('Select Organization', coerce=int, validators=[Optional()])
    new_company = StringField('Organization Name', validators=[Optional()])
    submit = SubmitField('Create Account')

class ProfileEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    department = StringField('Department', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class DeleteAccountForm(FlaskForm):
    confirm_text = StringField('Type "DELETE" to confirm', validators=[DataRequired()])
    password = PasswordField('Your Password', validators=[DataRequired()])
    submit = SubmitField('Delete Account')

class LocationForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired(), Length(max=200)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State/Province', validators=[Optional(), Length(max=50)])
    zip_code = StringField('ZIP/Postal Code', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    latitude = FloatField('Latitude', validators=[Optional()])
    longitude = FloatField('Longitude', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=20)])
    contact_email = StringField('Contact Email', validators=[Optional(), Email(), Length(max=120)])
    submit = SubmitField('Save Location')

class MaintenanceScheduleForm(FlaskForm):
    frequency = SelectField('Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')], validators=[DataRequired()])
    frequency_value = IntegerField('Every X (days/weeks/months/years)', default=1, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    estimated_duration = IntegerField('Estimated Duration (minutes)', validators=[Optional()])
    next_due = DateTimeField('Next Due', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    sop_id = SelectField('Standard Operating Procedure (SOP)', coerce=int, validators=[Optional()])
    assigned_team_id = SelectField('Assign to Team', coerce=int, validators=[Optional()])
    is_active = BooleanField('Is Active', default=True)
    submit = SubmitField('Save')

class SOPForm(FlaskForm):
    name = StringField('SOP Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('PM', 'Preventive Maintenance'),
        ('Safety', 'Safety Procedure'),
        ('Operation', 'Operation Procedure'),
        ('Emergency', 'Emergency Procedure'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    equipment_id = SelectField('Equipment', coerce=int, validators=[Optional()])
    estimated_duration = IntegerField('Estimated Duration (minutes)', validators=[Optional()])
    safety_notes = TextAreaField('Safety Notes', validators=[Optional()])
    required_tools = TextAreaField('Required Tools', validators=[Optional()])
    required_parts = TextAreaField('Required Parts', validators=[Optional()])
    is_active = BooleanField('Is Active', default=True)
    submit = SubmitField('Save')

class SOPChecklistItemForm(FlaskForm):
    description = TextAreaField('Checklist Item Description', validators=[DataRequired()])
    order = IntegerField('Order', validators=[DataRequired()])
    is_required = BooleanField('Required', default=True)
    expected_result = TextAreaField('Expected Result', validators=[Optional()])
    submit = SubmitField('Add Item')

class TeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    members = SelectMultipleField('Add Members', coerce=int, validators=[Optional()])
    submit = SubmitField('Save')

# Google OAuth blueprint
app.config['OAUTHLIB_INSECURE_TRANSPORT'] = True  # Remove in production

google_bp = make_google_blueprint(
    client_id=app.config.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=app.config.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    companies = Company.query.all()
    form.company_id.choices = [(0, '--- Select an organization ---')] + [(c.id, c.name) for c in companies]
    
    if form.validate_on_submit():
        # Handle organization selection based on type
        if form.organization_type.data == 'new_org':
            if not form.new_company.data:
                flash('Please enter your organization name.', 'error')
                return render_template('signup.html', form=form)
            # Create new organization
            company = Company(name=form.new_company.data)
            db.session.add(company)
            db.session.commit()
            company_id = company.id
        else:  # existing_org
            if not form.company_id.data:
                flash('Please select an organization to join.', 'error')
                return render_template('signup.html', form=form)
            company_id = form.company_id.data
        
        # Check for existing user
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'error')
            return render_template('signup.html', form=form)
        
        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            company_id=company_id
        )
        
        # Set admin role for the first user of a new organization
        if form.organization_type.data == 'new_org':
            user.role = 'admin'
        
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        if form.organization_type.data == 'new_org':
            flash(f'Account created successfully! Welcome to {form.new_company.data}. You are now the administrator. Please log in.', 'success')
        else:
            flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html', form=form)

@app.route('/login/google')
def login_google():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        flash('Failed to fetch user info from Google.', 'error')
        return redirect(url_for('login'))
    info = resp.json()
    user = User.query.filter_by(email=info['email']).first()
    if not user:
        user = User(
            username=info.get('email').split('@')[0],
            email=info.get('email'),
            first_name=info.get('given_name', ''),
            last_name=info.get('family_name', ''),
            google_id=info.get('id')
        )
        db.session.add(user)
        db.session.commit()
    login_user(user)
    flash('Logged in with Google!', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Edit user profile"""
    form = ProfileEditForm(obj=current_user)
    
    if form.validate_on_submit():
        # Check if username or email already exists (excluding current user)
        existing_user = User.query.filter(
            db.and_(
                db.or_(User.username == form.username.data, User.email == form.email.data),
                User.id != current_user.id
            )
        ).first()
        
        if existing_user:
            if existing_user.username == form.username.data:
                flash('Username already taken.', 'error')
            else:
                flash('Email already registered.', 'error')
            return render_template('profile_edit.html', form=form)
        
        # Update user information
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.department = form.department.data
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile_edit.html', form=form)

@app.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('change_password.html', form=form)

@app.route('/profile/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """Delete user account"""
    form = DeleteAccountForm()
    
    if form.validate_on_submit():
        if form.confirm_text.data != 'DELETE':
            flash('Please type "DELETE" to confirm account deletion.', 'error')
            return render_template('delete_account.html', form=form)
        
        if not current_user.check_password(form.password.data):
            flash('Password is incorrect.', 'error')
            return render_template('delete_account.html', form=form)
        
        # Get user ID before deletion for logout
        user_id = current_user.id
        
        # Delete user (this will cascade to related records)
        db.session.delete(current_user)
        db.session.commit()
        
        # Logout the user
        logout_user()
        flash('Your account has been deleted successfully.', 'success')
        return redirect(url_for('login'))
    
    return render_template('delete_account.html', form=form)

# Location routes
@app.route('/locations')
@login_required
def locations_list():
    """List all locations"""
    search_query = request.args.get('search', '').strip()
    query = filter_by_company(Location.query)
    if search_query:
        query = query.filter(
            db.or_(
                Location.name.ilike(f'%{search_query}%'),
                Location.city.ilike(f'%{search_query}%'),
                Location.state.ilike(f'%{search_query}%'),
                Location.contact_person.ilike(f'%{search_query}%')
            )
        )
    locations = query.all()
    return render_template('locations/list.html', locations=locations)

@app.route('/locations/new', methods=['GET', 'POST'])
@login_required
def location_new():
    """Create new location"""
    form = LocationForm()
    
    if form.validate_on_submit():
        location = Location(
            name=form.name.data,
            address=form.address.data,
            city=form.city.data,
            state=form.state.data,
            zip_code=form.zip_code.data,
            country=form.country.data or 'USA',
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            description=form.description.data,
            contact_person=form.contact_person.data,
            contact_phone=form.contact_phone.data,
            contact_email=form.contact_email.data
        )
        db.session.add(location)
        db.session.commit()
        flash('Location created successfully!', 'success')
        return redirect(url_for('locations_list'))
    
    return render_template('locations/new.html', form=form)

@app.route('/locations/<int:id>')
@login_required
def location_detail(id):
    """Location detail page"""
    location = Location.query.get_or_404(id)
    enforce_company_access(location)
    return render_template('locations/detail.html', location=location)

@app.route('/locations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def location_edit(id):
    """Edit location"""
    location = Location.query.get_or_404(id)
    enforce_company_access(location)
    form = LocationForm(obj=location)
    
    if form.validate_on_submit():
        location.name = form.name.data
        location.address = form.address.data
        location.city = form.city.data
        location.state = form.state.data
        location.zip_code = form.zip_code.data
        location.country = form.country.data or 'USA'
        location.latitude = form.latitude.data
        location.longitude = form.longitude.data
        location.description = form.description.data
        location.contact_person = form.contact_person.data
        location.contact_phone = form.contact_phone.data
        location.contact_email = form.contact_email.data
        
        db.session.commit()
        flash('Location updated successfully!', 'success')
        return redirect(url_for('location_detail', id=id))
    
    return render_template('locations/edit.html', form=form, location=location)

@app.route('/locations/<int:id>/delete', methods=['POST'])
@login_required
def location_delete(id):
    """Delete location"""
    location = Location.query.get_or_404(id)
    enforce_company_access(location)
    db.session.delete(location)
    db.session.commit()
    flash('Location deleted!', 'success')
    return redirect(url_for('locations_list'))

@app.route('/maps')
@login_required
def maps():
    """Interactive maps page showing all locations (company-scoped)"""
    locations = filter_by_company(Location.query).filter_by(is_active=True).all()
    locations_data = [loc.to_dict() for loc in locations]
    return render_template('maps.html', locations=locations_data)

@app.route('/equipment/<int:id>/maintenance-schedule/new', methods=['GET', 'POST'])
@login_required
def maintenance_schedule_new(id):
    equipment = Equipment.query.get_or_404(id)
    form = MaintenanceScheduleForm()
    
    # Populate form choices
    form.sop_id.choices = [(0, '-- Select SOP --')] + [(s.id, s.name) for s in SOP.query.filter_by(is_active=True).order_by(SOP.name).all()]
    form.assigned_team_id.choices = [(0, '-- Select Team --')] + [(t.id, t.name) for t in Team.query.order_by(Team.name).all()]
    
    if form.validate_on_submit():
        schedule = MaintenanceSchedule(
            equipment_id=equipment.id,
            frequency=form.frequency.data,
            frequency_value=form.frequency_value.data,
            description=form.description.data,
            estimated_duration=form.estimated_duration.data,
            next_due=form.next_due.data,
            sop_id=form.sop_id.data if form.sop_id.data != 0 else None,
            assigned_team_id=form.assigned_team_id.data if form.assigned_team_id.data != 0 else None,
            is_active=form.is_active.data
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Maintenance schedule created!', 'success')
        return redirect(url_for('equipment_detail', id=equipment.id))
    return render_template('maintenance_schedule_form.html', form=form, equipment=equipment, action='new')

@app.route('/equipment/<int:id>/maintenance-schedule/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
def maintenance_schedule_edit(id, schedule_id):
    equipment = Equipment.query.get_or_404(id)
    schedule = MaintenanceSchedule.query.get_or_404(schedule_id)
    form = MaintenanceScheduleForm(obj=schedule)
    
    # Populate form choices
    form.sop_id.choices = [(0, '-- Select SOP --')] + [(s.id, s.name) for s in SOP.query.filter_by(is_active=True).order_by(SOP.name).all()]
    form.assigned_team_id.choices = [(0, '-- Select Team --')] + [(t.id, t.name) for t in Team.query.order_by(Team.name).all()]
    
    if form.validate_on_submit():
        schedule.frequency = form.frequency.data
        schedule.frequency_value = form.frequency_value.data
        schedule.description = form.description.data
        schedule.estimated_duration = form.estimated_duration.data
        schedule.next_due = form.next_due.data
        schedule.sop_id = form.sop_id.data if form.sop_id.data != 0 else None
        schedule.assigned_team_id = form.assigned_team_id.data if form.assigned_team_id.data != 0 else None
        schedule.is_active = form.is_active.data
        db.session.commit()
        flash('Maintenance schedule updated!', 'success')
        return redirect(url_for('equipment_detail', id=equipment.id))
    return render_template('maintenance_schedule_form.html', form=form, equipment=equipment, action='edit')

@app.route('/equipment/<int:id>/maintenance-schedule/<int:schedule_id>/delete', methods=['POST'])
@login_required
def maintenance_schedule_delete(id, schedule_id):
    equipment = Equipment.query.get_or_404(id)
    schedule = MaintenanceSchedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash('Maintenance schedule deleted!', 'success')
    return redirect(url_for('equipment_detail', id=equipment.id))

@app.route('/teams', methods=['GET', 'POST'])
@login_required
def teams():
    users = filter_by_company(User.query).order_by(User.first_name, User.last_name).all()
    teams = filter_by_company(Team.query).order_by(Team.name).all()
    search_user = request.args.get('search_user', '').strip().lower()
    search_team = request.args.get('search_team', '').strip().lower()
    filtered_users = [u for u in users if search_user in (u.first_name + ' ' + u.last_name + ' ' + u.username).lower()] if search_user else users
    filtered_teams = [t for t in teams if search_team in t.name.lower()] if search_team else teams
    return render_template('teams.html', users=filtered_users, teams=filtered_teams)

@app.route('/teams/create', methods=['GET', 'POST'])
@login_required
def create_team():
    form = TeamForm()
    form.members.choices = [(u.id, f"{u.first_name} {u.last_name} ({u.username})") for u in User.query.order_by(User.first_name, User.last_name).all()]
    if form.validate_on_submit():
        team = Team(name=form.name.data, description=form.description.data)
        team.members = User.query.filter(User.id.in_(form.members.data)).all()
        db.session.add(team)
        db.session.commit()
        flash('Team created!', 'success')
        return redirect(url_for('teams'))
    return render_template('team_form.html', form=form, action='create')

@app.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    enforce_company_access(team)
    form = TeamForm(obj=team)
    form.members.choices = [(u.id, f"{u.first_name} {u.last_name} ({u.username})") for u in filter_by_company(User.query).order_by(User.first_name, User.last_name).all()]
    if request.method == 'GET':
        form.members.data = [u.id for u in team.members]
    if form.validate_on_submit():
        team.name = form.name.data
        team.description = form.description.data
        team.members = User.query.filter(User.id.in_(form.members.data)).all()
        db.session.commit()
        flash('Team updated!', 'success')
        return redirect(url_for('teams'))
    return render_template('team_form.html', form=form, action='edit', team=team)

@app.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    enforce_company_access(team)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted!', 'success')
    return redirect(url_for('teams'))

@app.route('/teams/<int:team_id>/add_member', methods=['POST'])
@login_required
def add_member_to_team(team_id):
    team = Team.query.get_or_404(team_id)
    user_id = int(request.form.get('user_id'))
    user = User.query.get(user_id)
    if user and user not in team.members:
        team.members.append(user)
        db.session.commit()
        flash('User added to team!', 'success')
    return redirect(url_for('teams'))

@app.route('/teams/<int:team_id>/remove_member', methods=['POST'])
@login_required
def remove_member_from_team(team_id):
    team = Team.query.get_or_404(team_id)
    user_id = int(request.form.get('user_id'))
    user = User.query.get(user_id)
    if user and user in team.members:
        team.members.remove(user)
        db.session.commit()
        flash('User removed from team!', 'success')
    return redirect(url_for('teams'))

# SOP Routes
@app.route('/sops')
@login_required
def sops_list():
    """List all SOPs"""
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    query = filter_by_company(SOP.query)
    if search:
        query = query.filter(
            db.or_(
                SOP.name.ilike(f'%{search}%'),
                SOP.description.ilike(f'%{search}%')
            )
        )
    if category_filter:
        query = query.filter(SOP.category == category_filter)
    sops = query.order_by(SOP.name).all()
    categories = query.with_entities(SOP.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    return render_template('sops/list.html', sops=sops, categories=categories)

@app.route('/sops/new', methods=['GET', 'POST'])
@login_required
def sop_new():
    """Create new SOP"""
    form = SOPForm()
    form.equipment_id.choices = [(0, '-- Select Equipment --')] + [(e.id, e.name) for e in Equipment.query.order_by(Equipment.name).all()]
    
    if form.validate_on_submit():
        sop = SOP(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            equipment_id=form.equipment_id.data if form.equipment_id.data != 0 else None,
            estimated_duration=form.estimated_duration.data,
            safety_notes=form.safety_notes.data,
            required_tools=form.required_tools.data,
            required_parts=form.required_parts.data,
            is_active=form.is_active.data,
            created_by_id=current_user.id
        )
        db.session.add(sop)
        db.session.commit()
        flash('SOP created successfully!', 'success')
        return redirect(url_for('sop_detail', id=sop.id))
    
    return render_template('sops/new.html', form=form)

@app.route('/sops/<int:id>')
@login_required
def sop_detail(id):
    """View SOP details"""
    sop = SOP.query.get_or_404(id)
    return render_template('sops/detail.html', sop=sop)

@app.route('/sops/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def sop_edit(id):
    """Edit SOP"""
    sop = SOP.query.get_or_404(id)
    enforce_company_access(sop)
    form = SOPForm(obj=sop)
    form.equipment_id.choices = [(0, '-- Select Equipment --')] + [(e.id, e.name) for e in Equipment.query.order_by(Equipment.name).all()]
    
    if form.validate_on_submit():
        sop.name = form.name.data
        sop.description = form.description.data
        sop.category = form.category.data
        sop.equipment_id = form.equipment_id.data if form.equipment_id.data != 0 else None
        sop.estimated_duration = form.estimated_duration.data
        sop.safety_notes = form.safety_notes.data
        sop.required_tools = form.required_tools.data
        sop.required_parts = form.required_parts.data
        sop.is_active = form.is_active.data
        
        db.session.commit()
        flash('SOP updated successfully!', 'success')
        return redirect(url_for('sop_detail', id=sop.id))
    
    return render_template('sops/edit.html', form=form, sop=sop)

@app.route('/sops/<int:id>/delete', methods=['POST'])
@login_required
def sop_delete(id):
    """Delete SOP"""
    sop = SOP.query.get_or_404(id)
    enforce_company_access(sop)
    db.session.delete(sop)
    db.session.commit()
    flash('SOP deleted successfully!', 'success')
    return redirect(url_for('sops_list'))

@app.route('/sops/<int:id>/add-checklist-item', methods=['POST'])
@login_required
def sop_add_checklist_item(id):
    """Add checklist item to SOP"""
    sop = SOP.query.get_or_404(id)
    form = SOPChecklistItemForm()
    
    if form.validate_on_submit():
        item = SOPChecklistItem(
            sop_id=sop.id,
            description=form.description.data,
            order=form.order.data,
            is_required=form.is_required.data,
            expected_result=form.expected_result.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Checklist item added successfully!', 'success')
    
    return redirect(url_for('sop_detail', id=sop.id))

@app.route('/sops/<int:id>/delete-checklist-item/<int:item_id>', methods=['POST'])
@login_required
def sop_delete_checklist_item(id, item_id):
    """Delete checklist item from SOP"""
    item = SOPChecklistItem.query.get_or_404(item_id)
    if item.sop_id != id:
        abort(404)
    
    db.session.delete(item)
    db.session.commit()
    flash('Checklist item deleted successfully!', 'success')
    return redirect(url_for('sop_detail', id=id))

# Calendar view for maintenance schedules
@app.route('/calendar')
@login_required
def maintenance_calendar():
    """Calendar view of upcoming maintenance tasks"""
    # Get date range for calendar (current month by default)
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Get all active maintenance schedules
    schedules = MaintenanceSchedule.query.filter_by(is_active=True).all()
    
    # Generate calendar events
    calendar_events = []
    for schedule in schedules:
        if schedule.next_due:
            calendar_events.append({
                'id': schedule.id,
                'title': f"{schedule.equipment.name if schedule.equipment else 'Unknown'} - {schedule.description}",
                'start': schedule.next_due.isoformat(),
                'end': (schedule.next_due + timedelta(minutes=schedule.estimated_duration or 60)).isoformat(),
                'equipment_name': schedule.equipment.name if schedule.equipment else 'Unknown',
                'description': schedule.description,
                'assigned_team': schedule.assigned_team.name if schedule.assigned_team else None,
                'sop_name': schedule.sop.name if schedule.sop else None,
                'url': url_for('equipment_detail', id=schedule.equipment_id)
            })
    
    return render_template('maintenance_calendar.html', 
                         calendar_events=calendar_events,
                         year=year, 
                         month=month)

@app.route('/maintenance-schedule/<int:schedule_id>/create-work-order', methods=['POST'])
@login_required
def create_work_order_from_schedule(schedule_id):
    """Create a work order from a maintenance schedule"""
    schedule = MaintenanceSchedule.query.get_or_404(schedule_id)
    
    # Generate work order number
    work_order_number = generate_work_order_number()
    
    # Create work order
    work_order = WorkOrder(
        work_order_number=work_order_number,
        title=f"PM: {schedule.description}",
        description=f"Preventive maintenance task: {schedule.description}",
        priority='medium',
        status='open',
        type='preventive',
        equipment_id=schedule.equipment_id,
        assigned_technician_id=schedule.assigned_team.members[0].id if schedule.assigned_team and schedule.assigned_team.members else None,
        assigned_team_id=schedule.assigned_team_id,
        created_by_id=current_user.id,
        scheduled_date=schedule.next_due,
        due_date=schedule.next_due + timedelta(hours=2) if schedule.next_due else None,
        estimated_duration=schedule.estimated_duration
    )
    
    db.session.add(work_order)
    db.session.flush()  # Get the work order ID
    
    # Create checklist items from SOP if available
    if schedule.sop:
        for checklist_item in schedule.sop.checklist_items:
            work_order_checklist = WorkOrderChecklist(
                work_order_id=work_order.id,
                sop_checklist_item_id=checklist_item.id
            )
            db.session.add(work_order_checklist)
    
    # Update maintenance schedule
    schedule.last_performed = datetime.utcnow()
    
    # Calculate next due date based on frequency
    if schedule.next_due:
        if schedule.frequency == 'daily':
            schedule.next_due = schedule.next_due + timedelta(days=schedule.frequency_value)
        elif schedule.frequency == 'weekly':
            schedule.next_due = schedule.next_due + timedelta(weeks=schedule.frequency_value)
        elif schedule.frequency == 'monthly':
            # Simple month calculation (30 days)
            schedule.next_due = schedule.next_due + timedelta(days=30 * schedule.frequency_value)
        elif schedule.frequency == 'yearly':
            schedule.next_due = schedule.next_due + timedelta(days=365 * schedule.frequency_value)
    
    db.session.commit()
    
    flash(f'Work order {work_order_number} created from maintenance schedule!', 'success')
    return redirect(url_for('work_order_detail', id=work_order.id))

# Mobile Technician Routes
@app.route('/mobile')
def mobile_home():
    """Mobile home page - redirects to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('mobile_dashboard'))
    return redirect(url_for('mobile_login'))

@app.route('/mobile/login', methods=['GET', 'POST'])
def mobile_login():
    """Mobile-optimized login page"""
    if current_user.is_authenticated:
        return redirect(url_for('mobile_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('mobile_dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('mobile/login.html')

@app.route('/mobile/dashboard')
@login_required
def mobile_dashboard():
    """Mobile dashboard showing assigned tasks"""
    # Get work orders assigned to current user (technician or team member)
    assigned_work_orders = filter_by_company(WorkOrder.query).filter(
        db.or_(
            WorkOrder.assigned_technician_id == current_user.id,
            WorkOrder.assigned_team_id.in_([team.id for team in current_user.teams])
        )
    ).filter(
        WorkOrder.status.in_(['open', 'in_progress'])
    ).order_by(WorkOrder.priority.desc(), WorkOrder.due_date.asc()).all()
    
    # Get completed work orders from today
    today = datetime.now().date()
    completed_today = filter_by_company(WorkOrder.query).filter(
        db.or_(
            WorkOrder.assigned_technician_id == current_user.id,
            WorkOrder.assigned_team_id.in_([team.id for team in current_user.teams])
        )
    ).filter(
        WorkOrder.status == 'completed',
        db.func.date(WorkOrder.actual_end_time) == today
    ).count()
    
    return render_template('mobile/dashboard.html', 
                         work_orders=assigned_work_orders,
                         completed_today=completed_today)

@app.route('/mobile/tasks')
@login_required
def mobile_tasks():
    """Mobile task list with filtering options"""
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    query = filter_by_company(WorkOrder.query).filter(
        db.or_(
            WorkOrder.assigned_technician_id == current_user.id,
            WorkOrder.assigned_team_id.in_([team.id for team in current_user.teams])
        )
    )
    
    if status_filter != 'all':
        query = query.filter(WorkOrder.status == status_filter)
    
    if priority_filter != 'all':
        query = query.filter(WorkOrder.priority == priority_filter)
    
    work_orders = query.order_by(WorkOrder.priority.desc(), WorkOrder.due_date.asc()).all()
    
    return render_template('mobile/tasks.html', 
                         work_orders=work_orders,
                         status_filter=status_filter,
                         priority_filter=priority_filter)

@app.route('/mobile/task/<int:work_order_id>')
@login_required
def mobile_task_detail(work_order_id):
    """Mobile-optimized task detail view"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    # Check if user is assigned to this work order
    if (work_order.assigned_technician_id != current_user.id and 
        work_order.assigned_team_id not in [team.id for team in current_user.teams]):
        abort(403)
    
    return render_template('mobile/task_detail.html', work_order=work_order)

@app.route('/mobile/task/<int:work_order_id>/start', methods=['POST'])
@login_required
def mobile_start_task(work_order_id):
    """Start a work order task"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    # Check if user is assigned to this work order
    if (work_order.assigned_technician_id != current_user.id and 
        work_order.assigned_team_id not in [team.id for team in current_user.teams]):
        abort(403)
    
    if work_order.status == 'open':
        work_order.status = 'in_progress'
        work_order.actual_start_time = datetime.utcnow()
        db.session.commit()
        flash('Task started successfully!', 'success')
    
    return redirect(url_for('mobile_task_detail', work_order_id=work_order_id))

@app.route('/mobile/task/<int:work_order_id>/complete', methods=['POST'])
@login_required
def mobile_complete_task(work_order_id):
    """Complete a work order task with proof upload"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    # Check if user is assigned to this work order
    if (work_order.assigned_technician_id != current_user.id and 
        work_order.assigned_team_id not in [team.id for team in current_user.teams]):
        abort(403)
    
    if request.method == 'POST':
        # Handle proof image uploads
        proof_images = []
        if 'proof_images' in request.files:
            uploaded_files = request.files.getlist('proof_images')
            for file in uploaded_files:
                file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'work_orders'), 'image')
                if file_path:
                    proof_images.append(file_path)
        
        # Update work order
        work_order.status = 'completed'
        work_order.actual_end_time = datetime.utcnow()
        if work_order.actual_start_time:
            work_order.actual_duration = int((work_order.actual_end_time - work_order.actual_start_time).total_seconds() / 60)
        
        work_order.completion_notes = request.form.get('completion_notes', '')
        
        # Add proof images to existing images
        if proof_images:
            current_images = work_order.images or ''
            updated_images = ','.join([current_images, *proof_images]) if current_images else ','.join(proof_images)
            work_order.images = updated_images
        
        db.session.commit()
        flash('Task completed successfully!', 'success')
        return redirect(url_for('mobile_dashboard'))
    
    return render_template('mobile/complete_task.html', work_order=work_order)

@app.route('/mobile/task/<int:work_order_id>/add-proof', methods=['POST'])
@login_required
def mobile_add_proof(work_order_id):
    """Add proof images to an existing work order"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    # Check if user is assigned to this work order
    if (work_order.assigned_technician_id != current_user.id and 
        work_order.assigned_team_id not in [team.id for team in current_user.teams]):
        abort(403)
    
    # Handle proof image uploads
    proof_images = []
    if 'proof_images' in request.files:
        uploaded_files = request.files.getlist('proof_images')
        for file in uploaded_files:
            file_path = save_uploaded_file(file, os.path.join(app.static_folder, 'uploads', 'work_orders'), 'image')
            if file_path:
                proof_images.append(file_path)
    
    if proof_images:
        # Add proof images to existing images
        current_images = work_order.images or ''
        updated_images = ','.join([current_images, *proof_images]) if current_images else ','.join(proof_images)
        work_order.images = updated_images
        db.session.commit()
        flash('Proof images added successfully!', 'success')
    
    return redirect(url_for('mobile_task_detail', work_order_id=work_order_id))

@app.route('/mobile/profile')
@login_required
def mobile_profile():
    """Mobile profile view"""
    return render_template('mobile/profile.html')

@app.route('/mobile/logout')
@login_required
def mobile_logout():
    """Mobile logout"""
    logout_user()
    return redirect(url_for('mobile_login'))

# API endpoints for mobile app
@app.route('/api/mobile/tasks')
@login_required
def api_mobile_tasks():
    """API endpoint for mobile task list"""
    work_orders = filter_by_company(WorkOrder.query).filter(
        db.or_(
            WorkOrder.assigned_technician_id == current_user.id,
            WorkOrder.assigned_team_id.in_([team.id for team in current_user.teams])
        )
    ).filter(
        WorkOrder.status.in_(['open', 'in_progress'])
    ).order_by(WorkOrder.priority.desc(), WorkOrder.due_date.asc()).all()
    
    return jsonify([{
        'id': wo.id,
        'title': wo.title,
        'priority': wo.priority,
        'status': wo.status,
        'due_date': wo.due_date.isoformat() if wo.due_date else None,
        'equipment_name': wo.equipment.name if wo.equipment else None,
        'has_images': bool(wo.images),
        'has_videos': bool(wo.videos),
        'has_voice_notes': bool(wo.voice_notes)
    } for wo in work_orders])

@app.route('/api/mobile/task/<int:work_order_id>')
@login_required
def api_mobile_task_detail(work_order_id):
    """API endpoint for mobile task detail"""
    work_order = WorkOrder.query.get_or_404(work_order_id)
    
    # Check if user is assigned to this work order
    if (work_order.assigned_technician_id != current_user.id and 
        work_order.assigned_team_id not in [team.id for team in current_user.teams]):
        abort(403)
    
    return jsonify({
        'id': work_order.id,
        'title': work_order.title,
        'description': work_order.description,
        'priority': work_order.priority,
        'status': work_order.status,
        'type': work_order.type,
        'equipment': {
            'id': work_order.equipment.id,
            'name': work_order.equipment.name,
            'location': work_order.equipment.location
        } if work_order.equipment else None,
        'scheduled_date': work_order.scheduled_date.isoformat() if work_order.scheduled_date else None,
        'due_date': work_order.due_date.isoformat() if work_order.due_date else None,
        'estimated_duration': work_order.estimated_duration,
        'actual_duration': work_order.actual_duration,
        'completion_notes': work_order.completion_notes,
        'images': work_order.images.split(',') if work_order.images else [],
        'videos': work_order.videos.split(',') if work_order.videos else [],
        'voice_notes': work_order.voice_notes.split(',') if work_order.voice_notes else [],
        'created_at': work_order.created_at.isoformat(),
        'actual_start_time': work_order.actual_start_time.isoformat() if work_order.actual_start_time else None,
        'actual_end_time': work_order.actual_end_time.isoformat() if work_order.actual_end_time else None
    })

# Reporting and Analytics Routes
@app.route('/reports')
@login_required
def reports_dashboard():
    """Main reports dashboard"""
    # Get basic metrics
    total_work_orders = filter_by_company(WorkOrder.query).count()
    completed_work_orders = filter_by_company(WorkOrder.query).filter_by(status='completed').count()
    on_time_work_orders = filter_by_company(WorkOrder.query).filter(
        WorkOrder.status == 'completed',
        WorkOrder.actual_end_time <= WorkOrder.due_date
    ).count()
    
    # Calculate percentages
    completion_rate = (completed_work_orders / total_work_orders * 100) if total_work_orders > 0 else 0
    on_time_rate = (on_time_work_orders / completed_work_orders * 100) if completed_work_orders > 0 else 0
    
    # Get recent activity
    recent_work_orders = filter_by_company(WorkOrder.query).order_by(WorkOrder.created_at.desc()).limit(10).all()
    
    # Get equipment performance
    equipment_stats = db.session.query(
        Equipment.name,
        db.func.count(WorkOrder.id).label('total_tasks'),
        db.func.avg(WorkOrder.actual_duration).label('avg_duration')
    ).join(WorkOrder).group_by(Equipment.id).all()
    
    return render_template('reports/dashboard.html',
                         total_work_orders=total_work_orders,
                         completed_work_orders=completed_work_orders,
                         completion_rate=completion_rate,
                         on_time_rate=on_time_rate,
                         recent_work_orders=recent_work_orders,
                         equipment_stats=equipment_stats)

@app.route('/reports/task-logs')
@login_required
def task_logs():
    """Task logs with filtering and export options"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    equipment_id = request.args.get('equipment_id', 'all')
    assigned_to = request.args.get('assigned_to', 'all')
    
    # Build query
    query = filter_by_company(WorkOrder.query)
    
    if start_date:
        query = query.filter(WorkOrder.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(WorkOrder.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if status != 'all':
        query = query.filter(WorkOrder.status == status)
    if priority != 'all':
        query = query.filter(WorkOrder.priority == priority)
    if equipment_id != 'all':
        query = query.filter(WorkOrder.equipment_id == equipment_id)
    if assigned_to != 'all':
        query = query.filter(WorkOrder.assigned_technician_id == assigned_to)
    
    work_orders = query.order_by(WorkOrder.created_at.desc()).all()
    
    # Get filter options
    equipment_list = Equipment.query.all()
    users_list = User.query.filter_by(role='technician').all()
    
    return render_template('reports/task_logs.html',
                         work_orders=work_orders,
                         equipment_list=equipment_list,
                         users_list=users_list,
                         filters={
                             'start_date': start_date,
                             'end_date': end_date,
                             'status': status,
                             'priority': priority,
                             'equipment_id': equipment_id,
                             'assigned_to': assigned_to
                         })

@app.route('/reports/performance-metrics')
@login_required
def performance_metrics():
    """Detailed performance metrics and analytics"""
    # Time period filter
    period = request.args.get('period', '30')  # days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(period))
    
    # Get work orders in period
    work_orders = filter_by_company(WorkOrder.query).filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at <= end_date
    ).all()
    
    # Calculate metrics
    total_tasks = len(work_orders)
    completed_tasks = len([wo for wo in work_orders if wo.status == 'completed'])
    on_time_tasks = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
    
    # Calculate percentages
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    on_time_rate = (on_time_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
    
    # Equipment performance
    equipment_performance = {}
    for wo in work_orders:
        if wo.equipment:
            if wo.equipment.name not in equipment_performance:
                equipment_performance[wo.equipment.name] = {'total': 0, 'completed': 0, 'on_time': 0}
            equipment_performance[wo.equipment.name]['total'] += 1
            if wo.status == 'completed':
                equipment_performance[wo.equipment.name]['completed'] += 1
                if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                    equipment_performance[wo.equipment.name]['on_time'] += 1
    
    # Technician performance
    technician_performance = {}
    for wo in work_orders:
        if wo.assigned_technician:
            tech_name = f"{wo.assigned_technician.first_name} {wo.assigned_technician.last_name}"
            if tech_name not in technician_performance:
                technician_performance[tech_name] = {'total': 0, 'completed': 0, 'on_time': 0}
            technician_performance[tech_name]['total'] += 1
            if wo.status == 'completed':
                technician_performance[tech_name]['completed'] += 1
                if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                    technician_performance[tech_name]['on_time'] += 1
    
    # Priority breakdown
    priority_breakdown = {}
    for wo in work_orders:
        if wo.priority not in priority_breakdown:
            priority_breakdown[wo.priority] = {'total': 0, 'completed': 0, 'on_time': 0}
        priority_breakdown[wo.priority]['total'] += 1
        if wo.status == 'completed':
            priority_breakdown[wo.priority]['completed'] += 1
            if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                priority_breakdown[wo.priority]['on_time'] += 1
    
    return render_template('reports/performance_metrics.html',
                         period=period,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         on_time_tasks=on_time_tasks,
                         completion_rate=completion_rate,
                         on_time_rate=on_time_rate,
                         equipment_performance=equipment_performance,
                         technician_performance=technician_performance,
                         priority_breakdown=priority_breakdown)

@app.route('/reports/export/csv')
@login_required
def export_csv():
    """Export task logs as CSV for compliance"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    equipment_id = request.args.get('equipment_id', 'all')
    assigned_to = request.args.get('assigned_to', 'all')
    
    # Build query
    query = filter_by_company(WorkOrder.query)
    
    if start_date:
        query = query.filter(WorkOrder.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(WorkOrder.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if status != 'all':
        query = query.filter(WorkOrder.status == status)
    if priority != 'all':
        query = query.filter(WorkOrder.priority == priority)
    if equipment_id != 'all':
        query = query.filter(WorkOrder.equipment_id == equipment_id)
    if assigned_to != 'all':
        query = query.filter(WorkOrder.assigned_technician_id == assigned_to)
    
    work_orders = query.order_by(WorkOrder.created_at.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Work Order ID',
        'Title',
        'Description',
        'Type',
        'Priority',
        'Status',
        'Equipment',
        'Location',
        'Assigned To',
        'Created Date',
        'Scheduled Date',
        'Due Date',
        'Actual Start Time',
        'Actual End Time',
        'Estimated Duration (min)',
        'Actual Duration (min)',
        'Completion Notes',
        'Images',
        'Videos',
        'Voice Notes'
    ])
    
    # Write data
    for wo in work_orders:
        writer.writerow([
            wo.work_order_number,
            wo.title,
            wo.description,
            wo.type,
            wo.priority,
            wo.status,
            wo.equipment.name if wo.equipment else 'N/A',
            wo.equipment.location if wo.equipment else 'N/A',
            f"{wo.assigned_technician.first_name} {wo.assigned_technician.last_name}" if wo.assigned_technician else 'N/A',
            wo.created_at.strftime('%Y-%m-%d %H:%M:%S') if wo.created_at else 'N/A',
            wo.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if wo.scheduled_date else 'N/A',
            wo.due_date.strftime('%Y-%m-%d %H:%M:%S') if wo.due_date else 'N/A',
            wo.actual_start_time.strftime('%Y-%m-%d %H:%M:%S') if wo.actual_start_time else 'N/A',
            wo.actual_end_time.strftime('%Y-%m-%d %H:%M:%S') if wo.actual_end_time else 'N/A',
            wo.estimated_duration if wo.estimated_duration else 'N/A',
            wo.actual_duration if wo.actual_duration else 'N/A',
            wo.completion_notes if wo.completion_notes else 'N/A',
            wo.images if wo.images else 'N/A',
            wo.videos if wo.videos else 'N/A',
            wo.voice_notes if wo.voice_notes else 'N/A'
        ])
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=task_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@app.route('/reports/export/compliance-report')
@login_required
def export_compliance_report():
    """Export comprehensive compliance report"""
    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last year
    
    # Get all work orders
    work_orders = WorkOrder.query.filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at <= end_date
    ).all()
    
    # Calculate compliance metrics
    total_tasks = len(work_orders)
    completed_tasks = len([wo for wo in work_orders if wo.status == 'completed'])
    on_time_tasks = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
    
    # Create comprehensive report
    output = StringIO()
    writer = csv.writer(output)
    
    # Report header
    writer.writerow(['CMMS Compliance Report'])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'])
    writer.writerow([])
    
    # Summary metrics
    writer.writerow(['SUMMARY METRICS'])
    writer.writerow(['Total Tasks', total_tasks])
    writer.writerow(['Completed Tasks', completed_tasks])
    writer.writerow(['On-Time Tasks', on_time_tasks])
    writer.writerow(['Completion Rate', f"{(completed_tasks/total_tasks*100):.1f}%" if total_tasks > 0 else "0%"])
    writer.writerow(['On-Time Rate', f"{(on_time_tasks/completed_tasks*100):.1f}%" if completed_tasks > 0 else "0%"])
    writer.writerow([])
    
    # Detailed task log
    writer.writerow(['DETAILED TASK LOG'])
    writer.writerow([
        'Work Order ID',
        'Title',
        'Type',
        'Priority',
        'Status',
        'Equipment',
        'Assigned To',
        'Created Date',
        'Due Date',
        'Actual End Date',
        'On Time',
        'Estimated Duration',
        'Actual Duration',
        'Variance'
    ])
    
    for wo in work_orders:
        on_time = 'Yes' if (wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date) else 'No'
        variance = ''
        if wo.estimated_duration and wo.actual_duration:
            variance = wo.actual_duration - wo.estimated_duration
        
        writer.writerow([
            wo.work_order_number,
            wo.title,
            wo.type,
            wo.priority,
            wo.status,
            wo.equipment.name if wo.equipment else 'N/A',
            f"{wo.assigned_technician.first_name} {wo.assigned_technician.last_name}" if wo.assigned_technician else 'N/A',
            wo.created_at.strftime('%Y-%m-%d') if wo.created_at else 'N/A',
            wo.due_date.strftime('%Y-%m-%d') if wo.due_date else 'N/A',
            wo.actual_end_time.strftime('%Y-%m-%d') if wo.actual_end_time else 'N/A',
            on_time,
            wo.estimated_duration if wo.estimated_duration else 'N/A',
            wo.actual_duration if wo.actual_duration else 'N/A',
            variance
        ])
    
    # Equipment performance
    writer.writerow([])
    writer.writerow(['EQUIPMENT PERFORMANCE'])
    writer.writerow(['Equipment', 'Total Tasks', 'Completed', 'On-Time', 'Completion Rate', 'On-Time Rate'])
    
    equipment_stats = {}
    for wo in work_orders:
        if wo.equipment:
            if wo.equipment.name not in equipment_stats:
                equipment_stats[wo.equipment.name] = {'total': 0, 'completed': 0, 'on_time': 0}
            equipment_stats[wo.equipment.name]['total'] += 1
            if wo.status == 'completed':
                equipment_stats[wo.equipment.name]['completed'] += 1
                if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                    equipment_stats[wo.equipment.name]['on_time'] += 1
    
    for equipment, stats in equipment_stats.items():
        completion_rate = f"{(stats['completed']/stats['total']*100):.1f}%" if stats['total'] > 0 else "0%"
        on_time_rate = f"{(stats['on_time']/stats['completed']*100):.1f}%" if stats['completed'] > 0 else "0%"
        writer.writerow([
            equipment,
            stats['total'],
            stats['completed'],
            stats['on_time'],
            completion_rate,
            on_time_rate
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@app.route('/reports/equipment-analytics')
@login_required
def equipment_analytics():
    """Equipment-specific analytics and performance"""
    equipment_id = request.args.get('equipment_id')
    
    if equipment_id:
        equipment = Equipment.query.get_or_404(equipment_id)
        work_orders = WorkOrder.query.filter_by(equipment_id=equipment_id).order_by(WorkOrder.created_at.desc()).all()
        
        # Calculate equipment metrics
        total_tasks = len(work_orders)
        completed_tasks = len([wo for wo in work_orders if wo.status == 'completed'])
        on_time_tasks = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        on_time_rate = (on_time_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
        
        # Average duration
        completed_with_duration = [wo for wo in work_orders if wo.status == 'completed' and wo.actual_duration]
        avg_duration = sum(wo.actual_duration for wo in completed_with_duration) / len(completed_with_duration) if completed_with_duration else 0
        
        # Priority breakdown
        priority_breakdown = {}
        for wo in work_orders:
            if wo.priority not in priority_breakdown:
                priority_breakdown[wo.priority] = 0
            priority_breakdown[wo.priority] += 1
        
        return render_template('reports/equipment_analytics.html',
                             equipment=equipment,
                             work_orders=work_orders,
                             total_tasks=total_tasks,
                             completed_tasks=completed_tasks,
                             on_time_tasks=on_time_tasks,
                             completion_rate=completion_rate,
                             on_time_rate=on_time_rate,
                             avg_duration=avg_duration,
                             priority_breakdown=priority_breakdown)
    
    # List all equipment with basic stats
    equipment_list = Equipment.query.all()
    equipment_stats = []
    
    for equipment in equipment_list:
        work_orders = WorkOrder.query.filter_by(equipment_id=equipment.id).all()
        total = len(work_orders)
        completed = len([wo for wo in work_orders if wo.status == 'completed'])
        on_time = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
        
        equipment_stats.append({
            'equipment': equipment,
            'total_tasks': total,
            'completed_tasks': completed,
            'on_time_tasks': on_time,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'on_time_rate': (on_time / completed * 100) if completed > 0 else 0
        })
    
    return render_template('reports/equipment_list.html', equipment_stats=equipment_stats)

# Admin Dashboard Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard with overview and quick actions"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get overview statistics
    total_equipment = Equipment.query.count()
    total_work_orders = WorkOrder.query.count()
    open_work_orders = WorkOrder.query.filter_by(status='open').count()
    in_progress_work_orders = WorkOrder.query.filter_by(status='in_progress').count()
    completed_work_orders = WorkOrder.query.filter_by(status='completed').count()
    total_technicians = User.query.filter_by(role='technician').count()
    
    # Get recent activity
    recent_work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).limit(10).all()
    recent_equipment = Equipment.query.order_by(Equipment.created_at.desc()).limit(5).all()
    
    # Get equipment by status (operational, maintenance, offline)
    operational_equipment = Equipment.query.filter_by(status='operational').count()
    maintenance_equipment = Equipment.query.filter_by(status='maintenance').count()
    offline_equipment = Equipment.query.filter_by(status='offline').count()
    
    # Get work orders by priority
    urgent_work_orders = WorkOrder.query.filter_by(priority='urgent').count()
    high_work_orders = WorkOrder.query.filter_by(priority='high').count()
    medium_work_orders = WorkOrder.query.filter_by(priority='medium').count()
    low_work_orders = WorkOrder.query.filter_by(priority='low').count()

    # Calculate real system health
    system_health_data = calculate_system_health()
    system_health = system_health_data['overall_health']
    
    # Get user counts by role
    admin_count = User.query.filter_by(role='admin').count()
    manager_count = User.query.filter_by(role='manager').count()
    technician_count = User.query.filter_by(role='technician').count()
    viewer_count = User.query.filter_by(role='viewer').count()
    
    # Get total users for the company
    total_users = filter_by_company(User.query).count()
    active_work_orders = open_work_orders + in_progress_work_orders

    return render_template('admin/dashboard.html',
                         total_equipment=total_equipment,
                         total_work_orders=total_work_orders,
                         open_work_orders=open_work_orders,
                         in_progress_work_orders=in_progress_work_orders,
                         completed_work_orders=completed_work_orders,
                         total_technicians=total_technicians,
                         recent_work_orders=recent_work_orders,
                         recent_equipment=recent_equipment,
                         operational_equipment=operational_equipment,
                         maintenance_equipment=maintenance_equipment,
                         offline_equipment=offline_equipment,
                         urgent_work_orders=urgent_work_orders,
                         high_work_orders=high_work_orders,
                         medium_work_orders=medium_work_orders,
                         low_work_orders=low_work_orders,
                         system_health=system_health,
                         system_health_data=system_health_data,
                         admin_count=admin_count,
                         manager_count=manager_count,
                         technician_count=technician_count,
                         viewer_count=viewer_count,
                         total_users=total_users,
                         active_work_orders=active_work_orders)

@app.route('/admin/assets')
@login_required
def admin_assets():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    status_filter = request.args.get('status', 'all')
    location_filter = request.args.get('location', 'all')
    type_filter = request.args.get('type', 'all')
    search_query = request.args.get('search', '')
    query = filter_by_company(Equipment.query)
    if status_filter != 'all':
        query = query.filter(Equipment.status == status_filter)
    if location_filter != 'all':
        query = query.filter(Equipment.location == location_filter)
    if type_filter != 'all':
        query = query.filter(Equipment.type == type_filter)
    if search_query:
        query = query.filter(
            db.or_(
                Equipment.name.contains(search_query),
                Equipment.model.contains(search_query),
                Equipment.serial_number.contains(search_query),
                Equipment.location.contains(search_query)
            )
        )
    equipment_list = query.order_by(Equipment.name).all()
    locations = query.with_entities(Equipment.location).distinct().all()
    equipment_types = query.with_entities(Equipment.type).distinct().all()
    return render_template('admin/assets.html',
                         equipment_list=equipment_list,
                         locations=[loc[0] for loc in locations if loc[0]],
                         equipment_types=[type[0] for type in equipment_types if type[0]],
                         filters={
                             'status': status_filter,
                             'location': location_filter,
                             'type': type_filter,
                             'search': search_query
                         })

@app.route('/admin/work-orders')
@login_required
def admin_work_orders():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    equipment_filter = request.args.get('equipment_id', 'all')
    technician_filter = request.args.get('technician_id', 'all')
    type_filter = request.args.get('type', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search_query = request.args.get('search', '')
    query = filter_by_company(WorkOrder.query)
    if status_filter != 'all':
        query = query.filter(WorkOrder.status == status_filter)
    if priority_filter != 'all':
        query = query.filter(WorkOrder.priority == priority_filter)
    if equipment_filter != 'all':
        query = query.filter(WorkOrder.equipment_id == equipment_filter)
    if technician_filter != 'all':
        query = query.filter(WorkOrder.assigned_technician_id == technician_filter)
    if type_filter != 'all':
        query = query.filter(WorkOrder.type == type_filter)
    if date_from:
        query = query.filter(WorkOrder.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(WorkOrder.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    if search_query:
        query = query.filter(
            db.or_(
                WorkOrder.title.contains(search_query),
                WorkOrder.description.contains(search_query),
                WorkOrder.work_order_number.contains(search_query)
            )
        )
    work_orders = query.order_by(WorkOrder.created_at.desc()).all()
    equipment_list = filter_by_company(Equipment.query).all()
    technicians = filter_by_company(User.query.filter_by(role='technician')).all()
    from datetime import datetime
    now = datetime.now()
    return render_template('admin/work_orders.html',
                         work_orders=work_orders,
                         equipment_list=equipment_list,
                         technicians=technicians,
                         filters={
                             'status': status_filter,
                             'priority': priority_filter,
                             'equipment_id': equipment_filter,
                             'technician_id': technician_filter,
                             'type': type_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search_query
                         },
                         now=now)

@app.route('/admin/technicians')
@login_required
def admin_technicians():
    """Admin technician management"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    team_filter = request.args.get('team_id', 'all')
    search_query = request.args.get('search', '')
    
    # Build query
    query = User.query.filter_by(role='technician')
    
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    if team_filter != 'all':
        query = query.join(User.teams).filter(Team.id == team_filter)
    if search_query:
        query = query.filter(
            db.or_(
                User.first_name.contains(search_query),
                User.last_name.contains(search_query),
                User.email.contains(search_query),
                User.username.contains(search_query)
            )
        )
    
    technicians = query.all()
    
    # Get technician performance stats
    technician_stats = []
    for tech in technicians:
        work_orders = WorkOrder.query.filter_by(assigned_technician_id=tech.id).all()
        total_tasks = len(work_orders)
        completed_tasks = len([wo for wo in work_orders if wo.status == 'completed'])
        on_time_tasks = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
        
        technician_stats.append({
            'technician': tech,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'on_time_tasks': on_time_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'on_time_rate': (on_time_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
        })
    
    # Get filter options
    teams = Team.query.all()
    
    return render_template('admin/technicians.html',
                         technician_stats=technician_stats,
                         teams=teams,
                         filters={
                             'status': status_filter,
                             'team_id': team_filter,
                             'search': search_query
                         })

@app.route('/admin/quick-actions')
@login_required
def admin_quick_actions():
    """Quick actions for admins"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('admin/quick_actions.html')

@app.route('/admin/bulk-assign', methods=['POST'])
@login_required
def admin_bulk_assign():
    """Bulk assign work orders to technicians"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_work_orders'))
    
    work_order_ids = request.form.getlist('work_order_ids')
    technician_id = request.form.get('technician_id')
    
    if not work_order_ids or not technician_id:
        flash('Please select work orders and a technician.', 'error')
        return redirect(url_for('admin_work_orders'))
    
    technician = User.query.get(technician_id)
    if not technician or technician.role != 'technician':
        flash('Invalid technician selected.', 'error')
        return redirect(url_for('admin_work_orders'))
    
    # Update work orders
    updated_count = 0
    for work_order_id in work_order_ids:
        work_order = WorkOrder.query.get(work_order_id)
        if work_order:
            work_order.assigned_technician_id = technician_id
            updated_count += 1
    
    db.session.commit()
    flash(f'Successfully assigned {updated_count} work orders to {technician.first_name} {technician.last_name}.', 'success')
    
    return redirect(url_for('admin_work_orders'))

@app.route('/admin/bulk-status', methods=['POST'])
@login_required
def admin_bulk_status():
    """Bulk update work order status"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_work_orders'))
    
    work_order_ids = request.form.getlist('work_order_ids')
    new_status = request.form.get('new_status')
    
    if not work_order_ids or not new_status:
        flash('Please select work orders and a new status.', 'error')
        return redirect(url_for('admin_work_orders'))
    
    # Update work orders
    updated_count = 0
    for work_order_id in work_order_ids:
        work_order = WorkOrder.query.get(work_order_id)
        if work_order:
            work_order.status = new_status
            if new_status == 'in_progress' and not work_order.actual_start_time:
                work_order.actual_start_time = datetime.utcnow()
            elif new_status == 'completed' and not work_order.actual_end_time:
                work_order.actual_end_time = datetime.utcnow()
            updated_count += 1
    
    db.session.commit()
    flash(f'Successfully updated status for {updated_count} work orders to {new_status.replace("_", " ").title()}.', 'success')
    
    return redirect(url_for('admin_work_orders'))

@app.route('/admin/equipment-status', methods=['POST'])
@login_required
def admin_equipment_status():
    """Update equipment status"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_assets'))
    
    equipment_id = request.form.get('equipment_id')
    new_status = request.form.get('new_status')
    
    if not equipment_id or not new_status:
        flash('Please select equipment and a new status.', 'error')
        return redirect(url_for('admin_assets'))
    
    equipment = Equipment.query.get(equipment_id)
    if not equipment:
        flash('Equipment not found.', 'error')
        return redirect(url_for('admin_assets'))
    
    equipment.status = new_status
    db.session.commit()
    flash(f'Equipment {equipment.name} status updated to {new_status.title()}.', 'success')
    
    return redirect(url_for('admin_assets'))

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Admin analytics and insights"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get time period filter
    period = request.args.get('period', '30')  # days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(period))
    
    # Get work orders in period
    work_orders = filter_by_company(WorkOrder.query).filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at <= end_date
    ).all()
    
    # Calculate metrics
    total_tasks = len(work_orders)
    completed_tasks = len([wo for wo in work_orders if wo.status == 'completed'])
    on_time_tasks = len([wo for wo in work_orders if wo.status == 'completed' and wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date])
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    on_time_rate = (on_time_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
    
    # Equipment performance
    equipment_performance = {}
    for wo in work_orders:
        if wo.equipment:
            if wo.equipment.name not in equipment_performance:
                equipment_performance[wo.equipment.name] = {'total': 0, 'completed': 0, 'on_time': 0}
            equipment_performance[wo.equipment.name]['total'] += 1
            if wo.status == 'completed':
                equipment_performance[wo.equipment.name]['completed'] += 1
                if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                    equipment_performance[wo.equipment.name]['on_time'] += 1
    
    # Technician performance
    technician_performance = {}
    for wo in work_orders:
        if wo.assigned_technician:
            tech_name = f"{wo.assigned_technician.first_name} {wo.assigned_technician.last_name}"
            if tech_name not in technician_performance:
                technician_performance[tech_name] = {'total': 0, 'completed': 0, 'on_time': 0}
            technician_performance[tech_name]['total'] += 1
            if wo.status == 'completed':
                technician_performance[tech_name]['completed'] += 1
                if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                    technician_performance[tech_name]['on_time'] += 1
    
    # Priority breakdown
    priority_breakdown = {}
    for wo in work_orders:
        if wo.priority not in priority_breakdown:
            priority_breakdown[wo.priority] = {'total': 0, 'completed': 0, 'on_time': 0}
        priority_breakdown[wo.priority]['total'] += 1
        if wo.status == 'completed':
            priority_breakdown[wo.priority]['completed'] += 1
            if wo.actual_end_time and wo.due_date and wo.actual_end_time <= wo.due_date:
                priority_breakdown[wo.priority]['on_time'] += 1
    
    return render_template('admin/analytics.html',
                         period=period,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         on_time_tasks=on_time_tasks,
                         completion_rate=completion_rate,
                         on_time_rate=on_time_rate,
                         equipment_performance=equipment_performance,
                         technician_performance=technician_performance,
                         priority_breakdown=priority_breakdown)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    department_filter = request.args.get('department', '')
    search_query = request.args.get('search', '')
    query = filter_by_company(User.query)
    if role_filter:
        query = query.filter(User.role == role_filter)
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    if department_filter:
        query = query.filter(User.department == department_filter)
    if search_query:
        query = query.filter(
            db.or_(
                User.first_name.contains(search_query),
                User.last_name.contains(search_query),
                User.email.contains(search_query),
                User.username.contains(search_query)
            )
        )
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, filters={
        'role': role_filter,
        'status': status_filter,
        'department': department_filter,
        'search': search_query
    })

@app.route('/admin/users/create', methods=['POST'])
@login_required
def admin_create_user():
    """Create new user from admin panel"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_users'))
    
    data = request.form
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    if User.query.filter_by(email=data['email']).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data['role'],
        department=data.get('department'),
        phone=data.get('phone'),
        is_active=data.get('is_active') == 'on'
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'User {user.first_name} {user.last_name} created successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>')
@login_required
def admin_get_user(user_id):
    """Get user data for editing"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    enforce_company_access(user)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'department': user.department,
        'phone': user.phone,
        'is_active': user.is_active
    })

@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@login_required
def admin_update_user(user_id):
    """Update user from admin panel"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    enforce_company_access(user)
    data = request.form
    
    # Update user fields
    user.first_name = data['first_name']
    user.last_name = data['last_name']
    user.email = data['email']
    user.role = data['role']
    user.department = data.get('department')
    user.phone = data.get('phone')
    user.is_active = data.get('is_active') == 'on'
    
    db.session.commit()
    
    flash(f'User {user.first_name} {user.last_name} updated successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def admin_toggle_user_status(user_id):
    """Toggle user active status"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    enforce_company_access(user)
    
    # Prevent deactivating own account
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'User {"activated" if user.is_active else "deactivated"} successfully'})

@app.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    """Reset user password"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    enforce_company_access(user)
    
    # Generate temporary password
    import secrets
    import string
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    user.set_password(temp_password)
    user.password_reset_required = True
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Password reset successfully. Temporary password: {temp_password}'})

@app.route('/admin/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def admin_change_user_role(user_id):
    """Change user role"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    if user.company_id != current_user.company_id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    # Prevent admin from changing their own role
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot change your own role'})
    
    data = request.get_json()
    new_role = data.get('role')
    
    if new_role not in ['admin', 'manager', 'technician', 'viewer']:
        return jsonify({'success': False, 'message': 'Invalid role'})
    
    # Prevent removing the last admin
    if user.role == 'admin' and new_role != 'admin':
        admin_count = User.query.filter_by(company_id=current_user.company_id, role='admin').count()
        if admin_count <= 1:
            return jsonify({'success': False, 'message': 'Cannot remove the last administrator'})
    
    user.role = new_role
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'User role updated to {new_role}'})

@app.route('/admin/roles')
@login_required
def admin_roles():
    """Admin role management"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get role statistics
    role_stats = {}
    roles = ['administrator', 'manager', 'technician', 'viewer']
    
    for role in roles:
        role_stats[role] = User.query.filter_by(role=role).count()
    
    return render_template('admin/roles.html', role_stats=role_stats)

@app.route('/admin/teams')
@login_required
def admin_teams():
    """Admin team management"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    teams = Team.query.all()
    technicians = User.query.filter_by(role='technician').all()
    
    return render_template('admin/teams.html', teams=teams, technicians=technicians)

@app.route('/admin/equipment')
@login_required
def admin_equipment():
    """Admin equipment management"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    location_filter = request.args.get('location', 'all')
    type_filter = request.args.get('type', 'all')
    search_query = request.args.get('search', '')
    
    # Build query
    query = Equipment.query
    
    if status_filter != 'all':
        query = query.filter(Equipment.status == status_filter)
    if location_filter != 'all':
        query = query.filter(Equipment.location == location_filter)
    if type_filter != 'all':
        query = query.filter(Equipment.type == type_filter)
    if search_query:
        query = query.filter(
            db.or_(
                Equipment.name.contains(search_query),
                Equipment.model.contains(search_query),
                Equipment.serial_number.contains(search_query),
                Equipment.location.contains(search_query)
            )
        )
    
    equipment_list = query.order_by(Equipment.name).all()
    
    # Get filter options
    locations = db.session.query(Equipment.location).distinct().all()
    equipment_types = db.session.query(Equipment.type).distinct().all()
    
    return render_template('admin/assets.html',
                         equipment_list=equipment_list,
                         locations=[loc[0] for loc in locations if loc[0]],
                         equipment_types=[type[0] for type in equipment_types if type[0]],
                         filters={
                             'status': status_filter,
                             'location': location_filter,
                             'type': type_filter,
                             'search': search_query
                         })

@app.route('/admin/settings')
@login_required
def admin_settings():
    """Admin system settings"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('admin/settings.html')

@app.route('/admin/save-settings', methods=['POST'])
@login_required
def admin_save_settings():
    """Save general system settings"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_settings'))
    
    # In a real implementation, you would save these to a settings table or config file
    flash('General settings saved successfully.', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/save-security-settings', methods=['POST'])
@login_required
def admin_save_security_settings():
    """Save security settings"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_settings'))
    
    # In a real implementation, you would save these to a settings table or config file
    flash('Security settings saved successfully.', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/save-notification-settings', methods=['POST'])
@login_required
def admin_save_notification_settings():
    """Save notification settings"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_settings'))
    
    # In a real implementation, you would save these to a settings table or config file
    flash('Notification settings saved successfully.', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/bulk-equipment-status', methods=['POST'])
@login_required
def admin_bulk_equipment_status():
    """Bulk update equipment status"""
    # Check if user has admin privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    equipment_ids = request.form.getlist('equipment_ids')
    new_status = request.form.get('new_status')
    
    if not equipment_ids or not new_status:
        return jsonify({'success': False, 'message': 'Please select equipment and a new status'}), 400
    
    # Update equipment status
    updated_count = 0
    for equipment_id in equipment_ids:
        equipment = Equipment.query.get(equipment_id)
        if equipment:
            equipment.status = new_status
            updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Successfully updated status for {updated_count} equipment items to {new_status.title()}'
    })

# Quick Assets Routes
@app.route('/quick-assets')
@login_required
def quick_assets():
    """Quick Asset Registry - Main view"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    department_filter = request.args.get('department', 'all')
    location_filter = request.args.get('location', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    tag_filter = request.args.get('tag', '')
    
    # Build query
    query = Equipment.query
    
    if category_filter != 'all':
        query = query.filter(Equipment.category == category_filter)
    if department_filter != 'all':
        query = query.filter(Equipment.department == department_filter)
    if location_filter != 'all':
        query = query.filter(Equipment.location == location_filter)
    if status_filter != 'all':
        query = query.filter(Equipment.status == status_filter)
    if search_query:
        query = query.filter(
            db.or_(
                Equipment.name.contains(search_query),
                Equipment.equipment_id.contains(search_query),
                Equipment.serial_number.contains(search_query),
                Equipment.manufacturer.contains(search_query),
                Equipment.model.contains(search_query)
            )
        )
    if tag_filter:
        query = query.filter(Equipment.tags.contains(tag_filter))
    
    equipment_list = query.order_by(Equipment.name).all()
    
    # Get filter options
    categories = db.session.query(Equipment.category).distinct().all()
    departments = db.session.query(Equipment.department).distinct().all()
    locations = db.session.query(Equipment.location).distinct().all()
    statuses = ['operational', 'maintenance', 'offline', 'out_of_service']
    
    # Extract tags from all equipment
    all_tags = set()
    for equipment in Equipment.query.all():
        if equipment.tags:
            tags = [tag.strip() for tag in equipment.tags.split(',') if tag.strip()]
            all_tags.update(tags)
    
    # Build filtered_args for tag filter links
    filtered_args = {k: v for k, v in request.args.items() if k != 'tag'}

    return render_template('quick_assets/index.html',
                         equipment_list=equipment_list,
                         categories=[cat[0] for cat in categories if cat[0]],
                         departments=[dept[0] for dept in departments if dept[0]],
                         locations=[loc[0] for loc in locations if loc[0]],
                         statuses=statuses,
                         all_tags=sorted(all_tags),
                         filters={
                             'category': category_filter,
                             'department': department_filter,
                             'location': location_filter,
                             'status': status_filter,
                             'search': search_query,
                             'tag': tag_filter
                         },
                         filtered_args=filtered_args)

@app.route('/quick-assets/add', methods=['GET', 'POST'])
@login_required
def quick_assets_add():
    """Quick Add Asset"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.form
        
        # Generate unique equipment ID if not provided
        equipment_id = data.get('equipment_id')
        if not equipment_id:
            equipment_id = f"EQ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Create equipment
        equipment = Equipment(
            name=data['name'],
            equipment_id=equipment_id,
            category=data['category'],
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            location=data.get('location'),
            department=data.get('department'),
            tags=data.get('tags'),
            description=data.get('description'),
            status=data.get('status', 'operational'),
            criticality=data.get('criticality', 'medium')
        )
        
        db.session.add(equipment)
        db.session.commit()
        
        flash('Asset added successfully!', 'success')
        return redirect(url_for('quick_assets'))
    
    # Get existing data for autocomplete
    categories = db.session.query(Equipment.category).distinct().all()
    departments = db.session.query(Equipment.department).distinct().all()
    locations = db.session.query(Equipment.location).distinct().all()
    
    return render_template('quick_assets/add.html',
                         categories=[cat[0] for cat in categories if cat[0]],
                         departments=[dept[0] for dept in departments if dept[0]],
                         locations=[loc[0] for loc in locations if loc[0]])

@app.route('/quick-assets/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def quick_assets_edit(id):
    """Quick Edit Asset"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    equipment = Equipment.query.get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        
        equipment.name = data['name']
        equipment.category = data['category']
        equipment.manufacturer = data.get('manufacturer')
        equipment.model = data.get('model')
        equipment.serial_number = data.get('serial_number')
        equipment.location = data.get('location')
        equipment.department = data.get('department')
        equipment.tags = data.get('tags')
        equipment.description = data.get('description')
        equipment.status = data.get('status', 'operational')
        equipment.criticality = data.get('criticality', 'medium')
        
        db.session.commit()
        
        flash('Asset updated successfully!', 'success')
        return redirect(url_for('quick_assets'))
    
    # Get existing data for autocomplete
    categories = db.session.query(Equipment.category).distinct().all()
    departments = db.session.query(Equipment.department).distinct().all()
    locations = db.session.query(Equipment.location).distinct().all()
    
    return render_template('quick_assets/edit.html',
                         equipment=equipment,
                         categories=[cat[0] for cat in categories if cat[0]],
                         departments=[dept[0] for dept in departments if dept[0]],
                         locations=[loc[0] for loc in locations if loc[0]])

@app.route('/quick-assets/<int:id>/delete', methods=['POST'])
@login_required
def quick_assets_delete(id):
    """Delete Asset"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    equipment = Equipment.query.get_or_404(id)
    
    try:
        db.session.delete(equipment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asset deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error deleting asset'}), 500

@app.route('/quick-assets/bulk-add', methods=['POST'])
@login_required
def quick_assets_bulk_add():
    """Bulk Add Assets from CSV"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    if 'csv_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Please upload a CSV file'}), 400
    
    try:
        # Read CSV file
        csv_data = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_data))
        
        added_count = 0
        errors = []
        
        for row in csv_reader:
            try:
                # Generate unique equipment ID if not provided
                equipment_id = row.get('equipment_id')
                if not equipment_id:
                    equipment_id = f"EQ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                
                equipment = Equipment(
                    name=row['name'],
                    equipment_id=equipment_id,
                    category=row.get('category', 'Unknown'),
                    manufacturer=row.get('manufacturer'),
                    model=row.get('model'),
                    serial_number=row.get('serial_number'),
                    location=row.get('location'),
                    department=row.get('department'),
                    tags=row.get('tags'),
                    description=row.get('description'),
                    status=row.get('status', 'operational'),
                    criticality=row.get('criticality', 'medium')
                )
                
                db.session.add(equipment)
                added_count += 1
                
            except Exception as e:
                errors.append(f"Row {added_count + 1}: {str(e)}")
        
        db.session.commit()
        
        message = f"Successfully added {added_count} assets"
        if errors:
            message += f". Errors: {', '.join(errors[:5])}"
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error processing CSV: {str(e)}'}), 500

@app.route('/quick-assets/export-csv')
@login_required
def quick_assets_export_csv():
    """Export Assets to CSV"""
    # Check if user has admin/manager privileges
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    equipment_list = Equipment.query.order_by(Equipment.name).all()
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Name', 'Equipment ID', 'Category', 'Manufacturer', 'Model', 
        'Serial Number', 'Location', 'Department', 'Tags', 'Status', 
        'Criticality', 'Description', 'Created At'
    ])
    
    # Write data
    for equipment in equipment_list:
        writer.writerow([
            equipment.name,
            equipment.equipment_id,
            equipment.category,
            equipment.manufacturer or '',
            equipment.model or '',
            equipment.serial_number or '',
            equipment.location or '',
            equipment.department or '',
            equipment.tags or '',
            equipment.status,
            equipment.criticality,
            equipment.description or '',
            equipment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=assets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

# Quick Assets API Routes
@app.route('/api/quick-assets/categories')
@login_required
def api_quick_assets_categories():
    """Get all categories for autocomplete"""
    categories = db.session.query(Equipment.category).distinct().all()
    return jsonify([cat[0] for cat in categories if cat[0]])

@app.route('/api/quick-assets/departments')
@login_required
def api_quick_assets_departments():
    """Get all departments for autocomplete"""
    departments = db.session.query(Equipment.department).distinct().all()
    return jsonify([dept[0] for dept in departments if dept[0]])

@app.route('/api/quick-assets/locations')
@login_required
def api_quick_assets_locations():
    """Get all locations for autocomplete"""
    locations = db.session.query(Equipment.location).distinct().all()
    return jsonify([loc[0] for loc in locations if loc[0]])

@app.route('/api/quick-assets/tags')
@login_required
def api_quick_assets_tags():
    """Get all tags for autocomplete"""
    all_tags = set()
    for equipment in Equipment.query.all():
        if equipment.tags:
            tags = [tag.strip() for tag in equipment.tags.split(',') if tag.strip()]
            all_tags.update(tags)
    return jsonify(sorted(all_tags))

@app.route('/quick-maintenance-schedule', methods=['GET', 'POST'])
@login_required
def quick_maintenance_schedule():
    """Quick maintenance scheduling from dashboard"""
    if request.method == 'POST':
        data = request.form
        equipment_id = data.get('equipment_id')
        frequency = data.get('frequency')
        frequency_value = data.get('frequency_value', 1)
        description = data.get('description')
        next_due = data.get('next_due')
        
        if not all([equipment_id, frequency, description, next_due]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('quick_maintenance_schedule'))
        
        try:
            equipment = Equipment.query.get_or_404(equipment_id)
            schedule = MaintenanceSchedule(
                equipment_id=equipment.id,
                frequency=frequency,
                frequency_value=int(frequency_value),
                description=description,
                estimated_duration=data.get('estimated_duration'),
                next_due=datetime.strptime(next_due, '%Y-%m-%dT%H:%M'),
                is_active=True
            )
            db.session.add(schedule)
            db.session.commit()
            flash(f'Maintenance schedule created for {equipment.name}!', 'success')
            return redirect(url_for('equipment_detail', id=equipment.id))
        except Exception as e:
            flash(f'Error creating maintenance schedule: {str(e)}', 'error')
            return redirect(url_for('quick_maintenance_schedule'))
    
    # GET request - show form
    equipment_list = Equipment.query.filter_by(status='operational').order_by(Equipment.name).all()
    return render_template('quick_maintenance_schedule.html', equipment_list=equipment_list)

@app.route('/qr-report/<equipment_id>', methods=['GET', 'POST'])
def qr_failure_report(equipment_id):
    """QR code failure reporting page"""
    equipment = Equipment.query.get_or_404(equipment_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            description = request.form.get('description', '').strip()
            failure_type = request.form.get('failure_type', 'mechanical')
            urgency = request.form.get('urgency', 'high')
            reporter_name = request.form.get('reporter_name', '').strip()
            reporter_phone = request.form.get('reporter_phone', '').strip()
            
            if not description:
                flash('Please provide a description of the failure.', 'error')
                return render_template('qr_failure_report.html', equipment=equipment)
            
            # Handle file uploads
            images = []
            videos = []
            audio_files = []
            
            # Handle image uploads
            if 'images' in request.files:
                for file in request.files.getlist('images'):
                    if file and file.filename:
                        file_path = save_uploaded_file(file, 'static/uploads/work_orders', 'image')
                        if file_path:
                            images.append(file_path)
            
            # Handle video uploads
            if 'videos' in request.files:
                for file in request.files.getlist('videos'):
                    if file and file.filename:
                        file_path = save_uploaded_file(file, 'static/uploads/work_orders', 'video')
                        if file_path:
                            videos.append(file_path)
            
            # Handle audio uploads
            if 'audio_files' in request.files:
                for file in request.files.getlist('audio_files'):
                    if file and file.filename:
                        file_path = save_uploaded_file(file, 'static/uploads/work_orders', 'audio')
                        if file_path:
                            audio_files.append(file_path)
            
            # Create work order
            work_order = WorkOrder(
                work_order_number=generate_work_order_number(),
                title=f"QR Report: {failure_type.title()} Failure - {equipment.name}",
                description=f"Failure reported via QR code:\n\n{description}\n\nReporter: {reporter_name or 'Anonymous'}\nPhone: {reporter_phone or 'Not provided'}",
                priority='urgent' if urgency == 'high' else 'high',
                status='open',
                type='corrective',
                equipment_id=equipment.id,
                created_by_id=1,  # Default admin user, you might want to handle this differently
                scheduled_date=datetime.now(),
                due_date=datetime.now() + timedelta(hours=4) if urgency == 'high' else datetime.now() + timedelta(days=1),
                images=','.join(images) if images else None,
                videos=','.join(videos) if videos else None,
                voice_notes=','.join(audio_files) if audio_files else None
            )
            
            db.session.add(work_order)
            
            # Update equipment status to maintenance if it was operational
            if equipment.status == 'operational':
                equipment.status = 'maintenance'
                equipment.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Failure report submitted successfully! Work Order #{work_order.work_order_number} has been created.', 'success')
            return render_template('qr_failure_report_success.html', work_order=work_order, equipment=equipment)
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting report: {str(e)}', 'error')
            return render_template('qr_failure_report.html', equipment=equipment)
    
    return render_template('qr_failure_report.html', equipment=equipment)

@app.route('/api/qr-equipment/<equipment_id>')
def api_qr_equipment(equipment_id):
    """API endpoint for QR code equipment data"""
    equipment = Equipment.query.get_or_404(equipment_id)
    return jsonify(equipment.to_dict())

@app.route('/qr-image/<equipment_id>')
def qr_image(equipment_id):
    qr_url = request.host_url.rstrip('/') + f'/qr-report/{equipment_id}'
    img = qrcode.make(qr_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/generate-qr/<equipment_id>')
@login_required
def generate_qr_code(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    qr_url = request.host_url.rstrip('/') + f'/qr-report/{equipment.id}'
    # Generate QR code as data URI
    img = qrcode.make(qr_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    img_data = f"data:image/png;base64,{img_b64}"
    return render_template('generate_qr.html', equipment=equipment, qr_url=qr_url, qr_img=img_data)

@app.route('/api/generate-qr/<equipment_id>')
@login_required
def api_generate_qr(equipment_id):
    """API endpoint to get QR code data"""
    equipment = Equipment.query.get_or_404(equipment_id)
    qr_url = request.host_url.rstrip('/') + f'/qr-report/{equipment.id}'
    
    return jsonify({
        'equipment_id': equipment.id,
        'equipment_name': equipment.name,
        'qr_url': qr_url,
        'qr_data': f"Equipment: {equipment.name}\nID: {equipment.equipment_id}\nLocation: {equipment.location or 'Not specified'}\nReport Issue: {qr_url}"
    })

@app.route('/test-qr')
def test_qr():
    """Test QR code generation"""
    test_url = request.host_url.rstrip('/') + '/qr-report/1'
    return render_template('test_qr.html', qr_url=test_url)

# WhatsApp Integration Routes
@app.route('/whatsapp/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """WhatsApp webhook endpoint for receiving messages"""
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == os.getenv('WHATSAPP_VERIFY_TOKEN'):
            return challenge
        else:
            return 'Forbidden', 403
    
    elif request.method == 'POST':
        # Process incoming messages
        data = request.get_json()
        try:
            from whatsapp_webhook import WhatsAppWebhookHandler
            result = WhatsAppWebhookHandler.process_incoming_message(data)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/whatsapp/verify', methods=['GET', 'POST'])
@login_required
def whatsapp_verify():
    """WhatsApp number verification page"""
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        verification_code = request.form.get('verification_code')
        
        if not phone_number:
            flash('Please enter your WhatsApp number.', 'error')
            return render_template('whatsapp_verify.html')
        
        # Format phone number (remove spaces, add country code if needed)
        phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not phone_number.startswith('+'):
            phone_number = '+1' + phone_number  # Default to US
        
        # Check if verification code is provided
        if verification_code:
            # Verify the code
            whatsapp_user = WhatsAppUser.query.filter_by(
                whatsapp_number=phone_number,
                verification_code=verification_code
            ).first()
            
            if whatsapp_user and whatsapp_user.verification_expires > datetime.now():
                whatsapp_user.is_verified = True
                whatsapp_user.verification_code = None
                whatsapp_user.verification_expires = None
                db.session.commit()
                flash('WhatsApp number verified successfully!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid or expired verification code.', 'error')
        else:
            # Send verification code
            import random
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Check if user already has a WhatsApp profile
            existing_user = WhatsAppUser.query.filter_by(user_id=current_user.id).first()
            if existing_user:
                existing_user.whatsapp_number = phone_number
                existing_user.verification_code = code
                existing_user.verification_expires = datetime.now() + timedelta(minutes=10)
                existing_user.is_verified = False
            else:
                whatsapp_user = WhatsAppUser(
                    user_id=current_user.id,
                    whatsapp_number=phone_number,
                    verification_code=code,
                    verification_expires=datetime.now() + timedelta(minutes=10),
                    is_verified=False
                )
                db.session.add(whatsapp_user)
            
            db.session.commit()
            
            # Send verification code via WhatsApp
            try:
                from whatsapp_integration import whatsapp
                message = f"Your CMMS verification code is: {code}\n\nThis code will expire in 10 minutes."
                result = whatsapp.send_message(phone_number, message)
                
                if result['success']:
                    flash('Verification code sent to your WhatsApp number.', 'success')
                else:
                    flash(f'Error sending verification code: {result.get("error")}', 'error')
            except Exception as e:
                flash(f'Error sending verification code: {str(e)}', 'error')
        
        return render_template('whatsapp_verify.html', phone_number=phone_number)
    
    return render_template('whatsapp_verify.html')

@app.route('/whatsapp/settings', methods=['GET', 'POST'])
@login_required
def whatsapp_settings():
    """WhatsApp notification settings"""
    whatsapp_user = WhatsAppUser.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        if not whatsapp_user:
            flash('Please verify your WhatsApp number first.', 'error')
            return redirect(url_for('whatsapp_verify'))
        
        # Update notification preferences
        preferences = {
            'work_order_assignments': request.form.get('work_order_assignments') == 'on',
            'priority_escalations': request.form.get('priority_escalations') == 'on',
            'parts_delivery': request.form.get('parts_delivery') == 'on',
            'maintenance_reminders': request.form.get('maintenance_reminders') == 'on',
            'emergency_broadcasts': request.form.get('emergency_broadcasts') == 'on',
            'daily_checklists': request.form.get('daily_checklists') == 'on'
        }
        
        whatsapp_user.notification_preferences = json.dumps(preferences)
        whatsapp_user.preferred_language = request.form.get('preferred_language', 'en')
        db.session.commit()
        
        flash('WhatsApp settings updated successfully!', 'success')
        return redirect(url_for('whatsapp_settings'))
    
    preferences = {}
    if whatsapp_user and whatsapp_user.notification_preferences:
        preferences = json.loads(whatsapp_user.notification_preferences)
    
    return render_template('whatsapp_settings.html', 
                         whatsapp_user=whatsapp_user, 
                         preferences=preferences)

@app.route('/whatsapp/templates')
@login_required
def whatsapp_templates():
    """Manage WhatsApp message templates (company-scoped)"""
    templates = filter_by_company(WhatsAppTemplate.query).all()
    return render_template('whatsapp_templates.html', templates=templates)

@app.route('/whatsapp/templates/new', methods=['GET', 'POST'])
@login_required
def whatsapp_template_new():
    """Create new WhatsApp template (company-scoped)"""
    if request.method == 'POST':
        data = request.form
        template = WhatsAppTemplate(
            name=data['name'],
            category=data['category'],
            template_id=data['template_id'],
            language=data['language'],
            content=data['content'],
            variables=data.get('variables'),
            is_active=data.get('is_active') == 'on',
            company_id=current_user.company_id
        )
        db.session.add(template)
        db.session.commit()
        flash('WhatsApp template created successfully!', 'success')
        return redirect(url_for('whatsapp_templates'))
    
    return render_template('whatsapp_template_new.html')

@app.route('/whatsapp/emergency', methods=['GET', 'POST'])
@login_required
def whatsapp_emergency():
    """Send emergency broadcast (company-scoped)"""
    if request.method == 'POST':
        data = request.form
        emergency = EmergencyBroadcast(
            title=data['title'],
            message=data['message'],
            priority=data['priority'],
            equipment_id=data.get('equipment_id'),
            location_id=data.get('location_id'),
            sent_by_id=current_user.id,
            recipients=data.get('recipients', 'all'),
            expires_at=datetime.now() + timedelta(hours=24) if data.get('expires') else None,
            company_id=current_user.company_id
        )
        db.session.add(emergency)
        db.session.commit()
        
        # Send emergency broadcast
        try:
            from whatsapp_notifications import WhatsAppNotifications
            success = WhatsAppNotifications.send_emergency_broadcast(emergency)
            
            if success:
                flash('Emergency broadcast sent successfully!', 'success')
            else:
                flash('Error sending emergency broadcast.', 'error')
        except Exception as e:
            flash(f'Error sending emergency broadcast: {str(e)}', 'error')
        
        return redirect(url_for('whatsapp_emergency'))
    
    equipment_list = filter_by_company(Equipment.query).all()
    locations = filter_by_company(Location.query).all()
    return render_template('whatsapp_emergency.html', 
                         equipment_list=equipment_list, 
                         locations=locations)

@app.route('/whatsapp/notifications')
@login_required
def whatsapp_notifications():
    """View WhatsApp notification logs (company-scoped)"""
    page = request.args.get('page', 1, type=int)
    notifications = filter_by_company(NotificationLog.query).filter_by(
        notification_type='whatsapp'
    ).order_by(NotificationLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('whatsapp_notifications.html', notifications=notifications)

@app.route('/api/whatsapp/send-test', methods=['POST'])
@login_required
def api_whatsapp_send_test():
    """Send test WhatsApp message"""
    whatsapp_user = WhatsAppUser.query.filter_by(user_id=current_user.id).first()
    if not whatsapp_user or not whatsapp_user.is_verified:
        return jsonify({'success': False, 'error': 'WhatsApp not verified'})
    
    try:
        from whatsapp_integration import whatsapp
        message = "🧪 Test message from CMMS\n\nThis is a test message to verify your WhatsApp integration is working correctly."
        result = whatsapp.send_message(whatsapp_user.whatsapp_number, message)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/whatsapp/users')
@login_required
def api_whatsapp_users():
    """Get all WhatsApp users for admin (company-scoped)"""
    users = filter_by_company(WhatsAppUser.query).all()
    return jsonify([user.to_dict() for user in users])

@app.route('/whatsapp/disconnect', methods=['POST'])
@login_required
def whatsapp_disconnect():
    """Disconnect WhatsApp integration for current user"""
    whatsapp_user = WhatsAppUser.query.filter_by(user_id=current_user.id).first()
    
    if whatsapp_user:
        # Delete all associated messages
        WhatsAppMessage.query.filter_by(whatsapp_user_id=whatsapp_user.id).delete()
        
        # Delete the WhatsApp user profile
        db.session.delete(whatsapp_user)
        db.session.commit()
        
        flash('WhatsApp integration disconnected successfully.', 'success')
    else:
        flash('No WhatsApp integration found to disconnect.', 'info')
    
    return redirect(url_for('profile'))

@app.route('/whatsapp/templates/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def whatsapp_template_edit(id):
    """Edit WhatsApp template"""
    template = WhatsAppTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        template.name = data['name']
        template.category = data['category']
        template.template_id = data['template_id']
        template.language = data['language']
        template.content = data['content']
        template.variables = data.get('variables')
        template.is_active = data.get('is_active') == 'on'
        db.session.commit()
        flash('WhatsApp template updated successfully!', 'success')
        return redirect(url_for('whatsapp_templates'))
    
    return render_template('whatsapp_template_edit.html', template=template)

@app.route('/whatsapp/templates/<int:id>/delete', methods=['POST'])
@login_required
def whatsapp_template_delete(id):
    """Delete WhatsApp template"""
    template = WhatsAppTemplate.query.get_or_404(id)
    try:
        db.session.delete(template)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/whatsapp/retry-notification/<int:notification_id>', methods=['POST'])
@login_required
def api_retry_notification(notification_id):
    """Retry failed WhatsApp notification"""
    notification = NotificationLog.query.get_or_404(notification_id)
    
    if notification.status != 'failed':
        return jsonify({'success': False, 'error': 'Notification is not in failed status'})
    
    try:
        # Retry sending the notification
        from whatsapp_notifications import WhatsAppNotifications
        success = WhatsAppNotifications.send_notification(notification)
        
        if success:
            notification.status = 'sent'
            notification.sent_at = datetime.now()
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to send notification'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print(os.getenv('DATABASE_URL'))
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)