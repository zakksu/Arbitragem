"""Shared helpers for Streamlit dashboard."""

from __future__ import annotations

import os
from functools import lru_cache

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

_READ_TIMEOUT = 12.0
_WRITE_TIMEOUT = 120.0


@lru_cache(maxsize=1)
def _http_client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        timeout=httpx.Timeout(_READ_TIMEOUT, connect=2.0),
        limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
    )


def api_get(path: str, params: dict | None = None) -> dict | list:
    r = _http_client().get(path, params=params or {})
    r.raise_for_status()
    return r.json()


def api_patch(path: str, json: dict | None = None) -> dict:
    r = _http_client().patch(path, json=json or {})
    r.raise_for_status()
    return r.json()


def api_post(path: str, json: dict | None = None) -> dict:
    client = _http_client()
    r = client.post(path, json=json or {}, timeout=_WRITE_TIMEOUT)
    if r.status_code >= 400:
        detail = r.text
        try:
            detail = r.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(str(detail))
    r.raise_for_status()
    return r.json()


def api_upload_csv(path: str, file_name: str, file_bytes: bytes) -> dict:
    r = _http_client().post(
        path,
        files={"file": (file_name, file_bytes, "text/csv")},
        timeout=_WRITE_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def trades_to_df(trades: list) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    return pd.DataFrame(trades)


def scans_to_df(scans: list) -> pd.DataFrame:
    if not scans:
        return pd.DataFrame()
    df = pd.DataFrame(scans)
    if "pattern_tags" in df.columns:
        df["pattern_tags"] = df["pattern_tags"].apply(lambda t: t or [])
    return df
