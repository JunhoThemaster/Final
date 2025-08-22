# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image
import imageio.v2 as iio

IMG_EXT = {".jpg",".jpeg",".png",".webp",".bmp"}
VID_EXT = {".mp4",".mov",".mkv",".avi"}

def read_first_frame_any(path, target_w=384, target_h=384):
    p = Path(path)
    if p.is_dir():
        imgs = sorted([q for q in p.iterdir() if q.suffix.lower() in IMG_EXT])
        if not imgs:
            raise FileNotFoundError(f"No frame images in {p}")
        img = Image.open(imgs[0]).convert("RGB")
    elif p.suffix.lower() in VID_EXT:
        with iio.get_reader(str(p)) as r:
            frame = r.get_data(0)
        img = Image.fromarray(frame).convert("RGB")
    else:
        # 단일 이미지 파일
        img = Image.open(p).convert("RGB")
    return img.resize((target_w, target_h))
