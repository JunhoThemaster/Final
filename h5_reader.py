# -*- coding: utf-8 -*-
"""
h5에서 step 개수와 대표 액션/관절 수치 일부를 읽어
자연어 요약에 사용할 '요점값'을 반환하는 모듈
"""
from typing import Dict, Any
import h5py

def get_num_steps(h5_path: str) -> int:
    with h5py.File(h5_path, "r") as f:
        ds = f.get("/observation/timestamp/control/step_start")
        if ds is not None:
            return int(len(ds[()]))
        for name in ("/observation/timestamp/step", "/observation/timestamp"):
            if name in f:
                arr = f[name][()]
                if arr.ndim == 1:
                    return int(len(arr))
    raise RuntimeError("step 개수를 찾을 수 없습니다. h5 구조를 확인하세요.")

def sample_action_numbers(h5_path: str, idx: int, max_joints: int = 6) -> Dict[str, Any]:
    out = {}
    with h5py.File(h5_path, "r") as f:
        def safe(name):
            return name in f and f[name][()].ndim in (1,2)

        for key in ("/action/joint_position", "/action/joint_positions", "/action/target_cartesian_position"):
            if safe(key):
                arr = f[key][()]
                if arr.ndim == 1:
                    vals = [float(arr[idx])]
                else:
                    D = arr.shape[1]
                    j = min(D, max_joints)
                    vals = [float(arr[idx, d]) for d in range(j)]
                out[key.split("/")[-1]] = vals

        for key in ("/observation/cartesian_position", "/observation/ee_cartesian_position"):
            if safe(key):
                arr = f[key][()]
                if arr.ndim == 1:
                    vals = [float(arr[idx])]
                else:
                    D = arr.shape[1]
                    j = min(D, 3)
                    vals = [float(arr[idx, d]) for d in range(j)]
                out[key.split("/")[-1]] = vals
    return out
