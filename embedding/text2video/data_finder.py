# embedding/text2video/data_finder.py
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Iterable, List, Optional

VID_EXT = {".mp4", ".mov", ".mkv", ".avi"}

def discover_video_roots(
    base_dirs: Iterable[str] = ("data",),
    lab_names: Iterable[str] = (),
    max_depth: int = 3,
) -> List[Path]:
    """
    lab 힌트를 쓰되, 구현은 단순: base 자체만 루트로 두고 시작.
    - lab 폴더를 굳이 더 찾는 과탐색을 줄이고, 일단 base 디렉토리만 루트로 삼음.
    - (대부분 케이스) 루트가 소수이고, 아래의 정확 매칭 글롭이 빠르게 끝남.
    """
    roots: List[Path] = []
    for b in base_dirs:
        p = Path(b).resolve()
        if p.exists():
            roots.append(p)
    return roots or [Path("data").resolve()]

def _glob_first(root: Path, patterns: list[str], max_hits: int = 1) -> List[Path]:
    """
    여러 패턴을 순서대로 글롭하여 최초 max_hits개만 수집.
    - 조기 종료로 디스크 트래버설 최소화.
    """
    out: List[Path] = []
    for pat in patterns:
        for hit in root.glob(pat):
            out.append(hit)
            if len(out) >= max_hits:
                return out
    return out

def resolve_video_exact(
    roots: Iterable[Path],
    lab_name: str,
    session_id: str,
    camera_id: str,
) -> Optional[Path]:
    """
    '정확 매칭' 규칙을 글롭 패턴으로 바로 표현:
      - **/*{sid}*/(recordings/MP4|MP4)/*{cam}*.mp4
      - 없으면 **/*{sid}*/*{cam}*.mp4 (제한 깊이로 과탐색 완화는 roots 설계로 해결)
    여러 개면 경로가 짧은 순으로 정렬해 1개 반환.
    """
    sid = (session_id or "").lower()
    cam = (camera_id or "").lower()

    if not sid or not cam:
        return None

    # 우선순위 높은 패턴들
    pri_patterns = [
        f"**/*{sid}*/recordings/MP4/*{cam}*.mp4",
        f"**/*{sid}*/MP4/*{cam}*.mp4",
    ]
    # 최후 fallback
    fb_patterns = [
        f"**/*{sid}*/*{cam}*.mp4",
    ]

    candidates: List[Path] = []
    for root in roots:
        # 1) 우선 패턴에서 바로 찾기
        hits = _glob_first(root, pri_patterns, max_hits=3)
        if not hits:
            hits = _glob_first(root, fb_patterns, max_hits=3)

        for h in hits:
            # 케이스 인식: 소문자 비교로 camera_id 포함 재확인
            if cam in h.name.lower() and h.suffix.lower() in VID_EXT:
                candidates.append(h)

        if candidates:
            break  # 루트별 조기 종료

    if not candidates:
        return None

    candidates.sort(key=lambda p: len(str(p)))
    return candidates[0]
