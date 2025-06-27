#!/usr/bin/env python3
"""
Database migration script to add SOP (Standard Operating Procedures) system
This script adds the new tables for SOPs, checklist items, and work order checklists
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import SOP, SOPChecklistItem, WorkOrderChecklist

def migrate_sop_system():
    """Migrate database to add SOP system tables"""
    print("Starting SOP system migration...")
    
    with app.app_context():
        try:
            # Create new tables
            print("Creating SOP tables...")
            db.create_all()
            
            # Check if tables were created successfully
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            required_tables = ['sops', 'sop_checklist_items', 'work_order_checklists']
            created_tables = []
            
            for table in required_tables:
                if table in existing_tables:
                    created_tables.append(table)
                    print(f"✓ Table '{table}' exists")
                else:
                    print(f"✗ Table '{table}' was not created")
            
            if len(created_tables) == len(required_tables):
                print("\n✅ SOP system migration completed successfully!")
                print(f"Created {len(created_tables)} new tables:")
                for table in created_tables:
                    print(f"  - {table}")
                
                # Add sample SOP data
                print("\nCreating sample SOP data...")
                create_sample_data()
                
            else:
                print(f"\n❌ Migration failed. Only {len(created_tables)} of {len(required_tables)} tables were created.")
                return False
                
        except Exception as e:
            print(f"❌ Migration failed with error: {str(e)}")
            return False
    
    return True

def create_sample_data():
    """Create sample SOP data for testing"""
    try:
        from models import User, Equipment
        
        # Get first user and equipment for sample data
        user = User.query.first()
        equipment = Equipment.query.first()
        
        if not user or not equipment:
            print("⚠️  No users or equipment found. Skipping sample data creation.")
            return
        
        # Create sample SOP
        sop = SOP(
            name="Conveyor Belt Maintenance",
            description="Regular maintenance procedure for conveyor belt system including cleaning, inspection, and lubrication.",
            category="PM",
            equipment_id=equipment.id,
            estimated_duration=45,
            safety_notes="Ensure conveyor is stopped and locked out before performing maintenance. Wear appropriate PPE.",
            required_tools="Grease gun, cleaning supplies, inspection mirror, flashlight",
            required_parts="Conveyor belt grease, cleaning cloths",
            is_active=True,
            created_by_id=user.id
        )
        
        db.session.add(sop)
        db.session.flush()  # Get the SOP ID
        
        # Create checklist items
        checklist_items = [
            {
                'description': 'Stop conveyor and lock out power',
                'order': 1,
                'is_required': True,
                'expected_result': 'Conveyor is completely stopped and cannot be started'
            },
            {
                'description': 'Inspect belt for damage or wear',
                'order': 2,
                'is_required': True,
                'expected_result': 'Belt is in good condition with no visible damage'
            },
            {
                'description': 'Clean belt surface and rollers',
                'order': 3,
                'is_required': True,
                'expected_result': 'Belt and rollers are clean and free of debris'
            },
            {
                'description': 'Lubricate roller bearings',
                'order': 4,
                'is_required': True,
                'expected_result': 'All bearings are properly lubricated'
            },
            {
                'description': 'Check belt tension',
                'order': 5,
                'is_required': True,
                'expected_result': 'Belt tension is within specifications'
            },
            {
                'description': 'Test conveyor operation',
                'order': 6,
                'is_required': True,
                'expected_result': 'Conveyor starts and runs smoothly'
            },
            {
                'description': 'Document maintenance in log',
                'order': 7,
                'is_required': False,
                'expected_result': 'Maintenance activities are recorded'
            }
        ]
        
        for item_data in checklist_items:
            checklist_item = SOPChecklistItem(
                sop_id=sop.id,
                description=item_data['description'],
                order=item_data['order'],
                is_required=item_data['is_required'],
                expected_result=item_data['expected_result']
            )
            db.session.add(checklist_item)
        
        db.session.commit()
        print("✅ Sample SOP 'Conveyor Belt Maintenance' created with 7 checklist items")
        
    except Exception as e:
        print(f"⚠️  Error creating sample data: {str(e)}")
        db.session.rollback()

if __name__ == "__main__":
    print("=" * 50)
    print("SOP System Database Migration")
    print("=" * 50)
    
    success = migrate_sop_system()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Start the application: python app.py")
        print("2. Navigate to /sops to view and manage SOPs")
        print("3. Navigate to /calendar to view maintenance calendar")
        print("4. Create maintenance schedules with SOP assignments")
    else:
        print("\n💥 Migration failed. Please check the error messages above.")
        sys.exit(1) 