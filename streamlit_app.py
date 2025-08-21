# streamlit_app.py
import os, json, numpy as np, streamlit as st
from pathlib import Path
from typing import List, Tuple
from config import PATHS, PIPE, MODEL
from embedder_siglip import UnifiedEmbedder
from h5_reader import get_num_steps
import imageio.v2 as iio  # pip install imageio imageio-ffmpeg
from PIL import Image

st.set_page_config(page_title="Robot Video Search", layout="wide")

# ---------- Utilities ----------
@st.cache_data
def load_jsonl_vectors(path: str) -> Tuple[np.ndarray, list]:
    X, metas = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            o = json.loads(line)
            v = o.get("vector")
            if v is None: continue
            X.append(np.asarray(v, dtype=np.float32))
            metas.append(o)
    return np.vstack(X), metas

@st.cache_resource
def load_embedder():
    return UnifiedEmbedder(MODEL.model_name, device=MODEL.device, dtype=MODEL.dtype, normalize=True)

def cosine_topk(vecs: np.ndarray, metas: list, qvec: np.ndarray, k: int):
    q = qvec / (np.linalg.norm(qvec) + 1e-12)
    sims = (vecs @ q) / (np.linalg.norm(vecs, axis=1) + 1e-12)
    idx = np.argsort(-sims)[:k]
    return [(float(sims[i]), metas[i]) for i in idx]

def _count_frames(video_path: str) -> int:
    try:
        with iio.get_reader(video_path) as r:
            return r.count_frames()
    except Exception:
        return 0

def _step_to_frame(step_idx: int, n_steps: int, total_frames: int) -> int:
    if n_steps <= 1 or total_frames <= 0: return 0
    return round(step_idx * (total_frames-1) / max(1, (n_steps-1)))

def extract_frames(video_path: str, start_f: int, end_f: int) -> List[Image.Image]:
    frames = []
    with iio.get_reader(video_path) as r:
        for fid in range(max(0, start_f), max(0, end_f)+1):
            try:
                arr = r.get_data(fid)
                frames.append(Image.fromarray(arr))
            except Exception:
                break
    return frames

@st.cache_data(show_spinner=False)
def ensure_gif(meta: dict, win: int = 24, fps: int = 12, scale_w: int = 384) -> str:
    """썸네일/클립 URL이 없을 때 on-the-fly GIF 생성 (캐시됨)"""
    # 1) 경로/인덱스
    video_dir = os.path.dirname(PATHS.video_path)
    mp4 = os.path.join(video_dir, meta.get("image_ref") or os.path.basename(PATHS.video_path))
    n_steps = get_num_steps(PATHS.h5_path)
    total = _count_frames(mp4)

    # 2) center_frame (문서에 있으면 우선 사용)
    center = int(meta.get("center_frame_idx") or _step_to_frame(int(meta["step_idx"]), n_steps, total))
    start, end = max(0, center-win), min(max(0,total-1), center+win)

    # 3) 프레임 추출 → 리사이즈 → GIF 저장
    frames = extract_frames(mp4, start, end)
    if not frames:
        raise RuntimeError("프레임 추출 실패")
    if scale_w:
        frames = [f.resize((scale_w, int(f.height*scale_w/f.width))) for f in frames]

    outdir = Path("previews"); outdir.mkdir(exist_ok=True)
    out = outdir / f"{meta.get('camera_id','cam')}_{meta.get('step_idx',0)}_{win}.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], loop=0, duration=int(1000/max(1,fps)))
    return str(out)

# ---------- UI ----------
st.title("🔎 Robot Video Search (Hybrid Preview)")

X, metas = load_jsonl_vectors(PIPE.out_jsonl)
embedder = load_embedder()

col1, col2 = st.columns([3,1])
with col1:
    q = st.text_input("Query", "컵을 옮기는 장면")
with col2:
    topk = st.slider("Top-K", 1, 10, 5)
    win  = st.slider("±Frames", 4, 48, 24)

if q:
    with st.spinner("Searching..."):
        qv = embedder.embed_texts([q])[0]
        hits = cosine_topk(X, metas, qv, k=topk)

    st.subheader("Results")
    for rank, (score, m) in enumerate(hits, 1):
        c1, c2 = st.columns([1,3])
        with c1:
            # 1) 우선 사전 생성 URL이 있으면 그것부터
            thumb = m.get("thumb_url")
            clip  = m.get("clip_url")
            if clip:
                st.video(clip)
            elif thumb:
                st.image(thumb)
            else:
                # 2) 없으면 on-the-fly 생성 (캐시됨)
                try:
                    gif_path = ensure_gif(m, win=win)
                    st.image(gif_path)
                except Exception as e:
                    st.error(f"미리보기 실패: {e}")

        with c2:
            st.markdown(f"**Top-{rank} · score={score:.3f}**")
            st.write(f"step={m.get('step_idx')}  cam={m.get('camera_id')}  session={m.get('session_id')}")
            st.text((m.get("text") or "")[:300])
            # 옵션: 길게 보기 버튼 → 더 큰 win으로 on-the-fly 생성
            if st.button(f"▶ 더 길게 보기 (step {m.get('step_idx')})", key=f"long_{rank}"):
                try:
                    long_gif = ensure_gif(m, win=win*2)
                    st.image(long_gif, caption="Longer preview")
                except Exception as e:
                    st.error(f"생성 실패: {e}")
