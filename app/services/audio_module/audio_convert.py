import subprocess
import os

def convert_webm_to_wav(webm_path: str, wav_path: str):
    """
    Converts a .webm audio file to .wav using ffmpeg.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return wav_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 변환 실패: {e}")
        raise RuntimeError("WebM → WAV 변환 중 오류 발생")
