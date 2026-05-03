"""
Structured logging configuration.

Logs are emitted as JSON in non-development environments. We never log secrets,
passwords, full JWTs, Stripe API keys, or full PII. The redactor below scrubs
common offenders.
"""
import logging
import re
import sys
from typing import Any, Dict

import structlog

from app.core.config import get_settings

settings = get_settings()

_SECRET_PATTERNS = [
    re.compile(r"(password\"?\s*[:=]\s*\")[^\"]+(\")", re.I),
    re.compile(r"(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+", re.I),
    re.compile(r"(sk_(?:test|live)_)[A-Za-z0-9]+", re.I),
    re.compile(r"(eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.)[A-Za-z0-9_\-]+"),  # JWT-ish
]


def _redact(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(event_dict.items()):
        if isinstance(v, str):
            for pat in _SECRET_PATTERNS:
                v = pat.sub(lambda m: m.group(1) + "***REDACTED***", v)
            event_dict[k] = v
    return event_dict


def configure_logging() -> None:
    level = logging.DEBUG if settings.APP_DEBUG else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact,
    ]
    if settings.APP_ENV == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=processors,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "dynametrix"):
    return structlog.get_logger(name)
