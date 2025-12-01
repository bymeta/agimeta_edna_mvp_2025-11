"""Database connection utilities"""

from contextlib import contextmanager
from typing import Generator, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from edna_common.config import get_settings


class DatabasePool:
    """Thread-safe PostgreSQL connection pool"""

    _pool: Optional[ThreadedConnectionPool] = None

    @classmethod
    def get_pool(cls) -> ThreadedConnectionPool:
        """Get or create connection pool"""
        if cls._pool is None:
            settings = get_settings()
            cls._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=settings.database_pool_size + settings.database_max_overflow,
                dsn=settings.database_url,
            )
        return cls._pool

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator[psycopg2.extensions.connection, None, None]:
        """Get a connection from the pool"""
        pool = cls.get_pool()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)

    @classmethod
    @contextmanager
    def get_cursor(cls) -> Generator[RealDictCursor, None, None]:
        """Get a cursor from the pool"""
        with cls.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

