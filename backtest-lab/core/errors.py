"""공용 예외 타입 및 Streamlit 친화적 에러 표시 헬퍼."""
from __future__ import annotations


class DataSourceUnavailable(Exception):
    """외부 데이터 소스가 재시도 후에도 응답하지 않을 때 발생."""

    def __init__(self, source: str, detail: str = ""):
        self.source = source
        self.detail = detail
        super().__init__(f"[{source}] 데이터를 가져오지 못했습니다. {detail}".strip())


def show_data_error(st_module, err: DataSourceUnavailable) -> None:
    """Streamlit 페이지에서 크래시 대신 경고 배너로 표시."""
    st_module.warning(
        f"⚠️ {err.source} 데이터를 불러오지 못했습니다 (캐시된 값이 있으면 그것을 표시합니다). "
        f"{err.detail}"
    )
