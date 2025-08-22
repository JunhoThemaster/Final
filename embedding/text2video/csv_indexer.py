# -*- coding: utf-8 -*-
"""
고정 스키마용 CSV 인덱서 (초간단/고속판)
- 컬럼명은 고정: session_id, camera_id, video_summary, lab_name
- 기본 CSV 경로: data/all_labs_merged.csv
- 반환: dict[session_id] = { "camera_id":..., "caption":..., "lab":... }
"""

import csv
from pathlib import Path
from typing import Dict

# 고정 경로/스키마 (필요하면 여기만 바꾸세요)
DEFAULT_CSV = Path("data/all_labs_merged.csv")
REQUIRED = ("session_id", "camera_id", "video_summary", "lab_name")

def discover_csv() -> Path:
    """항상 같은 파일을 쓴다는 전제라면 단순 반환."""
    return DEFAULT_CSV

def _require_headers(headers) -> None:
    miss = [h for h in REQUIRED if h not in headers]
    if miss:
        raise SystemExit(f"[ERR] CSV missing required columns: {miss} (have: {headers})")

def build_session_index(csv_path: str | Path | None = None) -> Dict[str, Dict[str, str]]:
    """
    매우 빠른 인덱싱: 별칭/오버라이드 없음, 고정 컬럼만 읽음.
    """
    p = Path(csv_path) if csv_path else discover_csv()
    if not p.exists():
        raise SystemExit(f"[ERR] CSV not found: {p}")

    idx: Dict[str, Dict[str, str]] = {}
    with open(p, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        headers = [h.strip() for h in (r.fieldnames or [])]
        _require_headers(headers)

        # 필드 키 조회 비용을 줄이기 위해 인덱스 캐시
        sid_k, cam_k, cap_k, lab_k = "session_id", "camera_id", "video_summary", "lab_name"

        for row in r:
            # 최소 트림만 수행 (lower 필요 없음: 스키마 고정이므로)
            sid = (row.get(sid_k) or "").strip()
            if not sid:
                continue
            cam = (row.get(cam_k) or "").strip()
            cap = (row.get(cap_k) or "").strip()
            lab = (row.get(lab_k) or "").strip()
            idx[sid] = {"camera_id": cam, "caption": cap, "lab": lab}
    return idx
