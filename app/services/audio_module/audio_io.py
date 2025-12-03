import soundfile as sf
from scipy.signal import resample_poly
import numpy as np
# 프론트에서 받아오는 wav 는 기본적으로 44100 이라서 학습전 멜스펙토그램으로 변환 -> 스펙토 이미지를 이용해 학습했는데 변환 과정에서 샘플링레이트가 16000이었기에 변환과정이 필요
def load_audio_float32(path: str):
    target_sr = 16000
    y, sr = sf.read(path)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != target_sr:
        y = resample_poly(y, target_sr, sr)
    return y.astype(np.float32)  #  이미 16000Hz 로 리샘플된 오디오
