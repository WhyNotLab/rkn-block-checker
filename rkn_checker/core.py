from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator
from urllib.parse import urlparse

import requests

from . import dns as dns_mod
from . import http as http_mod
from . import network
from .models import CheckResult, Verdict

logger = logging.getLogger(__name__)

DEFAULT_WORKERS = 10


def get_self_info(timeout: float = 5.0) -> dict:
    try:
        r = requests.get("https://ipinfo.io/json", timeout=timeout)
        if r.ok:
            return r.json()
    except requests.RequestException as e:
        logger.debug("self-info lookup failed: %s", e)
    return {}


def check_url(name: str, url: str, timeout: float = 5.0) -> CheckResult:
    host = urlparse(url).hostname or url
    res = CheckResult(name=name, url=url)

    res.sys_ip = dns_mod.resolve_system(host)
    res.doh_ip = dns_mod.resolve_doh(host, timeout=timeout)

    if res.sys_ip is None and res.doh_ip is not None:
        res.verdict = Verdict.DNS_BLOCK
        res.dns_error = "system resolver failed, DoH succeeded"
        res.notes.append("system DNS doesn't resolve, DoH does — DNS poisoning")
        return res

    if res.sys_ip is None and res.doh_ip is None:
        res.verdict = Verdict.DOWN
        res.dns_error = "domain not resolved anywhere"
        res.notes.append("domain doesn't resolve via system DNS or DoH")
        return res

    if res.sys_ip and res.doh_ip and res.sys_ip != res.doh_ip:
        res.dns_mismatch = True
        res.notes.append(f"DNS mismatch: sys={res.sys_ip} vs doh={res.doh_ip}")

    res.tcp_ok, res.tcp_time_ms, res.tcp_error = network.check_tcp(
        host, timeout=timeout
    )
    if not res.tcp_ok:
        if res.tcp_error == "timeout":
            res.verdict = Verdict.TIMEOUT
            res.notes.append("TCP timeout — port 443 unreachable")
        elif "reset" in (res.tcp_error or ""):
            res.verdict = Verdict.TCP_RESET
            res.notes.append("TCP RST — IP-level block")
        else:
            res.verdict = Verdict.DOWN
            res.notes.append(f"TCP failed: {res.tcp_error}")
        return res

    (
        res.tls_ok,
        res.tls_time_ms,
        res.tls_cert_cn,
        res.tls_error,
    ) = network.check_tls(host, timeout=timeout)
    if not res.tls_ok:
        err = (res.tls_error or "").lower()
        if "reset" in err:
            res.verdict = Verdict.TLS_BLOCK
            res.notes.append("TLS reset — DPI cutting on SNI (typical RKN/TSPU)")
        elif "timeout" in err:
            res.verdict = Verdict.TLS_BLOCK
            res.notes.append("TLS timeout — silent drop after ClientHello")
        else:
            res.verdict = Verdict.TLS_BLOCK
            res.notes.append(f"TLS error: {res.tls_error}")
        return res

    probe = http_mod.fetch(url, timeout=timeout)
    res.status_code = probe.status_code
    res.plt_ms = probe.elapsed_ms
    res.http_error = probe.error

    if probe.timed_out:
        res.verdict = Verdict.TIMEOUT
        return res
    if probe.error:
        res.verdict = Verdict.DOWN
        return res

    if res.status_code == 451:
        res.verdict = Verdict.HTTP_STUB
        res.notes.append("HTTP 451 — Unavailable For Legal Reasons")
        return res

    if http_mod.looks_like_stub(probe.body_snippet):
        res.verdict = Verdict.HTTP_STUB
        res.notes.append("response body matches an ISP stub-page marker")
        return res

    res.verdict = Verdict.OK
    return res


def iter_check_urls(
    urls: dict[str, str],
    max_workers: int = DEFAULT_WORKERS,
    timeout: float = 5.0,
) -> Iterator[CheckResult]:
    """Yield CheckResult objects as soon as each probe finishes.

    Order is *not* the input order — it's the completion order. Callers that
    need the original order should sort by name (or look it up) after
    consuming the iterator. Callers that just want to print results live as
    they arrive can iterate directly.
    """
    if not urls:
        return
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(check_url, name, url, timeout) for name, url in urls.items()
        ]
        for fut in as_completed(futures):
            yield fut.result()


def check_urls_parallel(
    urls: dict[str, str],
    max_workers: int = DEFAULT_WORKERS,
    timeout: float = 5.0,
) -> list[CheckResult]:
    """Run all probes in parallel and return results in the original input order.

    Backwards-compatible wrapper around iter_check_urls — used by the JSON
    output path where streaming gives no benefit (the document has to be
    emitted as a whole anyway).
    """
    name_order = list(urls.keys())
    by_name = {
        r.name: r
        for r in iter_check_urls(urls, max_workers=max_workers, timeout=timeout)
    }
    return [by_name[name] for name in name_order if name in by_name]
