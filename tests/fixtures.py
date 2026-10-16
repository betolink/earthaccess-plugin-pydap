"""Conformance fixtures for PyDAP: real UMM, no backend patch needed."""

from __future__ import annotations

import contextlib
from contextlib import AbstractContextManager
from typing import Any

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
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("result_set", GranuleResultSet([make_granule()]))
        kwargs.setdefault(
            "unsupported_result_set",
            GranuleResultSet([make_granule(collection_id="C-NO-OPENDAP", urls=[])]),
        )
        super().__init__(**kwargs)

    def backend(self) -> AbstractContextManager[Any]:
        # The xarray client only builds URLs; nothing to patch.
        return contextlib.nullcontext()
