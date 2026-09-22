from __future__ import annotations
import logging

class RunContextFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record,"run_id"): record.run_id="-"
        return True

def get_logger(name="forge"):
    logger=logging.getLogger(name)
    if not logger.handlers:
        handler=logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | run=%(run_id)s | %(message)s",datefmt="%H:%M:%S"))
        handler.addFilter(RunContextFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate=False
    return logger
