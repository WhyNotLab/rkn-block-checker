from unittest.mock import patch, MagicMock

from rkn_checker.dns import resolve_system, resolve_doh


class TestResolveSystem:
    @patch("rkn_checker.dns.socket.gethostbyname", return_value="1.2.3.4")
    def test_returns_ip_on_success(self, mock_gethost):
        assert resolve_system("example.com") == "1.2.3.4"

    @patch("rkn_checker.dns.socket.gethostbyname", side_effect=__import__("socket").gaierror("fail"))
    def test_returns_none_on_gaierror(self, mock_gethost):
        assert resolve_system("example.com") is None


class TestResolveDoh:
    @patch("rkn_checker.dns.requests.get")
    def test_returns_ip_from_answer(self, mock_get):
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"Answer": [{"type": 1, "data": "9.9.9.9"}]}
        mock_get.return_value = resp
        assert resolve_doh("example.com") == "9.9.9.9"

    @patch("rkn_checker.dns.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        resp = MagicMock()
        resp.ok = False
        mock_get.return_value = resp
        assert resolve_doh("example.com") is None

    @patch("rkn_checker.dns.requests.get", side_effect=__import__("requests").exceptions.RequestException("network error"))
    def test_returns_none_on_request_exception(self, mock_get):
        assert resolve_doh("example.com") is None

    @patch("rkn_checker.dns.requests.get")
    def test_passes_timeout_param(self, mock_get):
        resp = MagicMock()
        resp.ok = False
        mock_get.return_value = resp
        resolve_doh("example.com", timeout=2.5)
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["timeout"] == 2.5
