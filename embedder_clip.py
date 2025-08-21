# embedder_clip.py
# -*- coding: utf-8 -*-
"""
CLIP 기반 멀티모달 임베딩 유틸
- 이미지와 텍스트를 같은 임베딩 공간/차원으로 생성
- SigLIP과 동일한 인터페이스 제공(embed_texts, embed_images)
"""

from typing import List
import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

class CLIPEmbedder:
    """
    CLIP 임베더
    - embed_texts(List[str])  -> (N, D)
    - embed_images(List[Image.Image]) -> (N, D)
    """
    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: str = "cuda",
        dtype: str = "float16",
        normalize: bool = True,
    ):
        self.device = torch.device(device if (device == "cpu" or torch.cuda.is_available()) else "cpu")
        self.normalize = normalize

        # dtype 설정 (CLIP은 fp16 권장)
        if str(dtype).lower() in ("fp16", "float16"):
            self.dtype = torch.float16
        elif str(dtype).lower() in ("bf16", "bfloat16"):
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float32

        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name, torch_dtype=self.dtype)
        self.model.to(self.device).eval()

        # 투영 차원
        self.embed_dim = int(getattr(self.model.config, "projection_dim", 0)) or 0

    @torch.inference_mode()
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if len(texts) == 0:
            return np.empty((0, self.embed_dim or 0), dtype=np.float32)
        enc = self.processor(text=texts, padding=True, truncation=True, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        emb = self.model.get_text_features(**enc)  # (B, D)
        if self.embed_dim == 0:
            self.embed_dim = int(emb.shape[-1])
        if self.normalize:
            emb = torch.nn.functional.normalize(emb, p=2, dim=-1)
        return emb.detach().cpu().numpy().astype(np.float32)

    @torch.inference_mode()
    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        if len(images) == 0:
            return np.empty((0, self.embed_dim or 0), dtype=np.float32)
        enc = self.processor(images=images, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        emb = self.model.get_image_features(**enc)  # (B, D)
        if self.embed_dim == 0:
            self.embed_dim = int(emb.shape[-1])
        if self.normalize:
            emb = torch.nn.functional.normalize(emb, p=2, dim=-1)
        return emb.detach().cpu().numpy().astype(np.float32)

    def get_dim(self) -> int:
        return int(self.embed_dim)





