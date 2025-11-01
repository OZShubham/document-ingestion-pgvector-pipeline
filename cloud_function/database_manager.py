import asyncpg
import asyncio
import logging
import os
from typing import Optional, List, Any
from google.cloud.sql.connector import Connector
from pgvector.asyncpg import register_vector
from config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager using asyncpg + Cloud SQL Connector + pgvector.
    Uses password authentication only.
    Handles event loop changes in Cloud Functions.
    """

    def __init__(self):
        # Do NOT create Connector or pool at import time
        self._pool = None
        self._connector = None
        self._connector_loop = None  # Track which loop owns the connector
        self._lock = None
        self._lock_loop = None  # Track which loop owns the lock
        self._initialized = False

    async def _ensure_lock(self):
        """Ensure lock exists for current event loop"""
        current_loop = asyncio.get_running_loop()
        
        if self._lock is None or self._lock_loop is not current_loop:
            self._lock = asyncio.Lock()
            self._lock_loop = current_loop
            logger.debug("🔒 Created new lock for current event loop")
        
        return self._lock

    async def _ensure_connector(self):
        """Ensure connector exists in current event loop"""
        current_loop = asyncio.get_running_loop()
        
        # If connector exists but is for a different loop, close it and create new one
        if self._connector is not None and self._connector_loop is not current_loop:
            logger.info("🔄 Event loop changed, closing old connector and creating new one")
            try:
                await self._connector.close_async()
            except Exception as e:
                logger.warning(f"⚠️ Error closing old connector: {e}")
            self._connector = None
            self._pool = None  # Also invalidate pool
        
        # Create new connector if needed
        if self._connector is None:
            self._connector = Connector(loop=current_loop)
            self._connector_loop = current_loop
            logger.info("✅ Cloud SQL Connector initialized with current event loop")
        
        return self._connector

    async def _get_pool(self) -> "SimpleConnectionPool":
        """Get or create connection pool (loop-safe)."""
        current_loop = asyncio.get_running_loop()
        
        # If pool exists but connector is for different loop, invalidate pool
        if self._pool is not None and self._connector_loop is not current_loop:
            logger.info("🔄 Event loop changed, invalidating pool")
            self._pool = None
        
        if self._pool is not None:
            return self._pool

        # Create lock if needed
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            # Double-check after acquiring lock
            if self._pool is not None and self._connector_loop is current_loop:
                return self._pool

            # Ensure connector exists for current loop
            await self._ensure_connector()

            # Get credentials from environment
            db_instance = os.getenv("DB_INSTANCE")
            if not db_instance:
                # Fallback to Config if env var not set
                from config import Config
                config = Config()
                db_instance = config.DB_INSTANCE
            
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD")
            
            if not db_password:
                raise ValueError("DB_PASSWORD environment variable is required")
            
            # Get other config values
            from config import Config
            config = Config()
            
            logger.info("🔐 Using password authentication")
            logger.info(f"🔌 Initializing database connection pool...")
            
            # Check if DB_INSTANCE is already a full connection string (PROJECT:REGION:INSTANCE)
            # or just the instance name
            if db_instance and db_instance.count(':') >= 2:
                # Already a full connection string
                instance_connection_name = db_instance
                logger.info(f"   Using full connection string: {instance_connection_name}")
            else:
                # Just instance name, build full string
                instance_connection_name = f"{config.PROJECT_ID}:{config.DB_REGION}:{db_instance}"
                logger.info(f"   Built connection string: {instance_connection_name}")
            
            logger.info(f"   User: {db_user}")
            logger.info(f"   Database: {config.DB_NAME}")

            # Connection factory function
            async def get_connection():
                try:
                    connector = await self._ensure_connector()
                    
                    conn = await connector.connect_async(
                        instance_connection_string=instance_connection_name,
                        driver="asyncpg",
                        user=db_user,
                        password=db_password,
                        db=config.DB_NAME,
                    )
                    
                    # Register pgvector extension on the connection
                    try:
                        await register_vector(conn)
                        logger.debug("✅ Registered pgvector on connection")
                    except Exception as e:
                        logger.warning(f"⚠️ register_vector failed: {e}")
                    
                    return conn
                except Exception as e:
                    logger.error(f"Failed to create connection: {e}", exc_info=True)
                    raise

            # Create initial connections
            logger.info("Creating initial connections...")
            connections = []
            for i in range(2):  # min_size=2
                try:
                    conn = await get_connection()
                    connections.append(conn)
                    logger.info(f"✅ Created connection {i+1}/2")
                except Exception as e:
                    logger.error(f"❌ Failed to create connection {i+1}: {e}")
                    # Clean up any successful connections
                    for c in connections:
                        try:
                            await c.close()
                        except:
                            pass
                    raise

            # Create custom pool
            self._pool = SimpleConnectionPool(
                get_connection_func=get_connection,
                initial_connections=connections,
                max_size=10
            )

            logger.info(f"✅ Database pool initialized with {len(connections)} connections")
            return self._pool

    async def init_vector_extension(self):
        """Enable pgvector extension"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info(f"✅ pgvector extension enabled")
        except Exception as e:
            logger.error(f"❌ Failed to enable vector extension: {e}")
            raise

    async def init_vector_table(self):
        """Initialize vector table for storing embeddings"""
        from config import Config
        config = Config()
        
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Create the table with vector column (dimension from config)
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {config.VECTOR_TABLE_NAME} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        document_id UUID NOT NULL,
                        project_id UUID NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector({config.EMBEDDING_DIMENSION}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                """)

                # Create index for vector similarity search using HNSW (cosine)
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {config.VECTOR_TABLE_NAME}_embedding_idx 
                    ON {config.VECTOR_TABLE_NAME} 
                    USING hnsw (embedding vector_cosine_ops)
                """)

                # Index for project filtering
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {config.VECTOR_TABLE_NAME}_project_idx 
                    ON {config.VECTOR_TABLE_NAME} (project_id)
                """)
            logger.info(f"✅ Vector table '{config.VECTOR_TABLE_NAME}' initialized")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"✅ Vector table '{config.VECTOR_TABLE_NAME}' already exists")
            else:
                logger.error(f"❌ Failed to init vector table: {e}")
                raise

    async def execute_query(self, query: str, params: tuple = None):
        """Execute a single query"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(query, *(params or ()))
            return result

    async def execute_many(self, query: str, params_list: List[tuple]):
        """Execute multiple queries in a transaction"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for params in params_list:
                    await conn.execute(query, *params)

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Any]:
        """Fetch a single row"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *(params or ()))
            return row

    async def fetch_all(self, query: str, params: tuple = None) -> List[Any]:
        """Fetch all rows"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return rows

    async def close(self):
        """Close pool and connector"""
        if self._pool:
            try:
                await self._pool.close()
                logger.info(f"🧹 Closed database pool")
            except Exception as e:
                logger.warning(f"⚠️ Error closing pool: {e}")

        if self._connector:
            try:
                await self._connector.close_async()
                logger.info(f"🧹 Closed Cloud SQL connector")
            except Exception as e:
                logger.warning(f"⚠️ Error closing connector: {e}")

        self._pool = None
        self._connector = None
        self._connector_loop = None
        self._lock = None


class SimpleConnectionPool:
    """
    Simple connection pool for Cloud SQL Connector.
    """

    def __init__(self, get_connection_func, initial_connections, max_size=10):
        self._get_connection_func = get_connection_func
        self._available = list(initial_connections)
        self._in_use = set()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    class _ConnectionContextManager:
        """Context manager for acquiring/releasing connections"""

        def __init__(self, pool):
            self._pool = pool
            self._conn = None

        async def __aenter__(self):
            self._conn = await self._pool._acquire()
            return self._conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._pool._release(self._conn)

    def acquire(self):
        """Get a connection from the pool"""
        return self._ConnectionContextManager(self)

    async def _acquire(self):
        """Internal acquire method"""
        async with self._lock:
            # Try to get an available connection
            if self._available:
                conn = self._available.pop()
                self._in_use.add(conn)
                return conn

            # Create new connection if under max_size
            total = len(self._available) + len(self._in_use)
            if total < self._max_size:
                conn = await self._get_connection_func()
                self._in_use.add(conn)
                return conn

        # Wait for a connection to become available
        await asyncio.sleep(0.1)
        return await self._acquire()

    async def _release(self, conn):
        """Internal release method"""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._available.append(conn)

    async def close(self):
        """Close all connections"""
        async with self._lock:
            for conn in self._available:
                try:
                    await conn.close()
                except Exception:
                    pass
            for conn in list(self._in_use):
                try:
                    await conn.close()
                except Exception:
                    pass
            self._available.clear()
            self._in_use.clear()