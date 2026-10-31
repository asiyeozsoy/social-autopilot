from __future__ import annotations

import os
import time

import requests


class PublishError(RuntimeError):
    pass


class NotConfigured(PublishError):
    """A secret or setting is missing: wait quietly, don't count it as a failed attempt."""


def creds(brand: str, name: str) -> str:
    """Read a per-brand secret, e.g. creds('tinynotes', 'IG_TOKEN') -> $TINYNOTES_IG_TOKEN."""
    key = f"{brand.upper()}_{name}"
    value = os.environ.get(key, "")
    if not value:
        raise NotConfigured(f"secret {key} is not set")
    return value


def check(resp: requests.Response, what: str) -> dict:
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:300]}
    err = body.get("error") if isinstance(body, dict) else None
    tiktok_ok = isinstance(err, dict) and err.get("code") == "ok"  # TikTok wraps success in error.code="ok"
    if resp.status_code >= 400 or (err and not tiktok_ok):
        raise PublishError(f"{what} failed ({resp.status_code}): {err or body}")
    return body


def poll(fn, done, fail=lambda r: False, every=5, timeout=600, what="processing"):
    end = time.time() + timeout
    while True:
        result = fn()
        if done(result):
            return result
        if fail(result):
            raise PublishError(f"{what} failed: {result}")
        if time.time() > end:
            raise PublishError(f"{what} timed out: {result}")
        time.sleep(every)
