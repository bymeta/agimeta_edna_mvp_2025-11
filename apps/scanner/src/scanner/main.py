"""Scanner service main entry point"""

import sys
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "edna-common" / "src"))

import logging
from edna_common.config import get_settings
from edna_common.logging import setup_logging
from scanner.scanner import Scanner

setup_logging("scanner")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for scanner service"""
    settings = get_settings()
    logger.info("Starting scanner service", extra={"database_url": settings.database_url})

    scanner = Scanner(settings.database_url)
    
    # Run as a job
    try:
        # Scan all configured source databases
        results = scanner.scan_source_databases()
        
        logger.info(
            "Scanner completed",
            extra={
                "scanned_databases": results.get("scanned_databases", 0),
                "failed_databases": results.get("failed_databases", 0),
                "total_tables": results.get("total_tables", 0),
                "status": results.get("status", "unknown")
            }
        )
        
        # Log per-database results
        for db_result in results.get("database_results", []):
            logger.info(
                f"Database scan result: {db_result.get('source_db_name')}",
                extra=db_result
            )
        
        if results.get("failed_databases", 0) > 0:
            logger.warning(f"Some databases failed to scan: {results.get('failed_databases')}")
        
    except Exception as e:
        logger.error("Scanner failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

