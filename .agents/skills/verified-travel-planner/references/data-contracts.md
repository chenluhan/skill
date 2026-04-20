# Data Contracts

## trip-request.json

Normalized request object.

Required top-level fields:

```json
{
  "origin": {
    "city": "Shanghai"
  },
  "stops": [
    {
      "city": "Hangzhou",
      "nights": 2,
      "must_see": ["西湖"]
    }
  ],
  "date_range": {
    "start": "2026-05-01",
    "end": "2026-05-03"
  },
  "travelers": {
    "adults": 2,
    "children": 1,
    "infants": 0,
    "seniors": 0
  },
  "rooms": {
    "count": 1
  },
  "budget_mode": "soft_target",
  "budget_target": 5000,
  "hotel_level": "midscale",
  "transport_preferences": ["train", "flight", "self_drive"],
  "must_see": [],
  "constraints": [],
  "trip_style_tags": ["scenery", "food"],
  "traveler_needs": ["infant_friendly", "low_transfer"],
  "pace_preference": "relaxed",
  "recommendation_confidence": "medium",
  "intake_status": "ready_for_recommendation",
  "missing_preference_fields": [],
  "followup_questions": [],
  "vehicle_profile": {
    "powertrain": "gasoline",
    "consumption_per_100km": 8.2,
    "unit_price": 7.8,
    "currency": "CNY"
  },
  "pace": "morning-anchor-afternoon-anchor-free-evening",
  "currency": "CNY"
}
```

Rules:

- `stops` length must be `1..3`
- `date_range.end` must be on or after `date_range.start`
- `budget_target` is optional only when `budget_mode = "no_cap"`
- `transport_preferences` may include `self_drive`
- `vehicle_profile` is optional and is only used for self-drive estimates
- `rooms.count` must be a positive integer
- `trip_style_tags` should capture what the traveler wants to optimize for, such as `scenery`, `food`, `culture`, `family`, `photo`
- `traveler_needs` should capture execution constraints such as `infant_friendly`, `low_transfer`, `stroller_friendly`
- `pace_preference` should be one of `relaxed`, `balanced`, `dense`
- `intake_status` should be `ready_for_recommendation` or `needs_followup`

## quote-records.json

Envelope shape:

```json
{
  "trip_request_ref": "trip-request.json",
  "queried_at": "2026-04-18T12:00:00+08:00",
  "quotes": [],
  "provider_status": {},
  "warnings": [],
  "unverified_items": []
}
```

Each quote object must contain:

```json
{
  "segment_key": "hotel:Hangzhou:2026-05-01:2026-05-03",
  "category": "hotel",
  "provider": "flyai_openclaw",
  "product_name": "West Lake Garden Hotel",
  "source_ref": "https://example.com/offer/123",
  "queried_at": "2026-04-18T12:00:00+08:00",
  "unit_price": 899,
  "total_price": 1798,
  "currency": "CNY",
  "conditions": {
    "room_type": "Deluxe Twin",
    "refund_policy": "Free cancellation before 18:00"
  },
  "verification_status": "verified",
  "traveler_scope": {
    "adults": 2,
    "children": 1
  },
  "booking_url": "https://example.com/offer/123",
  "metadata": {
    "recommended": true
  }
}
```

Allowed `verification_status` values:

- `verified`
- `estimated`
- `unverified`
- `provider_unavailable`
- `provider_error`

## itinerary-manifest.json

Top-level shape:

```json
{
  "summary": {},
  "stop_order": [],
  "day_plans": [],
  "recommended_pois": [],
  "candidate_clusters": [],
  "selection_rationale": [],
  "followup_questions_asked": [],
  "verified_budget": {},
  "unverified_items": [],
  "booking_links": [],
  "evidence_refs": [],
  "alternatives": []
}
```

Required sections:

- `summary`: trip overview, traveler counts, date range, coverage status
- `stop_order`: ordered city list
- `day_plans[]`: one item per day
- `recommended_pois[]`: ranked destination anchors with recommendation reasons
- `candidate_clusters[]`: grouped recommendation buckets such as scenic / culture / food
- `selection_rationale[]`: why the planner chose this route rhythm
- `followup_questions_asked[]`: preference gaps that should have been clarified before finalizing
- `verified_budget`: totals plus selected verified offers
- `unverified_items[]`: missing or failed budget items
- `booking_links[]`: selected booking targets
- `evidence_refs[]`: source links or page refs

## Provider Output Rules

- Keep raw provider payloads out of the final manifest unless they are needed as evidence.
- Normalize all money to numeric `CNY` values before summing.
- Preserve original booking links and human-readable product names.
- Keep `self_drive` estimates out of `verified_budget` even when they have numeric prices.
