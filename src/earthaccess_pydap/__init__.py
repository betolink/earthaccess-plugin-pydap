"""earthaccess-pydap: lazy OPeNDAP access through PyDAP."""

from __future__ import annotations

from .errors import NoOPeNDAPUrlsError
from .plugin import PyDAPPlugin

__all__ = ["NoOPeNDAPUrlsError", "PyDAPPlugin"]
