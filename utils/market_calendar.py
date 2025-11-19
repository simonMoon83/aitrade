"""
시장 거래일 캘린더 유틸리티
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas_market_calendars as mcal
import pytz

from utils.logger import setup_logger

logger = setup_logger("market_calendar")


class MarketCalendar:
    """NYSE(미국 주식 시장) 거래 일정 헬퍼"""

    def __init__(self, calendar_code: str = "XNYS"):
        self.calendar = mcal.get_calendar(calendar_code)
        self.ny_tz = pytz.timezone("America/New_York")
        self.local_tz = datetime.now().astimezone().tzinfo
        self._session_cache: Dict[str, Optional[Dict]] = {}

    def _normalize_date(self, value: Optional[date | datetime]) -> date:
        if value is None:
            return datetime.now(self.ny_tz).date()
        if isinstance(value, datetime):
            return value.astimezone(self.ny_tz).date()
        return value

    def _get_session(self, session_date: date) -> Optional[Dict]:
        key = session_date.strftime("%Y-%m-%d")
        if key in self._session_cache:
            return self._session_cache[key]

        try:
            schedule = self.calendar.schedule(
                start_date=key,
                end_date=key,
            )
        except Exception as exc:
            logger.error(f"거래 일정 조회 실패 ({key}): {exc}")
            self._session_cache[key] = None
            return None

        if schedule.empty:
            self._session_cache[key] = None
            return None

        market_open_utc = schedule.iloc[0]["market_open"]
        market_close_utc = schedule.iloc[0]["market_close"]
        session_info = {
            "date": session_date,
            "market_open_et": market_open_utc.tz_convert(self.ny_tz),
            "market_close_et": market_close_utc.tz_convert(self.ny_tz),
            "market_open_local": market_open_utc.tz_convert(self.local_tz),
            "market_close_local": market_close_utc.tz_convert(self.local_tz),
        }
        self._session_cache[key] = session_info
        return session_info

    def get_session_times(self, session_date: Optional[date | datetime]) -> Optional[Dict]:
        """지정 날짜의 장 시작/종료 시간 반환"""
        if session_date is None:
            return None
        normalized = self._normalize_date(session_date)
        return self._get_session(normalized)

    def is_trading_day(self, target_date: Optional[date | datetime] = None) -> bool:
        target_date = self._normalize_date(target_date)
        session = self._get_session(target_date)
        return session is not None

    def get_previous_trading_day(
        self, target_date: Optional[date | datetime] = None, include_today: bool = False
    ) -> Optional[date]:
        target_date = self._normalize_date(target_date)
        start = target_date - timedelta(days=14)
        valid_days = self.calendar.valid_days(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=target_date.strftime("%Y-%m-%d"),
        )
        for ts in reversed(valid_days):
            day = ts.to_pydatetime().date()
            if include_today:
                if day <= target_date:
                    return day
            else:
                if day < target_date:
                    return day
        return None

    def get_next_trading_day(
        self, target_date: Optional[date | datetime] = None, include_today: bool = False
    ) -> Optional[date]:
        target_date = self._normalize_date(target_date)
        end = target_date + timedelta(days=14)
        valid_days = self.calendar.valid_days(
            start_date=target_date.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
        for ts in valid_days:
            day = ts.to_pydatetime().date()
            if include_today:
                if day >= target_date:
                    return day
            else:
                if day > target_date:
                    return day
        return None

    def get_last_completed_trading_day(self, now: Optional[datetime] = None) -> Optional[date]:
        now = now.astimezone(self.ny_tz) if now else datetime.now(self.ny_tz)
        today_session = self._get_session(now.date())
        if today_session:
            if now >= today_session["market_close_et"]:
                return today_session["date"]
            if today_session["market_open_et"] <= now < today_session["market_close_et"]:
                # 장 중에는 아직 완전한 데이터가 아닐 수 있으므로 전일 반환
                return self.get_previous_trading_day(today_session["date"])
        return self.get_previous_trading_day(now.date(), include_today=True)

    def get_recent_trading_days(self, end_date: date, count: int) -> List[date]:
        start = end_date - timedelta(days=count * 3)
        valid_days = self.calendar.valid_days(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )
        recent = [ts.to_pydatetime().date() for ts in valid_days]
        if not recent:
            return []
        return recent[-count:]

    def adjust_to_trading_day(self, target_date: Optional[date | datetime] = None) -> Optional[date]:
        target_date = self._normalize_date(target_date)
        if self.is_trading_day(target_date):
            return target_date
        return self.get_previous_trading_day(target_date, include_today=True)

    def get_market_state(self, now: Optional[datetime] = None) -> Dict:
        now = now.astimezone(self.ny_tz) if now else datetime.now(self.ny_tz)
        today_session = self._get_session(now.date())
        state = {
            "is_open": False,
            "session_date": None,
            "market_open": None,
            "market_close": None,
            "next_open": None,
            "next_close": None,
            "message": "",
        }

        if today_session:
            open_et = today_session["market_open_et"]
            close_et = today_session["market_close_et"]
            if open_et <= now <= close_et:
                next_day = self.get_next_trading_day(today_session["date"])
                next_session = self._get_session(next_day) if next_day else None
                state.update(
                    {
                        "is_open": True,
                        "session_date": today_session["date"],
                        "market_open": today_session["market_open_local"],
                        "market_close": today_session["market_close_local"],
                        "next_open": next_session["market_open_local"] if next_session else None,
                        "next_close": next_session["market_close_local"] if next_session else None,
                        "message": "정규장 거래 중",
                    }
                )
                return state

        next_day = self.get_next_trading_day(now.date(), include_today=True)
        next_session = self._get_session(next_day) if next_day else None
        prev_day = self.get_previous_trading_day(now.date(), include_today=True)
        prev_session = self._get_session(prev_day) if prev_day else None

        state.update(
            {
                "session_date": next_session["date"] if next_session else None,
                "market_open": next_session["market_open_local"] if next_session else None,
                "market_close": next_session["market_close_local"] if next_session else None,
                "next_open": next_session["market_open_local"] if next_session else None,
                "next_close": next_session["market_close_local"] if next_session else None,
                "message": "장외 시간" if prev_session else "휴장일",
                "previous_session_date": prev_session["date"] if prev_session else None,
            }
        )
        return state


market_calendar = MarketCalendar()


