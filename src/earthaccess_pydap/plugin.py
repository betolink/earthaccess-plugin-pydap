"""The PyDAP plugin: lazy OPeNDAP access through xarray.

``_open`` is isolated so the unverified xarray/pydap integration is patched in
one place. RelatedUrls handling is pure Python and tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from earthaccess_plugin_spec import PluginBase, Support

from .errors import NoOPeNDAPUrlsError

__all__ = ["PyDAPPlugin"]


class PyDAPPlugin(PluginBase):
    name = "pydap"
    needs = frozenset({"umm"})
    auth = "edl"
    output = "xarray"

    @dataclass
    class Options:
        protocol: Literal["dap4", "dap2"] = "dap4"
        url_filter: str | None = None  # substring match on OPeNDAP hrefs
        combine: Literal["by_coords", "nested"] = "by_coords"
        concat_dim: str | None = None  # required when combine == 'nested'

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

    def open(self, results: Any = None, **options: Any) -> Any:
        """Lazy open: returns the dataset directly."""

        return self.run(results, **options)

    def _supports(self, results: Any) -> Support:
        # Granule links are better evidence than a collection association,
        # because the data opened is the granule URL.
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
            return Support(True)
        return Support(False, "none of these granules has an OPeNDAP link")


def _open(urls: list[str], session: Any, options: Any) -> Any:
    # VERIFY: session= and dap4:// reach the pydap backend in the pinned versions.
    import xarray as xr

    if len(urls) == 1:
        return xr.open_dataset(urls[0], engine="pydap", session=session)
    extra = {"concat_dim": options.concat_dim} if options.combine == "nested" else {}
    return xr.open_mfdataset(
        urls, engine="pydap", session=session, combine=options.combine, **extra
    )


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
