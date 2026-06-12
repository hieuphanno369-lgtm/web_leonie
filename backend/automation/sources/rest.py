import os
import re
import time
from typing import Iterator

import httpx

from automation.models import RestSource

_VAR = re.compile(r"\$\{(\w+)\}")


class MissingEnvVar(Exception):
    pass


def _env(name: str) -> str:
    if name not in os.environ:
        raise MissingEnvVar(f"Missing env var {name}")
    return os.environ[name]


def _resolve(template: str) -> str:
    return _VAR.sub(lambda m: _env(m.group(1)), template)


def _dig(obj, path: str):
    if not path:
        return obj
    for part in path.split("."):
        obj = obj.get(part) if isinstance(obj, dict) else None
    return obj


class RestFetcher:
    """Consumes a RestSource config and yields pages of raw records."""

    def __init__(self, source: RestSource):
        self.s = source

    def _auth_and_headers(self):
        headers = {k: _resolve(v) for k, v in self.s.headers.items()}
        auth = None
        a = self.s.auth
        if a.type == "api_key" and a.header_name and a.value_ref:
            headers[a.header_name] = _env(a.value_ref)
        elif a.type == "bearer" and a.value_ref:
            headers["Authorization"] = "Bearer " + _env(a.value_ref)
        elif a.type == "basic" and a.user_ref and a.pass_ref:
            auth = httpx.BasicAuth(_env(a.user_ref), _env(a.pass_ref))
        return headers, auth

    def _get(self, client, url, params, headers, auth):
        delay = 0.5
        for attempt in range(self.s.max_retries + 1):
            resp = client.get(url, params=params, headers=headers, auth=auth)
            if resp.status_code < 400:
                return resp
            retryable = resp.status_code == 429 or resp.status_code >= 500
            if retryable and attempt < self.s.max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
        return resp

    def fetch_pages(self, limit_pages: int | None = None, client=None) -> Iterator[list[dict]]:
        headers, auth = self._auth_and_headers()   # resolves ${VAR} up front (may raise)
        url = _resolve(self.s.url)
        base_params = {k: _resolve(v) for k, v in self.s.params.items()}
        own = client is None
        cl = client or httpx.Client(timeout=self.s.timeout_seconds)
        try:
            page_num = self.s.pagination.start if self.s.pagination else None
            count = 0
            while True:
                params = dict(base_params)
                if self.s.pagination:
                    params[self.s.pagination.param] = page_num
                resp = self._get(cl, url, params, headers, auth)
                records = _dig(resp.json(), self.s.records_path)
                if records is None:
                    records = []
                if not isinstance(records, list):
                    records = [records]
                if not records:
                    break
                yield records
                count += 1
                if limit_pages is not None and count >= limit_pages:
                    break
                if not self.s.pagination:
                    break
                page_num += 1
        finally:
            if own:
                cl.close()
