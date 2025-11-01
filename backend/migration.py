"""
Precise Migration Script - Add only the missing columns
"""
import asyncio
import os
import sys
from database_manager import DatabaseManager
import asyncio
from database_manager import DatabaseManager

from config import Config
dir_path = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(dir_path, 'secrets', 'credentials.json')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path


async def add_missing_columns():
    """Add the 2 missing columns identified in schema inspection"""
    
    db_manager = DatabaseManager()
    
    try:
        await db_manager._get_pool()
        print("✅ Connected to database\n")
        
        print("=" * 80)
        print("🔄 Running Migrations")
        print("=" * 80 + "\n")
        
        # Migration 1: Add updated_at to documents table
        print("⏳ Adding 'updated_at' to documents table...")
        try:
            await db_manager.execute_query("""
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            print("✅ Added 'updated_at' to documents - SUCCESS\n")
        except Exception as e:
            print(f"❌ Failed to add 'updated_at' to documents: {e}\n")
        
        # Migration 2: Add deleted_at to members table
        print("⏳ Adding 'deleted_at' to members table...")
        try:
            await db_manager.execute_query("""
                ALTER TABLE members 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;
            """)
            print("✅ Added 'deleted_at' to members - SUCCESS\n")
        except Exception as e:
            print(f"❌ Failed to add 'deleted_at' to members: {e}\n")
        
        # Optional: Add missing columns that might be useful
        print("⏳ Adding optional columns...")
        
        # Add mime_type alias for file_type (for consistency)
        try:
            await db_manager.execute_query("""
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100);
                
                -- Copy file_type to mime_type for existing records
                UPDATE documents SET mime_type = file_type WHERE mime_type IS NULL;
            """)
            print("✅ Added 'mime_type' to documents - SUCCESS\n")
        except Exception as e:
            print(f"❌ Optional mime_type migration: {e}\n")
        
        # Add processing_time_ms if missing
        try:
            await db_manager.execute_query("""
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER;
            """)
            print("✅ Added 'processing_time_ms' to documents - SUCCESS\n")
        except Exception as e:
            print(f"❌ Optional processing_time_ms migration: {e}\n")
        
        # Add chunk_count if missing
        try:
            await db_manager.execute_query("""
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
            """)
            print("✅ Added 'chunk_count' to documents - SUCCESS\n")
        except Exception as e:
            print(f"❌ Optional chunk_count migration: {e}\n")
        
        # Create indexes for better performance
        print("⏳ Creating indexes...")
        try:
            await db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_members_deleted_at 
                ON members(deleted_at) WHERE deleted_at IS NULL;
                
                CREATE INDEX IF NOT EXISTS idx_documents_updated_at 
                ON documents(updated_at);
            """)
            print("✅ Created performance indexes - SUCCESS\n")
        except Exception as e:
            print(f"❌ Index creation: {e}\n")
        
        print("=" * 80)
        print("✅ Migration Complete!")
        print("=" * 80)
        print("\nYou can now restart your FastAPI server.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()
        print("\n🧹 Database connection closed")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PRECISE MIGRATION                                    ║
║                                                                              ║
║  This will add the following missing columns:                               ║
║  1. documents.updated_at  (TIMESTAMP)                                       ║
║  2. members.deleted_at    (TIMESTAMP)                                       ║
║                                                                              ║
║  Optional additions:                                                         ║
║  • documents.mime_type                                                       ║
║  • documents.processing_time_ms                                              ║
║  • documents.chunk_count                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    confirm = input("\n⚠️  Continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        asyncio.run(add_missing_columns())
    else:
        print("❌ Migration cancelled")