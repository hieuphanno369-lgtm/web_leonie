import csv
import io
import os
from typing import Iterator

from automation.models import SalesforceSource


class SalesforceFetcher:
    """Pulls records from Salesforce via bulk2 (default) or REST query_all."""

    def __init__(self, source: SalesforceSource):
        self.s = source

    def _connect(self):
        from simple_salesforce import Salesforce  # lazy: not always installed

        user = os.environ[self.s.user_ref]
        password = os.environ[self.s.pass_ref]
        token = os.environ.get(self.s.token_ref, "") if self.s.token_ref else ""
        return Salesforce(
            username=user,
            password=password,
            security_token=token,
            instance_url=self.s.instance_url,
        )

    def fetch_pages(self, limit_pages: int | None = None) -> Iterator[list[dict]]:
        sf = self._connect()

        if self.s.use_bulk:
            sf_obj = getattr(sf.bulk2, self.s.object_name)
            chunks = list(sf_obj.query(self.s.soql))
            if not chunks:
                yield []
                return

            # Bulk2 yields CSV string chunks; first has the header row,
            # subsequent chunks are continuation rows without a header.
            parts: list[str] = []
            for i, chunk in enumerate(chunks):
                text = chunk if isinstance(chunk, str) else chunk.decode("utf-8")
                if i > 0 and "\n" in text:
                    text = text.split("\n", 1)[1]
                parts.append(text)

            reader = csv.DictReader(io.StringIO("".join(parts)))
            yield [dict(row) for row in reader]

        else:
            # REST query_all handles pagination internally
            result = sf.query_all(self.s.soql)
            records = result.get("records", [])
            for r in records:
                r.pop("attributes", None)
            yield records
