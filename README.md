
# Text->Image Embedding MVP (SigLIP) — Video-level (first frame)

## 폴더 구조
```
text2video_mvp/
  data/                         # 샘플 데이터 (사용자가 업로드한 파일에서 복사됨)
    16787047.mp4
    metadata_CLVR+13759f6e+2023-05-15-22h-22m-44s.json
    trajectory.h5
    analysis_final.csv
  artifacts/ti_only/            # 출력(JSONL)
  embedding/text2video/
    embed_ti_video_level.py     # 영상 1개 -> 첫 프레임 임베딩 1개
    embedder_siglip.py          # SigLIP 임베더
  scripts/
    simple_search.py            # 텍스트 -> 이미지 검색
  requirements.txt
```

## 설치
```bash
pip install -r requirements.txt
```

## 임베딩 생성 (영상 1개 -> JSONL 1줄)
```bash
python embedding/text2video/embed_ti_video_level.py \
  --video data/16787047.mp4 \
  --metadata data/metadata_CLVR+13759f6e+2023-05-15-22h-22m-44s.json \
  --out artifacts/ti_only/embeddings.jsonl
```

## 검색 (텍스트 -> 이미지)
python -u scripts\simple_search_v2.py --jsonl artifacts\ti_only\embeddings.jsonl --query "컵을 집어 이동하는 장면" --device cuda