"""PostgreSQL schema introspection and profiling"""

import logging
import re
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from fnmatch import fnmatch
import hashlib

logger = logging.getLogger(__name__)


class Scanner:
    """Scans PostgreSQL schemas and profiles tables"""

    def __init__(self, database_url: str):
        self.database_url = database_url  # URL to edna database (for config)
        self._edna_connection = None

    def get_connection(self, database_url: Optional[str] = None):
        """Get database connection"""
        url = database_url or self.database_url
        return psycopg2.connect(url)
    
    def get_edna_connection(self):
        """Get connection to edna database (for reading source database configs)"""
        if self._edna_connection is None or self._edna_connection.closed:
            self._edna_connection = psycopg2.connect(self.database_url)
        return self._edna_connection
    
    def get_source_databases(self) -> List[Dict[str, Any]]:
        """Get list of active source databases to scan"""
        with self.get_edna_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        source_db_id,
                        source_db_name,
                        host,
                        port,
                        database_name,
                        username,
                        password_encrypted,
                        schemas,
                        table_blacklist,
                        metadata
                    FROM edna_source_databases
                    WHERE active = TRUE
                    ORDER BY source_db_name
                """)
                return [dict(row) for row in cur.fetchall()]
    
    def build_database_url(self, source_db: Dict[str, Any]) -> str:
        """Build PostgreSQL connection URL from source database config"""
        # For now, use password_encrypted directly (in production, decrypt it)
        password = source_db.get("password_encrypted", "")
        if not password:
            # Try to get from metadata
            password = source_db.get("metadata", {}).get("password", "")

        host = source_db["host"]
        port = source_db["port"]

        # Special handling: allow 'localhost' from UI, map to host.docker.internal inside Docker
        if host in ("localhost", "127.0.0.1"):
            host = "host.docker.internal"
        
        # Build DSN (allow empty password)
        if password:
            return f"postgresql://{source_db['username']}:{password}@{host}:{port}/{source_db['database_name']}"
        else:
            return f"postgresql://{source_db['username']}@{host}:{port}/{source_db['database_name']}"
    
    def is_table_blacklisted(self, table_name: str, blacklist: List[str]) -> bool:
        """Check if table name matches any blacklist pattern"""
        if not blacklist:
            return False
        
        for pattern in blacklist:
            # Support % wildcard (convert to fnmatch pattern)
            fnmatch_pattern = pattern.replace('%', '*')
            if fnmatch(table_name.lower(), fnmatch_pattern.lower()):
                return True
        return False

    def enumerate_tables(self, schema: str = "public", database_url: Optional[str] = None, blacklist: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Enumerate all tables in a schema"""
        with self.get_connection(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """, (schema,))
                tables = [dict(row) for row in cur.fetchall()]
                
                # Filter blacklisted tables
                if blacklist:
                    tables = [
                        t for t in tables 
                        if not self.is_table_blacklisted(t["table_name"], blacklist)
                    ]
                
                return tables

    def profile_table(self, schema: str, table: str, database_url: Optional[str] = None) -> Dict[str, Any]:
        """Profile a single table"""
        with self.get_connection(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get row count
                cur.execute(f'SELECT COUNT(*) as count FROM "{schema}"."{table}"')
                row_count = cur.fetchone()["count"]

                # Get column information
                cur.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, table))
                columns = [dict(row) for row in cur.fetchall()]

                # Column-level profiling (distinct_count, null_count, null_rate)
                column_profiles: List[Dict[str, Any]] = []
                for col in columns:
                    col_name = col["column_name"]
                    try:
                        # Compute distinct and null counts per column
                        cur.execute(
                            f'''
                            SELECT 
                                COUNT(DISTINCT "{col_name}") AS distinct_count,
                                SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END) AS null_count
                            FROM "{schema}"."{table}"
                            '''
                        )
                        stats = cur.fetchone()
                        distinct_count = stats["distinct_count"]
                        null_count = stats["null_count"] or 0
                        null_rate = float(null_count) / float(row_count) if row_count > 0 else None
                    except Exception:
                        # If anything goes wrong, fall back to None values
                        distinct_count = None
                        null_count = None
                        null_rate = None

                    column_profiles.append(
                        {
                            "column_name": col_name,
                            "data_type": col.get("data_type"),
                            "row_count": row_count,
                            "distinct_count": distinct_count,
                            "null_count": null_count,
                            "null_rate": null_rate,
                        }
                    )

                # Get sample data (first row)
                sample = None
                if row_count > 0:
                    try:
                        cur.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 1')
                        sample_row = cur.fetchone()
                        if sample_row:
                            sample = dict(sample_row)
                    except Exception:
                        # Skip sample if there's an issue (e.g., permissions)
                        pass

                return {
                    "schema": schema,
                    "table": table,
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": columns,
                    "column_profiles": column_profiles,
                    "sample": sample,
                }

    def scan_all_tables(
        self, 
        schema: str = "public", 
        database_url: Optional[str] = None,
        blacklist: Optional[List[str]] = None,
        source_db_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Scan and profile all tables in a schema"""
        tables = self.enumerate_tables(schema, database_url, blacklist)
        profiles = []

        for table_info in tables:
            try:
                profile = self.profile_table(
                    table_info["table_schema"], 
                    table_info["table_name"],
                    database_url
                )
                # Add source database info if provided
                if source_db_id:
                    profile["source_db_id"] = source_db_id
                profiles.append(profile)
                logger.info(
                    f"Profiled {table_info['table_schema']}.{table_info['table_name']}",
                    extra={"row_count": profile["row_count"], "source_db_id": source_db_id}
                )
            except Exception as e:
                logger.error(
                    f"Failed to profile {table_info['table_schema']}.{table_info['table_name']}",
                    exc_info=True
                )

        return profiles
    
    def create_scan_run(self, source_system: str, metrics: Optional[Dict[str, Any]] = None) -> str:
        """Create a new scan_run row and return its ID."""
        metrics_json = json.dumps(metrics or {})
        with self.get_edna_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scan_run (source_system, status, metrics_json)
                    VALUES (%s, 'PENDING', %s::jsonb)
                    RETURNING scan_run_id
                    """,
                    (source_system, metrics_json),
                )
                scan_run_id = cur.fetchone()[0]
                conn.commit()
                return scan_run_id

    def update_scan_run_status(
        self,
        scan_run_id: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update status/metrics for a scan_run."""
        metrics_json = json.dumps(metrics or {})
        with self.get_edna_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE scan_run
                    SET 
                        status = %s,
                        metrics_json = %s::jsonb,
                        ended_at = NOW()
                    WHERE scan_run_id = %s
                    """,
                    (status, metrics_json, scan_run_id),
                )
                conn.commit()

    def persist_scan_profiles(
        self,
        scan_run_id: str,
        source_system: str,
        profiles: List[Dict[str, Any]],
    ) -> None:
        """Persist table/column profiling information for a scan run."""
        if not profiles:
            return

        with self.get_edna_connection() as conn:
            with conn.cursor() as cur:
                for profile in profiles:
                    table_name = f'{profile["schema"]}.{profile["table"]}'
                    row_count = profile.get("row_count")

                    # Create a simple hash of the sample row to detect changes
                    sample = profile.get("sample")
                    sample_hash = None
                    if sample is not None:
                        try:
                            sample_json = json.dumps(sample, sort_keys=True, default=str)
                            sample_hash = hashlib.sha1(sample_json.encode("utf-8")).hexdigest()
                        except Exception:
                            sample_hash = None

                    cur.execute(
                        """
                        INSERT INTO scan_profile_table (
                            scan_run_id,
                            source_system,
                            table_name,
                            row_count,
                            sample_hash
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (scan_run_id, table_name) DO UPDATE SET
                            row_count = EXCLUDED.row_count,
                            sample_hash = EXCLUDED.sample_hash,
                            profiled_at = NOW()
                        """,
                        (scan_run_id, source_system, table_name, row_count, sample_hash),
                    )

                    # Column-level entries
                    for col_profile in profile.get("column_profiles", []):
                        cur.execute(
                            """
                            INSERT INTO scan_profile_column (
                                scan_run_id,
                                source_system,
                                table_name,
                                column_name,
                                data_type,
                                row_count,
                                distinct_count,
                                null_count,
                                null_rate
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (scan_run_id, table_name, column_name) DO UPDATE SET
                                data_type = EXCLUDED.data_type,
                                row_count = EXCLUDED.row_count,
                                distinct_count = EXCLUDED.distinct_count,
                                null_count = EXCLUDED.null_count,
                                null_rate = EXCLUDED.null_rate,
                                profiled_at = NOW()
                            """,
                            (
                                scan_run_id,
                                source_system,
                                table_name,
                                col_profile.get("column_name"),
                                col_profile.get("data_type"),
                                col_profile.get("row_count"),
                                col_profile.get("distinct_count"),
                                col_profile.get("null_count"),
                                col_profile.get("null_rate"),
                            ),
                        )

            conn.commit()
        logger.info(
            "Persisted scan profiles",
            extra={"scan_run_id": scan_run_id, "tables": len(profiles), "source_system": source_system},
        )

    def scan_source_databases(self) -> Dict[str, Any]:
        """Scan all configured source databases"""
        source_dbs = self.get_source_databases()
        
        if not source_dbs:
            logger.warning("No active source databases configured. Scanning default edna database.")
            # Fallback to default behavior: scan current edna database as demo source
            source_system = "demo-db"
            scan_run_id = self.create_scan_run(source_system=source_system)

            try:
                profiles = self.scan_all_tables(schema="public")
                if profiles:
                    # Existing behavior: persist candidates/demonstration objects
                    self.persist_candidates(profiles)
                    # New behavior: persist detailed scan profiles for MVP
                    self.persist_scan_profiles(
                        scan_run_id=scan_run_id,
                        source_system=source_system,
                        profiles=profiles,
                    )

                metrics = {
                    "total_tables": len(profiles),
                    "total_rows": sum(p.get("row_count", 0) for p in profiles),
                }
                self.update_scan_run_status(scan_run_id, "SUCCESS", metrics)

                return {
                    "scanned_databases": 0,
                    "total_tables": len(profiles),
                    "status": "completed",
                    "scan_run_id": scan_run_id,
                    "metrics": metrics,
                }
            except Exception as e:
                logger.error("Fallback scan failed", exc_info=True)
                self.update_scan_run_status(
                    scan_run_id,
                    "FAILED",
                    {"error": str(e)},
                )
                raise
        
        total_profiles = []
        results = {
            "scanned_databases": 0,
            "failed_databases": 0,
            "total_tables": 0,
            "database_results": []
        }
        
        for source_db in source_dbs:
            source_db_id = source_db["source_db_id"]
            source_db_name = source_db["source_db_name"]
            
            logger.info(f"Scanning source database: {source_db_name} ({source_db_id})")
            
            try:
                # Build connection URL
                db_url = self.build_database_url(source_db)
                
                # Get schemas to scan
                schemas = source_db.get("schemas") or []
                if not schemas:
                    # If no schemas specified, scan all non-system schemas
                    with self.get_connection(db_url) as conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute("""
                                SELECT DISTINCT table_schema
                                FROM information_schema.tables
                                WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                                AND table_type = 'BASE TABLE'
                                ORDER BY table_schema
                            """)
                            schemas = [row["table_schema"] for row in cur.fetchall()]
                
                # Get blacklist
                blacklist = source_db.get("table_blacklist") or []
                # Always add edna_* to blacklist if not already present
                if "edna_%" not in blacklist:
                    blacklist.append("edna_%")
                
                # Scan each schema
                db_profiles = []
                for schema in schemas:
                    schema_profiles = self.scan_all_tables(
                        schema=schema,
                        database_url=db_url,
                        blacklist=blacklist,
                        source_db_id=source_db_id
                    )
                    db_profiles.extend(schema_profiles)
                
                total_profiles.extend(db_profiles)
                results["scanned_databases"] += 1
                results["total_tables"] += len(db_profiles)
                
                # Update last scan status
                self.update_scan_status(source_db_id, "success", len(db_profiles))
                
                results["database_results"].append({
                    "source_db_id": source_db_id,
                    "source_db_name": source_db_name,
                    "status": "success",
                    "tables_scanned": len(db_profiles),
                    "schemas_scanned": len(schemas)
                })
                
                logger.info(
                    f"✓ Scanned {source_db_name}: {len(db_profiles)} tables in {len(schemas)} schemas"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to scan source database {source_db_name}: {e}",
                    exc_info=True
                )
                results["failed_databases"] += 1
                self.update_scan_status(source_db_id, "failed", 0, str(e))
                
                results["database_results"].append({
                    "source_db_id": source_db_id,
                    "source_db_name": source_db_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Persist all candidates
        if total_profiles:
            self.persist_candidates(total_profiles)
        
        results["status"] = "completed"
        return results
    
    def update_scan_status(
        self, 
        source_db_id: str, 
        status: str, 
        tables_scanned: int = 0,
        error: Optional[str] = None
    ):
        """Update last scan status for a source database"""
        try:
            with self.get_edna_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE edna_source_databases
                        SET 
                            last_scan_at = NOW(),
                            last_scan_status = %s,
                            last_scan_error = %s,
                            updated_at = NOW()
                        WHERE source_db_id = %s
                    """, (status, error, source_db_id))
                    conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update scan status for {source_db_id}: {e}")

    def guess_object_type(self, table_name: str) -> str:
        """Guess object type from table name"""
        # Remove common prefixes/suffixes
        name = table_name.lower()
        
        # Remove common table prefixes
        name = re.sub(r'^(tbl_|tb_|t_|table_)', '', name)
        # Remove common suffixes
        name = re.sub(r'(_tbl|_table|_tb)$', '', name)
        
        # Handle plural forms (simple: remove 's' at end)
        if name.endswith('s') and len(name) > 1:
            name = name[:-1]
        
        # Common mappings
        type_mappings = {
            'customer': 'customer',
            'customers': 'customer',
            'user': 'user',
            'users': 'user',
            'account': 'account',
            'accounts': 'account',
            'order': 'order',
            'orders': 'order',
            'product': 'product',
            'products': 'product',
            'invoice': 'invoice',
            'invoices': 'invoice',
            'contact': 'contact',
            'contacts': 'contact',
            'person': 'person',
            'persons': 'person',
            'people': 'person',
            'employee': 'employee',
            'employees': 'employee',
            'vendor': 'vendor',
            'vendors': 'vendor',
            'supplier': 'supplier',
            'suppliers': 'supplier',
        }
        
        if name in type_mappings:
            return type_mappings[name]
        
        # Default: use the cleaned table name
        return name if name else 'unknown'

    def persist_candidates(self, profiles: List[Dict[str, Any]]) -> None:
        """Persist candidate objects to staging table and create demo objects"""
        if not profiles:
            logger.info("No profiles to persist")
            return
        
        logger.info(f"Persisting {len(profiles)} candidate profiles")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for profile in profiles:
                    schema = profile["schema"]
                    table = profile["table"]
                    row_count = profile["row_count"]
                    guess_type = self.guess_object_type(table)
                    
                    # Insert/update candidate in staging table
                    source_db_id = profile.get("source_db_id")
                    try:
                        # Check if edna_object_candidates has source_db_id column (for future migration)
                        # For now, include source_db_id in metadata or use separate approach
                        cur.execute("""
                            INSERT INTO edna_object_candidates (schema, table_name, guess_type, row_count)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (schema, table_name) 
                            DO UPDATE SET 
                                guess_type = EXCLUDED.guess_type,
                                row_count = EXCLUDED.row_count
                        """, (schema, table, guess_type, row_count))
                        
                        logger.info(
                            f"Persisted candidate: {schema}.{table} -> {guess_type} ({row_count} rows)"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to persist candidate for {schema}.{table}: {e}",
                            exc_info=True
                        )
                        continue
                    
                    # Create demo object in edna_objects if we have sample data
                    if profile.get("sample") and row_count > 0:
                        try:
                            source_id = f"temp:{schema}.{table}"
                            attributes = profile["sample"]
                            
                            # Convert sample data to JSON-serializable format
                            json_attributes = {}
                            for key, value in attributes.items():
                                if value is None:
                                    json_attributes[key] = None
                                elif isinstance(value, (str, int, float, bool)):
                                    json_attributes[key] = value
                                else:
                                    json_attributes[key] = str(value)
                            
                            # Compute a simple golden_id (hash of source_id + object_type)
                            import hashlib
                            golden_id_string = f"scanner|{source_id}|{guess_type}"
                            golden_id = hashlib.sha1(golden_id_string.encode("utf-8")).hexdigest()
                            
                            cur.execute("""
                                INSERT INTO edna_objects (
                                    golden_id, source_system, source_id, object_type, attributes
                                ) VALUES (%s, %s, %s, %s, %s::jsonb)
                                ON CONFLICT (source_system, source_id, object_type)
                                DO UPDATE SET
                                    attributes = EXCLUDED.attributes,
                                    updated_at = NOW()
                            """, (
                                golden_id,
                                "scanner",
                                source_id,
                                guess_type,
                                json.dumps(json_attributes)
                            ))
                            
                            logger.info(
                                f"Created demo object: {source_id} -> {guess_type} (golden_id: {golden_id[:8]}...)"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to create demo object for {schema}.{table}: {e}",
                                exc_info=True
                            )
                            # Don't fail the whole process if demo object creation fails
                            continue
                
                conn.commit()
        
        logger.info(f"✓ Persisted {len(profiles)} candidates")

