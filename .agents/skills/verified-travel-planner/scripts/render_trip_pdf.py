#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import pathlib
import shutil
import subprocess
from typing import Any

from _travel_common import TravelPlannerError, read_json


def esc(value: Any) -> str:
    return html.escape(str(value))


def money(value: Any) -> str:
    try:
        return f"¥{float(value):,.0f}"
    except Exception:
        return esc(value)


def transport_label(value: str) -> str:
    return {
        "flight": "航班",
        "train": "火车",
        "self_drive": "自驾",
    }.get(str(value), str(value))


def render_offer_rows(offers: list[dict[str, Any]]) -> str:
    rows = []
    for offer in offers:
        condition_text = " / ".join(
            f"{esc(key)}: {esc(val)}" for key, val in (offer.get("conditions") or {}).items() if val
        )
        rows.append(
            "| {category} | {product} | {price} | {provider} | {source} |".format(
                category=esc(offer["category"]),
                product=esc(offer["product_name"]),
                price=money(offer["total_price"]),
                provider=esc(offer["provider"]),
                source=f"[link]({offer['source_ref']})",
            )
        )
        if condition_text:
            rows.append(f"|  | 条件 | {condition_text} |  |  |")
    if not rows:
        rows.append("| - | 无已核验报价 | - | - | - |")
    return "\n".join(rows)


def render_day_cards(day_plans: list[dict[str, Any]]) -> str:
    blocks = []
    for item in day_plans:
        notes = "".join(f"<li>{esc(note)}</li>" for note in item.get("notes", [])) or "<li>无额外说明</li>"
        blocks.append(
            f"""
<div class="day-card">
  <h3>{esc(item['date'])} · {esc(item['city'])}</h3>
  <p><strong>上午：</strong>{esc(item['morning'])}</p>
  <p><strong>下午：</strong>{esc(item['afternoon'])}</p>
  <p><strong>晚上：</strong>{esc(item['evening'])}</p>
  <ul>{notes}</ul>
</div>
""".strip()
        )
    return "\n\n".join(blocks)


def render_self_drive_section(manifest: dict[str, Any]) -> str:
    summary = manifest.get("self_drive_summary")
    if not summary or not summary.get("enabled"):
        return ""
    segments = summary.get("segments") or []
    if not segments:
        return """
## 自驾说明

- 已选择自驾，但当前没有可用路线快照，自驾成本无法形成可解释结果。
""".strip()

    rows = []
    for segment in segments:
        rows.append(
            "| {route} | {distance} km | {duration} 分钟 | {tolls} | {estimate} | {source} |".format(
                route=f"{esc(segment['from_city'])} -> {esc(segment['to_city'])}",
                distance=esc(segment["distance_km"]),
                duration=esc(segment["duration_minutes"]),
                tolls=money(segment.get("tolls", 0)),
                estimate=money(segment.get("estimated_total")) if segment.get("estimated_total") is not None else "未提供车辆参数",
                source=f"[link]({segment['source_ref']})",
            )
        )
    total_line = (
        f"- 自驾估算总成本：**{money(summary['estimated_total'])}**，来源为高德过路费 + 用户提供车辆能耗/能源单价。"
        if summary.get("estimated_total") is not None
        else "- 当前只完成了路线、里程、时长与过路费核验；未提供车辆能耗/能源单价，因此没有自驾成本估算。"
    )
    return f"""
## 自驾说明

{total_line}

注意：自驾估算不会并入“准确总价”，因为油费/电费仍依赖车辆参数与能源单价输入。

| 路段 | 距离 | 时长 | 过路费 | 自驾估算 | 证据 |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}
""".strip()


def render_recommendation_rows(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        rows.append(
            "| {city} | {name} | {cluster} | {reason} | {source} |".format(
                city=esc(item.get("city")),
                name=esc(item.get("name")),
                cluster=esc(item.get("cluster")),
                reason=esc(item.get("reason")),
                source=f"[link]({item['source_ref']})" if item.get("source_ref") else "-",
            )
        )
    if not rows:
        rows.append("| - | 无推荐锚点 | - | - | - |")
    return "\n".join(rows)


def render_markdown(
    manifest: dict[str, Any], trip_request: dict[str, Any], quotes_envelope: dict[str, Any]
) -> str:
    summary = manifest["summary"]
    warning_block = ""
    if manifest["unverified_items"]:
        items = "\n".join(
            f"- `{esc(item['segment_key'])}`: {esc(item['reason'])}"
            for item in manifest["unverified_items"]
        )
        warning_block = f"""
<div class="warning-box">
  <strong>预算未闭合</strong>
  <p>以下项目未通过实时核验，因此没有进入准确总价：</p>
</div>

{items}
"""

    alternative_block = ""
    if manifest["alternatives"]:
        alt = manifest["alternatives"][0]
        alternative_block = f"""
## 更省钱备选

总价：**{money(alt['total_price'])}**

| 类别 | 产品 | 价格 | Provider | 证据 |
| --- | --- | --- | --- | --- |
{render_offer_rows(alt['selected_offers'])}
"""

    evidence_list = "\n".join(f"- [证据链接]({link})" for link in manifest["evidence_refs"]) or "- 无"
    self_drive_section = render_self_drive_section(manifest)
    rationale_block = "\n".join(f"- {esc(item)}" for item in manifest.get("selection_rationale", [])) or "- 无"
    followup_block = "\n".join(
        f"- {esc(item)}" for item in manifest.get("followup_questions_asked", [])
    ) or "- 无"

    return f"""
<div class="hero">
  <h1>已核验国内游行程</h1>
  <p>这份 PDF 只把通过实时查询核验的预算项计入总价。未核验项目会被单独列出，不会被伪装成准确预算。</p>
  <div class="meta">
    <span class="meta-chip">{esc(summary['origin'])} 出发</span>
    <span class="meta-chip">{esc(' → '.join(summary['stops']))}</span>
    <span class="meta-chip">{esc(summary['date_range']['start'])} 至 {esc(summary['date_range']['end'])}</span>
    <span class="meta-chip">{summary['trip_days']} 天</span>
  </div>
</div>

## 摘要

<div class="cards">
  <div class="card">
    <div class="card-label">准确总价</div>
    <div class="card-value">{money(summary['primary_total'])}</div>
  </div>
  <div class="card">
    <div class="card-label">预算模式</div>
    <div class="card-value">{esc(summary['budget_mode'])}</div>
  </div>
  <div class="card">
    <div class="card-label">预算目标</div>
    <div class="card-value">{money(summary['budget_target']) if summary['budget_target'] else '不限'}</div>
  </div>
  <div class="card">
    <div class="card-label">核验覆盖</div>
    <div class="card-value">{esc(summary['coverage_status'])}</div>
  </div>
</div>

- 出行人数：`{sum(trip_request['travelers'].values())}` 人
- 房间需求：`{trip_request['rooms']['count']}` 间
- 交通偏好：`{', '.join(transport_label(item) for item in trip_request['transport_preferences'])}`
- 推荐置信度：`{esc(summary.get('recommendation_confidence') or '-')}`
- intake 状态：`{esc(summary.get('intake_status') or '-')}`

{warning_block}

## 推荐依据

{rationale_block}

### 若要进一步定制，建议补问

{followup_block}

## 推荐锚点

| 城市 | 锚点 | 类别 | 推荐原因 | 证据 |
| --- | --- | --- | --- | --- |
{render_recommendation_rows(manifest.get('recommended_pois', []))}

## 每日安排

{render_day_cards(manifest['day_plans'])}

## 已核验预算

| 类别 | 产品 | 价格 | Provider | 证据 |
| --- | --- | --- | --- | --- |
{render_offer_rows(manifest['verified_budget']['selected_offers'])}

{alternative_block}

{self_drive_section}

## 供应商与路线说明

{chr(10).join(f"- {esc(item)}" for item in summary.get('warnings', [])) or '- 无'}

## 证据链

{evidence_list}
""".strip() + "\n"


def run_command(command: list[str], error_prefix: str) -> None:
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise TravelPlannerError(f"{error_prefix}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trip-request", required=True, help="Path to trip-request.json")
    parser.add_argument("--quotes", required=True, help="Path to quote-records.json")
    parser.add_argument("--input", required=True, help="Path to itinerary-manifest.json")
    parser.add_argument("--output-dir", required=True, help="Directory for markdown/html/pdf output")
    args = parser.parse_args()

    trip_request = read_json(args.trip_request)
    quotes_envelope = read_json(args.quotes)
    manifest = read_json(args.input)

    output_dir = pathlib.Path(args.output_dir)
    export_dir = output_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "itinerary-report.md"
    html_path = output_dir / "itinerary-report.html"
    pdf_path = export_dir / "itinerary.pdf"

    markdown = render_markdown(manifest, trip_request, quotes_envelope)
    markdown_path.write_text(markdown, encoding="utf-8")

    pandoc = shutil.which("pandoc")
    weasyprint = shutil.which("weasyprint")
    if not pandoc or not weasyprint:
        parser.exit(1, "[ERROR] pandoc and weasyprint are required to export the PDF\n")

    css_path = pathlib.Path(__file__).resolve().parent.parent / "assets" / "report.css"
    run_command(
        [
            pandoc,
            str(markdown_path),
            "-f",
            "gfm",
            "-t",
            "html5",
            "--standalone",
            "--css",
            str(css_path),
            "-o",
            str(html_path),
        ],
        "Failed to render HTML with pandoc",
    )
    run_command(
        [weasyprint, str(html_path), str(pdf_path)],
        "Failed to render PDF with weasyprint",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
