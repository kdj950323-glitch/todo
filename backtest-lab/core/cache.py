"""2단 캐시: 로컬 파일 캐시(프로세스 재시작 후에도 유지) + retry.

스크레이핑 기반 소스(pykrx)와 비공식 클라이언트(yfinance)를 보호하기 위해
모든 외부 데이터 호출은 disk_cache + retry 데코레이터를 함께 사용한다.
"""
from __future__ import annotations

import functools
import hashlib
import pickle
import time
from pathlib import Path
from typing import Callable

import pandas as pd

from core.config import DATA_CACHE_DIR, RETRY_ATTEMPTS, RETRY_BACKOFF_BASE_SEC
from core.errors import DataSourceUnavailable


def _cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    raw = f"{func_name}|{args}|{sorted(kwargs.items())}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _cache_paths(subdir: str, key: str) -> tuple[Path, Path]:
    d = DATA_CACHE_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.parquet", d / f"{key}.pkl"


def _is_fresh(path: Path, ttl: int | None) -> bool:
    if not path.exists():
        return False
    if ttl is None:
        return True
    return (time.time() - path.stat().st_mtime) < ttl


def _load(parquet_path: Path, pkl_path: Path):
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if pkl_path.exists():
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
    raise FileNotFoundError


def _save(value, parquet_path: Path, pkl_path: Path) -> None:
    if isinstance(value, pd.DataFrame):
        value.to_parquet(parquet_path)
        pkl_path.unlink(missing_ok=True)
    else:
        with open(pkl_path, "wb") as f:
            pickle.dump(value, f)
        parquet_path.unlink(missing_ok=True)


def disk_cache(subdir: str, ttl: int | None, source: str = ""):
    """결과를 로컬 파일로 영속 캐싱하는 데코레이터.

    force_refresh=True 키워드 인자를 호출 시 넘기면 캐시를 무시하고 재조회한다.
    소스 호출이 실패해도 만료된 캐시가 있으면 그것을 반환해 크래시를 피한다.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, force_refresh: bool = False, **kwargs):
            key = _cache_key(func.__name__, args, kwargs)
            parquet_path, pkl_path = _cache_paths(subdir, key)

            if not force_refresh and (_is_fresh(parquet_path, ttl) or _is_fresh(pkl_path, ttl)):
                try:
                    return _load(parquet_path, pkl_path)
                except FileNotFoundError:
                    pass

            try:
                value = func(*args, **kwargs)
                _save(value, parquet_path, pkl_path)
                return value
            except Exception as exc:  # noqa: BLE001 - 폴백을 위해 광범위 캐치
                try:
                    return _load(parquet_path, pkl_path)
                except FileNotFoundError:
                    raise DataSourceUnavailable(source or func.__name__, str(exc)) from exc

        return wrapper

    return decorator


def retry(attempts: int = RETRY_ATTEMPTS, backoff_base: float = RETRY_BACKOFF_BASE_SEC, source: str = ""):
    """지수 백오프 재시도 데코레이터. 소진 시 DataSourceUnavailable을 발생시킨다."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if i < attempts - 1:
                        time.sleep(backoff_base ** i)
            raise DataSourceUnavailable(source or func.__name__, str(last_exc))

        return wrapper

    return decorator
