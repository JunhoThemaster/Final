# run_embed_pipeline_clip.py
# -*- coding: utf-8 -*-
"""
엔드투엔드(CLIP):
- h5에서 step/숫자요약
- 비디오에서 대표 프레임
- 라벨/메타 로드
- CLIP으로 텍스트/이미지 임베딩 생성
- 텍스트와 이미지 임베딩 평균 → ES JSONL 저장
"""
import os, json
import pandas as pd
import numpy as np
from tqdm import tqdm

from config import PATHS, MODEL, VIDEO, PIPE
from embedder_clip import CLIPEmbedder
from h5_reader import get_num_steps, sample_action_numbers
from video_reader import extract_step_frames
from text_builders import build_numeric_sentence, build_step_text
from es_schemas import build_es_doc


def _build_doc_no_enforce(*, doc_id, session_id, camera_id, step_idx, time_ms, text, embedding, image_ref=""):
    # 차원(dims) 강제 없이 비교용 JSONL 문서 생성
    return {
        "doc_id": doc_id,
        "session_id": session_id,
        "camera_id": camera_id,
        "step_idx": int(step_idx),
        "time_ms": int(time_ms) if time_ms is not None else 0,
        "text": text or "",
        "image_ref": image_ref or "",
        "embedding": list(map(float, embedding)),  # ← dims 강제 없음
    }


def _load_labels(labels_csv: str) -> pd.DataFrame:
    if not os.path.exists(labels_csv):
        raise FileNotFoundError(f"라벨 CSV를 찾을 수 없습니다: {labels_csv}")
    df = pd.read_csv(labels_csv, encoding="utf-8")
    if "idx" not in df.columns:
        df["idx"] = np.arange(len(df), dtype=int)
    for k in ("session_id", "camera_id"):
        if k not in df.columns:
            df[k] = ""
    if "time_ms" not in df.columns:
        df["time_ms"] = 0
    return df

def _load_metadata(meta_json_path: str) -> dict:
    if meta_json_path and os.path.exists(meta_json_path):
        with open(meta_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def main():
    # CLIP 결과 파일명
    out_path = os.path.splitext(PIPE.out_jsonl)[0] + ".clip.jsonl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    labels = _load_labels(PATHS.labels_csv)
    meta = _load_metadata(PATHS.metadata_json)
    current_task = meta.get("current_task", "")

    try:
        n_steps_h5 = get_num_steps(PATHS.h5_path)
    except Exception:
        n_steps_h5 = int(labels["idx"].max()) + 1

    emb = CLIPEmbedder(
        model_name="openai/clip-vit-base-patch32",
        device=MODEL.device,
        dtype=MODEL.dtype,
        normalize=PIPE.normalize
    )
    print(f"[INFO] embed_dim={emb.get_dim()}, model=CLIP")

    fout = open(out_path, "w", encoding="utf-8")
    labels_by_idx = {int(r["idx"]): r for _, r in labels.iterrows()}
    step_indices = list(range(0, n_steps_h5, PIPE.step_stride))

    for idx in tqdm(step_indices, desc="Embedding steps (CLIP)"):
        row = labels_by_idx.get(idx, {})
        session_id = str(row.get("session_id", "")) or "unknown_session"
        camera_id  = str(row.get("camera_id", "")) or "unknown_camera"
        time_ms    = int(row.get("time_ms", 0) or 0)

        num = {}
        try:
            num = sample_action_numbers(PATHS.h5_path, idx, max_joints=PIPE.text_max_joints)
        except Exception:
            pass
        numeric_sentence = build_numeric_sentence(num, ndigits=PIPE.round_ndigits)
        text = build_step_text(row, current_task=current_task, numeric_sentence=numeric_sentence)

        images = extract_step_frames(
            PATHS.video_path, n_steps_h5, idx,
            target_w=VIDEO.target_w, target_h=VIDEO.target_h,
            frames_per_step=VIDEO.frames_per_step,
            frame_window=VIDEO.frame_window
        )
        if len(images) == 0:
            text_vec = emb.embed_texts([text])[0]
            fused_vec = text_vec
        else:
            img_vecs = emb.embed_images(images)
            img_vec = img_vecs.mean(axis=0, keepdims=True)[0]
            text_vec = emb.embed_texts([text])[0]
            fused_vec = (img_vec + text_vec) / 2.0
            if PIPE.normalize:
                import numpy as np
                norm = np.linalg.norm(fused_vec) + 1e-12
                fused_vec = (fused_vec / norm).astype(np.float32)

        doc_id = f"{session_id}:{camera_id}:{idx}"
        doc = _build_doc_no_enforce(
            doc_id=doc_id,
            session_id=session_id,
            camera_id=camera_id,
            step_idx=idx,
            time_ms=time_ms,
            text=text,
            embedding=fused_vec.tolist(),  # 512차원 그대로 기록
            image_ref=os.path.basename(PATHS.video_path)
        )
        fout.write(json.dumps(doc, ensure_ascii=False) + "\n")

    fout.close()
    print(f"[DONE] ES 적재용 JSONL(CLIP) 저장: {out_path}")

if __name__ == "__main__":
    main()
