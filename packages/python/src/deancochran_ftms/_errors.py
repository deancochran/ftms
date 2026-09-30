"""Internal shared codec exception."""

from __future__ import annotations

from typing import Literal


class RawCodecError(ValueError):
    """Invalid strict raw-codec input, with a stable diagnostic ``code``."""

    def __init__(self, code: Literal["kind", "length", "range"], message: str) -> None:
        super().__init__(message)
        self.code = code
