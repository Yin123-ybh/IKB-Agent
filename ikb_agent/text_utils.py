from __future__ import annotations

import math
import re
from collections import Counter

_LATIN_TOKEN_RE = re.compile(r"[a-zA-Z]+[a-zA-Z0-9+\-]*|\d+[a-zA-Z0-9+\-]*")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_MODEL_RE = re.compile(r"\b[A-Z]{1,8}[-\s]?\d{1,5}[A-Z0-9+\-]*\b", re.I)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text: str) -> list[str]:
    text = normalize_text(text).lower()
    latin_tokens = _LATIN_TOKEN_RE.findall(text)
    cjk_tokens = _CJK_RE.findall(text)
    return latin_tokens + cjk_tokens


def vectorize(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    counts = Counter(tokens)
    if not counts:
        return {}
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {token: value / norm for token, value in counts.items()}


def sparse_vectorize(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    counts = Counter(tokens)
    if not counts:
        return {}
    total = len(tokens)
    return {token: count / total for token, count in counts.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def sparse_overlap(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    numerator = sum(min(left[token], right[token]) for token in shared)
    denominator = sum(max(left.get(token, 0), right.get(token, 0)) for token in set(left) | set(right))
    return numerator / denominator if denominator else 0.0


def guess_item_name(file_title: str, context: str) -> str:
    source = f"{file_title}\n{context}"
    model_matches = _MODEL_RE.findall(source)
    normalized_models = []
    for match in model_matches:
        model = re.sub(r"\s+", "-", match.upper())
        if "DEMO" in model:
            continue
        if model not in normalized_models:
            normalized_models.append(model)

    title = re.sub(r"\.[a-zA-Z0-9]+$", "", file_title or "").strip()
    title = re.sub(r"(用户手册|说明书|使用手册|使用说明|操作指南|整本手册|文档|的使用)$", "", title).strip(" -_")

    if normalized_models:
        model = normalized_models[0]
        compact_title = re.sub(r"[^a-z0-9]+", "", title.lower())
        compact_model = re.sub(r"[^a-z0-9]+", "", model.lower())
        if compact_model not in compact_title:
            return f"{title} {model}".strip()
        return title or model

    for keyword in ("万用表", "路由器", "网桥", "交换机", "传感器", "控制器", "主板", "平台", "系统"):
        if keyword in source:
            return title if keyword in title else f"{title} {keyword}".strip()
    return title or "未知商品"


def strip_markdown(text: str, limit: int = 420) -> str:
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"[#>*_`~-]+", " ", text)
    return normalize_text(text)[:limit]
