from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from .targets import STUB_MARKERS

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0
DEFAULT_USER_AGENT = "Mozilla/5.0 (RKN-Checker)"
BODY_SNIPPET_LEN = 2000


@dataclass
class HttpProbe:
    status_code: Optional[int] = None
    elapsed_ms: Optional[float] = None
    body_snippet: str = ""
    body_raw: str = ""
    error: Optional[str] = None
    timed_out: bool = False


def fetch(url: str, timeout: float = DEFAULT_TIMEOUT) -> HttpProbe:
    try:
        r = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        body = r.text[:BODY_SNIPPET_LEN]
        return HttpProbe(
            status_code=r.status_code,
            elapsed_ms=r.elapsed.total_seconds() * 1000,
            body_snippet=body.lower(),
            body_raw=body,
        )
    except requests.exceptions.Timeout:
        return HttpProbe(error="timeout", timed_out=True)
    except requests.exceptions.RequestException as e:
        return HttpProbe(error=f"{type(e).__name__}: {e}")


def looks_like_stub(body_snippet: str) -> bool:
    return any(marker in body_snippet for marker in STUB_MARKERS)
