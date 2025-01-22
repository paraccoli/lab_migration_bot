import logging

logging.basicConfig(
    filename="logs.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_event(event, level="INFO"):
    if level == "INFO":
        logging.info(event)
    elif level == "WARNING":
        logging.warning(event)
    elif level == "ERROR":
        logging.error(event)
    elif level == "CRITICAL":
        logging.critical(event)