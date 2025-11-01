#!/usr/bin/env python3
'''
Setup script for GCP Document Processing Pipeline
Run this after deploying infrastructure
'''

import asyncio
import sys
from database_manager import DatabaseManager

async def setup_database():
    '''Initialize database tables'''
    print("🔧 Setting up database...")
    
    db = DatabaseManager()
    await db.initialize()
    await db.init_vector_table()
    
    # Create example project
    query = '''
        INSERT INTO projects (name, description, storage_path)
        VALUES ($1, $2, $3)
        ON CONFLICT (storage_path) DO NOTHING
        RETURNING id
    '''
    
    result = await db.execute_query(
        query,
        ('Demo Project', 'Demo project for testing', 'documents/demo-project')
    )
    
    row = result.fetchone()
    if row:
        project_id = row[0]
        print(f"✓ Created demo project: {project_id}")
    else:
        print("✓ Demo project already exists")
    
    await db.close()
    print("✅ Database setup complete!")

if __name__ == '__main__':
    asyncio.run(setup_database())