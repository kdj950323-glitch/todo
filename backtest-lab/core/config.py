"""전역 설정: 경로, 캐시 TTL, 자산군별 기본 티커 상수."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_CACHE_DIR = BASE_DIR / "data_cache"
DATA_CACHE_DIR.mkdir(exist_ok=True)

# 캐시 TTL (초). None = 무기한(마감된 과거 데이터).
TTL_HISTORICAL = None
TTL_TODAY = 20 * 60

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SEC = 1.5

DEFAULT_KR_TICKER = "005930"  # 삼성전자
DEFAULT_US_TICKER = "AAPL"
DEFAULT_CRYPTO_TICKER = "BTC-USD"

# 인기 코인 티커 (yfinance 표기, 퀵 선택용). 자유 입력도 가능.
POPULAR_CRYPTO_TICKERS = {
    "BTC-USD": "비트코인",
    "ETH-USD": "이더리움",
    "XRP-USD": "리플",
    "SOL-USD": "솔라나",
    "DOGE-USD": "도지코인",
    "ADA-USD": "에이다",
    "AVAX-USD": "아발란체",
    "TRX-USD": "트론",
    "DOT-USD": "폴카닷",
    "LINK-USD": "체인링크",
    "LTC-USD": "라이트코인",
    "MATIC-USD": "폴리곤",
}
