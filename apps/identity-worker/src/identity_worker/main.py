"""Identity worker main entry point"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "edna-common" / "src"))

import logging
from edna_common.config import get_settings
from edna_common.logging import setup_logging
from identity_worker.worker import IdentityWorker

setup_logging("identity-worker")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for identity worker"""
    parser = argparse.ArgumentParser(description="Identity Worker - Process customer data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (don't write to database)"
    )
    parser.add_argument(
        "--source-system",
        default="demo",
        help="Source system identifier (default: demo)"
    )
    
    args = parser.parse_args()
    
    settings = get_settings()
    logger.info(
        "Starting identity worker",
        extra={
            "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "***",
            "dry_run": args.dry_run,
            "source_system": args.source_system
        }
    )
    
    worker = IdentityWorker(settings.database_url, dry_run=args.dry_run)
    
    try:
        stats = worker.process_customers(source_system=args.source_system)
        
        logger.info(
            "Identity worker completed",
            extra={
                "stats": stats,
                "dry_run": args.dry_run
            }
        )
        
        if stats["errors"] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error("Identity worker failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

