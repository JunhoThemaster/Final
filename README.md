
# Text->Image Embedding MVP (SigLIP) — Video-level (first frame)

## 폴더 구조
```
text2video_mvp/

  artifacts/ti_only/            # 임베딩 파일(jsonl) 생성되는 디렉토리
    embeddings.jsonl            # all_labs_merged.csv와 각 랩실별 영상의 첫프레임 임베딩 파일
  
  data/                         # 샘플 데이터 (사용자가 업로드한 파일에서 복사됨)
    AUTOLab_2gb_sessions
    CLVR_2gb_sessions
    iprl_2gb_sessions
    IRIS_2gb_sessions
    PennPAL_2gb_sessions
    TRI_2gb_sessions
    all_labs_merged.csv         # 캡션이 들어간 csv 파일
  
  embedding/text2video/
    csv_indexer.py              # csv 파일 리더
    embed_batch_ti_from_csv.py  # 실제로 임베딩을 작동하는 스크립트 (영상 1개 -> 첫 프레임 임베딩 1개)
    io_first_frame.py           # 영상 및 이미지 파일 리더
    embedder_siglip.py          # SigLIP 임베더
  
  scripts/
    simple_search.py            # 텍스트 -> 이미지 검색
  requirements.txt
```

## 설치
```bash
pip install -r requirements.txt
```

## 임베딩 생성 (각 세션 아이디의 영상 1개 -> JSONL 1줄)
```bash
python embedding/text2video/embed_batch_ti_from_csv.py



```

## 임베딩시 누락 행이 있을때(강력하게 지정해서 임베딩)
```bash
python embedding\text2video\embed_batch_ti_from_csv.py ^
  --out artifacts\ti_only\embeddings.jsonl ^
  --csv data\all_labs_merged.csv ^
  --video-root data ^
  --session-col session_id ^
  --camera-col camera_id ^
  --caption-col video_summary ^
  --lab-col lab_name ^
  --docid-with-lab ^
  --device cuda ^
  --dtype float16
 ```
# 각 옵션에 대한 자세한 설명은 해당 스크립트 main 함수에 직접 적혀 있음

## 검색 (텍스트 -> 이미지) 
python scripts\search_from_jsonl.py ^
  --query "컵 집는 장면" ^
  --make-gif ^
  --video-root data ^
  --jsonl artifacts/ti_only/embeddings.jsonl 


# 쿼리는 자유롭게 변경해도 됨
# 현재 해당하는 영상의 첫 프레임이 이미지 임베딩되는 상황
# search_from_json.py를 이용해 쿼리를 임베딩해서 jsonl파일에서 유사도로 검색하는 구조
# 검색하는 기능은 text to text 임베딩과 동시에 적용되어야 한다고 생각함
# 따라서 지금 만들어진 서치 기능은 로컬 환경에서 text to img의 테스트용
# text to text 까지 고려해서 새로 만들어야함