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

STYLE_ALIASES = {
    "scenery": "scenery",
    "风景": "scenery",
    "看风景": "scenery",
    "自然": "scenery",
    "food": "food",
    "美食": "food",
    "吃": "food",
    "吃特色": "food",
    "culture": "culture",
    "文化": "culture",
    "人文": "culture",
    "古城": "culture",
    "history": "culture",
    "photo": "photo",
    "拍照": "photo",
    "拍照打卡": "photo",
    "打卡": "photo",
    "family": "family",
    "亲子": "family",
    "family_trip": "family",
    "relaxation": "relaxation",
    "休闲": "relaxation",
    "放空": "relaxation",
}

PACE_ALIASES = {
    "relaxed": "relaxed",
    "轻松": "relaxed",
    "慢一点": "relaxed",
    "休闲": "relaxed",
    "balanced": "balanced",
    "适中": "balanced",
    "正常": "balanced",
    "morning-anchor-afternoon-anchor-free-evening": "balanced",
    "dense": "dense",
    "紧凑": "dense",
    "高密度": "dense",
    "暴走": "dense",
    "morning-anchor-afternoon-anchor-evening-anchor": "dense",
}

PACE_TEMPLATES = {
    "relaxed": "morning-anchor-afternoon-anchor-free-evening",
    "balanced": "morning-anchor-afternoon-anchor-free-evening",
    "dense": "morning-anchor-afternoon-anchor-evening-anchor",
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


def normalize_string_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        values = [raw]
    else:
        values = list(raw)
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def infer_trip_style_tags(payload: dict[str, Any]) -> tuple[list[str], str]:
    explicit = normalize_string_list(payload.get("trip_style_tags"))
    tags: list[str] = []
    source = "default"
    for item in explicit:
        normalized = STYLE_ALIASES.get(item.lower(), STYLE_ALIASES.get(item))
        if normalized and normalized not in tags:
            tags.append(normalized)
    if tags:
        source = "explicit"

    texts = normalize_string_list(payload.get("constraints"))
    texts.append(str(payload.get("notes") or ""))
    texts.extend(str(item) for item in normalize_must_see(payload.get("must_see")))
    joined = " ".join(texts)
    keyword_map = {
        "scenery": ["风景", "自然", "景色", "湖", "海", "山", "看风景"],
        "food": ["美食", "小吃", "吃", "特色"],
        "culture": ["古城", "人文", "文化", "历史", "古镇", "博物馆"],
        "photo": ["拍照", "打卡", "出片"],
        "family": ["亲子", "宝宝", "婴儿", "儿童", "家庭"],
        "relaxation": ["休闲", "放空", "松弛", "慢一点"],
    }
    for tag, keywords in keyword_map.items():
        if tag in tags:
            continue
        if any(keyword in joined for keyword in keywords):
            tags.append(tag)
            if source == "default":
                source = "inferred"
    return tags, source


def derive_traveler_needs(payload: dict[str, Any], travelers: dict[str, int]) -> tuple[list[str], str]:
    needs: list[str] = []
    source = "default"

    def add_need(value: str, inferred_source: str) -> None:
        nonlocal source
        if value not in needs:
            needs.append(value)
        if source == "default":
            source = inferred_source

    if travelers.get("infants", 0) > 0:
        for item in ("infant_friendly", "stroller_friendly", "nap_friendly", "low_transfer"):
            add_need(item, "inferred")
    elif travelers.get("children", 0) > 0:
        for item in ("child_friendly", "family_friendly", "low_transfer"):
            add_need(item, "inferred")
    if travelers.get("seniors", 0) > 0:
        for item in ("senior_friendly", "low_transfer"):
            add_need(item, "inferred")

    joined = " ".join(normalize_string_list(payload.get("constraints")) + [str(payload.get("notes") or "")])
    keyword_map = {
        "family_friendly": ["亲子", "家庭"],
        "low_transfer": ["少折腾", "少换酒店", "低折腾", "不赶"],
        "flat_walking": ["不爬山", "少走路", "平缓"],
        "slow_start": ["不早起", "晚点出门"],
        "parking_friendly": ["自驾", "开车"],
    }
    for need, keywords in keyword_map.items():
        if any(keyword in joined for keyword in keywords):
            add_need(need, "inferred")
    return needs, source


def normalize_pace_preference(payload: dict[str, Any]) -> tuple[str, str, str]:
    raw = str(payload.get("pace_preference") or payload.get("pace") or "").strip()
    if raw:
        normalized = PACE_ALIASES.get(raw.lower(), PACE_ALIASES.get(raw))
        if normalized:
            return normalized, PACE_TEMPLATES[normalized], "explicit"

    joined = " ".join(normalize_string_list(payload.get("constraints")) + [str(payload.get("notes") or "")])
    inferred_keywords = {
        "relaxed": ["轻松", "休闲", "慢一点", "不赶", "不早起"],
        "dense": ["高密度", "紧凑", "多玩点", "暴走"],
    }
    for pace_preference, keywords in inferred_keywords.items():
        if any(keyword in joined for keyword in keywords):
            return pace_preference, PACE_TEMPLATES[pace_preference], "inferred"
    return "balanced", PACE_TEMPLATES["balanced"], "default"


def build_followup_questions(missing_fields: list[str]) -> list[str]:
    question_map = {
        "trip_style_tags": "这趟更偏风景、美食、休闲放空、拍照打卡，还是人文古城？",
        "traveler_needs": "同行人有没有老人、小孩、婴儿，或者不想爬山、少折腾这类执行约束？",
        "pace_preference": "你希望每天节奏偏轻松、适中，还是尽量多看点？",
    }
    return [question_map[field] for field in missing_fields if field in question_map]


def assess_recommendation_state(
    normalized: dict[str, Any],
    *,
    pace_source: str,
) -> tuple[str, str, list[str], list[str]]:
    missing: list[str] = []
    if not normalized["must_see"] and not normalized["trip_style_tags"]:
        missing.append("trip_style_tags")
    if (
        not normalized["must_see"]
        and not normalized["traveler_needs"]
        and normalized["travelers"].get("children", 0) == 0
        and normalized["travelers"].get("infants", 0) == 0
        and normalized["travelers"].get("seniors", 0) == 0
    ):
        missing.append("traveler_needs")
    if not normalized["must_see"] and pace_source == "default":
        missing.append("pace_preference")

    if normalized["must_see"]:
        confidence = "high"
    elif not missing:
        confidence = "high" if pace_source != "default" and normalized["trip_style_tags"] else "medium"
    elif len(missing) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    intake_status = "needs_followup" if len(missing) >= 2 and not normalized["must_see"] else "ready_for_recommendation"
    return intake_status, confidence, missing, build_followup_questions(missing)


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
        "currency": str(payload.get("currency") or "CNY"),
        "notes": payload.get("notes") or "",
    }

    trip_style_tags, _ = infer_trip_style_tags(payload)
    traveler_needs, _ = derive_traveler_needs(payload, normalized["travelers"])
    pace_preference, pace_template, pace_source = normalize_pace_preference(payload)
    normalized["trip_style_tags"] = trip_style_tags
    normalized["traveler_needs"] = traveler_needs
    normalized["pace_preference"] = pace_preference
    normalized["pace"] = pace_template

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
    (
        normalized["intake_status"],
        normalized["recommendation_confidence"],
        normalized["missing_preference_fields"],
        normalized["followup_questions"],
    ) = assess_recommendation_state(normalized, pace_source=pace_source)
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
