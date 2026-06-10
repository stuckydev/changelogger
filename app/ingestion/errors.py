from __future__ import annotations


class FetchError(Exception):
    def __init__(self, app_slug: str, message: str) -> None:
        self.app_slug = app_slug
        super().__init__(message)
