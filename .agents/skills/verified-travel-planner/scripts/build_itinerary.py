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


def recommendation_label(cluster: str) -> str:
    return {
        "must_see": "明确想去",
        "scenic": "风景",
        "culture": "人文",
        "family": "亲子友好",
        "food": "觅食区域",
        "photo": "拍照",
    }.get(cluster, cluster)


def effective_recommendations(quotes_envelope: dict[str, Any]) -> list[dict[str, Any]]:
    recommended = list(quotes_envelope.get("recommended_pois") or [])
    if recommended:
        return recommended
    fallback: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in quotes_envelope.get("poi_hits", []):
        key = (item["city"], item["name"])
        if not item.get("name") or key in seen:
            continue
        seen.add(key)
        fallback.append(
            {
                "city": item["city"],
                "name": item["name"],
                "cluster": item.get("cluster") or "scenic",
                "reason": "当前按目的地通用 POI 结果补足候选锚点。",
                "address": item.get("address"),
                "location": item.get("location"),
                "source_ref": item.get("source_ref"),
                "traveler_fit": [],
                "route_fit": "standard",
            }
        )
    return fallback[:6]


def next_recommendation(
    city: str,
    recommendation_pool: dict[str, list[dict[str, Any]]],
    indexes: dict[str, int],
    *,
    repeat_last: bool = False,
) -> dict[str, Any] | None:
    items = recommendation_pool.get(city) or []
    if not items:
        return None
    index = indexes.get(city, 0)
    if index >= len(items):
        if not repeat_last:
            return None
        index = len(items) - 1
    indexes[city] = min(index + 1, len(items))
    return items[index]


def build_selection_rationale(
    trip_request: dict[str, Any],
    recommended_pois: list[dict[str, Any]],
) -> list[str]:
    rationale = []
    if trip_request.get("must_see"):
        rationale.append("优先保留了用户明确点名的目的地锚点。")
    elif recommended_pois:
        rationale.append("用户没有明确 must-see，因此先用真实 POI 数据生成候选锚点，再按画像筛选。")

    if trip_request.get("trip_style_tags"):
        rationale.append(
            "本次推荐重点围绕："
            + "、".join(str(tag) for tag in trip_request["trip_style_tags"])
            + "。"
        )
    if trip_request.get("traveler_needs"):
        rationale.append(
            "执行层优先照顾："
            + "、".join(str(item) for item in trip_request["traveler_needs"])
            + "。"
        )
    if "self_drive" in trip_request.get("transport_preferences", []):
        rationale.append("因为选择了自驾，默认更偏向顺路、少回头、停车更友好的锚点。")
    pace = trip_request.get("pace_preference") or "balanced"
    pace_text = {
        "relaxed": "轻松",
        "balanced": "适中",
        "dense": "高密度",
    }.get(pace, pace)
    rationale.append(f"每日节奏按“{pace_text}”口径排布，而不是把所有热门点机械塞满。")
    return rationale


def build_day_plans(
    trip_request: dict[str, Any],
    quotes_envelope: dict[str, Any],
) -> list[dict[str, Any]]:
    schedule = trip_request.get("stop_schedule") or compute_stop_schedule(trip_request)
    recommendations = effective_recommendations(quotes_envelope)
    anchor_by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    food_by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for poi in recommendations:
        if poi.get("cluster") == "food":
            food_by_city[poi["city"]].append(poi)
        else:
            anchor_by_city[poi["city"]].append(poi)

    route_by_segment = {
        item["segment_key"]: item for item in quotes_envelope.get("route_snapshots", [])
    }
    transport_segments = {item["segment_key"]: item for item in build_trip_segments(trip_request)}
    anchor_indexes: dict[str, int] = defaultdict(int)
    food_indexes: dict[str, int] = defaultdict(int)
    pace = trip_request.get("pace_preference") or "balanced"

    days = []
    all_dates = daterange(
        parse_date(trip_request["date_range"]["start"]),
        parse_date(trip_request["date_range"]["end"]),
    )
    for day_index, current_date in enumerate(all_dates, start=1):
        stop = find_current_stop(schedule, current_date)
        fallback_anchor = (anchor_by_city.get(stop["city"]) or [None])[0]
        notes = []
        travel_in = None
        travel_out = None
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
                travel_in = {"prefix": transport_prefix, "segment": segment}
            if (
                current_date.isoformat() == trip_request["date_range"]["end"]
                and segment["from_city"] == stop["city"]
                and segment["to_city"] == trip_request["origin"]["city"]
            ):
                travel_out = {"prefix": transport_prefix, "segment": segment}

        first_anchor = next_recommendation(stop["city"], anchor_by_city, anchor_indexes)
        second_anchor = None
        if pace in {"balanced", "dense"} and not travel_in and not travel_out:
            second_anchor = next_recommendation(stop["city"], anchor_by_city, anchor_indexes)
            if (
                second_anchor
                and first_anchor
                and second_anchor.get("name") == first_anchor.get("name")
            ):
                second_anchor = None
        food_anchor = next_recommendation(
            stop["city"],
            food_by_city,
            food_indexes,
            repeat_last=True,
        )

        morning = first_anchor["name"] if first_anchor else "自由活动"
        if pace == "relaxed":
            afternoon = "午休 / 机动安排 / 沿途慢逛"
        else:
            afternoon = second_anchor["name"] if second_anchor else "酒店入住或机动安排"
        evening = f"自由觅食：{food_anchor['name']}" if food_anchor else "自由安排"
        if not first_anchor and fallback_anchor:
            morning = f"围绕{fallback_anchor['name']} 低密度慢逛"
            if pace != "relaxed":
                afternoon = f"围绕{fallback_anchor['name']} 机动安排"

        if travel_in:
            segment = travel_in["segment"]
            if travel_in["prefix"] == "自驾":
                morning = f"从 {segment['from_city']} 自驾到 {segment['to_city']}"
            else:
                morning = f"从 {segment['from_city']} 前往 {segment['to_city']}"
            afternoon = first_anchor["name"] if first_anchor else "入住酒店 / 机动安排"
        elif day_index == 1 and trip_request["origin"]["city"] != stop["city"]:
            if trip_request["transport_preferences"] == ["self_drive"]:
                morning = f"从 {trip_request['origin']['city']} 自驾到 {stop['city']}"
            else:
                morning = f"从 {trip_request['origin']['city']} 出发前往 {stop['city']}"

        if travel_out:
            prefix = "自驾返回" if trip_request["transport_preferences"] == ["self_drive"] else "返回"
            afternoon = f"{prefix} {trip_request['origin']['city']}"
        used_recommendations = []
        for anchor in (first_anchor, second_anchor):
            if not anchor:
                continue
            if morning == anchor["name"] or afternoon == anchor["name"]:
                used_recommendations.append(anchor)
        if food_anchor and food_anchor["name"] in evening:
            used_recommendations.append(food_anchor)
        for anchor in used_recommendations:
            notes.append(
                f"推荐理由：{anchor['name']} 属于{recommendation_label(str(anchor.get('cluster')))}，{anchor.get('reason')}"
            )
        if trip_request.get("intake_status") == "needs_followup":
            notes.append("当前偏好 intake 仍偏薄，目的地锚点按默认推荐口径生成。")

        days.append(
            {
                "date": current_date.isoformat(),
                "city": stop["city"],
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening,
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
    evidence_refs.extend(
        item.get("source_ref")
        for item in effective_recommendations(quotes_envelope)
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
            "intake_status": trip_request.get("intake_status"),
            "recommendation_confidence": trip_request.get("recommendation_confidence"),
            "missing_preference_fields": trip_request.get("missing_preference_fields", []),
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
        "recommended_pois": effective_recommendations(quotes_envelope),
        "candidate_clusters": quotes_envelope.get("candidate_clusters", []),
        "selection_rationale": build_selection_rationale(
            trip_request,
            effective_recommendations(quotes_envelope),
        ),
        "followup_questions_asked": trip_request.get("followup_questions", []),
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
