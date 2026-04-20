#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys

from _travel_common import get_secret, iso_now, resolve_flyai_bridge, safe_http_json, write_json


def check_binary(name: str) -> dict[str, object]:
    path = shutil.which(name)
    return {"available": bool(path), "path": path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Path to dependency-report.json")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Return success even when live providers are not fully configured",
    )
    args = parser.parse_args()

    flyai_bridge = resolve_flyai_bridge()
    amap_key = get_secret("AMAP_WEB_SERVICE_KEY")

    report = {
        "generated_at": iso_now(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
        },
        "checks": {
            "pandoc": check_binary("pandoc"),
            "weasyprint": check_binary("weasyprint"),
            "flyai_openclaw": {
                "configured": bool(flyai_bridge["command"] or flyai_bridge["endpoint"]),
                "mode": flyai_bridge["mode"],
                "source": flyai_bridge["source"],
                "command": flyai_bridge["command"],
                "endpoint": flyai_bridge["endpoint"],
            },
            "amap_web_service": {
                "configured": bool(amap_key),
                "key_present": bool(amap_key),
                "source": "env_or_keychain" if amap_key else None,
            },
            "12306_official_query": {
                "reachable": False,
                "station_catalog": False,
                "notes": [],
            },
        },
        "summary": {},
    }

    station_url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
    station_response, station_error = safe_http_json(
        "https://search.12306.cn/search/v1/train/search",
        params={"keyword": "北京"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    if station_response is not None:
        report["checks"]["12306_official_query"]["reachable"] = True
    else:
        report["checks"]["12306_official_query"]["notes"].append(
            f"Train search endpoint was not reachable as JSON: {station_error}"
        )

    try:
        import urllib.request

        with urllib.request.urlopen(station_url, timeout=15) as response:
            body = response.read(80).decode("utf-8-sig", "ignore")
        report["checks"]["12306_official_query"]["station_catalog"] = bool(body.startswith("var station_names"))
    except Exception as exc:  # pragma: no cover - best effort probe
        report["checks"]["12306_official_query"]["notes"].append(
            f"Failed to load station catalog: {exc}"
        )

    pdf_ready = report["checks"]["pandoc"]["available"] and report["checks"]["weasyprint"]["available"]
    provider_ready = report["checks"]["flyai_openclaw"]["configured"] and report["checks"]["amap_web_service"]["configured"]
    report["summary"] = {
        "pdf_ready": bool(pdf_ready),
        "verified_quote_ready": bool(provider_ready),
        "train_best_effort_ready": bool(
            report["checks"]["12306_official_query"]["station_catalog"]
        ),
        "ready_for_verified_run": bool(pdf_ready and provider_ready),
    }

    write_json(args.output, report)
    if args.allow_partial or report["summary"]["ready_for_verified_run"]:
        return 0
    parser.exit(1, "[ERROR] Live provider or PDF dependencies are incomplete\n")


if __name__ == "__main__":
    raise SystemExit(main())
