"""날짜 포맷 변환 헬퍼."""
from __future__ import annotations

import datetime as dt


def to_yyyymmdd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def to_iso(d: dt.date) -> str:
    return d.strftime("%Y-%m-%d")
