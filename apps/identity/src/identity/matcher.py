"""Rule-based deterministic matching"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class IdentityMatcher:
    """Deterministic matching using rules"""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

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

    def get_active_rules(
        self,
        object_type: Optional[str] = None,
        source_system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active matching rules"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT rule_id, rule_name, object_type, source_system,
                           key_fields, normalization_rules
                    FROM edna_identity_rules
                    WHERE active = TRUE
                """
                params = []
                
                if object_type:
                    query += " AND object_type = %s"
                    params.append(object_type)
                
                if source_system:
                    query += " AND source_system = %s"
                    params.append(source_system)
                
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def match_and_upsert(
        self,
        source_system: str,
        source_id: str,
        object_type: str,
        attributes: Dict[str, Any]
    ) -> str:
        """Match using rules and upsert into edna_objects"""
        # Get matching rule
        rules = self.get_active_rules(object_type=object_type, source_system=source_system)
        
        if not rules:
            logger.warning(
                f"No active rule found for object_type={object_type}, source_system={source_system}"
            )
            # Fallback: use source_id as key
            key_string = f"{source_system}|{source_id}|{object_type}"
            golden_id = hashlib.sha1(key_string.encode("utf-8")).hexdigest()
        else:
            # Use first matching rule
            rule = rules[0]
            # Handle JSONB fields (may be dict or list)
            key_fields = rule["key_fields"]
            if isinstance(key_fields, dict):
                key_fields = list(key_fields.values()) if key_fields else []
            elif not isinstance(key_fields, list):
                key_fields = [key_fields] if key_fields else []
            
            normalization_rules = rule.get("normalization_rules", {})
            if isinstance(normalization_rules, str):
                import json
                normalization_rules = json.loads(normalization_rules) if normalization_rules else {}
            
            # Merge attributes with source identifiers for matching
            match_data = {
                **attributes,
                "source_system": source_system,
                "source_id": source_id,
            }
            
            golden_id = self.compute_golden_id(match_data, key_fields, normalization_rules)

        # Upsert into edna_objects
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edna_objects (
                        golden_id, source_system, source_id, object_type, attributes
                    ) VALUES (%s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (source_system, source_id, object_type)
                    DO UPDATE SET
                        attributes = EXCLUDED.attributes,
                        updated_at = NOW()
                    RETURNING golden_id
                """, (golden_id, source_system, source_id, object_type, json.dumps(attributes)))
                
                result = cur.fetchone()
                conn.commit()
                
                logger.info(
                    f"Upserted object: golden_id={golden_id}, source={source_system}:{source_id}"
                )
                
                return result[0] if result else golden_id

