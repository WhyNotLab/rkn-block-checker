from unittest.mock import patch, MagicMock

from rkn_checker.http import fetch, looks_like_stub


class TestFetch:
    @patch("rkn_checker.http.requests.get")
    def test_success_returns_probe(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.elapsed.total_seconds.return_value = 0.1
        resp.text = "<html>ok</html>"
        mock_get.return_value = resp
        probe = fetch("https://example.com")
        assert probe.status_code == 200
        assert probe.error is None

    @patch("rkn_checker.http.requests.get", side_effect=__import__("requests").exceptions.Timeout("t"))
    def test_timeout_returns_timed_out_probe(self, mock_get):
        probe = fetch("https://example.com")
        assert probe.timed_out is True
        assert probe.error == "timeout"

    @patch("rkn_checker.http.requests.get", side_effect=__import__("requests").exceptions.RequestException("e"))
    def test_generic_error_returns_error_probe(self, mock_get):
        probe = fetch("https://example.com")
        assert probe.error is not None
        assert probe.timed_out is False

    @patch("rkn_checker.http.requests.get")
    def test_passes_timeout_param(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.elapsed.total_seconds.return_value = 0.05
        resp.text = "ok"
        mock_get.return_value = resp
        fetch("https://example.com", timeout=2.0)
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["timeout"] == 2.0


class TestLooksLikeStubNegative:
    def test_generic_blocked_by_does_not_match(self):
        assert looks_like_stub("this resource is blocked by your provider") is False

    def test_bare_rkn_gov_ru_does_not_match(self):
        assert looks_like_stub("for more information visit rkn.gov.ru") is False

    def test_generic_po_resheniu_does_not_match(self):
        assert looks_like_stub("по решению суда") is False
