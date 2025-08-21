# -*- coding: utf-8 -*-
"""
step→frame 매핑 및 프레임 추출
- h5 step 인덱스와 비디오 프레임 개수를 선형 매핑
"""
from typing import List
import cv2
from PIL import Image

def _step_to_frame(step_idx: int, n_steps: int, total_frames: int) -> int:
    if n_steps <= 1 or total_frames <= 0:
        return 0
    return int(round(step_idx * (total_frames - 1) / max(1, (n_steps - 1))))

def extract_step_frames(
    video_path: str,
    n_steps: int,
    step_idx: int,
    target_w: int,
    target_h: int,
    frames_per_step: int = 1,
    frame_window: int = 0
) -> List[Image.Image]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"비디오를 열 수 없습니다: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    center = _step_to_frame(step_idx, n_steps, total)
    frame_ids = [center]

    if frames_per_step > 1 and frame_window > 0:
        lo = max(0, center - frame_window)
        hi = min(total - 1, center + frame_window)
        if hi > lo:
            stride = max(1, (hi - lo) // (frames_per_step - 1))
            frame_ids = list(range(lo, hi + 1, stride))[:frames_per_step]

    images: List[Image.Image] = []
    for fid in frame_ids:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fid))
        ok, fr = cap.read()
        if not ok:
            continue
        fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        fr = cv2.resize(fr, (target_w, target_h))
        images.append(Image.fromarray(fr))
    cap.release()
    return images
