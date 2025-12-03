import numpy as np
import librosa
import sounddevice as sd
import torch
from .extract_melspectogram import preprocess_audio


from ...DL_model.CNNBILSTM import CNNBiLSTM

#  오디오 파라미터 설정
SR = 16000           # 샘플링 레이트
DURATION = 4         # 녹음 시간(초)
SAMPLES = SR * DURATION
DEVICE_INDEX = 1 

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CNNBiLSTM().to(device)
model.load_state_dict(torch.load("app/services/audio_module/audio_model.pth", map_location=device))
model.eval()
label_classes = np.load("app/services/audio_module/label_encoder_classes.npy", allow_pickle=True)




def predict_emotion(audio):
    mel_tensor = preprocess_audio(audio).to(device)

    # 시각화
    mel_np = mel_tensor.squeeze().cpu().numpy()
  

    # 추론
    with torch.no_grad():
        output = model(mel_tensor)
        pred = output.argmax(1).item()
        probs = torch.softmax(output, dim=1).cpu().numpy().squeeze()

    print(" 감정별 확률:")
    for i, p in enumerate(probs):
        print(f"  {label_classes[i]:<10}: {p:.2f}")

    return label_classes[pred],probs
