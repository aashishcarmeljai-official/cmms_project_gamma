from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, IntegerField, BooleanField, DateTimeField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from flask_dance.contrib.google import make_google_blueprint, google

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
from models import User, Equipment, WorkOrder, MaintenanceSchedule, Inventory, WorkOrderPart, Location, Team

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
@login_required
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
@login_required
def equipment_list():
    """List all equipment"""
    equipment = Equipment.query.all()
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
            specifications=data.get('specifications')
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
    work_orders = WorkOrder.query.filter_by(equipment_id=id).order_by(WorkOrder.created_at.desc()).all()
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
@login_required
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
@login_required
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
            created_by_id=current_user.id,  # Use current authenticated user
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
@login_required
def work_order_detail(id):
    """Work order detail page"""
    work_order = WorkOrder.query.get_or_404(id)
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

# Inventory routes
@app.route('/inventory')
@login_required
def inventory_list():
    """List all inventory items"""
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Search in part number, name, category, and location
        inventory = Inventory.query.filter(
            db.or_(
                Inventory.part_number.ilike(f'%{search_query}%'),
                Inventory.name.ilike(f'%{search_query}%'),
                Inventory.category.ilike(f'%{search_query}%'),
                Inventory.location.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        inventory = Inventory.query.all()
    
    return render_template('inventory/list.html', inventory=inventory, search_query=search_query)

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
    return render_template('inventory/detail.html', inventory=inventory)

@app.route('/inventory/<int:id>/delete', methods=['POST'])
@login_required
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

@app.route('/api/locations')
def api_locations():
    """API endpoint for locations"""
    locations = Location.query.all()
    return jsonify([loc.to_dict() for loc in locations])

@app.route('/api/calendar-events')
@login_required
def api_calendar_events():
    work_orders = WorkOrder.query.filter(WorkOrder.scheduled_date != None).all()
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
    submit = SubmitField('Sign Up')

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
    is_active = BooleanField('Is Active', default=True)
    submit = SubmitField('Save')

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
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'error')
            return render_template('signup.html', form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
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
    
    if search_query:
        locations = Location.query.filter(
            db.or_(
                Location.name.ilike(f'%{search_query}%'),
                Location.city.ilike(f'%{search_query}%'),
                Location.state.ilike(f'%{search_query}%'),
                Location.contact_person.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        locations = Location.query.all()
    
    return render_template('locations/list.html', locations=locations, search_query=search_query)

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
    equipment = Equipment.query.filter_by(location_id=id).all()
    users = User.query.filter_by(location_id=id).all()
    return render_template('locations/detail.html', location=location, equipment=equipment, users=users)

@app.route('/locations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def location_edit(id):
    """Edit location"""
    location = Location.query.get_or_404(id)
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
    
    try:
        # Check if location has associated equipment or users
        equipment_count = Equipment.query.filter_by(location_id=id).count()
        users_count = User.query.filter_by(location_id=id).count()
        
        if equipment_count > 0 or users_count > 0:
            flash(f'Cannot delete location "{location.name}". It has {equipment_count} equipment and {users_count} users assigned to it.', 'error')
            return redirect(url_for('location_detail', id=id))
        
        db.session.delete(location)
        db.session.commit()
        flash(f'Location "{location.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting location: {str(e)}', 'error')
    
    return redirect(url_for('locations_list'))

@app.route('/maps')
@login_required
def maps():
    """Interactive maps page showing all locations"""
    locations = Location.query.filter_by(is_active=True).all()
    locations_data = [loc.to_dict() for loc in locations]
    return render_template('maps.html', locations=locations_data)

@app.route('/equipment/<int:id>/maintenance-schedule/new', methods=['GET', 'POST'])
@login_required
def maintenance_schedule_new(id):
    equipment = Equipment.query.get_or_404(id)
    form = MaintenanceScheduleForm()
    if form.validate_on_submit():
        schedule = MaintenanceSchedule(
            equipment_id=equipment.id,
            frequency=form.frequency.data,
            frequency_value=form.frequency_value.data,
            description=form.description.data,
            estimated_duration=form.estimated_duration.data,
            next_due=form.next_due.data,
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
    if form.validate_on_submit():
        schedule.frequency = form.frequency.data
        schedule.frequency_value = form.frequency_value.data
        schedule.description = form.description.data
        schedule.estimated_duration = form.estimated_duration.data
        schedule.next_due = form.next_due.data
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
    users = User.query.order_by(User.first_name, User.last_name).all()
    teams = Team.query.order_by(Team.name).all()
    search_user = request.args.get('search_user', '').strip().lower()
    search_team = request.args.get('search_team', '').strip().lower()
    filtered_users = [u for u in users if search_user in (u.first_name + ' ' + u.last_name + ' ' + u.username).lower()] if search_user else users
    filtered_teams = [t for t in teams if search_team in t.name.lower()] if search_team else teams
    return render_template('teams.html', users=filtered_users, teams=filtered_teams, all_users=users, all_teams=teams, search_user=search_user, search_team=search_team)

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
    form = TeamForm(obj=team)
    form.members.choices = [(u.id, f"{u.first_name} {u.last_name} ({u.username})") for u in User.query.order_by(User.first_name, User.last_name).all()]
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

if __name__ == '__main__':
    print(os.getenv('DATABASE_URL'))
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)