#!/usr/bin/env python3
"""Seed demo data: 10 customers and 25 events"""

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "edna-common" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "identity" / "src"))

from identity.matcher import IdentityMatcher

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


def seed_customers(conn, matcher: IdentityMatcher, count: int = 10) -> list:
    """Seed customer data"""
    logger.info(f"Seeding {count} customers...")
    
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    companies = ["Acme Corp", "Tech Solutions", "Global Industries", "Digital Services", "Innovation Labs"]
    domains = ["example.com", "test.com", "demo.org", "sample.net"]
    
    golden_ids = []
    
    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
        phone = f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        company = random.choice(companies)
        
        attributes = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "company": company,
            "status": random.choice(["active", "inactive", "pending"]),
        }
        
        source_id = f"CUST-{i+1:04d}"
        
        try:
            golden_id = matcher.match_and_upsert(
                source_system="crm",
                source_id=source_id,
                object_type="customer",
                attributes=attributes
            )
            golden_ids.append(golden_id)
            logger.info(f"  Created customer: {first_name} {last_name} ({golden_id[:8]}...)")
        except Exception as e:
            logger.error(f"Failed to create customer {source_id}: {e}")
    
    logger.info(f"✓ Seeded {len(golden_ids)} customers")
    return golden_ids


def seed_events(conn, golden_ids: list, count: int = 25) -> None:
    """Seed event data"""
    logger.info(f"Seeding {count} events...")
    
    event_types = [
        "object.created",
        "object.updated",
        "object.deleted",
        "object.viewed",
        "object.exported",
        "object.shared",
    ]
    
    source_systems = ["crm", "erp", "cms", "analytics"]
    
    with conn.cursor() as cur:
        for i in range(count):
            event_type = random.choice(event_types)
            golden_id = random.choice(golden_ids) if golden_ids else None
            source_system = random.choice(source_systems)
            
            payload = {
                "action": event_type.split(".")[1],
                "timestamp": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
                "user_id": f"user-{random.randint(1, 10)}",
                "metadata": {
                    "ip_address": f"192.168.1.{random.randint(1, 255)}",
                    "user_agent": random.choice([
                        "Mozilla/5.0",
                        "Chrome/120.0",
                        "Safari/17.0",
                    ])
                }
            }
            
            occurred_at = datetime.utcnow() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            cur.execute("""
                INSERT INTO edna_events (event_type, golden_id, source_system, payload, occurred_at)
                VALUES (%s, %s, %s, %s::jsonb, %s)
            """, (event_type, golden_id, source_system, json.dumps(payload), occurred_at))
    
    conn.commit()
    logger.info(f"✓ Seeded {count} events")


def seed_identity_rule(conn) -> None:
    """Seed a sample identity rule for customers"""
    logger.info("Seeding identity rule...")
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO edna_identity_rules (
                rule_id, rule_name, object_type, source_system,
                key_fields, normalization_rules, active
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
            ON CONFLICT (rule_id) DO NOTHING
        """, (
            "rule-customer-001",
            "Customer Email and Phone Match",
            "customer",
            "crm",
            json.dumps(["email", "phone"]),
            json.dumps({
                "email": "lowercase",
                "phone": "digits_only"
            }),
            True
        ))
    
    conn.commit()
    logger.info("✓ Seeded identity rule")


def main():
    """Main entry point"""
    database_url = get_database_url()
    logger.info(f"Connecting to database: {database_url.split('@')[-1] if '@' in database_url else '***'}")
    
    try:
        conn = psycopg2.connect(database_url)
        matcher = IdentityMatcher(database_url)
        
        # Seed identity rule first (needed for customer matching)
        seed_identity_rule(conn)
        
        # Seed customers
        golden_ids = seed_customers(conn, matcher, count=10)
        
        # Seed events
        seed_events(conn, golden_ids, count=25)
        
        conn.close()
        logger.info("✓ Demo data seeding completed")
        
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

