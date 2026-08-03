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

# 인기 국내 종목/ETF (퀵 선택용). 자유 입력도 가능.
POPULAR_KR_TICKERS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "005380": "현대차",
    "000270": "기아",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "068270": "셀트리온",
    "105560": "KB금융",
    "069500": "KODEX 200 (ETF)",
    "091160": "KODEX 반도체 (ETF)",
}

# 인기 미국 종목/ETF (yfinance 표기, 퀵 선택용). 자유 입력도 가능.
POPULAR_US_TICKERS = {
    "AAPL": "애플",
    "MSFT": "마이크로소프트",
    "GOOGL": "알파벳(구글)",
    "AMZN": "아마존",
    "NVDA": "엔비디아",
    "TSLA": "테슬라",
    "META": "메타",
    "SPY": "S&P500 ETF",
    "QQQ": "나스닥100 ETF",
    "VOO": "S&P500 ETF (뱅가드)",
}

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
