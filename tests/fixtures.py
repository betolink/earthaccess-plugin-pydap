"""Conformance fixtures for PyDAP: real UMM, patched xarray/pydap seam."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from unittest import mock

from earthaccess_plugin_spec.results import GranuleResultSet
from earthaccess_plugin_spec.testing import Fixtures

__all__ = ["PyDAPFixtures", "make_granule"]


def make_granule(
    *,
    collection_id: str = "C1234-EXAMPLE",
    concept_id: str = "G1234-EXAMPLE",
    ur: str = "G1234.EXAMPLE",
    urls: list[str] | None = None,
) -> dict[str, Any]:
    urls = urls if urls is not None else ["https://example.org/g1.dap"]
    return {
        "meta": {"concept-id": concept_id, "collection-concept-id": collection_id},
        "umm": {
            "GranuleUR": ur,
            "RelatedUrls": [{"Type": "OPeNDAP", "URL": url} for url in urls],
        },
    }


class PyDAPFixtures(Fixtures):
    def __init__(self, dataset: Any = None, **kwargs: Any) -> None:
        kwargs.setdefault("result_set", GranuleResultSet([make_granule()]))
        super().__init__(**kwargs)
        self.dataset = dataset if dataset is not None else object()

    def backend(self) -> AbstractContextManager[Any]:
        import earthaccess_pydap.plugin as plugin_mod

        return mock.patch.object(
            plugin_mod, "_open", lambda urls, session, options: self.dataset
        )
