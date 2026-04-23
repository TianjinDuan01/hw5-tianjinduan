#!/usr/bin/env python3
"""Calculate a business-hours-aware SLA breach timestamp for a single ticket."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass
class Config:
    ticket_id: Optional[str]
    created_at: datetime
    sla_hours: float
    timezone: str
    business_start: time
    business_end: time
    working_days: List[int]
    evaluated_at: Optional[datetime]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate the exact SLA breach time using business-hour-aware datetime math."
    )
    parser.add_argument("--created-at", required=True, help="Ticket creation timestamp in ISO 8601 format.")
    parser.add_argument("--sla-hours", required=True, type=float, help="SLA duration in hours.")
    parser.add_argument("--timezone", required=True, help="IANA timezone, e.g. America/Los_Angeles.")
    parser.add_argument("--business-start", required=True, help="Business day start time in HH:MM.")
    parser.add_argument("--business-end", required=True, help="Business day end time in HH:MM.")
    parser.add_argument(
        "--working-days",
        nargs="+",
        type=int,
        required=True,
        help="Working days as integers where Monday=0 and Sunday=6.",
    )
    parser.add_argument("--ticket-id", default=None, help="Optional ticket identifier.")
    parser.add_argument(
        "--evaluated-at",
        default=None,
        help="Optional timestamp used to decide whether the ticket is within SLA or breached.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON instead of compact JSON.",
    )
    return parser.parse_args()


def parse_hhmm(value: str) -> time:
    try:
        hour_str, minute_str = value.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
        return time(hour=hour, minute=minute)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid HH:MM time: {value}") from exc


def parse_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid IANA timezone: {name}") from exc


def parse_iso_datetime(value: str, tz: ZoneInfo, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO 8601 timestamp.") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)
    return dt


def validate_working_days(days: List[int]) -> List[int]:
    if not days:
        raise ValueError("working_days must not be empty.")
    invalid = [day for day in days if day < 0 or day > 6]
    if invalid:
        raise ValueError(f"working_days contains invalid values: {invalid}")
    deduped = sorted(set(days))
    return deduped


def build_config(args: argparse.Namespace) -> Config:
    tz = parse_timezone(args.timezone)
    business_start = parse_hhmm(args.business_start)
    business_end = parse_hhmm(args.business_end)

    if business_start >= business_end:
        raise ValueError("business_start must be earlier than business_end.")

    if args.sla_hours <= 0:
        raise ValueError("sla_hours must be a positive number.")

    working_days = validate_working_days(args.working_days)
    created_at = parse_iso_datetime(args.created_at, tz, "created_at")
    evaluated_at = (
        parse_iso_datetime(args.evaluated_at, tz, "evaluated_at")
        if args.evaluated_at
        else None
    )

    return Config(
        ticket_id=args.ticket_id,
        created_at=created_at,
        sla_hours=args.sla_hours,
        timezone=args.timezone,
        business_start=business_start,
        business_end=business_end,
        working_days=working_days,
        evaluated_at=evaluated_at,
    )


def combine_local(day: date, local_time: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, local_time).replace(tzinfo=tz)


def is_working_day(day: date, working_days: List[int]) -> bool:
    return day.weekday() in working_days


def next_working_day(day: date, working_days: List[int]) -> date:
    current = day + timedelta(days=1)
    while not is_working_day(current, working_days):
        current += timedelta(days=1)
    return current


def align_to_business_time(dt: datetime, business_start: time, business_end: time, working_days: List[int]) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("Internal error: datetime must be timezone-aware before alignment.")
    tz = dt.tzinfo

    current = dt
    while True:
        current_date = current.date()

        if not is_working_day(current_date, working_days):
            next_day = next_working_day(current_date, working_days)
            current = combine_local(next_day, business_start, tz)
            continue

        start_dt = combine_local(current_date, business_start, tz)
        end_dt = combine_local(current_date, business_end, tz)

        if current < start_dt:
            return start_dt
        if current >= end_dt:
            next_day = next_working_day(current_date, working_days)
            current = combine_local(next_day, business_start, tz)
            continue
        return current


def format_trace_window(start: datetime, end: datetime) -> str:
    weekday = start.strftime("%a")
    return f"{weekday} {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def compute_breach(config: Config) -> Dict[str, Any]:
    tz = parse_timezone(config.timezone)
    current = align_to_business_time(
        config.created_at.astimezone(tz),
        config.business_start,
        config.business_end,
        config.working_days,
    )
    remaining_hours = config.sla_hours
    trace: List[str] = []
    breach_time = None

    if current != config.created_at.astimezone(tz):
        original = config.created_at.astimezone(tz)
        if not is_working_day(original.date(), config.working_days):
            trace.append(
                f"{original.strftime('%a')} skipped: non-working day, counting starts {current.strftime('%a %H:%M')}"
            )
        else:
            start_dt = combine_local(original.date(), config.business_start, tz)
            end_dt = combine_local(original.date(), config.business_end, tz)
            if original < start_dt:
                trace.append(
                    f"{original.strftime('%a %H:%M')} adjusted to business start at {start_dt.strftime('%a %H:%M')}"
                )
            elif original >= end_dt:
                trace.append(
                    f"{original.strftime('%a %H:%M')} adjusted to next working window at {current.strftime('%a %H:%M')}"
                )

    while remaining_hours > 1e-9:
        day = current.date()
        end_of_window = combine_local(day, config.business_end, tz)
        available_hours = (end_of_window - current).total_seconds() / 3600.0

        if remaining_hours <= available_hours + 1e-9:
            breach_time = current + timedelta(hours=remaining_hours)
            counted = round(remaining_hours, 4)
            trace.append(f"{format_trace_window(current, breach_time)} counted: {counted:g}h")
            remaining_hours = 0.0
            break

        counted = round(available_hours, 4)
        trace.append(f"{format_trace_window(current, end_of_window)} counted: {counted:g}h")
        remaining_hours -= available_hours

        next_day = day + timedelta(days=1)
        while not is_working_day(next_day, config.working_days):
            trace.append(f"{next_day.strftime('%a')} skipped: non-working day")
            next_day += timedelta(days=1)

        current = combine_local(next_day, config.business_start, tz)

    status = None
    if config.evaluated_at is not None:
        status = "within_sla" if config.evaluated_at <= breach_time else "breached"

    result = {
        "ticket_id": config.ticket_id,
        "timezone": config.timezone,
        "created_at_local": config.created_at.astimezone(tz).isoformat(),
        "sla_hours": config.sla_hours,
        "business_start": config.business_start.strftime("%H:%M"),
        "business_end": config.business_end.strftime("%H:%M"),
        "working_days": config.working_days,
        "breach_at_local": breach_time.isoformat() if breach_time else None,
        "evaluated_at_local": config.evaluated_at.astimezone(tz).isoformat() if config.evaluated_at else None,
        "status": status,
        "calculation_trace": trace,
    }
    return result


def main() -> None:
    try:
        args = parse_args()
        config = build_config(args)
        result = compute_breach(config)
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
    except ValueError as exc:
        error_payload = {"error": str(exc)}
        print(json.dumps(error_payload, indent=2))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
