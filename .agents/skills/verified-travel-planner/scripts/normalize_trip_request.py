#!/usr/bin/env python3

from __future__ import annotations

import argparse
from typing import Any

from _travel_common import (
    TravelPlannerError,
    compute_stop_schedule,
    normalize_budget_mode,
    normalize_city_node,
    normalize_rooms,
    normalize_transport_preferences,
    normalize_travelers,
    normalize_vehicle_profile,
    parse_date,
    read_json,
    total_travelers,
    write_json,
)


ALIASES = {
    "from": "origin",
    "origin_city": "origin",
    "destination": "stops",
    "destinations": "stops",
    "start_date": "date_range.start",
    "depart_date": "date_range.start",
    "end_date": "date_range.end",
    "return_date": "date_range.end",
}


def merge_aliases(raw: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw)
    for old_key, new_key in ALIASES.items():
        if old_key not in result or new_key in result:
            continue
        value = result.pop(old_key)
        if "." not in new_key:
            result[new_key] = value
            continue
        parent, child = new_key.split(".", 1)
        result.setdefault(parent, {})
        result[parent][child] = value
    return result


def normalize_must_see(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def normalize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = merge_aliases(raw)
    origin = payload.get("origin")
    stops = payload.get("stops")
    date_range = payload.get("date_range")
    budget_mode = payload.get("budget_mode")
    transport_preferences = payload.get("transport_preferences")

    if origin is None:
        raise TravelPlannerError("Missing required field: origin")
    if not stops:
        raise TravelPlannerError("Missing required field: stops")
    if not date_range:
        raise TravelPlannerError("Missing required field: date_range")
    if budget_mode is None:
        raise TravelPlannerError("Missing required field: budget_mode")
    if transport_preferences is None:
        raise TravelPlannerError("Missing required field: transport_preferences")

    normalized_stops = stops if isinstance(stops, list) else [stops]
    normalized_stops = [normalize_city_node(item) for item in normalized_stops]
    if not 1 <= len(normalized_stops) <= 3:
        raise TravelPlannerError("stops must contain between 1 and 3 cities")

    start = parse_date(date_range.get("start"))
    end = parse_date(date_range.get("end"))
    if end < start:
        raise TravelPlannerError("date_range.end must be on or after date_range.start")

    normalized = {
        "origin": normalize_city_node(origin),
        "stops": normalized_stops,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "travelers": normalize_travelers(payload.get("travelers")),
        "rooms": normalize_rooms(payload.get("rooms")),
        "budget_mode": normalize_budget_mode(budget_mode),
        "budget_target": payload.get("budget_target"),
        "hotel_level": str(payload.get("hotel_level") or "midscale"),
        "transport_preferences": normalize_transport_preferences(transport_preferences),
        "must_see": normalize_must_see(payload.get("must_see")),
        "constraints": payload.get("constraints") or [],
        "vehicle_profile": normalize_vehicle_profile(payload.get("vehicle_profile")),
        "pace": str(payload.get("pace") or "morning-anchor-afternoon-anchor-free-evening"),
        "currency": str(payload.get("currency") or "CNY"),
        "notes": payload.get("notes") or "",
    }

    if normalized["budget_mode"] != "no_cap":
        if normalized["budget_target"] in (None, ""):
            raise TravelPlannerError("budget_target is required unless budget_mode is no_cap")
        normalized["budget_target"] = float(normalized["budget_target"])
    else:
        normalized["budget_target"] = None

    if total_travelers(normalized["travelers"]) <= 0:
        raise TravelPlannerError("travelers must sum to at least one traveler")

    normalized["trip_days"] = (end - start).days + 1
    normalized["trip_nights"] = max(normalized["trip_days"] - 1, 0)
    normalized["stop_schedule"] = compute_stop_schedule(normalized)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to raw request JSON")
    parser.add_argument("--output", required=True, help="Path to normalized trip-request.json")
    args = parser.parse_args()

    try:
        raw = read_json(args.input)
        normalized = normalize_payload(raw)
        write_json(args.output, normalized)
    except (TravelPlannerError, OSError, ValueError) as exc:
        parser.exit(1, f"[ERROR] {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
