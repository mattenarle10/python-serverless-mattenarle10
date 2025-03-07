import logging

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler if not already added
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Ensure all log methods are available
logger.debug = logger.debug
logger.info = logger.info
logger.warning = logger.warning
logger.error = logger.error
logger.critical = logger.critical
