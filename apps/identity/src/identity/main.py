"""Identity service main entry point"""

import sys
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages" / "edna-common" / "src"))

import logging
from edna_common.config import get_settings
from edna_common.logging import setup_logging
from identity.matcher import IdentityMatcher

setup_logging("identity")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for identity service (can be used as CLI or library)"""
    settings = get_settings()
    logger.info("Identity service initialized", extra={"database_url": settings.database_url})
    
    # This service is primarily used as a library by other services
    # But can be run standalone for testing
    matcher = IdentityMatcher(settings.database_url)
    rules = matcher.get_active_rules()
    logger.info(f"Loaded {len(rules)} active rules")


if __name__ == "__main__":
    main()

