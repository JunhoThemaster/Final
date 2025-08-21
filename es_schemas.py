# -*- coding: utf-8 -*-
"""
엘라스틱서치 매핑/도큐먼트 스키마 예시
"""
ES_MAPPING_EXAMPLE = r"""
PUT pcn_robot_embeddings
{
  "mappings": {
    "properties": {
      "doc_id":      { "type": "keyword" },
      "session_id":  { "type": "keyword" },
      "camera_id":   { "type": "keyword" },
      "step_idx":    { "type": "integer" },
      "time_ms":     { "type": "long" },
      "text":        { "type": "text" },
      "image_ref":   { "type": "keyword" },
      "vector": {
        "type": "dense_vector",
        "dims": 1152,                 
        "similarity": "cosine",
        "index": true
      }
    }
  }
}
"""

def build_es_doc(
    *,
    doc_id: str,
    session_id: str,
    camera_id: str,
    step_idx: int,
    time_ms: int,
    text: str,
    embedding: list,
    image_ref: str = ""
) -> dict:
    return {
        "doc_id": doc_id,
        "session_id": session_id,
        "camera_id": camera_id,
        "step_idx": step_idx,
        "time_ms": int(time_ms) if time_ms is not None else 0,
        "text": text,
        "image_ref": image_ref,
        "vector": embedding
    }



# ##==========추가 확장용 =============#

# # -*- coding: utf-8 -*-
# """
# 엘라스틱서치 매핑/도큐먼트 스키마 예시 (기존 형식 유지, 필드만 보강)
# - text: 기본 text 필드
# - vector: dense_vector(1152, cosine)
# - labels/meta: 명시 스키마
# - feat.*: 동적 템플릿으로 숫자→float, bool→boolean, 그 외→keyword
# """
# ES_MAPPING_EXAMPLE = r"""
# PUT pcn_robot_embeddings
# {
#   "mappings": {
#     "dynamic": false,
#     "dynamic_templates": [
#       { "feat_numbers":  { "path_match": "feat.*", "match_mapping_type": "number",  "mapping": { "type": "float"   } } },
#       { "feat_booleans": { "path_match": "feat.*", "match_mapping_type": "boolean", "mapping": { "type": "boolean" } } },
#       { "feat_strings":  { "path_match": "feat.*", "match_mapping_type": "string",  "mapping": { "type": "keyword", "ignore_above": 256 } } }
#     ],
#     "properties": {
#       "doc_id":      { "type": "keyword" },
#       "session_id":  { "type": "keyword" },
#       "camera_id":   { "type": "keyword" },
#       "step_idx":    { "type": "integer" },
#       "time_ms":     { "type": "long" },
#       "text":        { "type": "text" },
#       "image_ref":   { "type": "keyword" },

#       "vector": {
#         "type": "dense_vector",
#         "dims": 1152,
#         "similarity": "cosine",
#         "index": true
#       },

#       "labels": {
#         "properties": {
#           "label_state":     { "type": "keyword" },
#           "sub_label":       { "type": "keyword" },
#           "attributes":      { "type": "keyword" },
#           "confidence":      { "type": "keyword" },
#           "is_uncertain":    { "type": "boolean" },
#           "presented_order": { "type": "integer" },
#           "desc_major":      { "type": "text" },
#           "desc_sub":        { "type": "text" },
#           "desc_attrs":      { "type": "text" },
#           "description":     { "type": "text" },
#           "nl_tags":         { "type": "keyword", "ignore_above": 256 }
#         }
#       },

#       "meta": {
#         "properties": {
#           "uuid":             { "type": "keyword" },
#           "lab":              { "type": "keyword" },
#           "user":             { "type": "keyword" },
#           "user_id":          { "type": "keyword" },
#           "date":             { "type": "keyword" },     # 날짜 문자열 그대로 저장(필요시 date로 변경)
#           "scene_id":         { "type": "long" },
#           "success":          { "type": "boolean" },
#           "robot_serial":     { "type": "keyword" },
#           "current_task":     { "type": "text" },
#           "trajectory_length":{ "type": "integer" }
#         }
#       },

#       "feat": { "type": "object", "dynamic": true }
#     }
#   }
# }
# """

# # -----------------------------------------------
# # 빌더 (기존 시그니처 유지 + 선택 인자만 추가)
# # - 슬래시 경로를 점 표기로 통일(feat key)
# # - vector 길이(1152) 검증
# # - labels.nl_tags: "a;b;c" → ["a","b","c"]로 정규화(옵션)
# # -----------------------------------------------
# from typing import Dict, Any, Iterable, Union
# import math

# _DIMS = 1152

# def _ensure_dims(vec: Iterable[Union[int, float]], dims: int = _DIMS) -> list:
#     v = []
#     for x in vec:
#         if x is None or (isinstance(x, float) and math.isnan(x)):
#             v.append(0.0)
#         else:
#             v.append(float(x))
#     if len(v) != dims:
#         raise ValueError(f"vector length {len(v)} != {dims}")
#     return v

# def _norm_feat_keys(feat: Dict[str, Any]) -> Dict[str, Any]:
#     """'a/b/c' → 'a.b.c'로 통일"""
#     out = {}
#     for k, v in (feat or {}).items():
#         nk = str(k).replace("/", ".").replace("..", ".")
#         out[nk] = v
#     return out

# def _split_tags(s) -> list:
#     if s is None:
#         return []
#     if isinstance(s, (list, tuple)):
#         return [str(t).strip().lower() for t in s if str(t).strip()]
#     return [t.strip().lower() for t in str(s).replace(",", ";").split(";") if t.strip()]

# def build_es_doc(
#     *,
#     doc_id: str,
#     session_id: str,
#     camera_id: str,
#     step_idx: int,
#     time_ms: int,
#     text: str,
#     embedding: list,
#     image_ref: str = "",
#     labels: Dict[str, Any] = None,   # 선택
#     meta: Dict[str, Any] = None,     # 선택
#     feat: Dict[str, Any] = None      # 선택
# ) -> dict:
#     labels = dict(labels or {})
#     if "nl_tags" in labels:
#         labels["nl_tags"] = _split_tags(labels["nl_tags"])

#     doc = {
#         "doc_id": doc_id,
#         "session_id": session_id,
#         "camera_id": camera_id,
#         "step_idx": int(step_idx),
#         "time_ms": int(time_ms) if time_ms is not None else 0,
#         "text": text or "",
#         "image_ref": image_ref or "",
#         "vector": _ensure_dims(embedding, _DIMS),
#         "labels": labels,
#         "meta": dict(meta or {}),
#         "feat": _norm_feat_keys(dict(feat or {}))
#     }
#     return doc
