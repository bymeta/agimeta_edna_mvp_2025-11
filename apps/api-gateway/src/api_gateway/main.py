"""API Gateway main entry point"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "edna-common" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "identity" / "src"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
import json

import logging
from edna_common.config import get_settings
from edna_common.logging import setup_logging
from edna_common.models import BusinessObject, Event, MatchRule
from identity.matcher import IdentityMatcher

setup_logging("api-gateway")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title="Enterprise DNA API Gateway", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize identity matcher
matcher = IdentityMatcher(settings.database_url)


def run_migrations_on_startup():
    """Run database migrations on startup"""
    try:
        # Determine paths
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        migrations_dir = repo_root / "infra" / "migrations"
        scripts_dir = repo_root / "scripts"
        
        if migrations_dir.exists() and scripts_dir.exists():
            logger.info(f"Running migrations from: {migrations_dir}")
            # Add scripts to path and import
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            
            # Import migration runner
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "run_migrations",
                scripts_dir / "run_migrations.py"
            )
            if spec and spec.loader:
                run_migrations_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(run_migrations_module)
                run_migrations_module.run_migrations(migrations_dir)
                logger.info("✓ Migrations completed")
        else:
            logger.warning(f"Migrations directory not found: {migrations_dir}")
    except Exception as e:
        logger.error(f"Migration failed on startup: {e}", exc_info=True)
        # Don't fail startup, but log the error
        pass


# Run migrations on startup
run_migrations_on_startup()


def get_connection():
    """Get database connection"""
    return psycopg2.connect(settings.database_url)


def validate_sort_order(value: str) -> str:
    """Validate sort order parameter"""
    if value.lower() not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_order: {value}. Must be 'asc' or 'desc'"
        )
    return value.lower()


def validate_sort_field(field: str, allowed_fields: list) -> str:
    """Validate sort field parameter"""
    if field.lower() not in [f.lower() for f in allowed_fields]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by: {field}. Allowed values: {', '.join(allowed_fields)}"
        )
    return field.lower()


@app.get("/healthz")
async def healthz():
    """Health check endpoint"""
    try:
        # Test database connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "service": "api-gateway"}
    except Exception as e:
        logger.error("Health check failed", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/objects")
async def list_objects(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    object_type: Optional[str] = Query(None, description="Filter by object type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results (1-1000)"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, updated_at"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    """List business objects with pagination, filtering, and sorting"""
    try:
        # Validate sort parameters
        validate_sort_order(sort_order)
        allowed_sort_fields = ["created_at", "updated_at"]
        sort_by = validate_sort_field(sort_by, allowed_sort_fields)
        
        # Validate limit and offset
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid limit: {limit}. Must be between 1 and 1000"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid offset: {offset}. Must be >= 0"
            )
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with filters
                query = "SELECT * FROM edna_objects WHERE 1=1"
                params = []
                
                if source_system:
                    if not source_system.strip():
                        raise HTTPException(
                            status_code=400,
                            detail="source_system cannot be empty"
                        )
                    query += " AND source_system = %s"
                    params.append(source_system.strip())
                
                if object_type:
                    if not object_type.strip():
                        raise HTTPException(
                            status_code=400,
                            detail="object_type cannot be empty"
                        )
                    query += " AND object_type = %s"
                    params.append(object_type.strip())
                
                # Add sorting
                order_direction = "ASC" if sort_order.lower() == "asc" else "DESC"
                # Map sort_by to actual column name
                sort_column_map = {
                    "created_at": "created_at",
                    "updated_at": "updated_at"
                }
                sort_column = sort_column_map.get(sort_by, "created_at")
                query += f" ORDER BY {sort_column} {order_direction}"
                
                # Add pagination
                query += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                # Get total count for pagination metadata
                count_query = "SELECT COUNT(*) as total FROM edna_objects WHERE 1=1"
                count_params = []
                
                if source_system:
                    count_query += " AND source_system = %s"
                    count_params.append(source_system.strip())
                
                if object_type:
                    count_query += " AND object_type = %s"
                    count_params.append(object_type.strip())
                
                cur.execute(count_query, count_params)
                total_count = cur.fetchone()["total"]
                
                # Execute main query
                cur.execute(query, params)
                objects = [dict(row) for row in cur.fetchall()]
                
                return {
                    "objects": objects,
                    "count": len(objects),
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + len(objects)) < total_count
                }
    except HTTPException:
        raise
    except psycopg2.Error as e:
        logger.error("Database error listing objects", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Failed to list objects", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/objects/{golden_id}")
async def get_object(golden_id: str):
    """Get a specific business object"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM edna_objects WHERE golden_id = %s", (golden_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Object not found")
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get object", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/objects")
async def create_object(obj: dict):
    """Create or update a business object"""
    try:
        source_system = obj.get("source_system")
        source_id = obj.get("source_id")
        object_type = obj.get("object_type")
        attributes = obj.get("attributes", {})
        
        if not all([source_system, source_id, object_type]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: source_system, source_id, object_type"
            )
        
        # Use identity matcher to compute golden_id and upsert
        golden_id = matcher.match_and_upsert(
            source_system=source_system,
            source_id=source_id,
            object_type=object_type,
            attributes=attributes
        )
        
        return {"golden_id": golden_id, "status": "created_or_updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create object", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
async def list_events(
    golden_id: Optional[str] = Query(None, description="Filter by golden object ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results (1-1000)"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("occurred_at", description="Field to sort by: occurred_at"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    """List events with pagination, filtering, and sorting"""
    try:
        # Validate sort parameters
        validate_sort_order(sort_order)
        allowed_sort_fields = ["occurred_at"]
        sort_by = validate_sort_field(sort_by, allowed_sort_fields)
        
        # Validate limit and offset
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid limit: {limit}. Must be between 1 and 1000"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid offset: {offset}. Must be >= 0"
            )
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with filters
                query = "SELECT * FROM edna_events WHERE 1=1"
                params = []
                
                if golden_id:
                    if not golden_id.strip():
                        raise HTTPException(
                            status_code=400,
                            detail="golden_id cannot be empty"
                        )
                    query += " AND golden_id = %s"
                    params.append(golden_id.strip())
                
                if event_type:
                    if not event_type.strip():
                        raise HTTPException(
                            status_code=400,
                            detail="event_type cannot be empty"
                        )
                    query += " AND event_type = %s"
                    params.append(event_type.strip())
                
                if source_system:
                    if not source_system.strip():
                        raise HTTPException(
                            status_code=400,
                            detail="source_system cannot be empty"
                        )
                    query += " AND source_system = %s"
                    params.append(source_system.strip())
                
                # Add sorting
                order_direction = "ASC" if sort_order.lower() == "asc" else "DESC"
                # Map sort_by to actual column name
                sort_column_map = {
                    "occurred_at": "occurred_at"
                }
                sort_column = sort_column_map.get(sort_by, "occurred_at")
                query += f" ORDER BY {sort_column} {order_direction}"
                
                # Add pagination
                query += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                # Get total count for pagination metadata
                count_query = "SELECT COUNT(*) as total FROM edna_events WHERE 1=1"
                count_params = []
                
                if golden_id:
                    count_query += " AND golden_id = %s"
                    count_params.append(golden_id.strip())
                
                if event_type:
                    count_query += " AND event_type = %s"
                    count_params.append(event_type.strip())
                
                if source_system:
                    count_query += " AND source_system = %s"
                    count_params.append(source_system.strip())
                
                cur.execute(count_query, count_params)
                total_count = cur.fetchone()["total"]
                
                # Execute main query
                cur.execute(query, params)
                events = [dict(row) for row in cur.fetchall()]
                
                return {
                    "events": events,
                    "count": len(events),
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + len(events)) < total_count
                }
    except HTTPException:
        raise
    except psycopg2.Error as e:
        logger.error("Database error listing events", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Failed to list events", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events")
async def create_event(event: dict):
    """Create a new event"""
    try:
        event_type = event.get("event_type")
        source_system = event.get("source_system")
        
        if not event_type or not source_system:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: event_type, source_system"
            )
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edna_events (event_type, golden_id, source_system, payload)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING event_id
                """, (
                    event_type,
                    event.get("golden_id"),
                    source_system,
                    json.dumps(event.get("payload", {}))
                ))
                conn.commit()
                event_id = cur.fetchone()[0]
                
                return {"event_id": event_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create event", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/identity/rules")
async def list_identity_rules(
    object_type: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List identity matching rules"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM edna_identity_rules WHERE 1=1"
                params = []
                
                if active_only:
                    query += " AND active = TRUE"
                
                if object_type:
                    query += " AND object_type = %s"
                    params.append(object_type)
                
                if source_system:
                    query += " AND source_system = %s"
                    params.append(source_system)
                
                query += " ORDER BY created_at DESC"
                
                cur.execute(query, params)
                rules = [dict(row) for row in cur.fetchall()]
                
                return {"rules": rules, "count": len(rules)}
    except Exception as e:
        logger.error("Failed to list identity rules", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/identity/rules")
async def create_identity_rule(rule: dict):
    """Create or update an identity matching rule"""
    try:
        rule_id = rule.get("rule_id")
        if not rule_id:
            raise HTTPException(status_code=400, detail="Missing required field: rule_id")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edna_identity_rules (
                        rule_id, rule_name, object_type, source_system,
                        key_fields, normalization_rules, active
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (rule_id) DO UPDATE SET
                        rule_name = EXCLUDED.rule_name,
                        object_type = EXCLUDED.object_type,
                        source_system = EXCLUDED.source_system,
                        key_fields = EXCLUDED.key_fields,
                        normalization_rules = EXCLUDED.normalization_rules,
                        active = EXCLUDED.active,
                        updated_at = NOW()
                    RETURNING rule_id
                """, (
                    rule_id,
                    rule.get("rule_name"),
                    rule.get("object_type"),
                    rule.get("source_system"),
                    json.dumps(rule.get("key_fields", [])),
                    json.dumps(rule.get("normalization_rules", {})),
                    rule.get("active", True)
                ))
                conn.commit()
                return {"rule_id": cur.fetchone()[0], "status": "created_or_updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create identity rule", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.api_gateway_host,
        port=settings.api_gateway_port,
        log_config=None  # Use our structured logging
    )

