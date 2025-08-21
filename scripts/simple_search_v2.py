# -*- coding: utf-8 -*-
import os, sys, argparse, json, time, numpy as np

# embedder_siglip.py 경로 추가
THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(THIS, "..", "embedding", "text2video"))

# Windows에서 출력 깨짐 방지
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from embedder_siglip import UnifiedEmbedder

def log(msg):
    print(msg, flush=True)

def load_jsonl_vectors(path: str):
    log(f"[1/5] JSONL 로드: {os.path.abspath(path)}")
    n_total = 0
    vecs, metas = [], []
    if not os.path.exists(path):
        raise SystemExit(f"파일이 없습니다: {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            n_total += 1
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            v = obj.get("vector")
            if v is None:
                continue
            vecs.append(v)
            metas.append(obj)
    X = np.asarray(vecs, dtype=np.float32)
    log(f"  - 전체 라인: {n_total}, 유효 벡터: {len(vecs)}")
    if X.size == 0:
        raise SystemExit("No vectors found in JSONL (vector 필드가 없는지 확인).")
    return X, metas

def l2norm(a, axis=None, eps=1e-12):
    n = np.linalg.norm(a, axis=axis, keepdims=True)
    return a / (n + eps)

def cosine_topk(X: np.ndarray, q: np.ndarray, k: int = 5):
    # 안전하게 L2 정규화
    Xn = l2norm(X, axis=1)
    qn = q / (np.linalg.norm(q) + 1e-12)
    sims = Xn @ qn
    idx = np.argsort(-sims)[:k]
    return idx, sims[idx]

def main():
    ap = argparse.ArgumentParser(description="Text->Image cosine search (diagnostic verbose)")
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--model", default="google/siglip-so400m-patch14-384")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--device", default=None)           # cuda / cpu
    ap.add_argument("--dtype", default="float16", choices=["float16","float32"])
    args = ap.parse_args()

    X, metas = load_jsonl_vectors(args.jsonl)
    log(f"[2/5] 문서 행렬 모양: {X.shape}")

    log(f"[3/5] 임베더 로드: model={args.model}, device={args.device or '(auto)'} dtype={args.dtype}")
    emb = UnifiedEmbedder(args.model, device=args.device, dtype=args.dtype, normalize=True)

    t0 = time.time()
    qv = emb.embed_texts([args.query])[0].astype(np.float32)
    log(f"  - 쿼리 임베딩 완료: shape={qv.shape}, elapsed={time.time()-t0:.2f}s")

    log(f"[4/5] 코사인 Top-{args.topk} 계산")
    idx, sims = cosine_topk(X, qv, args.topk)

    log(f"[5/5] 결과")
    for rank, (i, s) in enumerate(zip(idx, sims), 1):
        m = metas[i]
        print(f"{rank}. score={s:.4f} | doc_id={m.get('doc_id')} | image_ref={m.get('image_ref')}", flush=True)

if __name__ == "__main__":
    main()
