from typing import Iterator, Protocol


class Source(Protocol):
    def fetch_pages(self, limit_pages: int | None = None) -> Iterator[list[dict]]:
        ...
