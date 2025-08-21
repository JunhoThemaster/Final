
import os, json, argparse
from pathlib import Path
from PIL import Image
import imageio.v2 as iio

from embedder_siglip import UnifiedEmbedder

def read_first_frame(video_path, target_w=384, target_h=384):
    # Read first frame and resize to model-friendly size
    with iio.get_reader(video_path) as r:
        frame = r.get_data(0)
    img = Image.fromarray(frame).convert("RGB")
    img = img.resize((target_w, target_h))
    return img

def main():
    ap = argparse.ArgumentParser(description="Text->Image embedding (video-level, first frame only)")
    ap.add_argument("--video", required=True, help="Path to MP4")
    ap.add_argument("--metadata", default="", help="Optional metadata JSON path")
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument("--model", default="google/siglip-so400m-patch14-384")
    ap.add_argument("--device", default=None)
    ap.add_argument("--dtype", default="float16", choices=["float16","float32"])
    args = ap.parse_args()

    Path(os.path.dirname(args.out) or ".").mkdir(parents=True, exist_ok=True)

    # 1) First frame
    img = read_first_frame(args.video)

    # 2) Embed image
    emb = UnifiedEmbedder(args.model, device=args.device, dtype=args.dtype, normalize=True)
    vec_img = emb.embed_images([img])[0]

    # 3) Optional caption/meta (kept minimal; not used for search score)
    meta = {}
    if args.metadata and os.path.exists(args.metadata):
        try:
            meta = json.load(open(args.metadata, "r", encoding="utf-8"))
        except Exception:
            meta = {} 

    # 4) Build doc (video-level, vector=image embedding only)
    doc = {
        "doc_id": f"video:{meta.get('uuid','unknown')}:{meta.get('wrist_cam_serial','cam')}",
        "session_id": meta.get("uuid","unknown"),
        "camera_id":  str(meta.get("wrist_cam_serial") or meta.get("ext1_cam_serial") or "cam"),
        "step_idx":   0,
        "time_ms":    0,
        "text":       "",  # caption can be added later
        "image_ref":  os.path.basename(args.video),
        "vector":     vec_img.tolist()
    }

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print("[OK] Saved:", args.out)

if __name__ == "__main__":
    main()
