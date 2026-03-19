#!/usr/bin/env python
"""Script to add is_deleted column to leads table"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column exists
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('leads')]
        
        if 'is_deleted' not in columns:
            # Add the column
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE leads ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL'))
                conn.commit()
            print('✓ is_deleted column added successfully')
        else:
            print('✓ is_deleted column already exists')
    except Exception as e:
        print(f'Error: {e}')
