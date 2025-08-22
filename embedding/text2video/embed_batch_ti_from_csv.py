# -*- coding: utf-8 -*-
"""
CSV 기반 배치 임베딩 (첫 프레임만 사용)
- CSV 인덱스(csv_indexer)에서 세션/캡션/카메라 정보를 읽음
- data_finder 를 이용해 비디오 루트 경로 및 파일 매칭
- 첫 프레임을 읽어 임베딩 생성
- JSONL 포맷으로 저장 (한 줄 = 한 세션)
"""

import json
import argparse
from pathlib import Path
import sys

# 현재 파일 경로를 sys.path에 추가 (로컬 모듈 import 가능하게 설정)
THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS))

# 로컬 모듈 임포트
from csv_indexer import discover_csv, build_session_index
from data_finder import discover_video_roots, resolve_video_exact
from embedder_siglip import UnifiedEmbedder
from io_first_frame import read_first_frame_any


# 이미 저장된 JSONL에서 doc_id(중복 방지용 키) 로드
def load_existing_doc_ids(out_jsonl: Path) -> set:
    seen = set()
    if not out_jsonl.exists():  # 파일이 없으면 빈 set 반환
        return seen
    with open(out_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                did = obj.get("doc_id")
                if did:
                    seen.add(did)  # 중복 체크용으로 set에 추가
            except Exception:
                pass
    return seen


def main():
    # -----------------------
    # 1) 인자 파서 설정
    # -----------------------
    ap = argparse.ArgumentParser(description="Batch embed first-frame (CSV-only)")
    # CSV 경로 (미지정 시 csv_indexer.discover_csv()가 기본값)
    ap.add_argument("--csv", default="", help="(선택) CSV 경로. 미지정 시 csv_indexer의 기본을 사용")
    # 출력 및 임베딩 옵션
    ap.add_argument("--out", default="artifacts/ti_only/embeddings.jsonl",
                    help="출력 JSONL 파일 경로")
    ap.add_argument("--model", default="google/siglip-so400m-patch14-384",
                    help="사용할 임베딩 모델")
    ap.add_argument("--device", default="cuda", help="디바이스 (cuda / cpu)")
    ap.add_argument("--dtype", default="float16", choices=["float16", "float32", "bfloat16"],
                    help="임베딩 연산 데이터 타입")
    ap.add_argument("--target-w", type=int, default=384, help="입력 이미지 가로 크기")
    ap.add_argument("--target-h", type=int, default=384, help="입력 이미지 세로 크기")
    ap.add_argument("--docid-with-lab", dest="docid_with_lab", action="store_true",
                    help="doc_id 생성 시 lab 이름 포함 여부")
    # 비디오 루트 경로 (없으면 data/ 디렉토리 자동 탐색)
    ap.add_argument("--video-root", nargs="*", default=None,
                    help="비디오 루트 디렉토리 경로")
    args = ap.parse_args()

    # -----------------------
    # 2) CSV 인덱스 생성
    # -----------------------
    # CSV 파일 경로 결정 (직접 지정 or 기본 discover_csv)
    csv_path = Path(args.csv).resolve() if args.csv else discover_csv()
    # 세션별 인덱스 딕셔너리 생성 (session_id → {lab, camera_id, caption})
    idx = build_session_index(str(csv_path))
    print("[INFO] parsed sessions:", len(idx))
    if idx:
        # 샘플 한 개 출력 (디버깅용)
        sample_key = next(iter(idx))
        print("[INFO] sample:", sample_key, idx[sample_key])

    # -----------------------
    # 3) 임베딩 모델 로드
    # -----------------------
    emb = UnifiedEmbedder(
        args.model,
        device=args.device,
        dtype=args.dtype,
        normalize=True  # 벡터 정규화 여부
    )

    # -----------------------
    # 4) 출력 파일/중복 관리
    # -----------------------
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)  # 출력 폴더 생성
    seen = load_existing_doc_ids(out_path)  # 기존 doc_id 중복 체크
    mode = "a" if out_path.exists() else "w"  # 기존 있으면 append

    # -----------------------
    # 5) 비디오 루트 경로 탐색
    # -----------------------
    if args.video_root:
        # 명시적으로 주어진 루트 사용
        roots = [Path(r).resolve() for r in args.video_root]
    else:
        # 자동 탐색: 기본적으로 ./data/ 아래 3단계 깊이까지 검색
        roots = discover_video_roots(base_dirs=("data",), lab_names=(), max_depth=3)
    print("[INFO] roots to search:")
    for r in roots:
        print(" -", r)

    # -----------------------
    # 6) 메인 루프: 세션별 처리
    # -----------------------
    n_ok = n_skip = n_miss = 0
    with open(out_path, mode, encoding="utf-8") as fout:
        for sid, info in idx.items():
            cam = (info.get("camera_id", "") or "cam")
            lab = info.get("lab", "")
            caption = info.get("caption", "")

            # doc_id 생성 (lab 포함 여부 옵션)
            doc_id = f"video:{lab}:{sid}:{cam}" if args.docid_with_lab else f"video:{sid}:{cam}"
            if doc_id in seen:
                # 이미 처리된 세션이면 건너뜀
                n_skip += 1
                continue

            # 비디오 파일 경로 찾기 (lab, session_id, camera_id 기반)
            res = resolve_video_exact(roots, lab, sid, cam)
            if not res:
                n_miss += 1
                continue

            try:
                # 첫 프레임 읽기 (리사이즈 포함)
                img = read_first_frame_any(
                    str(res), target_w=args.target_w, target_h=args.target_h
                )
                # 임베딩 계산
                vec = emb.embed_images([img])[0]
            except Exception as e:
                # 임베딩 실패 시 miss 처리
                n_miss += 1
                print(f"[ERR] {sid}/{cam} embed fail: {e}")
                continue

            # JSONL 문서 구성
            doc = {
                "doc_id":     doc_id,
                "session_id": sid,
                "camera_id":  cam,
                "lab":        lab,
                "text":       caption,
                "image_ref":  Path(res).name,
                "step_idx":   0,   # 첫 프레임이므로 항상 0
                "time_ms":    0,   # 첫 프레임은 시간 0으로 간주
                "vector":     vec.tolist(),
            }
            # 한 줄 단위로 JSONL에 기록
            fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
            seen.add(doc_id)
            n_ok += 1

    # -----------------------
    # 7) 결과 요약 출력
    # -----------------------
    print(f"[DONE] new={n_ok}, skipped(dup)={n_skip}, not_found={n_miss}, total_sessions={len(idx)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
