from rkn_checker.output import _summary_verdict


class TestSummaryVerdict:
    def test_inconclusive_when_whitelist_mostly_fails(self):
        _, msg, note = _summary_verdict(
            white_ok=5, white_total=20,
            black_ok=0, black_blocked=15, black_total=15,
        )
        assert "inconclusive" in msg.lower()

    def test_no_blocks_when_blacklist_fully_open(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=15, black_blocked=0, black_total=15,
        )
        assert "not in" in msg.lower()

    def test_blocked_zone_high_confidence(self):
        _, msg, note = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=3, black_blocked=12, black_total=15,
            black_high_conf=10,
        )
        assert "blocked zone" in msg.lower()
        assert "high confidence" in msg.lower()

    def test_blocked_zone_medium_confidence(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=3, black_blocked=12, black_total=15,
            black_high_conf=2,
        )
        assert "blocked zone" in msg.lower()
        assert "medium confidence" in msg.lower()

    def test_partial_blocks_when_some_blacklist_loads(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=10, black_blocked=5, black_total=15,
        )
        assert "partial" in msg.lower()

    def test_partial_blocks_at_threshold_boundary(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=3, black_blocked=11, black_total=15,
            black_high_conf=8,
        )
        assert "blocked zone" in msg.lower()

    def test_whitelist_check_takes_priority(self):
        _, msg, _ = _summary_verdict(
            white_ok=2, white_total=20,
            black_ok=0, black_blocked=15, black_total=15,
            black_high_conf=15,
        )
        assert "inconclusive" in msg.lower()

    def test_timeouts_excluded_from_blocked_count(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=5, black_blocked=5, black_total=15,
            black_timeout=5,
        )
        assert "partial" in msg.lower()

    def test_all_timeouts_is_inconclusive(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=0, black_blocked=0, black_total=15,
            black_timeout=15,
        )
        assert "inconclusive" in msg.lower() or "timed out" in msg.lower()

    def test_timeouts_do_not_affect_threshold(self):
        _, msg, _ = _summary_verdict(
            white_ok=20, white_total=20,
            black_ok=2, black_blocked=8, black_total=15,
            black_timeout=5,
        )
        assert "blocked zone" in msg.lower()