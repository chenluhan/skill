---
name: verified-travel-planner
description: Verify and plan China domestic trips with live quotes, route evidence, self-drive routing, and PDF export. Use when Codex needs to clarify travel requirements, normalize them into `trip-request.json`, collect real hotel/flight/ticket quotes from configured providers, verify train prices against 12306 official channels, route stops with Amap, estimate self-drive segments from Amap plus vehicle inputs, or generate a travel itinerary PDF with evidence and unverified-item warnings.
---

# Verified Travel Planner

## Overview

Use this skill to turn a vague domestic travel request into a verified itinerary package. Optimize for trustworthy budget math, not inspirational copy.

## Non-Negotiable Rules

- Refuse to query prices before the required trip fields are complete.
- Keep the accurate budget limited to `transport + hotel + attraction tickets`.
- Exclude any quote that does not include `source_ref`, `queried_at`, and enough conditions to explain what was priced.
- Treat train fares as dynamic until verified through `12306` official channels.
- Treat self-drive as `route verified first, cost estimated second`. Do not fold self-drive into the accurate total unless a future version has a fully verifiable cost source.
- Never describe the budget as accurate when `unverified_items` is non-empty.

## Required Inputs

Confirm these fields before you call any quote script:

- `origin`
- `stops[]` with at most 3 stops
- `date_range.start`
- `date_range.end`
- `travelers`
- `rooms`
- `budget_mode`
- `transport_preferences`

Fill these defaults when the user does not care:

- `hotel_level = "midscale"`
- `pace = "morning-anchor-afternoon-anchor-free-evening"`
- `currency = "CNY"`
- `must_see = []`
- `constraints = []`

Optional self-drive fields:

- `vehicle_profile.powertrain`
- `vehicle_profile.consumption_per_100km`
- `vehicle_profile.unit_price`

When `vehicle_profile` is missing, still build the self-drive route but keep the cost outside the accurate budget.

## Workflow

### 1. Check the environment

Run:

```bash
python3 scripts/check_dependencies.py --output <run-dir>/dependency-report.json --allow-partial
```

Read [references/provider-contracts.md](references/provider-contracts.md) before wiring providers.

### 2. Normalize the request

Write a loose request JSON, then normalize it:

```bash
python3 scripts/normalize_trip_request.py \
  --input <run-dir>/raw-request.json \
  --output <run-dir>/trip-request.json
```

Use [references/data-contracts.md](references/data-contracts.md) when deciding field shapes.

### 3. Collect live quotes

Run:

```bash
python3 scripts/collect_live_quotes.py \
  --input <run-dir>/trip-request.json \
  --output <run-dir>/quote-records.json
```

Provider priority:

- `flyai_openclaw` for flight / hotel / attraction ticket offers
- `amap_route_poi` for coordinates, POIs, route snapshots, tolls, and self-drive evidence
- `12306_official_query` for train fares
- `elong_hotel` only as a later fallback extension

If a provider is missing, write the failure into the output. Do not hide it.

### 4. Build the itinerary

Run:

```bash
python3 scripts/build_itinerary.py \
  --trip-request <run-dir>/trip-request.json \
  --quotes <run-dir>/quote-records.json \
  --output <run-dir>/itinerary-manifest.json
```

Use the primary bundle for the main plan. When budget mode is `hard_cap` or `soft_target`, also try to produce a cheaper alternative from the verified offers.

If `transport_preferences` contains `self_drive`, also surface:

- route distance and duration
- Amap tolls
- optional self-drive estimate based on `vehicle_profile`

Keep that estimate outside `verified_budget`.

### 5. Render the PDF

Run:

```bash
python3 scripts/render_trip_pdf.py \
  --trip-request <run-dir>/trip-request.json \
  --quotes <run-dir>/quote-records.json \
  --input <run-dir>/itinerary-manifest.json \
  --output-dir <run-dir>
```

Expected outputs:

- `itinerary-report.md`
- `itinerary-report.html`
- `export/itinerary.pdf`

If PDF export fails, keep the markdown and HTML and report the exact blocker.

## Failure Handling

- If required trip inputs are missing, stop and ask for the missing fields.
- If `flyai_openclaw` is not configured, continue only if the user accepts a partial result with missing verified quotes.
- If `12306` returns HTML or blocks access, mark train segments `unverified`.
- If `AMAP_WEB_SERVICE_KEY` is missing, skip route evidence and flag the itinerary as partially verified.
- If self-drive is requested without `vehicle_profile`, keep the route and toll evidence but mark the self-drive cost as open.
- If `pandoc` or `weasyprint` is missing, do not say PDF succeeded.

## Output Location

Prefer this run layout:

```text
notes/travel-planner-runs/YYYY-MM-DD-<trip-slug>/
```

Keep all intermediate JSON and the final PDF together so the evidence chain is auditable.
