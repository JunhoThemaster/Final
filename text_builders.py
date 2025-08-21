# -*- coding: utf-8 -*-
"""
텍스트 합성:
- 라벨 CSV의 자연어 설명(description, desc_major/sub/attrs, nl_tags)
- h5 수치 요약(sample_action_numbers) → 짧은 문장으로 변환
- 메타데이터 current_task/scene 정보 등
"""
from typing import Dict, Any, Optional, List
import math

def _is_blank(x) -> bool:
    if x is None:
        return True
    # float NaN
    if isinstance(x, float) and math.isnan(x):
        return True
    s = str(x).strip()
    return (s == "" or s.lower() == "nan" or s.lower() == "none" or s.lower() == "null")

def _clean(x) -> str:
    return "" if _is_blank(x) else str(x).strip()

def _fmt_vals(vals: List[float], ndigits: int = 3, max_items: int = 6) -> str:
    vals = vals[:max_items]
    return ", ".join([str(round(float(v), ndigits)) for v in vals])

def build_numeric_sentence(num: Dict[str, Any], ndigits: int = 3) -> str:
    if not num:
        return ""
    parts = []
    for k, v in num.items():
        if isinstance(v, (list, tuple)):
            parts.append(f"{k}: {_fmt_vals(list(v), ndigits)}")
        else:
            try:
                parts.append(f"{k}: {round(float(v), ndigits)}")
            except Exception:
                # 숫자 아님 → 스킵
                continue
    return " | ".join(parts)

def build_step_text(
    row: Dict[str, Any],
    current_task: Optional[str],
    numeric_sentence: str
) -> str:
    bits: List[str] = []
    for key in ("description", "desc_major", "desc_sub", "desc_attrs"):
        s = _clean(row.get(key, "")) if isinstance(row, dict) else ""
        if s:
            bits.append(s)

    if current_task and not _is_blank(current_task):
        bits.append(f"task: {current_task}")

    if numeric_sentence and not _is_blank(numeric_sentence):
        bits.append(f"state: {numeric_sentence}")

    tag = _clean(row.get("nl_tags", "")) if isinstance(row, dict) else ""
    if tag:
        bits.append(f"tags: {tag}")

    # 중복 공백 제거
    text = " ".join(bits)
    text = " ".join(text.split())
    return text
