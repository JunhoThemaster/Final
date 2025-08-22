# -*- coding: utf-8 -*-
"""
Text→Image cosine search (+ optional GIF)
- embeddings.jsonl 로드 → 텍스트 쿼리 임베딩 → 코사인 Top-K
- (선택) data_finder 로 비디오 경로 찾고 GIF 저장
"""

import os, sys, argparse, json, time, re
from pathlib import Path
import numpy as np

# 로컬 모듈 경로 (embedding/text2video)
THIS = Path(__file__).resolve().parent
for p in (THIS / "embedding" / "text2video", THIS.parent / "embedding" / "text2video"):
    if p.is_dir():
        sys.path.insert(0, str(p))

# Windows 콘솔 한글 출력
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# 필수 모듈
try:
    from embedder_siglip import UnifiedEmbedder
    from data_finder import discover_video_roots, resolve_video_exact
except Exception as e:
    raise SystemExit(f"[ERR] 로컬 모듈 임포트 실패: {e}")

# (GIF 옵션용) cv2 / imageio
try:
    import cv2
except Exception as e:
    cv2 = None
try:
    import imageio.v2 as imageio
except Exception as e:
    imageio = None


# ---------- 유틸 ----------
def log(msg: str) -> None:
    print(msg, flush=True)

def l2norm(a, axis=None, eps=1e-12):
    n = np.linalg.norm(a, axis=axis, keepdims=True)
    return a / (n + eps)

def cosine_topk(X: np.ndarray, q: np.ndarray, k: int = 5):
    Xn = l2norm(X, axis=1)
    qn = q / (np.linalg.norm(q) + 1e-12)
    sims = Xn @ qn
    idx = np.argsort(-sims)[:k]
    return idx, sims[idx]

def _safe_name(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"[^A-Za-z0-9가-힣._-]+", "_", s) or "query"

def _fast_find_by_image_ref(roots: list[Path], image_ref: str) -> Path | None:
    """image_ref(파일명)가 있으면 이름 정확 일치로 빠르게 찾기."""
    if not image_ref:
        return None
    low = image_ref.lower()
    for r in roots:
        # 최댓 3개 찾으면 즉시 반환(성능 위해 조기 종료)
        hits = []
        for p in r.rglob(image_ref):
            if p.name.lower() == low:
                hits.append(p)
                if len(hits) >= 3:
                    break
        if hits:
            hits.sort(key=lambda p: (len(str(p)), p.as_posix().lower()))
            return hits[0]
    return None


# ---------- 데이터 로드 ----------
def load_jsonl_vectors(path: str) -> tuple[np.ndarray, list[dict]]:
    log(f"[1/5] JSONL 로드: {Path(path).resolve()}")
    if not Path(path).exists():
        raise SystemExit(f"[ERR] 파일이 없습니다: {path}")
    vecs, metas = [], []
    n_total = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            n_total += 1
            line = (line or "").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            v = obj.get("vector")
            if v is None:
                continue
            vecs.append(v)
            metas.append(obj)
    X = np.asarray(vecs, dtype=np.float32)
    log(f"  - 전체 라인: {n_total:,} | 유효 벡터: {len(vecs):,}")
    if X.size == 0:
        raise SystemExit("[ERR] JSONL에 vector 필드가 없습니다.")
    return X, metas


# ---------- GIF ----------
def extract_gif(video_path: str, out_path: str,
                center_ms=0, pre_ms=1000, post_ms=1000, fps=8, out_width: int | None = 384):
    if imageio is None or cv2 is None:
        raise SystemExit("[ERR] GIF 생성을 위해 imageio, opencv-python 이 필요합니다.")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"비디오를 열 수 없습니다: {video_path}")
    try:
        fps_vid = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        dur_ms  = int(1000.0 * total / max(fps_vid, 1e-6))
        start_ms = max(0, int(center_ms) - int(pre_ms))
        end_ms   = min(dur_ms, int(center_ms) + int(post_ms))
        if end_ms <= start_ms:
            start_ms, end_ms = 0, min(dur_ms, 2000)
        step_ms = max(1, int(1000.0 / max(int(fps), 1)))
        timestamps = range(start_ms, end_ms, step_ms)

        frames = []
        for t in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(t))
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            if out_width and out_width > 0:
                h, w = frame.shape[:2]
                new_w = int(out_width)
                new_h = max(1, int(h * (new_w / float(max(w, 1)))))
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        if not frames:
            raise RuntimeError("선택 구간에서 프레임을 읽지 못했습니다.")
        imageio.mimsave(out_path, frames, duration=1.0 / float(max(int(fps), 1)))
        return {"frames": len(frames), "start_ms": start_ms, "end_ms": end_ms, "fps": fps}
    finally:
        cap.release()


# ---------- 메인 ----------
def main():
    ap = argparse.ArgumentParser(description="Text→Image cosine search (+ optional GIF)")
    ap.add_argument("--jsonl", default="artifacts/ti_only/embeddings.jsonl",
                    help="임베딩 JSONL 경로")
    ap.add_argument("--query", required=True, help="텍스트 쿼리")
    ap.add_argument("--model", default="google/siglip-so400m-patch14-384")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--device", default=None, help="cuda / cpu (생략 시 자동)")
    ap.add_argument("--dtype", default="float16", choices=["float16", "float32"])

    # GIF 옵션
    ap.add_argument("--make-gif", action="store_true", help="Top-K에서 GIF 생성")
    ap.add_argument("--gif-topk", type=int, default=5)
    ap.add_argument("--gif-dir", default="gif", help="GIF 출력 기본 폴더 (기본: ./gif)")
    ap.add_argument("--gif-center-ms", type=int, default=None)
    ap.add_argument("--gif-pre-ms", type=int, default=1000)
    ap.add_argument("--gif-post-ms", type=int, default=1000)
    ap.add_argument("--gif-fps", type=int, default=8)
    ap.add_argument("--gif-width", type=int, default=384)
    ap.add_argument("--video-root", nargs="*", default=None, help="비디오 루트(여러 개 가능). 생략 시 ./data 자동")

    args = ap.parse_args()

    # 장치/정밀도 보정
    try:
        import torch  # noqa
        has_cuda = torch.cuda.is_available()
    except Exception:
        has_cuda = False
    if args.device is None:
        args.device = "cuda" if has_cuda else "cpu"
    if args.dtype == "float16" and args.device == "cpu":
        args.dtype = "float32"

    # 1) 임베딩 로드
    X, metas = load_jsonl_vectors(args.jsonl)
    log(f"[2/5] 문서 행렬: {X.shape}")

    # 2) 임베더 & 쿼리 임베딩
    log(f"[3/5] 임베더 로드: model={args.model}, device={args.device}, dtype={args.dtype}")
    emb = UnifiedEmbedder(args.model, device=args.device, dtype=args.dtype, normalize=True)
    t0 = time.time()
    qv = emb.embed_texts([args.query])[0].astype(np.float32)
    log(f"  - 쿼리 임베딩 완료 ({time.time()-t0:.2f}s)")

    # 3) 코사인 Top-K (중복 제거: lab/sid/cam/image_ref 기준)
    log(f"[4/5] 코사인 Top-{args.topk}")
    idx, sims = cosine_topk(X, qv, args.topk)
    seen = set()
    uniq_idx, uniq_sims = [], []
    for i, s in zip(idx, sims):
        m = metas[int(i)]
        key = ((m.get("lab") or "").lower(),
               (m.get("session_id") or "").lower(),
               (m.get("camera_id") or "").lower(),
               (m.get("image_ref") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        uniq_idx.append(int(i))
        uniq_sims.append(float(s))
    idx = np.array(uniq_idx, dtype=int)
    sims = np.array(uniq_sims, dtype=float)

    # 결과 표시
    log("[5/5] 검색 결과")
    for rank, (i, s) in enumerate(zip(idx, sims), 1):
        m = metas[int(i)]
        text = (m.get("text") or "").replace("\n", " ")
        if len(text) > 60:
            text = text[:60] + "…"
        print(f"{rank:>2}. score={s:7.4f} | lab={m.get('lab')} "
              f"| doc_id={m.get('doc_id')} | image_ref={m.get('image_ref')} | text=\"{text}\"")

    # === (옵션) GIF ===
    if not args.make_gif:
        return

    if imageio is None or cv2 is None:
        raise SystemExit("[ERR] GIF 생성을 위해 imageio, opencv-python 이 필요합니다. "
                         "pip install imageio opencv-python")

    # 루트: 명시 없으면 ./data 를 기본으로
    labs_hint = {(metas[int(i)].get("lab") or "") for i in idx[:args.gif_topk]}
    roots = [Path(r).resolve() for r in args.video_root] if args.video_root else \
            discover_video_roots(base_dirs=("data",), lab_names=labs_hint, max_depth=3)
    for r in roots:
        print(" - search root:", r)

    # 출력 폴더
    out_base = Path(args.gif_dir).resolve()
    qdir = out_base / _safe_name(args.query)
    qdir.mkdir(parents=True, exist_ok=True)

    saved = set()
    for rank, i in enumerate(idx[:args.gif_topk], 1):
        m = metas[int(i)]
        lab = m.get("lab") or ""
        sid = m.get("session_id") or ""
        cam = m.get("camera_id") or ""
        imgref = m.get("image_ref") or ""
        center = args.gif_center_ms if args.gif_center_ms is not None else int(m.get("time_ms") or 0)

        # 1) image_ref로 빠른 탐색 → 2) 실패 시 규칙 기반 탐색
        vpath = _fast_find_by_image_ref(roots, imgref) or \
                resolve_video_exact(roots, lab, sid, cam)
        if not vpath:
            print(f"[WARN] 영상 미발견: lab={lab} sid={sid} cam={cam} imgref={imgref}")
            continue

        abspath = Path(vpath).resolve().as_posix().lower()
        if abspath in saved:
            print(f"[SKIP] 중복 영상: {vpath}")
            continue
        saved.add(abspath)

        name = f"{rank:02d}_{_safe_name(lab)}_{_safe_name(sid)}_{_safe_name(cam)}.gif"
        out_path = (qdir / name).as_posix()
        try:
            info = extract_gif(
                str(vpath), out_path,
                center_ms=center,
                pre_ms=args.gif_pre_ms,
                post_ms=args.gif_post_ms,
                fps=args.gif_fps,
                out_width=(args.gif_width if args.gif_width > 0 else None),
            )
            print(f"[GIF] saved: {out_path} | frames={info['frames']} "
                  f"| window={info['start_ms']}~{info['end_ms']}ms | from={vpath}")
        except Exception as e:
            print(f"[ERR] GIF 실패: {out_path} :: {e}")

if __name__ == "__main__":
    main()
