# run_embed_pipeline_gemma3.py
# -*- coding: utf-8 -*-
"""
엔드투엔드 (Gemma3 멀티모달):
- h5에서 step 개수/숫자 요약 로드
- 비디오에서 대표 프레임 추출
- 라벨/메타 읽어 자연어 텍스트 합성(text_builders)
- Gemma3으로 텍스트/이미지 임베딩 생성
- 텍스트와 이미지 임베딩 평균 융합(정규화 옵션 지원)
- 차원 강제 없이 비교/검색용 JSONL 저장 (key: 'embedding')

주의:
- es_schemas.build_es_doc()는 1152차원(SigLIP)에 맞춰져 있어 차원 불일치 에러가 납니다.
  → 여기서는 로컬 빌더(_build_doc_no_enforce)로 JSONL을 생성합니다.
- ES 적재 시에는 모델별 인덱스를 만들고 dims를 해당 모델 차원으로 설정하세요.
"""

import os
import json
import numpy as np
import pandas as pd
from tqdm import tqdm

from config import PATHS, MODEL, VIDEO, PIPE
from h5_reader import get_num_steps, sample_action_numbers
from video_reader import extract_step_frames
from text_builders import build_numeric_sentence, build_step_text
from embedder_gemma3 import Gemma3Embedder


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


def _build_doc_no_enforce(
    *,
    doc_id: str,
    session_id: str,
    camera_id: str,
    step_idx: int,
    time_ms: int,
    text: str,
    embedding: np.ndarray,
    image_ref: str = "",
) -> dict:
    """
    ES 스키마 차원 강제 없이 비교/검색용 JSONL 문서 생성.
    `embedding` 키로 저장하며, compare_models.py/검색 유틸이 이 키를 인식합니다.
    """
    return {
        "doc_id": doc_id,
        "session_id": session_id,
        "camera_id": camera_id,
        "step_idx": int(step_idx),
        "time_ms": int(time_ms) if time_ms is not None else 0,
        "text": text or "",
        "image_ref": image_ref or "",
        "embedding": list(map(float, embedding)),
    }


def main():
    # 출력 파일명: 기존 out_jsonl의 베이스에 .gemma3.jsonl를 붙입니다.
    base = os.path.splitext(PIPE.out_jsonl)[0]
    out_path = base + ".gemma3.jsonl"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # 라벨/메타 로드
    labels = _load_labels(PATHS.labels_csv)
    meta = _load_metadata(PATHS.metadata_json)
    current_task = meta.get("current_task", "")

    # step 개수 추정 (h5 불가 시 라벨 idx 최대치로 폴백)
    try:
        n_steps_h5 = get_num_steps(PATHS.h5_path)
    except Exception:
        n_steps_h5 = int(labels["idx"].max()) + 1

    # Gemma3 임베더
    emb = Gemma3Embedder(
        model_name="google/gemma-3-4b-it",  # 멀티모달 변형/경량 모델로 교체 가능
        device=MODEL.device,
        dtype=MODEL.dtype,
        normalize=PIPE.normalize,
    )
    print(f"[INFO] embed_dim≈{emb.embed_dim}, model=Gemma3")

    # step 인덱스 목록 구성
    labels_by_idx = {int(r["idx"]): r for _, r in labels.iterrows()}
    step_indices = list(range(0, n_steps_h5, PIPE.step_stride))

    written = 0
    with open(out_path, "w", encoding="utf-8") as fout:
        for idx in tqdm(step_indices, desc="Embedding steps (Gemma3)"):
            row = labels_by_idx.get(idx, {})
            session_id = str(row.get("session_id", "")) or "unknown_session"
            camera_id = str(row.get("camera_id", "")) or "unknown_camera"
            time_ms = int(row.get("time_ms", 0) or 0)

            # (1) 수치 요약 → 자연어 텍스트 합성
            nums = {}
            try:
                nums = sample_action_numbers(PATHS.h5_path, idx, max_joints=PIPE.text_max_joints)
            except Exception:
                pass
            numeric_sentence = build_numeric_sentence(nums, ndigits=PIPE.round_ndigits)
            text = build_step_text(row, current_task=current_task, numeric_sentence=numeric_sentence)

            # (2) 대표 프레임 추출
            images = extract_step_frames(
                PATHS.video_path,
                n_steps_h5,
                idx,
                target_w=VIDEO.target_w,
                target_h=VIDEO.target_h,
                frames_per_step=VIDEO.frames_per_step,
                frame_window=VIDEO.frame_window,
            )

            # (3) 텍스트/이미지 임베딩 & 융합
            text_vec = emb.embed_texts([text])[0]
            if len(images) == 0:
                fused_vec = text_vec
            else:
                img_vecs = emb.embed_images(images)  # (F, D)
                img_vec = img_vecs.mean(axis=0)      # 대표 프레임 평균
                fused_vec = (img_vec + text_vec) / 2.0
                if PIPE.normalize:
                    norm = np.linalg.norm(fused_vec) + 1e-12
                    fused_vec = (fused_vec / norm).astype(np.float32)

            # (4) JSONL 기록 (차원 강제 없음)
            doc_id = f"{session_id}:{camera_id}:{idx}"
            doc = _build_doc_no_enforce(
                doc_id=doc_id,
                session_id=session_id,
                camera_id=camera_id,
                step_idx=idx,
                time_ms=time_ms,
                text=text,
                embedding=fused_vec.tolist(),
                image_ref=os.path.basename(PATHS.video_path),
            )
            fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
            written += 1

    print(f"[DONE] 비교/검색용 JSONL(Gemma3) 저장: {out_path}  (written={written})")


if __name__ == "__main__":
    main()
