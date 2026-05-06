from __future__ import annotations

import logging
import socket
import ssl
import time
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 5.0


def check_tcp(
    host: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bool, Optional[float], Optional[str]]:
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, (time.monotonic() - start) * 1000, None
    except socket.timeout:
        return False, None, "timeout"
    except ConnectionResetError:
        return False, None, "connection reset"
    except OSError as e:
        return False, None, f"{type(e).__name__}: {e}"


def check_tls(
    host: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bool, Optional[float], Optional[str], Optional[str]]:
    ctx = ssl.create_default_context()
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cn = _extract_cn(ssock.getpeercert())
                return True, (time.monotonic() - start) * 1000, cn, None
    except socket.timeout:
        return False, None, None, "timeout"
    except ssl.SSLError as e:
        return False, None, None, f"SSLError: {e.reason or e}"
    except ConnectionAbortedError:
        return False, None, None, "connection reset during TLS"
    except ConnectionResetError:
        return False, None, None, "connection reset during TLS"
    except OSError as e:
        return False, None, None, f"{type(e).__name__}: {e}"


def _extract_cn(cert: Optional[dict]) -> Optional[str]:
    if not cert:
        return None
    for tup in cert.get("subject", ()):
        for k, v in tup:
            if k == "commonName":
                return v
    return None
