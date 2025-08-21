# PCN 멀티모달 임베딩 파이프라인 (SigLIP)

## 설치
```bash
pip install "transformers>=4.40" torch pillow opencv-python h5py numpy pandas tqdm
# GPU CUDA 빌드(옵션): pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## 입력 파일
- `trajectory.h5`
- `16787047.mp4` (혹은 대상 카메라 mp4)
- `analysis_final.csv`
- `metadata_*.json` (선택)

경로/모델 설정은 `config.py`에서 수정.

## 실행
```bash
python run_embed_pipeline.py
```
- 결과: `embeddings_es_ready.jsonl` (ES 적재용)

## 결과 빠른 검증
```bash
python verify_search.py
# 터미널에 텍스트 쿼리를 입력하면 top-5 step이 출력됩니다.
```

## ES 적재(참고)
`es_schemas.py`의 매핑 예시를 참고해 인덱스 생성 후 JSONL을 bulk로 넣으세요.
