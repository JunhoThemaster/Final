import librosa
import numpy as np
import torch
def preprocess_audio(audio, sr=16000, n_fft=2048, hop_length=512, n_mels=128, max_len=256):
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels
    )
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    mel_db = (mel_db - np.mean(mel_db)) / (np.std(mel_db) + 1e-6)

    # Padding or trimming
    if mel_db.shape[1] < max_len:
        pad_width = max_len - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad_width)), mode='constant')
    else:
        start = (mel_db.shape[1] - max_len) // 2
        mel_db = mel_db[:, start:start + max_len]

    return torch.tensor(mel_db).unsqueeze(0).unsqueeze(0).float()