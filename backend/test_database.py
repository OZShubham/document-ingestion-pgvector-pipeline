"""
Test script to verify the database manager works correctly
"""
import asyncio
import os
import sys
from database_manager import DatabaseManager
from config import Config
dir_path = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(dir_path, 'secrets', 'credentials.json')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path





async def inspect_database():
    """Inspect all tables and their columns in the database"""
    
    db_manager = DatabaseManager()
    
    try:
        # Initialize connection pool
        await db_manager._get_pool()
        print("✅ Connected to database\n")
        print("=" * 80)
        
        # Get all tables
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        
        tables = await db_manager.fetch_all(tables_query)
        print(f"📊 Found {len(tables)} tables in the database\n")
        
        for table_row in tables:
            table_name = table_row[0]
            print("=" * 80)
            print(f"📋 TABLE: {table_name}")
            print("=" * 80)
            
            # Get column information
            columns_query = """
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = $1
                ORDER BY ordinal_position;
            """
            
            columns = await db_manager.fetch_all(columns_query, (table_name,))
            
            print(f"\n{'Column Name':<30} {'Data Type':<20} {'Nullable':<10} {'Default':<30}")
            print("-" * 100)
            
            for col in columns:
                col_name = col[0]
                data_type = col[1]
                max_length = col[2]
                is_nullable = col[3]
                col_default = col[4] or ""
                
                # Format data type with length if applicable
                if max_length:
                    data_type = f"{data_type}({max_length})"
                
                print(f"{col_name:<30} {data_type:<20} {is_nullable:<10} {col_default:<30}")
            
            # Get primary keys
            pk_query = """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = $1::regclass AND i.indisprimary;
            """
            
            pks = await db_manager.fetch_all(pk_query, (table_name,))
            if pks:
                pk_names = [pk[0] for pk in pks]
                print(f"\n🔑 Primary Key(s): {', '.join(pk_names)}")
            
            # Get foreign keys
            fk_query = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = $1;
            """
            
            fks = await db_manager.fetch_all(fk_query, (table_name,))
            if fks:
                print(f"\n🔗 Foreign Keys:")
                for fk in fks:
                    print(f"   {fk[0]} -> {fk[1]}.{fk[2]}")
            
            # Get indexes
            idx_query = """
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = $1
                AND schemaname = 'public';
            """
            
            indexes = await db_manager.fetch_all(idx_query, (table_name,))
            if indexes:
                print(f"\n📑 Indexes:")
                for idx in indexes:
                    print(f"   {idx[0]}")
            
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name};"
            count = await db_manager.fetch_one(count_query)
            print(f"\n📊 Row Count: {count[0]}")
            
            print("\n")
        
        print("=" * 80)
        print("✅ Database inspection complete!")
        print("=" * 80)
        
        # Generate CREATE TABLE statements
        print("\n\n" + "=" * 80)
        print("📝 GENERATING CREATE TABLE STATEMENTS")
        print("=" * 80 + "\n")
        
        for table_row in tables:
            table_name = table_row[0]
            
            # Get table definition
            columns = await db_manager.fetch_all(columns_query, (table_name,))
            
            print(f"-- Table: {table_name}")
            print(f"CREATE TABLE IF NOT EXISTS {table_name} (")
            
            col_defs = []
            for col in columns:
                col_name = col[0]
                data_type = col[1]
                max_length = col[2]
                is_nullable = col[3]
                col_default = col[4]
                
                # Format data type
                if max_length:
                    col_type = f"{data_type.upper()}({max_length})"
                else:
                    col_type = data_type.upper()
                
                # Build column definition
                col_def = f"    {col_name} {col_type}"
                
                if is_nullable == 'NO':
                    col_def += " NOT NULL"
                
                if col_default:
                    col_def += f" DEFAULT {col_default}"
                
                col_defs.append(col_def)
            
            print(",\n".join(col_defs))
            print(");\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()
        print("\n🧹 Database connection closed")


async def check_specific_columns():
    """Check if specific columns exist in key tables"""
    
    db_manager = DatabaseManager()
    
    try:
        await db_manager._get_pool()
        
        print("\n" + "=" * 80)
        print("🔍 CHECKING KEY COLUMNS")
        print("=" * 80 + "\n")
        
        # Tables and columns to check
        checks = {
            'projects': ['id', 'name', 'description', 'storage_path', 'created_at', 'updated_at', 'deleted_at'],
            'documents': ['id', 'project_id', 'filename', 'status', 'created_at', 'updated_at', 'deleted_at'],
            'members': ['id', 'project_id', 'user_id', 'email', 'role', 'created_at', 'deleted_at'],
            'document_vectors': ['id', 'document_id', 'project_id', 'embedding', 'content', 'metadata'],
            'document_chunks': ['id', 'document_id', 'project_id', 'chunk_index', 'content_preview']
        }
        
        for table_name, expected_columns in checks.items():
            # Check if table exists
            table_check = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                );
            """
            table_exists = await db_manager.fetch_one(table_check, (table_name,))
            
            if not table_exists[0]:
                print(f"❌ Table '{table_name}' does NOT exist")
                continue
            
            print(f"✅ Table '{table_name}' exists")
            
            # Get actual columns
            columns_query = """
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = $1;
            """
            actual_columns_rows = await db_manager.fetch_all(columns_query, (table_name,))
            actual_columns = [row[0] for row in actual_columns_rows]
            
            # Check each expected column
            for col in expected_columns:
                if col in actual_columns:
                    print(f"   ✅ Column '{col}' exists")
                else:
                    print(f"   ❌ Column '{col}' MISSING")
            
            # Show extra columns not in expected list
            extra = set(actual_columns) - set(expected_columns)
            if extra:
                print(f"   ℹ️  Extra columns: {', '.join(extra)}")
            
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     DATABASE SCHEMA INSPECTOR                                ║
║                                                                              ║
║  This script will analyze your database structure and show:                 ║
║  • All tables and their columns                                             ║
║  • Data types and constraints                                               ║
║  • Primary and foreign keys                                                 ║
║  • Indexes                                                                   ║
║  • Row counts                                                                ║
║  • Missing columns that the API expects                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Run inspection
    asyncio.run(inspect_database())
    
    # Check specific columns
    asyncio.run(check_specific_columns())
    
    print("\n" + "=" * 80)
    print("✨ Inspection complete! Review the output above.")
    print("=" * 80)