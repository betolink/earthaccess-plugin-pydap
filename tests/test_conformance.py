from earthaccess_plugin_spec.testing import run_conformance

from earthaccess_pydap import PyDAPPlugin

from .fixtures import PyDAPFixtures


def test_conformance():
    run_conformance(PyDAPPlugin, fixtures=PyDAPFixtures())
