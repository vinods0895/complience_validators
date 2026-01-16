import logging
import os

def setup_logger(name: str, log_file: str, level=logging.INFO):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger
