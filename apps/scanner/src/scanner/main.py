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
        profiles = scanner.scan_all_tables()
        logger.info(f"Scanned {len(profiles)} tables", extra={"table_count": len(profiles)})
        
        for profile in profiles:
            logger.info(
                "Table profile",
                extra={
                    "schema": profile["schema"],
                    "table": profile["table"],
                    "row_count": profile["row_count"],
                    "column_count": profile["column_count"],
                }
            )
        
        # Persist candidates after profiling
        if profiles:
            scanner.persist_candidates(profiles)
            logger.info("✓ Candidate persistence completed")
        
    except Exception as e:
        logger.error("Scanner failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

