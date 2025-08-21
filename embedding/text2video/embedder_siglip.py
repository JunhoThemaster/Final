# -*- coding: utf-8 -*-
"""
SigLIP 기반 멀티모달 임베딩 유틸
- 이미지와 텍스트를 같은 임베딩 공간/차원으로 생성
- 통합 forward가 아닌 전용 함수(get_*_features) 사용으로 안전화
"""

from typing import List
import torch
import numpy as np
from PIL import Image
from transformers import SiglipProcessor, SiglipModel


class UnifiedEmbedder:
    """
    SigLIP 통합 임베더
    - embed_texts(List[str])  -> (N, D)
    - embed_images(List[Image.Image]) -> (N, D)
    - 차원 D 동일 (모델에 따라 768/1024/1152 등)
    """
    def __init__(
        self,
        model_name: str,
        device: str = "cuda",
        dtype: str = "float16",
        normalize: bool = True,
    ):
        # 디바이스/정규화
        self.device = torch.device(device if (device == "cpu" or torch.cuda.is_available()) else "cpu")
        self.normalize = normalize

        # dtype
        if dtype.lower() in ("fp16", "float16"):
            self.dtype = torch.float16
        elif dtype.lower() in ("bf16", "bfloat16"):
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float32  # CPU 권장

        # Processor & Model (여기서 forward 호출 금지!)
        self.processor = SiglipProcessor.from_pretrained(model_name)
        self.model = SiglipModel.from_pretrained(model_name, torch_dtype=self.dtype)
        self.model.to(self.device).eval()

        # 임베딩 차원: config.projection_dim 사용 (없으면 추후 첫 임베딩 시 확정)
        self.embed_dim = int(getattr(self.model.config, "projection_dim", 0)) or 0

    # -----------------------------
    # 텍스트 임베딩
    # -----------------------------
    @torch.inference_mode()
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if len(texts) == 0:
            return np.empty((0, self.embed_dim or 0), dtype=np.float32)

        # tokenizer → ids, mask
        enc = self.processor(
            text=texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        input_ids = enc.get("input_ids", None)
        attention_mask = enc.get("attention_mask", None)
        if input_ids is None:
            # SigLIP 텍스트 경로는 input_ids가 반드시 있어야 함
            raise ValueError("SigLIP 텍스트 임베딩에 필요한 input_ids가 생성되지 않았습니다.")

        input_ids = input_ids.to(self.device)
        attention_mask = attention_mask.to(self.device) if attention_mask is not None else None

        # ⚠️ 통합 forward 금지: 전용 함수 사용
        emb = self.model.get_text_features(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )  # (B, D)

        if self.embed_dim == 0:
            self.embed_dim = int(emb.shape[-1])

        if self.normalize:
            emb = torch.nn.functional.normalize(emb, p=2, dim=-1)

        return emb.detach().cpu().numpy().astype(np.float32)

    # -----------------------------
    # 이미지 임베딩
    # -----------------------------
    @torch.inference_mode()
    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        if len(images) == 0:
            return np.empty((0, self.embed_dim or 0), dtype=np.float32)

        # processor → pixel_values
        enc = self.processor(
            images=images,
            return_tensors="pt",
        )
        pixel_values = enc.get("pixel_values", None)
        if pixel_values is None:
            raise ValueError("SigLIP 이미지 임베딩에 필요한 pixel_values가 생성되지 않았습니다.")

        pixel_values = pixel_values.to(self.device)

        # ⚠️ 통합 forward 금지: 전용 함수 사용
        emb = self.model.get_image_features(pixel_values=pixel_values)  # (B, D)

        if self.embed_dim == 0:
            self.embed_dim = int(emb.shape[-1])

        if self.normalize:
            emb = torch.nn.functional.normalize(emb, p=2, dim=-1)

        return emb.detach().cpu().numpy().astype(np.float32)

    # -----------------------------
    # 텍스트/이미지 쌍 임베딩 결합
    # -----------------------------
    def embed_pair_and_fuse(self, texts: List[str], images: List[Image.Image], mode: str = "mean") -> np.ndarray:
        te = self.embed_texts(texts)
        ie = self.embed_images(images)
        assert te.shape[0] == ie.shape[0], "텍스트/이미지 배치 크기가 다릅니다."

        if mode == "mean":
            fused = (te + ie) / 2.0
        else:
            # 필요 시 가중 평균/concat 등 확장
            fused = (te + ie) / 2.0

        if self.normalize:
            denom = np.linalg.norm(fused, axis=1, keepdims=True) + 1e-12
            fused = fused / denom
        return fused

    def get_dim(self) -> int:
        return int(self.embed_dim)
