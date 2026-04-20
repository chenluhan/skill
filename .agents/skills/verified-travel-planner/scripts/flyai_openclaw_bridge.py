#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from typing import Any

from _travel_common import TravelPlannerError, extract_json_object, iso_now, sanitize_money


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise TravelPlannerError("Bridge stdin was empty")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TravelPlannerError("Bridge stdin was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise TravelPlannerError("Bridge payload must be a JSON object")
    return payload


def run_flyai(args: list[str]) -> dict[str, Any]:
    if not shutil.which("flyai"):
        raise TravelPlannerError("flyai CLI is not installed or not on PATH")
    completed = subprocess.run(
        ["flyai", *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise TravelPlannerError(f"flyai command failed: {stderr}")
    stdout = completed.stdout.strip()
    if not stdout:
        raise TravelPlannerError("flyai command returned empty stdout")
    try:
        payload = extract_json_object(stdout)
    except json.JSONDecodeError as exc:
        raise TravelPlannerError("flyai command returned non-JSON stdout") from exc
    if not isinstance(payload, dict):
        raise TravelPlannerError("flyai response must be a JSON object")
    return payload


def traveler_counts(request_item: dict[str, Any]) -> tuple[int, int, int]:
    travelers = request_item.get("travelers") or {}
    adults = int(travelers.get("adults", 0) or 0) + int(travelers.get("seniors", 0) or 0)
    children = int(travelers.get("children", 0) or 0)
    infants = int(travelers.get("infants", 0) or 0)
    return adults, children, infants


def verified_traveler_scope(request_item: dict[str, Any]) -> dict[str, int]:
    travelers = request_item.get("travelers") or {}
    return {
        "adults": int(travelers.get("adults", 0) or 0),
        "children": 0,
        "infants": 0,
        "seniors": int(travelers.get("seniors", 0) or 0),
    }


def make_unverified_offer(
    request_item: dict[str, Any],
    *,
    reason: str,
    source_ref: str | None = None,
) -> dict[str, Any]:
    return {
        "segment_key": request_item["segment_key"],
        "category": request_item["category"],
        "provider": "flyai_openclaw",
        "product_name": f"{request_item['category']} quote unavailable",
        "source_ref": source_ref or "https://flyai.open.fliggy.com/docs/quickstart",
        "queried_at": iso_now(),
        "unit_price": 0,
        "total_price": 0,
        "currency": "CNY",
        "conditions": {"verification_reason": reason},
        "verification_status": "unverified",
        "traveler_scope": request_item.get("travelers") or {},
        "booking_url": source_ref,
        "metadata": {"verification_reason": reason},
    }


def normalize_hotel_offer(request_item: dict[str, Any], item: dict[str, Any], index: int) -> dict[str, Any]:
    nights = (dt.date.fromisoformat(request_item["check_out"]) - dt.date.fromisoformat(request_item["check_in"])).days
    rooms = int((request_item.get("rooms") or {}).get("count", 1) or 1)
    nightly_price = sanitize_money(item["price"])
    total_price = round(nightly_price * max(nights, 1) * rooms, 2)
    return {
        "segment_key": request_item["segment_key"],
        "category": "hotel",
        "provider": "flyai_openclaw",
        "product_name": item["name"],
        "source_ref": item["detailUrl"],
        "queried_at": iso_now(),
        "unit_price": nightly_price,
        "total_price": total_price,
        "currency": "CNY",
        "conditions": {
            "city": request_item["city"],
            "check_in": request_item["check_in"],
            "check_out": request_item["check_out"],
            "nights": nights,
            "rooms": rooms,
            "address": item.get("address"),
            "star": item.get("star"),
            "brand": item.get("brandName"),
            "price_basis": "per room per night",
        },
        "verification_status": "verified",
        "traveler_scope": request_item.get("travelers") or {},
        "booking_url": item["detailUrl"],
        "metadata": {
            "recommended": index == 0,
            "hotel_id": item.get("shId"),
            "main_pic": item.get("mainPic"),
        },
    }


def search_hotels(request_item: dict[str, Any], trip_request: dict[str, Any]) -> list[dict[str, Any]]:
    command = [
        "search-hotel",
        "--dest-name",
        request_item["city"],
        "--check-in-date",
        request_item["check_in"],
        "--check-out-date",
        request_item["check_out"],
        "--sort",
        "price_asc" if trip_request.get("budget_mode") != "no_cap" else "rate_desc",
    ]
    payload = run_flyai(command)
    items = ((payload.get("data") or {}).get("itemList") or [])[:5]
    offers = []
    for index, item in enumerate(items):
        if not item.get("detailUrl") or item.get("price") in (None, ""):
            continue
        offers.append(normalize_hotel_offer(request_item, item, index))
    if offers:
        return offers
    return [
        make_unverified_offer(
            request_item,
            reason="FlyAI hotel search returned no usable priced hotel results",
        )
    ]


def first_segment(item: dict[str, Any]) -> dict[str, Any] | None:
    journeys = item.get("journeys") or []
    if not journeys:
        return None
    segments = (journeys[0] or {}).get("segments") or []
    return segments[0] if segments else None


def search_flights(request_item: dict[str, Any]) -> list[dict[str, Any]]:
    adults, children, infants = traveler_counts(request_item)
    if children or infants:
        return [
            make_unverified_offer(
                request_item,
                reason=(
                    "FlyAI flight search currently returns adult fare lines. Child or infant pricing "
                    "needs passenger-specific verification, so this segment is excluded from the "
                    "accurate budget."
                ),
            )
        ]

    payload = run_flyai(
        [
            "search-flight",
            "--origin",
            request_item["origin"],
            "--destination",
            request_item["destination"],
            "--dep-date",
            request_item["date"],
            "--sort-type",
            "3",
        ]
    )
    items = ((payload.get("data") or {}).get("itemList") or [])[:5]
    offers = []
    for index, item in enumerate(items):
        segment = first_segment(item)
        jump_url = item.get("jumpUrl")
        price = item.get("ticketPrice") or item.get("adultPrice")
        if segment is None or not jump_url or price in (None, ""):
            continue
        unit_price = sanitize_money(price)
        offers.append(
            {
                "segment_key": request_item["segment_key"],
                "category": "flight",
                "provider": "flyai_openclaw",
                "product_name": (
                    f"{segment.get('marketingTransportName', '航班')} "
                    f"{segment.get('marketingTransportNo', '').strip()} "
                    f"{segment.get('seatClassName', '').strip()}".strip()
                ),
                "source_ref": jump_url,
                "queried_at": iso_now(),
                "unit_price": unit_price,
                "total_price": round(unit_price * adults, 2),
                "currency": "CNY",
                "conditions": {
                    "dep_city": request_item["origin"],
                    "destination": request_item["destination"],
                    "dep_date": request_item["date"],
                    "dep_time": segment.get("depDateTime"),
                    "arr_time": segment.get("arrDateTime"),
                    "duration_minutes": item.get("totalDuration"),
                    "seat_class": segment.get("seatClassName"),
                    "journey_type": (item.get("journeys") or [{}])[0].get("journeyType"),
                },
                "verification_status": "verified",
                "traveler_scope": verified_traveler_scope(request_item),
                "booking_url": jump_url,
                "metadata": {"recommended": index == 0},
            }
        )
    if offers:
        return offers
    return [
        make_unverified_offer(
            request_item,
            reason="FlyAI flight search returned no usable priced flight results",
        )
    ]


def normalize_ticket_offer(request_item: dict[str, Any], item: dict[str, Any], index: int) -> dict[str, Any]:
    adults, _, _ = traveler_counts(request_item)
    ticket_info = item.get("ticketInfo") or {}
    free_status = str(item.get("freePoiStatus") or "").upper()
    if ticket_info.get("price") not in (None, ""):
        unit_price = sanitize_money(ticket_info["price"])
        verification_status = "verified"
    elif free_status == "FREE":
        unit_price = 0.0
        verification_status = "verified"
    else:
        return make_unverified_offer(
            request_item,
            reason="FlyAI attraction result did not include a verifiable ticket price",
            source_ref=item.get("jumpUrl"),
        )

    return {
        "segment_key": request_item["segment_key"],
        "category": "ticket",
        "provider": "flyai_openclaw",
        "product_name": ticket_info.get("ticketName") or item.get("name") or request_item["keyword"],
        "source_ref": item["jumpUrl"],
        "queried_at": iso_now(),
        "unit_price": unit_price,
        "total_price": round(unit_price * adults, 2),
        "currency": "CNY",
        "conditions": {
            "city": request_item["city"],
            "poi_name": item.get("name"),
            "address": item.get("address"),
            "ticket_name": ticket_info.get("ticketName"),
            "price_date": ticket_info.get("priceDate"),
            "free_poi_status": item.get("freePoiStatus"),
        },
        "verification_status": verification_status,
        "traveler_scope": verified_traveler_scope(request_item),
        "booking_url": item["jumpUrl"],
        "metadata": {
            "recommended": index == 0,
            "main_pic": item.get("mainPic"),
        },
    }


def search_tickets(request_item: dict[str, Any]) -> list[dict[str, Any]]:
    adults, children, infants = traveler_counts(request_item)
    if children or infants:
        return [
            make_unverified_offer(
                request_item,
                reason=(
                    "FlyAI attraction pricing currently verifies adult ticket lines only. Child or "
                    "infant ticket policy may differ by attraction, so this segment is excluded "
                    "from the accurate budget."
                ),
            )
        ]

    payload = run_flyai(
        [
            "search-poi",
            "--city-name",
            request_item["city"],
            "--keyword",
            request_item["keyword"],
        ]
    )
    items = ((payload.get("data") or {}).get("itemList") or [])[:5]
    offers = []
    for index, item in enumerate(items):
        if not item.get("jumpUrl"):
            continue
        offer = normalize_ticket_offer(request_item, item, index)
        if offer.get("verification_status") == "verified":
            offers.append(offer)
    if offers:
        return offers
    return [
        make_unverified_offer(
            request_item,
            reason="FlyAI attraction search returned no usable ticket price",
        )
    ]


def collect_offers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    trip_request = payload.get("trip_request") or {}
    requests = payload.get("requests") or []
    offers: list[dict[str, Any]] = []
    for request_item in requests:
        category = request_item.get("category")
        try:
            if category == "hotel":
                offers.extend(search_hotels(request_item, trip_request))
            elif category == "flight":
                offers.extend(search_flights(request_item))
            elif category == "ticket":
                offers.extend(search_tickets(request_item))
            else:
                offers.append(
                    make_unverified_offer(
                        request_item,
                        reason=f"Unsupported flyai bridge category: {category}",
                    )
                )
        except Exception as exc:
            offers.append(
                make_unverified_offer(
                    request_item,
                    reason=str(exc),
                )
            )
    return offers


def main() -> int:
    try:
        payload = read_payload()
        offers = collect_offers(payload)
    except Exception as exc:
        message = str(exc) if isinstance(exc, TravelPlannerError) else repr(exc)
        print(json.dumps({"offers": [], "error": message}, ensure_ascii=False))
        return 1

    print(json.dumps({"offers": offers}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
