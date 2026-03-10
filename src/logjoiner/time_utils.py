from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def parse_kst_datetime(value: str) -> datetime:
    try:
        naive = datetime.strptime(value, DATETIME_FMT)
    except ValueError as exc:
        raise ValueError(
            f"잘못된 시간 형식: {value}. 형식은 yyyy-MM-dd HH:mm:ss 이어야 합니다."
        ) from exc
    return naive.replace(tzinfo=KST)


def to_utc_epoch_ms(kst_dt: datetime) -> int:
    utc_dt = kst_dt.astimezone(timezone.utc)
    return int(utc_dt.timestamp() * 1000)
