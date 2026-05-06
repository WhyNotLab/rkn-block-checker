from unittest.mock import patch, MagicMock

from rkn_checker.network import check_tcp, check_tls


class TestCheckTcp:
    @patch("rkn_checker.network.socket.create_connection")
    def test_success_returns_true_and_time(self, mock_conn):
        mock_conn.return_value.__enter__ = MagicMock(return_value=None)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        ok, ms, err = check_tcp("example.com")
        assert ok is True
        assert ms is not None
        assert err is None

    @patch("rkn_checker.network.socket.create_connection", side_effect=__import__("socket").timeout("t"))
    def test_timeout_returns_false_timeout_string(self, mock_conn):
        ok, ms, err = check_tcp("example.com")
        assert ok is False
        assert err == "timeout"

    @patch("rkn_checker.network.socket.create_connection", side_effect=ConnectionResetError("r"))
    def test_reset_returns_false_reset_string(self, mock_conn):
        ok, ms, err = check_tcp("example.com")
        assert ok is False
        assert "reset" in err


class TestCheckTls:
    @patch("rkn_checker.network.socket.create_connection")
    def test_connection_aborted_returns_reset_string(self, mock_conn):
        mock_conn.side_effect = ConnectionAbortedError("abort")
        ok, ms, cn, err = check_tls("example.com")
        assert ok is False
        assert "reset" in err

    @patch("rkn_checker.network.socket.create_connection", side_effect=__import__("socket").timeout("t"))
    def test_timeout_returns_timeout(self, mock_conn):
        ok, ms, cn, err = check_tls("example.com")
        assert ok is False
        assert err == "timeout"
