#!/usr/bin/env python3
"""Parse resume files into normalized text plus source anchors and OCR fallback."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
OFFICE_EXTENSIONS = {".docx", ".doc", ".rtf", ".odt"}
PDF_EXTENSIONS = {".pdf"}

SECTION_PATTERNS = [
    ("profile", re.compile(r"^(summary|profile|about me|professional summary|个人简介|个人总结|自我评价)$", re.I)),
    ("experience", re.compile(r"^(experience|work experience|employment|professional experience|工作经历|实习经历|职业经历)$", re.I)),
    ("projects", re.compile(r"^(projects|project experience|selected projects|项目经历|项目经验)$", re.I)),
    ("education", re.compile(r"^(education|academic background|学历|教育经历|教育背景)$", re.I)),
    ("skills", re.compile(r"^(skills|technical skills|core skills|技能|专业技能|核心技能)$", re.I)),
    ("awards", re.compile(r"^(awards|honors|certifications|奖项|荣誉|证书)$", re.I)),
    ("languages", re.compile(r"^(languages|language skills|语言能力)$", re.I)),
]

SECTION_LABELS = {
    "profile": "个人简介",
    "experience": "工作经历",
    "projects": "项目经历",
    "education": "教育经历",
    "skills": "技能",
    "awards": "奖项",
    "languages": "语言能力",
    "other": "其他",
}

CONFIDENCE_ORDER = {"failed": 0, "low": 1, "medium": 2, "high": 3}
PARSER_PRIORITY = {
    "pdftotext": 4,
    "mdls": 3,
    "pdf-internal": 2,
    "strings": 0,
}

METRIC_PATTERN = re.compile(
    r"("
    r"\d+(?:\.\d+)?\s?%|"
    r"\d+(?:\.\d+)?\s?(?:万|千|亿|k|K|m|M|w|W)|"
    r"(?:DAU|WAU|MAU|GMV|CTR|CVR|ROI|CAC|LTV|NPS|ARPU|留存率|转化率|点击率|日活|周活|月活|收入|成本|时长|满意度)"
    r")",
    re.I,
)
OWNERSHIP_KEYWORDS = ["主导", "负责", "推动", "设计", "定义", "搭建", "统筹", "协调", "独立负责", "owner", "owned", "led", "drove"]
RESULT_KEYWORDS = ["提升", "增长", "降低", "减少", "优化", "上线后", "结果", "improve", "improved", "increase", "increased", "reduce", "reduced", "launched"]
RISK_KEYWORDS = ["参与", "协助", "支持", "优化体验", "提升效率", "赋能", "闭环", "抓手", "负责推进", "参与了", "配合"]


@dataclass
class LineRecord:
    text: str
    line_number: int
    page_number: int | None = None


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    lines = text.split("\n")
    repaired: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        if index + 1 < len(lines):
            following = lines[index + 1].strip()
            if re.fullmatch(r"[\u4e00-\u9fff]{1,2}", current) and re.fullmatch(r"[\u4e00-\u9fff]{1,8}", following):
                repaired.append(current + following)
                index += 2
                continue
        repaired.append(lines[index])
        index += 1
    text = "\n".join(repaired)
    text = re.sub(r"(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def count_words(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_+-]+", text))


def readability_ratio(text: str) -> float:
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return 0.0
    readable = sum(
        1
        for char in chars
        if re.match(r"[\u4e00-\u9fffA-Za-z0-9，。；：、,.%()（）+\-_/]", char)
    )
    return readable / len(chars)


def guess_sections(text: str) -> list[dict[str, int | str]]:
    sections: list[dict[str, int | str]] = []
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines, start=1):
        if not line or len(line) > 50:
            continue
        collapsed = re.sub(r"[:：\-\s]+$", "", line)
        for canonical, pattern in SECTION_PATTERNS:
            if pattern.match(collapsed):
                if sections and sections[-1]["start_line"] == index:
                    break
                sections.append(
                    {
                        "name": canonical,
                        "heading": line,
                        "start_line": index,
                    }
                )
                break
    for index, section in enumerate(sections):
        next_start = len(lines)
        if index + 1 < len(sections):
            next_start = int(sections[index + 1]["start_line"]) - 1
        section["end_line"] = next_start
    return sections


def build_line_records(raw_text: str) -> list[LineRecord]:
    return [
        LineRecord(text=line.strip(), line_number=index)
        for index, line in enumerate(raw_text.splitlines(), start=1)
        if line.strip()
    ]


def next_non_empty_line(records: list[LineRecord], index: int) -> str:
    for offset in range(index + 1, len(records)):
        if records[offset].text:
            return records[offset].text
    return ""


def is_bullet(text: str) -> bool:
    return bool(re.match(r"^[-•*·▪‣]\s*", text))


def strip_bullet(text: str) -> str:
    return re.sub(r"^[-•*·▪‣]\s*", "", text).strip()


def looks_like_project_title(text: str, section_name: str, next_line: str) -> bool:
    if section_name not in {"projects", "experience"}:
        return False
    if not text or is_bullet(text):
        return False
    if len(text) > 48:
        return False
    if text.endswith(("。", ".", "；", ";", "：", ":")):
        return False
    if next_line and is_bullet(next_line):
        return True
    if section_name == "projects" and len(text) <= 24:
        return True
    return False


def build_blocks(raw_text: str, sections_guess: list[dict[str, int | str]]) -> list[dict[str, Any]]:
    records = build_line_records(raw_text)
    section_by_line = {int(section["start_line"]): str(section["name"]) for section in sections_guess}

    blocks: list[dict[str, Any]] = []
    current_section = "other"
    current_group_title: str | None = None

    for index, record in enumerate(records):
        line = record.text
        if record.line_number in section_by_line:
            current_section = section_by_line[record.line_number]
            current_group_title = None
            blocks.append(
                {
                    "id": f"b{len(blocks) + 1}",
                    "text": line,
                    "raw_text": line,
                    "kind": "section_heading",
                    "section_name": current_section,
                    "section_label": SECTION_LABELS.get(current_section, SECTION_LABELS["other"]),
                    "group_title": None,
                    "line_number": record.line_number,
                    "page_number": record.page_number,
                }
            )
            continue

        next_line = next_non_empty_line(records, index)
        kind = "bullet" if is_bullet(line) else "paragraph"
        clean_text = strip_bullet(line) if kind == "bullet" else line

        if looks_like_project_title(clean_text, current_section, next_line):
            kind = "project_title"
            current_group_title = clean_text

        blocks.append(
            {
                "id": f"b{len(blocks) + 1}",
                "text": clean_text,
                "raw_text": line,
                "kind": kind,
                "section_name": current_section,
                "section_label": SECTION_LABELS.get(current_section, SECTION_LABELS["other"]),
                "group_title": current_group_title,
                "line_number": record.line_number,
                "page_number": record.page_number,
            }
        )

    return blocks


def split_into_spans(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])\s+|(?<=[。！？!?；;])|(?<=\.)\s+(?=[A-Z])", text) if part.strip()]
    return parts or [text]


def build_spans(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for block in blocks:
        if block["kind"] == "section_heading":
            continue
        fragments = split_into_spans(str(block["text"]))
        for order, fragment in enumerate(fragments, start=1):
            spans.append(
                {
                    "id": f"s{len(spans) + 1}",
                    "block_id": block["id"],
                    "text": fragment,
                    "order": order,
                    "section_name": block["section_name"],
                    "group_title": block["group_title"],
                }
            )
    return spans


def add_anchor(
    anchors: list[dict[str, Any]],
    anchor_type: str,
    block: dict[str, Any],
    span: dict[str, Any] | None,
    source_text: str,
    highlight_text: str | None,
    confidence: float,
) -> None:
    source_text = source_text.strip()
    if not source_text:
        return

    key = (anchor_type, block["id"], source_text)
    if any((item["type"], item["source_block_id"], item["source_text"]) == key for item in anchors):
        return

    anchors.append(
        {
            "id": f"a{len(anchors) + 1}",
            "type": anchor_type,
            "source_block_id": block["id"],
            "source_span_id": span["id"] if span else None,
            "source_text": source_text,
            "highlight_text": (highlight_text or source_text).strip(),
            "section_name": block["section_name"],
            "section_label": block["section_label"],
            "group_title": block["group_title"],
            "line_number": block["line_number"],
            "page_number": block["page_number"],
            "confidence": round(confidence, 2),
        }
    )


def build_anchors(blocks: list[dict[str, Any]], spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    block_index = {block["id"]: block for block in blocks}
    anchors: list[dict[str, Any]] = []

    for block in blocks:
        if block["kind"] == "project_title":
            add_anchor(anchors, "project-title", block, None, str(block["text"]), str(block["text"]), 0.95)

    for span in spans:
        block = block_index[span["block_id"]]
        text = str(span["text"])

        metric_match = METRIC_PATTERN.search(text)
        if metric_match:
            add_anchor(anchors, "metric", block, span, text, metric_match.group(0), 0.92)

        if any(keyword.lower() in text.lower() for keyword in OWNERSHIP_KEYWORDS):
            add_anchor(anchors, "ownership", block, span, text, text, 0.85)

        if metric_match or any(keyword.lower() in text.lower() for keyword in RESULT_KEYWORDS):
            add_anchor(anchors, "result", block, span, text, metric_match.group(0) if metric_match else text, 0.8)

        if any(keyword.lower() in text.lower() for keyword in RISK_KEYWORDS):
            add_anchor(anchors, "risk", block, span, text, text, 0.7)

    return anchors


def infer_confidence(word_count: int, readable_ratio: float, sections_count: int, anchors_count: int) -> str:
    if word_count < 25 or readable_ratio < 0.32:
        return "failed"
    if word_count < 80 or readable_ratio < 0.52:
        return "low"
    if sections_count == 0 or anchors_count < 2:
        return "medium"
    return "high"


def clamp_confidence(computed: str, ceiling: str | None) -> str:
    if not ceiling:
        return computed
    if CONFIDENCE_ORDER[computed] > CONFIDENCE_ORDER[ceiling]:
        return ceiling
    return computed


def quality_score(word_count: int, readable_ratio_value: float, sections_count: int, anchors: list[dict[str, Any]]) -> float:
    project_titles = sum(1 for anchor in anchors if anchor["type"] == "project-title")
    metrics = sum(1 for anchor in anchors if anchor["type"] == "metric")
    score = (
        min(word_count, 260) * 0.42
        + readable_ratio_value * 40
        + sections_count * 12
        + len(anchors) * 2.2
        + project_titles * 5
        + metrics * 3
    )
    return round(score, 2)


def assemble_result(
    path: Path,
    parser_used: str,
    parse_strategy: str,
    raw_text: str,
    warnings: list[str],
    confidence_ceiling: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_text = normalize_text(raw_text)
    sections_guess = guess_sections(raw_text)
    blocks = build_blocks(raw_text, sections_guess)
    spans = build_spans(blocks)
    anchors = build_anchors(blocks, spans)
    word_count = count_words(raw_text)
    readable_ratio_value = readability_ratio(raw_text)
    confidence = clamp_confidence(
        infer_confidence(word_count, readable_ratio_value, len(sections_guess), len(anchors)),
        confidence_ceiling,
    )

    parse_warnings = list(warnings)
    if not raw_text:
        confidence = "failed"
        parse_warnings.append("No extractable text was found.")
    elif confidence == "low":
        parse_warnings.append("Extracted text is short or noisy; output quality may be limited.")
    elif confidence == "medium" and not sections_guess:
        parse_warnings.append("No obvious resume sections were detected; structure may be noisy.")

    result: dict[str, Any] = {
        "path": str(path),
        "file_type": path.suffix.lower().lstrip("."),
        "parser_used": parser_used,
        "parse_strategy": parse_strategy,
        "confidence": confidence,
        "quality_score": quality_score(word_count, readable_ratio_value, len(sections_guess), anchors),
        "quality": {
            "word_count": word_count,
            "readability_ratio": round(readable_ratio_value, 3),
            "sections_count": len(sections_guess),
            "anchors_count": len(anchors),
        },
        "word_count": word_count,
        "sections_guess": sections_guess,
        "parse_warnings": parse_warnings,
        "raw_text": raw_text,
        "blocks": blocks,
        "spans": spans,
        "anchors": anchors,
    }
    if extra:
        result.update(extra)
    return result


def parse_text(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return assemble_result(path, "plain-text", "text", text, [])


def parse_with_textutil(path: Path) -> tuple[str | None, list[str]]:
    if sys.platform != "darwin":
        return None, ["macOS textutil is unavailable on this platform."]
    if shutil.which("textutil") is None:
        return None, ["textutil is not installed."]

    result = run_command(["textutil", "-convert", "txt", "-stdout", str(path)])
    warnings: list[str] = []
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or "textutil conversion failed."
        warnings.append(message)
        return None, warnings
    return result.stdout, warnings


def parse_docx_xml(path: Path) -> tuple[str, list[str]]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts: list[str] = []
    warnings: list[str] = []

    with zipfile.ZipFile(path) as archive:
        xml_paths = sorted(
            name
            for name in archive.namelist()
            if name == "word/document.xml"
            or re.fullmatch(r"word/(header|footer)\d*\.xml", name)
        )
        if not xml_paths:
            raise ValueError("word/document.xml not found inside DOCX file.")

        for xml_path in xml_paths:
            root = ET.fromstring(archive.read(xml_path))
            for paragraph in root.findall(".//w:p", namespace):
                parts = []
                for node in paragraph.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    if tag == "t" and node.text:
                        parts.append(node.text)
                    elif tag in {"tab"}:
                        parts.append("\t")
                    elif tag in {"br", "cr"}:
                        parts.append("\n")
                line = "".join(parts).strip()
                if line:
                    texts.append(line)

    if not texts:
        warnings.append("DOCX parsed but no paragraph text was found.")
    return "\n".join(texts), warnings


def parse_office(path: Path) -> dict[str, Any]:
    textutil_text, warnings = parse_with_textutil(path)
    if textutil_text:
        return assemble_result(path, "textutil", "text", textutil_text, warnings)

    if path.suffix.lower() == ".docx":
        try:
            text, xml_warnings = parse_docx_xml(path)
            warnings.extend(xml_warnings)
            return assemble_result(path, "docx-xml", "text", text, warnings, confidence_ceiling="medium")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"DOCX XML fallback failed: {exc}")

    return assemble_result(path, "unsupported-office-format", "text", "", warnings, confidence_ceiling="failed")


def parse_pdf_with_pdftotext(path: Path) -> tuple[str | None, list[str]]:
    if shutil.which("pdftotext") is None:
        return None, []
    result = run_command(["pdftotext", "-layout", str(path), "-"])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout, []
    warning = (result.stderr or result.stdout).strip() or "pdftotext failed."
    return None, [warning]


def parse_pdf_with_mdls(path: Path) -> tuple[str | None, list[str]]:
    if sys.platform != "darwin" or shutil.which("mdls") is None:
        return None, []
    result = run_command(["mdls", "-raw", "-name", "kMDItemTextContent", str(path)])
    if result.returncode != 0:
        return None, [(result.stderr or result.stdout).strip() or "mdls failed."]
    output = result.stdout.strip()
    if not output or output == "(null)":
        return None, ["Spotlight text extraction returned null."]
    if output.startswith('"') and output.endswith('"'):
        output = output[1:-1]
        output = output.encode("utf-8").decode("unicode_escape")
    return output, []


def parse_pdf_objects(data: bytes) -> dict[int, bytes]:
    objects: dict[int, bytes] = {}
    for match in re.finditer(rb"(?ms)(\d+)\s+\d+\s+obj\b(.*?)\bendobj\b", data):
        objects[int(match.group(1))] = match.group(2).strip()
    return objects


def split_stream_object(body: bytes) -> tuple[bytes, bytes | None]:
    if b"stream" not in body:
        return body.strip(), None

    stream_start = body.find(b"stream")
    dict_part = body[:stream_start].strip()
    stream_end = body.rfind(b"endstream")
    stream = body[stream_start + len(b"stream") : stream_end]
    if stream.startswith(b"\r\n"):
        stream = stream[2:]
    elif stream.startswith(b"\n"):
        stream = stream[1:]
    if stream.endswith(b"\r\n"):
        stream = stream[:-2]
    elif stream.endswith(b"\n"):
        stream = stream[:-1]
    return dict_part, stream


def decode_stream(dict_part: bytes, stream: bytes) -> bytes:
    if b"/FlateDecode" in dict_part:
        return zlib.decompress(stream)
    return stream


def parse_cmap(stream_text: str) -> tuple[dict[int, str], int]:
    mapping: dict[int, str] = {}
    code_bytes = 2

    codespace_match = re.search(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*endcodespacerange", stream_text)
    if codespace_match:
        code_bytes = max(1, len(codespace_match.group(1)) // 2)

    for block in re.findall(r"beginbfchar(.*?)endbfchar", stream_text, re.S):
        for source, target in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            target_text = bytes.fromhex(target).decode("utf-16-be", errors="ignore")
            mapping[int(source, 16)] = target_text

    for block in re.findall(r"beginbfrange(.*?)endbfrange", stream_text, re.S):
        for line in block.splitlines():
            line = line.strip()
            if not line or not line.startswith("<"):
                continue
            simple_match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
            if simple_match:
                start = int(simple_match.group(1), 16)
                end = int(simple_match.group(2), 16)
                target = int(simple_match.group(3), 16)
                for offset, codepoint in enumerate(range(start, end + 1)):
                    mapping[codepoint] = chr(target + offset)
                continue

            array_match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", line)
            if array_match:
                start = int(array_match.group(1), 16)
                targets = re.findall(r"<([0-9A-Fa-f]+)>", array_match.group(3))
                for offset, target in enumerate(targets):
                    mapping[start + offset] = bytes.fromhex(target).decode("utf-16-be", errors="ignore")

    return mapping, code_bytes


def build_font_decoders(objects: dict[int, bytes]) -> dict[str, dict[str, Any]]:
    font_name_to_object: dict[str, int] = {}
    for body in objects.values():
        dict_part, _ = split_stream_object(body)
        font_block_match = re.search(rb"/Font\s*<<(.*?)>>", dict_part, re.S)
        if not font_block_match:
            continue
        for name, object_id in re.findall(rb"/([A-Za-z0-9]+)\s+(\d+)\s+0\s+R", font_block_match.group(1)):
            font_name_to_object[name.decode("ascii")] = int(object_id)

    decoders: dict[str, dict[str, Any]] = {}
    for font_name, object_id in font_name_to_object.items():
        body = objects.get(object_id, b"")
        dict_part, _ = split_stream_object(body)
        decoder: dict[str, Any] = {
            "encoding": "latin-1",
            "code_bytes": 1,
            "mapping": {},
        }

        if b"/MacRomanEncoding" in dict_part:
            decoder["encoding"] = "mac_roman"

        cmap_match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", dict_part)
        if cmap_match:
            cmap_object = objects.get(int(cmap_match.group(1)), b"")
            cmap_dict, cmap_stream = split_stream_object(cmap_object)
            if cmap_stream is not None:
                cmap_text = decode_stream(cmap_dict, cmap_stream).decode("latin-1", errors="ignore")
                mapping, code_bytes = parse_cmap(cmap_text)
                decoder["mapping"] = mapping
                decoder["code_bytes"] = code_bytes
                decoder["encoding"] = "cmap"

        decoders[font_name] = decoder

    return decoders


def decode_pdf_literal_bytes(data: bytes) -> bytes:
    result = bytearray()
    index = 0
    while index < len(data):
        char = data[index]
        if char != 0x5C:
            result.append(char)
            index += 1
            continue

        index += 1
        if index >= len(data):
            break
        escaped = data[index]
        escapes = {
            ord("n"): b"\n",
            ord("r"): b"\r",
            ord("t"): b"\t",
            ord("b"): b"\b",
            ord("f"): b"\f",
            ord("("): b"(",
            ord(")"): b")",
            ord("\\"): b"\\",
        }
        if escaped in escapes:
            result.extend(escapes[escaped])
            index += 1
            continue
        if escaped in (ord("\n"), ord("\r")):
            index += 1
            if escaped == ord("\r") and index < len(data) and data[index] == ord("\n"):
                index += 1
            continue
        if 48 <= escaped <= 55:
            octal = bytes([escaped])
            index += 1
            for _ in range(2):
                if index < len(data) and 48 <= data[index] <= 55:
                    octal += bytes([data[index]])
                    index += 1
                else:
                    break
            result.append(int(octal, 8))
            continue

        result.append(escaped)
        index += 1
    return bytes(result)


def decode_pdf_text_bytes(raw: bytes, decoder: dict[str, Any]) -> str:
    mapping = decoder.get("mapping") or {}
    code_bytes = int(decoder.get("code_bytes", 1))
    encoding = str(decoder.get("encoding", "latin-1"))

    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", errors="ignore")

    if mapping:
        chars = []
        for index in range(0, len(raw), code_bytes):
            chunk = raw[index : index + code_bytes]
            if len(chunk) != code_bytes:
                continue
            code = int.from_bytes(chunk, "big")
            chars.append(mapping.get(code, ""))
        return "".join(chars)

    return raw.decode(encoding, errors="ignore")


def extract_actual_text(raw_dict: bytes) -> str | None:
    match = re.search(rb"/ActualText\s*\((.*?)\)", raw_dict, re.S)
    if not match:
        return None
    literal = decode_pdf_literal_bytes(match.group(1))
    if literal.startswith(b"\xfe\xff"):
        return literal[2:].decode("utf-16-be", errors="ignore")
    return literal.decode("latin-1", errors="ignore")


def tokenize_pdf_content(data: bytes, start: int = 0, end_char: int | None = None) -> tuple[list[tuple[str, Any]], int]:
    tokens: list[tuple[str, Any]] = []
    index = start
    length = len(data)
    whitespace = b" \t\r\n\x0c\x00"
    delimiters = b"[]<>{}/()%"

    while index < length:
        char = data[index]

        if end_char is not None and char == end_char:
            return tokens, index + 1
        if char in whitespace:
            index += 1
            continue
        if char == ord("%"):
            while index < length and data[index] not in b"\r\n":
                index += 1
            continue
        if char == ord("/"):
            index += 1
            start_name = index
            while index < length and data[index] not in whitespace + delimiters:
                index += 1
            tokens.append(("name", data[start_name:index].decode("latin-1", errors="ignore")))
            continue
        if char == ord("("):
            index += 1
            depth = 1
            literal = bytearray()
            while index < length and depth > 0:
                current = data[index]
                if current == ord("\\"):
                    literal.append(current)
                    index += 1
                    if index < length:
                        literal.append(data[index])
                        index += 1
                    continue
                if current == ord("("):
                    depth += 1
                elif current == ord(")"):
                    depth -= 1
                    if depth == 0:
                        index += 1
                        break
                literal.append(current)
                index += 1
            tokens.append(("literal", bytes(literal)))
            continue
        if char == ord("["):
            nested, index = tokenize_pdf_content(data, index + 1, ord("]"))
            tokens.append(("array", nested))
            continue
        if char == ord("<"):
            if index + 1 < length and data[index + 1] == ord("<"):
                depth = 1
                cursor = index + 2
                while cursor < length and depth > 0:
                    if data[cursor:cursor + 2] == b"<<":
                        depth += 1
                        cursor += 2
                        continue
                    if data[cursor:cursor + 2] == b">>":
                        depth -= 1
                        cursor += 2
                        if depth == 0:
                            break
                        continue
                    cursor += 1
                tokens.append(("dict", data[index:cursor]))
                index = cursor
                continue
            cursor = index + 1
            while cursor < length and data[cursor] != ord(">"):
                cursor += 1
            tokens.append(("hex", data[index + 1:cursor]))
            index = cursor + 1
            continue

        start_token = index
        while index < length and data[index] not in whitespace + delimiters:
            index += 1
        token = data[start_token:index].decode("latin-1", errors="ignore")
        if token:
            if re.fullmatch(r"[+-]?(?:\d+\.\d+|\d+)", token):
                tokens.append(("number", token))
            else:
                tokens.append(("word", token))

    return tokens, index


def decode_text_operand(operand: tuple[str, Any], font_name: str | None, decoders: dict[str, dict[str, Any]]) -> str:
    decoder = decoders.get(font_name or "", {"encoding": "latin-1", "code_bytes": 1, "mapping": {}})
    kind, value = operand
    if kind == "literal":
        raw = decode_pdf_literal_bytes(value)
        return decode_pdf_text_bytes(raw, decoder)
    if kind == "hex":
        hex_data = re.sub(rb"\s+", b"", value)
        if len(hex_data) % 2 == 1:
            hex_data += b"0"
        raw = bytes.fromhex(hex_data.decode("ascii"))
        return decode_pdf_text_bytes(raw, decoder)
    return ""


def extract_text_from_content_stream(stream: bytes, decoders: dict[str, dict[str, Any]]) -> str:
    tokens, _ = tokenize_pdf_content(stream)
    stack: list[tuple[str, Any]] = []
    current_font: str | None = None
    current_x: float | None = None
    current_y: float | None = None
    last_x: float | None = None
    last_y: float | None = None
    skip_marked_text = False
    parts: list[str] = []

    def append_text(text: str, force_newline: bool = False) -> None:
        nonlocal last_x, last_y
        if force_newline and parts and not parts[-1].endswith("\n"):
            parts.append("\n")
        text = normalize_text(text)
        if not text:
            return
        elif current_y is not None and last_y is not None:
            if abs(current_y - last_y) > 4 and parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            elif current_x is not None and last_x is not None and current_x - last_x > 18:
                if parts and not re.search(r"[\s\n]$", parts[-1]):
                    parts.append(" ")
        parts.append(text)
        last_x = current_x
        last_y = current_y

    for kind, value in tokens:
        if kind != "word":
            stack.append((kind, value))
            continue

        operator = value
        if operator == "Tf":
            if len(stack) >= 2:
                font_operand = stack[-2]
                if font_operand[0] == "name":
                    current_font = str(font_operand[1])
            stack.clear()
        elif operator == "Tm":
            if len(stack) >= 6:
                try:
                    current_x = float(str(stack[-2][1]))
                    current_y = float(str(stack[-1][1]))
                except ValueError:
                    current_x = current_y = None
            stack.clear()
        elif operator in {"Td", "TD"}:
            if len(stack) >= 2 and current_x is not None and current_y is not None:
                try:
                    current_x += float(str(stack[-2][1]))
                    current_y += float(str(stack[-1][1]))
                except ValueError:
                    current_x = current_y = None
            stack.clear()
        elif operator == "T*":
            append_text("", force_newline=True)
            stack.clear()
        elif operator in {"Tj", "'", '"'}:
            if not skip_marked_text and stack:
                append_text(
                    decode_text_operand(stack[-1], current_font, decoders),
                    force_newline=operator in {"'", '"'},
                )
            stack.clear()
        elif operator == "TJ":
            if not skip_marked_text and stack and stack[-1][0] == "array":
                text_parts = []
                for item in stack[-1][1]:
                    if item[0] in {"literal", "hex"}:
                        text_parts.append(decode_text_operand(item, current_font, decoders))
                append_text("".join(text_parts))
            stack.clear()
        elif operator == "BDC":
            actual_text = None
            for item in reversed(stack):
                if item[0] == "dict":
                    actual_text = extract_actual_text(item[1])
                    if actual_text:
                        break
            if actual_text:
                append_text(actual_text)
                skip_marked_text = True
            stack.clear()
        elif operator == "EMC":
            skip_marked_text = False
            stack.clear()
        elif operator in {"BT", "ET", "q", "Q"}:
            stack.clear()
        else:
            stack.clear()

    text = "".join(parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_pdf_internal(path: Path) -> tuple[str | None, list[str]]:
    data = path.read_bytes()
    objects = parse_pdf_objects(data)
    if not objects:
        return None, ["No PDF objects were parsed."]

    decoders = build_font_decoders(objects)
    content_stream_ids: list[int] = []
    for body in objects.values():
        dict_part, _ = split_stream_object(body)
        if re.search(rb"/Type\s*/Page\b", dict_part) and not re.search(rb"/Type\s*/Pages\b", dict_part):
            single = re.search(rb"/Contents\s+(\d+)\s+0\s+R", dict_part)
            if single:
                content_stream_ids.append(int(single.group(1)))
                continue
            array_match = re.search(rb"/Contents\s*\[(.*?)\]", dict_part, re.S)
            if array_match:
                for object_id in re.findall(rb"(\d+)\s+0\s+R", array_match.group(1)):
                    content_stream_ids.append(int(object_id))

    if not content_stream_ids:
        return None, ["No page content streams were found."]

    extracted_parts = []
    for object_id in content_stream_ids:
        body = objects.get(object_id)
        if not body:
            continue
        dict_part, stream = split_stream_object(body)
        if stream is None:
            continue
        try:
            decoded = decode_stream(dict_part, stream)
        except zlib.error as exc:
            return None, [f"Failed to decompress PDF content stream: {exc}"]
        extracted_parts.append(extract_text_from_content_stream(decoded, decoders))

    text = "\n".join(part for part in extracted_parts if part.strip())
    if not text.strip():
        return None, ["Parsed PDF content streams but no readable text was recovered."]
    return text, []


def parse_pdf_with_strings(path: Path) -> tuple[str | None, list[str]]:
    if shutil.which("strings") is None:
        return None, []
    result = run_command(["strings", "-a", str(path)])
    if result.returncode != 0:
        return None, [(result.stderr or result.stdout).strip() or "strings failed."]

    lines = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if len(line) < 4:
            continue
        if line.startswith("%PDF") or line in {"obj", "endobj", "stream", "endstream", "xref", "trailer", "startxref", "%%EOF"}:
            continue
        if re.search(r"^[A-Za-z0-9./_-]+\s+\d+\s+\d+\s+R$", line):
            continue
        if sum(char.isalnum() or "\u4e00" <= char <= "\u9fff" for char in line) < max(3, len(line) // 4):
            continue
        if re.search(r"[\u4e00-\u9fffA-Za-z]", line):
            lines.append(line)

    text = "\n".join(lines)
    if not text.strip():
        return None, ["Binary string extraction did not yield readable text."]
    warnings = [
        "Fallback PDF parsing used binary string extraction; layout and some text may be missing.",
        "If this PDF is image-only, OCR fallback should be preferred.",
    ]
    return text, warnings


def run_resume_ocr_script(path: Path) -> dict[str, Any]:
    script_path = Path(__file__).with_name("resume_ocr.py")
    result = subprocess.run(
        [sys.executable, str(script_path), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not result.stdout.strip():
        message = (result.stderr or result.stdout).strip() or "OCR fallback failed."
        raise RuntimeError(message)

    payload = json.loads(result.stdout)
    if not payload.get("rawText") and not payload.get("raw_text"):
        message = "; ".join(payload.get("warnings", [])) or "OCR fallback failed."
        raise RuntimeError(message)
    return payload


def parse_pdf_text_candidates(path: Path) -> list[dict[str, Any]]:
    parsers: list[tuple[str, Callable[[Path], tuple[str | None, list[str]]], str | None]] = [
        ("pdftotext", parse_pdf_with_pdftotext, "high"),
        ("mdls", parse_pdf_with_mdls, "medium"),
        ("pdf-internal", parse_pdf_internal, "medium"),
        ("strings", parse_pdf_with_strings, "low"),
    ]

    candidates: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for parser_name, parser, confidence_ceiling in parsers:
        text, warnings = parser(path)
        if not text:
            continue
        normalized = normalize_text(text)
        if not normalized or normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        candidate = assemble_result(
                path,
                parser_name,
                "text",
                normalized,
                warnings,
                confidence_ceiling=confidence_ceiling,
            )
        candidate["parser_priority"] = PARSER_PRIORITY.get(parser_name, 1)
        candidates.append(candidate)
    return candidates


def should_attempt_ocr(best_text_candidate: dict[str, Any] | None) -> bool:
    if best_text_candidate is None:
        return True
    return (
        best_text_candidate["confidence"] in {"failed", "low"}
        or best_text_candidate["quality_score"] < 95
        or best_text_candidate["quality"]["anchors_count"] < 3
    )


def choose_better_candidate(text_candidate: dict[str, Any] | None, ocr_candidate: dict[str, Any] | None) -> dict[str, Any]:
    if text_candidate is None and ocr_candidate is None:
        raise ValueError("No parse candidates are available.")
    if text_candidate is None:
        return ocr_candidate  # type: ignore[return-value]
    if ocr_candidate is None:
        return text_candidate

    text_rank = CONFIDENCE_ORDER[text_candidate["confidence"]]
    ocr_rank = CONFIDENCE_ORDER[ocr_candidate["confidence"]]
    if text_candidate["parser_used"] == "strings" and ocr_rank >= CONFIDENCE_ORDER["low"]:
        ocr_candidate["parse_warnings"] = text_candidate["parse_warnings"] + [
            "Switched to OCR because binary-string PDF fallback was not reliable enough."
        ] + ocr_candidate["parse_warnings"]
        return ocr_candidate
    if ocr_rank > text_rank:
        ocr_candidate["parse_warnings"] = text_candidate["parse_warnings"] + [
            f"Switched to OCR because text-layer extraction confidence was {text_candidate['confidence']}."
        ] + ocr_candidate["parse_warnings"]
        return ocr_candidate
    if (
        text_rank <= CONFIDENCE_ORDER["low"]
        and ocr_rank >= text_rank
        and ocr_candidate["quality_score"] >= text_candidate["quality_score"] - 25
        and (
            text_candidate.get("parser_priority", 1) <= 1
            or text_candidate["quality"]["sections_count"] < 2
        )
    ):
        ocr_candidate["parse_warnings"] = text_candidate["parse_warnings"] + [
            "Switched to OCR because low-confidence text extraction was not trustworthy enough."
        ] + ocr_candidate["parse_warnings"]
        return ocr_candidate
    if text_rank > ocr_rank:
        return text_candidate
    if ocr_candidate["quality_score"] > text_candidate["quality_score"] + 6:
        ocr_candidate["parse_warnings"] = text_candidate["parse_warnings"] + [
            "Switched to OCR because OCR produced a cleaner resume structure."
        ] + ocr_candidate["parse_warnings"]
        return ocr_candidate
    return text_candidate


def parse_pdf(path: Path) -> dict[str, Any]:
    text_candidates = parse_pdf_text_candidates(path)
    best_text_candidate = max(
        text_candidates,
        key=lambda item: (
            CONFIDENCE_ORDER[item["confidence"]],
            item["quality"]["sections_count"],
            item["quality"]["anchors_count"],
            item.get("parser_priority", 1),
            item["quality_score"],
        ),
        default=None,
    )

    ocr_candidate: dict[str, Any] | None = None
    if should_attempt_ocr(best_text_candidate):
        try:
            ocr_payload = run_resume_ocr_script(path)
            ocr_candidate = assemble_result(
                path,
                "vision-ocr",
                "ocr",
                str(ocr_payload.get("raw_text", ocr_payload.get("rawText", ""))),
                list(ocr_payload.get("warnings", [])),
                extra={
                    "ocr_engine": ocr_payload.get("engine", "vision"),
                    "ocr_pages": ocr_payload.get("pages", []),
                },
            )
        except Exception as exc:
            warning = f"OCR fallback unavailable: {exc}"
            if best_text_candidate is not None:
                best_text_candidate["parse_warnings"].append(warning)
            else:
                best_text_candidate = assemble_result(
                    path,
                    "pdf-failed",
                    "text",
                    "",
                    [warning, "Unable to extract reliable text from PDF."],
                    confidence_ceiling="failed",
                )

    return choose_better_candidate(best_text_candidate, ocr_candidate)


def parse_resume(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return parse_text(path)
    if suffix in OFFICE_EXTENSIONS:
        return parse_office(path)
    if suffix in PDF_EXTENSIONS:
        return parse_pdf(path)
    return assemble_result(
        path,
        "unsupported-extension",
        "text",
        "",
        [f"Unsupported file extension: {suffix or '(none)'}"],
        confidence_ceiling="failed",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse resume files into normalized text, anchors, and OCR-aware confidence signals.")
    parser.add_argument("path", help="Path to a resume file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    try:
        result = parse_resume(Path(args.path).expanduser())
    except Exception as exc:
        result = {
            "path": str(Path(args.path).expanduser()),
            "file_type": Path(args.path).suffix.lower().lstrip("."),
            "parser_used": "exception",
            "parse_strategy": "text",
            "confidence": "failed",
            "quality_score": 0.0,
            "quality": {
                "word_count": 0,
                "readability_ratio": 0.0,
                "sections_count": 0,
                "anchors_count": 0,
            },
            "word_count": 0,
            "sections_guess": [],
            "parse_warnings": [str(exc)],
            "raw_text": "",
            "blocks": [],
            "spans": [],
            "anchors": [],
        }

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0 if result["confidence"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
