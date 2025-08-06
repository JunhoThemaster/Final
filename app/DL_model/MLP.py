# app/services/analyzer.py

import torch
import numpy as np
from typing import List

class MLPClassifier(torch.nn.Module):
    def __init__(self, input_dim, num_classes):
        super(MLPClassifier, self).__init__()
        self.model = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 64),
            torch.nn.BatchNorm1d(64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(32, num_classes)
        )

    def forward(self, x):
        return self.model(x)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = MLPClassifier(input_dim=15, num_classes=3).to(device)
model.load_state_dict(torch.load("app/services/video_module/model_3class.pth", map_location="cpu"))
model.eval()

label_map = {0: "불안정", 1: "자신감", 2: "자연스러움"}
emotion_list = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

def emotion_to_onehot(emotion: str) -> List[int]:
    onehot = [0] * len(emotion_list)
    if emotion in emotion_list:
        onehot[emotion_list.index(emotion)] = 1
    return onehot

def analyze_vector(input_vector: List[float]) -> str:
    x = torch.tensor(np.array(input_vector, dtype=np.float32)).unsqueeze(0).to(device)
    with torch.no_grad():
        output = model(x)
        pred = torch.argmax(output, dim=1).item()
    return label_map[pred]
