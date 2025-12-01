#!/usr/bin/env python3
"""Run database migrations in order"""

import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from POSTGRES_* environment variables"""
    user = os.getenv("POSTGRES_USER", "edna")
    password = os.getenv("POSTGRES_PASSWORD", "edna")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "edna")
    
    # Allow override with DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_migration_files(migrations_dir: Path) -> List[Tuple[str, Path]]:
    """Get migration files sorted by name"""
    migrations = []
    for file_path in sorted(migrations_dir.glob("*.sql")):
        migrations.append((file_path.stem, file_path))
    return migrations


def compute_checksum(content: str) -> str:
    """Compute SHA256 checksum of migration content"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_applied_migrations(conn) -> set:
    """Get set of already applied migration IDs"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT migration_id FROM edna_migrations")
        return {row["migration_id"] for row in cur.fetchall()}


def apply_migration(conn, migration_id: str, file_path: Path) -> None:
    """Apply a single migration file"""
    logger.info(f"Applying migration: {migration_id}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    checksum = compute_checksum(content)
    
    # Execute migration - split by semicolon and execute each statement
    # Filter out empty statements and comments
    statements = []
    current_statement = []
    
    for line in content.split('\n'):
        stripped = line.strip()
        # Skip empty lines and single-line comments
        if not stripped or stripped.startswith('--'):
            continue
        current_statement.append(line)
        # If line ends with semicolon, it's the end of a statement
        if stripped.endswith(';'):
            stmt = '\n'.join(current_statement).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current_statement = []
    
    # Execute each statement
    with conn.cursor() as cur:
        for statement in statements:
            if statement:
                try:
                    cur.execute(statement)
                except psycopg2.Error as e:
                    logger.error(f"Error executing statement in {migration_id}: {e}")
                    logger.error(f"Statement: {statement[:200]}...")
                    raise
    
    # Record migration
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO edna_migrations (migration_id, checksum)
            VALUES (%s, %s)
            ON CONFLICT (migration_id) DO NOTHING
        """, (migration_id, checksum))
    
    conn.commit()
    logger.info(f"✓ Applied migration: {migration_id}")


def ensure_migration_table(conn) -> None:
    """Ensure migration tracking table exists"""
    migration_table_sql = """
    CREATE TABLE IF NOT EXISTS edna_migrations (
        migration_id VARCHAR(255) PRIMARY KEY,
        applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        checksum VARCHAR(64)
    );
    CREATE INDEX IF NOT EXISTS idx_edna_migrations_applied_at ON edna_migrations(applied_at);
    """
    
    with conn.cursor() as cur:
        cur.execute(migration_table_sql)
    conn.commit()


def run_migrations(migrations_dir: Path) -> None:
    """Run all pending migrations"""
    database_url = get_database_url()
    logger.info(f"Connecting to database: {database_url.split('@')[-1] if '@' in database_url else '***'}")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        
        # Ensure migration table exists
        ensure_migration_table(conn)
        
        # Get applied migrations
        applied = get_applied_migrations(conn)
        logger.info(f"Found {len(applied)} already applied migrations")
        
        # Get all migration files
        migrations = get_migration_files(migrations_dir)
        logger.info(f"Found {len(migrations)} migration files")
        
        # Apply pending migrations
        applied_count = 0
        for migration_id, file_path in migrations:
            if migration_id in applied:
                logger.info(f"⏭ Skipping already applied migration: {migration_id}")
                continue
            
            apply_migration(conn, migration_id, file_path)
            applied_count += 1
        
        if applied_count == 0:
            logger.info("✓ All migrations are up to date")
        else:
            logger.info(f"✓ Applied {applied_count} migration(s)")
        
        conn.close()
        
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point"""
    # Determine migrations directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    migrations_dir = repo_root / "infra" / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    logger.info(f"Running migrations from: {migrations_dir}")
    run_migrations(migrations_dir)


if __name__ == "__main__":
    main()

