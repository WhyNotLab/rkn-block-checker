from unittest.mock import patch

from rkn_checker.core import check_url
from rkn_checker.http import HttpProbe
from rkn_checker.models import Confidence, Verdict


def _patches(
    *,
    sys_ip="1.2.3.4",
    doh_ip="1.2.3.4",
    tcp=(True, 10.0, None),
    tls=(True, 20.0, "example.com", None),
    http=None,
):
    if http is None:
        http = HttpProbe(status_code=200, elapsed_ms=100.0, body_snippet="<html>ok</html>")
    return [
        patch("rkn_checker.core.dns_mod.resolve_system", return_value=sys_ip),
        patch("rkn_checker.core.dns_mod.resolve_doh", return_value=doh_ip),
        patch("rkn_checker.core.network.check_tcp", return_value=tcp),
        patch("rkn_checker.core.network.check_tls", return_value=tls),
        patch("rkn_checker.core.http_mod.fetch", return_value=http),
    ]


def _run_with(patches):
    for p in patches:
        p.start()
    try:
        return check_url("test", "https://example.com/")
    finally:
        for p in patches:
            p.stop()


class TestVerdictPath:
    def test_happy_path_yields_ok(self):
        r = _run_with(_patches())
        assert r.verdict == Verdict.OK
        assert r.confidence == Confidence.HIGH

    def test_dns_block_when_system_fails_but_doh_works(self):
        r = _run_with(_patches(sys_ip=None, doh_ip="1.2.3.4"))
        assert r.verdict == Verdict.DNS_BLOCK
        assert r.confidence == Confidence.HIGH

    def test_down_when_neither_resolver_finds_domain(self):
        r = _run_with(_patches(sys_ip=None, doh_ip=None))
        assert r.verdict == Verdict.DOWN
        assert r.confidence == Confidence.LOW

    def test_dns_mismatch_is_flagged_but_not_fatal(self):
        r = _run_with(_patches(sys_ip="1.1.1.1", doh_ip="2.2.2.2"))
        assert r.dns_mismatch is True
        assert r.verdict == Verdict.OK

    def test_tcp_timeout_yields_timeout_verdict(self):
        r = _run_with(_patches(tcp=(False, None, "timeout")))
        assert r.verdict == Verdict.TIMEOUT
        assert r.confidence == Confidence.LOW

    def test_tcp_reset_yields_tcp_reset_verdict(self):
        r = _run_with(_patches(tcp=(False, None, "connection reset")))
        assert r.verdict == Verdict.TCP_RESET
        assert r.confidence == Confidence.MEDIUM

    def test_tcp_other_failure_yields_down(self):
        r = _run_with(_patches(tcp=(False, None, "OSError: no route to host")))
        assert r.verdict == Verdict.DOWN

    def test_tls_reset_is_classified_as_tls_block(self):
        r = _run_with(_patches(tls=(False, None, None, "connection reset during TLS")))
        assert r.verdict == Verdict.TLS_BLOCK
        assert r.confidence == Confidence.MEDIUM

    def test_tls_timeout_is_also_a_tls_block(self):
        r = _run_with(_patches(tls=(False, None, None, "timeout")))
        assert r.verdict == Verdict.TLS_BLOCK
        assert r.confidence == Confidence.MEDIUM

    def test_http_451_is_an_http_stub(self):
        probe = HttpProbe(status_code=451, elapsed_ms=50.0, body_snippet="")
        r = _run_with(_patches(http=probe))
        assert r.verdict == Verdict.HTTP_STUB
        assert r.confidence == Confidence.HIGH

    def test_http_stub_marker_in_body(self):
        probe = HttpProbe(status_code=200, elapsed_ms=50.0,
                          body_snippet="доступ ограничен по решению")
        r = _run_with(_patches(http=probe))
        assert r.verdict == Verdict.HTTP_STUB
        assert r.confidence == Confidence.HIGH

    def test_http_timeout_yields_timeout(self):
        probe = HttpProbe(error="timeout", timed_out=True)
        r = _run_with(_patches(http=probe))
        assert r.verdict == Verdict.TIMEOUT

    def test_normal_200_is_ok(self):
        probe = HttpProbe(status_code=200, elapsed_ms=50.0,
                          body_snippet="<html><body>welcome</body></html>")
        r = _run_with(_patches(http=probe))
        assert r.verdict == Verdict.OK
        assert r.confidence == Confidence.HIGH