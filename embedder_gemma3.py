# embedder_gemma3.py
from typing import List, Optional
import torch, numpy as np
from PIL import Image
from transformers import AutoProcessor

try:
    from transformers import AutoModelForImageTextToText as _GemmaModelCls
except Exception:
    from transformers import AutoModelForVision2Seq as _GemmaModelCls


def _masked_mean(hidden: torch.Tensor, attn: Optional[torch.Tensor], eps: float = 1e-12) -> torch.Tensor:
    # hidden: [B,T,H], attn: [B,T] or None
    h = hidden.float()
    if attn is None:
        out = h.mean(dim=1)
    else:
        w = attn.float().unsqueeze(-1)  # [B,T,1]
        num = (h * w).sum(dim=1)        # [B,H]
        den = w.sum(dim=1) + eps        # [B,1]
        out = num / den
    out = torch.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    return out.to(hidden.dtype)

def _safe_l2_normalize(x: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    x32 = x.float()
    n = torch.linalg.norm(x32, dim=-1, keepdim=True)
    x32 = x32 / (n + eps)
    x32 = torch.nan_to_num(x32, nan=0.0, posinf=0.0, neginf=0.0)
    return x32.to(x.dtype)


class Gemma3Embedder:
    def __init__(self, model_name="google/gemma-3-4b-it", device="cuda", dtype="float16", normalize=True):
        # device / dtype
        self.device = torch.device(device if (device == "cpu" or torch.cuda.is_available()) else "cpu")
        if str(dtype).lower() in ("fp16","float16"):
            self.dtype = torch.float16
        elif str(dtype).lower() in ("bf16","bfloat16"):
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float32
        self.normalize = normalize

        # model / processor
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = _GemmaModelCls.from_pretrained(model_name, torch_dtype=self.dtype)
        self.model.to(self.device).eval()
        if hasattr(self.model.config, "output_hidden_states"):
            self.model.config.output_hidden_states = True  # forward()에서 hidden_states 켜기

        # hidden size → 임베딩 차원
        self.embed_dim = int(getattr(self.model.config, "hidden_size", 0)) or 3072

        # 정확한 이미지 시작 토큰 결정
        self._boi = getattr(self.processor, "boi_token", None) or getattr(self.processor, "image_token", None)
        if not self._boi:
            # 토큰 id → 문자열 역변환 시도
            tok_id = getattr(self.processor, "image_token_id", None)
            if tok_id is not None and hasattr(self.processor, "tokenizer"):
                try:
                    self._boi = self.processor.tokenizer.convert_ids_to_tokens(int(tok_id))
                except Exception:
                    pass
        if not self._boi:
            # 최후 폴백(일반적으로는 boi_token이 존재해야 정상)
            self._boi = "<image>"

    # -------------------- text --------------------
    @torch.inference_mode()
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.embed_dim), dtype=np.float32)

        enc = self.processor(
            text=texts,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}

        out = self.model(**enc)  # forward, not generate
        hidden = out.hidden_states[-1]  # [B,T,H]
        attn = enc.get("attention_mask", None)
        if attn is not None:
            attn = attn.to(self.device)

        pooled = _masked_mean(hidden, attn)  # [B,H]
        if self.normalize:
            pooled = _safe_l2_normalize(pooled)

        vec = pooled.detach().float().cpu().numpy()
        return vec

    # -------------------- image --------------------
    @torch.inference_mode()
    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        if not images:
            return np.empty((0, self.embed_dim), dtype=np.float32)

        vecs = []
        for img in images:
            # 이미지 1장 ↔ 이미지 토큰 1개. 절대 잘리지 않도록 truncation/padding 끔
            enc = self.processor(
                images=[img],
                text=[self._boi],
                return_tensors="pt",
                padding=False,
                truncation=False,
            )
            enc = {k: v.to(self.device) for k, v in enc.items()}

            out = self.model(**enc)
            hidden = out.hidden_states[-1]  # [1,T,H]
            attn = enc.get("attention_mask", None)
            if attn is not None:
                attn = attn.to(self.device)

            pooled = _masked_mean(hidden, attn)  # [1,H]
            if self.normalize:
                pooled = _safe_l2_normalize(pooled)

            pooled = torch.nan_to_num(pooled, nan=0.0, posinf=0.0, neginf=0.0)
            vecs.append(pooled.detach().float().cpu().numpy()[0])

        return np.stack(vecs, axis=0)  # (N,H)
