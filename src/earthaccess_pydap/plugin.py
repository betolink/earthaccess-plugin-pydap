"""The PyDAP plugin: lazy OPeNDAP access through xarray or native pydap.

``request(engine="xarray")`` (the default) returns a lazy xarray Dataset;
``request(engine="pydap")`` returns the native pydap dataset(s) from
``open_url``. Either way the flow is ``request()`` -> ``Job`` -> ``results()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from earthaccess_plugin_spec import Capabilities, Capability, PluginBase

from .errors import NoOPeNDAPUrlsError

__all__ = ["PyDAPPlugin"]

# OPeNDAP's intrinsic capabilities (any DAP endpoint advertises these).
_OPENDAP_OPERATIONS = frozenset(
    {
        Capability.LAZY_READ,
        Capability.SUBSET_DIMENSION,
        Capability.SUBSET_VARIABLE,
    }
)


class PyDAPPlugin(PluginBase):
    name = "pydap"
    needs = frozenset({"umm"})
    auth = "edl"
    output = "xarray"

    @dataclass
    class Options:
        # "xarray": a lazy xarray.Dataset; "pydap": the native pydap dataset(s).
        engine: Literal["xarray", "pydap"] = "xarray"
        protocol: Literal["dap4", "dap2"] = "dap4"
        url_filter: str | None = None  # substring match on OPeNDAP hrefs
        # Concatenating several granules needs a real concat dimension; nested is
        # the mode that streams and lets dask push slices to the server.
        combine: Literal["by_coords", "nested"] = "nested"
        concat_dim: str | None = "time"
        # Dask chunking for multi-granule opens. ``None`` keeps a single granule
        # lazy (OPeNDAP pushes the subset down); multi-granule defaults to
        # "auto". Pass small chunks (e.g. {"lat": 400, "lon": 400}) to fetch
        # only your subset.
        chunks: Any = None

        def __post_init__(self) -> None:
            if self.combine == "nested" and self.concat_dim is None:
                raise ValueError("combine=nested requires concat_dim")

    def _request(self, results: Any, options: Options) -> Any:
        urls = [
            with_scheme(url, options.protocol)
            for url in opendap_urls(results, options.url_filter)
        ]
        if not urls:
            raise NoOPeNDAPUrlsError(
                f"no OPeNDAP links in the UMM for {results.collection_id}"
            )
        # Login happens here, on the caller's thread, not in the worker.
        session = self._ctx.auth.session()
        return self.job(lambda: _open(urls, session, options))

    def _supports(self, results: Any) -> Capabilities:
        # Granule links are better evidence than a collection association,
        # because the data opened is the granule URL.
        if not _has_granules(results):
            return Capabilities(
                None, reason="supply search results to check OPeNDAP links"
            )
        urls = opendap_urls(results)
        if urls:
            granules = list(getattr(results, "ids", ()) or ())
            if len(urls) < len(granules):
                self._ctx.logger.info(
                    "%s: %d of %d granules have an OPeNDAP link",
                    self.name,
                    len(urls),
                    len(granules),
                )
            return Capabilities(True, operations=_OPENDAP_OPERATIONS)
        return Capabilities(False, reason="none of these granules has an OPeNDAP link")


def _has_granules(results: Any) -> bool:
    umm = getattr(results, "umm", None)
    return bool(list(umm())) if callable(umm) else False


def _open(urls: list[str], session: Any, options: Any) -> Any:
    if options.engine == "pydap":
        return _native_datasets(urls, session, options.protocol)

    import xarray as xr

    if len(urls) == 1:
        # One OPeNDAP dataset: keep it lazy (numpy-backed). xarray pushes the
        # subset straight to the server, so only the requested slice is fetched;
        # wrapping it in dask would download the whole variable.
        extra = {} if options.chunks is None else {"chunks": options.chunks}
        return xr.open_dataset(urls[0], engine="pydap", session=session, **extra)
    # Several granules: dask is required to concatenate lazily. Chunk so a
    # subset maps to server-side constraint expressions instead of whole files.
    chunks = options.chunks if options.chunks is not None else "auto"
    extra = {"concat_dim": options.concat_dim} if options.combine == "nested" else {}
    return xr.open_mfdataset(
        urls,
        engine="pydap",
        session=session,
        combine=options.combine,
        parallel=True,
        chunks=chunks,
        **extra,
    )


def _native_datasets(urls: list[str], session: Any, protocol: str) -> Any:
    """The raw pydap datasets: one per OPeNDAP URL (a granule URL is one file).

    A single URL returns its dataset; several return a list. This is metadata
    plus lazy arrays, so ``.tree()`` and native operations work without
    downloading data.
    """

    import pydap.client

    datasets = [
        pydap.client.open_url(url, protocol=protocol, session=session) for url in urls
    ]
    return datasets[0] if len(datasets) == 1 else datasets


def opendap_urls(results: Any, needle: str | None = None) -> list[str]:
    """Collect OPeNDAP hrefs from the granules' UMM RelatedUrls."""

    urls: list[str] = []
    for umm in results.umm():
        for related in umm.get("RelatedUrls", []):
            kind = f"{related.get('Type', '')} {related.get('Subtype', '')}".upper()
            url = related.get("URL", "")
            if (
                "OPENDAP" in kind
                and url
                and (needle is None or needle in url)
                and url not in urls
            ):
                urls.append(url)
    return urls


def with_scheme(url: str, protocol: str) -> str:
    # VERIFY: whether OPeNDAP URLs carry suffixes such as .html or .dmr to strip.
    if url.startswith(("dap2://", "dap4://")):
        return url
    return protocol + "://" + url.split("://", 1)[-1]
