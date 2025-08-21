# -*- coding: utf-8 -*-
"""
SigLIP vs CLIP vs Gemma3 검색 비교 + Top-1 구간 GIF 자동 생성

- 입력: 각 모델의 임베딩 JSONL (SigLIP/CLIP/Gemma3) — 하나만 줘도 동작, 여러 개면 모두 비교
- 동작:
  1) 쿼리 문장을 각 모델 임베더로 임베딩
  2) 각 JSONL에서 코사인 유사도 Top-k를 출력
  3) 각 모델의 Top-1 결과 기준으로 비디오에서 ±win 프레임 추출 → GIF 저장
- 출력: 콘솔 결과 + previews/ 아래에 GIF 파일들 저장

필수 의존성:
  pip install imageio imageio-ffmpeg pillow numpy
"""

import os, re, json, argparse, numpy as np
from typing import Tuple, List
from pathlib import Path
from PIL import Image

# 프로젝트 설정/유틸
from config import PATHS, MODEL
from h5_reader import get_num_steps

# ---- 비디오 백엔드 (imageio) ----
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
    JSONL에서 (vector/embedding, meta) 로드
    반환:
      X: (N, D) float32
      metas: 길이 N의 dict 리스트
    """
    X, metas = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            v = o.get("vector", o.get("embedding", None))
            if v is None:
                continue
            X.append(np.asarray(v, dtype=np.float32))
            metas.append(o)
    if not X:
        raise RuntimeError(f"임베딩이 비었습니다: {path}")
    return np.vstack(X), metas


def cosine_topk(vecs: np.ndarray, metas: list, qvec: np.ndarray, k: int):
    q = qvec / (np.linalg.norm(qvec) + 1e-12)
    V = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    sims = V @ q
    idx = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i]), metas[i]) for i in idx]


def sanitize_filename(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_\-]+", "_", s)[:100]


def _count_frames(video_path: str) -> int:
    if not _HAS_IIO:
        return 0
    try:
        with iio.get_reader(video_path) as r:
            return r.count_frames()
    except Exception:
        return 0


def _step_to_frame(step_idx: int, n_steps: int, total_frames: int) -> int:
    # H5 정확 타임매핑 없을 때의 선형 근사
    if n_steps <= 1 or total_frames <= 0:
        return 0
    return round(step_idx * (total_frames - 1) / max(1, (n_steps - 1)))


def _extract_frames(video_path: str, start_f: int, end_f: int, scale_w: int = 384) -> List[Image.Image]:
    frames: List[Image.Image] = []
    if not _HAS_IIO:
        return frames
    with iio.get_reader(video_path) as r:
        for fid in range(max(0, start_f), max(0, end_f) + 1):
            try:
                arr = r.get_data(fid)
                im = Image.fromarray(arr)
                if scale_w:
                    new_w = int(scale_w)
                    new_h = int(im.height * new_w / max(1, im.width))
                    im = im.resize((new_w, new_h))
                frames.append(im)
            except Exception:
                break
    return frames


def _save_gif(frames: List[Image.Image], out_path: str, fps: int = 12):
    if not frames:
        raise RuntimeError("프레임이 비어 GIF를 만들 수 없습니다.")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / max(1, fps))
    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0, duration=duration_ms)
    return out_path


# =========================
# 임베더 로딩
# =========================
def get_siglip():
    from embedder_siglip import UnifiedEmbedder
    return UnifiedEmbedder(MODEL.model_name, device=MODEL.device, dtype=MODEL.dtype, normalize=True)

def get_clip():
    from embedder_clip import CLIPEmbedder
    return CLIPEmbedder("openai/clip-vit-base-patch32", device=MODEL.device, dtype=MODEL.dtype, normalize=True)

def get_gemma3():
    from embedder_gemma3 import Gemma3Embedder
    return Gemma3Embedder("google/gemma-3-4b-it", device=MODEL.device, dtype=MODEL.dtype, normalize=True)


# =========================
# 실행부
# =========================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--siglip_jsonl", help="SigLIP JSONL")
    ap.add_argument("--clip_jsonl", help="CLIP JSONL")
    ap.add_argument("--gemma3_jsonl", help="Gemma3 JSONL")
    ap.add_argument("--query", action="append", help="텍스트 쿼리 (여러 번 지정 가능)")
    ap.add_argument("--queries_file", help="한 줄당 하나의 쿼리 텍스트 파일")
    ap.add_argument("--topk", type=int, default=5, help="검색 상위 개수(출력용)")
    # GIF 옵션
    ap.add_argument("--gif_topn", type=int, default=1, help="모델별 상위 N개에 대해 GIF 생성 (기본 1)")
    ap.add_argument("--win", type=int, default=24, help="Top-1 기준 ±win 프레임 창")
    ap.add_argument("--fps", type=int, default=12, help="GIF FPS")
    ap.add_argument("--scale_w", type=int, default=384, help="GIF 가로 크기(px), 0이면 원본")
    ap.add_argument("--outdir", default="./previews", help="GIF 출력 폴더")
    args = ap.parse_args()

    # 쿼리 수집
    queries = []
    if args.query:
        queries.extend([q.strip() for q in args.query if q.strip()])
    if args.queries_file and os.path.exists(args.queries_file):
        with open(args.queries_file, "r", encoding="utf-8") as f:
            queries.extend([ln.strip() for ln in f if ln.strip()])
    if not queries:
        raise SystemExit("쿼리를 하나 이상 지정하세요. (--query 또는 --queries_file)")

    # 모델별 JSONL 로드 및 임베더 준비
    models = []  # (name, X, metas, embedder_loader)
    if args.siglip_jsonl:
        Xs, Ms = load_jsonl_vectors(args.siglip_jsonl)
        models.append(("SigLIP", Xs, Ms, get_siglip))
    if args.clip_jsonl:
        Xc, Mc = load_jsonl_vectors(args.clip_jsonl)
        models.append(("CLIP", Xc, Mc, get_clip))
    if args.gemma3_jsonl:
        Xg, Mg = load_jsonl_vectors(args.gemma3_jsonl)
        models.append(("Gemma3", Xg, Mg, get_gemma3))
    if not models:
        raise SystemExit("비교할 JSONL이 없습니다. (--siglip_jsonl/--clip_jsonl/--gemma3_jsonl) 중 하나 이상 지정")

    print("[OK] Loaded models:", ", ".join([n for n, *_ in models]))
    print(f"[INFO] topk={args.topk}, gif_topn={args.gif_topn}, win=±{args.win}, outdir='{args.outdir}'\n")

    # 공통 경로/정보
    video_dir = os.path.dirname(PATHS.video_path)
    n_steps = get_num_steps(PATHS.h5_path)

    # 모델별 임베더는 재사용(쿼리 여러 개일 때 성능)
    embedders = {}
    for name, _, _, loader in models:
        embedders[name] = loader()

    for qi, q in enumerate(queries, 1):
        print("=" * 100)
        print(f"[{qi}] Query: {q}")

        for name, X, metas, _ in models:
            embedder = embedders[name]
            qv = embedder.embed_texts([q])[0]
            hits = cosine_topk(X, metas, qv, k=max(args.topk, args.gif_topn))

            # 콘솔 Top-k 출력
            print(f"\n[{name}] Top-{args.topk}:")
            for r, (i, sim, m) in enumerate(hits[:args.topk], 1):
                txt = (m.get("text") or "").replace("\n", " ")[:120]
                print(f"{r:>2}. sim={sim:.3f}  step={m.get('step_idx')}  cam={m.get('camera_id')}  | {txt}...")

            # Top-N 결과에 대해 GIF 생성
            made = 0
            for rank, (i, sim, m) in enumerate(hits[:args.gif_topn], 1):
                mp4 = os.path.join(video_dir, m.get("image_ref") or os.path.basename(PATHS.video_path))
                total = _count_frames(mp4)
                center = _step_to_frame(int(m.get("step_idx", 0)), n_steps, total)
                start_f = max(0, center - args.win)
                end_f = min(max(0, total - 1), center + args.win)

                # 추출/저장
                try:
                    frames = _extract_frames(mp4, start_f, end_f, scale_w=args.scale_w)
                    if not frames:
                        print(f"  [WARN] GIF 실패(프레임 없음): {mp4}")
                        continue
                    fn = f"{sanitize_filename(q)}__{name}_top{rank}_step{m.get('step_idx')}_win{args.win}.gif"
                    out_path = os.path.join(args.outdir, fn)
                    _save_gif(frames, out_path, fps=args.fps)
                    print(f"  [OK] GIF 저장 → {out_path}")
                    made += 1
                except Exception as e:
                    print(f"  [ERR] GIF 생성 실패: {e}")

            if made == 0:
                print("  [INFO] 저장된 GIF가 없습니다.")
        print()  # blank line


if __name__ == "__main__":
    main()
