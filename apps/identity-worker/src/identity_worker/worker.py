"""Identity worker for processing customer data"""

import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class IdentityWorker:
    """Worker that processes source data and creates golden objects"""

    def __init__(self, database_url: str, dry_run: bool = False):
        self.database_url = database_url
        self.dry_run = dry_run

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

    def get_identity_rules(self, object_type: str = "customer") -> List[Dict[str, Any]]:
        """Get active identity rules for a given object type"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT rule_id, rule_name, object_type, source_system,
                           key_fields, normalization_rules, active
                    FROM edna_identity_rules
                    WHERE object_type = %s AND active = TRUE
                    ORDER BY rule_id
                """, (object_type,))
                rules = [dict(row) for row in cur.fetchall()]
                logger.info(f"Found {len(rules)} active identity rule(s) for object_type={object_type}")
                return rules

    def ensure_demo_source_table(self) -> None:
        """Ensure demo_customers table exists, create if missing"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'demo_customers'
                    )
                """)
                exists = cur.fetchone()[0]
                
                if not exists:
                    logger.info("Creating demo_customers table...")
                    cur.execute("""
                        CREATE TABLE demo_customers (
                            customer_id VARCHAR(255) PRIMARY KEY,
                            email VARCHAR(255),
                            phone VARCHAR(50),
                            first_name VARCHAR(100),
                            last_name VARCHAR(100),
                            company VARCHAR(255),
                            status VARCHAR(50),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """)
                    
                    # Insert sample data
                    sample_data = [
                        ('CUST-001', 'alice.smith@example.com', '555-123-4567', 'Alice', 'Smith', 'Acme Corp', 'active'),
                        ('CUST-002', 'bob.johnson@test.com', '555-234-5678', 'Bob', 'Johnson', 'Tech Solutions', 'active'),
                        ('CUST-003', 'charlie.williams@demo.org', '555-345-6789', 'Charlie', 'Williams', 'Global Industries', 'inactive'),
                        ('CUST-004', 'diana.brown@sample.net', '555-456-7890', 'Diana', 'Brown', 'Digital Services', 'active'),
                        ('CUST-005', 'eve.jones@example.com', '555-567-8901', 'Eve', 'Jones', 'Innovation Labs', 'pending'),
                    ]
                    
                    cur.executemany("""
                        INSERT INTO demo_customers 
                        (customer_id, email, phone, first_name, last_name, company, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, sample_data)
                    
                    conn.commit()
                    logger.info("✓ Created demo_customers table with sample data")
                else:
                    logger.info("demo_customers table already exists")

    def query_source_data(self, source_table: str = "demo_customers") -> List[Dict[str, Any]]:
        """Query source data from demo table"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM {source_table}')
                rows = [dict(row) for row in cur.fetchall()]
                logger.info(f"Queried {len(rows)} rows from {source_table}")
                return rows

    def normalize_value(self, value: Any, rule: str) -> str:
        """Normalize a value according to a rule"""
        if value is None:
            return ""
        
        value_str = str(value).strip()
        
        if rule == "lowercase":
            return value_str.lower()
        elif rule == "uppercase":
            return value_str.upper()
        elif rule == "digits_only":
            return "".join(c for c in value_str if c.isdigit())
        elif rule == "alphanumeric_only":
            return "".join(c for c in value_str if c.isalnum())
        elif rule == "trim":
            return value_str.strip()
        else:
            return value_str

    def compute_golden_id(
        self,
        source_data: Dict[str, Any],
        key_fields: List[str],
        normalization_rules: Dict[str, str]
    ) -> str:
        """Compute deterministic golden ID from normalized keys"""
        import hashlib
        
        # Extract and normalize key values
        key_values = []
        for field in key_fields:
            value = source_data.get(field)
            norm_rule = normalization_rules.get(field, "trim")
            normalized = self.normalize_value(value, norm_rule)
            key_values.append(f"{field}:{normalized}")

        # Concatenate and hash
        key_string = "|".join(sorted(key_values))
        return hashlib.sha1(key_string.encode("utf-8")).hexdigest()

    def process_customers(self, source_system: str = "demo") -> Dict[str, Any]:
        """Process customer data from demo source table"""
        logger.info(f"Starting identity worker (dry_run={self.dry_run})")
        
        # Ensure demo table exists
        self.ensure_demo_source_table()
        
        # Get identity rules
        rules = self.get_identity_rules(object_type="customer")
        
        if not rules:
            logger.warning("No active identity rules found for object_type='customer'")
            logger.info("Creating default rule...")
            self._create_default_rule()
            rules = self.get_identity_rules(object_type="customer")
        
        if not rules:
            logger.error("Failed to get identity rules")
            return {"processed": 0, "created": 0, "updated": 0, "errors": 0}
        
        # Use first rule
        rule = rules[0]
        logger.info(f"Using rule: {rule['rule_id']} - {rule['rule_name']}")
        
        # Get key fields and normalization rules
        key_fields = rule["key_fields"]
        if not isinstance(key_fields, list):
            key_fields = list(key_fields) if key_fields else []
        
        normalization_rules = rule.get("normalization_rules", {})
        if not isinstance(normalization_rules, dict):
            normalization_rules = {}
        
        logger.info(f"Key fields: {key_fields}")
        logger.info(f"Normalization rules: {normalization_rules}")
        
        # Query source data
        source_rows = self.query_source_data()
        
        if not source_rows:
            logger.warning("No source data found")
            return {"processed": 0, "created": 0, "updated": 0, "errors": 0}
        
        # Process each row
        stats = {"processed": 0, "created": 0, "updated": 0, "errors": 0}
        
        with self.get_connection() as conn:
            for row in source_rows:
                try:
                    stats["processed"] += 1
                    
                    # Extract source_id (assuming customer_id field exists)
                    source_id = row.get("customer_id") or f"DEMO-{stats['processed']}"
                    
                    # Prepare attributes (all fields except key fields used for matching)
                    attributes = {k: v for k, v in row.items() if k not in key_fields}
                    # Also include key fields in attributes for reference
                    for key_field in key_fields:
                        if key_field in row:
                            attributes[key_field] = row[key_field]
                    
                    # Compute golden_id
                    golden_id = self.compute_golden_id(row, key_fields, normalization_rules)
                    
                    logger.info(
                        f"Processing: source_id={source_id}, golden_id={golden_id[:8]}...",
                        extra={
                            "source_id": source_id,
                            "golden_id": golden_id,
                            "object_type": "customer"
                        }
                    )
                    
                    if not self.dry_run:
                        # Upsert into edna_objects
                        with conn.cursor() as cur:
                            # Check if exists
                            cur.execute("""
                                SELECT golden_id FROM edna_objects
                                WHERE source_system = %s AND source_id = %s AND object_type = %s
                            """, (source_system, source_id, "customer"))
                            existing = cur.fetchone()
                            
                            if existing:
                                # Update
                                cur.execute("""
                                    UPDATE edna_objects
                                    SET attributes = %s::jsonb,
                                        golden_id = %s,
                                        updated_at = NOW()
                                    WHERE source_system = %s AND source_id = %s AND object_type = %s
                                """, (
                                    json.dumps(attributes),
                                    golden_id,
                                    source_system,
                                    source_id,
                                    "customer"
                                ))
                                stats["updated"] += 1
                                logger.info(f"  ✓ Updated object: {source_id}")
                            else:
                                # Insert
                                cur.execute("""
                                    INSERT INTO edna_objects (
                                        golden_id, source_system, source_id, object_type, attributes
                                    ) VALUES (%s, %s, %s, %s, %s::jsonb)
                                """, (
                                    golden_id,
                                    source_system,
                                    source_id,
                                    "customer",
                                    json.dumps(attributes)
                                ))
                                stats["created"] += 1
                                logger.info(f"  ✓ Created object: {source_id}")
                            
                            conn.commit()
                    else:
                        # Dry run - just log what would be done
                        logger.info(f"  [DRY RUN] Would upsert: source_id={source_id}, golden_id={golden_id[:8]}...")
                        stats["created"] += 1  # Count as would-create in dry run
                        
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"Error processing row: {e}",
                        exc_info=True,
                        extra={"source_id": row.get("customer_id", "unknown")}
                    )
        
        logger.info(
            f"✓ Processing complete: processed={stats['processed']}, "
            f"created={stats['created']}, updated={stats['updated']}, errors={stats['errors']}"
        )
        
        return stats

    def _create_default_rule(self) -> None:
        """Create a default identity rule for customers"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edna_identity_rules (
                        rule_id, rule_name, object_type, source_system,
                        key_fields, normalization_rules, active
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (rule_id) DO NOTHING
                """, (
                    "rule-customer-default",
                    "Default Customer Email and Phone Match",
                    "customer",
                    "demo",
                    json.dumps(["email", "phone"]),
                    json.dumps({
                        "email": "lowercase",
                        "phone": "digits_only"
                    }),
                    True
                ))
                conn.commit()
                logger.info("✓ Created default identity rule")

