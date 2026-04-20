#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import platform
import re
import shutil
import shlex
import subprocess
import sys
from typing import Any
from urllib import error, parse, request


class TravelPlannerError(Exception):
    pass


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise TravelPlannerError(f"Invalid ISO date: {value}") from exc


def read_json(path: str | os.PathLike[str]) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | os.PathLike[str], payload: Any) -> None:
    destination = pathlib.Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_text(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> str:
    req = request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8-sig", "ignore")


def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> Any:
    if params:
        url = f"{url}?{parse.urlencode(params, doseq=True)}"
    body = None
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, headers=req_headers, data=body)
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8-sig", "ignore")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TravelPlannerError(f"Expected JSON from {url}, received non-JSON body") from exc


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return value or "trip"


def normalize_budget_mode(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "hard": "hard_cap",
        "hardcap": "hard_cap",
        "hard_cap": "hard_cap",
        "soft": "soft_target",
        "softtarget": "soft_target",
        "soft_target": "soft_target",
        "none": "no_cap",
        "nocap": "no_cap",
        "no_cap": "no_cap",
    }
    result = aliases.get(normalized)
    if result is None:
        raise TravelPlannerError(
            f"Unsupported budget_mode '{value}'. Use hard_cap, soft_target, or no_cap."
        )
    return result


def normalize_transport_preferences(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items = [value]
    else:
        raw_items = list(value or [])
    normalized: list[str] = []
    aliases = {
        "flight": "flight",
        "plane": "flight",
        "air": "flight",
        "航班": "flight",
        "飞机": "flight",
        "train": "train",
        "rail": "train",
        "火车": "train",
        "高铁": "train",
        "动车": "train",
        "self_drive": "self_drive",
        "self-drive": "self_drive",
        "selfdrive": "self_drive",
        "drive": "self_drive",
        "driving": "self_drive",
        "car": "self_drive",
        "自驾": "self_drive",
        "开车": "self_drive",
        "both": "both",
        "all": "both",
        "都可": "both",
    }
    for item in raw_items:
        key = aliases.get(str(item).strip().lower(), aliases.get(str(item).strip(), str(item).strip()))
        if key == "both":
            normalized.extend(["train", "flight"])
            continue
        if key in {"train", "flight", "self_drive"}:
            normalized.append(key)
    deduped: list[str] = []
    for item in normalized:
        if item not in deduped:
            deduped.append(item)
    return deduped or ["train", "flight"]


def normalize_vehicle_profile(value: Any) -> dict[str, Any] | None:
    if value in (None, "", {}):
        return None
    if not isinstance(value, dict):
        raise TravelPlannerError("vehicle_profile must be an object")
    profile = {
        "powertrain": str(value.get("powertrain") or "gasoline").strip().lower(),
        "consumption_per_100km": float(value["consumption_per_100km"]),
        "unit_price": float(value["unit_price"]),
        "currency": str(value.get("currency") or "CNY"),
    }
    if profile["consumption_per_100km"] <= 0:
        raise TravelPlannerError("vehicle_profile.consumption_per_100km must be positive")
    if profile["unit_price"] <= 0:
        raise TravelPlannerError("vehicle_profile.unit_price must be positive")
    if profile["powertrain"] not in {"gasoline", "diesel", "ev", "phev"}:
        raise TravelPlannerError(
            "vehicle_profile.powertrain must be one of gasoline, diesel, ev, or phev"
        )
    profile["consumption_unit"] = "kWh" if profile["powertrain"] == "ev" else "L"
    if "plate_city" in value and value["plate_city"]:
        profile["plate_city"] = str(value["plate_city"]).strip()
    return profile


def normalize_pet_profile(value: Any) -> dict[str, Any] | None:
    if value in (None, "", {}):
        return None
    if isinstance(value, str):
        return {
            "type": value.strip().lower(),
            "count": 1,
        }
    if not isinstance(value, dict):
        raise TravelPlannerError("pet_profile must be an object")

    profile: dict[str, Any] = {}
    if value.get("type"):
        profile["type"] = str(value["type"]).strip().lower()
    if value.get("size"):
        profile["size"] = str(value["size"]).strip().lower()
    if value.get("count") not in (None, ""):
        profile["count"] = int(value["count"])
        if profile["count"] <= 0:
            raise TravelPlannerError("pet_profile.count must be positive")
    if "needs_pet_friendly_hotel" in value:
        profile["needs_pet_friendly_hotel"] = bool(value["needs_pet_friendly_hotel"])
    if "needs_walking_space" in value:
        profile["needs_walking_space"] = bool(value["needs_walking_space"])
    if "accepts_short_carrier_stays" in value:
        profile["accepts_short_carrier_stays"] = bool(value["accepts_short_carrier_stays"])
    return profile or None


def normalize_city_node(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"city": value.strip()}
    if isinstance(value, dict):
        city = value.get("city") or value.get("name")
        if not city:
            raise TravelPlannerError("City node is missing 'city'")
        node = dict(value)
        node["city"] = str(city).strip()
        node.pop("name", None)
        return node
    raise TravelPlannerError(f"Unsupported city node: {value!r}")


def normalize_travelers(value: Any) -> dict[str, int]:
    if isinstance(value, int):
        if value <= 0:
            raise TravelPlannerError("travelers must be positive")
        return {"adults": value, "children": 0, "infants": 0, "seniors": 0}
    if not isinstance(value, dict):
        raise TravelPlannerError("travelers must be an integer or object")
    travelers = {
        "adults": int(value.get("adults", value.get("count", 0)) or 0),
        "children": int(value.get("children", 0) or 0),
        "infants": int(value.get("infants", 0) or 0),
        "seniors": int(value.get("seniors", 0) or 0),
    }
    if travelers["adults"] <= 0:
        raise TravelPlannerError("At least one adult traveler is required")
    return travelers


def normalize_rooms(value: Any) -> dict[str, int]:
    if isinstance(value, int):
        count = value
    elif isinstance(value, dict):
        count = int(value.get("count", 0) or 0)
    else:
        raise TravelPlannerError("rooms must be an integer or object")
    if count <= 0:
        raise TravelPlannerError("rooms.count must be positive")
    return {"count": count}


def total_travelers(travelers: dict[str, int]) -> int:
    return sum(int(value or 0) for value in travelers.values())


def daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    days = (end - start).days
    return [start + dt.timedelta(days=offset) for offset in range(days + 1)]


def compute_stop_schedule(trip_request: dict[str, Any]) -> list[dict[str, Any]]:
    stops = [dict(item) for item in trip_request["stops"]]
    start = parse_date(trip_request["date_range"]["start"])
    end = parse_date(trip_request["date_range"]["end"])
    total_nights = max((end - start).days, 0)

    specified = 0
    unspecified_indexes: list[int] = []
    for index, stop in enumerate(stops):
        nights = stop.get("nights")
        if nights is None:
            unspecified_indexes.append(index)
            continue
        nights = int(nights)
        if nights < 0:
            raise TravelPlannerError("stop.nights cannot be negative")
        stops[index]["nights"] = nights
        specified += nights

    if specified > total_nights:
        raise TravelPlannerError("Specified stop nights exceed trip duration")

    remaining = max(total_nights - specified, 0)
    if unspecified_indexes:
        base = remaining // len(unspecified_indexes)
        extra = remaining % len(unspecified_indexes)
        for order, index in enumerate(unspecified_indexes):
            stops[index]["nights"] = base + (1 if order < extra else 0)

    cursor = start
    scheduled: list[dict[str, Any]] = []
    for stop in stops:
        nights = int(stop.get("nights", 0))
        departure = cursor + dt.timedelta(days=nights)
        scheduled.append(
            {
                **stop,
                "arrival_date": cursor.isoformat(),
                "departure_date": departure.isoformat(),
                "nights": nights,
            }
        )
        cursor = departure
    if scheduled:
        scheduled[-1]["departure_date"] = end.isoformat()
    return scheduled


def build_trip_segments(trip_request: dict[str, Any]) -> list[dict[str, Any]]:
    schedule = compute_stop_schedule(trip_request)
    origin = trip_request["origin"]["city"]
    segments: list[dict[str, Any]] = []
    if not schedule:
        return segments

    first_stop = schedule[0]["city"]
    if origin != first_stop:
        segments.append(
            {
                "segment_key": f"transport:{slugify(origin)}:{slugify(first_stop)}:{schedule[0]['arrival_date']}",
                "from_city": origin,
                "to_city": first_stop,
                "date": schedule[0]["arrival_date"],
                "kind": "outbound",
            }
        )

    for current, nxt in zip(schedule, schedule[1:]):
        if current["city"] == nxt["city"]:
            continue
        segments.append(
            {
                "segment_key": (
                    f"transport:{slugify(current['city'])}:{slugify(nxt['city'])}:{current['departure_date']}"
                ),
                "from_city": current["city"],
                "to_city": nxt["city"],
                "date": current["departure_date"],
                "kind": "intercity",
            }
        )

    last_stop = schedule[-1]["city"]
    if last_stop != origin:
        segments.append(
            {
                "segment_key": f"transport:{slugify(last_stop)}:{slugify(origin)}:{trip_request['date_range']['end']}",
                "from_city": last_stop,
                "to_city": origin,
                "date": trip_request["date_range"]["end"],
                "kind": "return",
            }
        )
    return segments


def extract_json_object(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def run_command_json(command: str, payload: dict[str, Any], timeout: int = 120) -> Any:
    try:
        completed = subprocess.run(
            shlex.split(command),
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TravelPlannerError(f"Command bridge failed: {exc}") from exc
    stdout = completed.stdout.decode("utf-8", "ignore").strip()
    if not stdout:
        raise TravelPlannerError("Command bridge returned empty stdout")
    try:
        return extract_json_object(stdout)
    except json.JSONDecodeError as exc:
        raise TravelPlannerError("Command bridge returned non-JSON stdout") from exc


def resolve_flyai_bridge() -> dict[str, str | None]:
    command = os.environ.get("FLYAI_OPENCLAW_CMD")
    endpoint = os.environ.get("FLYAI_OPENCLAW_ENDPOINT")
    if command or endpoint:
        return {
            "command": command,
            "endpoint": endpoint,
            "mode": "command" if command else "http",
            "source": "environment",
        }

    bundled_bridge = pathlib.Path(__file__).with_name("flyai_openclaw_bridge.py")
    if bundled_bridge.exists() and shutil.which("flyai"):
        return {
            "command": f"{shlex.quote(sys.executable)} {shlex.quote(str(bundled_bridge))}",
            "endpoint": None,
            "mode": "command",
            "source": "bundled_cli_bridge",
        }

    return {"command": None, "endpoint": None, "mode": None, "source": None}


def keychain_service_name(secret_name: str) -> str:
    return f"codex.verified-travel-planner.{secret_name}"


def read_macos_keychain_secret(secret_name: str) -> str | None:
    if platform.system() != "Darwin":
        return None
    account = os.environ.get("USER") or "codex"
    service = keychain_service_name(secret_name)
    try:
        completed = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                service,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def get_secret(secret_name: str) -> str | None:
    direct = os.environ.get(secret_name)
    if direct:
        return direct
    return read_macos_keychain_secret(secret_name)


def sanitize_money(value: Any) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value or "").strip()
    if not text:
        raise TravelPlannerError("Money value is empty")
    text = re.sub(r"[^0-9.]+", "", text)
    if not text:
        raise TravelPlannerError(f"Cannot parse money value: {value}")
    return round(float(text), 2)


def safe_http_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[Any | None, str | None]:
    try:
        return fetch_json(
            url,
            params=params,
            headers=headers,
            payload=payload,
            timeout=timeout,
        ), None
    except (TravelPlannerError, error.URLError, error.HTTPError, TimeoutError) as exc:
        return None, str(exc)
