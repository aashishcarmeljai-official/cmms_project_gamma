#!/usr/bin/env python3
"""
Database initialization script for CMMS
Run this script to create all database tables and optionally add sample data.
"""

from app import app, db
from models import (
    User, Equipment, WorkOrder, MaintenanceSchedule, Inventory, WorkOrderPart,
    Location, Team, SOP, SOPChecklistItem, WhatsAppUser, WhatsAppTemplate,
    EmergencyBroadcast, NotificationLog, Company
)
from datetime import datetime, timedelta
import json

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")

def create_sample_data():
    """Create comprehensive sample data for testing"""
    with app.app_context():
        print("Creating comprehensive sample data...")
        
        # --- Multi-Tenancy: Create a Company ---
        print("Creating company...")
        company = Company(name='Acme Corporation')
        db.session.add(company)
        db.session.commit()
        print(f"✅ Company created: {company.name} (ID: {company.id})")
        
        # Create locations
        print("Creating locations...")
        location1 = Location(
            name='Main Building',
            address='123 Industrial Ave',
            city='Springfield',
            state='IL',
            zip_code='62701',
            country='USA',
            latitude=39.7817,
            longitude=-89.6501,
            description='Main manufacturing facility',
            contact_person='John Smith',
            contact_phone='555-0100',
            contact_email='facilities@company.com',
            company_id=company.id
        )
        
        location2 = Location(
            name='Warehouse Complex',
            address='456 Storage Blvd',
            city='Springfield',
            state='IL',
            zip_code='62702',
            country='USA',
            latitude=39.7917,
            longitude=-89.6601,
            description='Storage and distribution center',
            contact_person='Jane Doe',
            contact_phone='555-0101',
            contact_email='warehouse@company.com',
            company_id=company.id
        )
        
        location3 = Location(
            name='Office Building',
            address='789 Corporate Dr',
            city='Springfield',
            state='IL',
            zip_code='62703',
            country='USA',
            latitude=39.7717,
            longitude=-89.6401,
            description='Administrative offices',
            contact_person='Bob Johnson',
            contact_phone='555-0102',
            contact_email='admin@company.com',
            company_id=company.id
        )
        
        db.session.add_all([location1, location2, location3])
        db.session.commit()
        print("✅ Locations created")
        
        # Create users with different roles
        print("Creating users...")
        admin = User(
            username='admin',
            email='admin@company.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            department='IT',
            phone='555-0100',
            location_id=location3.id,
            company_id=company.id
        )
        admin.set_password('admin123')
        
        manager = User(
            username='manager',
            email='manager@company.com',
            first_name='Sarah',
            last_name='Manager',
            role='manager',
            department='Maintenance',
            phone='555-0101',
            location_id=location1.id,
            company_id=company.id
        )
        manager.set_password('manager123')
        
        technician1 = User(
            username='tech1',
            email='tech1@company.com',
            first_name='John',
            last_name='Technician',
            role='technician',
            department='Maintenance',
            phone='555-0102',
            location_id=location1.id,
            company_id=company.id
        )
        technician1.set_password('tech123')
        
        technician2 = User(
            username='tech2',
            email='tech2@company.com',
            first_name='Mike',
            last_name='Wilson',
            role='technician',
            department='Maintenance',
            phone='555-0103',
            location_id=location1.id,
            company_id=company.id
        )
        technician2.set_password('tech123')
        
        technician3 = User(
            username='tech3',
            email='tech3@company.com',
            first_name='Lisa',
            last_name='Garcia',
            role='technician',
            department='Maintenance',
            phone='555-0104',
            location_id=location2.id,
            company_id=company.id
        )
        technician3.set_password('tech123')
        
        viewer = User(
            username='viewer',
            email='viewer@company.com',
            first_name='Tom',
            last_name='Viewer',
            role='viewer',
            department='Operations',
            phone='555-0105',
            location_id=location3.id,
            company_id=company.id
        )
        viewer.set_password('viewer123')
        
        db.session.add_all([admin, manager, technician1, technician2, technician3, viewer])
        db.session.commit()
        print("✅ Users created")
        
        # Create teams
        print("Creating teams...")
        maintenance_team = Team(
            name='Maintenance Team A',
            description='Primary maintenance team for Building A',
            company_id=company.id
        )
        maintenance_team.members = [technician1, technician2]
        
        warehouse_team = Team(
            name='Warehouse Team',
            description='Maintenance team for warehouse operations',
            company_id=company.id
        )
        warehouse_team.members = [technician3]
        
        emergency_team = Team(
            name='Emergency Response Team',
            description='Team for critical equipment and emergency situations',
            company_id=company.id
        )
        emergency_team.members = [technician1, technician2, technician3]
        
        db.session.add_all([maintenance_team, warehouse_team, emergency_team])
        db.session.commit()
        print("✅ Teams created")
        
        # Create equipment with locations
        print("Creating equipment...")
        equipment1 = Equipment(
            name='HVAC Unit #1',
            equipment_id='HVAC-001',
            category='hvac',
            type='Climate Control',
            manufacturer='Carrier',
            model='48TC',
            serial_number='SN123456789',
            location='Building A - Floor 1',
            location_id=location1.id,
            department='Facilities',
            status='operational',
            criticality='high',
            description='Main HVAC unit for Building A',
            specifications='48,000 BTU cooling capacity, 3-phase power',
            tags='hvac,climate,air-conditioning',
            company_id=company.id
        )
        
        equipment2 = Equipment(
            name='Production Line Conveyor',
            equipment_id='CONV-001',
            category='machinery',
            type='Conveyor System',
            manufacturer='Hytrol',
            model='EZLogic',
            serial_number='SN987654321',
            location='Production Floor',
            location_id=location1.id,
            department='Manufacturing',
            status='operational',
            criticality='critical',
            description='Main production line conveyor system',
            specifications='100 ft length, 500 lb capacity, variable speed',
            tags='conveyor,production,automation',
            company_id=company.id
        )
        
        equipment3 = Equipment(
            name='Emergency Generator',
            equipment_id='GEN-001',
            category='electrical',
            type='Backup Power',
            manufacturer='Cummins',
            model='C1100D5',
            serial_number='SN456789123',
            location='Generator Room',
            location_id=location1.id,
            department='Facilities',
            status='operational',
            criticality='critical',
            description='Emergency backup generator',
            specifications='1100 kW, Diesel powered, automatic transfer switch',
            tags='generator,emergency,power',
            company_id=company.id
        )
        
        equipment4 = Equipment(
            name='Forklift #1',
            equipment_id='FL-001',
            category='vehicles',
            type='Material Handling',
            manufacturer='Toyota',
            model='8FGCU25',
            serial_number='SN789123456',
            location='Warehouse Floor',
            location_id=location2.id,
            department='Warehouse',
            status='operational',
            criticality='medium',
            description='Electric forklift for warehouse operations',
            specifications='5000 lb capacity, 48V battery, 3-wheel design',
            tags='forklift,warehouse,material-handling',
            company_id=company.id
        )
        
        equipment5 = Equipment(
            name='Compressor Station',
            equipment_id='COMP-001',
            category='pneumatic',
            type='Air System',
            manufacturer='Ingersoll Rand',
            model='XP750',
            serial_number='SN321654987',
            location='Compressor Room',
            location_id=location1.id,
            department='Manufacturing',
            status='maintenance',
            criticality='high',
            description='Industrial air compressor for manufacturing',
            specifications='750 CFM, 150 PSI, 100 HP motor',
            tags='compressor,air,pneumatic',
            company_id=company.id
        )
        
        db.session.add_all([equipment1, equipment2, equipment3, equipment4, equipment5])
        db.session.commit()
        print("✅ Equipment created")
        
        # Create SOPs with checklist items
        print("Creating SOPs...")
        sop1 = SOP(
            name='HVAC Filter Replacement',
            description='Standard procedure for replacing HVAC air filters',
            category='PM',
            equipment_id=equipment1.id,
            estimated_duration=60,
            safety_notes='Ensure power is off before accessing filter compartment',
            required_tools='Screwdriver, new filters, gloves',
            required_parts='Air filters (part #FILTER-001)',
            is_active=True,
            created_by_id=admin.id,
            company_id=company.id
        )
        
        sop2 = SOP(
            name='Conveyor Belt Inspection',
            description='Weekly inspection procedure for conveyor belts',
            category='PM',
            equipment_id=equipment2.id,
            estimated_duration=30,
            safety_notes='Lock out/tag out before inspection, check for moving parts',
            required_tools='Flashlight, measuring tape, inspection mirror',
            required_parts='None',
            is_active=True,
            created_by_id=admin.id,
            company_id=company.id
        )
        
        sop3 = SOP(
            name='Emergency Generator Test',
            description='Monthly testing procedure for emergency generator',
            category='PM',
            equipment_id=equipment3.id,
            estimated_duration=120,
            safety_notes='Wear hearing protection, ensure proper ventilation',
            required_tools='Multimeter, fuel gauge, hearing protection',
            required_parts='None',
            is_active=True,
            created_by_id=admin.id,
            company_id=company.id
        )
        
        db.session.add_all([sop1, sop2, sop3])
        db.session.commit()
        
        # Create checklist items for SOPs
        checklist1_1 = SOPChecklistItem(
            sop_id=sop1.id,
            description='Turn off HVAC unit power',
            order=1,
            is_required=True,
            expected_result='Unit is completely powered off'
        )
        
        checklist1_2 = SOPChecklistItem(
            sop_id=sop1.id,
            description='Remove old air filters',
            order=2,
            is_required=True,
            expected_result='Old filters removed and disposed properly'
        )
        
        checklist1_3 = SOPChecklistItem(
            sop_id=sop1.id,
            description='Install new air filters',
            order=3,
            is_required=True,
            expected_result='New filters installed correctly'
        )
        
        checklist1_4 = SOPChecklistItem(
            sop_id=sop1.id,
            description='Restore power and test operation',
            order=4,
            is_required=True,
            expected_result='Unit operates normally with new filters'
        )
        
        checklist2_1 = SOPChecklistItem(
            sop_id=sop2.id,
            description='Inspect belt tension',
            order=1,
            is_required=True,
            expected_result='Belt tension is within specifications'
        )
        
        checklist2_2 = SOPChecklistItem(
            sop_id=sop2.id,
            description='Check for belt wear and damage',
            order=2,
            is_required=True,
            expected_result='No excessive wear or damage found'
        )
        
        checklist2_3 = SOPChecklistItem(
            sop_id=sop2.id,
            description='Inspect pulley alignment',
            order=3,
            is_required=True,
            expected_result='Pulleys are properly aligned'
        )
        
        db.session.add_all([
            checklist1_1, checklist1_2, checklist1_3, checklist1_4,
            checklist2_1, checklist2_2, checklist2_3
        ])
        db.session.commit()
        print("✅ SOPs and checklists created")
        
        # Create sample inventory items
        print("Creating inventory...")
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
            location='Warehouse A - Shelf 1',
            company_id=company.id
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
            location='Warehouse B - Shelf 3',
            company_id=company.id
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
            location='Warehouse A - Shelf 2',
            company_id=company.id
        )
        
        inventory4 = Inventory(
            part_number='BATTERY-001',
            name='Forklift Battery',
            description='48V battery for electric forklifts',
            category='Batteries',
            manufacturer='EnerSys',
            supplier='Battery World',
            unit_cost=2500.00,
            current_stock=2,
            minimum_stock=1,
            maximum_stock=3,
            unit_of_measure='pieces',
            location='Warehouse B - Shelf 4',
            company_id=company.id
        )
        
        inventory5 = Inventory(
            part_number='COMPRESSOR-001',
            name='Air Compressor Filter',
            description='High-pressure air filter for compressor systems',
            category='Filters',
            manufacturer='Donaldson',
            supplier='Air Systems Inc',
            unit_cost=85.00,
            current_stock=8,
            minimum_stock=3,
            maximum_stock=15,
            unit_of_measure='pieces',
            location='Warehouse A - Shelf 3',
            company_id=company.id
        )
        
        db.session.add_all([inventory1, inventory2, inventory3, inventory4, inventory5])
        db.session.commit()
        print("✅ Inventory items created")
        
        # Create sample work orders
        print("Creating work orders...")
        work_order1 = WorkOrder(
            work_order_number='WO-20241201-ABC12345',
            title='HVAC Filter Replacement',
            description='Replace air filters in HVAC Unit #1 as per preventive maintenance schedule',
            priority='medium',
            type='preventive',
            equipment_id=equipment1.id,
            assigned_technician_id=technician1.id,
            assigned_team_id=maintenance_team.id,
            created_by_id=admin.id,
            estimated_duration=60,
            scheduled_date=datetime.now() + timedelta(days=1),
            due_date=datetime.now() + timedelta(days=2),
            company_id=company.id
        )
        
        work_order2 = WorkOrder(
            work_order_number='WO-20241201-DEF67890',
            title='Conveyor Belt Inspection',
            description='Weekly inspection of conveyor belt for wear and tear',
            priority='high',
            type='preventive',
            equipment_id=equipment2.id,
            assigned_technician_id=technician2.id,
            assigned_team_id=maintenance_team.id,
            created_by_id=manager.id,
            estimated_duration=30,
            scheduled_date=datetime.now() + timedelta(days=2),
            due_date=datetime.now() + timedelta(days=3),
            company_id=company.id
        )
        
        work_order3 = WorkOrder(
            work_order_number='WO-20241201-GHI11111',
            title='Compressor Repair',
            description='Compressor showing unusual noise and vibration. Needs immediate attention.',
            priority='urgent',
            type='corrective',
            equipment_id=equipment5.id,
            assigned_technician_id=technician1.id,
            assigned_team_id=emergency_team.id,
            created_by_id=manager.id,
            estimated_duration=240,
            scheduled_date=datetime.now(),
            due_date=datetime.now() + timedelta(hours=8),
            company_id=company.id
        )
        
        work_order4 = WorkOrder(
            work_order_number='WO-20241201-JKL22222',
            title='Forklift Battery Maintenance',
            description='Monthly battery maintenance and cleaning for Forklift #1',
            priority='low',
            type='preventive',
            equipment_id=equipment4.id,
            assigned_technician_id=technician3.id,
            assigned_team_id=warehouse_team.id,
            created_by_id=manager.id,
            estimated_duration=90,
            scheduled_date=datetime.now() + timedelta(days=5),
            due_date=datetime.now() + timedelta(days=7),
            company_id=company.id
        )
        
        db.session.add_all([work_order1, work_order2, work_order3, work_order4])
        db.session.commit()
        print("✅ Work orders created")
        
        # Create sample maintenance schedules
        print("Creating maintenance schedules...")
        schedule1 = MaintenanceSchedule(
            equipment_id=equipment1.id,
            schedule_type='calendar',
            frequency='monthly',
            frequency_value=1,
            description='Monthly HVAC filter replacement',
            estimated_duration=60,
            is_active=True,
            sop_id=sop1.id,
            assigned_team_id=maintenance_team.id,
            next_due=datetime.now() + timedelta(days=30),
            company_id=company.id
        )
        
        schedule2 = MaintenanceSchedule(
            equipment_id=equipment2.id,
            schedule_type='calendar',
            frequency='weekly',
            frequency_value=1,
            description='Weekly conveyor belt inspection',
            estimated_duration=30,
            is_active=True,
            sop_id=sop2.id,
            assigned_team_id=maintenance_team.id,
            next_due=datetime.now() + timedelta(days=7),
            company_id=company.id
        )
        
        schedule3 = MaintenanceSchedule(
            equipment_id=equipment3.id,
            schedule_type='calendar',
            frequency='monthly',
            frequency_value=1,
            description='Monthly emergency generator test',
            estimated_duration=120,
            is_active=True,
            sop_id=sop3.id,
            assigned_team_id=emergency_team.id,
            next_due=datetime.now() + timedelta(days=15),
            company_id=company.id
        )
        
        schedule4 = MaintenanceSchedule(
            equipment_id=equipment4.id,
            schedule_type='calendar',
            frequency='monthly',
            frequency_value=1,
            description='Monthly forklift battery maintenance',
            estimated_duration=90,
            is_active=True,
            assigned_team_id=warehouse_team.id,
            next_due=datetime.now() + timedelta(days=20),
            company_id=company.id
        )
        
        db.session.add_all([schedule1, schedule2, schedule3, schedule4])
        db.session.commit()
        print("✅ Maintenance schedules created")
        
        # Create WhatsApp templates
        print("Creating WhatsApp templates...")
        template1 = WhatsAppTemplate(
            name='work_order_assignment',
            category='work_order',
            template_id='work_order_assignment',
            language='en',
            content='🔧 New Work Order Assigned\n\nWork Order: {{work_order_number}}\nEquipment: {{equipment_name}}\nPriority: {{priority}}\nDescription: {{description}}',
            variables=json.dumps(['work_order_number', 'equipment_name', 'priority', 'description']),
            is_active=True,
            company_id=company.id
        )
        
        template2 = WhatsAppTemplate(
            name='priority_escalation',
            category='work_order',
            template_id='priority_escalation',
            language='en',
            content='🚨 Priority Escalated\n\nWork Order: {{work_order_number}}\nEquipment: {{equipment_name}}\nPriority: {{old_priority}} → {{new_priority}}\nPlease prioritize this work order.',
            variables=json.dumps(['work_order_number', 'equipment_name', 'old_priority', 'new_priority']),
            is_active=True,
            company_id=company.id
        )
        
        template3 = WhatsAppTemplate(
            name='maintenance_reminder',
            category='maintenance',
            template_id='maintenance_reminder',
            language='en',
            content='📅 Maintenance Reminder\n\nEquipment: {{equipment_name}}\nTask: {{task_description}}\nDue: {{due_date}}',
            variables=json.dumps(['equipment_name', 'task_description', 'due_date']),
            is_active=True,
            company_id=company.id
        )
        
        template4 = WhatsAppTemplate(
            name='emergency_broadcast',
            category='emergency',
            template_id='emergency_broadcast',
            language='en',
            content='🚨 EMERGENCY: {{title}}\n\n{{message}}\n\nPriority: {{priority}}',
            variables=json.dumps(['title', 'message', 'priority']),
            is_active=True,
            company_id=company.id
        )
        
        db.session.add_all([template1, template2, template3, template4])
        db.session.commit()
        print("✅ WhatsApp templates created")
        
        # Create sample WhatsApp users (verified)
        print("Creating WhatsApp users...")
        whatsapp_user1 = WhatsAppUser(
            user_id=technician1.id,
            whatsapp_number='+15550101010',
            is_verified=True,
            preferred_language='en',
            notification_preferences=json.dumps({
                'work_order_assignments': True,
                'priority_escalations': True,
                'parts_delivery': True,
                'maintenance_reminders': True,
                'emergency_broadcasts': True,
                'daily_checklists': True
            }),
            is_active=True,
            company_id=company.id
        )
        
        whatsapp_user2 = WhatsAppUser(
            user_id=technician2.id,
            whatsapp_number='+15550101011',
            is_verified=True,
            preferred_language='es',
            notification_preferences=json.dumps({
                'work_order_assignments': True,
                'priority_escalations': True,
                'parts_delivery': False,
                'maintenance_reminders': True,
                'emergency_broadcasts': True,
                'daily_checklists': False
            }),
            is_active=True,
            company_id=company.id
        )
        
        whatsapp_user3 = WhatsAppUser(
            user_id=technician3.id,
            whatsapp_number='+15550101012',
            is_verified=False,  # Not verified yet
            preferred_language='en',
            notification_preferences=json.dumps({
                'work_order_assignments': True,
                'priority_escalations': True,
                'parts_delivery': True,
                'maintenance_reminders': True,
                'emergency_broadcasts': True,
                'daily_checklists': True
            }),
            is_active=True,
            company_id=company.id
        )
        
        db.session.add_all([whatsapp_user1, whatsapp_user2, whatsapp_user3])
        db.session.commit()
        print("✅ WhatsApp users created")
        
        # Create sample emergency broadcast
        print("Creating emergency broadcast...")
        emergency1 = EmergencyBroadcast(
            title='Compressor Emergency Shutdown',
            message='Compressor Station showing critical overheating. All operations in Building A should be stopped immediately. Maintenance team respond immediately.',
            priority='critical',
            equipment_id=equipment5.id,
            location_id=location1.id,
            sent_by_id=manager.id,
            recipients='all',
            is_active=True,
            expires_at=datetime.now() + timedelta(hours=24),
            company_id=company.id
        )
        
        db.session.add(emergency1)
        db.session.commit()
        print("✅ Emergency broadcast created")
        
        # Create sample notification logs
        print("Creating notification logs...")
        notification1 = NotificationLog(
            notification_type='whatsapp',
            recipient_id=technician1.id,
            recipient_whatsapp_id=whatsapp_user1.id,
            subject='New Work Order Assignment',
            content='🔧 New Work Order Assigned\n\nWork Order: WO-20241201-ABC12345\nEquipment: HVAC Unit #1\nPriority: Medium\nDescription: Replace air filters in HVAC Unit #1',
            status='delivered',
            work_order_id=work_order1.id,
            sent_at=datetime.now() - timedelta(hours=2),
            delivered_at=datetime.now() - timedelta(hours=2, minutes=1),
            company_id=company.id
        )
        
        notification2 = NotificationLog(
            notification_type='whatsapp',
            recipient_id=technician2.id,
            recipient_whatsapp_id=whatsapp_user2.id,
            subject='Emergency Broadcast',
            content='🚨 EMERGENCY: Compressor Emergency Shutdown\n\nCompressor Station showing critical overheating. All operations in Building A should be stopped immediately.',
            status='delivered',
            sent_at=datetime.now() - timedelta(hours=1),
            delivered_at=datetime.now() - timedelta(hours=1, minutes=30),
            company_id=company.id
        )
        
        db.session.add_all([notification1, notification2])
        db.session.commit()
        print("✅ Notification logs created")
        
        print("\n🎉 Comprehensive sample data created successfully!")
        print("\n📋 Sample Data Summary:")
        print(f"  • {Location.query.count()} Locations")
        print(f"  • {User.query.count()} Users")
        print(f"  • {Team.query.count()} Teams")
        print(f"  • {Equipment.query.count()} Equipment")
        print(f"  • {SOP.query.count()} SOPs")
        print(f"  • {Inventory.query.count()} Inventory Items")
        print(f"  • {WorkOrder.query.count()} Work Orders")
        print(f"  • {MaintenanceSchedule.query.count()} Maintenance Schedules")
        print(f"  • {WhatsAppTemplate.query.count()} WhatsApp Templates")
        print(f"  • {WhatsAppUser.query.count()} WhatsApp Users")
        print(f"  • {EmergencyBroadcast.query.count()} Emergency Broadcasts")
        print(f"  • {NotificationLog.query.count()} Notification Logs")
        
        print("\n🔑 Login Credentials:")
        print("  Admin: username='admin', password='admin123'")
        print("  Manager: username='manager', password='manager123'")
        print("  Technician 1: username='tech1', password='tech123'")
        print("  Technician 2: username='tech2', password='tech123'")
        print("  Technician 3: username='tech3', password='tech123'")
        print("  Viewer: username='viewer', password='viewer123'")
        
        print("\n📱 WhatsApp Integration:")
        print("  • 2 verified WhatsApp users (tech1, tech2)")
        print("  • 1 unverified user (tech3)")
        print("  • 4 message templates created")
        print("  • Sample emergency broadcast")
        print("  • Sample notification logs")
        
        print("\n🏭 Sample Equipment:")
        print("  • HVAC Unit #1 (operational)")
        print("  • Production Line Conveyor (operational)")
        print("  • Emergency Generator (operational)")
        print("  • Forklift #1 (operational)")
        print("  • Compressor Station (maintenance)")
        
        print("\n📋 Sample Work Orders:")
        print("  • HVAC Filter Replacement (preventive)")
        print("  • Conveyor Belt Inspection (preventive)")
        print("  • Compressor Repair (corrective, urgent)")
        print("  • Forklift Battery Maintenance (preventive)")

        # --- Multi-Tenancy: Create a Second Company and Sample Data ---
        print("Creating second company and sample data...")
        company2 = Company(name='Beta Industries')
        db.session.add(company2)
        db.session.commit()
        print(f"✅ Company created: {company2.name} (ID: {company2.id})")

        # Create a location for Beta Industries
        beta_location = Location(
            name='Beta HQ',
            address='456 Beta Ave',
            city='Metropolis',
            state='NY',
            zip_code='10001',
            country='USA',
            latitude=40.7128,
            longitude=-74.0060,
            description='Main office for Beta Industries',
            contact_person='Jane Beta',
            contact_phone='555-0200',
            contact_email='hq@beta.com',
            company_id=company2.id
        )
        db.session.add(beta_location)
        db.session.commit()

        # Create a user for Beta Industries
        beta_user = User(
            username='beta_admin',
            email='admin@beta.com',
            first_name='Beta',
            last_name='Admin',
            role='admin',
            department='IT',
            phone='555-0201',
            location_id=beta_location.id,
            company_id=company2.id
        )
        beta_user.set_password('beta123')
        db.session.add(beta_user)
        db.session.commit()

        # Create equipment for Beta Industries
        beta_equipment = Equipment(
            name='Beta Generator',
            equipment_id='BGEN-001',
            category='electrical',
            type='Generator',
            manufacturer='GenCo',
            model='BG-1000',
            serial_number='BG1000SN',
            location='Beta HQ - Basement',
            location_id=beta_location.id,
            department='Facilities',
            status='operational',
            criticality='high',
            description='Backup generator for Beta HQ',
            specifications='1000 kW, Diesel',
            tags='generator,backup',
            company_id=company2.id
        )
        db.session.add(beta_equipment)
        db.session.commit()
        print("✅ Sample data for Beta Industries created!")

if __name__ == '__main__':
    print("CMMS Database Initialization")
    print("=" * 40)
    
    try:
        # Initialize database tables
        init_database()
        
        # Ask if user wants sample data
        response = input("\nDo you want to create comprehensive sample data? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            create_sample_data()
        else:
            print("Skipping sample data creation.")
        
        print("\n✅ Database initialization completed!")
        print("You can now run 'python app.py' to start the CMMS application.")
        print("\n📚 Next Steps:")
        print("1. Start the application: python app.py")
        print("2. Login with admin credentials")
        print("3. Explore the WhatsApp integration features")
        print("4. Test emergency broadcasts and notifications")
        
    except Exception as e:
        print(f"❌ Error during database initialization: {e}")
        print("Please check your database connection and try again.") 