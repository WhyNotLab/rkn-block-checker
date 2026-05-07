from __future__ import annotations

import json
import logging
import socket
import struct
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DOH_ENDPOINTS = [
    "https://cloudflare-dns.com/dns-query",
    "https://freedns.controld.com/dns-query",
    "https://dns.quad9.net/dns-query",
    "https://dns.google/dns-query",
    "https://dns.alidns.com/dns-query",
    "https://dns.nextdns.io",
]
DOH_TIMEOUT = 5.0


def resolve_system(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        logger.debug("system DNS failed for %s: %s", host, e)
        return None


def _parse_dns_wire_a(data: bytes) -> Optional[str]:
    """Извлекает первый A-record из бинарного DNS-ответа (RFC 1035 wire format)."""
    try:
        if len(data) < 12:
            return None
        qdcount = struct.unpack("!H", data[4:6])[0]
        ancount = struct.unpack("!H", data[6:8])[0]
        if ancount == 0:
            return None
        pos = 12
        # пропускаем секцию вопросов
        for _ in range(qdcount):
            while pos < len(data):
                length = data[pos]
                pos += 1
                if length == 0:
                    break
                if length >= 0xC0:   # указатель-сжатие
                    pos += 1
                    break
                pos += length
            pos += 4  # QTYPE + QCLASS
        # читаем секцию ответов
        for _ in range(ancount):
            if pos >= len(data):
                break
            if data[pos] >= 0xC0:    # имя — сжатый указатель
                pos += 2
            else:
                while pos < len(data) and data[pos] != 0:
                    if data[pos] >= 0xC0:
                        pos += 2
                        break
                    pos += data[pos] + 1
                else:
                    pos += 1
            if pos + 10 > len(data):
                break
            rtype, _rclass, _ttl, rdlen = struct.unpack("!HHIH", data[pos:pos + 10])
            pos += 10
            if rtype == 1 and rdlen == 4:   # A record
                return socket.inet_ntoa(data[pos:pos + 4])
            pos += rdlen
    except Exception as exc:
        logger.debug("dns wire parse error: %s", exc)
    return None


def resolve_doh(
    host: str, timeout: float = DOH_TIMEOUT
) -> tuple[Optional[str], Optional[str], Optional[float]]:
    """Возвращает (ip, endpoint, latency_ms) первого сработавшего DoH-сервера."""
    for endpoint in DOH_ENDPOINTS:
        try:
            t0 = time.perf_counter()
            r = requests.get(
                endpoint,
                params={"name": host, "type": "A"},
                headers={"accept": "application/dns-json"},
                timeout=timeout,
            )
            latency_ms = (time.perf_counter() - t0) * 1000
            if not r.ok:
                logger.debug("DoH %s returned %s for %s", endpoint, r.status_code, host)
                continue
            ct = r.headers.get("content-type", "")
            # бинарный wire-format (ControlD и другие)
            if "dns-message" in ct:
                ip = _parse_dns_wire_a(r.content)
                if ip:
                    logger.debug("DoH (wire) resolved %s via %s -> %s (%.0fms)", host, endpoint, ip, latency_ms)
                    return ip, endpoint, latency_ms
                continue
            # JSON-формат (RFC 8484 / google style)
            for ans in r.json().get("Answer", []):
                if ans.get("type") == 1:
                    ip = ans.get("data")
                    logger.debug("DoH (json) resolved %s via %s -> %s (%.0fms)", host, endpoint, ip, latency_ms)
                    return ip, endpoint, latency_ms
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.debug("DoH %s failed for %s: %s", endpoint, host, e)
    return None, None, None
