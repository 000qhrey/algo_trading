import logging, sys
from pathlib import Path

def setup_logger(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("algo_trading")
    if logger.handlers:                     # ← guards against duplicates
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(Path("algo_trading.log"))
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.propagate = False
    return logger
