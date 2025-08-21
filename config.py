# -*- coding: utf-8 -*-
"""
전역 설정: 모델/경로/샘플링 등
- 필요 시 팀 환경에 맞게 변경
"""
from dataclasses import dataclass

@dataclass
class Paths:
    h5_path: str = r"C:\Users\jkl\Desktop\BigData\project2_pcn(LMM)\data\CLVR_2gb_sessions\failure\2023-05-15\Mon_May_15_22_22_44_2023\Mon_May_15_22_22_44_2023\trajectory.h5"
    video_path: str = r"C:\Users\jkl\Desktop\BigData\project2_pcn(LMM)\data\CLVR_2gb_sessions\failure\2023-05-15\Mon_May_15_22_22_44_2023\Mon_May_15_22_22_44_2023\recordings\MP4\20103212.mp4"
    # 분석 결과 CSV (라벨 합쳐진 파일). 트리상 여기 존재합니다.
    labels_csv: str = r"C:\Users\jkl\Desktop\BigData\project2_pcn(LMM)\data\CLVR_2gb_sessions\clvr\failure\2023-05-15\Mon_May_15_22_22_44_2023\analysis_final.csv"
    # 메타데이터 JSON
    metadata_json: str = r"C:\Users\jkl\Desktop\BigData\project2_pcn(LMM)\data\CLVR_2gb_sessions\clvr\failure\2023-05-15\Mon_May_15_22_22_44_2023\metadata_CLVR+13759f6e+2023-05-15-22h-22m-44s.json"


@dataclass
class ModelCfg:
    # SigLIP 모델은 이미지/텍스트 임베딩 차원 통일을 보장
    # (google/siglip-so400m-patch14-384: 고성능/범용)
    model_name: str = "google/siglip-so400m-patch14-384"
    device: str = "cuda"      # "cuda" | "cpu"
    dtype: str = "float16"    # "float16" | "bfloat16" | "float32"

@dataclass
class VideoCfg:
    target_w: int = 384       # SigLIP 384 권장 크기
    target_h: int = 384
    frames_per_step: int = 1  # step당 추출 프레임 수(1이면 정중앙)
    frame_window: int = 0     # ±window 내에서 고르게 추출 (0이면 중앙만)

@dataclass
class PipelineCfg:
    step_stride: int = 1      # 1이면 모든 step, 5면 0,5,10,... 샘플
    text_max_joints: int = 6   # h5에서 자연어로 담을 관절 개수
    round_ndigits: int = 3     # 수치 반올림 자리수
    out_jsonl: str = r"C:\Users\jkl\Desktop\BigData\project2_pcn(LMM)\data\pcn_embed\embeddings_es_ready.jsonl"
    normalize: bool = True     # 임베딩 L2 정규화

# 기본 설정 합치기
PATHS = Paths()
MODEL = ModelCfg()
VIDEO = VideoCfg()
PIPE  = PipelineCfg()
