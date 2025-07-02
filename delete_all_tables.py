#!/usr/bin/env python3
"""
delete_all_tables.py

WARNING: This script will DROP ALL TABLES in your database.
Use with caution. Make sure you have backups if needed.
"""
from app import app, db

if __name__ == '__main__':
    print("WARNING: This will permanently DELETE ALL TABLES in your database!")
    confirm = input("Type 'DELETE' to confirm: ").strip()
    if confirm == 'DELETE':
        with app.app_context():
            db.drop_all()
            print("✅ All tables dropped successfully.")
    else:
        print("Operation cancelled.") 