"""Semantic service main entry point"""

import sys
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "edna-common" / "src"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
import json

import logging
from edna_common.config import get_settings
from edna_common.logging import setup_logging

setup_logging("semantic")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Semantic Glossary Service",
    version="0.1.0",
    description="Service for managing terms, KPIs, and glossary definitions"
)


# Pydantic models for request/response
class TermCreate(BaseModel):
    """Model for creating a term"""
    term_id: str = Field(..., description="Unique identifier for the term")
    term_name: str = Field(..., description="Name of the term")
    definition: str = Field(..., description="Definition of the term")
    object_type: Optional[str] = Field(None, description="Optional link to object type")
    category: Optional[str] = Field(None, description="Category of the term")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "term_id": "term-customer-001",
                "term_name": "Customer Lifetime Value",
                "definition": "The total revenue a business can expect from a customer relationship",
                "object_type": "customer",
                "category": "business_metric",
                "metadata": {"source": "internal", "version": "1.0"}
            }
        }


class TermUpdate(BaseModel):
    """Model for updating a term"""
    term_name: Optional[str] = None
    definition: Optional[str] = None
    object_type: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[dict] = None


class KPICreate(BaseModel):
    """Model for creating a KPI"""
    kpi_id: str = Field(..., description="Unique identifier for the KPI")
    kpi_name: str = Field(..., description="Name of the KPI")
    definition: str = Field(..., description="Definition of the KPI")
    metric_type: Optional[str] = Field(None, description="Type of metric (e.g., count, sum, average)")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    object_type: Optional[str] = Field(None, description="Optional link to object type")
    calculation_formula: Optional[str] = Field(None, description="Formula for calculating the KPI")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "kpi_id": "kpi-customer-001",
                "kpi_name": "Active Customers",
                "definition": "Number of customers with active status",
                "metric_type": "count",
                "unit": "customers",
                "object_type": "customer",
                "calculation_formula": "COUNT(*) WHERE status = 'active'",
                "metadata": {"threshold": 1000, "target": 5000}
            }
        }


class KPIUpdate(BaseModel):
    """Model for updating a KPI"""
    kpi_name: Optional[str] = None
    definition: Optional[str] = None
    metric_type: Optional[str] = None
    unit: Optional[str] = None
    object_type: Optional[str] = None
    calculation_formula: Optional[str] = None
    metadata: Optional[dict] = None


def get_connection():
    """Get database connection"""
    return psycopg2.connect(settings.database_url)


@app.get("/healthz")
async def healthz():
    """Health check endpoint"""
    return {"status": "ok", "service": "semantic"}


@app.get("/glossary")
async def list_glossary_terms():
    """List all glossary terms"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT term, definition, category, metadata
                    FROM edna_glossary
                    ORDER BY term
                """)
                terms = [dict(row) for row in cur.fetchall()]
                return {"terms": terms}
    except psycopg2.OperationalError as e:
        logger.error("Database connection failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as e:
        logger.error("Failed to list glossary terms", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/glossary")
async def create_glossary_term(term: dict):
    """Create a new glossary term"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edna_glossary (term, definition, category, metadata)
                    VALUES (%s, %s, %s, %s::jsonb)
                    ON CONFLICT (term) DO UPDATE SET
                        definition = EXCLUDED.definition,
                        category = EXCLUDED.category,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING term
                """, (
                    term.get("term"),
                    term.get("definition"),
                    term.get("category"),
                    json.dumps(term.get("metadata", {}))
                ))
                conn.commit()
                return {"term": cur.fetchone()[0]}
    except Exception as e:
        logger.error("Failed to create glossary term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/glossary/{term}")
async def get_glossary_term(term: str):
    """Get a specific glossary term"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT term, definition, category, metadata
                    FROM edna_glossary
                    WHERE term = %s
                """, (term,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Term not found")
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get glossary term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/glossary/{term}")
async def delete_glossary_term(term: str):
    """Delete a glossary term"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM edna_glossary WHERE term = %s", (term,))
                conn.commit()
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Term not found")
                return {"status": "deleted", "term": term}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete glossary term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Terms CRUD endpoints
@app.get("/terms", response_model=dict)
async def list_terms(
    object_type: Optional[str] = Query(None, description="Filter by object type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all terms with optional filtering and pagination.
    
    Returns a list of terms with optional filtering by object_type or category.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM edna_terms WHERE 1=1"
                params = []
                
                if object_type:
                    query += " AND object_type = %s"
                    params.append(object_type)
                
                if category:
                    query += " AND category = %s"
                    params.append(category)
                
                # Get total count
                count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                
                # Add pagination and sorting
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                terms = [dict(row) for row in cur.fetchall()]
                
                return {
                    "terms": terms,
                    "count": len(terms),
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
    except Exception as e:
        logger.error("Failed to list terms", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/terms/{term_id}", response_model=dict)
async def get_term(term_id: str):
    """
    Get a specific term by ID.
    
    Returns the term details including definition, object_type link, and metadata.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM edna_terms WHERE term_id = %s", (term_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Term not found")
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/terms", response_model=dict, status_code=201)
async def create_term(term: TermCreate):
    """
    Create a new term.
    
    Creates a term with optional link to object_type. The term_id must be unique.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO edna_terms (
                        term_id, term_name, definition, object_type, category, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING *
                """, (
                    term.term_id,
                    term.term_name,
                    term.definition,
                    term.object_type,
                    term.category,
                    json.dumps(term.metadata)
                ))
                conn.commit()
                result = cur.fetchone()
                return dict(result)
    except psycopg2.IntegrityError as e:
        logger.error("Failed to create term (duplicate)", exc_info=True)
        raise HTTPException(status_code=409, detail="Term with this ID already exists")
    except Exception as e:
        logger.error("Failed to create term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/terms/{term_id}", response_model=dict)
async def update_term(term_id: str, term_update: TermUpdate):
    """
    Update an existing term.
    
    Updates specified fields of a term. Only provided fields will be updated.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build update query dynamically
                updates = []
                params = []
                
                if term_update.term_name is not None:
                    updates.append("term_name = %s")
                    params.append(term_update.term_name)
                
                if term_update.definition is not None:
                    updates.append("definition = %s")
                    params.append(term_update.definition)
                
                if term_update.object_type is not None:
                    updates.append("object_type = %s")
                    params.append(term_update.object_type)
                
                if term_update.category is not None:
                    updates.append("category = %s")
                    params.append(term_update.category)
                
                if term_update.metadata is not None:
                    updates.append("metadata = %s::jsonb")
                    params.append(json.dumps(term_update.metadata))
                
                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")
                
                updates.append("updated_at = NOW()")
                params.append(term_id)
                
                query = f"""
                    UPDATE edna_terms
                    SET {', '.join(updates)}
                    WHERE term_id = %s
                    RETURNING *
                """
                
                cur.execute(query, params)
                conn.commit()
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Term not found")
                
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/terms/{term_id}", response_model=dict)
async def delete_term(term_id: str):
    """
    Delete a term by ID.
    
    Permanently deletes the term from the database.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM edna_terms WHERE term_id = %s", (term_id,))
                conn.commit()
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Term not found")
                return {"status": "deleted", "term_id": term_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete term", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# KPIs CRUD endpoints
@app.get("/kpis", response_model=dict)
async def list_kpis(
    object_type: Optional[str] = Query(None, description="Filter by object type"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all KPIs with optional filtering and pagination.
    
    Returns a list of KPIs with optional filtering by object_type or metric_type.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM edna_kpis WHERE 1=1"
                params = []
                
                if object_type:
                    query += " AND object_type = %s"
                    params.append(object_type)
                
                if metric_type:
                    query += " AND metric_type = %s"
                    params.append(metric_type)
                
                # Get total count
                count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                
                # Add pagination and sorting
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                kpis = [dict(row) for row in cur.fetchall()]
                
                return {
                    "kpis": kpis,
                    "count": len(kpis),
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
    except Exception as e:
        logger.error("Failed to list KPIs", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kpis/{kpi_id}", response_model=dict)
async def get_kpi(kpi_id: str):
    """
    Get a specific KPI by ID.
    
    Returns the KPI details including definition, calculation formula, and object_type link.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM edna_kpis WHERE kpi_id = %s", (kpi_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="KPI not found")
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get KPI", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kpis", response_model=dict, status_code=201)
async def create_kpi(kpi: KPICreate):
    """
    Create a new KPI.
    
    Creates a KPI with optional link to object_type. The kpi_id must be unique.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO edna_kpis (
                        kpi_id, kpi_name, definition, metric_type, unit,
                        object_type, calculation_formula, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING *
                """, (
                    kpi.kpi_id,
                    kpi.kpi_name,
                    kpi.definition,
                    kpi.metric_type,
                    kpi.unit,
                    kpi.object_type,
                    kpi.calculation_formula,
                    json.dumps(kpi.metadata)
                ))
                conn.commit()
                result = cur.fetchone()
                return dict(result)
    except psycopg2.IntegrityError as e:
        logger.error("Failed to create KPI (duplicate)", exc_info=True)
        raise HTTPException(status_code=409, detail="KPI with this ID already exists")
    except Exception as e:
        logger.error("Failed to create KPI", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/kpis/{kpi_id}", response_model=dict)
async def update_kpi(kpi_id: str, kpi_update: KPIUpdate):
    """
    Update an existing KPI.
    
    Updates specified fields of a KPI. Only provided fields will be updated.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build update query dynamically
                updates = []
                params = []
                
                if kpi_update.kpi_name is not None:
                    updates.append("kpi_name = %s")
                    params.append(kpi_update.kpi_name)
                
                if kpi_update.definition is not None:
                    updates.append("definition = %s")
                    params.append(kpi_update.definition)
                
                if kpi_update.metric_type is not None:
                    updates.append("metric_type = %s")
                    params.append(kpi_update.metric_type)
                
                if kpi_update.unit is not None:
                    updates.append("unit = %s")
                    params.append(kpi_update.unit)
                
                if kpi_update.object_type is not None:
                    updates.append("object_type = %s")
                    params.append(kpi_update.object_type)
                
                if kpi_update.calculation_formula is not None:
                    updates.append("calculation_formula = %s")
                    params.append(kpi_update.calculation_formula)
                
                if kpi_update.metadata is not None:
                    updates.append("metadata = %s::jsonb")
                    params.append(json.dumps(kpi_update.metadata))
                
                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")
                
                updates.append("updated_at = NOW()")
                params.append(kpi_id)
                
                query = f"""
                    UPDATE edna_kpis
                    SET {', '.join(updates)}
                    WHERE kpi_id = %s
                    RETURNING *
                """
                
                cur.execute(query, params)
                conn.commit()
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="KPI not found")
                
                return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update KPI", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/kpis/{kpi_id}", response_model=dict)
async def delete_kpi(kpi_id: str):
    """
    Delete a KPI by ID.
    
    Permanently deletes the KPI from the database.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM edna_kpis WHERE kpi_id = %s", (kpi_id,))
                conn.commit()
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="KPI not found")
                return {"status": "deleted", "kpi_id": kpi_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete KPI", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.api_gateway_host,
        port=8002,
        log_config=None  # Use our structured logging
    )

