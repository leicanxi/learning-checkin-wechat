from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Shanghai"
LOCAL_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE)


def local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def local_today():
    return local_now().date()


def local_now_naive() -> datetime:
    return local_now().replace(tzinfo=None)
