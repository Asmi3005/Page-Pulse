import logging
import sys
from contextvars import ContextVar

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
        root.setLevel(level)

    return logging.getLogger("page_pulse")


logger = setup_logging()
