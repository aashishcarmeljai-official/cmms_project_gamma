#!/usr/bin/env python3
"""
Database initialization script for CMMS
Run this script to create all database tables and optionally add sample data.
"""

from app import app, db
from models import User, Equipment, WorkOrder, MaintenanceSchedule, Inventory, WorkOrderPart
from datetime import datetime, timedelta

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")

def create_sample_data():
    """Create sample data for testing"""
    with app.app_context():
        print("Creating sample data...")
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@company.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            department='IT',
            phone='555-0100'
        )
        admin.set_password('admin123')
        
        # Create technician user
        technician = User(
            username='tech1',
            email='tech1@company.com',
            first_name='John',
            last_name='Technician',
            role='technician',
            department='Maintenance',
            phone='555-0101'
        )
        technician.set_password('tech123')
        
        # Add users to database
        db.session.add(admin)
        db.session.add(technician)
        db.session.commit()
        print("✅ Users created")
        
        # Create sample equipment
        equipment1 = Equipment(
            name='HVAC Unit #1',
            equipment_id='HVAC-001',
            category='hvac',
            manufacturer='Carrier',
            model='48TC',
            serial_number='SN123456789',
            location='Building A - Floor 1',
            department='Facilities',
            status='operational',
            criticality='high',
            description='Main HVAC unit for Building A',
            specifications='48,000 BTU cooling capacity'
        )
        
        equipment2 = Equipment(
            name='Production Line Conveyor',
            equipment_id='CONV-001',
            category='machinery',
            manufacturer='Hytrol',
            model='EZLogic',
            serial_number='SN987654321',
            location='Production Floor',
            department='Manufacturing',
            status='operational',
            criticality='critical',
            description='Main production line conveyor system',
            specifications='100 ft length, 500 lb capacity'
        )
        
        equipment3 = Equipment(
            name='Emergency Generator',
            equipment_id='GEN-001',
            category='electrical',
            manufacturer='Cummins',
            model='C1100D5',
            serial_number='SN456789123',
            location='Generator Room',
            department='Facilities',
            status='operational',
            criticality='critical',
            description='Emergency backup generator',
            specifications='1100 kW, Diesel powered'
        )
        
        db.session.add(equipment1)
        db.session.add(equipment2)
        db.session.add(equipment3)
        db.session.commit()
        print("✅ Equipment created")
        
        # Create sample work orders
        work_order1 = WorkOrder(
            work_order_number='WO-20241201-ABC12345',
            title='HVAC Filter Replacement',
            description='Replace air filters in HVAC Unit #1',
            priority='medium',
            type='preventive',
            equipment_id=equipment1.id,
            assigned_technician_id=technician.id,
            created_by_id=admin.id,
            estimated_duration=60,
            scheduled_date=datetime.now() + timedelta(days=1)
        )
        
        work_order2 = WorkOrder(
            work_order_number='WO-20241201-DEF67890',
            title='Conveyor Belt Inspection',
            description='Inspect conveyor belt for wear and tear',
            priority='high',
            type='preventive',
            equipment_id=equipment2.id,
            assigned_technician_id=technician.id,
            created_by_id=admin.id,
            estimated_duration=120,
            scheduled_date=datetime.now() + timedelta(days=2)
        )
        
        db.session.add(work_order1)
        db.session.add(work_order2)
        db.session.commit()
        print("✅ Work orders created")
        
        # Create sample inventory items
        inventory1 = Inventory(
            part_number='FILTER-001',
            name='HVAC Air Filter',
            description='High-efficiency air filter for HVAC units',
            category='Filters',
            manufacturer='3M',
            supplier='ABC Supplies',
            unit_cost=25.50,
            current_stock=50,
            minimum_stock=10,
            maximum_stock=100,
            unit_of_measure='pieces',
            location='Warehouse A - Shelf 1'
        )
        
        inventory2 = Inventory(
            part_number='BELT-001',
            name='Conveyor Belt',
            description='Heavy-duty conveyor belt for production line',
            category='Belts',
            manufacturer='Gates',
            supplier='XYZ Industrial',
            unit_cost=150.00,
            current_stock=5,
            minimum_stock=2,
            maximum_stock=10,
            unit_of_measure='pieces',
            location='Warehouse B - Shelf 3'
        )
        
        inventory3 = Inventory(
            part_number='OIL-001',
            name='Motor Oil',
            description='Synthetic motor oil for equipment lubrication',
            category='Lubricants',
            manufacturer='Mobil',
            supplier='OilCo',
            unit_cost=15.75,
            current_stock=20,
            minimum_stock=5,
            maximum_stock=50,
            unit_of_measure='quarts',
            location='Warehouse A - Shelf 2'
        )
        
        db.session.add(inventory1)
        db.session.add(inventory2)
        db.session.add(inventory3)
        db.session.commit()
        print("✅ Inventory items created")
        
        # Create sample maintenance schedules
        schedule1 = MaintenanceSchedule(
            equipment_id=equipment1.id,
            schedule_type='calendar',
            frequency='monthly',
            frequency_value=1,
            description='Monthly HVAC filter replacement',
            estimated_duration=60,
            is_active=True,
            next_due=datetime.now() + timedelta(days=30)
        )
        
        schedule2 = MaintenanceSchedule(
            equipment_id=equipment2.id,
            schedule_type='calendar',
            frequency='weekly',
            frequency_value=1,
            description='Weekly conveyor belt inspection',
            estimated_duration=30,
            is_active=True,
            next_due=datetime.now() + timedelta(days=7)
        )
        
        db.session.add(schedule1)
        db.session.add(schedule2)
        db.session.commit()
        print("✅ Maintenance schedules created")
        
        print("\n🎉 Sample data created successfully!")
        print("\nLogin credentials:")
        print("Admin: username='admin', password='admin123'")
        print("Technician: username='tech1', password='tech123'")

if __name__ == '__main__':
    print("CMMS Database Initialization")
    print("=" * 40)
    
    try:
        # Initialize database tables
        init_database()
        
        # Ask if user wants sample data
        response = input("\nDo you want to create sample data? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            create_sample_data()
        else:
            print("Skipping sample data creation.")
        
        print("\n✅ Database initialization completed!")
        print("You can now run 'python app.py' to start the CMMS application.")
        
    except Exception as e:
        print(f"❌ Error during database initialization: {e}")
        print("Please check your database connection and try again.") 