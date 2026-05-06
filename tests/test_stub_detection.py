from rkn_checker.http import looks_like_stub


class TestLooksLikeStub:
    def test_empty_body_is_not_stub(self):
        assert looks_like_stub("") is False

    def test_normal_page_is_not_stub(self):
        body = "<html><body>welcome to our online store</body></html>"
        assert looks_like_stub(body) is False

    def test_detects_access_restricted_phrase(self):
        body = "<html><body>доступ ограничен по решению суда</body></html>"
        assert looks_like_stub(body) is True

    def test_detects_blocked_phrase(self):
        body = "сайт заблокирован"
        assert looks_like_stub(body) is True

    def test_detects_english_blocked_by_roskomnadzor(self):
        body = "this resource is blocked by roskomnadzor"
        assert looks_like_stub(body) is True

    def test_detects_blocked_by_rkn(self):
        body = "this resource is blocked by rkn"
        assert looks_like_stub(body) is True

    def test_generic_blocked_by_does_not_match(self):
        body = "this resource is blocked by your provider"
        assert looks_like_stub(body) is False

    def test_detects_rkn_register_link(self):
        body = "for details see rkn.gov.ru/org/register"
        assert looks_like_stub(body) is True

    def test_bare_rkn_gov_ru_does_not_match(self):
        body = "for more information visit rkn.gov.ru"
        assert looks_like_stub(body) is False

    def test_po_resheniu_removed_marker_does_not_match(self):
        body = "по решению суда"
        assert looks_like_stub(body) is False

    def test_detects_unified_registry_phrase(self):
        body = "сайт включён в единый реестр запрещённых ресурсов"
        assert looks_like_stub(body) is True

    def test_caller_must_lowercase_body(self):
        # The matcher does a plain substring scan — uppercase shouldn't match.
        body = "ДОСТУП ОГРАНИЧЕН"
        assert looks_like_stub(body) is False
