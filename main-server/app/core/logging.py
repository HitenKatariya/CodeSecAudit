"""Structured logging with secret redaction and Redis Streams publishing for main-server."""

import logging
import re
from datetime import datetime, timezone
import redis

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)bearer\s+([A-Za-z0-9_\-\.]{16,})"),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(r"\1: [REDACTED]", redacted)
    return redacted


class RedisStreamHandler(logging.Handler):
    def __init__(self, redis_url: str, stream_key: str = "log:main-server", maxlen: int = 10000):
        super().__init__()
        self.stream_key = stream_key
        self.maxlen = maxlen
        try:
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        except Exception:
            self.client = None

    def emit(self, record: logging.LogRecord) -> None:
        if not self.client:
            return
        try:
            msg = self.format(record)
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "message": redact_secrets(msg),
                "logger": record.name,
                "service": "main-server",
            }
            self.client.xadd(self.stream_key, payload, maxlen=self.maxlen, approximate=True)
        except Exception:
            pass


def setup_logger(redis_url: str, log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("main_server")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    console = logging.StreamHandler()
    formatter = logging.Formatter('{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}')
    console.setFormatter(formatter)
    logger.addHandler(console)

    if redis_url:
        stream_handler = RedisStreamHandler(redis_url)
        logger.addHandler(stream_handler)

    return logger
