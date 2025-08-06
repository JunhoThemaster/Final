// src/components/VoiceLevelMeter.tsx
import React, { useEffect, useRef, useState } from "react";
import AudioVisualizer from "./AudioVisualizer";
export interface AudioAnalysisResult {
  text: string;
  emotion: string;
  probabilities: Record<string, number>;
}

interface Props {
  isRecording: boolean;
  userId: string;
  token: string;
  onResult: (result: AudioAnalysisResult) => void;  // 🔥 수정
}

const VoiceLevelMeter: React.FC<Props> = ({ isRecording, userId, token, onResult }) => {
  const [volume, setVolume] = useState(0);
  const [playUrl, setPlayUrl] = useState<string | null>(null);     // ▶️ 재생용 URL
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const tempBufferRef = useRef<Float32Array[]>([]);

  const hasSentRef = useRef(false); // 중복 전송 방지

useEffect(() => {
  if (isRecording) {
    hasSentRef.current = false; // 녹음 시작 시 초기화
    startMic();
  } else {
    stopMic();
  }

  return () => {
    // ❌ 여기에서 stopMic 제거!
    URL.revokeObjectURL(playUrl || "");
  };
}, [isRecording]);


  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { noiseSuppression: true, echoCancellation: true, autoGainControl: true }
      });
      const audioCtx = new AudioContext();
      const src = audioCtx.createMediaStreamSource(stream);
      const proc = audioCtx.createScriptProcessor(4096, 1, 1);

      proc.onaudioprocess = e => {
        const input = e.inputBuffer.getChannelData(0);
        tempBufferRef.current.push(new Float32Array(input));
        const avg = input.reduce((s, v) => s + Math.abs(v), 0) / input.length;
        setVolume(Math.min(100, Math.round(avg * 100)));
      };

      src.connect(proc);
      proc.connect(audioCtx.destination);

      audioContextRef.current = audioCtx;
      processorRef.current = proc;
    } catch (err) {
      console.error("마이크 접근 실패:", err);
    }
  };

  const stopMic = async () => {
    // 1) 녹음 중지

    if (hasSentRef.current) return; // ✅ 이미 보냈으면 중단
    hasSentRef.current = true;
    processorRef.current?.disconnect();
    audioContextRef.current?.close();
    const origSR = audioContextRef.current?.sampleRate || 48000;
    audioContextRef.current = null;
    processorRef.current = null;

    // 2) Float32Array 합치기
    const chunks = tempBufferRef.current.splice(0);
    const totalLen = chunks.reduce((s, c) => s + c.length, 0);
    if (totalLen === 0) { setVolume(0); return; }
    const merged = new Float32Array(totalLen);
    let off = 0;
    for (const c of chunks) {
      merged.set(c, off);
      off += c.length;
    }

    // 3) 16kHz 다운샘플링 via OfflineAudioContext
    const offline = new OfflineAudioContext(1, Math.ceil(totalLen * 16000 / origSR), 16000);
    const buf = offline.createBuffer(1, totalLen, origSR);
    buf.copyToChannel(merged, 0);
    const src = offline.createBufferSource();
    src.buffer = buf;
    src.connect(offline.destination);
    src.start();
    const rendered = await offline.startRendering();   // AudioBuffer @16kHz
    const ds = rendered.getChannelData(0);

    // 4) PCM16 변환
    const pcm16 = new Int16Array(ds.length);
    for (let i = 0; i < ds.length; i++) {
      const s = Math.max(-1, Math.min(1, ds[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // 5) WAV 헤더 붙이기
    const wavBlob = encodeWAV(pcm16, 1, 16000);

    // ▶️ 즉시 재생
    const url = URL.createObjectURL(wavBlob);
    setPlayUrl(url);

    // 6) FormData로 서버 전송
    const form = new FormData();
    form.append("audio_file", wavBlob, "audio.wav");
    try {
      const res = await fetch(
        `http://localhost:8000/api/user/audio/${userId}?token=${token}`,
        { method: "POST", body: form }
      );
      const data = await res.json();
      onResult({
        text: data.text,
        emotion: data.emotion,
        probabilities: data.probabilities,
      });

    } catch (err) {
      console.error("오디오 전송 실패:", err);
    }

    setVolume(0);
  };

  // WAV 인코딩 (RIFF 헤더)
  const encodeWAV = (samples: Int16Array, channels: number, sampleRate: number) => {
    const buf = new ArrayBuffer(44 + samples.length * 2);
    const dv = new DataView(buf);
    writeString(dv, 0, "RIFF"); dv.setUint32(4, 36 + samples.length * 2, true);
    writeString(dv, 8, "WAVE"); writeString(dv, 12, "fmt "); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, channels, true);
    dv.setUint32(24, sampleRate, true);
    dv.setUint32(28, sampleRate * channels * 2, true);
    dv.setUint16(32, channels * 2, true); dv.setUint16(34, 16, true);
    writeString(dv, 36, "data"); dv.setUint32(40, samples.length * 2, true);
    let off = 44;
    for (let i = 0; i < samples.length; i++, off += 2) {
      dv.setInt16(off, samples[i], true);
    }
    return new Blob([dv], { type: "audio/wav" });
  };
  const writeString = (dv: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) dv.setUint8(offset + i, str.charCodeAt(i));
  };

  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ fontWeight: "bold", marginBottom: "0.5rem" }}>🎤 마이크 레벨</div>
      <AudioVisualizer audioLevel={volume} />

      {/* ▶️ 다운샘플된 WAV 바로 재생 */}
   
    </div>
  );
};

export default VoiceLevelMeter;
