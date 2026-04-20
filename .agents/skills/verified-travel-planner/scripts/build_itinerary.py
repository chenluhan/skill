#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from _travel_common import (
    TravelPlannerError,
    build_trip_segments,
    compute_stop_schedule,
    daterange,
    parse_date,
    read_json,
    slugify,
    write_json,
)


BUDGET_CATEGORIES = {"flight", "hotel", "ticket", "train"}


def primary_sort_key(quote: dict[str, Any]) -> tuple[Any, ...]:
    metadata = quote.get("metadata") or {}
    return (
        0 if metadata.get("recommended") else 1,
        int(metadata.get("preference_rank", 50)),
        float(quote["total_price"]),
    )


def budget_sort_key(quote: dict[str, Any]) -> tuple[Any, ...]:
    metadata = quote.get("metadata") or {}
    return (
        float(quote["total_price"]),
        int(metadata.get("preference_rank", 50)),
        0 if metadata.get("recommended") else 1,
    )


def collect_expected_segments(trip_request: dict[str, Any]) -> list[dict[str, str]]:
    schedule = trip_request.get("stop_schedule") or compute_stop_schedule(trip_request)
    expected = []
    for segment in build_trip_segments(trip_request):
        expected.append({"segment_key": segment["segment_key"], "category": "transport"})
    for stop in schedule:
        if int(stop.get("nights", 0)) > 0:
            expected.append(
                {
                    "segment_key": f"hotel:{slugify(stop['city'])}:{stop['arrival_date']}:{stop['departure_date']}",
                    "category": "hotel",
                }
            )
    return expected


def choose_bundle(
    grouped_quotes: dict[str, list[dict[str, Any]]], sort_key
) -> dict[str, dict[str, Any]]:
    selection = {}
    for segment_key, quotes in grouped_quotes.items():
        if not quotes:
            continue
        selection[segment_key] = sorted(quotes, key=sort_key)[0]
    return selection


def total_bundle(selection: dict[str, dict[str, Any]]) -> float:
    return round(sum(float(item["total_price"]) for item in selection.values()), 2)


def distinct_selection(
    primary: dict[str, dict[str, Any]],
    budget: dict[str, dict[str, Any]],
) -> bool:
    return any(
        primary.get(key, {}).get("product_name") != budget.get(key, {}).get("product_name")
        or float(primary.get(key, {}).get("total_price", 0))
        != float(budget.get(key, {}).get("total_price", 0))
        for key in set(primary) | set(budget)
    )


def find_current_stop(schedule: list[dict[str, Any]], target_date) -> dict[str, Any]:
    for index, stop in enumerate(schedule):
        arrival = parse_date(stop["arrival_date"])
        departure = parse_date(stop["departure_date"])
        if index < len(schedule) - 1 and arrival <= target_date < departure:
            return stop
        if index == len(schedule) - 1 and arrival <= target_date <= departure:
            return stop
    return schedule[-1]


def build_day_plans(
    trip_request: dict[str, Any],
    quotes_envelope: dict[str, Any],
) -> list[dict[str, Any]]:
    schedule = trip_request.get("stop_schedule") or compute_stop_schedule(trip_request)
    poi_by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for poi in quotes_envelope.get("poi_hits", []):
        poi_by_city[poi["city"]].append(poi)

    route_by_segment = {
        item["segment_key"]: item for item in quotes_envelope.get("route_snapshots", [])
    }
    transport_segments = {item["segment_key"]: item for item in build_trip_segments(trip_request)}

    days = []
    all_dates = daterange(
        parse_date(trip_request["date_range"]["start"]),
        parse_date(trip_request["date_range"]["end"]),
    )
    for day_index, current_date in enumerate(all_dates, start=1):
        stop = find_current_stop(schedule, current_date)
        city_pois = poi_by_city.get(stop["city"], [])
        morning = city_pois[0]["name"] if city_pois else "自由活动"
        afternoon = city_pois[1]["name"] if len(city_pois) > 1 else "酒店入住或机动安排"
        notes = []

        for segment_key, segment in transport_segments.items():
            if segment["date"] != current_date.isoformat():
                continue
            route = route_by_segment.get(segment_key)
            transport_prefix = "自驾" if (
                (route and route.get("transport_mode") == "self_drive")
                or trip_request["transport_preferences"] == ["self_drive"]
            ) else "前往"
            transport_note = f"{transport_prefix} {segment['from_city']} -> {segment['to_city']}"
            if route:
                transport_note += f"（高德约 {route['duration_minutes']} 分钟 / {route['distance_km']} km）"
            notes.append(transport_note)
            if segment["to_city"] == stop["city"]:
                if transport_prefix == "自驾":
                    morning = f"从 {segment['from_city']} 自驾到 {segment['to_city']}"
                else:
                    morning = f"从 {segment['from_city']} 前往 {segment['to_city']}"
        if day_index == 1 and trip_request["origin"]["city"] != stop["city"]:
            if trip_request["transport_preferences"] == ["self_drive"]:
                morning = f"从 {trip_request['origin']['city']} 自驾到 {stop['city']}"
            else:
                morning = f"从 {trip_request['origin']['city']} 出发前往 {stop['city']}"
        if current_date.isoformat() == trip_request["date_range"]["end"] and stop["city"] != trip_request["origin"]["city"]:
            prefix = "自驾返回" if trip_request["transport_preferences"] == ["self_drive"] else "返回"
            afternoon = f"{prefix} {trip_request['origin']['city']}"

        days.append(
            {
                "date": current_date.isoformat(),
                "city": stop["city"],
                "morning": morning,
                "afternoon": afternoon,
                "evening": "自由安排",
                "notes": notes,
            }
        )
    return days


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trip-request", required=True, help="Path to trip-request.json")
    parser.add_argument("--quotes", required=True, help="Path to quote-records.json")
    parser.add_argument("--output", required=True, help="Path to itinerary-manifest.json")
    args = parser.parse_args()

    trip_request = read_json(args.trip_request)
    quotes_envelope = read_json(args.quotes)

    verified_quotes = [
        item
        for item in quotes_envelope.get("quotes", [])
        if item.get("verification_status") == "verified" and item.get("category") in BUDGET_CATEGORIES
    ]
    grouped_quotes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for quote in verified_quotes:
        grouped_quotes[quote["segment_key"]].append(quote)

    primary_selection = choose_bundle(grouped_quotes, primary_sort_key)
    budget_selection = choose_bundle(grouped_quotes, budget_sort_key)
    primary_total = total_bundle(primary_selection)
    budget_total = total_bundle(budget_selection)

    expected_segment_keys = {item["segment_key"] for item in collect_expected_segments(trip_request)}
    existing_unverified = list(quotes_envelope.get("unverified_items", []))
    covered_segment_keys = set(primary_selection)
    self_drive_estimate_keys = {
        item["segment_key"]
        for item in quotes_envelope.get("quotes", [])
        if item.get("category") == "self_drive"
    }
    for segment_key in expected_segment_keys - covered_segment_keys:
        if not any(item["segment_key"] == segment_key for item in existing_unverified):
            reason = "No verified offer available for this required segment"
            category = "budget_item"
            if "self_drive" in trip_request["transport_preferences"]:
                category = "self_drive"
                if segment_key in self_drive_estimate_keys:
                    reason = (
                        "Only a self-drive estimate is available for this segment. It stays outside "
                        "the accurate budget until a fully verifiable cost source exists."
                    )
                else:
                    reason = (
                        "Self-drive was requested, but this segment does not have a verified transport "
                        "quote and therefore is not counted in the accurate budget."
                    )
            existing_unverified.append(
                {
                    "segment_key": segment_key,
                    "category": category,
                    "provider": "unknown",
                    "reason": reason,
                    "source_ref": None,
                }
            )

    selected_primary_offers = list(primary_selection.values())
    selected_budget_offers = list(budget_selection.values())
    self_drive_estimates = [
        item
        for item in quotes_envelope.get("quotes", [])
        if item.get("category") == "self_drive"
    ]

    booking_links = [
        item["booking_url"] or item["source_ref"]
        for item in selected_primary_offers
        if item.get("booking_url") or item.get("source_ref")
    ]
    evidence_refs = [
        item["source_ref"] for item in selected_primary_offers if item.get("source_ref")
    ]
    evidence_refs.extend(
        item.get("source_ref")
        for item in quotes_envelope.get("route_snapshots", [])
        if item.get("source_ref")
    )

    coverage_status = "complete" if not existing_unverified else "partial"
    budget_target = trip_request.get("budget_target")
    alternatives = []
    if (
        trip_request["budget_mode"] != "no_cap"
        and distinct_selection(primary_selection, budget_selection)
    ):
        alternatives.append(
            {
                "label": "cheaper-alternative",
                "total_price": budget_total,
                "selected_offers": selected_budget_offers,
            }
        )

    manifest = {
        "summary": {
            "origin": trip_request["origin"]["city"],
            "stops": [stop["city"] for stop in trip_request["stop_schedule"]],
            "date_range": trip_request["date_range"],
            "trip_days": trip_request["trip_days"],
            "travelers": trip_request["travelers"],
            "budget_mode": trip_request["budget_mode"],
            "budget_target": budget_target,
            "coverage_status": coverage_status,
            "primary_total": primary_total,
            "budget_total": budget_total,
            "within_budget": (
                None
                if budget_target is None or existing_unverified
                else primary_total <= float(budget_target)
            ),
            "warnings": quotes_envelope.get("warnings", []),
        },
        "stop_order": [stop["city"] for stop in trip_request["stop_schedule"]],
        "day_plans": build_day_plans(trip_request, quotes_envelope),
        "verified_budget": {
            "currency": trip_request["currency"],
            "primary_total": primary_total,
            "selected_offers": selected_primary_offers,
            "cheapest_total": budget_total,
        },
        "unverified_items": existing_unverified,
        "booking_links": sorted(set(link for link in booking_links if link)),
        "evidence_refs": sorted(set(link for link in evidence_refs if link)),
        "alternatives": alternatives,
        "route_snapshots": quotes_envelope.get("route_snapshots", []),
        "poi_hits": quotes_envelope.get("poi_hits", []),
        "self_drive_summary": quotes_envelope.get("self_drive_summary"),
        "self_drive_estimates": self_drive_estimates,
    }

    write_json(args.output, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
