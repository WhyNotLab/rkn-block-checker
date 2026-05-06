from unittest.mock import patch

import pytest

from rkn_checker.cli import main


class TestMutuallyExclusiveFlags:
    def test_white_and_black_together_exits(self):
        with pytest.raises(SystemExit) as ei:
            main(["--white", "--black"])
        assert ei.value.code == 2


class TestValidation:
    def test_workers_zero_exits(self):
        with pytest.raises(SystemExit) as ei:
            main(["--workers", "0"])
        assert ei.value.code == 2

    def test_timeout_negative_exits(self):
        with pytest.raises(SystemExit) as ei:
            main(["--timeout", "-1"])
        assert ei.value.code == 2


class TestJsonModeTimeout:
    @patch("rkn_checker.cli.get_self_info", return_value={"ip": "1.2.3.4"})
    @patch("rkn_checker.core.check_urls_parallel", return_value=[])
    def test_json_mode_passes_timeout_to_get_self_info(self, mock_parallel, mock_self):
        main(["--json", "--timeout", "3.0"])
        mock_self.assert_called_with(timeout=3.0)

    @patch("rkn_checker.cli.get_self_info", return_value=None)
    @patch("rkn_checker.core.check_urls_parallel", return_value=[])
    def test_no_self_info_flag_skips_lookup(self, mock_parallel, mock_self):
        main(["--json", "--no-self-info"])
        mock_self.assert_not_called()


class TestStreamingNoSelfInfo:
    @patch("rkn_checker.cli.print_header")
    @patch("rkn_checker.cli._run_streaming", return_value=([], []))
    def test_no_self_info_passes_empty_dict_to_header(self, mock_stream, mock_header):
        main(["--no-self-info"])
        mock_header.assert_called_with({})
