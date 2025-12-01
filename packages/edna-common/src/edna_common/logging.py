"""Structured logging setup"""

import logging
import sys
from typing import Optional
from edna_common.config import get_settings


def setup_logging(service_name: str, log_level: Optional[str] = None) -> None:
    """Configure structured logging for a service"""
    settings = get_settings()
    level = log_level or settings.log_level

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter based on format preference
    if settings.log_format == "json":
        import json
        from datetime import datetime

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "service": service_name,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)

        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

