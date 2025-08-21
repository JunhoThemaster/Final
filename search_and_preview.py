# -*- coding: utf-8 -*-
"""
쿼리 → 임베딩 Top-k → (옵션) 겹침 억제 + (옵션) 라벨 기반 '세그먼트 전체' GIF 생성

핵심 기능
- --diversify: 시간적으로 서로 가까운(겹치는) 결과를 억제하여 Top-k 다양화
  · 자동 간격: ±win 프레임 창을 '스텝 수'로 환산하여 최소 간격으로 사용
  · 직접 간격: --min_step_gap N 으로 고정(스텝 단위)

- --segment off|label|jsonl
  · off   : Top-1 스텝 중심의 ±win 프레임 범위를 GIF로 생성(기존 방식)
  · label : 라벨 연속성으로 '세그먼트 경계'를 추정하여 해당 세그먼트 전체 GIF
            (연속 판정 필드: --label_field, 허용 스텝 간격: --max_gap)
  · jsonl : JSONL 문서가 이미 seg_start_idx/seg_end_idx 를 가지고 있으면 그대로 사용
            (없으면 label 방식으로 폴백)

- --min_frames: 세그먼트 범위가 너무 짧아 한 장처럼 보이는 경우를 방지하기 위해
               최소 프레임 개수를 보장(기본 12프레임)

- --debug: 실제 프레임 범위/개수, total_frames 등을 출력 (문제 상황 진단용)

전제
- config.py 의 PATHS, PIPE, MODEL 사용
- embedder_siglip.UnifiedEmbedder 사용 (SigLIP 임베더)
- h5_reader.get_num_steps 사용 (세션의 총 step 수)
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

from config import PATHS, PIPE, MODEL
from embedder_siglip import UnifiedEmbedder
from h5_reader import get_num_steps

# -------------------------
# 영상 백엔드 (imageio 권장)
# -------------------------
try:
    import imageio.v2 as iio
    _HAS_IIO = True
except Exception:
    _HAS_IIO = False


# =========================
# 공통 유틸
# =========================
def load_jsonl_vectors(path: str) -> Tuple[np.ndarray, list]:
    """
    JSONL에서 (vector, meta) 로드
    - vector 키는 'vector' 또는 'embedding' 둘 다 허용
    반환:
      X: (N, D) float32
      metas: 길이 N의 메타 리스트(각 항목은 dict)
    """
    X, metas = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            vec = obj.get("vector")
            if vec is None:
                vec = obj.get("embedding")
            if vec is None:
                continue
            X.append(np.asarray(vec, dtype=np.float32))
            metas.append(obj)
    if not X:
        raise RuntimeError("임베딩이 비었습니다. JSONL을 확인하세요.")
    return np.vstack(X), metas


def cosine_topk(vecs: np.ndarray, metas: list, qvec: np.ndarray, k: int):
    """
    코사인 유사도 Top-k
    반환: [(idx(int), sim(float), meta(dict)), ...] (sim 내림차순)
    """
    q = qvec / (np.linalg.norm(qvec) + 1e-12)
    Vn = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    sims = Vn @ q
    order = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i]), metas[i]) for i in order]


def _count_frames(video_path: str) -> int:
    """
    비디오 총 프레임 수
    - imageio 백엔드 사용
    """
    if not _HAS_IIO:
        return 0
    try:
        with iio.get_reader(video_path) as r:
            return r.count_frames()
    except Exception:
        return 0


def _step_to_frame(step_idx: int, n_steps: int, total_frames: int) -> int:
    """
    step_idx -> frame_idx 선형 매핑
    (H5 타임스탬프 정합이 없을 때의 실용적인 근사)
    """
    if n_steps <= 1 or total_frames <= 0:
        return 0
    return round(step_idx * (total_frames - 1) / max(1, (n_steps - 1)))


def extract_frames(video_path: str, start_f: int, end_f: int, scale_w: int = 384) -> List[Image.Image]:
    """
    [start_f, end_f] 범위의 프레임을 랜덤 시킹으로 추출
    - scale_w: 너비 기준 리사이즈(비율 유지), 0이면 원본 크기
    """
    frames: List[Image.Image] = []
    if not _HAS_IIO:
        return frames
    with iio.get_reader(video_path) as r:
        for fid in range(max(0, start_f), max(0, end_f) + 1):
            try:
                arr = r.get_data(fid)
                im = Image.fromarray(arr)
                if scale_w:
                    new_w = scale_w
                    new_h = int(im.height * new_w / max(1, im.width))
                    im = im.resize((new_w, new_h))
                frames.append(im)
            except Exception:
                break
    return frames


def save_as_gif(frames: List[Image.Image], out_path: str, fps: int = 12):
    """
    프레임 리스트 → GIF 파일 저장
    - fps: 초당 프레임 수(클수록 빠름)
    """
    if not frames:
        raise RuntimeError("프레임이 비어 GIF를 만들 수 없습니다.")
    Path(out_path).parent.mkdir(exist_ok=True, parents=True)
    duration_ms = int(1000 / max(1, fps))
    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0, duration=duration_ms)
    return out_path


def sanitize_filename(s: str) -> str:
    """파일명으로 안전하게 변환"""
    return re.sub(r"[^0-9A-Za-z가-힣_\-]+", "_", s)[:80]


# =========================
# 겹침 억제 (시간 NMS)
# =========================
def _estimate_min_step_gap(n_steps: int, total_frames: int, win_frames: int) -> int:
    """
    ±win 프레임 창을 '스텝 수'로 환산하여 최소 간격을 추정
    - 이 값 이하로 가까운 스텝들은 '같은 구간'으로 판단해 억제
    """
    if total_frames <= 1 or n_steps <= 1:
        return 1
    gap = round((2 * win_frames) * (n_steps - 1) / (total_frames - 1))
    return max(1, int(gap))


def suppress_overlaps_by_step(hits: list, min_step_gap: int) -> list:
    """
    같은 (session_id, camera_id) 내에서 step_idx 차이가 min_step_gap 이하인 결과를 제거
    hits: [(idx, sim, meta), ...]  (sim 내림차순 정렬 상태)
    """
    selected = []
    for h in hits:
        _, _, m = h
        sid = m.get("session_id")
        cam = m.get("camera_id")
        s = int(m.get("step_idx", 0))
        ok = True
        for _, _, m2 in selected:
            if m2.get("session_id") == sid and m2.get("camera_id") == cam:
                if abs(s - int(m2.get("step_idx", 0))) <= min_step_gap:
                    ok = False
                    break
        if ok:
            selected.append(h)
    return selected


# =========================
# 라벨 연속 세그먼트
# =========================
def _label_value(m: dict, field: str) -> str:
    """라벨 값 추출(비었으면 desc_sub → description 순으로 폴백)"""
    val = str(m.get(field, "") or "").strip()
    if not val or val.lower() in ("nan", "none", "null"):
        val = str(m.get("desc_sub", "") or "").strip() or str(m.get("description", "") or "").strip()
    return val


def _build_index_by_sc(metas: list):
    """
    (session_id, camera_id) → [(step_idx, meta), ...] (step_idx 오름차순)
    """
    from collections import defaultdict
    buckets = defaultdict(list)
    for m in metas:
        sid = m.get("session_id")
        cam = m.get("camera_id")
        s = int(m.get("step_idx", 0))
        buckets[(sid, cam)].append((s, m))
    for k in buckets:
        buckets[k] = sorted(buckets[k], key=lambda x: x[0])
    return buckets


def infer_segment_steps(anchor_meta: dict, metas_by_sc: dict, mode: str, label_field: str, max_gap: int):
    """
    anchor_meta가 속한 세션/카메라에서 세그먼트 [lo, hi] 스텝 범위를 추정

    - mode='jsonl': anchor_meta가 seg_start_idx/seg_end_idx 를 가지면 그대로 사용
                    (없으면 'label' 방식으로 폴백)
    - mode='label': label_field 값이 같은 항목이 '연속'되는 최대 범위를 확장
                    (연속성 판단 시 스텝이 약간 벌어진 경우도 --max_gap 만큼 허용)
    """
    if mode == "jsonl":
        if anchor_meta.get("seg_start_idx") is not None and anchor_meta.get("seg_end_idx") is not None:
            return int(anchor_meta["seg_start_idx"]), int(anchor_meta["seg_end_idx"])
        # 없으면 아래 label 방식으로 계속 진행

    sid, cam = anchor_meta.get("session_id"), anchor_meta.get("camera_id")
    anchor_s = int(anchor_meta.get("step_idx", 0))
    seq = metas_by_sc.get((sid, cam), [])
    if not seq:
        return anchor_s, anchor_s

    target = _label_value(anchor_meta, label_field)
    if not target:
        return anchor_s, anchor_s

    # 앵커 인덱스 찾기
    idx = None
    for i, (s, m) in enumerate(seq):
        if s == anchor_s:
            idx = i
            break
    if idx is None:
        return anchor_s, anchor_s

    # 왼쪽 확장
    lo = idx
    for i in range(idx - 1, -1, -1):
        s, m = seq[i]
        # 스텝이 너무 벌어지면 단절
        if abs(seq[i + 1][0] - s) > max_gap + 1:
            break
        if _label_value(m, label_field) != target:
            break
        lo = i

    # 오른쪽 확장
    hi = idx
    for i in range(idx + 1, len(seq)):
        s, m = seq[i]
        if abs(s - seq[i - 1][0]) > max_gap + 1:
            break
        if _label_value(m, label_field) != target:
            break
        hi = i

    return seq[lo][0], seq[hi][0]


# =========================
# 실행부 (CLI)
# =========================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=PIPE.out_jsonl, help="임베딩 JSONL 경로")
    ap.add_argument("--query", required=True, help="텍스트 쿼리")
    ap.add_argument("--topk", type=int, default=5, help="상위 결과 개수")
    ap.add_argument("--win", type=int, default=24, help="segment=off일 때 ±win 프레임 창")
    ap.add_argument("--outdir", default="./previews", help="출력 폴더")
    ap.add_argument("--outgif", default="", help="저장 파일명(미지정 시 자동 이름)")

    # 세그먼트 옵션
    ap.add_argument("--segment", choices=["off", "label", "jsonl"], default="off",
                    help="미리보기 GIF 범위: off=±win, label=라벨 연속 세그먼트, jsonl=문서 지정 세그먼트")
    ap.add_argument("--label_field", default="desc_major", help="라벨 연속 판정에 쓰는 필드명")
    ap.add_argument("--max_gap", type=int, default=1, help="라벨 연속으로 볼 최대 스텝 간격")

    # 겹침 억제(시간 NMS)
    ap.add_argument("--diversify", action="store_true", help="시간적으로 겹치는 결과 억제")
    ap.add_argument("--min_step_gap", type=int, default=-1,
                    help="같은 세션/카메라 내 결과 간 최소 스텝 간격(기본: win을 프레임→스텝으로 환산)")

    # 세그먼트가 너무 짧을 때 최소 프레임 보장 + 디버그
    ap.add_argument("--min_frames", type=int, default=12, help="GIF 최소 프레임 수 보장")
    ap.add_argument("--debug", action="store_true", help="세그먼트/프레임 범위 정보 출력")

    args = ap.parse_args()

    # 1) 임베딩/메타 로드
    X, metas = load_jsonl_vectors(args.jsonl)
    print("[OK] embeddings:", X.shape)

    # 2) 쿼리 임베딩
    embedder = UnifiedEmbedder(MODEL.model_name, device=MODEL.device, dtype=MODEL.dtype, normalize=True)
    qvec = embedder.embed_texts([args.query])[0]

    # 3) Top-k 검색
    hits = cosine_topk(X, metas, qvec, k=args.topk)

    # 4) 겹침 억제(선택)
    if args.diversify and len(hits) > 1:
        video_dir = os.path.dirname(PATHS.video_path)
        # Top-1 비디오(없으면 기본)로 총 프레임 수 추정
        v0 = os.path.join(video_dir, hits[0][2].get("image_ref") or os.path.basename(PATHS.video_path))
        total_frames = _count_frames(v0)
        n_steps = get_num_steps(PATHS.h5_path)
        min_gap = args.min_step_gap if args.min_step_gap >= 0 else _estimate_min_step_gap(n_steps, total_frames, args.win)
        hits = suppress_overlaps_by_step(hits, min_gap)

    # Top-k 출력
    print("Top-k:")
    for rank, (i, sim, m) in enumerate(hits, 1):
        txt = (m.get("text") or "").replace("\n", " ")[:100]
        print(f"{rank}. sim={sim:.4f}  step={m.get('step_idx')}  cam={m.get('camera_id')}  text={txt}...")

    # 5) 미리보기 생성 (Top-1)
    if not hits:
        raise RuntimeError("검색 결과가 없습니다.")
    top1 = hits[0][2]

    video_dir = os.path.dirname(PATHS.video_path)
    video_path = os.path.join(video_dir, top1.get("image_ref") or os.path.basename(PATHS.video_path))
    n_steps = get_num_steps(PATHS.h5_path)
    total = _count_frames(video_path)

    if args.segment == "off":
        # 기존 방식: Top-1 스텝 중심 ±win 프레임
        center = _step_to_frame(int(top1.get("step_idx", 0)), n_steps, total)
        start_f = max(0, center - args.win)
        end_f = min(max(0, total - 1), center + args.win)
        gif_name = args.outgif or f"{sanitize_filename(args.query)}_step{top1.get('step_idx')}_win{args.win}.gif"
    else:
        # 세그먼트 전체: 라벨 연속 or JSONL 지정
        metas_by_sc = _build_index_by_sc(metas)
        seg_lo, seg_hi = infer_segment_steps(
            top1, metas_by_sc, mode=args.segment, label_field=args.label_field, max_gap=args.max_gap
        )
        start_f = _step_to_frame(int(seg_lo), n_steps, total)
        end_f = _step_to_frame(int(seg_hi), n_steps, total)
        if start_f > end_f:
            start_f, end_f = end_f, start_f
        gif_name = args.outgif or f"{sanitize_filename(args.query)}_seg_{seg_lo}-{seg_hi}.gif"

    # 최소 프레임 보장(세그먼트가 너무 짧은 경우 완충)
    if (end_f - start_f + 1) < args.min_frames:
        center = _step_to_frame(int(top1.get("step_idx", 0)), n_steps, total)
        half = max(args.min_frames // 2, 4)
        start_f = max(0, center - half)
        end_f = min(max(0, total - 1), center + half)

    if args.debug:
        print(f"[DBG] total_frames={total}, n_steps={n_steps}")
        print(f"[DBG] frames range: {start_f}..{end_f}  (count={max(0, end_f - start_f + 1)})")
        print(f"[DBG] video_path={video_path}")

    # 프레임 추출 → GIF 저장
    frames = extract_frames(video_path, start_f, end_f, scale_w=384)
    out_path = os.path.join(args.outdir, gif_name)
    save_as_gif(frames, out_path, fps=12)
    print(f"[OK] GIF 저장: {out_path}")


if __name__ == "__main__":
    main()
