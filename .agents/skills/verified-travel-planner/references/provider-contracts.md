# Provider Contracts

## Environment Variables

### Safe local persistence on macOS

For secrets you want to keep off the repo and out of shell startup files, the planner can read from the macOS login Keychain.

Supported secret names:

```bash
AMAP_WEB_SERVICE_KEY
FLYAI_OPENCLAW_TOKEN
```

Store a value:

```bash
security add-generic-password -U \
  -a "$USER" \
  -s "codex.verified-travel-planner.AMAP_WEB_SERVICE_KEY" \
  -w "your-key"
```

Lookup precedence is:

1. process environment variable
2. macOS Keychain item `codex.verified-travel-planner.<SECRET_NAME>`

### flyai_openclaw

Configure one of these bridge modes:

1. Built-in CLI bridge

If `flyai` CLI is installed and `scripts/flyai_openclaw_bridge.py` exists, the planner can auto-discover it without extra env vars.

Prerequisites:

```bash
npm i -g @fly-ai/flyai-cli
flyai config set FLYAI_API_KEY "your-key"
```

Auto-discovered command shape:

```bash
python3 /path/to/verified-travel-planner/scripts/flyai_openclaw_bridge.py
```

2. Command bridge

```bash
export FLYAI_OPENCLAW_CMD="python3 /path/to/openclaw_bridge.py"
```

The command must:

- read a JSON payload from stdin
- write a JSON response to stdout
- exit non-zero on transport or auth failure

3. HTTP bridge

```bash
export FLYAI_OPENCLAW_ENDPOINT="http://127.0.0.1:8787/quote"
export FLYAI_OPENCLAW_TOKEN="optional-bearer-token"
```

The endpoint must accept a JSON POST body and return a JSON object.

Bridge request shape:

```json
{
  "trip_request": {},
  "requests": [
    {
      "segment_key": "flight:Shanghai:Hangzhou:2026-05-01",
      "category": "flight",
      "origin": "Shanghai",
      "destination": "Hangzhou",
      "date": "2026-05-01",
      "travelers": {
        "adults": 2
      }
    }
  ]
}
```

Bridge response shape:

```json
{
  "offers": [
    {
      "segment_key": "flight:Shanghai:Hangzhou:2026-05-01",
      "category": "flight",
      "provider": "flyai_openclaw",
      "product_name": "MU 1234",
      "source_ref": "https://...",
      "unit_price": 820,
      "total_price": 1640,
      "currency": "CNY",
      "conditions": {
        "cabin": "Economy"
      },
      "verification_status": "verified",
      "traveler_scope": {
        "adults": 2
      },
      "booking_url": "https://...",
      "metadata": {
        "recommended": true
      }
    }
  ]
}
```

## amap_route_poi

Required variable:

```bash
export AMAP_WEB_SERVICE_KEY="your-key"
```

Used endpoints:

- geocoding
- text search
- route planning

The script uses Amap for:

- city geocoding
- POI lookup for `must_see`
- route snapshots between consecutive stops
- toll extraction for self-drive segments

Route data is evidence, not a budget line item.

When `transport_preferences` includes `self_drive`, the script may also produce:

- route distance
- route duration
- Amap tolls
- user-profile-based energy cost estimates

These remain estimates unless a future version adds a fully verifiable vehicle-cost source.

## 12306_official_query

No developer key is assumed.

The script uses official public assets and query pages:

- station telecodes from `station_name.js`
- train search / fare query through the same official chain used by the 12306 site

Important constraints:

- the site may return HTML error pages instead of JSON
- anti-bot throttling may block unattended requests
- any non-JSON or partial result must mark the train segment as `unverified`

Do not convert train fares into fixed constants.

## elong_hotel

This adapter is not implemented in v1.

If you extend hotel coverage later, keep the output shape identical to `flyai_openclaw` offers so `build_itinerary.py` does not need provider-specific logic.
