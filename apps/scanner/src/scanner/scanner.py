"""PostgreSQL schema introspection and profiling"""

import logging
import re
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)


class Scanner:
    """Scans PostgreSQL schemas and profiles tables"""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

    def enumerate_tables(self, schema: str = "public") -> List[Dict[str, str]]:
        """Enumerate all tables in a schema"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """, (schema,))
                return [dict(row) for row in cur.fetchall()]

    def profile_table(self, schema: str, table: str) -> Dict[str, Any]:
        """Profile a single table"""
        with self.get_connection() as conn:
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
                    "sample": sample,
                }

    def scan_all_tables(self, schema: str = "public") -> List[Dict[str, Any]]:
        """Scan and profile all tables in a schema"""
        tables = self.enumerate_tables(schema)
        profiles = []

        for table_info in tables:
            try:
                profile = self.profile_table(table_info["table_schema"], table_info["table_name"])
                profiles.append(profile)
                logger.info(
                    f"Profiled {table_info['table_schema']}.{table_info['table_name']}",
                    extra={"row_count": profile["row_count"]}
                )
            except Exception as e:
                logger.error(
                    f"Failed to profile {table_info['table_schema']}.{table_info['table_name']}",
                    exc_info=True
                )

        return profiles

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
                    try:
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

