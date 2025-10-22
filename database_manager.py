from langchain_google_cloud_sql_pg import PostgresEngine
import asyncio
import logging
from typing import Optional, List, Dict, Any
import os
 
logger = logging.getLogger(__name__)
 
class DatabaseManager:
    """Enhanced database manager with project isolation"""
    def __init__(self):
        self.engine = None
        self._initialized = False
        self._lock = asyncio.Lock()
    async def initialize(self):
        """Initialize database engine"""
        from config import Config
        async with self._lock:
            if self._initialized:
                return
            try:
                if Config.USE_IAM_AUTH:
                    self.engine = await PostgresEngine.afrom_instance(
                        project_id=Config.PROJECT_ID,
                        region=Config.DB_REGION,
                        instance=Config.DB_INSTANCE,
                        database=Config.DB_NAME,
                        quota_project=Config.PROJECT_ID,
                    )
                else:
                    self.engine = await PostgresEngine.afrom_instance(
                        project_id=Config.PROJECT_ID,
                        region=Config.DB_REGION,
                        instance=Config.DB_INSTANCE,
                        database=Config.DB_NAME,
                        user=os.getenv('DB_USER', 'postgres'),
                        password=os.getenv('DB_PASSWORD'),
                    )
                self._initialized = True
                logger.info("Database connection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise
    async def init_vector_table(self):
        """Initialize vector store table"""
        from config import Config
        try:
            await self.engine.ainit_vectorstore_table(
                table_name=Config.VECTOR_TABLE_NAME,
                vector_size=Config.EMBEDDING_DIMENSION,
            )
            logger.info(f"Vector table {Config.VECTOR_TABLE_NAME} initialized")
        except Exception as e:
            logger.error(f"Failed to init vector table: {e}")
            raise
    async def execute_query(self, query: str, params: tuple = None):
        """Execute query"""
        async with self.engine._pool.connect() as conn:
            if params:
                result = await conn.execute(query, params)
            else:
                result = await conn.execute(query)
            await conn.commit()
            return result
    async def execute_many(self, query: str, params_list: List[tuple]):
        """Execute query with multiple parameter sets"""
        async with self.engine._pool.connect() as conn:
            for params in params_list:
                await conn.execute(query, params)
            await conn.commit()
    async def fetch_one(self, query: str, params: tuple = None) -> Optional[tuple]:
        """Fetch single row"""
        async with self.engine._pool.connect() as conn:
            result = await conn.execute(query, params or ())
            return result.fetchone()
    async def fetch_all(self, query: str, params: tuple = None) -> List[tuple]:
        """Fetch all rows"""
        async with self.engine._pool.connect() as conn:
            result = await conn.execute(query, params or ())
            return result.fetchall()
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine._pool.dispose()
            logger.info("Database connections closed")