#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from typing import Any
from urllib import parse

from _travel_common import (
    TravelPlannerError,
    build_trip_segments,
    compute_stop_schedule,
    fetch_json,
    get_secret,
    iso_now,
    read_json,
    read_text,
    run_command_json,
    safe_http_json,
    sanitize_money,
    slugify,
    resolve_flyai_bridge,
    write_json,
)


TRAIN_PRICE_CODES = {
    "A9": "商务座",
    "P": "特等座",
    "M": "一等座",
    "O": "二等座",
    "A6": "高级软卧",
    "A4": "软卧",
    "F": "动卧",
    "A3": "硬卧",
    "A2": "软座",
    "A1": "硬座",
    "WZ": "无座",
}


def add_unverified(
    envelope: dict[str, Any],
    *,
    category: str,
    provider: str,
    segment_key: str,
    reason: str,
    source_ref: str | None = None,
) -> None:
    envelope["unverified_items"].append(
        {
            "segment_key": segment_key,
            "category": category,
            "provider": provider,
            "reason": reason,
            "source_ref": source_ref,
            "queried_at": iso_now(),
        }
    )


def build_flyai_requests(trip_request: dict[str, Any]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    schedule = trip_request.get("stop_schedule") or compute_stop_schedule(trip_request)

    if "flight" in trip_request["transport_preferences"]:
        for segment in build_trip_segments(trip_request):
            requests.append(
                {
                    "segment_key": segment["segment_key"],
                    "category": "flight",
                    "origin": segment["from_city"],
                    "destination": segment["to_city"],
                    "date": segment["date"],
                    "travelers": trip_request["travelers"],
                }
            )

    for stop in schedule:
        if int(stop.get("nights", 0)) <= 0:
            continue
        requests.append(
            {
                "segment_key": (
                    f"hotel:{slugify(stop['city'])}:{stop['arrival_date']}:{stop['departure_date']}"
                ),
                "category": "hotel",
                "city": stop["city"],
                "check_in": stop["arrival_date"],
                "check_out": stop["departure_date"],
                "rooms": trip_request["rooms"],
                "travelers": trip_request["travelers"],
                "hotel_level": trip_request["hotel_level"],
            }
        )

    default_city = schedule[0]["city"] if schedule else trip_request["origin"]["city"]
    ticket_targets: list[dict[str, str]] = []
    for stop in schedule:
        for item in stop.get("must_see", []):
            ticket_targets.append({"city": stop["city"], "name": str(item)})
    for item in trip_request.get("must_see", []):
        if isinstance(item, dict):
            ticket_targets.append(
                {"city": str(item.get("city") or default_city), "name": str(item.get("name"))}
            )
        else:
            ticket_targets.append({"city": default_city, "name": str(item)})

    seen_targets: set[tuple[str, str]] = set()
    for target in ticket_targets:
        dedupe_key = (target["city"], target["name"])
        if dedupe_key in seen_targets:
            continue
        seen_targets.add(dedupe_key)
        requests.append(
            {
                "segment_key": f"ticket:{slugify(target['city'])}:{slugify(target['name'])}",
                "category": "ticket",
                "city": target["city"],
                "keyword": target["name"],
                "date": trip_request["date_range"]["start"],
                "travelers": trip_request["travelers"],
            }
        )
    return requests


def call_flyai_bridge(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    bridge = resolve_flyai_bridge()
    command = bridge["command"]
    endpoint = bridge["endpoint"]
    token = get_secret("FLYAI_OPENCLAW_TOKEN")
    if not command and not endpoint:
        return [], (
            "FLYAI_OPENCLAW_CMD or FLYAI_OPENCLAW_ENDPOINT is not configured, "
            "and no bundled flyai CLI bridge was available"
        )

    try:
        if command:
            response = run_command_json(command, payload)
        else:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = fetch_json(endpoint, headers=headers, payload=payload, timeout=90)
    except Exception as exc:
        return [], str(exc)

    offers = response.get("offers", []) if isinstance(response, dict) else []
    if not isinstance(offers, list):
        return [], "FlyAI bridge returned invalid offers payload"
    return offers, None


def normalize_offer(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "segment_key": raw["segment_key"],
        "category": raw["category"],
        "provider": raw.get("provider") or "flyai_openclaw",
        "product_name": raw["product_name"],
        "source_ref": raw["source_ref"],
        "queried_at": raw.get("queried_at") or iso_now(),
        "unit_price": sanitize_money(raw["unit_price"]),
        "total_price": sanitize_money(raw["total_price"]),
        "currency": raw.get("currency") or "CNY",
        "conditions": raw.get("conditions") or {},
        "verification_status": raw.get("verification_status") or "verified",
        "traveler_scope": raw.get("traveler_scope") or {},
        "booking_url": raw.get("booking_url"),
        "metadata": raw.get("metadata") or {},
    }


def add_flyai_quotes(envelope: dict[str, Any], trip_request: dict[str, Any]) -> None:
    requests = build_flyai_requests(trip_request)
    bridge = resolve_flyai_bridge()
    envelope["provider_status"]["flyai_openclaw"] = {
        "configured": bool(bridge["command"] or bridge["endpoint"]),
        "mode": bridge["mode"],
        "source": bridge["source"],
        "requested_segments": len(requests),
    }
    if not requests:
        envelope["provider_status"]["flyai_openclaw"]["reason"] = "No flight/hotel/ticket segments required"
        return

    offers, error_message = call_flyai_bridge({"trip_request": trip_request, "requests": requests})
    if error_message:
        envelope["provider_status"]["flyai_openclaw"]["error"] = error_message
        for item in requests:
            add_unverified(
                envelope,
                category=item["category"],
                provider="flyai_openclaw",
                segment_key=item["segment_key"],
                reason=error_message,
            )
        return

    accepted = 0
    for raw_offer in offers:
        try:
            quote = normalize_offer(raw_offer)
        except Exception as exc:
            add_unverified(
                envelope,
                category=raw_offer.get("category", "unknown"),
                provider="flyai_openclaw",
                segment_key=raw_offer.get("segment_key", "unknown"),
                reason=f"Incomplete offer payload: {exc}",
                source_ref=raw_offer.get("source_ref"),
            )
            continue
        if not quote["source_ref"]:
            add_unverified(
                envelope,
                category=quote["category"],
                provider=quote["provider"],
                segment_key=quote["segment_key"],
                reason="Offer missing source_ref",
            )
            continue
        if quote["verification_status"] != "verified":
            reason = (
                quote["metadata"].get("verification_reason")
                or quote["conditions"].get("verification_reason")
                or "Offer was not verified by the provider"
            )
            add_unverified(
                envelope,
                category=quote["category"],
                provider=quote["provider"],
                segment_key=quote["segment_key"],
                reason=str(reason),
                source_ref=quote["source_ref"],
            )
            continue
        envelope["quotes"].append(quote)
        accepted += 1
    envelope["provider_status"]["flyai_openclaw"]["accepted_offers"] = accepted


def geocode_city(city: str, amap_key: str) -> dict[str, Any] | None:
    payload, error_message = safe_http_json(
        "https://restapi.amap.com/v3/geocode/geo",
        params={"key": amap_key, "address": city},
        timeout=20,
    )
    if payload is None or str(payload.get("status")) != "1" or not payload.get("geocodes"):
        return None
    geocode = payload["geocodes"][0]
    return {
        "city": city,
        "formatted_address": geocode.get("formatted_address"),
        "location": geocode.get("location"),
    }


def recommendation_queries(stop: dict[str, Any], trip_request: dict[str, Any]) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    styles = set(trip_request.get("trip_style_tags") or [])
    traveler_needs = set(trip_request.get("traveler_needs") or [])
    explicit_targets = [str(item) for item in stop.get("must_see", []) if str(item).strip()]

    def add_query(keyword: str, cluster: str, reason: str, priority: int) -> None:
        candidate = {
            "keyword": keyword,
            "cluster": cluster,
            "reason": reason,
            "priority": priority,
        }
        if candidate not in queries:
            queries.append(candidate)

    for index, item in enumerate(explicit_targets):
        add_query(item, "must_see", "用户明确点名的目的地锚点", index)

    if not explicit_targets:
        if not styles or "scenery" in styles or "relaxation" in styles:
            add_query("古城", "scenic", "适合作为目的地慢逛锚点", 0)
            add_query("公园", "scenic", "低门槛风景点，适合留出机动时间", 1)
            add_query("风景区", "scenic", "补充代表性景观点", 2)
        if "culture" in styles:
            add_query("古城", "culture", "补充当地人文和历史氛围", 0)
            add_query("博物馆", "culture", "补充室内文化点位", 2)
        if "food" in styles:
            add_query("美食街", "food", "补充适合晚上觅食的区域", 1)
            add_query("小吃", "food", "补充本地特色小吃区域", 2)
        if "photo" in styles:
            add_query("观景台", "photo", "补充适合拍照出片的点位", 2)
        if traveler_needs & {"family_friendly", "child_friendly", "infant_friendly", "stroller_friendly"}:
            add_query("公园", "family", "优先平缓、低折腾的公共空间", 0)
            add_query("古城", "family", "补充适合推车慢逛的街区", 1)

    return queries[:6]


def score_recommendation_candidate(
    *,
    poi_name: str,
    cluster: str,
    priority: int,
    trip_request: dict[str, Any],
    address: Any,
) -> int:
    score = 100 - priority * 10
    if "self_drive" in trip_request.get("transport_preferences", []):
        score += 4
    if cluster == "food":
        score -= 6
    if not address:
        score -= 3

    traveler_needs = set(trip_request.get("traveler_needs") or [])
    if traveler_needs & {"infant_friendly", "child_friendly", "senior_friendly", "stroller_friendly"}:
        for keyword, penalty in {
            "山": 16,
            "索道": 20,
            "峡谷": 18,
            "徒步": 20,
            "漂流": 20,
        }.items():
            if keyword in poi_name:
                score -= penalty
    return score


def build_candidate_clusters(recommended_pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    labels = {
        "must_see": "明确想去",
        "scenic": "风景",
        "culture": "人文",
        "family": "亲子友好",
        "food": "觅食区域",
        "photo": "拍照",
    }
    for item in recommended_pois:
        grouped[item["cluster"]].append(item["name"])
    return [
        {
            "cluster": cluster,
            "label": labels.get(cluster, cluster),
            "items": names,
        }
        for cluster, names in grouped.items()
    ]


def add_amap_context(envelope: dict[str, Any], trip_request: dict[str, Any]) -> None:
    amap_key = get_secret("AMAP_WEB_SERVICE_KEY")
    envelope["provider_status"]["amap_route_poi"] = {"configured": bool(amap_key)}
    if not amap_key:
        envelope["warnings"].append("AMAP_WEB_SERVICE_KEY is missing; route evidence was skipped.")
        return

    schedule = trip_request.get("stop_schedule") or compute_stop_schedule(trip_request)
    cities = {trip_request["origin"]["city"], *(stop["city"] for stop in schedule)}
    geo_index: dict[str, dict[str, Any]] = {}
    for city in cities:
        geocode = geocode_city(city, amap_key)
        if geocode:
            geo_index[city] = geocode

    envelope["provider_status"]["amap_route_poi"]["geocoded_cities"] = sorted(geo_index)
    poi_hits: list[dict[str, Any]] = []
    recommended_candidates: list[dict[str, Any]] = []
    for stop in schedule:
        queries = recommendation_queries(stop, trip_request)
        for query in queries:
            keyword = query["keyword"]
            payload, error_message = safe_http_json(
                "https://restapi.amap.com/v3/place/text",
                params={
                    "key": amap_key,
                    "keywords": keyword,
                    "city": stop["city"],
                    "citylimit": "true",
                    "offset": 3,
                },
                timeout=20,
            )
            if payload is None or str(payload.get("status")) != "1":
                if error_message:
                    envelope["warnings"].append(f"Amap POI lookup failed for {stop['city']}/{keyword}: {error_message}")
                continue
            for poi in payload.get("pois", [])[:2]:
                source_ref = (
                    "https://uri.amap.com/search?keyword="
                    + parse.quote(str(keyword))
                    + "&city="
                    + parse.quote(stop["city"])
                )
                hit = {
                    "city": stop["city"],
                    "keyword": keyword,
                    "cluster": query["cluster"],
                    "name": poi.get("name"),
                    "address": poi.get("address"),
                    "location": poi.get("location"),
                    "source_ref": source_ref,
                }
                poi_hits.append(hit)
                if not hit["name"]:
                    continue
                recommended_candidates.append(
                    {
                        **hit,
                        "reason": query["reason"],
                        "score": score_recommendation_candidate(
                            poi_name=str(hit["name"]),
                            cluster=query["cluster"],
                            priority=int(query["priority"]),
                            trip_request=trip_request,
                            address=hit["address"],
                        ),
                        "route_fit": (
                            "self_drive_friendly"
                            if "self_drive" in trip_request.get("transport_preferences", [])
                            else "standard"
                        ),
                        "traveler_fit": list(trip_request.get("traveler_needs") or []),
                    }
                )

    route_snapshots: list[dict[str, Any]] = []
    route_mode = "self_drive" if trip_request["transport_preferences"] == ["self_drive"] else "driving"
    for segment in build_trip_segments(trip_request):
        origin_geo = geo_index.get(segment["from_city"])
        destination_geo = geo_index.get(segment["to_city"])
        if not origin_geo or not destination_geo:
            continue
        payload, error_message = safe_http_json(
            "https://restapi.amap.com/v3/direction/driving",
            params={
                "key": amap_key,
                "origin": origin_geo["location"],
                "destination": destination_geo["location"],
                "strategy": 0,
            },
            timeout=20,
        )
        if payload is None or str(payload.get("status")) != "1" or not payload.get("route", {}).get("paths"):
            if error_message:
                envelope["warnings"].append(
                    f"Amap route lookup failed for {segment['from_city']}->{segment['to_city']}: {error_message}"
                )
            continue
        path = payload["route"]["paths"][0]
        route_snapshots.append(
            {
                "segment_key": segment["segment_key"],
                "from_city": segment["from_city"],
                "to_city": segment["to_city"],
                "distance_km": round(float(path.get("distance", 0)) / 1000, 1),
                "duration_minutes": round(float(path.get("duration", 0)) / 60),
                "tolls": sanitize_money(path.get("tolls", 0) or 0),
                "strategy": path.get("strategy"),
                "transport_mode": route_mode,
                "source_ref": (
                    "https://uri.amap.com/navigation?from="
                    + parse.quote(origin_geo["location"])
                    + "&to="
                    + parse.quote(destination_geo["location"])
                    + "&mode=car"
                ),
            }
        )

    deduped_recommendations: list[dict[str, Any]] = []
    seen_recommendation_keys: set[tuple[str, str]] = set()
    seen_base_names: set[tuple[str, str]] = set()
    for candidate in sorted(recommended_candidates, key=lambda item: (-int(item["score"]), item["name"])):
        dedupe_key = (candidate["city"], candidate["name"])
        if dedupe_key in seen_recommendation_keys:
            continue
        base_name = str(candidate["name"]).split("-", 1)[0].strip()
        base_key = (candidate["city"], base_name)
        if base_key in seen_base_names and base_name != candidate["name"]:
            continue
        seen_recommendation_keys.add(dedupe_key)
        seen_base_names.add(base_key)
        deduped_recommendations.append(candidate)
    recommended_pois = deduped_recommendations[:6]

    envelope["poi_hits"] = poi_hits
    envelope["recommended_pois"] = recommended_pois
    envelope["candidate_clusters"] = build_candidate_clusters(recommended_pois)
    envelope["route_snapshots"] = route_snapshots


def add_self_drive_context(envelope: dict[str, Any], trip_request: dict[str, Any]) -> None:
    if "self_drive" not in trip_request["transport_preferences"]:
        return

    route_snapshots = {
        item["segment_key"]: item for item in envelope.get("route_snapshots", [])
    }
    profile = trip_request.get("vehicle_profile")
    summary = {
        "enabled": True,
        "has_vehicle_profile": bool(profile),
        "segments": [],
        "estimated_total": None,
        "currency": trip_request.get("currency") or "CNY",
    }
    estimated_total = 0.0

    for segment in build_trip_segments(trip_request):
        route = route_snapshots.get(segment["segment_key"])
        if route is None:
            add_unverified(
                envelope,
                category="self_drive",
                provider="amap_route_poi",
                segment_key=segment["segment_key"],
                reason="Self-drive requested but no Amap route snapshot was available for this segment",
                source_ref="https://lbs.amap.com/api/webservice/guide/api/direction",
            )
            continue

        segment_summary = {
            "segment_key": segment["segment_key"],
            "from_city": segment["from_city"],
            "to_city": segment["to_city"],
            "distance_km": route["distance_km"],
            "duration_minutes": route["duration_minutes"],
            "tolls": route.get("tolls", 0),
            "source_ref": route["source_ref"],
        }

        if profile:
            energy_cost = round(
                float(route["distance_km"]) * float(profile["consumption_per_100km"]) / 100.0
                * float(profile["unit_price"]),
                2,
            )
            estimated_total_segment = round(energy_cost + float(route.get("tolls", 0) or 0), 2)
            segment_summary["vehicle_profile"] = {
                "powertrain": profile["powertrain"],
                "consumption_per_100km": profile["consumption_per_100km"],
                "unit_price": profile["unit_price"],
                "consumption_unit": profile["consumption_unit"],
            }
            segment_summary["energy_cost_estimate"] = energy_cost
            segment_summary["estimated_total"] = estimated_total_segment
            estimated_total += estimated_total_segment

            envelope["quotes"].append(
                {
                    "segment_key": segment["segment_key"],
                    "category": "self_drive",
                    "provider": "amap_route_poi",
                    "product_name": f"自驾 {segment['from_city']} -> {segment['to_city']}",
                    "source_ref": route["source_ref"],
                    "queried_at": iso_now(),
                    "unit_price": estimated_total_segment,
                    "total_price": estimated_total_segment,
                    "currency": trip_request.get("currency") or "CNY",
                    "conditions": {
                        "distance_km": route["distance_km"],
                        "duration_minutes": route["duration_minutes"],
                        "tolls": route.get("tolls", 0),
                        "powertrain": profile["powertrain"],
                        "consumption_per_100km": profile["consumption_per_100km"],
                        "unit_price": profile["unit_price"],
                    },
                    "verification_status": "estimated",
                    "traveler_scope": trip_request["travelers"],
                    "booking_url": route["source_ref"],
                    "metadata": {
                        "budget_included": False,
                        "estimation_basis": "Amap route tolls + user vehicle profile",
                    },
                }
            )
        else:
            add_unverified(
                envelope,
                category="self_drive",
                provider="amap_route_poi",
                segment_key=segment["segment_key"],
                reason=(
                    "Self-drive route is available, but accurate cost is still open because "
                    "vehicle_profile is missing. Supply consumption_per_100km and unit_price "
                    "to generate an estimate outside the accurate budget."
                ),
                source_ref=route["source_ref"],
            )

        summary["segments"].append(segment_summary)

    if profile and summary["segments"]:
        summary["estimated_total"] = round(estimated_total, 2)
    envelope["self_drive_summary"] = summary


def load_12306_catalog() -> list[dict[str, str]]:
    js = read_text(
        "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    if "var station_names" not in js:
        raise TravelPlannerError("12306 station catalog format changed")
    raw = js.split("='", 1)[1].split("';", 1)[0]
    catalog: list[dict[str, str]] = []
    for chunk in raw.split("@"):
        if not chunk:
            continue
        fields = chunk.split("|")
        if len(fields) < 8:
            continue
        catalog.append(
            {
                "short": fields[0],
                "name": fields[1],
                "telecode": fields[2],
                "pinyin": fields[3],
                "abbr": fields[4],
                "city": fields[7],
            }
        )
    return catalog


def lookup_station(city_name: str, catalog: list[dict[str, str]]) -> dict[str, str] | None:
    candidates = []
    cleaned = city_name.replace("市", "").strip()
    for station in catalog:
        if station["name"] == city_name or station["name"] == cleaned:
            return station
        if station["city"] == city_name or station["city"] == cleaned:
            candidates.append(station)
    if candidates:
        preferred = [item for item in candidates if item["name"] in {city_name, cleaned}]
        return (preferred or candidates)[0]
    return None


def seat_preference_rank(train_code: str, seat_code: str) -> int:
    fast_order = ["O", "M", "P", "A9", "F", "A4", "A6", "WZ", "A1"]
    regular_order = ["A1", "A3", "A4", "A2", "WZ", "O", "M", "P", "A9"]
    order = fast_order if train_code.startswith(("G", "D", "C")) else regular_order
    try:
        return order.index(seat_code)
    except ValueError:
        return 99


def parse_12306_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("result"), list):
        return []
    return []


def add_12306_quotes(envelope: dict[str, Any], trip_request: dict[str, Any]) -> None:
    envelope["provider_status"]["12306_official_query"] = {
        "enabled": "train" in trip_request["transport_preferences"],
        "queried_segments": 0,
    }
    if "train" not in trip_request["transport_preferences"]:
        return

    if trip_request["travelers"].get("children", 0) or trip_request["travelers"].get("infants", 0):
        for segment in build_trip_segments(trip_request):
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason=(
                    "12306 public fare only verifies adult pricing. Child or infant train fares "
                    "require passenger-specific rules, so this segment is not counted as accurate."
                ),
                source_ref="https://kyfw.12306.cn/otn/leftTicketPrice/init",
            )
        envelope["provider_status"]["12306_official_query"]["reason"] = (
            "Skipped because child or infant passengers were present."
        )
        return

    try:
        catalog = load_12306_catalog()
    except Exception as exc:
        for segment in build_trip_segments(trip_request):
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason=f"Failed to load 12306 station catalog: {exc}",
            )
        return

    for segment in build_trip_segments(trip_request):
        envelope["provider_status"]["12306_official_query"]["queried_segments"] += 1
        from_station = lookup_station(segment["from_city"], catalog)
        to_station = lookup_station(segment["to_city"], catalog)
        if not from_station or not to_station:
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason="Unable to map city name to 12306 station telecode",
                source_ref="https://kyfw.12306.cn/otn/resources/js/framework/station_name.js",
            )
            continue

        query_payload, error_message = safe_http_json(
            "https://kyfw.12306.cn/otn/leftTicket/query",
            params={
                "leftTicketDTO.train_date": segment["date"],
                "leftTicketDTO.from_station": from_station["telecode"],
                "leftTicketDTO.to_station": to_station["telecode"],
                "purpose_codes": "ADULT",
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=20,
        )
        if query_payload is None:
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason=f"12306 train query failed: {error_message}",
                source_ref="https://kyfw.12306.cn/otn/leftTicket/init",
            )
            continue

        rows = parse_12306_rows(query_payload)
        candidates = []
        for row in rows[:10]:
            dto = row.get("queryLeftNewDTO", row)
            if not isinstance(dto, dict):
                continue
            if not all(
                dto.get(key)
                for key in (
                    "train_no",
                    "station_train_code",
                    "from_station_telecode",
                    "to_station_telecode",
                    "seat_types",
                )
            ):
                continue
            candidates.append(dto)
            if len(candidates) >= 3:
                break

        if not candidates:
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason="12306 did not return usable train rows",
                source_ref="https://kyfw.12306.cn/otn/leftTicket/init",
            )
            continue

        added = 0
        for candidate in candidates:
            price_payload, price_error = safe_http_json(
                "https://kyfw.12306.cn/otn/leftTicketPrice/queryPublicPrice",
                params={
                    "train_no": candidate["train_no"],
                    "train_code": candidate["station_train_code"],
                    "from_station_telecode": candidate["from_station_telecode"],
                    "to_station_telecode": candidate["to_station_telecode"],
                    "seat_types": candidate["seat_types"],
                    "train_date": segment["date"],
                },
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://kyfw.12306.cn/otn/leftTicketPrice/init",
                },
                timeout=20,
            )
            if price_payload is None or not price_payload.get("status"):
                continue
            fare_block = price_payload.get("data") or {}
            for seat_code, seat_name in TRAIN_PRICE_CODES.items():
                seat_price = fare_block.get(seat_code)
                if seat_price in (None, ""):
                    continue
                passenger_count = int(trip_request["travelers"].get("adults", 0)) + int(
                    trip_request["travelers"].get("seniors", 0)
                )
                unit_price = sanitize_money(seat_price)
                envelope["quotes"].append(
                    {
                        "segment_key": segment["segment_key"],
                        "category": "train",
                        "provider": "12306_official_query",
                        "product_name": f"{candidate['station_train_code']} {seat_name}",
                        "source_ref": "https://kyfw.12306.cn/otn/leftTicketPrice/init",
                        "queried_at": iso_now(),
                        "unit_price": unit_price,
                        "total_price": round(unit_price * passenger_count, 2),
                        "currency": "CNY",
                        "conditions": {
                            "seat_type": seat_name,
                            "train_code": candidate["station_train_code"],
                            "start_time": candidate.get("start_time"),
                            "arrive_time": candidate.get("arrive_time"),
                            "duration": candidate.get("lishi"),
                        },
                        "verification_status": "verified",
                        "traveler_scope": {
                            "adults": trip_request["travelers"].get("adults", 0),
                            "seniors": trip_request["travelers"].get("seniors", 0),
                        },
                        "booking_url": "https://kyfw.12306.cn/otn/leftTicket/init",
                        "metadata": {
                            "preference_rank": seat_preference_rank(
                                candidate["station_train_code"], seat_code
                            )
                        },
                    }
                )
                added += 1
        if added == 0:
            add_unverified(
                envelope,
                category="train",
                provider="12306_official_query",
                segment_key=segment["segment_key"],
                reason="12306 fare query returned no usable public fares",
                source_ref="https://kyfw.12306.cn/otn/leftTicketPrice/init",
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Normalized trip-request.json")
    parser.add_argument("--output", required=True, help="Path to quote-records.json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if no verified budget quotes were collected",
    )
    args = parser.parse_args()

    trip_request = read_json(args.input)
    envelope: dict[str, Any] = {
        "trip_request_ref": args.input,
        "queried_at": iso_now(),
        "quotes": [],
        "route_snapshots": [],
        "poi_hits": [],
        "provider_status": {},
        "warnings": [],
        "unverified_items": [],
    }

    add_flyai_quotes(envelope, trip_request)
    add_amap_context(envelope, trip_request)
    add_self_drive_context(envelope, trip_request)
    add_12306_quotes(envelope, trip_request)

    grouped: dict[str, int] = defaultdict(int)
    for quote in envelope["quotes"]:
        grouped[quote["category"]] += 1
    envelope["summary"] = {
        "quote_counts": dict(grouped),
        "verified_budget_quotes": len(
            [
                item
                for item in envelope["quotes"]
                if item["category"] in {"flight", "hotel", "ticket", "train"}
                and item["verification_status"] == "verified"
            ]
        ),
    }

    write_json(args.output, envelope)
    if args.strict and envelope["summary"]["verified_budget_quotes"] == 0:
        parser.exit(1, "[ERROR] No verified budget quotes were collected\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
