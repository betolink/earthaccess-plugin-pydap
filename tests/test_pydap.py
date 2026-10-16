import pytest
from earthaccess_plugin_spec import Support, UnsupportedCollectionError
from earthaccess_plugin_spec.results import GranuleResultSet
from earthaccess_plugin_spec.testing import fake_context

from earthaccess_pydap import NoOPeNDAPUrlsError, PyDAPPlugin
from earthaccess_pydap.plugin import with_scheme

from .fixtures import PyDAPFixtures, make_granule


class TestUrlExtraction:
    def test_basic(self):
        from earthaccess_pydap.plugin import opendap_urls

        rs = GranuleResultSet([make_granule(urls=["https://e.org/a.dap", "https://e.org/b.dap"])])
        assert opendap_urls(rs) == ["https://e.org/a.dap", "https://e.org/b.dap"]

    def test_filter_and_dedupe(self):
        from earthaccess_pydap.plugin import opendap_urls

        rs = GranuleResultSet(
            [make_granule(urls=["https://e.org/a.dap", "https://e.org/a.dap", "https://e.org/b.dap"])]
        )
        assert opendap_urls(rs, needle="a.dap") == ["https://e.org/a.dap"]

    def test_subtype_match_and_ignores_non_opendap(self):
        from earthaccess_pydap.plugin import opendap_urls

        granule = make_granule()
        granule["umm"]["RelatedUrls"] = [
            {"Type": "GET DATA", "Subtype": "OPeNDAP", "URL": "https://e.org/x"},
            {"Type": "GET DATA", "URL": "https://e.org/y"},
        ]
        assert opendap_urls(GranuleResultSet([granule])) == ["https://e.org/x"]


class TestWithScheme:
    @pytest.mark.parametrize(
        ("url", "protocol", "expected"),
        [
            ("https://e.org/a", "dap4", "dap4://e.org/a"),
            ("https://e.org/a", "dap2", "dap2://e.org/a"),
            ("dap4://e.org/a", "dap2", "dap4://e.org/a"),
        ],
    )
    def test_scheme(self, url, protocol, expected):
        assert with_scheme(url, protocol) == expected


class TestOptions:
    def test_nested_requires_concat_dim(self):
        with pytest.raises(ValueError, match="concat_dim"):
            PyDAPPlugin.Options(combine="nested")

    def test_nested_ok_with_concat_dim(self):
        options = PyDAPPlugin.Options(combine="nested", concat_dim="time")
        assert options.concat_dim == "time"

    def test_unknown_option_rejected(self):
        plugin = PyDAPPlugin(fake_context())
        with pytest.raises(TypeError):
            plugin.request(PyDAPFixtures().result_set, nope=1)


class TestRequest:
    def test_no_urls_raises(self):
        plugin = PyDAPPlugin(fake_context())
        granule = make_granule()
        granule["umm"]["RelatedUrls"] = [{"Type": "GET DATA", "URL": "https://e.org/y"}]
        # check=False bypasses the support gate and reaches the backend seam.
        with pytest.raises(NoOPeNDAPUrlsError):
            plugin.request(GranuleResultSet([granule]), check=False)

    def test_session_is_used_and_login_is_eager(self):
        ctx = fake_context()
        plugin = PyDAPPlugin(ctx)
        fixtures = PyDAPFixtures()
        with fixtures.backend():
            job = plugin.request(fixtures.result_set)
            result = job.results()
        assert ctx.auth.session_calls == 1
        assert result is fixtures.dataset

    def test_open_alias_returns_dataset(self):
        plugin = PyDAPPlugin(fake_context())
        fixtures = PyDAPFixtures()
        with fixtures.backend():
            result = plugin.open(fixtures.result_set)
        assert result is fixtures.dataset

    def test_protocol_is_forwarded(self):
        captured: dict = {}

        def fake_open(urls, session, options):
            captured["urls"] = urls
            return "ds"

        from unittest import mock

        import earthaccess_pydap.plugin as plugin_mod

        plugin = PyDAPPlugin(fake_context())
        fixtures = PyDAPFixtures()
        with mock.patch.object(plugin_mod, "_open", fake_open):
            result = plugin.request(fixtures.result_set, protocol="dap2").results()
        assert result == "ds"
        assert captured["urls"] == ["dap2://example.org/g1.dap"]


def test_entry_point_registered():
    from importlib.metadata import entry_points

    names = {ep.name for ep in entry_points(group="earthaccess.plugins")}
    assert "pydap" in names


class TestSupport:
    def test_supported_with_links(self):
        plugin = PyDAPPlugin(fake_context())
        assert plugin.supports(PyDAPFixtures().result_set) == Support(True)

    def test_unsupported_without_links(self):
        plugin = PyDAPPlugin(fake_context())
        support = plugin.supports(
            GranuleResultSet([make_granule(collection_id="C-X", urls=[])])
        )
        assert support.ok is False
        assert "OPeNDAP" in support.reason

    def test_request_raises_before_backend(self):
        from unittest import mock

        import earthaccess_pydap.plugin as plugin_mod

        plugin = PyDAPPlugin(fake_context())
        unsupported = GranuleResultSet([make_granule(collection_id="C-X", urls=[])])
        with (
            mock.patch.object(plugin_mod, "_open") as open_mock,
            pytest.raises(UnsupportedCollectionError),
        ):
            plugin.request(unsupported)
        open_mock.assert_not_called()
