"""PyDAP-specific errors."""

from __future__ import annotations

from earthaccess_plugin_spec import EarthaccessPluginError

__all__ = ["NoOPeNDAPUrlsError"]


class NoOPeNDAPUrlsError(EarthaccessPluginError):
    """Raised when the granules' UMM contains no OPeNDAP links."""
